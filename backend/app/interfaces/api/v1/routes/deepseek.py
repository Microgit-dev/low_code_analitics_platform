from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.prompt_template_renderer import MissingTemplateVariablesError, PromptTemplateRenderer
from app.application.use_cases.deepseek.execute_ai_template import ExecuteAITemplateUseCase, ListAITemplatesUseCase
from app.application.use_cases.deepseek.run_prompt_template import (
    GenerateDeepSeekResponseUseCase,
    RenderPromptTemplateUseCase,
)
from app.domain.entities.ai_template import AITemplateDefinition
from app.domain.entities.prompt_template import (
    DeepSeekGenerationOptions,
    PromptTemplate,
    PromptTemplateMessage,
    RenderedPromptTemplate,
)
from app.domain.gateways.ai_template_registry import AITemplateNotFoundError, AITemplateValidationError
from app.domain.entities.user import User
from app.domain.gateways.deepseek_gateway import DeepSeekGatewayError
from app.infrastructure.clients.deepseek_api_client import DeepSeekApiClient
from app.infrastructure.templates.deepseek_template_registry import InMemoryAITemplateRegistry
from app.interfaces.api.dependencies.auth import get_current_user
from app.interfaces.api.v1.schemas.deepseek import (
    AITemplateDefinitionResponse,
    AITemplateExecuteRequest,
    AITemplateExecuteResponse,
    AITemplateFieldResponse,
    DeepSeekPromptTemplateRequest,
    DeepSeekPromptTemplateResponse,
    DeepSeekUsageResponse,
    PromptTemplateRenderRequest,
    PromptTemplateRenderResponse,
    RenderedPromptMessageResponse,
)


router = APIRouter(prefix="/ai/deepseek", tags=["DeepSeek"])


def _map_request_to_template(payload: PromptTemplateRenderRequest) -> PromptTemplate:
    return PromptTemplate(
        name=payload.template_name,
        messages=[PromptTemplateMessage(role=message.role, template=message.template) for message in payload.messages],
        variables=payload.variables,
    )


def _map_rendered(rendered: RenderedPromptTemplate) -> PromptTemplateRenderResponse:
    return PromptTemplateRenderResponse(
        template_name=rendered.name,
        placeholders=rendered.placeholders,
        variables=rendered.variables,
        messages=[RenderedPromptMessageResponse(role=message.role, content=message.content) for message in rendered.messages],
    )


def _map_template_definition(definition: AITemplateDefinition) -> AITemplateDefinitionResponse:
    return AITemplateDefinitionResponse(
        template_id=definition.template_id,
        name=definition.name,
        description=definition.description,
        input_fields=[
            AITemplateFieldResponse(
                name=field.name,
                type=field.type,
                required=field.required,
                description=field.description,
            )
            for field in definition.input_fields
        ],
        default_model=definition.default_model,
    )


@router.get("/templates", response_model=list[AITemplateDefinitionResponse])
def list_ai_templates(
    current_user: User = Depends(get_current_user),
) -> list[AITemplateDefinitionResponse]:
    _ = current_user
    use_case = ListAITemplatesUseCase(InMemoryAITemplateRegistry())
    return [_map_template_definition(item) for item in use_case.execute()]


@router.post("/templates/{template_id}/execute", response_model=AITemplateExecuteResponse)
def execute_ai_template(
    template_id: str,
    payload: AITemplateExecuteRequest,
    current_user: User = Depends(get_current_user),
) -> AITemplateExecuteResponse:
    _ = current_user
    registry = InMemoryAITemplateRegistry()
    use_case = ExecuteAITemplateUseCase(registry, PromptTemplateRenderer(), DeepSeekApiClient())
    definition = next((item for item in registry.list_templates() if item.template_id == template_id), None)

    try:
        if definition is None:
            raise AITemplateNotFoundError(f"AI template '{template_id}' not found")
        prepared, completion = use_case.execute(
            template_id=template_id,
            input_data=payload.input,
            options=DeepSeekGenerationOptions(
                model=payload.model or definition.default_model,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            ),
        )
    except AITemplateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except AITemplateValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except MissingTemplateVariablesError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except DeepSeekGatewayError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return AITemplateExecuteResponse(
        template_id=prepared.definition.template_id,
        template_name=prepared.definition.name,
        normalized_input=prepared.normalized_input,
        model=completion.model,
        finish_reason=completion.finish_reason,
        request_id=completion.request_id,
        content=completion.content,
        usage=(
            DeepSeekUsageResponse(
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
                total_tokens=completion.usage.total_tokens,
            )
            if completion.usage
            else None
        ),
    )


@router.post("/render", response_model=PromptTemplateRenderResponse)
def render_prompt_template(
    payload: PromptTemplateRenderRequest,
    current_user: User = Depends(get_current_user),
) -> PromptTemplateRenderResponse:
    _ = current_user
    use_case = RenderPromptTemplateUseCase(PromptTemplateRenderer())

    try:
        rendered = use_case.execute(_map_request_to_template(payload))
    except MissingTemplateVariablesError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return _map_rendered(rendered)


@router.post("/generate", response_model=DeepSeekPromptTemplateResponse)
def generate_with_prompt_template(
    payload: DeepSeekPromptTemplateRequest,
    current_user: User = Depends(get_current_user),
) -> DeepSeekPromptTemplateResponse:
    _ = current_user
    use_case = GenerateDeepSeekResponseUseCase(PromptTemplateRenderer(), DeepSeekApiClient())

    try:
        rendered, completion = use_case.execute(
            template=_map_request_to_template(payload),
            options=DeepSeekGenerationOptions(
                model=payload.model,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            ),
        )
    except MissingTemplateVariablesError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except DeepSeekGatewayError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return DeepSeekPromptTemplateResponse(
        **_map_rendered(rendered).model_dump(),
        model=completion.model,
        finish_reason=completion.finish_reason,
        request_id=completion.request_id,
        content=completion.content,
        usage=(
            DeepSeekUsageResponse(
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
                total_tokens=completion.usage.total_tokens,
            )
            if completion.usage
            else None
        ),
    )
