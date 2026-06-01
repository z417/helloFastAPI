#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 10:03
 * @LastEditors  : Yuri
 * @LastEditTime : 25/Aug/2023 14:14
 * @FilePath     : /helloFastAPI/backend/src/main.py
 * @Description  : file desc
"""
from fastapi import FastAPI
from uvicorn import run

from src.appInit import AppInit
from src.common import APIException, http_exception_handler
from src.settings import settings
from src.utils import L


async def start_event() -> None:
    L.info("Server start")


async def shutdown_event() -> None:
    L.info("Server shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        version=settings.APP_VERSION,
        on_startup=[start_event],
        on_shutdown=[shutdown_event],
        openapi_url=settings.OPENAPI_URL,
        swagger_ui_parameters={"defaultModelsExpandDepth": -1},
        exception_handlers={APIException: http_exception_handler},
        docs_url="/docs" if settings.ENABLE_API_DOCS else None,
        redoc_url="/redoc" if settings.ENABLE_API_DOCS else None,
    )
    AppInit(app)
    return app


helloFastApi = create_app()

if __name__ == "__main__":
    run(
        app="src.main:helloFastApi",
        host=settings.UVICORN_HOST,
        port=settings.UVICORN_PORT,
        log_config=settings.UVICORN_LOG_CONFIG,
        reload=settings.UVICORN_RELOAD,
        ssl_keyfile=settings.UVICORN_SSL_KEYFILE if settings.UVICORN_SSL_KEYFILE else None,
        ssl_certfile=settings.UVICORN_SSL_CERTFILE if settings.UVICORN_SSL_CERTFILE else None,
    )
