#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 27/Apr/2023 06:55
 * @LastEditors  : Yuri
 * @LastEditTime : 21/Jun/2023 08:03
 * @FilePath     : /helloFastAPI/backend/src/Auth/config.py
 * @Description  : Auth module config
"""
from typing import Final

from passlib.context import CryptContext

TOKEN_URL = "/api/auth/token"
# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY: Final[str] = "180c3055d7ae1816e4084901378cbfa15aa84e7484c7bb782295771d0b5854e3"
ALGORITHM: Final[str] = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 30
DEFAULT_TOKEN_EXPIRE_MINUTES: Final[int] = 15
REFRESH_TOKEN_EXPIRE_MINUTES: Final[int] = 300
PWD_CONTEXT: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")


if __name__ == "__main__":
    print(PWD_CONTEXT.hash("123456"))
    print(PWD_CONTEXT.verify("123456", "$2b$12$1aTB0U6EJLf5/Ot7SdwfpOhLv77evLV9u27bIsOnjir5bLfW1Gqt."))
