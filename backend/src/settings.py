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
    APP_VERSION: str = config("APP_VERSION", default="1.0.0")
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
    ENV_FILE: str = ENV_FILE

    # ===== 影院核心业务高并发与安全热配置 =====
    DB_POOL_MODE: str = config("DB_POOL_MODE", cast=str, default="queue")  # 'queue' 启用连接池, 'null' 禁用
    BOOKING_LOCK_MODE: str = config("BOOKING_LOCK_MODE", cast=str, default="pessimistic")  # 'none' 无锁, 'pessimistic' 悲观锁, 'optimistic' 乐观锁
    CINEMA_SLOW_QUERY: bool = config("CINEMA_SLOW_QUERY", cast=bool, default=False)  # 慢查询开关
    BOOKING_SIGNATURE_CHECK: bool = config("BOOKING_SIGNATURE_CHECK", cast=bool, default=False)  # 接口签名校验开关
    BOOKING_SIGNATURE_SECRET: str = config("BOOKING_SIGNATURE_SECRET", cast=str, default="hello_cinema_range_secret_key")  # 签名秘钥，以.env配置优先级最高
    BOOKING_SM3_SIGNATURE_CHECK: bool = config("BOOKING_SM3_SIGNATURE_CHECK", cast=bool, default=False)  # 接口国密SM3签名校验开关
    BOOKING_SM4_PASSWORD_ENCRYPT: bool = config("BOOKING_SM4_PASSWORD_ENCRYPT", cast=bool, default=False)  # 登录密码国密SM4传输加密开关
    BOOKING_SM4_KEY: str = config("BOOKING_SM4_KEY", cast=str, default="hello_cinema_sm4")  # SM4 对称加密密钥，必须为16字节
    AUTH_STRONG_PASSWORD_CHECK: bool = config("AUTH_STRONG_PASSWORD_CHECK", cast=bool, default=False)  # 简单密码强度开关


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
