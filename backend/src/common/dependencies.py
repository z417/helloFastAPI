import asyncio
import os
from typing import Any, AsyncGenerator, Optional, Tuple

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.settings import settings
from src.utils import L

_engine: Optional[AsyncEngine] = None
_current_pool_mode: Optional[str] = None
_current_db_url: Optional[str] = None
_last_db_file_stat: Optional[Tuple[float, int, int]] = None
_engine_lock = asyncio.Lock()


async def get_async_engine() -> AsyncEngine:
    global _engine, _current_pool_mode, _current_db_url, _last_db_file_stat

    # 物理提取 SQLite 文件路径（如果适用）
    db_path = None
    db_url_str = str(settings.DB_URL)
    if "sqlite" in db_url_str:
        parts = db_url_str.split(":///")
        if len(parts) > 1:
            db_path = parts[-1]

    # 高速获取物理文件的 inode/修改时间/大小
    current_stat = None
    if db_path and os.path.exists(db_path):
        try:
            stat_res = os.stat(db_path)
            current_stat = (stat_res.st_mtime, stat_res.st_ino, stat_res.st_size)
        except Exception:
            pass

    async with _engine_lock:
        # 判定物理文件是否被外部 Pytest/重置 清盘并重建，从而触发连接池热载自愈
        db_file_changed = False
        if db_path and _engine is not None:
            if current_stat != _last_db_file_stat:
                db_file_changed = True
                L.info(f"检测到物理数据库文件 {db_path} 发生时空变更/重建，触发连接池 0 毫秒热载自愈重连...")

        # 检测配置热变更，或者初次启动初始化，或者文件被外部重建
        if _engine is None or _current_pool_mode != settings.DB_POOL_MODE or _current_db_url != str(settings.DB_URL) or db_file_changed:
            # 安全释放旧的连接池引擎
            if _engine is not None:
                L.info("动态检测到数据库性能配置、连接 URL 或物理文件发生变更，安全释放旧连接池引擎并清空句柄...")
                await _engine.dispose()

            _current_pool_mode = settings.DB_POOL_MODE
            _current_db_url = str(settings.DB_URL)
            _last_db_file_stat = current_stat

            engine_kwargs: dict[str, Any] = {}
            if _current_pool_mode == "null":
                L.info("连接池热载切换：[禁用长连接池] (NullPool)")
                engine_kwargs["poolclass"] = NullPool
            else:
                L.info("连接池热载切换：[启用高并发长连接池] (QueuePool)")
                engine_kwargs["pool_size"] = 100
                engine_kwargs["max_overflow"] = 200
                engine_kwargs["pool_timeout"] = 30

            _engine = create_async_engine(
                _current_db_url,
                **engine_kwargs,
                **settings.ENGINE_ARGS,
            )

    return _engine


async def get_async_session(engine: AsyncEngine = Depends(get_async_engine)) -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSession(engine, autoflush=True, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()


if __name__ == "__main__":
    from contextlib import asynccontextmanager

    from sqlalchemy import text

    async def test_engine():
        engine = await get_async_engine()
        async with engine.connect() as conn:
            res = await conn.execute(text("select 'hello world';"))
        print(res.all())

    async def test_session():
        engine = await get_async_engine()
        async with asynccontextmanager(get_async_session)(engine) as session:
            res = await session.execute(text("select 'hello fastapi';"))
            print(res.all())

    import asyncio

    async def main():
        await asyncio.gather(test_engine(), test_session())

    asyncio.run(main())
