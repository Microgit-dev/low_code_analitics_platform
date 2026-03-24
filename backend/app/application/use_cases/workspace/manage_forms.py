from typing import List, Optional

from app.domain.entities.form_configuration import FormConfiguration
from app.domain.repositories.form_configuration_repository import FormConfigurationRepository


class FormConfigurationNotFoundError(Exception):
    pass


class CreateFormConfigurationUseCase:
    def __init__(self, repository: FormConfigurationRepository):
        self.repository = repository

    def execute(self, form: FormConfiguration, owner_id: int) -> FormConfiguration:
        return self.repository.create(form, owner_id)


class ListFormConfigurationsUseCase:
    def __init__(self, repository: FormConfigurationRepository):
        self.repository = repository

    def execute(self, workspace_id: int, table_id: int) -> List[FormConfiguration]:
        return self.repository.list_by_table(workspace_id, table_id)


class GetFormConfigurationUseCase:
    def __init__(self, repository: FormConfigurationRepository):
        self.repository = repository

    def execute(self, workspace_id: int, form_id: int) -> FormConfiguration:
        form = self.repository.get_by_id(workspace_id, form_id)
        if not form:
            raise FormConfigurationNotFoundError(f"Form {form_id} not found")
        return form


class UpdateFormConfigurationUseCase:
    def __init__(self, repository: FormConfigurationRepository):
        self.repository = repository

    def execute(self, form: FormConfiguration, owner_id: int) -> FormConfiguration:
        # Verify form exists first
        existing = self.repository.get_by_id(form.workspace_id, form.id)
        if not existing:
            raise FormConfigurationNotFoundError(f"Form {form.id} not found")
        return self.repository.update(form, owner_id)


class DeleteFormConfigurationUseCase:
    def __init__(self, repository: FormConfigurationRepository):
        self.repository = repository

    def execute(self, workspace_id: int, form_id: int, owner_id: int) -> None:
        # Verify form exists first
        form = self.repository.get_by_id(workspace_id, form_id)
        if not form:
            raise FormConfigurationNotFoundError(f"Form {form_id} not found")
        self.repository.delete(workspace_id, form_id, owner_id)
