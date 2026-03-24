from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TableStructure:
    id: int | None
    workspace_id: int
    name: str
    description: str | None
    columns: list[dict[str, Any]]
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class TableRelation:
    id: int | None
    workspace_id: int
    source_table_id: int
    target_table_id: int
    relation_type: str
    name: str
    mapping: dict[str, str]
    properties: dict[str, Any]
    created_at: datetime | None = None
