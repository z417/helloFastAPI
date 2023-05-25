#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 27/Apr/2023 06:12
 * @LastEditors  : Yuri
 * @LastEditTime : 25/May/2023 06:04
 * @FilePath     : /teach/helloFastAPI/backend/src/Auth/schemas.py
 * @Description  : pydantic models for request and response
'''
from pydantic import EmailStr, Field, UUID4
from src.Auth.types import _NameType
from src.models import BaseModel
from typing import Optional
from datetime import date


class TokenResponseSchema(BaseModel):
    '''token response class'''
    access_token: str
    token_type: str = 'bearer'
    refresh_token: str


class RenewTokenResponseSchema(BaseModel):
    access_token: str


class SignupSchema(BaseModel):
    email: EmailStr = Field(description='Email address and unique')
    # TODO: password encrypt
    password: str = Field(example='aB_1234567')
    first_name: _NameType = Field(example='Yuri')
    last_name: _NameType = Field(example='Zhong')
    birthday: Optional[date]
    avatar: Optional[str] = Field(
        description='base64 image encode',
        example='data:image/png;base64,iVBORw0KGgoAAAAN..'
    )

    class Config:
        json_encoders = {
            EmailStr: lambda em: em.lower()
        }
        fields = {
            "password": {
                "regex": r"(?=.*[0-9])(?=.*[a-zA-Z])(?=.*[^a-zA-Z0-9]).{8,32}",
                "description": '''
                    Min 8 - Max 32 character length.
                    At least one upper case letter.
                    At least one lower case letter.
                    At least one digit.
                    At least one special character.
                ''',
            },
        }


class SignupResponseSchema(BaseModel):
    uid: UUID4
    full_name: str
    email: EmailStr
    frequency_max: int


class ProfileResponseSchema(BaseModel):
    uid: UUID4
    email: EmailStr
    full_name: str
    avatar: Optional[str]
    birthday: Optional[date]
