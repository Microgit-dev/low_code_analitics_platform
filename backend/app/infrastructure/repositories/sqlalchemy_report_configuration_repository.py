from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.report_configuration import ReportConfiguration
from app.domain.repositories.report_configuration_repository import ReportConfigurationRepository
from app.infrastructure.db.models.report_configuration_model import ReportConfigurationModel
from app.infrastructure.db.models.workspace_model import WorkspaceModel


class SQLAlchemyReportConfigurationRepository(ReportConfigurationRepository):
    def __init__(self, session: Session):
        self.session = session

    def _workspace_belongs_to_owner(self, workspace_id: int, owner_id: int) -> bool:
        stmt = select(WorkspaceModel).where(
            WorkspaceModel.id == workspace_id,
            WorkspaceModel.owner_id == owner_id,
        )
        return self.session.execute(stmt).scalar() is not None

    def list_by_workspace(self, workspace_id: int) -> list[ReportConfiguration]:
        stmt = select(ReportConfigurationModel).where(ReportConfigurationModel.workspace_id == workspace_id)
        rows = self.session.execute(stmt).scalars().all()
        return [self._to_entity(row) for row in rows]

    def get_by_id(self, workspace_id: int, report_id: int) -> ReportConfiguration | None:
        stmt = select(ReportConfigurationModel).where(
            ReportConfigurationModel.id == report_id,
            ReportConfigurationModel.workspace_id == workspace_id,
        )
        row = self.session.execute(stmt).scalar()
        if not row:
            return None
        return self._to_entity(row)

    def get_public_by_id(self, report_id: int) -> ReportConfiguration | None:
        stmt = select(ReportConfigurationModel).where(
            ReportConfigurationModel.id == report_id,
            ReportConfigurationModel.is_published.is_(True),
        )
        row = self.session.execute(stmt).scalar()
        if not row:
            return None
        return self._to_entity(row)

    def create(self, report: ReportConfiguration, owner_id: int) -> ReportConfiguration:
        if not self._workspace_belongs_to_owner(report.workspace_id, owner_id):
            raise PermissionError("Workspace does not belong to this user")

        db_report = ReportConfigurationModel(
            workspace_id=report.workspace_id,
            name=report.name,
            description=report.description,
            report_type=report.report_type,
            settings_json=deepcopy(report.settings),
            is_published=report.is_published,
        )
        self.session.add(db_report)
        self.session.commit()
        self.session.refresh(db_report)
        return self._to_entity(db_report)

    def update(self, report: ReportConfiguration, owner_id: int) -> ReportConfiguration:
        if not self._workspace_belongs_to_owner(report.workspace_id, owner_id):
            raise PermissionError("Workspace does not belong to this user")

        db_report = self.session.execute(
            select(ReportConfigurationModel).where(ReportConfigurationModel.id == report.id)
        ).scalar()
        if not db_report:
            raise ValueError(f"Report {report.id} not found")

        db_report.name = report.name
        db_report.description = report.description
        db_report.report_type = report.report_type
        db_report.settings_json = deepcopy(report.settings)
        db_report.is_published = report.is_published

        self.session.commit()
        self.session.refresh(db_report)
        return self._to_entity(db_report)

    def delete(self, workspace_id: int, report_id: int, owner_id: int) -> None:
        if not self._workspace_belongs_to_owner(workspace_id, owner_id):
            raise PermissionError("Workspace does not belong to this user")

        db_report = self.session.execute(
            select(ReportConfigurationModel).where(
                ReportConfigurationModel.id == report_id,
                ReportConfigurationModel.workspace_id == workspace_id,
            )
        ).scalar()
        if not db_report:
            raise ValueError(f"Report {report_id} not found")

        self.session.delete(db_report)
        self.session.commit()

    @staticmethod
    def _to_entity(model: ReportConfigurationModel) -> ReportConfiguration:
        return ReportConfiguration(
            id=model.id,
            workspace_id=model.workspace_id,
            name=model.name,
            description=model.description,
            report_type=model.report_type,
            settings=deepcopy(model.settings_json),
            is_published=model.is_published,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
