#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 03/May/2023 07:42
 * @LastEditors  : Yuri
 * @LastEditTime : 05/May/2023 06:04
 * @FilePath     : /teach/helloFastAPI/backend/src/tools/dbs.py
 * @Description  : file desc
'''
from databases import Database
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from typing import AsyncGenerator

# TODO: more kinds database adaptor, mysql, postgresql
DATABASE_URL = "sqlite+aiosqlite:///data/db.sqlite"
database = Database(DATABASE_URL)
metadata = MetaData()

engine = create_async_engine(
    url=DATABASE_URL,
    # pool_size=10,
    # max_overflow=-1,
    # pool_recycle=1200,
    echo=True,  # should False in prod env
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s

if __name__ == '__main__':
    '''
    create the database
    note that this is not required if you connect to existing database
    '''
    # just to be sure we clear the db before
    async def test_engine():
        async with engine.begin() as conn:
            await conn.run_sync(metadata.drop_all)
            await conn.run_sync(metadata.create_all)
            r = await conn.exec_driver_sql('select date()')
            print(list(r))

    from asyncio import run
    run(test_engine())
