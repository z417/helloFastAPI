#!/usr/bin/env python3
# coding=UTF-8
"""
 * @Author: z417
 * @Date: 2020-11-16 11:12:43
 * @LastEditors: z417
 * @LastEditTime: 2020-11-16 11:12:50
 * @FilePath: /helloFastAPI/backend/src/tools/logs.py
 * @Description: logging module
"""
from logging import Logger, config, getLogger
from typing import Dict, Final

from src.settings import settings


class Log:
    """Logger util"""

    __app_logging_config: Final[Dict] = {
        # https://docs.python.org/3/library/logging.config.html
        "version": 1,  # The only valid value at present is 1
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                # "()": "uvicorn.logging.AccessFormatter",  # ()means user-defined instantiation is wanted
                "format": "[%(levelname)s %(asctime)s.%(msecs)03d %(module)s.%(funcName)s(%(lineno)d)]: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "style": "%",
                # "validate": "",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                # "level": "",
                "formatter": "default",
                # "filters": "",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": "default",
                "filename": settings.APP_RUN_LOG,
                "when": "W3",  # Save log to a new file at 12am on Thursday
                "interval": 1,  # everyweek
                "backupCount": settings.APP_LOG_BACKUP_COUNT,
                "encoding": "utf-8",
            },
        },
        # "root": {
        #     "level": "INFO",
        #     "handlers": ["console"],
        # },
        "loggers": {
            settings.APP_NAME: {
                "level": settings.APP_LOG_LEVEL.upper(),  # DEBUG > INFO > WARNING > ERROR > CRITICAL
                "handlers": ["console", "file"],
                "propagate": 0,  # propagate always set to 0
            },
        },
    }

    def __init__(self, name="root"):
        """
        :param name: the logger
        """
        result = "Log configuration succeeds"
        self.name = name
        try:
            self.__config()
        except ValueError as e:
            if isinstance(e.__cause__, FileNotFoundError):
                try:
                    self.__config(False, e.__cause__.filename)
                except (ValueError, TypeError, AttributeError, ImportError) as m_e:
                    result = f"{type(m_e)}: {m_e}"
        finally:
            print(f"-----{result}-----")

    def __config(self, file_found=True, filename=""):
        if not file_found:
            from pathlib import Path

            Path(filename).parent.mkdir()
            print(f"+++++{Path(filename).parent} was maked+++++")
        config.dictConfig(self.__app_logging_config)
        self.__logger__ = getLogger(self.name)

    @property
    def get_logger(self) -> Logger:
        """get a logger"""
        return self.__logger__


L = Log(settings.APP_NAME).get_logger

if __name__ == "__main__":
    L.info("this is info msg")
    L.debug("this is debug msg")
    L.error("this is error msg")
    L.warning("this is warning msg")
    print(L.handlers)
    print(L.name)
