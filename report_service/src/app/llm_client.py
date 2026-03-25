from __future__ import annotations
import logging
import requests
from typing import Optional

from .config import settings

logger = logging.getLogger(__name__)

class LLMError(Exception):
    pass

class DeepSeekClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = (base_url or settings.deepseek_api_base_url).rstrip('/')
        self.model = model or settings.deepseek_default_model
        self.timeout = settings.deepseek_timeout_seconds

    def generate_text(self, prompt: str) -> str:
        if not self.api_key:
            raise LLMError("DEEPSEEK_API_KEY не задан.")
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Отвечай только требуемым форматом. Без пояснений."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": 2048,
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        except Exception as e:
            raise LLMError(f"Ошибка запроса к DeepSeek: {e}")
        if resp.status_code >= 300:
            raise LLMError(f"DeepSeek вернул {resp.status_code}: {resp.text}")
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise LLMError(f"Неверный формат ответа DeepSeek: {e}")
        return content
