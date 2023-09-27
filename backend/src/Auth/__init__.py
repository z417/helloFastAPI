#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 27/Apr/2023 07:39
 * @LastEditors  : Yuri
 * @LastEditTime : 20/Jun/2023 12:39
 * @FilePath     : /helloFastAPI/backend/src/Auth/__init__.py
 * @Description  : file desc
"""
__version__ = "0.0.1"

from src.Auth.models import User
from src.Auth.router import router as auth_router
from src.Auth.typed import _EmailStrType, _NameType

__all__ = ["auth_router", "User", "_EmailStrType", "_NameType"]
