#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 14:08
 * @LastEditors  : Yuri
 * @LastEditTime : 05/Jun/2023 08:27
 * @FilePath     : /teach/helloFastAPI/backend/src/models.py
 * @Description  : global models
'''
from datetime import datetime
from typing import Generic, Optional, TypeVar

from ormar import UUID, DateTime, ModelMeta
from pydantic import UUID4
from pydantic import BaseModel as PydanticBaseModel
from pydantic.generics import GenericModel
from sqlalchemy import func
from src.tools.dbs import database, metadata


def camel(s: str) -> str:
    words = s.split('_')
    return f'{words[0]}{"".join(word.capitalize() for word in words[1:])}'


class BaseMeta(ModelMeta):
    metadata = metadata
    database = database


class AuditMixin:
    created_by: UUID4 = UUID(comment='creator uid')
    updated_by: UUID4 = UUID(comment='updator uid')


class DateFieldsMixins:
    created_at: datetime = DateTime(
        index=True,
        server_default=func.now()
    )
    updated_at: datetime = DateTime(
        server_default=func.now(),
        server_onupdate=func.now(),  # TODO: not work!!
    )


class BaseModel(PydanticBaseModel):
    class Config:
        # alias_generator = camel  # disabled by swagger Authorize not work
        orm_mode = True


DataT = TypeVar('DataT')


class ResponseModel(GenericModel, Generic[DataT]):
    data: Optional[DataT]
    status: int = 1
    errCode: int = 200


if __name__ == '__main__':
    class TestModel(BaseModel):
        error_code: int = 200
        error_msg: str = 'success'

    print(TestModel(**{'errorCode': 301, 'errorMsg': 'balabala'}).json())
