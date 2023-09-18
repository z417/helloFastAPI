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

from sqlalchemy.ext.asyncio.session import AsyncSession
from src.middlewares import asyncDbengine


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(asyncDbengine, expire_on_commit=False) as session:
        yield session
