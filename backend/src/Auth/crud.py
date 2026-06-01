from typing import Any, Union
from uuid import UUID

from sqlalchemy import Result, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from src.Auth.models import User
from src.utils import L


async def create_table(session: AsyncSession, model):
    L.info(f'Create table "{model.__tablename__}"')
    conn = await session.connection()
    await conn.run_sync(model.metadata.create_all, checkfirst=True)


async def get_admin(session: AsyncSession) -> Result[Any]:
    return await session.execute(select(User.uid).where(User.admin == 1, User.is_deleted == 0, User.user_status == 0).limit(1))


async def get_user_by_pk(session: AsyncSession, pk: UUID) -> Union[User, None]:
    return await session.get(User, pk)


async def get_user_by_email(session: AsyncSession, email: str) -> Result[Any]:
    try:
        return await session.execute(select(User).where(User.is_deleted == 0).where(User.email == email))
    except OperationalError as e:
        if "no such table" in str(e):
            await create_table(session, User)
            return await session.execute(select(User).where(User.is_deleted == 0).where(User.email == email))
        raise e


async def create_user(session: AsyncSession, user: User) -> None:
    session.add(user)
    await session.commit()
