from __future__ import annotations

import logging
import re
from typing import List

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HtmlPostCheckError(Exception):
    pass


_UNDERLINE_RE = re.compile(r"_{2,}")
_PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")
_SINGLE_BRACE_EXPR_RE = re.compile(
    r"(?<!\{)\{\s*([A-Za-z_][A-Za-z0-9_]*(?:\([^{}<>:;\n]*\))?)\s*\}(?!\})"
)
_SPECIAL_PLACEHOLDER_SELECTORS = (".line", ".inline-line", ".total-line")


def _count_template_obligations(template_html: str) -> int:
    soup = BeautifulSoup(template_html, "lxml")
    obligations = 0
    for cell in soup.select("td, th"):
        text = (cell.get_text() or "").strip()
        if not text or _UNDERLINE_RE.search(text):
            obligations += 1
    return obligations


def _count_selected(soup: BeautifulSoup, selector: str) -> int:
    return len(soup.select(selector))


def _count_span(soup: BeautifulSoup, attr: str) -> int:
    return sum(1 for _ in soup.select(f"td[{attr}], th[{attr}]"))


def _has_structural_loss(template_html: str, html: str) -> bool:
    soup_tpl = BeautifulSoup(template_html, "lxml")
    soup_out = BeautifulSoup(html, "lxml")

    if _count_selected(soup_out, "table") < _count_selected(soup_tpl, "table"):
        return True
    if _count_selected(soup_out, "thead") < _count_selected(soup_tpl, "thead"):
        return True
    if _count_selected(soup_out, "tbody") < _count_selected(soup_tpl, "tbody"):
        return True

    for attr in ("rowspan", "colspan"):
        if _count_span(soup_out, attr) < _count_span(soup_tpl, attr):
            return True
    return False


def _normalize_expression(raw: str) -> str | None:
    expr = raw.strip().strip("{}").strip()
    if not expr:
        return None
    if any(ch in expr for ch in "<>;") or "\n" in expr or ":" in expr:
        return None
    return expr


def _extract_preferred_expressions(html: str) -> List[str]:
    candidates: List[str] = []
    for pattern in (_PLACEHOLDER_RE, _SINGLE_BRACE_EXPR_RE):
        for match in pattern.finditer(html):
            raw = match.group(1) if match.groups() else match.group(0)
            expr = _normalize_expression(raw)
            if expr:
                candidates.append(expr)
    return candidates


def _needs_placeholder_patch(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    if _UNDERLINE_RE.search(stripped):
        return True
    if stripped == "{{}}":
        return True
    if stripped.startswith("{") and stripped.endswith("}") and not _PLACEHOLDER_RE.fullmatch(stripped):
        return True
    return False


def _element_has_placeholder_content(node) -> bool:
    text = node.get_text(" ", strip=True)
    return bool(text and _PLACEHOLDER_RE.search(text))


def _required_special_placeholder_count(template_html: str) -> int:
    soup = BeautifulSoup(template_html, "lxml")
    count = 0
    for selector in _SPECIAL_PLACEHOLDER_SELECTORS:
        count += len(soup.select(selector))
    return count


def _filled_special_placeholder_count(html: str) -> int:
    soup = BeautifulSoup(html, "lxml")
    count = 0
    for selector in _SPECIAL_PLACEHOLDER_SELECTORS:
        count += sum(1 for node in soup.select(selector) if _element_has_placeholder_content(node))
    return count


def _pick_key(row_keys: List[str], *candidates: str) -> str | None:
    lowered = {key.lower(): key for key in row_keys}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]

    for candidate in candidates:
        needle = candidate.lower()
        for key in row_keys:
            if needle in key.lower():
                return key
    return None


def _pick_total_expr(row_keys: List[str]) -> str:
    for key in row_keys:
        low = key.lower()
        if any(token in low for token in ("total_amount", "accident_count", "defect_accident_count", "injured_count")):
            return f"sum({key})"
    base = row_keys[0] if row_keys else "value"
    return f"count({base})"


def validate_generated_html(template_html: str, html: str) -> str:
    if not html or not isinstance(html, str):
        raise HtmlPostCheckError("Пустой HTML от модели.")

    txt = html.strip()
    if txt.startswith("```") or txt.endswith("```"):
        raise HtmlPostCheckError("HTML не должен содержать markdown-заборы кода.")
    if "<!--" in txt or "-->" in txt:
        raise HtmlPostCheckError("HTML не должен содержать комментарии.")
    if "<script" in txt.lower():
        raise HtmlPostCheckError("В HTML не допускаются теги <script>.")
    if not txt[:1] == "<" or not txt.rstrip()[-1:] == ">":
        raise HtmlPostCheckError("Ответ должен быть только HTML без внешнего текста.")

    try:
        soup_tpl = BeautifulSoup(template_html, "lxml")
        soup_out = BeautifulSoup(txt, "lxml")
    except Exception as e:
        raise HtmlPostCheckError(f"Ошибка парсинга HTML: {e}")

    tpl_tables = soup_tpl.select("table")
    out_tables = soup_out.select("table")
    if len(out_tables) < len(tpl_tables):
        raise HtmlPostCheckError("В результате меньше таблиц, чем в шаблоне.")

    for attr in ("rowspan", "colspan"):
        if _count_span(soup_out, attr) < _count_span(soup_tpl, attr):
            raise HtmlPostCheckError(f"Потеряны атрибуты {attr} в таблицах.")

    required_placeholders = _count_template_obligations(template_html)
    placeholders_now = len(_PLACEHOLDER_RE.findall(txt))
    if placeholders_now < required_placeholders:
        raise HtmlPostCheckError(
            "Недостаточно выражений {{...}}: не все пустые/подчёркнутые поля заменены."
        )

    required_special = _required_special_placeholder_count(template_html)
    if required_special and _filled_special_placeholder_count(txt) < required_special:
        raise HtmlPostCheckError("Не все специальные поля формы заполнены placeholder-выражениями.")

    for cell in soup_out.select("td, th"):
        cell_text = (cell.get_text() or "").strip()
        if not cell_text:
            raise HtmlPostCheckError("В итоговом HTML остались пустые ячейки таблиц.")
        if _UNDERLINE_RE.search(cell_text):
            raise HtmlPostCheckError("Обнаружены подчёркивания, не заменённые на {{...}}.")

    return txt


def auto_patch_html(template_html: str, html: str, row_keys: List[str], header_hint: List[str] | None = None) -> str:
    """Best-effort автодозаполнение пустых/подчёркнутых мест {{...}} без изменения структуры."""
    txt = (html or "").strip()
    preferred_expressions = _extract_preferred_expressions(txt)
    base_html = template_html if not txt or _has_structural_loss(template_html, txt) else txt
    soup_out = BeautifulSoup(base_html, "lxml")

    headers_by_table = []
    for table in soup_out.select("table"):
        headers = [th.get_text(strip=True) for th in table.select("thead th")]
        headers_by_table.append(headers)

    preferred_index = 0

    def take_preferred_expr() -> str | None:
        nonlocal preferred_index
        while preferred_index < len(preferred_expressions):
            expr = preferred_expressions[preferred_index]
            preferred_index += 1
            if expr:
                return expr
        return None

    def choose_expr(table_idx: int, col_idx: int, context_text: str, cells_count: int) -> str:
        preferred = take_preferred_expr()
        if preferred:
            return preferred

        lowered_context = context_text.lower()
        if any(label in lowered_context for label in ("аппг", "период учета", "(+/-", "%%)")):
            if cells_count >= 12:
                form_d_map = {
                    1: "road_name",
                    3: "accident_count",
                    4: "injured_count",
                    5: "dead_count",
                    6: "severity_rate",
                    7: "defect_accident_count",
                    8: "defect_accident_share",
                    9: "defect_injured_count",
                    10: "defect_dead_count",
                    11: "defect_severity_rate",
                }
                matched = _pick_key(row_keys, form_d_map.get(col_idx, ""))
                if matched:
                    return matched
            if cells_count == 10:
                form_d_map = {
                    1: "accident_count",
                    2: "injured_count",
                    3: "dead_count",
                    4: "severity_rate",
                    5: "defect_accident_count",
                    6: "defect_accident_share",
                    7: "defect_injured_count",
                    8: "defect_dead_count",
                    9: "defect_severity_rate",
                }
                matched = _pick_key(row_keys, form_d_map.get(col_idx, ""))
                if matched:
                    return matched

        if "дорог" in lowered_context:
            matched = _pick_key(row_keys, "road_name")
            if matched:
                return matched
        if "период" in lowered_context or "год" in lowered_context:
            matched = _pick_key(row_keys, "period_label", "report_period")
            if matched:
                return matched
        if "ранен" in lowered_context:
            matched = _pick_key(row_keys, "injured_count", "defect_injured_count")
            if matched:
                return matched
        if "погиб" in lowered_context:
            matched = _pick_key(row_keys, "dead_count", "defect_dead_count")
            if matched:
                return matched
        if "тяжест" in lowered_context:
            matched = _pick_key(row_keys, "severity_rate", "defect_severity_rate")
            if matched:
                return matched
        if "%" in lowered_context:
            matched = _pick_key(row_keys, "defect_accident_share")
            if matched:
                return matched
        if "итог" in lowered_context or "сумм" in lowered_context:
            return _pick_total_expr(row_keys)
        if "дтп" in lowered_context:
            matched = _pick_key(row_keys, "accident_count", "defect_accident_count")
            if matched:
                return matched

        hdrs = headers_by_table[table_idx] if table_idx < len(headers_by_table) else []
        hdr = (hdrs[col_idx] if col_idx < len(hdrs) else "").lower()
        if any(key in (hdr + " " + lowered_context) for key in ["итог", "сумм"]):
            return _pick_total_expr(row_keys)
        if col_idx < len(row_keys):
            return row_keys[col_idx]
        return row_keys[0] if row_keys else "value"

    def set_placeholder(node, expr: str) -> None:
        node.clear()
        node.append("{{" + expr + "}}")

    for ti, table in enumerate(soup_out.select("table")):
        rows = table.select("tbody tr") or table.select("tr")
        for tr in rows:
            cells = tr.find_all(["td", "th"])
            for ci, cell in enumerate(cells):
                text = (cell.get_text() or "").strip()
                if _needs_placeholder_patch(text):
                    expr = choose_expr(ti, ci, tr.get_text(" ", strip=True), len(cells))
                    set_placeholder(cell, expr)

    for index, node in enumerate(soup_out.select(".line")):
        if _element_has_placeholder_content(node):
            continue
        context = node.parent.get_text(" ", strip=True).lower() if node.parent else ""
        if index == 0:
            expr = _pick_key(row_keys, "owner_name", "road_owner_name", "organization_name", "road_name") or "road_name"
        else:
            expr = _pick_key(row_keys, "report_period", "period_label") or "period_label"
        if "владелец" in context:
            expr = _pick_key(row_keys, "owner_name", "road_owner_name", "organization_name", "road_name") or expr
        if "период" in context:
            expr = _pick_key(row_keys, "report_period", "period_label") or expr
        set_placeholder(node, expr)

    for index, node in enumerate(soup_out.select(".inline-line")):
        if _element_has_placeholder_content(node):
            continue
        if index == 0:
            expr = _pick_key(row_keys, "total_length_km", "length_km", "road_length_km") or (row_keys[0] if row_keys else "value")
        else:
            expr = _pick_key(row_keys, "total_length_m", "length_m", "road_length_m") or (row_keys[0] if row_keys else "value")
        set_placeholder(node, expr)

    for node in soup_out.select(".total-line"):
        if _element_has_placeholder_content(node):
            continue
        set_placeholder(node, _pick_total_expr(row_keys))

    for node in soup_out.find_all(string=_UNDERLINE_RE):
        parent_text = node.parent.get_text(" ", strip=True) if node and node.parent else ""
        expr = choose_expr(0, 0, parent_text, 0)
        node.replace_with("{{" + expr + "}}")

    return str(soup_out)
