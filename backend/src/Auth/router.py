#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 27/Apr/2023 13:49
 * @LastEditors  : Yuri
 * @LastEditTime : 05/Jun/2023 08:31
 * @FilePath     : /teach/helloFastAPI/backend/src/Auth/router.py
 * @Description  : Auth endpoints
'''
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from src.Auth.config import ACCESS_TOKEN_EXPIRE_MINUTES
from src.Auth.dependencies import (
    authenticate_user_in_db,
    create_refresh_token,
    create_token,
    get_current_user,
    get_user_from_db,
    renew_token_via_refresh,
)
from src.Auth.models import Users
from src.Auth.schemas import (
    ProfileResponseSchema,
    RenewTokenResponseSchema,
    SignupResponseSchema,
    SignupSchema,
    TokenResponseSchema,
)
from src.middleware import GzipRequest, ValidationErrorLoggingRoute, customAPIRoute
from src.models import ResponseModel

# from src.middleware2 import GzipRoute, ValidationErrorLoggingRoute

router = APIRouter(
    prefix='/api/auth',  # has reletionship with config.TOKEN_URL
    tags=['Auth'],
    route_class=customAPIRoute(
        [GzipRequest],
        [ValidationErrorLoggingRoute]
    ),
    # route_class=GzipRoute,
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
    response_model=ResponseModel[SignupResponseSchema],
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
            data = SignupResponseSchema(
                uid=new_user.uid,
                full_name=new_user.full_name,
                email=new_user.email,
                frequency_max=new_user.frequency_max
            )
            return ResponseModel(data=data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e
            )


@router.get(
    '/token',
    status_code=status.HTTP_205_RESET_CONTENT,
    response_model=ResponseModel[RenewTokenResponseSchema],
    # openapi_extra={
    #     "responses": {
    #         "400": {
    #             "description": "Bad Request",
    #             "content": {
    #                 "application/json": {
    #                     "schema": {
    #                         "$ref": "#/components/schemas/TokenResponseSchema"
    #                     }
    #                 }
    #             }
    #         }
    #     }
    # },
)
async def renew_token(
    refresh_token: str = Query(
        title='Refresh token',
        description='The token that returned after login',
        alias='refreshToken'
    )
):
    new_token = await renew_token_via_refresh(refresh_token)
    return ResponseModel(data=RenewTokenResponseSchema(access_token=new_token))


@router.get(
    '/profile',
    status_code=status.HTTP_200_OK,
    response_model=ResponseModel[ProfileResponseSchema],
)
async def get_profile(current_user=Depends(get_current_user)):
    data = ProfileResponseSchema(
        uid=current_user.uid,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar=current_user.avatar,
        birthday=current_user.birthday,
    )
    return ResponseModel(data=data)
