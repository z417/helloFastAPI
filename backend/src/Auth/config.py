#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 27/Apr/2023 06:55
 * @LastEditors  : Yuri
 * @LastEditTime : 22/May/2023 02:39
 * @FilePath     : /teach/helloFastAPI/backend/src/Auth/config.py
 * @Description  : local config
'''
from passlib.context import CryptContext

TOKEN_URL = "/api/auth/token"
# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY: str = "180c3055d7ae1816e4084901378cbfa15aa84e7484c7bb782295771d0b5854e3"
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
DEFAULT_TOKEN_EXPIRE_MINUTES: int = 15
REFRESH_TOKEN_EXPIRE_MINUTES: int = 300
PWD_CONTEXT: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
