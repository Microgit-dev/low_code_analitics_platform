import re

from app.domain.entities.prompt_template import (
    PromptTemplate,
    PromptVariableValue,
    RenderedPromptMessage,
    RenderedPromptTemplate,
)


class MissingTemplateVariablesError(Exception):
    def __init__(self, missing_variables: list[str]) -> None:
        self.missing_variables = missing_variables
        super().__init__(f"Missing template variables: {', '.join(missing_variables)}")


class PromptTemplateRenderer:
    _variable_pattern = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")

    def extract_placeholders(self, template: PromptTemplate) -> list[str]:
        placeholders: set[str] = set()
        for message in template.messages:
            placeholders.update(self._variable_pattern.findall(message.template))
        return sorted(placeholders)

    def render(self, template: PromptTemplate) -> RenderedPromptTemplate:
        placeholders = self.extract_placeholders(template)
        missing = [placeholder for placeholder in placeholders if placeholder not in template.variables]
        if missing:
            raise MissingTemplateVariablesError(missing)

        rendered_messages = [
            RenderedPromptMessage(
                role=message.role,
                content=self._render_text(message.template, template.variables),
            )
            for message in template.messages
        ]

        return RenderedPromptTemplate(
            name=template.name,
            placeholders=placeholders,
            variables=template.variables,
            messages=rendered_messages,
        )

    def _render_text(self, raw_template: str, variables: dict[str, PromptVariableValue]) -> str:
        def replacer(match: re.Match[str]) -> str:
            key = match.group(1)
            value = variables.get(key)
            if value is None:
                return ""
            return str(value)

        return self._variable_pattern.sub(replacer, raw_template)
