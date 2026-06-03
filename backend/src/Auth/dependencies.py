from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Tuple, Union

import jwt
from cacheout import LFUCache
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.Auth.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    DEFAULT_TOKEN_EXPIRE_MINUTES,
    FLAG_USER_STATUS_LOCKED,
    PARSE_JWT_COUNT_PER_MINUTE,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    TOKEN_URL,
    auth_settings,
)
from src.Auth.crud import get_user_by_email
from src.Auth.models import User
from src.common import BadRequestException
from src.common.dependencies import get_async_session

cache = LFUCache()


async def create_token(data: dict, expires_delta: Union[timedelta, None] = None) -> Tuple[str, dict]:
    to_encode = data.copy()
    current_timestamp = datetime.now(timezone.utc)
    if expires_delta:
        expire = current_timestamp + expires_delta
    else:
        expire = current_timestamp + timedelta(minutes=DEFAULT_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": current_timestamp, "scope": "access_token"})
    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return access_token, to_encode


async def create_refresh_token(data: dict) -> str:
    payload = data.copy()
    exp = payload["exp"]
    match exp:
        case int() | float():
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        case datetime():
            exp_dt = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
        case _:
            exp_dt = datetime.now(timezone.utc)

    new_exp = exp_dt + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    payload.update(
        {
            "exp": new_exp,
            "scope": "refresh_token",
        }
    )
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def renew_token_via_refresh(refresh_token: str, session: AsyncSession) -> str:
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload["scope"] != "refresh_token":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid scope for token",
            )
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from e

    email = payload.get("sub")
    token_session_id = payload.get("session_id")
    if not email or not token_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    user = (await get_user_by_email(session, email)).scalar_one_or_none()
    if not user or user.user_status == FLAG_USER_STATUS_LOCKED or user.current_session_id != token_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or logged in elsewhere",
        )
    user_data = {k: v for k, v in payload.items() if k not in ("exp", "iat", "scope")}
    return (await create_token(user_data, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)))[0]


async def parse_jwt_data(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl=TOKEN_URL)),
) -> Mapping[str, Any]:
    # Limit interface invocation frequency per user per minute
    num = cache.get(token)
    cache.set(token, num + 1 if num else 1, ttl=1 * 60)
    if cache.get(token) > PARSE_JWT_COUNT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"WWW-Authenticate": f"Bearer {token}"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e
    return payload


async def authenticate_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session),
) -> User:

    plain_password = form_data.password
    if auth_settings.BOOKING_SM4_PASSWORD_ENCRYPT:
        try:
            # 1. 提取物理 IV (前32个 Hex 字符) 与 密文 (32位之后)
            raw_password_hex = form_data.password.strip()
            if len(raw_password_hex) < 64:
                raise ValueError("密文长度非法，必须包含 16 字节随机 IV 头部")

            iv_hex = raw_password_hex[:32]
            ct_hex = raw_password_hex[32:]

            iv = bytes.fromhex(iv_hex)
            ct = bytes.fromhex(ct_hex)

            # 2. SM4 CBC 模式解密

            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

            key = auth_settings.BOOKING_SM4_KEY.encode()
            cipher = Cipher(algorithms.SM4(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(ct) + decryptor.finalize()

            unpadder = padding.PKCS7(128).unpadder()
            password_bytes = unpadder.update(decrypted_padded) + unpadder.finalize()
            decrypted_payload = password_bytes.decode()

            # 3. 动态时间戳解析与 5 分钟重放时效性校验
            if ":" not in decrypted_payload:
                raise ValueError("密文负载格式非法，缺少分隔符")

            timestamp_str, plain_password = decrypted_payload.split(":", 1)
            ts_ms = int(timestamp_str)
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

            if abs(now_ms - ts_ms) > 300000:
                raise ValueError("接口安全验证失败，加密登录密码已超出 5 分钟有效期")

        except Exception as e:
            raise BadRequestException(f"密文解密失败，或安全防重放拦截: {str(e)}")

    user = (await get_user_by_email(session, form_data.username)).scalar_one_or_none()
    if user and user.verify_passwd(plain_password):
        if user.user_status == FLAG_USER_STATUS_LOCKED:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Your account is locked")
        return user
    raise BadRequestException("Incorrect username or password")


async def get_current_user(
    payload: dict = Depends(parse_jwt_data),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"Authenticate": "Bearer"},
    )
    email = payload.get("sub")
    if not email:
        raise credentials_exception
    user = (await get_user_by_email(session, email)).scalar_one_or_none()
    if not user or user.user_status == FLAG_USER_STATUS_LOCKED:
        raise credentials_exception

    token_session_id = payload.get("session_id")
    if not token_session_id or token_session_id != user.current_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or logged in elsewhere",
            headers={"Authenticate": "Bearer"},
        )
    return user
