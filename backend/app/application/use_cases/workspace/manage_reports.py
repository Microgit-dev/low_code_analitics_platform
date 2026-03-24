from app.domain.entities.report_configuration import ReportConfiguration
from app.domain.repositories.report_configuration_repository import ReportConfigurationRepository


class ReportConfigurationNotFoundError(Exception):
    pass


class CreateReportConfigurationUseCase:
    def __init__(self, repository: ReportConfigurationRepository):
        self.repository = repository

    def execute(self, report: ReportConfiguration, owner_id: int) -> ReportConfiguration:
        return self.repository.create(report, owner_id)


class ListReportConfigurationsUseCase:
    def __init__(self, repository: ReportConfigurationRepository):
        self.repository = repository

    def execute(self, workspace_id: int) -> list[ReportConfiguration]:
        return self.repository.list_by_workspace(workspace_id)


class GetReportConfigurationUseCase:
    def __init__(self, repository: ReportConfigurationRepository):
        self.repository = repository

    def execute(self, workspace_id: int, report_id: int) -> ReportConfiguration:
        report = self.repository.get_by_id(workspace_id, report_id)
        if not report:
            raise ReportConfigurationNotFoundError(f"Report {report_id} not found")
        return report


class GetPublicReportConfigurationUseCase:
    def __init__(self, repository: ReportConfigurationRepository):
        self.repository = repository

    def execute(self, report_id: int) -> ReportConfiguration:
        report = self.repository.get_public_by_id(report_id)
        if not report:
            raise ReportConfigurationNotFoundError(f"Public report {report_id} not found")
        return report


class UpdateReportConfigurationUseCase:
    def __init__(self, repository: ReportConfigurationRepository):
        self.repository = repository

    def execute(self, report: ReportConfiguration, owner_id: int) -> ReportConfiguration:
        existing = self.repository.get_by_id(report.workspace_id, report.id)
        if not existing:
            raise ReportConfigurationNotFoundError(f"Report {report.id} not found")
        return self.repository.update(report, owner_id)


class DeleteReportConfigurationUseCase:
    def __init__(self, repository: ReportConfigurationRepository):
        self.repository = repository

    def execute(self, workspace_id: int, report_id: int, owner_id: int) -> None:
        existing = self.repository.get_by_id(workspace_id, report_id)
        if not existing:
            raise ReportConfigurationNotFoundError(f"Report {report_id} not found")
        self.repository.delete(workspace_id, report_id, owner_id)
