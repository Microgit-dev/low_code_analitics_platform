from abc import ABC, abstractmethod

from app.domain.entities.workspace import Workspace


class WorkspaceRepository(ABC):
    @abstractmethod
    def create(self, workspace: Workspace) -> Workspace:
        raise NotImplementedError

    @abstractmethod
    def list_by_owner(self, owner_id: int) -> list[Workspace]:
        raise NotImplementedError

    @abstractmethod
    def update_by_owner(
        self,
        workspace_id: int,
        owner_id: int,
        name: str,
        description: str | None,
    ) -> Workspace | None:
        raise NotImplementedError

    @abstractmethod
    def delete_by_owner(self, workspace_id: int, owner_id: int) -> bool:
        raise NotImplementedError
