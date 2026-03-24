from typing import Any

from app.domain.entities.table_structure import TableRelation, TableStructure
from app.domain.repositories.table_structure_repository import TableStructureRepository


class TableStructureNotFoundError(Exception):
    pass


class TableRelationNotFoundError(Exception):
    pass


class CreateTableStructureUseCase:
    def __init__(self, repository: TableStructureRepository) -> None:
        self.repository = repository

    def execute(
        self,
        workspace_id: int,
        owner_id: int,
        name: str,
        description: str | None,
        columns: list[dict[str, Any]],
    ) -> TableStructure:
        created = self.repository.create_table(workspace_id, owner_id, name, description, columns)
        if created is None:
            raise TableStructureNotFoundError("Workspace not found")
        return created


class ListTableStructuresUseCase:
    def __init__(self, repository: TableStructureRepository) -> None:
        self.repository = repository

    def execute(self, workspace_id: int, owner_id: int) -> list[TableStructure]:
        return self.repository.list_tables(workspace_id, owner_id)


class UpdateTableStructureUseCase:
    def __init__(self, repository: TableStructureRepository) -> None:
        self.repository = repository

    def execute(
        self,
        workspace_id: int,
        owner_id: int,
        table_id: int,
        name: str,
        description: str | None,
        columns: list[dict[str, Any]],
    ) -> TableStructure:
        updated = self.repository.update_table(workspace_id, owner_id, table_id, name, description, columns)
        if updated is None:
            raise TableStructureNotFoundError("Table structure not found")
        return updated


class MoveTableColumnUseCase:
    def __init__(self, repository: TableStructureRepository) -> None:
        self.repository = repository

    def execute(
        self,
        workspace_id: int,
        owner_id: int,
        source_table_id: int,
        target_table_id: int,
        column_key: str,
    ) -> None:
        moved = self.repository.move_column(
            workspace_id,
            owner_id,
            source_table_id,
            target_table_id,
            column_key,
        )
        if not moved:
            raise TableStructureNotFoundError("Cannot move column")


class DeleteTableStructureUseCase:
    def __init__(self, repository: TableStructureRepository) -> None:
        self.repository = repository

    def execute(self, workspace_id: int, owner_id: int, table_id: int) -> None:
        deleted = self.repository.delete_table(workspace_id, owner_id, table_id)
        if not deleted:
            raise TableStructureNotFoundError("Table structure not found")


class ListTableRelationsUseCase:
    def __init__(self, repository: TableStructureRepository) -> None:
        self.repository = repository

    def execute(self, workspace_id: int, owner_id: int) -> list[TableRelation]:
        return self.repository.list_relations(workspace_id, owner_id)


class CreateTableRelationUseCase:
    def __init__(self, repository: TableStructureRepository) -> None:
        self.repository = repository

    def execute(
        self,
        workspace_id: int,
        owner_id: int,
        source_table_id: int,
        target_table_id: int,
        relation_type: str,
        name: str,
        mapping: dict[str, str],
        properties: dict[str, Any],
    ) -> TableRelation:
        created = self.repository.create_relation(
            workspace_id,
            owner_id,
            source_table_id,
            target_table_id,
            relation_type,
            name,
            mapping,
            properties,
        )
        if created is None:
            raise TableStructureNotFoundError("Source or target table not found")
        return created


class DeleteTableRelationUseCase:
    def __init__(self, repository: TableStructureRepository) -> None:
        self.repository = repository

    def execute(self, workspace_id: int, owner_id: int, relation_id: int) -> None:
        deleted = self.repository.delete_relation(workspace_id, owner_id, relation_id)
        if not deleted:
            raise TableRelationNotFoundError("Relation not found")
