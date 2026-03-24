from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class FormConfigurationModel(Base):
    """
    Модель конфигурации формы для сбора данных в таблицу.
    
    fields_json структура:
    [
        {
            "column_key": "user_name",
            "column_name": "Name",
            "field_label": "Your Full Name",
            "widget_type": "text_input",
            "required": True,
            "placeholder": "Enter your name",
            "help_text": "",
            "widget_settings": {}
        }
    ]
    """

    __tablename__ = "form_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    table_id: Mapped[int] = mapped_column(ForeignKey("table_structures.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    fields_json: Mapped[list] = mapped_column(JSONB, default=[])  # Конфиг полей формы
    is_published: Mapped[bool] = mapped_column(default=False)
    collect_email: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
