#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 02/Jun/2023 14:26
 * @LastEditors  : Yuri
 * @LastEditTime : 05/Jun/2023 06:21
 * @FilePath     : /teach/helloFastAPI/backend/src/settings.py
 * @Description  : file desc
'''
from os import environ
from uuid import uuid1

from databases import Database
from fastapi import FastAPI, Request, Response
from src.Auth.router import router as auth_router
from src.tools.logs import L
from starlette.middleware.cors import CORSMiddleware


def db_init(app: FastAPI):

    @app.on_event('startup')
    async def startup():
        L.info('Process database connection')
        database_: Database = app.state.database
        if not database_.is_connected:
            await database_.connect()

    @app.on_event('shutdown')
    async def shutdown():
        database_: Database = app.state.database
        if database_.is_connected:
            await database_.disconnect()


def router_init(app: FastAPI):
    app.include_router(auth_router)
    # app.include_router(file_code_box_router)


def middleware_init(app: FastAPI):
    origins = ['*']
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.middleware('http')
    async def add_request_id(r: Request, call_next):
        r.state.request_id = str(uuid1())
        resp: Response = await call_next(r)
        resp.headers['X-Request-ID'] = r.state.request_id
        return resp


def target_env_init(app: FastAPI):
    env = environ.get('ENVIRONMENT', 'dev')
    L.info(f'Start server with {env} environment')
    if env == 'prod':
        app.docs_url = None
        app.redoc_url = None
        app.debug = False
        return
    custom_openapi(app)


def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    http_methods = ["post", "get", "put", "delete",
                    "patch", "delete", "head", "options"]
    # look for the error 422 and removes it
    for method in openapi_schema["paths"]:
        for m in http_methods:
            try:
                del openapi_schema["paths"][method][m]["responses"]["422"]
            except KeyError:
                pass
    for schema in list(openapi_schema["components"]["schemas"]):
        if schema == "HTTPValidationError" or schema == "ValidationError":
            del openapi_schema["components"]["schemas"][schema]
    openapi_schema["info"].update({
        "description": "Hello FastAPI",
        "license": {
            "name": "LGPL-3.0",
            "url": "https://www.gnu.org/licenses/gpl-3.0.txt"
        },
        "contact": {
            "name": "HZN",
            "url": "https://www.haozhinuo.com",
            "email": "zhongtuo@haozhuinuo.com"
        },
    })
    app.openapi_schema = openapi_schema
