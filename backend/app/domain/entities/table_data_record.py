from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class TableDataRecord:
    """Запись данных в таблице"""
    id: Optional[int] = None
    workspace_id: Optional[int] = None
    table_id: Optional[int] = None
    data: dict = None  # JSONB с данными: {"column_key": value, ...}
    submitter_email: Optional[str] = None  # Email того, кто заполнил форму
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}
