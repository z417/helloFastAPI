from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_serializer, field_validator

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
    password: str = Field(
        min_length=1,
        max_length=32,
        examples=["aB_12345"],
        description="""
            Min 8 - Max 32 character length.
            At least one upper case letter.
            At least one lower case letter.
            At least one digit.
            At least one special character.
        """,
    )
    first_name: _NameType = Field(examples=["Yuri"])
    last_name: _NameType = Field(examples=["Zhong"])
    gender: Optional[int] = Field(default=2, description="0 female, 1 male, 2 unknow")
    birthday: Optional[date] = None
    avatar: Optional[str] = Field(
        default=None,
        description="base64 image encode",
        examples=["data:image/png;base64,iVBORw0KGgoAAA.."],
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v) -> str:
        from src.settings import settings

        if settings.AUTH_STRONG_PASSWORD_CHECK:
            if len(v) < 8:
                raise ValueError("Password must be at least 8 characters long")
            if not any(c.isupper() for c in v):
                raise ValueError("Password must contain at least one uppercase letter")
            if not any(c.islower() for c in v):
                raise ValueError("Password must contain at least one lowercase letter")
            if not any(c.isdigit() for c in v):
                raise ValueError("Password must contain at least one digit")
            if not any(not c.isalnum() for c in v):
                raise ValueError("Password must contain at least one special character")
        return v

    @field_serializer("email")
    def serialize_email(self, email: EmailStr) -> str:
        return email.lower()


class SignupResponseSchema(BaseModel):
    uid: UUID
    full_name: str
    email: EmailStr


class ProfileResponseSchema(BaseModel):
    uid: UUID
    email: EmailStr
    full_name: str
    avatar: Optional[str] = None
    birthday: Optional[date] = None
    gender: int
