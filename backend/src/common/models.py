from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import SMALLINT, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import Mapped, declarative_mixin, declared_attr, mapped_column


@declarative_mixin
class CommonAttr:
    @declared_attr
    @classmethod
    def created_by(cls) -> Mapped[Optional[UUID]]:
        return mapped_column(
            ForeignKey(
                "users.uid",
                name=f"fk_{getattr(cls, '__tablename__', cls.__name__.lower())}_created_by_on_users_uid",
            ),
            comment="creator",
        )

    @declared_attr
    @classmethod
    def updated_by(cls) -> Mapped[Optional[UUID]]:
        return mapped_column(
            ForeignKey(
                "users.uid",
                name=f"fk_{getattr(cls, '__tablename__', cls.__name__.lower())}_updated_by_on_users_uid",
            ),
            comment="updator",
        )

    @declared_attr
    @classmethod
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(
            TIMESTAMP(timezone=True),
            server_default=func.now(),
        )

    @declared_attr
    @classmethod
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(
            TIMESTAMP(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        )

    @declared_attr
    @classmethod
    def is_deleted(cls) -> Mapped[int]:
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

    from typing import cast

    from sqlalchemy.schema import CreateTable, Table

    print(CreateTable(cast(Table, User.__table__)))
