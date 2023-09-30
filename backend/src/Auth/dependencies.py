#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 27/Apr/2023 06:34
 * @LastEditors  : Yuri
 * @LastEditTime : 25/Aug/2023 16:32
 * @FilePath     : /helloFastAPI/backend/src/Auth/dependencies.py
 * @Description  : verify the data conforms to database constraints
"""
from datetime import datetime, timedelta
from typing import Mapping, Tuple, Union

from cacheout import LFUCache
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import ExpiredSignatureError, JWTError, jwt

from src.Auth.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    DEFAULT_TOKEN_EXPIRE_MINUTES,
    FLAG_USER_STATUS_LOCKED,
    PARSE_JWT_COUNT_PER_MINUTE,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    TOKEN_URL,
)
from src.Auth.crud import get_user_by_email
from src.Auth.models import User
from src.common import BadRequestException, get_async_session

cache = LFUCache()


async def create_token(data: dict, expires_delta: Union[timedelta, None] = None) -> Tuple[str, dict]:
    to_encode = data.copy()
    current_timestamp = datetime.utcnow()
    if expires_delta:
        expire = current_timestamp + expires_delta
    else:
        expire = current_timestamp + timedelta(minutes=DEFAULT_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": current_timestamp, "scope": "access_token"})
    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return access_token, to_encode


async def create_refresh_token(data: dict) -> str:
    exp = data["exp"]
    data.update(
        {
            "exp": datetime.fromtimestamp(exp) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
            "scope": "refresh_token",
        }
    )
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


async def renew_token_via_refresh(refresh_token: str) -> Union[str, HTTPException]:
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload["scope"] != "refresh_token":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid scope for token",
            )
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from e
    except ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired") from e
    return (await create_token(payload, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)))[0]


async def parse_jwt_data(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl=TOKEN_URL)),
) -> Union[Mapping, HTTPException]:
    # Limit interface invocation frequency per user per minute
    num = cache.get(token)
    cache.set(token, num + 1 if num else 1, ttl=1 * 60)
    if cache.get(token) > PARSE_JWT_COUNT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Authenticate": f"Bearer {token}"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e
    except ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from e
    return payload


async def authenticate_user(
    form_data=Depends(OAuth2PasswordRequestForm),
    session=Depends(get_async_session),
) -> Union[User, HTTPException, BadRequestException]:
    user: Union[User, None] = (await get_user_by_email(session, form_data.username)).scalar_one_or_none()
    if user and user.verify_passwd(form_data.password):
        if user.user_status == FLAG_USER_STATUS_LOCKED:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Your account is locked")
        return user
    raise BadRequestException("Incorrect username or password")


async def get_current_user(
    payload: dict = Depends(parse_jwt_data),
    session=Depends(get_async_session),
) -> Union[User, HTTPException]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"Authenticate": "Bearer"},
    )
    email = payload.get("sub")
    if not email:
        raise credentials_exception
    user: Union[User, None] = (await get_user_by_email(session, email)).scalar_one_or_none()
    if not user or user.user_status == FLAG_USER_STATUS_LOCKED:
        raise credentials_exception
    return user
