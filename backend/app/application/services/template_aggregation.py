from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any


TEMPLATE_FIELD_PATTERN = re.compile(r"\{\{\s*(.*?)\s*\}\}")


class TemplateAggregationError(ValueError):
    pass


@dataclass(frozen=True)
class _Identifier:
    value: str


@dataclass(frozen=True)
class _FunctionCall:
    name: str
    args: list[Any]


@dataclass(frozen=True)
class _StarToken:
    value: str = "*"


@dataclass(frozen=True)
class _Token:
    kind: str
    value: Any
    position: int


_STAR = _StarToken()


class _ExpressionParser:
    def __init__(self, source: str):
        self.source = source
        self.tokens = self._tokenize(source)
        self.index = 0

    def parse(self) -> Any:
        expression = self._parse_expression()
        self._expect("EOF")
        return expression

    def _parse_expression(self) -> Any:
        token = self._peek()

        if token.kind == "IDENT":
            identifier = self._consume("IDENT").value
            if self._peek().kind == "LPAREN":
                self._consume("LPAREN")
                args: list[Any] = []
                if self._peek().kind != "RPAREN":
                    while True:
                        args.append(self._parse_expression())
                        if self._peek().kind == "COMMA":
                            self._consume("COMMA")
                            continue
                        break
                self._expect("RPAREN")
                return _FunctionCall(name=identifier, args=args)
            return _Identifier(identifier)

        if token.kind == "NUMBER":
            return self._consume("NUMBER").value

        if token.kind == "STRING":
            return self._consume("STRING").value

        if token.kind == "STAR":
            self._consume("STAR")
            return _STAR

        raise TemplateAggregationError(
            f"Unexpected token '{token.kind}' at position {token.position} in expression '{self.source}'"
        )

    def _tokenize(self, source: str) -> list[_Token]:
        tokens: list[_Token] = []
        idx = 0
        length = len(source)

        while idx < length:
            char = source[idx]

            if char.isspace():
                idx += 1
                continue

            if char == "(":
                tokens.append(_Token("LPAREN", char, idx))
                idx += 1
                continue

            if char == ")":
                tokens.append(_Token("RPAREN", char, idx))
                idx += 1
                continue

            if char == ",":
                tokens.append(_Token("COMMA", char, idx))
                idx += 1
                continue

            if char == "*":
                tokens.append(_Token("STAR", char, idx))
                idx += 1
                continue

            if char in ('"', "'"):
                start = idx
                quote = char
                idx += 1
                buffer: list[str] = []
                while idx < length:
                    cur = source[idx]
                    if cur == "\\":
                        if idx + 1 >= length:
                            raise TemplateAggregationError(
                                f"Invalid escape sequence at position {idx} in expression '{source}'"
                            )
                        escaped = source[idx + 1]
                        escaped_map = {
                            "n": "\n",
                            "r": "\r",
                            "t": "\t",
                            "\\": "\\",
                            '"': '"',
                            "'": "'",
                        }
                        buffer.append(escaped_map.get(escaped, escaped))
                        idx += 2
                        continue
                    if cur == quote:
                        idx += 1
                        break
                    buffer.append(cur)
                    idx += 1
                else:
                    raise TemplateAggregationError(f"Unterminated string at position {start} in expression '{source}'")

                tokens.append(_Token("STRING", "".join(buffer), start))
                continue

            if char.isdigit() or (char in "+-" and idx + 1 < length and source[idx + 1].isdigit()):
                start = idx
                idx += 1
                has_dot = False
                while idx < length:
                    cur = source[idx]
                    if cur == "." and not has_dot:
                        has_dot = True
                        idx += 1
                        continue
                    if cur.isdigit():
                        idx += 1
                        continue
                    break

                raw_number = source[start:idx]
                number_value: int | float
                try:
                    number_value = float(raw_number) if "." in raw_number else int(raw_number)
                except ValueError as error:
                    raise TemplateAggregationError(
                        f"Invalid number '{raw_number}' at position {start} in expression '{source}'"
                    ) from error
                tokens.append(_Token("NUMBER", number_value, start))
                continue

            if char.isalpha() or char == "_":
                start = idx
                idx += 1
                while idx < length and (source[idx].isalnum() or source[idx] == "_"):
                    idx += 1
                tokens.append(_Token("IDENT", source[start:idx], start))
                continue

            raise TemplateAggregationError(
                f"Unexpected character '{char}' at position {idx} in expression '{source}'"
            )

        tokens.append(_Token("EOF", None, length))
        return tokens

    def _peek(self) -> _Token:
        return self.tokens[self.index]

    def _consume(self, kind: str) -> _Token:
        token = self._peek()
        if token.kind != kind:
            raise TemplateAggregationError(
                f"Expected token '{kind}', got '{token.kind}' at position {token.position} in expression '{self.source}'"
            )
        self.index += 1
        return token

    def _expect(self, kind: str) -> None:
        self._consume(kind)


def _to_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _to_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed_date = date.fromisoformat(normalized)
                return datetime.combine(parsed_date, time.min)
            except ValueError:
                return None
    return None


def _format_aggregation_value(value: float | int) -> str:
    if isinstance(value, float):
        normalized = round(value, 2)
        if normalized.is_integer():
            return str(int(normalized))
        return f"{normalized:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _node_to_scalar(node: Any) -> Any:
    if isinstance(node, _FunctionCall):
        raise TemplateAggregationError("Function call is not allowed in scalar position")

    if node is _STAR:
        return "*"

    if isinstance(node, _Identifier):
        lowered = node.value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "none"}:
            return None
        return node.value

    return node


def _node_to_field_key(node: Any, allow_star: bool = False) -> str:
    if node is _STAR and allow_star:
        return "*"
    scalar = _node_to_scalar(node)
    if isinstance(scalar, str):
        field_key = scalar.strip()
        if not field_key:
            raise TemplateAggregationError("Field key cannot be empty")
        if field_key == "*" and allow_star:
            return field_key
        return field_key
    raise TemplateAggregationError("Field key must be an identifier or string literal")


def _as_condition_call(node: Any) -> _FunctionCall:
    if not isinstance(node, _FunctionCall):
        raise TemplateAggregationError("Condition must be a function call")
    return node


def _values_equal(left: Any, right: Any) -> bool:
    left_number = _to_number(left)
    right_number = _to_number(right)
    if left_number is not None and right_number is not None:
        return left_number == right_number

    left_dt = _to_datetime(left)
    right_dt = _to_datetime(right)
    if left_dt is not None and right_dt is not None:
        return left_dt == right_dt

    return left == right


def _compare_order(left: Any, right: Any, operator: str) -> bool:
    left_number = _to_number(left)
    right_number = _to_number(right)
    if left_number is not None and right_number is not None:
        if operator == "gt":
            return left_number > right_number
        if operator == "gte":
            return left_number >= right_number
        if operator == "lt":
            return left_number < right_number
        return left_number <= right_number

    left_dt = _to_datetime(left)
    right_dt = _to_datetime(right)
    if left_dt is not None and right_dt is not None:
        if operator == "gt":
            return left_dt > right_dt
        if operator == "gte":
            return left_dt >= right_dt
        if operator == "lt":
            return left_dt < right_dt
        return left_dt <= right_dt

    if isinstance(left, str) and isinstance(right, str):
        if operator == "gt":
            return left > right
        if operator == "gte":
            return left >= right
        if operator == "lt":
            return left < right
        return left <= right

    return False


def _evaluate_condition(condition: _FunctionCall, row_data: dict[str, Any], current_value: Any) -> bool:
    name = condition.name.lower()
    args = condition.args

    if name in {"gt", "gte", "lt", "lte", "eq", "neq", "contains", "starts_with", "ends_with", "before", "after", "regex"}:
        if len(args) != 1:
            raise TemplateAggregationError(f"Condition '{name}' expects exactly 1 argument")

    if name in {"between", "date_between"} and len(args) != 2:
        raise TemplateAggregationError(f"Condition '{name}' expects exactly 2 arguments")

    if name in {"is_null", "not_null"} and len(args) != 0:
        raise TemplateAggregationError(f"Condition '{name}' expects no arguments")

    if name == "not":
        if len(args) != 1:
            raise TemplateAggregationError("Condition 'not' expects exactly 1 argument")
        nested = _as_condition_call(args[0])
        return not _evaluate_condition(nested, row_data, current_value)

    if name == "and":
        if len(args) < 1:
            raise TemplateAggregationError("Condition 'and' expects at least 1 argument")
        return all(_evaluate_condition(_as_condition_call(arg), row_data, current_value) for arg in args)

    if name == "or":
        if len(args) < 1:
            raise TemplateAggregationError("Condition 'or' expects at least 1 argument")
        return any(_evaluate_condition(_as_condition_call(arg), row_data, current_value) for arg in args)

    if name == "where":
        if len(args) != 2:
            raise TemplateAggregationError("Condition 'where' expects exactly 2 arguments: where(field, condition)")
        field_key = _node_to_field_key(args[0], allow_star=False)
        nested_condition = _as_condition_call(args[1])
        nested_value = row_data.get(field_key)
        return _evaluate_condition(nested_condition, row_data, nested_value)

    if name == "gt":
        return _compare_order(current_value, _node_to_scalar(args[0]), "gt")

    if name == "gte":
        return _compare_order(current_value, _node_to_scalar(args[0]), "gte")

    if name == "lt":
        return _compare_order(current_value, _node_to_scalar(args[0]), "lt")

    if name == "lte":
        return _compare_order(current_value, _node_to_scalar(args[0]), "lte")

    if name == "eq":
        return _values_equal(current_value, _node_to_scalar(args[0]))

    if name == "neq":
        return not _values_equal(current_value, _node_to_scalar(args[0]))

    if name == "between":
        left = _node_to_scalar(args[0])
        right = _node_to_scalar(args[1])
        current_number = _to_number(current_value)
        left_number = _to_number(left)
        right_number = _to_number(right)
        if current_number is not None and left_number is not None and right_number is not None:
            lower, upper = sorted((left_number, right_number))
            return lower <= current_number <= upper
        current_dt = _to_datetime(current_value)
        left_dt = _to_datetime(left)
        right_dt = _to_datetime(right)
        if current_dt is not None and left_dt is not None and right_dt is not None:
            lower, upper = sorted((left_dt, right_dt))
            return lower <= current_dt <= upper
        if isinstance(current_value, str) and isinstance(left, str) and isinstance(right, str):
            lower, upper = sorted((left, right))
            return lower <= current_value <= upper
        return False

    if name == "is_null":
        return current_value is None

    if name == "not_null":
        return current_value is not None

    if name == "contains":
        expected = str(_node_to_scalar(args[0]))
        haystack = "" if current_value is None else str(current_value)
        return expected in haystack

    if name == "starts_with":
        expected = str(_node_to_scalar(args[0]))
        value = "" if current_value is None else str(current_value)
        return value.startswith(expected)

    if name == "ends_with":
        expected = str(_node_to_scalar(args[0]))
        value = "" if current_value is None else str(current_value)
        return value.endswith(expected)

    if name == "before":
        current_dt = _to_datetime(current_value)
        threshold_dt = _to_datetime(_node_to_scalar(args[0]))
        return current_dt is not None and threshold_dt is not None and current_dt < threshold_dt

    if name == "after":
        current_dt = _to_datetime(current_value)
        threshold_dt = _to_datetime(_node_to_scalar(args[0]))
        return current_dt is not None and threshold_dt is not None and current_dt > threshold_dt

    if name == "date_between":
        current_dt = _to_datetime(current_value)
        left_dt = _to_datetime(_node_to_scalar(args[0]))
        right_dt = _to_datetime(_node_to_scalar(args[1]))
        if current_dt is None or left_dt is None or right_dt is None:
            return False
        lower, upper = sorted((left_dt, right_dt))
        return lower <= current_dt <= upper

    if name == "in":
        if len(args) < 1:
            raise TemplateAggregationError("Condition 'in' expects at least 1 argument")
        return any(_values_equal(current_value, _node_to_scalar(arg)) for arg in args)

    if name == "not_in":
        if len(args) < 1:
            raise TemplateAggregationError("Condition 'not_in' expects at least 1 argument")
        return not any(_values_equal(current_value, _node_to_scalar(arg)) for arg in args)

    if name == "regex":
        pattern = str(_node_to_scalar(args[0]))
        try:
            compiled = re.compile(pattern)
        except re.error as error:
            raise TemplateAggregationError(f"Invalid regex pattern '{pattern}': {error}") from error
        value = "" if current_value is None else str(current_value)
        return compiled.search(value) is not None

    raise TemplateAggregationError(
        f"Unsupported condition '{condition.name}'. "
        "Supported: gt, gte, lt, lte, eq, neq, between, is_null, not_null, contains, starts_with, "
        "ends_with, and, or, not, where, before, after, date_between, in, not_in, regex."
    )


def evaluate_template_expression(expression: str, rows: list[dict[str, Any]]) -> float | int:
    parsed = _ExpressionParser(expression).parse()
    if not isinstance(parsed, _FunctionCall):
        raise TemplateAggregationError(
            f"Invalid template expression '{{{{ {expression} }}}}'. Expected aggregation_func(key[, condition])."
        )

    function_name = parsed.name.lower()
    if function_name not in {"count", "sum", "avg", "min", "max"}:
        raise TemplateAggregationError(
            f"Unsupported aggregation '{parsed.name}'. Allowed: count, sum, avg, min, max."
        )

    if len(parsed.args) not in {1, 2}:
        raise TemplateAggregationError(
            f"Aggregation '{parsed.name}' expects 1 or 2 arguments: function(key[, condition])."
        )

    field_key = _node_to_field_key(parsed.args[0], allow_star=function_name == "count")
    if field_key == "*" and function_name != "count":
        raise TemplateAggregationError("Only count(*) is supported. Other aggregations require a field key.")

    condition: _FunctionCall | None = None
    if len(parsed.args) == 2:
        condition = _as_condition_call(parsed.args[1])

    if function_name == "count":
        count = 0
        for row in rows:
            row_data = row or {}
            current_value = None if field_key == "*" else row_data.get(field_key)
            if condition and not _evaluate_condition(condition, row_data, current_value):
                continue
            if field_key == "*":
                count += 1
                continue
            if current_value not in (None, ""):
                count += 1
        return count

    numeric_values: list[float] = []
    for row in rows:
        row_data = row or {}
        current_value = row_data.get(field_key)
        if condition and not _evaluate_condition(condition, row_data, current_value):
            continue
        number_value = _to_number(current_value)
        if number_value is not None:
            numeric_values.append(number_value)

    if not numeric_values:
        return 0

    if function_name == "sum":
        return sum(numeric_values)
    if function_name == "avg":
        return sum(numeric_values) / len(numeric_values)
    if function_name == "min":
        return min(numeric_values)
    return max(numeric_values)


def render_template_content(content_xml: str, rows: list[dict[str, Any]]) -> str:
    def replace_field(match: re.Match[str]) -> str:
        expression = match.group(1).strip()
        result = evaluate_template_expression(expression, rows)
        return _format_aggregation_value(result)

    return TEMPLATE_FIELD_PATTERN.sub(replace_field, content_xml)
