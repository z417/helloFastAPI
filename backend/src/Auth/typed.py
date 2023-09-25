#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 27/Apr/2023 14:50
 * @LastEditors  : Yuri
 * @LastEditTime : 20/Jun/2023 11:14
 * @FilePath     : /helloFastAPI/backend/src/Auth/typed.py
 * @Description  : define types
"""
from pydantic import constr

_NameType = constr(
    pattern=r"^[A-Za-z0-9-_]+$",
    to_lower=False,
    strip_whitespace=True,
    min_length=1,
    max_length=16,
)

_EmailStrType = constr(
    pattern=r"^[A-Za-z0-9]+([_\.][A-Za-z0-9]+)*@([A-Za-z0-9\-]+\.)+[A-Za-z]{2,7}$",
    to_lower=True,
    strip_whitespace=True,
    max_length=50,
)

__all__ = ["_NameType", "_EmailStrType"]
