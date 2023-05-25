#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 27/Apr/2023 13:49
 * @LastEditors  : Yuri
 * @LastEditTime : 06/May/2023 09:25
 * @FilePath     : /teach/helloFastAPI/backend/src/Auth/router.py
 * @Description  : Auth endpoints
'''
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from src.Auth.config import ACCESS_TOKEN_EXPIRE_MINUTES
from src.Auth.dependencies import (authenticate_user_in_db, create_refresh_token,
                                   create_token, renew_token_via_refresh, get_user_from_db)
from src.Auth.schemas import (
    TokenResponseSchema, SignupSchema, SignupResponseSchema, RenewTokenResponseSchema)
from src.Auth.models import Users

router = APIRouter(
    prefix='/api/auth',  # has reletionship with config.TOKEN_URL
    tags=['Auth'],
)


@router.post(
    '/token',
    response_model=TokenResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def OAuth2_login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user_in_db(form_data.username, form_data.password)
    access_token, data = await create_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = await create_refresh_token(data)
    return TokenResponseSchema(access_token=access_token, refresh_token=refresh_token)


@router.post(
    '/signup',
    status_code=status.HTTP_201_CREATED,
    response_model=SignupResponseSchema,
)
async def signup(req: SignupSchema):
    res = await get_user_from_db(email__icontains=req.email)
    if res:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The E-Mail is already used"
        )
    else:
        new_user = Users(**req.dict())
        try:
            await new_user.save()
            await new_user.upsert(created_by=new_user.uid, updated_by=new_user.uid)
            return SignupResponseSchema(
                uid=new_user.uid,
                full_name=new_user.full_name,
                email=new_user.email,
                frequency_max=new_user.frequency_max
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e
            )


@router.get(
    '/token',
    status_code=status.HTTP_205_RESET_CONTENT,
    response_model=RenewTokenResponseSchema
)
async def renew_token(
    refresh_token: str = Query(
        title='Refresh token',
        description='The token that returned after signin',
        alias='refreshToken'
    )
):
    new_token = await renew_token_via_refresh(refresh_token)
    return RenewTokenResponseSchema(access_token=new_token)
