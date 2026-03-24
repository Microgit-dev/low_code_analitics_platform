from abc import ABC, abstractmethod

from app.domain.entities.report_configuration import ReportConfiguration


class ReportConfigurationRepository(ABC):
    @abstractmethod
    def list_by_workspace(self, workspace_id: int) -> list[ReportConfiguration]:
        pass

    @abstractmethod
    def get_by_id(self, workspace_id: int, report_id: int) -> ReportConfiguration | None:
        pass

    @abstractmethod
    def get_public_by_id(self, report_id: int) -> ReportConfiguration | None:
        pass

    @abstractmethod
    def create(self, report: ReportConfiguration, owner_id: int) -> ReportConfiguration:
        pass

    @abstractmethod
    def update(self, report: ReportConfiguration, owner_id: int) -> ReportConfiguration:
        pass

    @abstractmethod
    def delete(self, workspace_id: int, report_id: int, owner_id: int) -> None:
        pass
