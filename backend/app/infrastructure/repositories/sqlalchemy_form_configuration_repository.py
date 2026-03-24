from copy import deepcopy
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities.form_configuration import FormConfiguration, FormField
from app.domain.entities.table_data_record import TableDataRecord
from app.domain.repositories.form_configuration_repository import (
    FormConfigurationRepository,
    TableDataRecordRepository,
)
from app.infrastructure.db.models.form_configuration_model import FormConfigurationModel
from app.infrastructure.db.models.table_data_record_model import TableDataRecordModel
from app.infrastructure.db.models.workspace_model import WorkspaceModel


class SQLAlchemyFormConfigurationRepository(FormConfigurationRepository):
    """Реализация репозитория форм с SQLAlchemy"""

    def __init__(self, session: Session):
        self.session = session

    def _workspace_belongs_to_owner(self, workspace_id: int, owner_id: int) -> bool:
        stmt = select(WorkspaceModel).where(
            WorkspaceModel.id == workspace_id, WorkspaceModel.owner_id == owner_id
        )
        return self.session.execute(stmt).scalar() is not None

    def list_by_table(self, workspace_id: int, table_id: Optional[int] = None) -> List[FormConfiguration]:
        stmt = select(FormConfigurationModel).where(FormConfigurationModel.workspace_id == workspace_id)
        if table_id is not None:
            stmt = stmt.where(FormConfigurationModel.table_id == table_id)
        forms = self.session.execute(stmt).scalars().all()

        return [
            FormConfiguration(
                id=form.id,
                workspace_id=form.workspace_id,
                table_id=form.table_id,
                name=form.name,
                description=form.description,
                fields=[
                    FormField(
                        table_id=f.get("table_id"),
                        column_key=f["column_key"],
                        column_name=f["column_name"],
                        field_label=f["field_label"],
                        widget_type=f["widget_type"],
                        required=f.get("required", True),
                        placeholder=f.get("placeholder"),
                        help_text=f.get("help_text"),
                        auto_generate_id=f.get("auto_generate_id", False),
                        widget_settings=f.get("widget_settings", {}),
                    )
                    for f in form.fields_json
                ],
                is_published=form.is_published,
                collect_email=form.collect_email,
                created_at=form.created_at,
                updated_at=form.updated_at,
            )
            for form in forms
        ]

    def get_by_id(self, workspace_id: int, form_id: int) -> Optional[FormConfiguration]:
        stmt = select(FormConfigurationModel).where(
            FormConfigurationModel.id == form_id, FormConfigurationModel.workspace_id == workspace_id
        )
        form = self.session.execute(stmt).scalar()

        if not form:
            return None

        return FormConfiguration(
            id=form.id,
            workspace_id=form.workspace_id,
            table_id=form.table_id,
            name=form.name,
            description=form.description,
            fields=[
                FormField(
                    table_id=f.get("table_id"),
                    column_key=f["column_key"],
                    column_name=f["column_name"],
                    field_label=f["field_label"],
                    widget_type=f["widget_type"],
                    required=f.get("required", True),
                    placeholder=f.get("placeholder"),
                    help_text=f.get("help_text"),
                    auto_generate_id=f.get("auto_generate_id", False),
                    widget_settings=f.get("widget_settings", {}),
                )
                for f in form.fields_json
            ],
            is_published=form.is_published,
            collect_email=form.collect_email,
            created_at=form.created_at,
            updated_at=form.updated_at,
        )

    def create(self, form: FormConfiguration, owner_id: int) -> FormConfiguration:
        if not self._workspace_belongs_to_owner(form.workspace_id, owner_id):
            raise PermissionError("Workspace does not belong to this user")

        db_form = FormConfigurationModel(
            workspace_id=form.workspace_id,
            table_id=form.table_id,
            name=form.name,
            description=form.description,
            fields_json=[
                {
                    "table_id": f.table_id,
                    "column_key": f.column_key,
                    "column_name": f.column_name,
                    "field_label": f.field_label,
                    "widget_type": f.widget_type,
                    "required": f.required,
                    "placeholder": f.placeholder,
                    "help_text": f.help_text,
                    "auto_generate_id": f.auto_generate_id,
                    "widget_settings": f.widget_settings,
                }
                for f in form.fields
            ],
            is_published=form.is_published,
            collect_email=form.collect_email,
        )
        self.session.add(db_form)
        self.session.commit()
        self.session.refresh(db_form)

        form.id = db_form.id
        form.created_at = db_form.created_at
        form.updated_at = db_form.updated_at
        return form

    def update(self, form: FormConfiguration, owner_id: int) -> FormConfiguration:
        if not self._workspace_belongs_to_owner(form.workspace_id, owner_id):
            raise PermissionError("Workspace does not belong to this user")

        db_form = self.session.execute(
            select(FormConfigurationModel).where(FormConfigurationModel.id == form.id)
        ).scalar()

        if not db_form:
            raise ValueError(f"Form {form.id} not found")

        db_form.name = form.name
        db_form.description = form.description
        db_form.fields_json = [
            {
                "table_id": f.table_id,
                "column_key": f.column_key,
                "column_name": f.column_name,
                "field_label": f.field_label,
                "widget_type": f.widget_type,
                "required": f.required,
                "placeholder": f.placeholder,
                "help_text": f.help_text,
                "auto_generate_id": f.auto_generate_id,
                "widget_settings": f.widget_settings,
            }
            for f in form.fields
        ]
        db_form.is_published = form.is_published
        db_form.collect_email = form.collect_email
        self.session.commit()
        self.session.refresh(db_form)

        form.created_at = db_form.created_at
        form.updated_at = db_form.updated_at
        return form

    def delete(self, workspace_id: int, form_id: int, owner_id: int) -> None:
        if not self._workspace_belongs_to_owner(workspace_id, owner_id):
            raise PermissionError("Workspace does not belong to this user")

        db_form = self.session.execute(
            select(FormConfigurationModel).where(
                FormConfigurationModel.id == form_id, FormConfigurationModel.workspace_id == workspace_id
            )
        ).scalar()

        if not db_form:
            raise ValueError(f"Form {form_id} not found")

        self.session.delete(db_form)
        self.session.commit()


class SQLAlchemyTableDataRecordRepository(TableDataRecordRepository):
    """Реализация репозитория записей данных с SQLAlchemy"""

    def __init__(self, session: Session):
        self.session = session

    def _workspace_belongs_to_owner(self, workspace_id: int, owner_id: int) -> bool:
        stmt = select(WorkspaceModel).where(
            WorkspaceModel.id == workspace_id, WorkspaceModel.owner_id == owner_id
        )
        return self.session.execute(stmt).scalar() is not None

    def list_by_table(
        self, workspace_id: int, table_id: int, skip: int = 0, limit: int = 50
    ) -> tuple[List[TableDataRecord], int]:
        # Общее количество
        count_stmt = select(func.count()).select_from(TableDataRecordModel).where(
            TableDataRecordModel.workspace_id == workspace_id, TableDataRecordModel.table_id == table_id
        )
        total = self.session.execute(count_stmt).scalar() or 0

        # Получи записи с пагинацией
        stmt = (
            select(TableDataRecordModel)
            .where(
                TableDataRecordModel.workspace_id == workspace_id,
                TableDataRecordModel.table_id == table_id,
            )
            .order_by(TableDataRecordModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        records = self.session.execute(stmt).scalars().all()

        return (
            [
                TableDataRecord(
                    id=r.id,
                    workspace_id=r.workspace_id,
                    table_id=r.table_id,
                    data=deepcopy(r.data_json),
                    submitter_email=r.submitter_email,
                    submitted_at=r.submitted_at,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in records
            ],
            total,
        )

    def get_by_id(self, workspace_id: int, record_id: int) -> Optional[TableDataRecord]:
        stmt = select(TableDataRecordModel).where(
            TableDataRecordModel.id == record_id, TableDataRecordModel.workspace_id == workspace_id
        )
        record = self.session.execute(stmt).scalar()

        if not record:
            return None

        return TableDataRecord(
            id=record.id,
            workspace_id=record.workspace_id,
            table_id=record.table_id,
            data=deepcopy(record.data_json),
            submitter_email=record.submitter_email,
            submitted_at=record.submitted_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def create_from_form(
        self, workspace_id: int, table_id: int, data: dict, submitter_email: Optional[str] = None
    ) -> TableDataRecord:
        # Не проверяем owner здесь, т.к. это публичный endpoint
        db_record = TableDataRecordModel(
            workspace_id=workspace_id,
            table_id=table_id,
            data_json=deepcopy(data),
            submitter_email=submitter_email,
            submitted_at=func.now(),
        )
        self.session.add(db_record)
        self.session.commit()
        self.session.refresh(db_record)

        return TableDataRecord(
            id=db_record.id,
            workspace_id=db_record.workspace_id,
            table_id=db_record.table_id,
            data=deepcopy(db_record.data_json),
            submitter_email=db_record.submitter_email,
            submitted_at=db_record.submitted_at,
            created_at=db_record.created_at,
            updated_at=db_record.updated_at,
        )

    def update(self, record: TableDataRecord, owner_id: int) -> TableDataRecord:
        if not self._workspace_belongs_to_owner(record.workspace_id, owner_id):
            raise PermissionError("Workspace does not belong to this user")

        db_record = self.session.execute(
            select(TableDataRecordModel).where(TableDataRecordModel.id == record.id)
        ).scalar()

        if not db_record:
            raise ValueError(f"Record {record.id} not found")

        db_record.data_json = deepcopy(record.data)
        self.session.commit()
        self.session.refresh(db_record)

        return TableDataRecord(
            id=db_record.id,
            workspace_id=db_record.workspace_id,
            table_id=db_record.table_id,
            data=deepcopy(db_record.data_json),
            submitter_email=db_record.submitter_email,
            submitted_at=db_record.submitted_at,
            created_at=db_record.created_at,
            updated_at=db_record.updated_at,
        )

    def delete(self, workspace_id: int, record_id: int, owner_id: int) -> None:
        if not self._workspace_belongs_to_owner(workspace_id, owner_id):
            raise PermissionError("Workspace does not belong to this user")

        db_record = self.session.execute(
            select(TableDataRecordModel).where(
                TableDataRecordModel.id == record_id, TableDataRecordModel.workspace_id == workspace_id
            )
        ).scalar()

        if not db_record:
            raise ValueError(f"Record {record_id} not found")

        self.session.delete(db_record)
        self.session.commit()
