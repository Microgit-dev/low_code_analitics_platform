from abc import ABC, abstractmethod
from typing import Any

from app.domain.entities.table_structure import TableRelation, TableStructure


class TableStructureRepository(ABC):
    @abstractmethod
    def list_tables(self, workspace_id: int, owner_id: int) -> list[TableStructure]:
        raise NotImplementedError

    @abstractmethod
    def create_table(
        self,
        workspace_id: int,
        owner_id: int,
        name: str,
        description: str | None,
        columns: list[dict[str, Any]],
    ) -> TableStructure | None:
        raise NotImplementedError

    @abstractmethod
    def update_table(
        self,
        workspace_id: int,
        owner_id: int,
        table_id: int,
        name: str,
        description: str | None,
        columns: list[dict[str, Any]],
    ) -> TableStructure | None:
        raise NotImplementedError

    @abstractmethod
    def delete_table(self, workspace_id: int, owner_id: int, table_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def move_column(
        self,
        workspace_id: int,
        owner_id: int,
        source_table_id: int,
        target_table_id: int,
        column_key: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_relations(self, workspace_id: int, owner_id: int) -> list[TableRelation]:
        raise NotImplementedError

    @abstractmethod
    def create_relation(
        self,
        workspace_id: int,
        owner_id: int,
        source_table_id: int,
        target_table_id: int,
        relation_type: str,
        name: str,
        mapping: dict[str, str],
        properties: dict[str, Any],
    ) -> TableRelation | None:
        raise NotImplementedError

    @abstractmethod
    def delete_relation(self, workspace_id: int, owner_id: int, relation_id: int) -> bool:
        raise NotImplementedError
