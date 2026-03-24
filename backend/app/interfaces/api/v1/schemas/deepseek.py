from pydantic import BaseModel, Field


class PromptTemplateMessageRequest(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    template: str = Field(min_length=1, max_length=20000)


class PromptTemplateRenderRequest(BaseModel):
    template_name: str | None = Field(default=None, max_length=255)
    messages: list[PromptTemplateMessageRequest] = Field(min_length=1)
    variables: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class DeepSeekPromptTemplateRequest(PromptTemplateRenderRequest):
    model: str | None = Field(default=None, max_length=100)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)


class RenderedPromptMessageResponse(BaseModel):
    role: str
    content: str


class PromptTemplateRenderResponse(BaseModel):
    template_name: str | None = None
    placeholders: list[str]
    variables: dict[str, str | int | float | bool | None]
    messages: list[RenderedPromptMessageResponse]


class DeepSeekUsageResponse(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class DeepSeekPromptTemplateResponse(PromptTemplateRenderResponse):
    model: str
    finish_reason: str | None = None
    request_id: str | None = None
    content: str
    usage: DeepSeekUsageResponse | None = None


class AITemplateFieldResponse(BaseModel):
    name: str
    type: str
    required: bool
    description: str


class AITemplateDefinitionResponse(BaseModel):
    template_id: str
    name: str
    description: str
    input_fields: list[AITemplateFieldResponse]
    default_model: str | None = None


class AITemplateExecuteRequest(BaseModel):
    input: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    model: str | None = Field(default=None, max_length=100)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)


class AITemplateExecuteResponse(BaseModel):
    template_id: str
    template_name: str
    normalized_input: dict[str, str | int | float | bool | None]
    model: str
    finish_reason: str | None = None
    request_id: str | None = None
    content: str
    usage: DeepSeekUsageResponse | None = None
