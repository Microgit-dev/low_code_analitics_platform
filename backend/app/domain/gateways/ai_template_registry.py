from abc import ABC, abstractmethod

from app.domain.entities.ai_template import AITemplateDefinition, AITemplatePreparedPrompt


class AITemplateNotFoundError(Exception):
    pass


class AITemplateValidationError(Exception):
    pass


class AITemplateRegistry(ABC):
    @abstractmethod
    def list_templates(self) -> list[AITemplateDefinition]:
        raise NotImplementedError

    @abstractmethod
    def prepare_prompt(self, template_id: str, input_data: dict) -> AITemplatePreparedPrompt:
        raise NotImplementedError
