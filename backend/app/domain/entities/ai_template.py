from dataclasses import dataclass, field
from typing import Any

from app.domain.entities.prompt_template import PromptTemplate


@dataclass(frozen=True)
class AITemplateFieldDefinition:
    name: str
    type: str
    required: bool
    description: str


@dataclass(frozen=True)
class AITemplateDefinition:
    template_id: str
    name: str
    description: str
    input_fields: list[AITemplateFieldDefinition] = field(default_factory=list)
    default_model: str | None = None


@dataclass(frozen=True)
class AITemplateExecutionRequest:
    template_id: str
    input_data: dict[str, Any]


@dataclass(frozen=True)
class AITemplatePreparedPrompt:
    definition: AITemplateDefinition
    template: PromptTemplate
    normalized_input: dict[str, Any]
