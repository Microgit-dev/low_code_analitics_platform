from typing import Any

from app.config import settings
from app.domain.entities.ai_template import (
    AITemplateDefinition,
    AITemplateFieldDefinition,
    AITemplatePreparedPrompt,
)
from app.domain.entities.prompt_template import PromptTemplate, PromptTemplateMessage
from app.domain.gateways.ai_template_registry import (
    AITemplateNotFoundError,
    AITemplateRegistry,
    AITemplateValidationError,
)


class InMemoryAITemplateRegistry(AITemplateRegistry):
    def __init__(self) -> None:
        self._definitions = {
            definition.template_id: definition
            for definition in [
                AITemplateDefinition(
                    template_id="table_structure_from_description",
                    name="Создание структуры таблицы по описанию",
                    description="Генерирует JSON структуры таблицы для low-code платформы по текстовому описанию.",
                    input_fields=[
                        AITemplateFieldDefinition(
                            name="description",
                            type="string",
                            required=True,
                            description="Описание бизнес-сущности и нужных полей таблицы.",
                        ),
                        AITemplateFieldDefinition(
                            name="table_name",
                            type="string",
                            required=False,
                            description="Желаемое название таблицы, если оно уже известно.",
                        ),
                        AITemplateFieldDefinition(
                            name="workspace_context",
                            type="string",
                            required=False,
                            description="Контекст workspace, предметной области или процесса.",
                        ),
                        AITemplateFieldDefinition(
                            name="constraints",
                            type="string",
                            required=False,
                            description="Дополнительные ограничения по колонкам, типам и правилам.",
                        ),
                    ],
                    default_model=settings.deepseek_default_model,
                ),
                AITemplateDefinition(
                    template_id="document_template_fill",
                    name="Заполнение шаблона документа",
                    description="Заполняет шаблон документа на основе контекста и возвращает готовый текст.",
                    input_fields=[
                        AITemplateFieldDefinition(
                            name="document_template",
                            type="string",
                            required=True,
                            description="Черновик документа или шаблон с разделами и маркерами.",
                        ),
                        AITemplateFieldDefinition(
                            name="context",
                            type="string",
                            required=True,
                            description="Фактические данные, которыми нужно заполнить документ.",
                        ),
                        AITemplateFieldDefinition(
                            name="instructions",
                            type="string",
                            required=False,
                            description="Стиль, ограничения и пожелания к результату.",
                        ),
                        AITemplateFieldDefinition(
                            name="output_format",
                            type="string",
                            required=False,
                            description="Ожидаемый формат результата: plain_text, markdown, json.",
                        ),
                    ],
                    default_model=settings.deepseek_default_model,
                ),
            ]
        }

    def list_templates(self) -> list[AITemplateDefinition]:
        return list(self._definitions.values())

    def prepare_prompt(self, template_id: str, input_data: dict) -> AITemplatePreparedPrompt:
        definition = self._definitions.get(template_id)
        if definition is None:
            raise AITemplateNotFoundError(f"AI template '{template_id}' not found")

        normalized_input = self._normalize_input(definition, input_data)
        if template_id == "table_structure_from_description":
            return AITemplatePreparedPrompt(
                definition=definition,
                template=self._build_table_structure_prompt(definition, normalized_input),
                normalized_input=normalized_input,
            )

        if template_id == "document_template_fill":
            return AITemplatePreparedPrompt(
                definition=definition,
                template=self._build_document_fill_prompt(definition, normalized_input),
                normalized_input=normalized_input,
            )

        raise AITemplateNotFoundError(f"AI template '{template_id}' is not implemented")

    def _normalize_input(self, definition: AITemplateDefinition, input_data: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for field in definition.input_fields:
            value = input_data.get(field.name)
            if field.required and (value is None or (isinstance(value, str) and not value.strip())):
                raise AITemplateValidationError(f"Field '{field.name}' is required")
            normalized[field.name] = value.strip() if isinstance(value, str) else value
        return normalized

    def _build_table_structure_prompt(
        self,
        definition: AITemplateDefinition,
        input_data: dict[str, Any],
    ) -> PromptTemplate:
        table_name = input_data.get("table_name") or "Новая таблица"
        workspace_context = input_data.get("workspace_context") or "Контекст не указан"
        constraints = input_data.get("constraints") or "Дополнительных ограничений нет"

        system_prompt = (
            "Ты проектируешь структуру таблиц для low-code аналитической платформы. "
            "Верни только JSON без пояснений. "
            "Структура JSON должна строго соответствовать формату: "
            "{\"name\": string, \"description\": string|null, \"columns\": ["
            "{\"key\": string, \"name\": string, \"type\": \"text|number|boolean|date|datetime|enum|list|geoPoint|geoPolygon\", "
            "\"required\": boolean, \"settings\": object}"
            "]}. "
            "Для enum используй settings.options как массив строк. "
            "Для list используй settings.itemType и при itemType=enum добавляй settings.options. "
            "Для geoPoint и geoPolygon используй settings.srid."
        )
        user_prompt = (
            "Сгенерируй структуру таблицы.\n"
            f"Желаемое название таблицы: {table_name}\n"
            f"Описание задачи: {input_data['description']}\n"
            f"Контекст workspace: {workspace_context}\n"
            f"Ограничения: {constraints}\n"
            "Сделай практичную структуру для реального продукта. "
            "Ключи колонок делай в snake_case на латинице."
        )
        return PromptTemplate(
            name=definition.name,
            messages=[
                PromptTemplateMessage(role="system", template=system_prompt),
                PromptTemplateMessage(role="user", template=user_prompt),
            ],
            variables={},
        )

    def _build_document_fill_prompt(
        self,
        definition: AITemplateDefinition,
        input_data: dict[str, Any],
    ) -> PromptTemplate:
        instructions = input_data.get("instructions") or "Сохраняй деловой, ясный и связный стиль."
        output_format = input_data.get("output_format") or "plain_text"

        system_prompt = (
            "Ты помощник по подготовке документов. "
            "Твоя задача: аккуратно заполнить шаблон документа фактами из контекста. "
            "Если данных не хватает, не выдумывай факты: обозначай пропуски как [НУЖНО УТОЧНЕНИЕ]."
        )
        user_prompt = (
            "Заполни шаблон документа.\n"
            f"Требуемый формат результата: {output_format}\n"
            f"Инструкции: {instructions}\n\n"
            "Шаблон документа:\n"
            f"{input_data['document_template']}\n\n"
            "Контекст для заполнения:\n"
            f"{input_data['context']}\n\n"
            "Верни только готовый результат без вступления."
        )
        return PromptTemplate(
            name=definition.name,
            messages=[
                PromptTemplateMessage(role="system", template=system_prompt),
                PromptTemplateMessage(role="user", template=user_prompt),
            ],
            variables={},
        )
