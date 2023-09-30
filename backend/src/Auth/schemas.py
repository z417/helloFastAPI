#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 27/Apr/2023 06:12
 * @LastEditors  : Yuri
 * @LastEditTime : 25/Aug/2023 16:33
 * @FilePath     : /helloFastAPI/backend/src/Auth/schemas.py
 * @Description  : pydantic models for request and response
"""
from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from src.Auth.typed import _NameType
from src.common import BaseModel


class TokenResponseSchema(BaseModel):
    """token response class"""

    access_token: str
    token_type: str = "Bearer"
    refresh_token: str


class RenewTokenResponseSchema(BaseModel):
    access_token: str


class SignupSchema(BaseModel):
    email: EmailStr = Field(description="Email address and unique")
    # TODO: password encrypt
    password: str = Field(
        examples=["aB_12345"],
        # pattern="(?=.*[0-9])(?=.*[a-zA-Z])(?=.*[^a-zA-Z0-9]).{8,32}",  # issue in V2.4.1 https://github.com/pydantic/pydantic/issues/7058
        description="""
            Min 8 - Max 32 character length.
            At least one upper case letter.
            At least one lower case letter.
            At least one digit.
            At least one special character.
        """,
    )
    first_name: _NameType = Field(examples=["Yuri"])  # type: ignore
    last_name: _NameType = Field(examples=["Zhong"])  # type: ignore
    birthday: Optional[date]
    avatar: Optional[str] = Field(
        description="base64 image encode",
        examples=["data:image/png;base64,iVBORw0KGgoAAAAN.."],
    )

    @field_validator("avatar")
    @classmethod
    def err_msg(cls, v):
        if not v:
            raise ValueError("{'detail': 'error message'}")
        return v

    class Config:
        json_encoders = {EmailStr: lambda em: em.lower()}


class SignupResponseSchema(BaseModel):
    uid: UUID
    full_name: str
    email: EmailStr


class ProfileResponseSchema(BaseModel):
    uid: UUID
    email: EmailStr
    full_name: str
    avatar: Optional[str]
    birthday: Optional[date]
