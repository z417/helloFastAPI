#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 25/Jun/2023 08:40
 * @LastEditors  : Yuri
 * @LastEditTime : 25/Jun/2023 08:40
 * @FilePath     : /helloFastAPI/backend/src/common/dependencies.py
 * @Description  : file desc
"""
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.settings import settings


async def get_async_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine: AsyncEngine = create_async_engine(
        str(settings.DB_URL),
        # If the same engine must be shared between different loop, it should be
        # configured to disable pooling using NullPool, preventing the Engine from using any connection more than once
        poolclass=NullPool,
        **settings.ENGINE_ARGS,
    )
    try:
        yield engine
    finally:
        await engine.dispose()


async def get_async_session(engine=Depends(get_async_engine)) -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSession(engine, autoflush=True, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()


if __name__ == "__main__":
    from sqlalchemy import text

    async def test_engine():
        e = get_async_engine()
        engine = await e.__anext__()
        async with engine.connect() as conn:
            res = await conn.execute(text("select 'hello world';"))
        print(res.all())

    async def test_session():
        e = get_async_engine()
        engine = await e.__anext__()
        session_gen = get_async_session(engine)
        session = await session_gen.__anext__()
        res = await session.execute(text("select 'hello fastapi';"))
        print(res.all())

    import asyncio

    async def main():
        await asyncio.gather(test_engine(), test_session())

    asyncio.run(main())
