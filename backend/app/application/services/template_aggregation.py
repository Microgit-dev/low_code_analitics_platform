from __future__ import annotations

import html
import calendar
import re
import math
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any


TEMPLATE_FIELD_PATTERN = re.compile(r"\{\{\s*(.*?)\s*\}\}")
ODT_SPACE_TAG_PATTERN = re.compile(r"<text:s(?:\s+text:c=\"(\d+)\")?\s*/>")
ODT_INLINE_SPACE_TAG_PATTERN = re.compile(r"<text:(?:tab|line-break)\b[^>]*/>")
XML_TAG_PATTERN = re.compile(r"</?[^>]+>")


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
class _UnaryOp:
    operator: str
    operand: Any


@dataclass(frozen=True)
class _BinaryOp:
    operator: str
    left: Any
    right: Any


@dataclass(frozen=True)
class _Token:
    kind: str
    value: Any
    position: int


_STAR = _StarToken()
_AGGREGATION_FUNCTIONS = {"count", "sum", "avg", "min", "max"}
_SCALAR_FUNCTIONS = {"first", "last"}
_DATE_HELPER_FUNCTIONS = {"date", "add_years"}
_VARIABLE_FUNCTIONS = {"set", "var"}
_CONDITION_FUNCTIONS = {
    "gt",
    "gte",
    "lt",
    "lte",
    "eq",
    "neq",
    "between",
    "is_null",
    "not_null",
    "contains",
    "starts_with",
    "ends_with",
    "and",
    "or",
    "not",
    "where",
    "before",
    "after",
    "date_between",
    "in",
    "not_in",
    "regex",
}


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
        return self._parse_additive()

    def _parse_additive(self) -> Any:
        node = self._parse_multiplicative()
        while self._peek().kind in {"PLUS", "MINUS"}:
            operator = self._consume(self._peek().kind).value
            right = self._parse_multiplicative()
            node = _BinaryOp(operator=operator, left=node, right=right)
        return node

    def _parse_multiplicative(self) -> Any:
        node = self._parse_unary()
        while self._peek().kind in {"STAR", "SLASH"}:
            operator_token = self._peek()
            operator = self._consume(operator_token.kind).value
            right = self._parse_unary()
            node = _BinaryOp(operator=operator, left=node, right=right)
        return node

    def _parse_unary(self) -> Any:
        token = self._peek()
        if token.kind in {"PLUS", "MINUS"}:
            operator = self._consume(token.kind).value
            operand = self._parse_unary()
            return _UnaryOp(operator=operator, operand=operand)
        return self._parse_primary()

    def _parse_primary(self) -> Any:
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

        if token.kind == "LPAREN":
            self._consume("LPAREN")
            nested = self._parse_expression()
            self._expect("RPAREN")
            return nested

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

            if char == "+":
                tokens.append(_Token("PLUS", char, idx))
                idx += 1
                continue

            if char == "-":
                tokens.append(_Token("MINUS", char, idx))
                idx += 1
                continue

            if char == "*":
                tokens.append(_Token("STAR", char, idx))
                idx += 1
                continue

            if char == "/":
                tokens.append(_Token("SLASH", char, idx))
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

            if char.isdigit():
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


def _format_aggregation_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "-"
        normalized = round(value, 2)
        if normalized.is_integer():
            return str(int(normalized))
        return f"{normalized:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _node_to_scalar(node: Any) -> Any:
    if isinstance(node, (_FunctionCall, _UnaryOp, _BinaryOp)):
        raise TemplateAggregationError("Expression is not allowed in scalar position")

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


def _node_to_variable_name(node: Any) -> str:
    scalar = _node_to_scalar(node)
    if not isinstance(scalar, str):
        raise TemplateAggregationError("Variable name must be an identifier or string literal")
    variable_name = scalar.strip()
    if not variable_name:
        raise TemplateAggregationError("Variable name cannot be empty")
    return variable_name


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


def _coerce_int(value: Any, label: str) -> int:
    number = _to_number(value)
    if number is None:
        raise TemplateAggregationError(f"{label} must be numeric")
    integer = int(number)
    if number != integer:
        raise TemplateAggregationError(f"{label} must be an integer")
    return integer


def _shift_years(value_dt: datetime, years: int) -> datetime:
    target_year = value_dt.year + years
    try:
        return value_dt.replace(year=target_year)
    except ValueError:
        max_day = calendar.monthrange(target_year, value_dt.month)[1]
        adjusted_day = min(value_dt.day, max_day)
        return value_dt.replace(year=target_year, day=adjusted_day)


def _resolve_condition_value(
    node: Any,
    row_data: dict[str, Any],
    current_value: Any,
    rows: list[dict[str, Any]],
    variables: dict[str, Any],
) -> Any:
    if isinstance(node, _UnaryOp):
        operand_value = _resolve_condition_value(node.operand, row_data, current_value, rows, variables)
        operand_number = _to_number(operand_value)
        if operand_number is None:
            raise TemplateAggregationError("Unary condition argument expects numeric operand")
        return operand_number if node.operator == "+" else -operand_number

    if isinstance(node, _BinaryOp):
        left_value = _resolve_condition_value(node.left, row_data, current_value, rows, variables)
        right_value = _resolve_condition_value(node.right, row_data, current_value, rows, variables)
        left_number = _to_number(left_value)
        right_number = _to_number(right_value)
        if left_number is None or right_number is None:
            raise TemplateAggregationError("Condition arithmetic arguments must be numeric")
        if node.operator == "+":
            return left_number + right_number
        if node.operator == "-":
            return left_number - right_number
        if node.operator == "*":
            return left_number * right_number
        return _safe_divide(left_number, right_number)

    if isinstance(node, _FunctionCall):
        name = node.name.lower()
        args = node.args

        if name == "date":
            if len(args) != 3:
                raise TemplateAggregationError("Function 'date' expects exactly 3 arguments: date(day, month, year)")
            day = _coerce_int(_resolve_condition_value(args[0], row_data, current_value, rows, variables), "day")
            month = _coerce_int(_resolve_condition_value(args[1], row_data, current_value, rows, variables), "month")
            year = _coerce_int(_resolve_condition_value(args[2], row_data, current_value, rows, variables), "year")
            try:
                return datetime(year=year, month=month, day=day)
            except ValueError as error:
                raise TemplateAggregationError(f"Invalid date({day}, {month}, {year}): {error}") from error

        if name == "add_years":
            if len(args) != 2:
                raise TemplateAggregationError("Function 'add_years' expects exactly 2 arguments: add_years(date_value, years)")
            base_value = _resolve_condition_value(args[0], row_data, current_value, rows, variables)
            years_delta = _coerce_int(_resolve_condition_value(args[1], row_data, current_value, rows, variables), "years")
            base_dt = _to_datetime(base_value)
            if base_dt is None:
                raise TemplateAggregationError("Function 'add_years' requires a valid date/datetime as first argument")
            return _shift_years(base_dt, years_delta)

        if name in _SCALAR_FUNCTIONS:
            return _evaluate_scalar_call(node, rows, variables)

        if name == "var":
            return _evaluate_variable_call(node, rows, variables)
        if name == "set":
            raise TemplateAggregationError("Function 'set' is not allowed in condition arguments")

        raise TemplateAggregationError(
            f"Unsupported function '{node.name}' in condition argument. "
            "Allowed helper functions: date(day, month, year), add_years(date_value, years), first(key[, condition]), last(key[, condition]), var(name)."
        )

    return _node_to_scalar(node)


def _evaluate_condition(
    condition: _FunctionCall,
    row_data: dict[str, Any],
    current_value: Any,
    rows: list[dict[str, Any]],
    variables: dict[str, Any],
) -> bool:
    name = condition.name.lower()
    args = condition.args

    if name == "var":
        if len(args) != 1:
            raise TemplateAggregationError("Condition 'var' expects exactly 1 argument: var(name)")
        variable_name = _node_to_variable_name(args[0])
        variable_value = variables.get(variable_name)
        if variable_value is None:
            return False
        if not isinstance(variable_value, _FunctionCall):
            raise TemplateAggregationError(
                f"Variable '{variable_name}' is not a condition. "
                "Use set(name, where(...)/and(...)/or(...)) for condition variables."
            )
        return _evaluate_condition(variable_value, row_data, current_value, rows, variables)

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
        return not _evaluate_condition(nested, row_data, current_value, rows, variables)

    if name == "and":
        if len(args) < 1:
            raise TemplateAggregationError("Condition 'and' expects at least 1 argument")
        return all(_evaluate_condition(_as_condition_call(arg), row_data, current_value, rows, variables) for arg in args)

    if name == "or":
        if len(args) < 1:
            raise TemplateAggregationError("Condition 'or' expects at least 1 argument")
        return any(_evaluate_condition(_as_condition_call(arg), row_data, current_value, rows, variables) for arg in args)

    if name == "where":
        if len(args) != 2:
            raise TemplateAggregationError("Condition 'where' expects exactly 2 arguments: where(field, condition)")
        field_key = _node_to_field_key(args[0], allow_star=False)
        nested_condition = _as_condition_call(args[1])
        nested_value = row_data.get(field_key)
        return _evaluate_condition(nested_condition, row_data, nested_value, rows, variables)

    if name == "gt":
        return _compare_order(current_value, _resolve_condition_value(args[0], row_data, current_value, rows, variables), "gt")

    if name == "gte":
        return _compare_order(current_value, _resolve_condition_value(args[0], row_data, current_value, rows, variables), "gte")

    if name == "lt":
        return _compare_order(current_value, _resolve_condition_value(args[0], row_data, current_value, rows, variables), "lt")

    if name == "lte":
        return _compare_order(current_value, _resolve_condition_value(args[0], row_data, current_value, rows, variables), "lte")

    if name == "eq":
        return _values_equal(current_value, _resolve_condition_value(args[0], row_data, current_value, rows, variables))

    if name == "neq":
        return not _values_equal(current_value, _resolve_condition_value(args[0], row_data, current_value, rows, variables))

    if name == "between":
        left = _resolve_condition_value(args[0], row_data, current_value, rows, variables)
        right = _resolve_condition_value(args[1], row_data, current_value, rows, variables)
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
        expected = str(_resolve_condition_value(args[0], row_data, current_value, rows, variables))
        haystack = "" if current_value is None else str(current_value)
        return expected in haystack

    if name == "starts_with":
        expected = str(_resolve_condition_value(args[0], row_data, current_value, rows, variables))
        value = "" if current_value is None else str(current_value)
        return value.startswith(expected)

    if name == "ends_with":
        expected = str(_resolve_condition_value(args[0], row_data, current_value, rows, variables))
        value = "" if current_value is None else str(current_value)
        return value.endswith(expected)

    if name == "before":
        current_dt = _to_datetime(current_value)
        threshold_dt = _to_datetime(_resolve_condition_value(args[0], row_data, current_value, rows, variables))
        return current_dt is not None and threshold_dt is not None and current_dt < threshold_dt

    if name == "after":
        current_dt = _to_datetime(current_value)
        threshold_dt = _to_datetime(_resolve_condition_value(args[0], row_data, current_value, rows, variables))
        return current_dt is not None and threshold_dt is not None and current_dt > threshold_dt

    if name == "date_between":
        current_dt = _to_datetime(current_value)
        left_dt = _to_datetime(_resolve_condition_value(args[0], row_data, current_value, rows, variables))
        right_dt = _to_datetime(_resolve_condition_value(args[1], row_data, current_value, rows, variables))
        if current_dt is None or left_dt is None or right_dt is None:
            return False
        lower, upper = sorted((left_dt, right_dt))
        return lower <= current_dt <= upper

    if name == "in":
        if len(args) < 1:
            raise TemplateAggregationError("Condition 'in' expects at least 1 argument")
        return any(
            _values_equal(current_value, _resolve_condition_value(arg, row_data, current_value, rows, variables))
            for arg in args
        )

    if name == "not_in":
        if len(args) < 1:
            raise TemplateAggregationError("Condition 'not_in' expects at least 1 argument")
        return not any(
            _values_equal(current_value, _resolve_condition_value(arg, row_data, current_value, rows, variables))
            for arg in args
        )

    if name == "regex":
        pattern = str(_resolve_condition_value(args[0], row_data, current_value, rows, variables))
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


def _normalize_numeric_result(value: float) -> float | int:
    return int(value) if float(value).is_integer() else value


def _expand_odt_space_tag(match: re.Match[str]) -> str:
    count_group = match.group(1)
    if not count_group:
        return " "
    try:
        count = int(count_group)
    except ValueError:
        return " "
    return " " * max(1, count)


def _normalize_template_expression_source(source: str) -> str:
    normalized = ODT_SPACE_TAG_PATTERN.sub(_expand_odt_space_tag, source)
    normalized = ODT_INLINE_SPACE_TAG_PATTERN.sub(" ", normalized)
    normalized = XML_TAG_PATTERN.sub("", normalized)
    normalized = html.unescape(normalized)
    return normalized.strip()


def _evaluate_aggregation_call(
    call: _FunctionCall,
    rows: list[dict[str, Any]],
    variables: dict[str, Any],
) -> float | int:
    function_name = call.name.lower()
    if function_name not in _AGGREGATION_FUNCTIONS:
        raise TemplateAggregationError(
            f"Unsupported aggregation '{call.name}'. Allowed: count, sum, avg, min, max."
        )

    if len(call.args) not in {1, 2}:
        raise TemplateAggregationError(
            f"Aggregation '{call.name}' expects 1 or 2 arguments: function(key[, condition])."
        )

    field_key = _node_to_field_key(call.args[0], allow_star=function_name == "count")
    if field_key == "*" and function_name != "count":
        raise TemplateAggregationError("Only count(*) is supported. Other aggregations require a field key.")

    condition: _FunctionCall | None = None
    if len(call.args) == 2:
        condition = _as_condition_call(call.args[1])

    if function_name == "count":
        count = 0
        for row in rows:
            row_data = row or {}
            current_value = None if field_key == "*" else row_data.get(field_key)
            if condition and not _evaluate_condition(condition, row_data, current_value, rows, variables):
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
        if condition and not _evaluate_condition(condition, row_data, current_value, rows, variables):
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


def _to_expression_number(value: Any) -> float:
    number = _to_number(value)
    if number is None:
        raise TemplateAggregationError(f"Expression value '{value}' is not numeric")
    return number


def _safe_divide(numerator: float, denominator: float) -> float:
    if numerator == 0:
        return float("nan")
    if denominator == 0:
        return float("nan")
    if math.isnan(numerator) or math.isnan(denominator):
        return float("nan")
    if math.isinf(numerator) or math.isinf(denominator):
        return float("nan")
    return numerator / denominator


def _evaluate_scalar_call(
    call: _FunctionCall,
    rows: list[dict[str, Any]],
    variables: dict[str, Any],
) -> Any:
    function_name = call.name.lower()
    if function_name not in _SCALAR_FUNCTIONS:
        raise TemplateAggregationError(
            f"Unsupported scalar function '{call.name}'. Allowed: first, last."
        )

    if len(call.args) not in {1, 2}:
        raise TemplateAggregationError(
            f"Function '{call.name}' expects 1 or 2 arguments: function(key[, condition])."
        )

    field_key = _node_to_field_key(call.args[0], allow_star=False)
    condition: _FunctionCall | None = None
    if len(call.args) == 2:
        condition = _as_condition_call(call.args[1])

    iterable = rows if function_name == "first" else reversed(rows)
    for row in iterable:
        row_data = row or {}
        current_value = row_data.get(field_key)
        if condition and not _evaluate_condition(condition, row_data, current_value, rows, variables):
            continue
        if current_value not in (None, ""):
            return current_value

    return ""


def _evaluate_node_value(node: Any, rows: list[dict[str, Any]], variables: dict[str, Any]) -> Any:
    if isinstance(node, (int, float, _UnaryOp, _BinaryOp)):
        return _evaluate_numeric_expression(node, rows, variables)

    if isinstance(node, _FunctionCall):
        function_name = node.name.lower()
        if function_name in _AGGREGATION_FUNCTIONS:
            return _evaluate_aggregation_call(node, rows, variables)
        if function_name in _SCALAR_FUNCTIONS:
            return _evaluate_scalar_call(node, rows, variables)
        if function_name in _DATE_HELPER_FUNCTIONS:
            return _resolve_condition_value(node, {}, None, rows, variables)
        if function_name in _VARIABLE_FUNCTIONS:
            return _evaluate_variable_call(node, rows, variables)

    return _node_to_scalar(node)


def _evaluate_variable_call(call: _FunctionCall, rows: list[dict[str, Any]], variables: dict[str, Any]) -> Any:
    function_name = call.name.lower()

    if function_name == "var":
        if len(call.args) != 1:
            raise TemplateAggregationError("Function 'var' expects exactly 1 argument: var(name)")
        variable_name = _node_to_variable_name(call.args[0])
        return variables.get(variable_name, "")

    if function_name == "set":
        if len(call.args) != 2:
            raise TemplateAggregationError("Function 'set' expects exactly 2 arguments: set(name, value)")
        variable_name = _node_to_variable_name(call.args[0])
        raw_value_node = call.args[1]
        if isinstance(raw_value_node, _FunctionCall) and raw_value_node.name.lower() in _CONDITION_FUNCTIONS:
            variable_value = raw_value_node
        else:
            variable_value = _evaluate_node_value(raw_value_node, rows, variables)
        variables[variable_name] = variable_value
        return ""

    raise TemplateAggregationError("Unsupported variable function. Allowed: set(name, value), var(name).")


def _evaluate_numeric_expression(node: Any, rows: list[dict[str, Any]], variables: dict[str, Any]) -> float:
    if isinstance(node, (int, float)):
        return float(node)

    if isinstance(node, _UnaryOp):
        operand = _evaluate_numeric_expression(node.operand, rows, variables)
        if node.operator == "+":
            return operand
        return -operand

    if isinstance(node, _BinaryOp):
        left = _evaluate_numeric_expression(node.left, rows, variables)
        right = _evaluate_numeric_expression(node.right, rows, variables)
        if node.operator == "+":
            return left + right
        if node.operator == "-":
            return left - right
        if node.operator == "*":
            return left * right
        return _safe_divide(left, right)

    if isinstance(node, _FunctionCall):
        name = node.name.lower()
        if name in _AGGREGATION_FUNCTIONS:
            return _to_expression_number(_evaluate_aggregation_call(node, rows, variables))
        if name in _SCALAR_FUNCTIONS:
            return _to_expression_number(_evaluate_scalar_call(node, rows, variables))
        if name in _VARIABLE_FUNCTIONS:
            return _to_expression_number(_evaluate_variable_call(node, rows, variables))

        if name == "add":
            if len(node.args) < 2:
                raise TemplateAggregationError("Function 'add' expects at least 2 arguments")
            return sum(_evaluate_numeric_expression(arg, rows, variables) for arg in node.args)

        if name == "sub":
            if len(node.args) != 2:
                raise TemplateAggregationError("Function 'sub' expects exactly 2 arguments")
            return _evaluate_numeric_expression(node.args[0], rows, variables) - _evaluate_numeric_expression(
                node.args[1], rows, variables
            )

        if name == "mul":
            if len(node.args) < 2:
                raise TemplateAggregationError("Function 'mul' expects at least 2 arguments")
            result = 1.0
            for arg in node.args:
                result *= _evaluate_numeric_expression(arg, rows, variables)
            return result

        if name == "div":
            if len(node.args) != 2:
                raise TemplateAggregationError("Function 'div' expects exactly 2 arguments")
            denominator = _evaluate_numeric_expression(node.args[1], rows, variables)
            numerator = _evaluate_numeric_expression(node.args[0], rows, variables)
            return _safe_divide(numerator, denominator)

        raise TemplateAggregationError(
            f"Unsupported function '{node.name}' in expression. "
            "Allowed: count, sum, avg, min, max, first, last, set, var, add, sub, mul, div and operators +, -, *, /."
        )

    raise TemplateAggregationError("Invalid arithmetic expression node")


def evaluate_template_expression(
    expression: str,
    rows: list[dict[str, Any]],
    variables: dict[str, Any] | None = None,
) -> Any:
    context = variables if variables is not None else {}
    parsed = _ExpressionParser(expression).parse()
    if isinstance(parsed, _FunctionCall):
        function_name = parsed.name.lower()
        if function_name in _AGGREGATION_FUNCTIONS:
            return _evaluate_aggregation_call(parsed, rows, context)
        if function_name in _SCALAR_FUNCTIONS:
            return _evaluate_scalar_call(parsed, rows, context)
        if function_name in _VARIABLE_FUNCTIONS:
            return _evaluate_variable_call(parsed, rows, context)

    value = _evaluate_numeric_expression(parsed, rows, context)
    return _normalize_numeric_result(value)


def render_template_content(content_xml: str, rows: list[dict[str, Any]]) -> str:
    variables: dict[str, Any] = {}

    def replace_field(match: re.Match[str]) -> str:
        raw_expression = match.group(1)
        expression = _normalize_template_expression_source(raw_expression)
        if not expression:
            return match.group(0)
        result = evaluate_template_expression(expression, rows, variables)
        return _format_aggregation_value(result)

    return TEMPLATE_FIELD_PATTERN.sub(replace_field, content_xml)
