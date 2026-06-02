from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.Auth.config import ACCESS_TOKEN_EXPIRE_MINUTES
from src.Auth.crud import create_user, get_user_by_email
from src.Auth.dependencies import authenticate_user, create_refresh_token, create_token, get_current_user, renew_token_via_refresh
from src.Auth.models import User
from src.Auth.schemas import ProfileResponseSchema, RenewTokenResponseSchema, SignupResponseSchema, SignupSchema, TokenResponseSchema
from src.common import ResponseModel, get_async_session
from src.utils import L


async def start_event() -> None:
    L.info("Auth router start event")


router = APIRouter(
    prefix="/api/auth",  # has reletionship with config.TOKEN_URL
    tags=["Auth"],
    on_startup=[start_event],
    # route_class=customAPIRoute([GzipRequest], [ValidationErrorLoggingRoute]),
    # route_class=GzipRoute,
)


@router.post("/token", response_model=TokenResponseSchema, status_code=status.HTTP_201_CREATED)
async def OAuth2_login(
    user: User = Depends(authenticate_user),
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponseSchema:
    import uuid

    session_id = str(uuid.uuid4())
    user.current_session_id = session_id
    await session.commit()

    access_token, data = await create_token(
        data={"sub": user.email, "session_id": session_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = await create_refresh_token(data)
    return TokenResponseSchema(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseModel[SignupResponseSchema],
)
async def signup(
    req: SignupSchema,
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel:
    res = (await get_user_by_email(session, req.email)).scalar_one_or_none()
    if res:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The E-Mail is already used")
    new_user = User(**(req.model_dump()))
    try:
        await create_user(session, new_user)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e) from e
    data = SignupResponseSchema(
        uid=new_user.uid,
        full_name=new_user.full_name,
        email=new_user.email,
    )
    return ResponseModel(data=data)


@router.get(
    "/token",
    status_code=status.HTTP_201_CREATED,
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
        title="Refresh token",
        description="The token that returned after login",
        alias="refreshToken",
    ),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel:
    new_token = await renew_token_via_refresh(refresh_token, session)
    data = RenewTokenResponseSchema(access_token=new_token)
    return ResponseModel(data=data)


@router.get(
    "/profile",
    status_code=status.HTTP_200_OK,
    response_model=ResponseModel[ProfileResponseSchema],
)
async def get_profile(current_user: User = Depends(get_current_user)) -> ResponseModel:
    data = ProfileResponseSchema(
        uid=current_user.uid,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar=current_user.avatar,
        birthday=current_user.birthday,
        gender=current_user.gender,
    )
    return ResponseModel(data=data)
