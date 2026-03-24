from dataclasses import dataclass, field
from typing import Any


PromptVariableValue = str | int | float | bool | None


@dataclass(frozen=True)
class PromptTemplateMessage:
    role: str
    template: str


@dataclass(frozen=True)
class PromptTemplate:
    name: str | None
    messages: list[PromptTemplateMessage]
    variables: dict[str, PromptVariableValue] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderedPromptMessage:
    role: str
    content: str


@dataclass(frozen=True)
class RenderedPromptTemplate:
    name: str | None
    placeholders: list[str]
    variables: dict[str, PromptVariableValue]
    messages: list[RenderedPromptMessage]


@dataclass(frozen=True)
class DeepSeekGenerationOptions:
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class DeepSeekUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class DeepSeekCompletion:
    content: str
    model: str
    finish_reason: str | None = None
    request_id: str | None = None
    usage: DeepSeekUsage | None = None
    raw_response: dict[str, Any] | None = None
