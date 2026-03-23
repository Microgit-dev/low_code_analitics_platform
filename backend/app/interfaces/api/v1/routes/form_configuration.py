from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.use_cases.workspace.manage_forms import (
    CreateFormConfigurationUseCase,
    DeleteFormConfigurationUseCase,
    FormConfigurationNotFoundError,
    GetFormConfigurationUseCase,
    ListFormConfigurationsUseCase,
    UpdateFormConfigurationUseCase,
)
from app.domain.entities.form_configuration import FormConfiguration, FormField
from app.domain.repositories.form_configuration_repository import FormConfigurationRepository
from app.infrastructure.db.models.form_configuration_model import FormConfigurationModel
from app.infrastructure.repositories.sqlalchemy_form_configuration_repository import (
    SQLAlchemyFormConfigurationRepository,
    SQLAlchemyTableDataRecordRepository,
)
from app.interfaces.api.dependencies.auth import get_current_user
from app.interfaces.api.dependencies.db import get_db
from app.interfaces.api.v1.schemas.form_configuration import (
    FormConfigurationCreateRequest,
    FormConfigurationResponse,
    PublicFormSubmitRequest,
    PublicFormSubmitResponse,
    PublicFormSubmitRecordResponse,
    FormConfigurationUpdateRequest,
    FormFieldSchema,
)

router = APIRouter()


def _map_form_field(field: FormField) -> FormFieldSchema:
    return FormFieldSchema(
        table_id=field.table_id,
        column_key=field.column_key,
        column_name=field.column_name,
        field_label=field.field_label,
        widget_type=field.widget_type,
        required=field.required,
        placeholder=field.placeholder,
        help_text=field.help_text,
        widget_settings=field.widget_settings,
    )


def _map_form_response(form: FormConfiguration) -> FormConfigurationResponse:
    now = datetime.utcnow()
    return FormConfigurationResponse(
        id=form.id,
        workspace_id=form.workspace_id,
        table_id=form.table_id,
        name=form.name,
        description=form.description,
        fields=[_map_form_field(field) for field in form.fields],
        is_published=form.is_published,
        collect_email=form.collect_email,
        created_at=form.created_at or now,
        updated_at=form.updated_at or now,
    )


def get_form_repo(session: Session = Depends(get_db)) -> FormConfigurationRepository:
    return SQLAlchemyFormConfigurationRepository(session)


@router.get("/forms/{form_id}")
def get_public_form(
    form_id: int,
    session: Session = Depends(get_db),
):
    """Публичный endpoint для получения опубликованной формы (без auth)"""
    form_model = session.execute(
        select(FormConfigurationModel).where(FormConfigurationModel.id == form_id)
    ).scalar()

    if not form_model or not form_model.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found or not published")

    return FormConfigurationResponse(
        id=form_model.id,
        workspace_id=form_model.workspace_id,
        table_id=form_model.table_id,
        name=form_model.name,
        description=form_model.description,
        fields=[
            FormFieldSchema(
                table_id=f.get("table_id"),
                column_key=f["column_key"],
                column_name=f["column_name"],
                field_label=f["field_label"],
                widget_type=f["widget_type"],
                required=f.get("required", True),
                placeholder=f.get("placeholder"),
                help_text=f.get("help_text"),
                widget_settings=f.get("widget_settings", {}),
            )
            for f in form_model.fields_json
        ],
        is_published=form_model.is_published,
        collect_email=form_model.collect_email,
        created_at=form_model.created_at,
        updated_at=form_model.updated_at,
    )


@router.post("/forms/{form_id}/submit", status_code=status.HTTP_201_CREATED)
def submit_public_form(
    form_id: int,
    payload: PublicFormSubmitRequest,
    session: Session = Depends(get_db),
):
    """Публичная отправка формы. Поддерживает поля из нескольких таблиц."""
    form_model = session.execute(
        select(FormConfigurationModel).where(FormConfigurationModel.id == form_id)
    ).scalar()

    if not form_model or not form_model.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found or not published")

    # Проверка обязательных полей
    missing_required: list[str] = []
    for field in form_model.fields_json:
        key = field.get("column_key")
        if not key:
            continue
        value = payload.data.get(key)
        if field.get("required", True):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing_required.append(key)

    if missing_required:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"missing_required_fields": missing_required},
        )

    # Раскладываем поля по таблицам
    table_payloads: dict[int, dict[str, Any]] = defaultdict(dict)
    for field in form_model.fields_json:
        key = field.get("column_key")
        if not key or key not in payload.data:
            continue
        value = payload.data.get(key)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue

        table_id = field.get("table_id") or form_model.table_id
        if table_id is None:
            continue

        table_payloads[int(table_id)][key] = value

    data_repo = SQLAlchemyTableDataRecordRepository(session)
    records: list[PublicFormSubmitRecordResponse] = []
    for table_id, data in table_payloads.items():
        if not data:
            continue
        created = data_repo.create_from_form(
            workspace_id=form_model.workspace_id,
            table_id=table_id,
            data=data,
            submitter_email=payload.submitter_email if form_model.collect_email else None,
        )
        records.append(PublicFormSubmitRecordResponse(table_id=table_id, record_id=created.id))

    return PublicFormSubmitResponse(form_id=form_model.id, records=records)


@router.get("/workspaces/{workspace_id}/forms")
def list_forms(
    workspace_id: int,
    table_id: int,
    current_user=Depends(get_current_user),
    repo: FormConfigurationRepository = Depends(get_form_repo),
):
    """Получить все формы для таблицы"""
    use_case = ListFormConfigurationsUseCase(repo)
    forms = use_case.execute(workspace_id, table_id)
    return [_map_form_response(form) for form in forms]


@router.post("/workspaces/{workspace_id}/forms", status_code=status.HTTP_201_CREATED)
def create_form(
    workspace_id: int,
    payload: FormConfigurationCreateRequest,
    current_user=Depends(get_current_user),
    repo: FormConfigurationRepository = Depends(get_form_repo),
):
    """Создать новую форму"""
    form = FormConfiguration(
        workspace_id=workspace_id,
        table_id=payload.table_id,
        name=payload.name,
        description=payload.description,
        fields=payload.fields,
        collect_email=payload.collect_email,
    )
    use_case = CreateFormConfigurationUseCase(repo)
    try:
        created = use_case.execute(form, current_user.id)
        return _map_form_response(created)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("/workspaces/{workspace_id}/forms/{form_id}")
def get_form(
    workspace_id: int,
    form_id: int,
    current_user=Depends(get_current_user),
    repo: FormConfigurationRepository = Depends(get_form_repo),
):
    """Получить форму по ID"""
    use_case = GetFormConfigurationUseCase(repo)
    try:
        form = use_case.execute(workspace_id, form_id)
        return _map_form_response(form)
    except FormConfigurationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")


@router.put("/workspaces/{workspace_id}/forms/{form_id}")
def update_form(
    workspace_id: int,
    form_id: int,
    payload: FormConfigurationUpdateRequest,
    current_user=Depends(get_current_user),
    repo: FormConfigurationRepository = Depends(get_form_repo),
):
    """Обновить форму"""
    # Получить существующую форму для сохранения table_id
    get_use_case = GetFormConfigurationUseCase(repo)
    try:
        existing = get_use_case.execute(workspace_id, form_id)
    except FormConfigurationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")

    form = FormConfiguration(
        id=form_id,
        workspace_id=workspace_id,
        table_id=existing.table_id,
        name=payload.name,
        description=payload.description,
        fields=payload.fields,
        is_published=payload.is_published,
        collect_email=payload.collect_email,
    )
    use_case = UpdateFormConfigurationUseCase(repo)
    try:
        updated = use_case.execute(form, current_user.id)
        return _map_form_response(updated)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except FormConfigurationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")


@router.delete("/workspaces/{workspace_id}/forms/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form(
    workspace_id: int,
    form_id: int,
    current_user=Depends(get_current_user),
    repo: FormConfigurationRepository = Depends(get_form_repo),
):
    """Удалить форму"""
    use_case = DeleteFormConfigurationUseCase(repo)
    try:
        use_case.execute(workspace_id, form_id, current_user.id)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except FormConfigurationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")
