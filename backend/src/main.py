#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 10:03
 * @LastEditors  : Yuri
 * @LastEditTime : 05/May/2023 05:59
 * @FilePath     : /teach/helloFastAPI/backend/src/main.py
 * @Description  : file desc
'''
import uvicorn
from fastapi import FastAPI
from src.Auth.router import router as auth_router
from src.FileCodeBox.router import router as file_code_box_router
from src.tools.logs import L
from starlette.middleware.cors import CORSMiddleware
from src.exceptions import APIException, http_exception_handler
from src.tools.dbs import database


def conf_init(app: FastAPI):
    from os import environ
    env = environ.get('ENVIRONMENT', 'dev')
    L.info(msg=f'Start server with {env} environment')
    if env == 'prod':
        app.docs_url = None
        app.redoc_url = None
        app.debug = False


def router_init(app: FastAPI):
    app.include_router(auth_router)
    app.include_router(file_code_box_router)


def middleware_init(app: FastAPI):
    # cors origin settings
    origins = ['*']
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def db_init(app):

    @app.on_event("startup")
    async def startup() -> None:
        L.info('Process database connection')
        database_ = app.state.database
        if not database_.is_connected:
            await database_.connect()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        database_ = app.state.database
        if database_.is_connected:
            await database_.disconnect()


async def start_event() -> None:
    L.info(msg='Server start')


async def shutdown_event() -> None:
    L.info(msg='Server shutdown')


def create_app() -> FastAPI:
    app = FastAPI(
        # routes=,
        title="HZN_DEMO",
        description="Hello FastAPI",
        version="0.0.1",
        on_startup=[start_event],
        on_shutdown=[shutdown_event],
        openapi_url='/api/v2/openapi.json',
        contact={
            "name": "HZN",
            "url": "https://www.haozhinuo.com",
            "email": "zhongtuo@haozhuinuo.com"
        },
        license_info={
            'name': 'LGPL-1.3',
            'url': 'https://www.gnu.org/licenses/fdl-1.3-standalone.html'
        },
        responses={404: {"description": "Not found"}},
        swagger_ui_parameters={"defaultModelsExpandDepth": -1},
        exception_handlers={APIException: http_exception_handler},
    )

    # 加载配置
    conf_init(app)

    # 初始化路由配置
    router_init(app)

    # 初始化中间件
    middleware_init(app)

    app.state.database = database
    # 建表 TODO: 判断是否需要初始化
    db_init(app)

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
        debug=True,
        reload=True,
    )
