import httpx

from app.config import settings
from app.domain.entities.prompt_template import (
    DeepSeekCompletion,
    DeepSeekGenerationOptions,
    DeepSeekUsage,
    RenderedPromptMessage,
)
from app.domain.gateways.deepseek_gateway import DeepSeekGateway, DeepSeekGatewayError


class DeepSeekApiClient(DeepSeekGateway):
    def __init__(self) -> None:
        self.base_url = settings.deepseek_api_base_url.rstrip("/")
        self.api_key = settings.deepseek_api_key
        self.default_model = settings.deepseek_default_model
        self.timeout_seconds = settings.deepseek_timeout_seconds

    def generate(
        self,
        messages: list[RenderedPromptMessage],
        options: DeepSeekGenerationOptions,
    ) -> DeepSeekCompletion:
        if not self.api_key:
            raise DeepSeekGatewayError("DeepSeek API key is not configured")

        payload: dict[str, object] = {
            "model": options.model or self.default_model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "stream": False,
        }
        if options.temperature is not None:
            payload["temperature"] = options.temperature
        if options.max_tokens is not None:
            payload["max_tokens"] = options.max_tokens

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            raise DeepSeekGatewayError(f"DeepSeek API returned status {exc.response.status_code}: {detail}") from exc
        except httpx.RequestError as exc:
            raise DeepSeekGatewayError(f"Cannot reach DeepSeek API: {exc}") from exc

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise DeepSeekGatewayError("DeepSeek API returned no choices")

        first_choice = choices[0]
        message = first_choice.get("message") or {}
        usage_payload = data.get("usage") or {}

        return DeepSeekCompletion(
            content=message.get("content", ""),
            model=data.get("model", payload["model"]),
            finish_reason=first_choice.get("finish_reason"),
            request_id=data.get("id"),
            usage=DeepSeekUsage(
                prompt_tokens=usage_payload.get("prompt_tokens"),
                completion_tokens=usage_payload.get("completion_tokens"),
                total_tokens=usage_payload.get("total_tokens"),
            ),
            raw_response=data,
        )
