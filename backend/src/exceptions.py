#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 14:32
 * @LastEditors  : Yuri
 * @LastEditTime : 04/May/2023 10:19
 * @FilePath     : /teach/helloFastAPI/backend/src/exceptions.py
 * @Description  : global exceptions
'''
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette import status


class APIException(Exception):
    def __init__(self, status_code=None, error_id=None, message=None):
        '''
        :param status_code:
        :param error_id:
        :param message:
        '''
        self.status_code = status_code
        self.message = message
        self.error_id = error_id

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f'{class_name}(status_code={self.status_code!r}, error_info={self.message!r})'


async def http_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    '''
    replace except_handler of fastapi
    '''
    return JSONResponse(
        {
            "error_info": exc.message,
            "error_type": exc.error_id
        },
        status_code=exc.status_code,
        headers={"Content-Type": "application/json"},
    )


class BadRequestException(APIException):
    def __init__(self, message):
        APIException.__init__(
            self,
            status.HTTP_400_BAD_REQUEST,
            error_id="error_bad_param",
            message=message
        )


class ConflictException(APIException):
    def __init__(self, message=None):
        APIException.__init__(
            self,
            status.HTTP_409_CONFLICT,
            error_id="error_already_exists",
            message=message
        )


class UnAuthenticatedException(APIException):
    def __init__(self, message=None):
        APIException.__init__(
            self,
            status.HTTP_401_UNAUTHORIZED,
            error_id="error_unauthenticated",
            message=message
        )


class ForbiddenException(APIException):
    def __init__(self, message=None):
        APIException.__init__(
            self,
            status.HTTP_403_FORBIDDEN,
            error_id="error_permission",
            message=message
        )


class NotFoundException(APIException):
    def __init__(self, message=None):
        APIException.__init__(
            self,
            status.HTTP_404_NOT_FOUND,
            error_id="error_not_found",
            message=message
        )


class InternalServerError(APIException):
    def __init__(self, message=None):
        APIException.__init__(
            self,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_id="Internal Server Error",
            message=message
        )
