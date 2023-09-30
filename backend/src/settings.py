#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 02/Jun/2023 14:26
 * @LastEditors  : Yuri
 * @LastEditTime : 25/Aug/2023 13:43
 * @FilePath     : /helloFastAPI/backend/src/settings.py
 * @Description  : file desc
"""
from json import dumps, loads
from pathlib import Path
from typing import Union

from starlette.config import Config, environ
from starlette.datastructures import Secret

ENV_FILE: Union[str, None] = environ.get("ENV_FILE")
if not ENV_FILE:
    print('-----ENV_FILE not specified, ".env" used as default-----')
    ENV_FILE = ".env"
config = Config(ENV_FILE)


class Settings:
    """load settings"""

    APP_NAME: str = config("APP_NAME", default="helloFastApi")
    APP_VERSION: str = config("APP_VERSION", default="0.0.1")
    APP_TITLE: str = config("APP_TITLE", default="Hello FastApi")
    APP_DESC: str = config("APP_DESC", default="A demo for fastapi")
    APP_LICENSE = config(
        "APP_LICENSE",
        cast=loads,
        default='{"name": "LGPL-3.0", "url": "https://www.gnu.org/licenses/gpl-3.0.txt"}',
    )
    APP_CONTACT = config(
        "APP_CONTACT",
        cast=loads,
        default='{"name": "HZN", "url": "https://www.haozhinuo.com", "email": "zhongtuo@haozhinuo.com"}',
    )
    APP_RUN_LOG: str = config("APP_RUN_LOG", cast=str, default="logs/run.log")
    APP_LOG_LEVEL: str = config("APP_LOG_LEVEL", default="INFO")
    # uvicorn_access_log backupCount should set via yml
    APP_LOG_BACKUP_COUNT: int = config("APP_LOG_BACKUP_COUNT", cast=int, default=4)
    OPENAPI_URL: str = config("OPENAPI_URL", cast=str, default="/api/v3/openapi.json")
    ENABLE_API_DOCS: bool = config("ENABLE_API_DOCS", cast=bool, default=False)
    UVICORN_HOST: str = config("UVICORN_HOST", cast=str, default="127.0.0.1")
    UVICORN_PORT: int = config("UVICORN_PORT", cast=int, default=8000)
    UVICORN_LOG_CONFIG: str = config("UVICORN_LOG_CONFIG", cast=str, default="conf/uvicornLog.yml")
    UVICORN_LOG_LEVEL: str = config("UVICORN_LOG_LEVEL", cast=str.lower, default="info")
    UVICORN_RELOAD: bool = config("UVICORN_RELOAD", cast=bool, default=False)
    UVICORN_SSL_KEYFILE: str = config("UVICORN_SSL_KEYFILE", cast=str, default="")
    UVICORN_SSL_CERTFILE: str = config("UVICORN_SSL_CERTFILE", cast=str, default="")
    DB_URL = config("DB_URL", cast=Secret, default="sqlite+aiosqlite:///db.sqlite")
    ENGINE_ARGS = config("ENGINE_ARGS", cast=loads, default='{"future": true}')


settings = Settings()

env_path = Path(ENV_FILE)
if not env_path.exists():
    print(f'-----"{ENV_FILE}" not exists, initial once at 1st run time-----')
    with env_path.open(mode="w+", encoding="utf-8") as f:
        for k in filter(lambda x: not x.startswith("__"), vars(Settings)):
            v = getattr(settings, k)
            v = v if not isinstance(v, dict) else dumps(v)
            f.write(f"{k}={v}\n")
        f.flush()

if __name__ == "__main__":
    print(settings.APP_TITLE)
    print(settings.OPENAPI_URL)
    print(settings.APP_LICENSE)
    print(settings.UVICORN_LOG_LEVEL)
    print(settings.ENABLE_API_DOCS)
    print(settings.UVICORN_SSL_KEYFILE)
    print(settings.DB_URL)
    print(settings.ENGINE_ARGS)
