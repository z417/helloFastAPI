#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 14:06
 * @LastEditors  : Yuri
 * @LastEditTime : 26/Aug/2023 07:28
 * @FilePath     : /helloFastAPI/backend/src/tools/__init__.py
 * @Description  : function tools
"""
from configparser import RawConfigParser
from functools import wraps
from hashlib import md5
from os import PathLike, environ
from subprocess import PIPE, Popen
from typing import Union

from .logs import L


async def get_md5(key: str) -> str:
    """return a md5 string"""
    return md5(key.encode(encoding="utf-8")).hexdigest()


async def set_env(**kw):
    """set runtime environments"""
    for k, v in kw.items():
        environ[k] = v


async def get_env(k: str) -> Union[str, KeyError]:
    """get envrionment"""
    try:
        return environ[k]
    except KeyError as e:
        raise e


async def shell(cmd: str) -> str:
    """execute commands"""
    output, _ = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).communicate()
    return output.decode("utf-8")


async def load_ini(file: Union[str, PathLike]) -> RawConfigParser:
    """load .ini file"""
    _ini = RawConfigParser()
    _ini.read(file, encoding="utf-8")
    return _ini


def singleton(cls):
    """
    singleton pattern decorator
    :param cls: the object you want to set singleton
    :return:
    """
    instances = {}

    @wraps(cls)
    def _wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return _wrapper


class Chain:
    def __init__(self, path=""):
        self._path = path

    def __getattr__(self, path):
        if path == "users":
            return lambda name: Chain(f"{self._path}/{name}")
        return Chain(f"{self._path}/{path}")

    def __str__(self):
        return self._path

    __repr__ = __str__


__all__ = [
    "L",
    "get_md5",
    "set_env",
    "get_env",
    "shell",
    "load_ini",
    "Chain",
    "singleton",
]

if __name__ == "__main__":
    import asyncio

    r = asyncio.run(shell("pwd"))
    L.info(r)

    L.info(Chain().api.users("nick").profile)  # type: ignore
