from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from .config import settings
from .db_executor import execute_safe_select
from .dto import ReportGenerationRequest
from .html_guard import HtmlPostCheckError, auto_patch_html, validate_generated_html
from .llm_client import DeepSeekClient
from .prompt_templates import HTML_PROMPT_TEMPLATE, SQL_PROMPT_TEMPLATE
from .sql_validator import SafeSqlValidator

logger = logging.getLogger(__name__)


class ReportGenerationService:
    def __init__(self):
        self.llm = DeepSeekClient()

    @staticmethod
    def _record_trace(trace: Optional[Dict[str, Any]], key: str, value: Any) -> None:
        if trace is not None:
            trace[key] = value

    @staticmethod
    def _is_stub_mode(req: ReportGenerationRequest) -> bool:
        driver = (req.db.driver or "").strip().lower()
        host = (req.db.host or "").strip().lower()
        return req.debug and (driver == "stub" or host == "stub")

    @staticmethod
    def _sample_value(column_name: str, column_type: str, row_index: int) -> Any:
        name = column_name.lower()
        ctype = column_type.lower()

        if "owner" in name or "organization" in name:
            return "ГКУ Дирекция развития УДС"
        if "report_period" in name:
            return "2026 год"
        if "length_km" in name:
            return 152
        if "length_m" in name:
            return 340
        if "road" in name and "name" in name:
            return f"Диагностическая дорога {row_index + 1}"
        if "region" in name:
            return ["Центральный", "Северный", "Южный"][row_index % 3]
        if "period_label" in name or name == "period":
            return ["АППГ", "Период учета", "(+/-, %)"][row_index % 3]
        if "date" in name:
            return f"2026-01-0{row_index + 1}"
        if "share" in name or "rate" in name or ctype in {"numeric", "number", "float", "double"}:
            return round(10.5 + row_index * 2.25, 2)
        if "count" in name or ctype in {"integer", "int", "bigint", "smallint"}:
            return 10 + row_index * 3
        if ctype in {"boolean", "bool"}:
            return row_index % 2 == 0
        return f"{column_name}_{row_index + 1}"

    def _run_stub_mode(
        self,
        req: ReportGenerationRequest,
        debug_info: Dict[str, Any],
        trace: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[Dict[str, Any]], str, Dict[str, Any]]:
        if not req.db_schema.tables or not req.db_schema.tables[0].columns:
            raise RuntimeError("Для diagnostic stub mode требуется хотя бы одна таблица с колонками в db_schema.")

        table = req.db_schema.tables[0]
        columns = [column.name for column in table.columns]
        sql = f"SELECT {', '.join(columns)} FROM {table.name}"
        sql_valid = SafeSqlValidator(req.db_schema).validate(sql)

        rows = []
        for row_index in range(2):
            rows.append(
                {
                    column.name: self._sample_value(column.name, column.type, row_index)
                    for column in table.columns
                }
            )

        html_ok = auto_patch_html(req.template_html, req.template_html, row_keys=columns or ["value"])
        html_ok = validate_generated_html(req.template_html, html_ok)

        debug_info["stub_mode"] = True
        debug_info["rows_count"] = len(rows)
        debug_info["columns"] = columns
        debug_info["html_status"] = "OK_STUB"

        self._record_trace(trace, "stub_mode", True)
        self._record_trace(trace, "sql_validated", sql_valid)
        self._record_trace(trace, "rows", rows)
        self._record_trace(trace, "columns", columns)
        self._record_trace(trace, "html_after_guard", html_ok)
        self._record_trace(trace, "html_status", "OK_STUB")

        return sql_valid, rows, html_ok, debug_info

    def _finalize_html(
        self,
        template_html: str,
        html_raw: str,
        row_keys: List[str],
        debug_info: Dict[str, Any],
        trace: Optional[Dict[str, Any]] = None,
    ) -> str:
        try:
            html_ok = validate_generated_html(template_html, html_raw)
            debug_info["html_status"] = "OK"
            self._record_trace(trace, "html_after_guard", html_ok)
            self._record_trace(trace, "html_status", "OK")
            return html_ok
        except HtmlPostCheckError as raw_error:
            patched = auto_patch_html(template_html, html_raw, row_keys=row_keys or ["value"])
            debug_info["html_status"] = "OK_AFTER_AUTOPATCH"
            debug_info["html_raw_validation_error"] = str(raw_error)
            html_ok = validate_generated_html(template_html, patched)
            self._record_trace(trace, "html_guard_error", str(raw_error))
            self._record_trace(trace, "html_after_guard", html_ok)
            self._record_trace(trace, "html_status", "OK_AFTER_AUTOPATCH")
            return html_ok

    def run(
        self,
        req: ReportGenerationRequest,
        trace: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[Dict[str, Any]], str, Dict[str, Any]]:
        debug_info: Dict[str, Any] = {}

        if self._is_stub_mode(req):
            return self._run_stub_mode(req, debug_info, trace=trace)

        schema_json = json.dumps(req.db_schema.model_dump(), ensure_ascii=False, indent=2)
        sql_prompt = SQL_PROMPT_TEMPLATE.format(
            template_html=req.template_html,
            db_schema=schema_json,
            report_request=req.report_request,
        )
        self._record_trace(trace, "stub_mode", False)
        self._record_trace(trace, "sql_prompt", sql_prompt)
        if req.debug or settings.debug:
            debug_info["sql_prompt"] = sql_prompt[:4000]

        sql_raw = self.llm.generate_text(sql_prompt)
        self._record_trace(trace, "sql_raw", sql_raw)
        logger.info("LLM SQL: %s", sql_raw)

        validator = SafeSqlValidator(req.db_schema)
        try:
            sql_valid = validator.validate(sql_raw)
        except Exception as exc:
            self._record_trace(trace, "sql_validation_error", str(exc))
            raise
        self._record_trace(trace, "sql_validated", sql_valid)

        try:
            rows, columns = execute_safe_select(sql_valid, req.db)
        except Exception as exc:
            self._record_trace(trace, "db_execution_error", str(exc))
            raise
        self._record_trace(trace, "rows", rows)
        self._record_trace(trace, "columns", columns)
        if req.debug or settings.debug:
            debug_info["rows_count"] = len(rows)
            debug_info["columns"] = columns

        rows_json = json.dumps(rows, ensure_ascii=False, default=str)
        func_json = json.dumps([f.model_dump() for f in req.function_catalog], ensure_ascii=False, indent=2)
        html_prompt = HTML_PROMPT_TEMPLATE.format(
            template_html=req.template_html,
            query_rows_json=rows_json,
            function_catalog=func_json,
        )
        self._record_trace(trace, "html_prompt", html_prompt)
        if req.debug or settings.debug:
            debug_info["html_prompt"] = html_prompt[:4000]

        html_raw = self.llm.generate_text(html_prompt)
        self._record_trace(trace, "html_raw", html_raw)
        html_ok = self._finalize_html(req.template_html, html_raw, columns, debug_info, trace=trace)

        return sql_valid, rows, html_ok, debug_info
