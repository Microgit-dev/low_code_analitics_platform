from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.form_configuration import FormConfiguration
from app.domain.entities.table_data_record import TableDataRecord


class FormConfigurationRepository(ABC):
    """Абстрактный репозиторий для управления конфигурациями форм"""

    @abstractmethod
    def list_by_table(self, workspace_id: int, table_id: Optional[int] = None) -> List[FormConfiguration]:
        """Получить формы workspace, опционально отфильтрованные по таблице"""
        pass

    @abstractmethod
    def get_by_id(self, workspace_id: int, form_id: int) -> Optional[FormConfiguration]:
        """Получить форму по ID с проверкой владельца"""
        pass

    @abstractmethod
    def create(self, form: FormConfiguration, owner_id: int) -> FormConfiguration:
        """Создать новую форму"""
        pass

    @abstractmethod
    def update(self, form: FormConfiguration, owner_id: int) -> FormConfiguration:
        """Обновить форму"""
        pass

    @abstractmethod
    def delete(self, workspace_id: int, form_id: int, owner_id: int) -> None:
        """Удалить форму"""
        pass


class TableDataRecordRepository(ABC):
    """Абстрактный репозиторий для управления записями данных"""

    @abstractmethod
    def list_by_table(
        self, workspace_id: int, table_id: int, skip: int = 0, limit: int = 50
    ) -> tuple[List[TableDataRecord], int]:
        """Получить записи таблицы c пагинацией, возвращает (список записей, всего)"""
        pass

    @abstractmethod
    def get_by_id(self, workspace_id: int, record_id: int) -> Optional[TableDataRecord]:
        """Получить запись по ID"""
        pass

    @abstractmethod
    def create_from_form(
        self, workspace_id: int, table_id: int, data: dict, submitter_email: Optional[str] = None
    ) -> TableDataRecord:
        """Создать запись из заполненной формы (без auth, но с workspace_id и table_id)"""
        pass

    @abstractmethod
    def update(self, record: TableDataRecord, owner_id: int) -> TableDataRecord:
        """Обновить запись (только авторизованный пользователь)"""
        pass

    @abstractmethod
    def delete(self, workspace_id: int, record_id: int, owner_id: int) -> None:
        """Удалить запись"""
        pass
