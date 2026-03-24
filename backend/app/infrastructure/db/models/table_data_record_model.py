from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class TableDataRecordModel(Base):
    """
    Модель для хранения заполненных записей данных в таблице.
    
    data_json структура:
    {
        "column_key1": value1,
        "column_key2": value2,
        ...
    }
    """

    __tablename__ = "table_data_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    table_id: Mapped[int] = mapped_column(ForeignKey("table_structures.id", ondelete="CASCADE"))
    data_json: Mapped[dict] = mapped_column(JSONB, default={})  # Заполненные данные
    submitter_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
