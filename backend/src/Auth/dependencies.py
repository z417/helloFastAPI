#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 27/Apr/2023 06:34
 * @LastEditors  : Yuri
 * @LastEditTime : 02/Jun/2023 09:56
 * @FilePath     : /teach/helloFastAPI/backend/src/Auth/dependencies.py
 * @Description  : verify the data conforms to database constraints
'''
from datetime import datetime, timedelta
from typing import Mapping, Tuple, Union, Optional
from cacheout import LFUCache
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from src.Auth.config import (ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM,
                             DEFAULT_TOKEN_EXPIRE_MINUTES, PWD_CONTEXT,
                             REFRESH_TOKEN_EXPIRE_MINUTES, SECRET_KEY, TOKEN_URL)
from src.Auth.models import Users
from src.exceptions import BadRequestException

cache = LFUCache()


async def create_token(
        data: dict,
        expires_delta: Union[timedelta, None] = None
) -> Tuple[str, dict]:
    to_encode = data.copy()
    current_timestamp = datetime.utcnow()
    if expires_delta:
        expire = current_timestamp + expires_delta
    else:
        expire = current_timestamp + \
            timedelta(minutes=DEFAULT_TOKEN_EXPIRE_MINUTES)
    to_encode.update(
        {'exp': expire, 'iat': current_timestamp, 'scope': 'access_token'})
    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return access_token, to_encode


async def create_refresh_token(data: dict) -> str:
    exp = data['exp']
    data.update({
        'exp': datetime.fromtimestamp(exp) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
        'scope': 'refresh_token'})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


async def renew_token_via_refresh(refresh_token: str) -> str:
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload['scope'] != 'refresh_token':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid scope for token')
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token")
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token expired')
    new_token = (await create_token(payload, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)))[0]
    return new_token


async def parse_jwt_data(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl=TOKEN_URL))
) -> Mapping:
    # Limit interface invocation frequency per user per minute
    num = cache.get(token)
    cache.set(token, num+1 if num else 1, ttl=1*60)
    if cache.get(token) > 60:  # Plan to use Users.frequency_max
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={'Authenticate': f"Bearer {token}"}
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token")
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token expired')
    return payload


async def get_user_from_db(users: Users = Depends(), *args, **kw) -> Optional[Users]:
    return await Users.objects.get_or_none(*args, **kw, is_deleted=0)


async def get_passwd_hash(passwd: str) -> str:
    '''have not used yet, cause ORM model provided this feature'''
    return PWD_CONTEXT.hash(passwd)


async def verify_passwd(plain_passwd, hashed_passwd) -> bool:
    '''have not used yet, cause ORM model provided this feature'''
    return PWD_CONTEXT.verify(plain_passwd, hashed_passwd)


async def authenticate_user_in_db(user_name: str, passwd: str) -> Users:
    q_user = await get_user_from_db(email__icontains=user_name)
    if not q_user or q_user.password != passwd:
        # raise HTTPException(
        #     status_code=status.HTTP_400_BAD_REQUEST,
        #     detail='Incorrect userName or password'
        # )
        raise BadRequestException('Incorrect userName or password')
    if q_user.user_status == 2:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail='Your account is locked'
        )
    return q_user


async def get_current_user(payload: dict = Depends(parse_jwt_data)) -> Users:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"Authenticate": "Bearer"},
    )
    user_email = payload.get('sub')
    if not user_email:
        raise credentials_exception
    user = await get_user_from_db(email__icontains=user_email)
    if not user:
        raise credentials_exception
    return user
