from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class TableRelationModel(Base):
    __tablename__ = "table_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_table_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("table_structures.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    target_table_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("table_structures.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mapping_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    properties_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
