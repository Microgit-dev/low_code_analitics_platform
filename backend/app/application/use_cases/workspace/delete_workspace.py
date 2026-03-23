from app.domain.repositories.workspace_repository import WorkspaceRepository


class WorkspaceNotFoundError(Exception):
    pass


class DeleteWorkspaceUseCase:
    def __init__(self, workspace_repository: WorkspaceRepository) -> None:
        self.workspace_repository = workspace_repository

    def execute(self, workspace_id: int, owner_id: int) -> None:
        deleted = self.workspace_repository.delete_by_owner(workspace_id=workspace_id, owner_id=owner_id)
        if not deleted:
            raise WorkspaceNotFoundError("Workspace not found")
