from configparser import RawConfigParser
from os import PathLike, environ
from subprocess import PIPE, Popen
from typing import Union


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
    return output.decode("utf-8").strip()


async def load_ini(file: Union[str, PathLike]) -> RawConfigParser:
    """load .ini file"""
    _ini = RawConfigParser()
    _ini.read(file, encoding="utf-8")
    return _ini
