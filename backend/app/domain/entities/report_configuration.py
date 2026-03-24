from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ReportConfiguration:
    id: int | None
    workspace_id: int
    name: str
    description: str | None
    report_type: str
    settings: dict[str, Any]
    is_published: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
