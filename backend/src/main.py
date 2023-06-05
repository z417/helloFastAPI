#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 10:03
 * @LastEditors  : Yuri
 * @LastEditTime : 05/Jun/2023 06:22
 * @FilePath     : /teach/helloFastAPI/backend/src/main.py
 * @Description  : file desc
'''
import uvicorn
from fastapi import FastAPI
from src.exceptions import APIException, http_exception_handler
from src.settings import db_init, middleware_init, router_init, target_env_init
from src.tools.dbs import database
from src.tools.logs import L


async def start_event() -> None:
    from logging import getLogger
    uvicorn_access = getLogger("uvicorn.access")
    uvicorn_access.handlers = L.handlers
    L.info(msg='Server start')


async def shutdown_event() -> None:
    L.info(msg='Server shutdown')


def create_app() -> FastAPI:
    app = FastAPI(
        title="HZN_DEMO",
        version="0.0.1",
        on_startup=[start_event],
        on_shutdown=[shutdown_event],
        openapi_url='/api/v3/openapi.json',
        swagger_ui_parameters={"defaultModelsExpandDepth": -1},
        exception_handlers={APIException: http_exception_handler},
    )

    app.state.database = database
    # 建表 TODO: 判断是否需要初始化
    db_init(app)

    # 初始化路由配置
    router_init(app)

    # 初始化中间件
    middleware_init(app)

    # 加载环境配置
    target_env_init(app)

    return app


app = create_app()
# @app.get('/api/files/{filePath:path}')
# async def get_file(filePath: str):
#     return {filePath}

if __name__ == '__main__':
    uvicorn.run(
        app='main:app',
        host='0.0.0.0',
        port=12345,
        log_level="debug",
        reload=True,
    )
