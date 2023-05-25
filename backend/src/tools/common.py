#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 09/Apr/2023 13:22
 * @LastEditors  : Yuri
 * @LastEditTime : 05/May/2023 05:55
 * @FilePath     : /teach/helloFastAPI/backend/src/tools/common.py
 * @Description  : commom functions
'''
from configparser import RawConfigParser
from hashlib import md5
from os import PathLike, environ
from subprocess import PIPE, Popen
from typing import AnyStr, Dict, Union


async def getMD5(key: str) -> str:
    return md5(key.encode(encoding='utf-8')).hexdigest()


async def setEnv(**kw: Dict[str, str]):
    for k, v in kw.items():
        environ[k] = v


async def getEnv(k: str) -> Union[str, KeyError]:
    try:
        return environ[k]
    except KeyError as e:
        raise e


async def shell(cmd: str) -> AnyStr:
    output, _ = Popen(
        cmd,
        shell=True,
        stdout=PIPE,
        stderr=PIPE).communicate()
    o = output.decode('utf-8')
    return o


async def loadConfig(file: Union[str, PathLike]) -> RawConfigParser:
    _ini = RawConfigParser()
    _ini.read(file, encoding='utf-8')
    return _ini


class Chain:
    def __init__(self, path=''):
        self._path = path

    def __getattr__(self, path):
        if path == 'users':
            return lambda name: Chain(f'{self._path}/{name}')
        return Chain(f'{self._path}/{path}')

    def __str__(self):
        return self._path

    __repr__ = __str__


if __name__ == '__main__':
    import asyncio

    from logs import L
    r = asyncio.run(shell("pwd"))
    L.info(r)
    ini = asyncio.run(loadConfig('./conf/log.ini'))
    for i in ini.sections():
        L.info(i)

    L.info(Chain().api.users('nick').profile)
