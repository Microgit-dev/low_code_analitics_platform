from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


@dataclass
class FormField:
    """Поле в форме конструктора"""
    column_key: str  # Ключ колонки из таблицы
    column_name: str  # Название колонки
    field_label: str  # Какой label показать в форме
    widget_type: str  # Тип виджета: text_input, textarea, number_input, date_input, datetime_input, select, checkbox, radio
    table_id: Optional[int] = None  # ID таблицы, в которую попадет это поле
    required: bool = True
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    widget_settings: dict = field(default_factory=dict)  # Доп. настройки для виджета


@dataclass
class FormConfiguration:
    """Конфигурация формы для заполнения данных"""
    id: Optional[int] = None
    workspace_id: Optional[int] = None
    table_id: Optional[int] = None
    name: str = ""
    description: str = ""
    fields: List[FormField] = field(default_factory=list)
    is_published: bool = False
    collect_email: bool = False  # Собирать ли email отправителя
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
