#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 19/Jun/2023 11:42
 * @LastEditors  : Yuri
 * @LastEditTime : 25/Aug/2023 16:27
 * @FilePath     : /helloFastAPI/backend/src/middlewares/dbEngine.py
 * @Description  : database engine module, created by middleware
"""
from typing import Dict, Optional, Union

from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.pool import NullPool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp

asyncDbengine: AsyncEngine


class DBEngineMiddleware(BaseHTTPMiddleware):
    """
    Database middleware
    """

    def __init__(
        self,
        app: ASGIApp,
        db_url: Union[str, URL],
        custom_engine: Optional[AsyncEngine] = None,
        engine_args: Union[Dict, None] = None,
        expire_on_commit: bool = False,
    ) -> None:
        super().__init__(app)
        global asyncDbengine  # pylint: disable=W0603
        self.expire_on_commit = expire_on_commit
        engine_args = engine_args or {}
        if custom_engine:
            asyncDbengine = custom_engine
        else:
            if not db_url:
                raise ValueError(
                    "You need to pass a db_url or a custom_engine parameter."
                )
            asyncDbengine = create_async_engine(
                db_url,
                # If the same engine must be shared between different loop, it should be configured to disable pooling using NullPool, preventing the Engine from using any connection more than once:
                poolclass=NullPool,
                **engine_args,
            )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        """
        should be re-write while inheriting "BaseHTTPMiddleware",
        otherwise will get NotImplementedError
        """
        response = await call_next(request)
        return response


if __name__ == "__main__":
    import asyncio

    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    from fastapi import FastAPI
    from sqlalchemy import text  # pylint: disable=C0412

    DBEngineMiddleware(
        FastAPI(),
        db_url=DATABASE_URL,
        engine_args={
            "echo": True,
            "future": True,  # Uses SQLAlchemy 2.0 API, backwards compatible
            "connect_args": {"check_same_thread": False},
        },
    )

    async def test_query():
        async with asyncDbengine.connect() as conn:
            res = await conn.execute(text("select 'hello world';"))
        print(res.all())
        await asyncDbengine.dispose()

    asyncio.run(test_query())
