from app.application.services.prompt_template_renderer import PromptTemplateRenderer
from app.domain.entities.prompt_template import (
    DeepSeekCompletion,
    DeepSeekGenerationOptions,
    PromptTemplate,
    RenderedPromptTemplate,
)
from app.domain.gateways.deepseek_gateway import DeepSeekGateway


class RenderPromptTemplateUseCase:
    def __init__(self, renderer: PromptTemplateRenderer) -> None:
        self.renderer = renderer

    def execute(self, template: PromptTemplate) -> RenderedPromptTemplate:
        return self.renderer.render(template)


class GenerateDeepSeekResponseUseCase:
    def __init__(self, renderer: PromptTemplateRenderer, gateway: DeepSeekGateway) -> None:
        self.renderer = renderer
        self.gateway = gateway

    def execute(
        self,
        template: PromptTemplate,
        options: DeepSeekGenerationOptions,
    ) -> tuple[RenderedPromptTemplate, DeepSeekCompletion]:
        rendered = self.renderer.render(template)
        completion = self.gateway.generate(rendered.messages, options)
        return rendered, completion
