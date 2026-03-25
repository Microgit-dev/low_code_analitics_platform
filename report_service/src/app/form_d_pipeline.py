from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from .diagnostic_form_d import (
    DEFAULT_FUNCTION_CATALOG,
    DEFAULT_REPORT_REQUEST,
    build_form_d_diagnostic_request_from_files,
    resolve_form_d_assets,
)
from .dto import ReportGenerationRequest
from .html_guard import HtmlPostCheckError
from .service import ReportGenerationService
from .sql_validator import SqlValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "examples" / "form_d_run_config.json"
DEFAULT_OUT_DIR = PROJECT_ROOT / "out" / "form_d_run"
REDACTED = "***redacted***"


class PipelineDbConfig(BaseModel):
    driver: str = "postgresql+psycopg"
    host: str = "172.20.10.3"
    port: int = 5432
    name: str = "dashboard"
    user: str = "postgres"
    password: str = "postgres"
    sslmode: str | None = None

    def to_request_dict(self) -> Dict[str, Any]:
        return {
            "driver": self.driver,
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "name": self.name,
            "database": self.name,
            "sslmode": self.sslmode,
        }

    def to_redacted_dict(self) -> Dict[str, Any]:
        data = self.to_request_dict()
        data["password"] = REDACTED
        return data


class FormDPipelineConfig(BaseModel):
    template: Path = Field(default=PROJECT_ROOT / "form_d.html")
    prompt: Path = Field(default=PROJECT_ROOT / "prompt_conversion_dps_new_2026.txt")
    mode: Literal["stub", "live"] = "stub"
    debug: bool = True
    trace: bool = True
    out_dir: Path = Field(default=DEFAULT_OUT_DIR)
    report_request: str = DEFAULT_REPORT_REQUEST
    function_catalog: List[Dict[str, Any]] = Field(default_factory=lambda: [item.copy() for item in DEFAULT_FUNCTION_CATALOG])
    db: PipelineDbConfig = Field(default_factory=PipelineDbConfig)
    fail_on_validation_error: bool = False
    print_summary: bool = False

    def to_redacted_dict(self) -> Dict[str, Any]:
        data = self.model_dump(mode="json")
        data["db"] = self.db.to_redacted_dict()
        return data


class PipelineRunResult(BaseModel):
    success: bool
    status: str
    exit_code: int
    mode: Literal["stub", "live"]
    out_dir: Path
    sql: str | None = None
    rows_count: int = 0
    error: str | None = None
    validation_error: str | None = None
    final_html_path: Path | None = None
    summary: str = ""


def _resolve_path(raw_path: str | Path, base_dir: Path) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def _load_config_data(config_path: Path) -> Dict[str, Any]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    db_data = data.get("db", {})
    if "db_name" in data and "name" not in db_data:
        db_data["name"] = data["db_name"]
    data["db"] = db_data

    base_dir = config_path.parent.resolve()
    for key in ("template", "template_path"):
        if key in data:
            data["template"] = _resolve_path(data[key], base_dir)
            break
    for key in ("prompt", "prompt_path"):
        if key in data:
            data["prompt"] = _resolve_path(data[key], base_dir)
            break
    for key in ("out_dir", "artifacts_dir"):
        if key in data:
            data["out_dir"] = _resolve_path(data[key], base_dir)
            break

    return data


def load_pipeline_config(config_path: str | Path | None = None) -> FormDPipelineConfig:
    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    resolved = path.resolve()
    data = _load_config_data(resolved)
    return FormDPipelineConfig.model_validate(data)


def _apply_cli_overrides(config: FormDPipelineConfig, args: argparse.Namespace) -> FormDPipelineConfig:
    updates: Dict[str, Any] = {}

    if args.mode:
        updates["mode"] = args.mode
    if args.template:
        updates["template"] = Path(args.template).resolve()
    if args.prompt:
        updates["prompt"] = Path(args.prompt).resolve()
    if args.out_dir:
        updates["out_dir"] = Path(args.out_dir).resolve()
    if args.fail_on_validation_error:
        updates["fail_on_validation_error"] = True
    if args.print_summary:
        updates["print_summary"] = True

    db_updates: Dict[str, Any] = {}
    if args.db_host:
        db_updates["host"] = args.db_host
    if args.db_port is not None:
        db_updates["port"] = args.db_port
    if args.db_name:
        db_updates["name"] = args.db_name
    if args.db_user:
        db_updates["user"] = args.db_user
    if args.db_password:
        db_updates["password"] = args.db_password
    if db_updates:
        updates["db"] = config.db.model_copy(update=db_updates)

    if not updates:
        return config
    return config.model_copy(update=updates)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the full form_d pipeline from one entrypoint.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--mode", choices=("stub", "live"))
    parser.add_argument("--template")
    parser.add_argument("--prompt")
    parser.add_argument("--out-dir")
    parser.add_argument("--db-host")
    parser.add_argument("--db-port", type=int)
    parser.add_argument("--db-name")
    parser.add_argument("--db-user")
    parser.add_argument("--db-password")
    parser.add_argument("--fail-on-validation-error", action="store_true")
    parser.add_argument("--print-summary", action="store_true")
    return parser


def _redact_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = json.loads(json.dumps(payload, ensure_ascii=False))
    if "db" in data and isinstance(data["db"], dict) and "password" in data["db"]:
        data["db"]["password"] = REDACTED
    return data


def _placeholder_text(reason: str) -> str:
    return f"Unavailable.\n{reason}\n"


def _placeholder_html(reason: str) -> str:
    safe_reason = reason.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        "<!doctype html><html lang=\"ru\"><body><h1>Artifact unavailable</h1><pre>"
        + safe_reason
        + "</pre></body></html>"
    )


def _extract_html_candidate(raw_html: str | None) -> str | None:
    if not raw_html:
        return None

    text = raw_html.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 3:
            candidate = parts[1]
            if candidate.lower().startswith("html"):
                candidate = candidate[4:]
            return candidate.strip()
    return text


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    _write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _build_summary(
    *,
    config: FormDPipelineConfig,
    status: str,
    success: bool,
    sql: str | None,
    rows_count: int,
    error: str | None,
    validation_error: str | None,
    duration_seconds: float,
    out_dir: Path,
) -> str:
    lines = [
        f"status: {status}",
        f"success: {success}",
        f"mode: {config.mode}",
        f"out_dir: {out_dir}",
        f"rows_count: {rows_count}",
        f"duration_seconds: {duration_seconds:.3f}",
        f"template: {config.template}",
        f"prompt: {config.prompt}",
        f"db_host: {config.db.host if config.mode == 'live' else 'stub'}",
        f"db_name: {config.db.name if config.mode == 'live' else 'stub'}",
    ]
    if sql:
        lines.append(f"sql_present: yes ({len(sql)} chars)")
    else:
        lines.append("sql_present: no")
    if validation_error:
        lines.append(f"validation_error: {validation_error}")
    if error:
        lines.append(f"error: {error}")
    return "\n".join(lines) + "\n"


def run_form_d_pipeline(config: FormDPipelineConfig) -> PipelineRunResult:
    started_at = perf_counter()
    config = config.model_copy(
        update={
            "template": config.template.resolve(),
            "prompt": config.prompt.resolve(),
            "out_dir": config.out_dir.resolve(),
        }
    )
    out_dir = config.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    template_path, prompt_path = resolve_form_d_assets(config.template, config.prompt)
    payload = build_form_d_diagnostic_request_from_files(
        template_path=template_path,
        prompt_path=prompt_path,
        mode=config.mode,
        db=config.db.to_request_dict(),
        debug=config.debug,
        report_request=config.report_request,
        function_catalog=config.function_catalog,
    )
    req = ReportGenerationRequest.model_validate(payload)

    trace: Dict[str, Any] = {}
    sql: str | None = None
    rows: List[Dict[str, Any]] = []
    html: str | None = None
    debug_info: Dict[str, Any] = {}
    status = "UNKNOWN"
    success = False
    error: str | None = None
    validation_error: str | None = None

    try:
        sql, rows, html, debug_info = ReportGenerationService().run(req, trace=trace)
        status = "OK"
        success = True
    except SqlValidationError as exc:
        validation_error = str(exc)
        status = "SQL_VALIDATION_ERROR"
        trace.setdefault("sql_validation_error", validation_error)
    except Exception as exc:
        error = str(exc)
        status = exc.__class__.__name__
        trace["exception_type"] = exc.__class__.__name__
        trace["exception_message"] = str(exc)
        trace["traceback"] = traceback.format_exc()

    final_html = html or trace.get("html_after_guard")
    rows_count = len(rows or trace.get("rows", []))
    duration_seconds = perf_counter() - started_at

    sql_prompt = trace.get("sql_prompt") or _placeholder_text("SQL prompt not produced. Stage was skipped or failed before prompt generation.")
    sql_raw = trace.get("sql_raw") or _placeholder_text("Raw SQL not produced. Stage was skipped or failed before LLM SQL output.")
    html_prompt = trace.get("html_prompt") or _placeholder_text("HTML prompt not produced. Stage was skipped or failed before prompt generation.")
    html_raw = trace.get("html_raw") or _placeholder_text("Raw HTML not produced. Stage was skipped or failed before LLM HTML output.")
    html_extracted = _extract_html_candidate(trace.get("html_raw")) or _placeholder_html(
        "HTML candidate could not be extracted because raw HTML output was unavailable."
    )
    html_after_guard = final_html or _placeholder_html(
        validation_error
        or error
        or "HTML guard stage did not produce a final HTML document."
    )
    final_result_html = final_html or _placeholder_html(
        validation_error
        or error
        or "Final HTML result was not produced."
    )

    _write_text(out_dir / "01_input_template.html", req.template_html)
    _write_json(out_dir / "02_run_config.json", config.to_redacted_dict())
    _write_json(out_dir / "03_diagnostic_payload.json", _redact_payload(payload))
    _write_text(out_dir / "04_sql_prompt.txt", sql_prompt)
    _write_text(out_dir / "05_sql_raw.txt", sql_raw)
    if validation_error:
        _write_text(out_dir / "06_sql_validation_error.txt", validation_error + "\n")
    else:
        _write_text(
            out_dir / "06_sql_validated.txt",
            (trace.get("sql_validated") or sql or _placeholder_text("Validated SQL is unavailable.")) + "\n",
        )
    _write_json(
        out_dir / "07_rows.json",
        rows if rows else {"status": "unavailable", "reason": validation_error or error or "No rows were fetched."},
    )
    _write_text(out_dir / "08_html_prompt.txt", html_prompt)
    _write_text(out_dir / "09_html_raw.txt", html_raw)
    _write_text(out_dir / "10_html_extracted.html", html_extracted)
    _write_text(out_dir / "11_html_after_guard.html", html_after_guard)

    exit_code = 0
    if validation_error and config.fail_on_validation_error:
        exit_code = 2
    elif error:
        exit_code = 1

    summary = _build_summary(
        config=config,
        status=status,
        success=success,
        sql=trace.get("sql_validated") or sql,
        rows_count=rows_count,
        error=error,
        validation_error=validation_error,
        duration_seconds=duration_seconds,
        out_dir=out_dir,
    )

    final_result = {
        "success": success,
        "status": status,
        "mode": config.mode,
        "debug": config.debug,
        "trace": config.trace,
        "sql": trace.get("sql_validated") or sql,
        "rows_count": rows_count,
        "error": error,
        "validation_error": validation_error,
        "debug_info": debug_info,
        "artifacts_dir": str(out_dir),
        "artifacts": {
            "sql_prompt": str(out_dir / "04_sql_prompt.txt"),
            "sql_raw": str(out_dir / "05_sql_raw.txt"),
            "sql_validated_or_error": str(
                out_dir / ("06_sql_validation_error.txt" if validation_error else "06_sql_validated.txt")
            ),
            "rows": str(out_dir / "07_rows.json"),
            "html_prompt": str(out_dir / "08_html_prompt.txt"),
            "html_raw": str(out_dir / "09_html_raw.txt"),
            "html_extracted": str(out_dir / "10_html_extracted.html"),
            "html_after_guard": str(out_dir / "11_html_after_guard.html"),
            "final_html": str(out_dir / "13_final_result.html"),
        },
        "summary": summary,
    }
    _write_json(out_dir / "12_final_result.json", final_result)
    _write_text(out_dir / "13_final_result.html", final_result_html)
    _write_text(out_dir / "14_run_summary.txt", summary)

    return PipelineRunResult(
        success=success,
        status=status,
        exit_code=exit_code,
        mode=config.mode,
        out_dir=out_dir,
        sql=trace.get("sql_validated") or sql,
        rows_count=rows_count,
        error=error,
        validation_error=validation_error,
        final_html_path=out_dir / "13_final_result.html",
        summary=summary,
    )


def parse_cli_config(argv: List[str] | None = None) -> FormDPipelineConfig:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    config = load_pipeline_config(args.config)
    return _apply_cli_overrides(config, args)


def main(argv: List[str] | None = None) -> int:
    config = parse_cli_config(argv)
    result = run_form_d_pipeline(config)
    if config.print_summary:
        print(result.summary, end="")
    return result.exit_code
