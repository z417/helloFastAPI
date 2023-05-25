#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 16:32
 * @LastEditors  : Yuri
 * @LastEditTime : 05/May/2023 10:57
 * @FilePath     : /teach/helloFastAPI/backend/src/Auth/models.py
 * @Description  : db models
'''
from typing import ForwardRef, Optional
from ormar import (UUID, Date, EncryptBackends, ForeignKey, Model, SmallInteger, String,
                   Text, UniqueColumns, property_field)
from pydantic import UUID4, EmailStr
from src.Auth.types import _NameType
from src.models import BaseMeta, DateFieldsMixins
from uuid import uuid4


# create the forwardref to model "Users"
UsersRef = ForwardRef("Users")


class Users(Model, DateFieldsMixins):
    class Meta(BaseMeta):
        tablename = "users"
        constraints = [UniqueColumns('email', 'is_deleted', name='emailxDel')]
    uid: UUID4 = UUID(
        primary_key=True,
        default_factory=uuid4,
        uuid_format="hex"
    )
    email: EmailStr = String(
        index=True,
        max_length=50,
        nullable=False,
        description='Email address',
        example='user@example.com',
    )
    password: str = String(
        max_length=32,
        min_length=8,
        example='aB_1234567',
        encrypt_secret='helloFastAPI',
        encrypt_backend=EncryptBackends.FERNET,
        name='passwd',
    )
    admin: int = SmallInteger(
        default=0,  # common user
        minimum=0,  # 1 means administrator
        maximum=2,  # guest
        comment='0 common user,1 administrator, 2 guest'
    )
    first_name: _NameType = String(max_length=50)
    last_name: _NameType = String(max_length=50)
    birthday: Optional[Date] = Date(comment="user's birthday", nullable=True)
    user_status: int = SmallInteger(
        default=0,  # normal
        minimum=0,  # 1 means abnormal
        maximum=2,  # 2 locked
        comment='0 normal,1 abnormal, 2 locked'
    )
    avatar: Optional[Text] = Text(
        nullable=True,
        description='base64 image encode',
        example='data:image/png;base64,iVBORw0KGgoAAAAN..',
        comment='user avatar, base64 encode',
    )
    created_by: Optional[UsersRef] = ForeignKey(
        UsersRef,
        related_name='fk_self_uidxCre',
    )
    updated_by: Optional[UsersRef] = ForeignKey(
        UsersRef,
        related_name='fk_self_uidxUpd',
    )
    is_deleted: int = SmallInteger(
        default=0,  # "Not deleted" of logical
        minimum=0,
        maximum=1,  # "Deleted" of logical
        comment='0 "Not deleted", 1 "Deleted"'
    )
    frequency_max: int = 600  # pydantic only fields, will not be stored in db

    @property_field
    def full_name(self) -> str:
        '''
        1. only available in the response from fastapi and dict() and json() methods
        2. cannot pass a value for this field in the request
        '''
        return f'{self.first_name} {self.last_name}'


Users.update_forward_refs()


if __name__ == '__main__':
    # print(Users.Meta.model_fields)
    print(Users.Meta.table.columns.keys())

    from asyncio import run, sleep
    from sqlalchemy.ext.asyncio import create_async_engine

    async def create_table():
        engine = create_async_engine("sqlite+aiosqlite:///data/db.sqlite")
        async with engine.begin() as conn:
            await conn.run_sync(Users.Meta.table.drop, checkfirst=True)
            await conn.run_sync(Users.Meta.table.create, checkfirst=True)

    async def insert_data(user: Users):
        print(user.dict())
        await user.save()

    async def upsert_data(user: Users):
        await sleep(5)
        await user.upsert(first_name=f'{user.first_name}+update', updated_by=user.uid)
        print(user.json())

    admin_uid = uuid4().hex
    admin_info = {
        "uid": admin_uid,
        "email": "admin@z417.top",
        "password": "admin12345",
        "admin": 1,
        "first_name": "ADMIN",
        "last_name": "adMin",
        "birthday": "1990-02-04",
        "user_status": 0,
        "avatar": "about:blank",
        # "created_at": "1605854050000",
        # "updated_at": "1605854050000",
        "created_by": admin_uid,
        "updated_by": admin_uid,
        "is_deleted": 0
    }
    admin = Users(**admin_info)
    run(create_table())
    run(insert_data(admin))
    run(upsert_data(admin))

    tester_info = {
        "email": "tester@z417.top",
        "password": "admin12345",
        "first_name": "tester",
        "last_name": "test",
        # "birthday": "1990-01-09",
        # "avatar": "about:blank",
    }
    tester = Users(**tester_info, created_by=admin.uid,
                   updated_by=admin.uid)
    run(insert_data(tester))
    run(upsert_data(tester))
