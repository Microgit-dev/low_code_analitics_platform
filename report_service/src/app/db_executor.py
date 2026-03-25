from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Result

from .config import settings
from .dto import DbConnection

logger = logging.getLogger(__name__)


class DbExecutionError(Exception):
    pass


def execute_safe_select(sql: str, conn: DbConnection) -> Tuple[List[Dict[str, Any]], List[str]]:
    try:
        engine = create_engine(
            conn.sqlalchemy_url(),
            pool_pre_ping=True,
            future=True,
            connect_args=conn.sqlalchemy_connect_args(),
        )
    except Exception as e:
        raise DbExecutionError(f"Ошибка создания подключения к БД: {e}")

    rows: List[Dict[str, Any]] = []
    columns: List[str] = []

    timeout_ms = settings.db_default_statement_timeout_ms
    max_rows = settings.db_max_rows

    try:
        with engine.begin() as c:
            c.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
            c.execute(text("SET LOCAL default_transaction_read_only = on"))
            result: Result = c.execute(text(sql))
            columns = list(result.keys())
            count = 0
            for row in result:
                rows.append(dict(row._mapping))
                count += 1
                if count >= max_rows:
                    break
    except Exception as e:
        raise DbExecutionError(f"Ошибка выполнения SQL: {e}")
    finally:
        try:
            engine.dispose()
        except Exception:
            pass

    return rows, columns
