#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 28/Apr/2023 10:14
 * @LastEditors  : Yuri
 * @LastEditTime : 04/May/2023 10:40
 * @FilePath     : /teach/helloFastAPI/backend/src/FileCodeBox/schemas.py
 * @Description  : file desc
'''
from pydantic import EmailStr, Field, UUID4
from src.models import BaseModel


class ShareDataSchema(BaseModel):
    '''token response class'''
    text: str
    size: int = 0
    exp_style: str
    exp_value: int
    type: str
    name: str
    key: str
