#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 14:08
 * @LastEditors  : Yuri
 * @LastEditTime : 21/Jun/2023 10:00
 * @FilePath     : /helloFastAPI/backend/src/common/models.py
 * @Description  : common models
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import SMALLINT, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class CommonAttr:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @declared_attr
    def created_by(cls) -> Mapped[Optional[UUID]]:
        return mapped_column(
            ForeignKey(
                "users.uid",
                name=f"fk_{cls.__tablename__}.created_by_on_users.uid",
            ),
            comment="creator",
        )

    @declared_attr
    def updated_by(cls) -> Mapped[Optional[UUID]]:
        return mapped_column(
            ForeignKey(
                "users.uid",
                name=f"fk_{cls.__tablename__}.updated_by_on_users.uid",
            ),
            comment="updator",
        )

    @declared_attr
    def created_at(cls) -> Mapped[TIMESTAMP]:
        return mapped_column(
            TIMESTAMP(timezone=True),
            server_default=func.now(),
        )

    @declared_attr
    def updated_at(cls) -> Mapped[TIMESTAMP]:
        return mapped_column(
            TIMESTAMP(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        )

    @declared_attr
    def is_deleted(cls) -> Mapped[SMALLINT]:
        return mapped_column(
            SMALLINT,
            default=0,  # "Not deleted" of logical
            comment='0 "Not deleted", 1 "Deleted"',
        )


if __name__ == "__main__":
    """Usage example"""
    from sqlalchemy.ext.asyncio import AsyncAttrs
    from sqlalchemy.orm import DeclarativeBase

    class Base(AsyncAttrs, DeclarativeBase):
        pass

    class User(Base, CommonAttr):
        __tablename__ = "users"
        uid: Mapped[UUID] = mapped_column(
            primary_key=True,
        )

    from sqlalchemy.schema import CreateTable

    print(CreateTable(User.__table__))
