from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.application.use_cases.workspace.manage_table_data import (
    CreateTableDataRecordUseCase,
    DeleteTableDataRecordUseCase,
    GetTableDataRecordUseCase,
    ListTableDataRecordsUseCase,
    TableDataRecordNotFoundError,
    UpdateTableDataRecordUseCase,
)
from app.domain.entities.table_data_record import TableDataRecord
from app.domain.repositories.form_configuration_repository import TableDataRecordRepository
from app.infrastructure.repositories.sqlalchemy_form_configuration_repository import (
    SQLAlchemyTableDataRecordRepository,
)
from app.interfaces.api.dependencies.auth import get_current_user
from app.interfaces.api.dependencies.db import get_db
from app.interfaces.api.v1.schemas.table_data_record import (
    FormSubmissionRequest,
    TableDataRecordResponse,
    TableDataRecordsListResponse,
)

router = APIRouter()


def get_data_repo(session: Session = Depends(get_db)) -> TableDataRecordRepository:
    return SQLAlchemyTableDataRecordRepository(session)


@router.get("/workspaces/{workspace_id}/tables/{table_id}/data")
def list_table_data(
    workspace_id: int,
    table_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user=Depends(get_current_user),
    repo: TableDataRecordRepository = Depends(get_data_repo),
):
    """Получить записи таблицы с пагинацией"""
    use_case = ListTableDataRecordsUseCase(repo)
    records, total = use_case.execute(workspace_id, table_id, skip, limit)

    return TableDataRecordsListResponse(
        items=[
            TableDataRecordResponse(
                id=r.id,
                workspace_id=r.workspace_id,
                table_id=r.table_id,
                data=r.data,
                submitter_email=r.submitter_email,
                submitted_at=r.submitted_at,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in records
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/workspaces/{workspace_id}/tables/{table_id}/data/{record_id}")
def get_table_data_record(
    workspace_id: int,
    table_id: int,
    record_id: int,
    current_user=Depends(get_current_user),
    repo: TableDataRecordRepository = Depends(get_data_repo),
):
    """Получить одну запись"""
    use_case = GetTableDataRecordUseCase(repo)
    try:
        record = use_case.execute(workspace_id, record_id)
        return TableDataRecordResponse(
            id=record.id,
            workspace_id=record.workspace_id,
            table_id=record.table_id,
            data=record.data,
            submitter_email=record.submitter_email,
            submitted_at=record.submitted_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
    except TableDataRecordNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")


@router.post(
    "/workspaces/{workspace_id}/tables/{table_id}/data/submit",
    status_code=status.HTTP_201_CREATED,
)
def submit_form_data(
    workspace_id: int,
    table_id: int,
    payload: FormSubmissionRequest,
    repo: TableDataRecordRepository = Depends(get_data_repo),
):
    """Публичный endpoint для заполнения формы (без auth)"""
    use_case = CreateTableDataRecordUseCase(repo)
    try:
        record = use_case.execute(workspace_id, table_id, payload.data, payload.submitter_email)
        return TableDataRecordResponse(
            id=record.id,
            workspace_id=record.workspace_id,
            table_id=record.table_id,
            data=record.data,
            submitter_email=record.submitter_email,
            submitted_at=record.submitted_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/workspaces/{workspace_id}/tables/{table_id}/data/{record_id}")
def update_table_data_record(
    workspace_id: int,
    table_id: int,
    record_id: int,
    payload: FormSubmissionRequest,
    current_user=Depends(get_current_user),
    repo: TableDataRecordRepository = Depends(get_data_repo),
):
    """Обновить запись (только авторизованный пользователь)"""
    use_case = UpdateTableDataRecordUseCase(repo)
    try:
        record = use_case.execute(
            TableDataRecord(
                id=record_id,
                workspace_id=workspace_id,
                table_id=table_id,
                data=payload.data,
                submitter_email=payload.submitter_email,
            ),
            current_user.id,
        )
        return TableDataRecordResponse(
            id=record.id,
            workspace_id=record.workspace_id,
            table_id=record.table_id,
            data=record.data,
            submitter_email=record.submitter_email,
            submitted_at=record.submitted_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except TableDataRecordNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")


@router.delete(
    "/workspaces/{workspace_id}/tables/{table_id}/data/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_table_data_record(
    workspace_id: int,
    table_id: int,
    record_id: int,
    current_user=Depends(get_current_user),
    repo: TableDataRecordRepository = Depends(get_data_repo),
):
    """Удалить запись (только авторизованный пользователь)"""
    use_case = DeleteTableDataRecordUseCase(repo)
    try:
        use_case.execute(workspace_id, record_id, current_user.id)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except TableDataRecordNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
