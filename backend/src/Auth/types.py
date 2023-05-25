#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 27/Apr/2023 14:50
 * @LastEditors  : Yuri
 * @LastEditTime : 05/May/2023 07:56
 * @FilePath     : /teach/helloFastAPI/backend/src/Auth/types.py
 * @Description  : define types
'''
from pydantic import constr

_NameType = constr(
    regex="^[A-Za-z0-9-_]+$",
    to_lower=False,
    strip_whitespace=True,
    min_length=1,
    max_length=16
)
