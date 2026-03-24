from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class FormFieldSchema(BaseModel):
    """Поле в конфигурации формы"""

    table_id: Optional[int] = None
    column_key: str
    column_name: str
    field_label: str
    widget_type: str  # text_input, textarea, number_input, date_input, datetime_input, select, checkbox, radio
    required: bool = True
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    auto_generate_id: bool = False
    widget_settings: dict = Field(default_factory=dict)


class FormConfigurationCreateRequest(BaseModel):
    """Request для создания формы"""

    table_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    fields: List[FormFieldSchema]
    collect_email: bool = False


class FormConfigurationUpdateRequest(BaseModel):
    """Request для обновления формы"""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    fields: List[FormFieldSchema]
    is_published: bool = False
    collect_email: bool = False


class FormConfigurationResponse(BaseModel):
    """Response с конфигурацией формы"""

    id: int
    workspace_id: int
    table_id: int
    name: str
    description: str
    fields: List[FormFieldSchema]
    is_published: bool
    collect_email: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PublicFormSubmitRequest(BaseModel):
    """Публичная отправка формы"""

    data: dict[str, Any]
    submitter_email: Optional[str] = None


class PublicFormSubmitRecordResponse(BaseModel):
    table_id: int
    record_id: int


class PublicFormSubmitResponse(BaseModel):
    form_id: int
    records: list[PublicFormSubmitRecordResponse]
