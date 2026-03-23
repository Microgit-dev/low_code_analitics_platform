from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class FormSubmissionRequest(BaseModel):
    """Request для отправки заполненной формы"""

    data: Dict[str, Any]  # {column_key: value, ...}
    submitter_email: Optional[str] = None


class TableDataRecordResponse(BaseModel):
    """Response с записью данных"""

    id: int
    workspace_id: int
    table_id: int
    data: Dict[str, Any]
    submitter_email: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TableDataRecordsListResponse(BaseModel):
    """Response со списком записей с пагинацией"""

    items: list[TableDataRecordResponse]
    total: int
    skip: int
    limit: int

    @property
    def pages(self) -> int:
        return (self.total + self.limit - 1) // self.limit
