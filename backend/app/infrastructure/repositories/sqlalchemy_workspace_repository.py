from sqlalchemy.orm import Session

from app.domain.entities.workspace import Workspace
from app.domain.repositories.workspace_repository import WorkspaceRepository
from app.infrastructure.db.models.workspace_model import WorkspaceModel


class SQLAlchemyWorkspaceRepository(WorkspaceRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, workspace: Workspace) -> Workspace:
        model = WorkspaceModel(
            owner_id=workspace.owner_id,
            name=workspace.name,
            description=workspace.description,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return Workspace(
            id=model.id,
            owner_id=model.owner_id,
            name=model.name,
            description=model.description,
            created_at=model.created_at,
        )

    def list_by_owner(self, owner_id: int) -> list[Workspace]:
        models = (
            self.db.query(WorkspaceModel)
            .filter(WorkspaceModel.owner_id == owner_id)
            .order_by(WorkspaceModel.created_at.desc())
            .all()
        )
        return [
            Workspace(
                id=model.id,
                owner_id=model.owner_id,
                name=model.name,
                description=model.description,
                created_at=model.created_at,
            )
            for model in models
        ]

    def update_by_owner(
        self,
        workspace_id: int,
        owner_id: int,
        name: str,
        description: str | None,
    ) -> Workspace | None:
        model = (
            self.db.query(WorkspaceModel)
            .filter(WorkspaceModel.id == workspace_id, WorkspaceModel.owner_id == owner_id)
            .first()
        )

        if model is None:
            return None

        model.name = name
        model.description = description

        self.db.commit()
        self.db.refresh(model)

        return Workspace(
            id=model.id,
            owner_id=model.owner_id,
            name=model.name,
            description=model.description,
            created_at=model.created_at,
        )

    def delete_by_owner(self, workspace_id: int, owner_id: int) -> bool:
        model = (
            self.db.query(WorkspaceModel)
            .filter(WorkspaceModel.id == workspace_id, WorkspaceModel.owner_id == owner_id)
            .first()
        )

        if model is None:
            return False

        self.db.delete(model)
        self.db.commit()
        return True
