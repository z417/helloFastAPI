from json import dumps, loads
from pathlib import Path

from starlette.config import Config, environ
from starlette.datastructures import Secret

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE: str = environ.get("ENV_FILE", str(BACKEND_DIR / ".env"))
if not environ.get("ENV_FILE"):
    print(f"-----ENV_FILE not specified, {ENV_FILE} used as default-----")
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
        default='{"name": "ENCL-1.0", "url": "file:///LICENSE"}',
    )
    APP_CONTACT = config(
        "APP_CONTACT",
        cast=loads,
        default='{"name": "HZN", "url": "https://www.haozhinuo.com", "email": "zhuwei@haozhinuo.com"}',
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

    # =====  =====
    DB_POOL_MODE: str = config("DB_POOL_MODE", cast=str, default="queue")  # 'queue' 启用连接池, 'null' 禁用


settings = Settings()


def auto_generate_env_file() -> None:
    """
    自愈防线：聚合全局和各业务子模块配置，逆向生成 backend/.env 文件
    """
    env_path = Path(ENV_FILE)
    if not env_path.exists():
        print(f'-----"{ENV_FILE}" not exists, initial once at 1st run time-----')

        # 动态延迟导入业务配置类，优雅防止循环引用
        from src.Cinema.config import CinemaSettings

        all_lines = []

        # 1. 抽取全局核心基底
        for k in filter(lambda x: not x.startswith("__"), vars(Settings)):
            v = getattr(settings, k)
            v = v if not isinstance(v, (dict, list)) else dumps(v)
            all_lines.append(f"{k}={v}")

        # 2. 抽取并追加影院业务
        for k in filter(lambda x: not x.startswith("__"), vars(CinemaSettings)):
            if k in vars(Settings):
                continue  # 过滤重复项
            v = getattr(CinemaSettings, k)
            v = v if not isinstance(v, (dict, list)) else dumps(v)
            all_lines.append(f"{k}={v}")

        with env_path.open(mode="w+", encoding="utf-8") as f:
            f.write("\n".join(all_lines) + "\n")
            f.flush()


# 执行自愈防线
auto_generate_env_file()

if __name__ == "__main__":
    print(settings.APP_TITLE)
    print(settings.OPENAPI_URL)
    print(settings.APP_LICENSE)
    print(settings.UVICORN_LOG_LEVEL)
    print(settings.ENABLE_API_DOCS)
    print(settings.UVICORN_SSL_KEYFILE)
    print(settings.DB_URL)
    print(settings.ENGINE_ARGS)
