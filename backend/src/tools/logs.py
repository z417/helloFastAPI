#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
 * @Author: z417
 * @Date: 2020-11-16 11:12:43
 * @LastEditors: z417
 * @LastEditTime: 2020-11-16 11:12:50
 * @FilePath: ./helloFastAPI/backend/utils/logs.py
 * @Description: logging mudule
'''
from functools import wraps
from logging import Logger, config, getLogger
from pathlib import Path


def singleton(cls):
    """
    单例模式装饰器
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


@singleton
class Log():
    def __init__(self, name='root'):
        """
        :param name:
        """
        # Save log to a new file at 12am everyday, no more than 6 files. utf-8
        self.__conf_log__ = Path().joinpath('conf', 'log.ini')
        try:
            config.fileConfig(self.__conf_log__)
        except FileNotFoundError as e:
            Path(e.filename).parent.mkdir()
            config.fileConfig(self.__conf_log__)
        self.__logger__ = getLogger(name)

    @property
    def get_logger(self) -> Logger:
        return self.__logger__


# Create a global logger object, named L
L = Log().get_logger

if __name__ == "__main__":
    L.info('this is info msg')
    L.debug('this is debug msg')
    L.error('this is error msg')
    L.warning('this is warning msg')
