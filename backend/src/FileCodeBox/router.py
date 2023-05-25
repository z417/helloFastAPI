#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 28/Apr/2023 09:00
 * @LastEditors  : Yuri
 * @LastEditTime : 06/May/2023 10:04
 * @FilePath     : /teach/helloFastAPI/backend/src/FileCodeBox/router.py
 * @Description  : FileCodeBox feature
'''
from fastapi import APIRouter, Depends
from pydantic import IPvAnyAddress
from src.Auth.dependencies import get_current_user
from src.FileCodeBox.config import (ERROR_COUNT, ERROR_MINUTE, UPLOAD_COUNT,
                                    UPLOAD_MINUTE)
from src.FileCodeBox.dependencies import IPRATELimit
from src.FileCodeBox.schemas import ShareDataSchema

router = APIRouter(
    prefix='/api/fileCodeBox',
    tags=['File Code Box'],
    # dependencies=[Depends(get_current_user)],
)


error_ip_limit = IPRATELimit(ERROR_COUNT, ERROR_MINUTE)
upload_ip_limit = IPRATELimit(UPLOAD_COUNT, UPLOAD_MINUTE)


@router.post('/share', description='share files')
async def share_file(
    file_model: ShareDataSchema,
    ip: IPvAnyAddress = Depends(error_ip_limit),
    current_user=Depends(get_current_user)
):
    upload_ip_limit.add_ip(ip)
    return 1
