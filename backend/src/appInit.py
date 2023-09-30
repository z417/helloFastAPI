#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 10:03
 * @LastEditors  : Yuri
 * @LastEditTime : 25/Aug/2023 14:14
 * @FilePath     : /helloFastAPI/backend/src/appInit.py
 * @Description  : file desc
"""
from uuid import uuid1

from fastapi import FastAPI, Request, Response
from starlette.middleware.cors import CORSMiddleware

from src.Auth import auth_router
from src.settings import settings
from src.tools import L


class AppInit:
    def __init__(self, app: FastAPI):
        self.__app__ = app
        self.middleware_init()  # order 1
        self.router_init()  # order 2
        self.target_env_init()  # order 3

    def custom_openapi(self):
        if self.__app__.openapi_schema:
            return
        from fastapi.openapi.utils import get_openapi

        openapi_schema = get_openapi(
            title=self.__app__.title,
            version=self.__app__.version,
            routes=self.__app__.routes,
        )
        http_methods = [
            "post",
            "get",
            "put",
            "delete",
            "patch",
            "delete",
            "head",
            "options",
        ]
        # look for the error 422 and removes it
        for method in openapi_schema.get("paths"):  # type: ignore
            for e in http_methods:
                try:  # do not try-except outside the for loop, cause some method has no 422
                    del openapi_schema["paths"][method][e]["responses"]["422"]
                except KeyError:
                    pass
        for schema in list(openapi_schema.get("components").get("schemas")):  # type: ignore
            if schema in ("HTTPValidationError", "ValidationError"):
                del openapi_schema["components"]["schemas"][schema]
        openapi_schema["info"].update(
            {
                "description": settings.APP_DESC,
                "license": settings.APP_LICENSE,
                "contact": settings.APP_CONTACT,
            }
        )
        self.__app__.openapi_schema = openapi_schema

    def target_env_init(self):
        ead = settings.ENABLE_API_DOCS
        L.debug(f'Start server with {"enable" if ead else "disable"} api docs')
        if ead:
            self.custom_openapi()

    def router_init(self):
        self.__app__.include_router(auth_router)
        # app.include_router(file_code_box_router)

    def middleware_init(self):
        origins = ["*"]
        self.__app__.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        # self.__app__.add_middleware(
        #     DBEngineMiddleware,
        #     db_url=str(settings.DB_URL),
        #     engine_args=settings.ENGINE_ARGS,
        # )

        @self.__app__.middleware("http")
        async def add_request_id(req: Request, call_next):
            req.state.request_id = str(uuid1())
            resp: Response = await call_next(req)
            resp.headers["X-Request-ID"] = req.state.request_id
            return resp
