from copy import deepcopy
from typing import Any

from sqlalchemy.orm import Session

from app.domain.entities.table_structure import TableRelation, TableStructure
from app.domain.repositories.table_structure_repository import TableStructureRepository
from app.infrastructure.db.models.table_relation_model import TableRelationModel
from app.infrastructure.db.models.table_structure_model import TableStructureModel
from app.infrastructure.db.models.workspace_model import WorkspaceModel


class SQLAlchemyTableStructureRepository(TableStructureRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def _workspace_belongs_to_owner(self, workspace_id: int, owner_id: int) -> bool:
        workspace = (
            self.db.query(WorkspaceModel)
            .filter(WorkspaceModel.id == workspace_id, WorkspaceModel.owner_id == owner_id)
            .first()
        )
        return workspace is not None

    def _get_table_for_owner(
        self,
        workspace_id: int,
        owner_id: int,
        table_id: int,
    ) -> TableStructureModel | None:
        return (
            self.db.query(TableStructureModel)
            .join(WorkspaceModel, WorkspaceModel.id == TableStructureModel.workspace_id)
            .filter(
                TableStructureModel.id == table_id,
                TableStructureModel.workspace_id == workspace_id,
                WorkspaceModel.owner_id == owner_id,
            )
            .first()
        )

    def list_tables(self, workspace_id: int, owner_id: int) -> list[TableStructure]:
        if not self._workspace_belongs_to_owner(workspace_id, owner_id):
            return []

        models = (
            self.db.query(TableStructureModel)
            .filter(TableStructureModel.workspace_id == workspace_id)
            .order_by(TableStructureModel.created_at.desc())
            .all()
        )
        return [
            TableStructure(
                id=model.id,
                workspace_id=model.workspace_id,
                name=model.name,
                description=model.description,
                columns=deepcopy(model.columns_json or []),
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in models
        ]

    def create_table(
        self,
        workspace_id: int,
        owner_id: int,
        name: str,
        description: str | None,
        columns: list[dict[str, Any]],
    ) -> TableStructure | None:
        if not self._workspace_belongs_to_owner(workspace_id, owner_id):
            return None

        model = TableStructureModel(
            workspace_id=workspace_id,
            name=name,
            description=description,
            columns_json=deepcopy(columns),
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return TableStructure(
            id=model.id,
            workspace_id=model.workspace_id,
            name=model.name,
            description=model.description,
            columns=deepcopy(model.columns_json or []),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def update_table(
        self,
        workspace_id: int,
        owner_id: int,
        table_id: int,
        name: str,
        description: str | None,
        columns: list[dict[str, Any]],
    ) -> TableStructure | None:
        model = self._get_table_for_owner(workspace_id, owner_id, table_id)
        if model is None:
            return None

        model.name = name
        model.description = description
        model.columns_json = deepcopy(columns)
        self.db.commit()
        self.db.refresh(model)
        return TableStructure(
            id=model.id,
            workspace_id=model.workspace_id,
            name=model.name,
            description=model.description,
            columns=deepcopy(model.columns_json or []),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def delete_table(self, workspace_id: int, owner_id: int, table_id: int) -> bool:
        model = self._get_table_for_owner(workspace_id, owner_id, table_id)
        if model is None:
            return False

        self.db.delete(model)
        self.db.commit()
        return True

    def move_column(
        self,
        workspace_id: int,
        owner_id: int,
        source_table_id: int,
        target_table_id: int,
        column_key: str,
    ) -> bool:
        source_model = self._get_table_for_owner(workspace_id, owner_id, source_table_id)
        target_model = self._get_table_for_owner(workspace_id, owner_id, target_table_id)
        if source_model is None or target_model is None:
            return False

        source_columns = deepcopy(source_model.columns_json or [])
        target_columns = deepcopy(target_model.columns_json or [])

        source_index = next((index for index, col in enumerate(source_columns) if col.get("key") == column_key), -1)
        if source_index < 0:
            return False

        moving_column = source_columns.pop(source_index)
        existing_in_target = next((col for col in target_columns if col.get("key") == column_key), None)
        if existing_in_target is not None:
            return False

        target_columns.append(moving_column)
        source_model.columns_json = source_columns
        target_model.columns_json = target_columns
        self.db.commit()
        return True

    def list_relations(self, workspace_id: int, owner_id: int) -> list[TableRelation]:
        if not self._workspace_belongs_to_owner(workspace_id, owner_id):
            return []

        models = (
            self.db.query(TableRelationModel)
            .filter(TableRelationModel.workspace_id == workspace_id)
            .order_by(TableRelationModel.created_at.desc())
            .all()
        )
        return [
            TableRelation(
                id=model.id,
                workspace_id=model.workspace_id,
                source_table_id=model.source_table_id,
                target_table_id=model.target_table_id,
                relation_type=model.relation_type,
                name=model.name,
                mapping=deepcopy(model.mapping_json or {}),
                properties=deepcopy(model.properties_json or {}),
                created_at=model.created_at,
            )
            for model in models
        ]

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
        source_model = self._get_table_for_owner(workspace_id, owner_id, source_table_id)
        target_model = self._get_table_for_owner(workspace_id, owner_id, target_table_id)
        if source_model is None or target_model is None:
            return None

        relation_model = TableRelationModel(
            workspace_id=workspace_id,
            source_table_id=source_table_id,
            target_table_id=target_table_id,
            relation_type=relation_type,
            name=name,
            mapping_json=deepcopy(mapping),
            properties_json=deepcopy(properties),
        )
        self.db.add(relation_model)
        self.db.commit()
        self.db.refresh(relation_model)
        return TableRelation(
            id=relation_model.id,
            workspace_id=relation_model.workspace_id,
            source_table_id=relation_model.source_table_id,
            target_table_id=relation_model.target_table_id,
            relation_type=relation_model.relation_type,
            name=relation_model.name,
            mapping=deepcopy(relation_model.mapping_json or {}),
            properties=deepcopy(relation_model.properties_json or {}),
            created_at=relation_model.created_at,
        )

    def delete_relation(self, workspace_id: int, owner_id: int, relation_id: int) -> bool:
        if not self._workspace_belongs_to_owner(workspace_id, owner_id):
            return False

        model = (
            self.db.query(TableRelationModel)
            .filter(TableRelationModel.id == relation_id, TableRelationModel.workspace_id == workspace_id)
            .first()
        )
        if model is None:
            return False

        self.db.delete(model)
        self.db.commit()
        return True
