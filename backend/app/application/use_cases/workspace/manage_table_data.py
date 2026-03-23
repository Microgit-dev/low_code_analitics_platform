from typing import List, Optional, Tuple

from app.domain.entities.table_data_record import TableDataRecord
from app.domain.repositories.form_configuration_repository import TableDataRecordRepository


class TableDataRecordNotFoundError(Exception):
    pass


class ListTableDataRecordsUseCase:
    def __init__(self, repository: TableDataRecordRepository):
        self.repository = repository

    def execute(
        self, workspace_id: int, table_id: int, skip: int = 0, limit: int = 50
    ) -> Tuple[List[TableDataRecord], int]:
        """Получить записи с пагинацией. Возвращает (список записей, всего)"""
        return self.repository.list_by_table(workspace_id, table_id, skip, limit)


class GetTableDataRecordUseCase:
    def __init__(self, repository: TableDataRecordRepository):
        self.repository = repository

    def execute(self, workspace_id: int, record_id: int) -> TableDataRecord:
        record = self.repository.get_by_id(workspace_id, record_id)
        if not record:
            raise TableDataRecordNotFoundError(f"Record {record_id} not found")
        return record


class CreateTableDataRecordUseCase:
    """Use case для создания записи из публичной формы (без auth)"""

    def __init__(self, repository: TableDataRecordRepository):
        self.repository = repository

    def execute(
        self, workspace_id: int, table_id: int, data: dict, submitter_email: Optional[str] = None
    ) -> TableDataRecord:
        return self.repository.create_from_form(workspace_id, table_id, data, submitter_email)


class UpdateTableDataRecordUseCase:
    def __init__(self, repository: TableDataRecordRepository):
        self.repository = repository

    def execute(self, record: TableDataRecord, owner_id: int) -> TableDataRecord:
        # Verify record exists first
        existing = self.repository.get_by_id(record.workspace_id, record.id)
        if not existing:
            raise TableDataRecordNotFoundError(f"Record {record.id} not found")
        return self.repository.update(record, owner_id)


class DeleteTableDataRecordUseCase:
    def __init__(self, repository: TableDataRecordRepository):
        self.repository = repository

    def execute(self, workspace_id: int, record_id: int, owner_id: int) -> None:
        # Verify record exists first
        record = self.repository.get_by_id(workspace_id, record_id)
        if not record:
            raise TableDataRecordNotFoundError(f"Record {record_id} not found")
        self.repository.delete(workspace_id, record_id, owner_id)
