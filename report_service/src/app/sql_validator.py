from __future__ import annotations
import logging
import json
import re
from typing import Dict, List, Optional

import sqlparse
import sqlglot
from sqlglot import expressions as exp

from .dto import DbSchema
from .config import settings

logger = logging.getLogger(__name__)

_DISALLOWED = {k.strip().upper() for k in settings.sql_disallowed_keywords.split(',')}
_COMMENT_PATTERNS = [r"--", r"/\*", r"\*/"]

class SqlValidationError(Exception):
    pass

class SafeSqlValidator:
    def __init__(self, schema: DbSchema):
        self.schema = schema
        self.allowed_tables = set(t.name for t in schema.tables)
        self.allowed_columns = schema.columns_by_table()

    def validate(self, sql: str) -> str:
        cleaned = sql.strip()
        if not cleaned:
            raise SqlValidationError("Пустой SQL.")

        # Reject obvious markdown/code fences and comments
        if cleaned.startswith("```") or cleaned.endswith("```"):
            raise SqlValidationError("SQL не должен содержать markdown-заборы кода.")
        for pat in _COMMENT_PATTERNS:
            if pat in cleaned:
                raise SqlValidationError("SQL не должен содержать комментарии.")

        # Ensure single statement
        parts = [p.strip() for p in sqlparse.split(cleaned) if p.strip()]
        if len(parts) != 1:
            raise SqlValidationError("Разрешён только один SQL-запрос.")
        single = parts[0]

        # Disallow dangerous keywords
        upper = re.sub(r"\s+", " ", single).upper()
        for bad in _DISALLOWED:
            if re.search(rf"\b{re.escape(bad)}\b", upper):
                raise SqlValidationError(f"Запрещённое ключевое слово: {bad}.")

        # Parse and analyze
        try:
            ast = sqlglot.parse_one(single, read="postgres")
        except Exception as e:
            raise SqlValidationError(f"Не удалось распарсить SQL: {e}")

        # Only SELECT / WITH ... SELECT allowed
        if not isinstance(ast, (exp.Select, exp.With, exp.Union, exp.Subquery, exp.CTE)):
            # Normalize: WITH returns exp.With
            pass
        root = ast
        if isinstance(root, exp.With):
            # must contain a final SELECT
            last = root.find(exp.Select)
            if not last:
                raise SqlValidationError("WITH должен заканчиваться SELECT.")
        elif isinstance(root, exp.Union):
            # union of selects is OK
            if not all(isinstance(node, (exp.Select, exp.Subquery)) for node in root.find_all(exp.Select)):
                raise SqlValidationError("Разрешён UNION только из SELECT.")
        elif not isinstance(root, (exp.Select, exp.Subquery)):
            raise SqlValidationError("Разрешены только SELECT или WITH ... SELECT.")

        # Disallow DDL/DML anywhere in tree
        forbidden_types = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Alter, exp.Drop, exp.Command)
        if any(isinstance(node, forbidden_types) for node in ast.walk()):
            raise SqlValidationError("Обнаружены запрещённые операции.")

                # Check referenced tables
        referenced_tables = set()
        alias_map = {}
        for t in ast.find_all(exp.Table):
            name = t.this and t.this.name
            if name:
                referenced_tables.add(name)
                if name not in self.allowed_tables:
                    raise SqlValidationError(f"Таблица не разрешена: {name}.")
                # collect aliases
                alias = getattr(t, 'alias', None)
                alias_name = None
                if alias is not None:
                    if isinstance(alias, str):
                        alias_name = alias
                    else:
                        try:
                            alias_name = alias.this.name if getattr(alias, 'this', None) else None
                        except Exception:
                            alias_name = None
                if alias_name:
                    alias_map[alias_name] = name

        # Check referenced columns where possible
        if referenced_tables:
            for col in ast.find_all(exp.Column):
                col_name = col.this and col.this.name
                tbl = col.table
                if not col_name:
                    continue
                if tbl:
                    # qualified: resolve alias if present
                    tbl_resolved = alias_map.get(tbl, tbl)
                    if tbl_resolved not in self.allowed_tables:
                        raise SqlValidationError(f"Таблица не разрешена для колонки: {tbl}.{col_name}.")
                    allowed_cols = set(self.allowed_columns.get(tbl_resolved, []))
                    if allowed_cols and col_name not in allowed_cols:
                        raise SqlValidationError(f"Колонка не разрешена: {tbl}.{col_name}.")
                else:
                    # unqualified: must exist in at least one referenced table's columns
                    allowed_any = any(
                        col_name in set(self.allowed_columns.get(t, [])) for t in referenced_tables
                    )
                    if not allowed_any:
                        raise SqlValidationError(f"Колонка не найдена в разрешённых таблицах: {col_name}.")

        # All good, return normalized SQL (but keep user's whitespace)
        return single







