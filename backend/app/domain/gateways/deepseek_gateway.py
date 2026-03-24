from abc import ABC, abstractmethod

from app.domain.entities.prompt_template import DeepSeekCompletion, DeepSeekGenerationOptions, RenderedPromptMessage


class DeepSeekGatewayError(Exception):
    pass


class DeepSeekGateway(ABC):
    @abstractmethod
    def generate(
        self,
        messages: list[RenderedPromptMessage],
        options: DeepSeekGenerationOptions,
    ) -> DeepSeekCompletion:
        raise NotImplementedError
