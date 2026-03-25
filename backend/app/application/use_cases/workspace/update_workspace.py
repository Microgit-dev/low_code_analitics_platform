from app.application.use_cases.workspace.delete_workspace import WorkspaceNotFoundError
from app.domain.entities.workspace import Workspace
from app.domain.repositories.workspace_repository import WorkspaceRepository


class UpdateWorkspaceUseCase:
    def __init__(self, workspace_repository: WorkspaceRepository) -> None:
        self.workspace_repository = workspace_repository

    def execute(
        self,
        workspace_id: int,
        owner_id: int,
        name: str,
        description: str | None = None,
    ) -> Workspace:
        updated = self.workspace_repository.update_by_owner(
            workspace_id=workspace_id,
            owner_id=owner_id,
            name=name,
            description=description,
        )

        if updated is None:
            raise WorkspaceNotFoundError("Workspace not found")

        return updated
