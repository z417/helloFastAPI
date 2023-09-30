#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 16:32
 * @LastEditors  : Yuri
 * @LastEditTime : 25/Jun/2023 05:56
 * @FilePath     : /helloFastAPI/backend/src/Auth/models.py
 * @Description  : Auth module db models
"""
from json import dumps
from re import match
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    DATE,
    SMALLINT,
    TEXT,
    VARCHAR,
    TypeDecorator,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, validates

from src.Auth.config import PWD_CONTEXT
from src.common import CommonAttr


class Base(AsyncAttrs, DeclarativeBase):
    pass


class PasswordT(TypeDecorator):
    """
    Allows storing and retrieving password hashes using passlib.context.CryptContext.
    """

    impl = CHAR(60)

    def process_bind_param(self, value: str, dialect):
        """
        return its hash.
        """
        return PWD_CONTEXT.hash(value)

    def process_result_value(self, value, dialect):
        return value


class User(Base, CommonAttr):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", "is_deleted", name="emailxDel"),)

    uid: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[VARCHAR] = mapped_column(
        VARCHAR(50),
        index=True,
        nullable=False,
    )

    @validates("email")
    def validate_email(self, key, addr):
        # only support lowercase
        if not match(r"^[a-z0-9]+([_\.][a-z0-9]+)*@([a-z0-9\-]+\.)+[a-z]{2,7}$", addr):
            raise ValueError("failed on email validation")
        return addr

    password: Mapped[CHAR] = mapped_column(
        "passwd",
        PasswordT,
    )

    def verify_passwd(self, passwd) -> bool:
        return PWD_CONTEXT.verify(passwd, self.password)

    admin: Mapped[SMALLINT] = mapped_column(
        SMALLINT,
        default=0,  # common user
        comment="0 common user,1 administrator, 2 guest",
    )
    first_name: Mapped[VARCHAR] = mapped_column(VARCHAR(50))
    last_name: Mapped[VARCHAR] = mapped_column(VARCHAR(50))
    gender: Mapped[SMALLINT] = mapped_column(
        SMALLINT,
        default=2,  # unknow
        comment="0 female,1 male, 2 unknow",
    )
    birthday: Mapped[Optional[DATE]] = mapped_column(DATE, comment="user's birthday", nullable=True)
    user_status: Mapped[SMALLINT] = mapped_column(SMALLINT, default=0, comment="0 normal,1 abnormal, 2 locked")
    avatar: Mapped[Optional[TEXT]] = mapped_column(
        TEXT,
        nullable=True,
        comment="user avatar, base64 encode",
    )

    @hybrid_property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return dumps({"email": self.email, "full_name": self.full_name, "user_status": self.user_status})


if __name__ == "__main__":
    """Usage example"""
    import asyncio
    from contextlib import asynccontextmanager
    from typing import AsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncEngine
    from sqlalchemy.ext.asyncio.session import AsyncSession

    async def create_engine() -> AsyncEngine:
        from sqlalchemy.ext.asyncio import create_async_engine

        from src.settings import settings

        return create_async_engine(
            str(settings.DB_URL),
            **settings.ENGINE_ARGS,
        )

    async def create_table(engine: AsyncEngine, drop_first=False) -> None:
        async with engine.connect() as conn:
            if drop_first:
                await conn.run_sync(User.metadata.drop_all, checkfirst=True)
            await conn.run_sync(User.metadata.create_all, checkfirst=True)

    @asynccontextmanager
    async def create_session(engine: AsyncEngine) -> AsyncContextManager[AsyncSession]:
        s = AsyncSession(engine)
        try:
            yield s
        finally:
            await s.close()

    async def insert_demo(session: AsyncSession) -> None:
        admin_info = {
            "email": "admin@z417.top",
            "password": "admin12345",
            "admin": 1,
            "first_name": "admin",
            "last_name": "admin",
        }
        admin = User(**admin_info)
        common_user_info = {
            "email": "common@hzn.com",
            "password": "common12345",
            "first_name": "common",
            "last_name": "common",
        }
        common_user = User(**common_user_info)
        session.add_all([admin, common_user])
        await session.commit()

    async def select_demo(session: AsyncSession) -> User:
        from sqlalchemy import select

        stmt = select(User).where(User.first_name == "common", User.is_deleted == 0)
        pick_user: User = (await session.execute(stmt)).scalar_one_or_none()
        print(pick_user)
        print(await pick_user.awaitable_attrs.password)
        return pick_user

    async def update_demo(session: AsyncSession, u: User) -> None:
        from sqlalchemy import update

        # update 1
        u.password = "common54321"
        await session.flush()
        await session.refresh(u)
        print(u.verify_passwd("common12345"))
        print(u.verify_passwd("common54321"))
        # update 2
        stmt = update(User).where(User.first_name == "common").values(gender=1).execution_options(synchronize_session="auto")
        up_user = await session.execute(stmt)
        print(up_user.rowcount)
        await session.commit()

    async def test_models():
        engine = await create_engine()
        await create_table(engine, True)
        async with create_session(engine) as session:
            await insert_demo(session)
            pick_user = await select_demo(session)
            await update_demo(session, pick_user)
        await engine.dispose()

    asyncio.run(test_models())
