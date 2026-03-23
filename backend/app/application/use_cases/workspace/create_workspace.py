from app.domain.entities.workspace import Workspace
from app.domain.repositories.workspace_repository import WorkspaceRepository


class CreateWorkspaceUseCase:
    def __init__(self, workspace_repository: WorkspaceRepository) -> None:
        self.workspace_repository = workspace_repository

    def execute(self, owner_id: int, name: str, description: str | None = None) -> Workspace:
        workspace = Workspace(id=None, owner_id=owner_id, name=name, description=description)
        return self.workspace_repository.create(workspace)
