from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

from parser.config import CONFIG, ensure_directories


_LOGGER_CREATED = False


def _formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _log_file() -> Path:
    ensure_directories()

    today = datetime.now().strftime("%Y-%m-%d")

    return CONFIG.log_directory / f"{today}.log"


def setup_logging() -> None:
    global _LOGGER_CREATED

    if _LOGGER_CREATED:
        return

    root = logging.getLogger()

    root.setLevel(CONFIG.log_level)

    formatter = _formatter()

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    logfile = RotatingFileHandler(
        filename=_log_file(),
        encoding="utf-8",
        maxBytes=5 * 1024 * 1024,
        backupCount=20,
    )

    logfile.setFormatter(formatter)

    root.addHandler(console)
    root.addHandler(logfile)

    _LOGGER_CREATED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


class LoggerMixin:

    @property
    def log(self) -> logging.Logger:

        return get_logger(self.__class__.__name__)