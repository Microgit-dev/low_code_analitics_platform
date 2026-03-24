from app.application.services.prompt_template_renderer import PromptTemplateRenderer
from app.domain.entities.ai_template import AITemplateDefinition, AITemplatePreparedPrompt
from app.domain.entities.prompt_template import DeepSeekCompletion, DeepSeekGenerationOptions
from app.domain.gateways.ai_template_registry import AITemplateRegistry
from app.domain.gateways.deepseek_gateway import DeepSeekGateway


class ListAITemplatesUseCase:
    def __init__(self, registry: AITemplateRegistry) -> None:
        self.registry = registry

    def execute(self) -> list[AITemplateDefinition]:
        return self.registry.list_templates()


class PrepareAITemplateUseCase:
    def __init__(self, registry: AITemplateRegistry, renderer: PromptTemplateRenderer) -> None:
        self.registry = registry
        self.renderer = renderer

    def execute(self, template_id: str, input_data: dict) -> AITemplatePreparedPrompt:
        prepared = self.registry.prepare_prompt(template_id, input_data)
        rendered = self.renderer.render(prepared.template)
        return AITemplatePreparedPrompt(
            definition=prepared.definition,
            template=prepared.template,
            normalized_input=prepared.normalized_input | {"rendered_messages": rendered.messages},
        )


class ExecuteAITemplateUseCase:
    def __init__(
        self,
        registry: AITemplateRegistry,
        renderer: PromptTemplateRenderer,
        gateway: DeepSeekGateway,
    ) -> None:
        self.registry = registry
        self.renderer = renderer
        self.gateway = gateway

    def execute(
        self,
        template_id: str,
        input_data: dict,
        options: DeepSeekGenerationOptions,
    ) -> tuple[AITemplatePreparedPrompt, DeepSeekCompletion]:
        prepared = self.registry.prepare_prompt(template_id, input_data)
        rendered = self.renderer.render(prepared.template)
        completion = self.gateway.generate(rendered.messages, options)
        return prepared, completion
