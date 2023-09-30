#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 14:32
 * @LastEditors  : Yuri
 * @LastEditTime : 21/Jun/2023 09:53
 * @FilePath     : /helloFastAPI/backend/src/common/exceptions.py
 * @Description  : global exceptions
"""
from fastapi.utils import is_body_allowed_for_status_code
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class APIException(Exception):
    def __init__(self, status_code=200, error_id=None, message=None, headers=None):
        """
        :param status_code:
        :param error_id:
        :param message:
        :param headers:
        """
        self.status_code = status_code
        self.message = message
        self.error_id = error_id
        self.headers = headers or {}

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code!r}, error_info={self.message!r})"


async def http_exception_handler(request: Request, exc: APIException) -> Response:
    """
    replace except_handler of fastapi
    """
    headers = getattr(exc, "headers", {})
    headers["Content-Type"] = "application/json"
    if not is_body_allowed_for_status_code(exc.status_code):
        return Response(status_code=exc.status_code, headers=headers)
    return JSONResponse(
        {"error_info": exc.message, "error_type": exc.error_id},
        status_code=exc.status_code,
        headers=headers,
    )


class BadRequestException(APIException):
    def __init__(self, message, headers=None):
        APIException.__init__(
            self,
            status.HTTP_400_BAD_REQUEST,
            error_id="error_bad_param",
            message=message,
            headers=headers,
        )


class ConflictException(APIException):
    def __init__(self, message=None, headers=None):
        APIException.__init__(
            self,
            status.HTTP_409_CONFLICT,
            error_id="error_already_exists",
            message=message,
            headers=headers,
        )


class UnAuthenticatedException(APIException):
    def __init__(self, message=None, headers=None):
        APIException.__init__(
            self,
            status.HTTP_401_UNAUTHORIZED,
            error_id="error_unauthenticated",
            message=message,
            headers=headers,
        )


class ForbiddenException(APIException):
    def __init__(self, message=None, headers=None):
        APIException.__init__(
            self,
            status.HTTP_403_FORBIDDEN,
            error_id="error_permission",
            message=message,
            headers=headers,
        )


class NotFoundException(APIException):
    def __init__(self, message=None, headers=None):
        APIException.__init__(
            self,
            status.HTTP_404_NOT_FOUND,
            error_id="error_not_found",
            message=message,
            headers=headers,
        )


class InternalServerError(APIException):
    def __init__(self, message=None, headers=None):
        APIException.__init__(
            self,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_id="Internal Server Error",
            message=message,
            headers=headers,
        )
