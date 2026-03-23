from app.domain.entities.workspace import Workspace
from app.domain.repositories.workspace_repository import WorkspaceRepository


class ListUserWorkspacesUseCase:
    def __init__(self, workspace_repository: WorkspaceRepository) -> None:
        self.workspace_repository = workspace_repository

    def execute(self, owner_id: int) -> list[Workspace]:
        return self.workspace_repository.list_by_owner(owner_id)
