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
from datetime import date, datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Extra
from pydantic.generics import GenericModel
from sqlalchemy import TIMESTAMP, SmallInteger, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def camel(snake_case: str) -> str:
    words = snake_case.split("_")
    return f'{words[0]}{"".join(word.capitalize() for word in words[1:])}'


class Base(AsyncAttrs, DeclarativeBase):
    type_annotation_map = {
        datetime: TIMESTAMP(timezone=True),
        date: TIMESTAMP(timezone=True),
    }
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),  # pylint: disable=E1102
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),  # pylint: disable=E1102
        onupdate=func.now(),  # pylint: disable=E1102
    )
    is_deleted: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,  # "Not deleted" of logical
        comment='0 "Not deleted", 1 "Deleted"',
    )


class BaseModel(PydanticBaseModel):
    class Config:
        # alias_generator = camel  # disabled by swagger Authorize not work
        # allow_population_by_field_name = True
        orm_mode = True
        extra = Extra.forbid


DataT = TypeVar("DataT")


class ResponseModel(GenericModel, Generic[DataT]):
    data: Optional[DataT]
    status: int = 1
    errCode: int = 200


if __name__ == "__main__":

    class TestModel(BaseModel):
        error_code: int = 200
        error_msg: str = "success"

    print(TestModel(**{"error_code": 301, "error_msg": "balabala"}).json())
