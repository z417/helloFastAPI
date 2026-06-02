import sys

from loguru import logger

from src.settings import settings

# Loguru setup mapping the legacy config
logger.remove()  # Remove the default standard handler
logger.add(sys.stdout, level=settings.APP_LOG_LEVEL.upper())
logger.add(
    settings.APP_RUN_LOG,
    rotation="1 week",
    retention=settings.APP_LOG_BACKUP_COUNT,
    level=settings.APP_LOG_LEVEL.upper(),
    encoding="utf-8",
)

L = logger
