#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 04/Jun/2023 05:58
 * @LastEditors  : Yuri
 * @LastEditTime : 04/Jun/2023 08:42
 * @FilePath     : helloFastAPI/backend/src/middleware.py
 * @Description  : file desc
'''
from gzip import decompress
from typing import Callable, Union
from fastapi.exceptions import RequestValidationError
from fastapi import Request, Response, HTTPException
from fastapi.routing import APIRoute
from src.utils import L


class GzipRequest(Request):
    async def body(self) -> bytes:
        if not hasattr(self, '_body'):
            body = await super().body()
            if 'application/gzip' in self.headers.getlist('Content-Transfer-Encoding'):
                L.debug('client send application/gzip in headers')
                try:
                    body = decompress(body)
                except Exception as e:
                    L.error(e)
            self._body = body
        return self._body


def customAPIRoute(request_handlers: list = []):
    class CustomAPIRoute(APIRoute):
        def get_route_handler(self) -> Callable:
            original_route_handler = super().get_route_handler()

            async def custom_route_handler(r: Request) -> Union[Response]:
                for reqh in request_handlers:
                    if reqh == GzipRequest:
                        r = GzipRequest(r.scope, r.receive)
                    break
                else:
                    L.info('no custom request handler of route')

                resp: Response = await original_route_handler(r)
                return resp

            return custom_route_handler

    return CustomAPIRoute



if __name__ == '__main__':
    customAPIRoute([GzipRequest])
    print(GzipRequest == GzipRequest)
