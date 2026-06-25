from __future__ import annotations

import sqlite3

from pathlib import Path

from parser.config import CONFIG
from parser.logger import get_logger

log = get_logger(__name__)


class Database:

    def __init__(self):

        self.path: Path = CONFIG.database

        self.connection = sqlite3.connect(self.path)

        self.connection.row_factory = sqlite3.Row

    def execute(self, sql: str, params=()):

        return self.connection.execute(sql, params)

    def executemany(self, sql: str, params):

        return self.connection.executemany(sql, params)

    def commit(self):

        self.connection.commit()

    def rollback(self):

        self.connection.rollback()

    def close(self):

        self.connection.close()

    def __enter__(self):

        return self

    def __exit__(self, exc_type, exc, tb):

        if exc is None:
            self.commit()
        else:
            self.rollback()

        self.close()