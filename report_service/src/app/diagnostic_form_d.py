from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping


SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_REPORT_REQUEST = "Диагностическая генерация HTML формы Д по новым данным."
DEFAULT_FUNCTION_CATALOG = [
    {"name": "value", "description": "Простое значение из строки данных без агрегации.", "example": "{{road_name}}"},
    {"name": "sum", "description": "Сумма значений по колонке.", "example": "{{sum(accident_count)}}"},
    {"name": "count", "description": "Количество строк или непустых значений.", "example": "{{count(road_name)}}"},
    {"name": "avg", "description": "Среднее значение по числовой колонке.", "example": "{{avg(severity_rate)}}"},
    {"name": "min", "description": "Минимальное значение по колонке.", "example": "{{min(report_period)}}"},
    {"name": "max", "description": "Максимальное значение по колонке.", "example": "{{max(report_period)}}"},
    {"name": "if", "description": "Условное выражение для текста и вычислений.", "example": "{{if(count(road_name) > 0, 'Да', 'Нет')}}"},
]


def _candidate_roots() -> List[Path]:
    candidates: List[Path] = []
    for candidate in (SCRIPT_PATH.parent.parent, SCRIPT_PATH.parent.parent.parent, Path("/app"), Path.cwd()):
        resolved = candidate.resolve()
        if resolved not in candidates:
            candidates.append(resolved)
    return candidates


def _resolve_root() -> Path:
    for candidate in _candidate_roots():
        if (candidate / "form_d.html").exists() and (candidate / "prompt_conversion_dps_new_2026.txt").exists():
            return candidate
    raise RuntimeError("Не удалось определить корень report_service для диагностического form_d payload.")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_fixture_from_txt(txt: str) -> Dict[str, Any]:
    table_name = None
    columns: List[Dict[str, str]] = []
    rows: List[Dict[str, Any]] = []

    for line in txt.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("- table_name:"):
            table_name = stripped.split(":", 1)[1].strip()
            continue
        if stripped.lower().startswith("- key="):
            body = stripped[1:].strip()
            parts = [part.strip() for part in body.replace(";", ",").split(",")]
            parsed: Dict[str, str] = {}
            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    parsed[key.strip().lower()] = value.strip()
            if {"key", "name", "type"} <= parsed.keys():
                columns.append({"key": parsed["key"], "name": parsed["name"], "type": parsed["type"]})
            continue
        if stripped.startswith("- {"):
            rows.append(json.loads(stripped[1:].strip()))

    if not table_name or not columns:
        raise RuntimeError("Не удалось собрать диагностический payload для form_d.")

    return {"table_name": table_name, "columns": columns, "rows": rows}


def resolve_form_d_assets(
    template_path: str | Path | None = None,
    prompt_path: str | Path | None = None,
) -> tuple[Path, Path]:
    root = _resolve_root()
    template = Path(template_path) if template_path is not None else root / "form_d.html"
    prompt = Path(prompt_path) if prompt_path is not None else root / "prompt_conversion_dps_new_2026.txt"
    return template.resolve(), prompt.resolve()


def build_form_d_diagnostic_request_from_files(
    template_path: str | Path | None = None,
    prompt_path: str | Path | None = None,
    *,
    mode: str = "stub",
    db: Mapping[str, Any] | None = None,
    debug: bool = True,
    report_request: str | None = None,
    function_catalog: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    template_file, prompt_file = resolve_form_d_assets(template_path=template_path, prompt_path=prompt_path)
    template_html = _read_text(template_file)
    fixture = _parse_fixture_from_txt(_read_text(prompt_file))

    mode_normalized = mode.strip().lower()
    if mode_normalized not in {"stub", "live"}:
        raise ValueError(f"Неподдерживаемый режим запуска: {mode}")

    db_payload: Dict[str, Any]
    if mode_normalized == "stub":
        db_payload = {
            "driver": "stub",
            "host": "stub",
            "port": 5432,
            "user": "stub",
            "password": "stub",
            "database": "report_service_diag",
            "sslmode": None,
        }
    else:
        if not db:
            raise ValueError("Для live mode требуется конфигурация подключения к БД.")
        db_payload = {
            "driver": db.get("driver", "postgresql+psycopg"),
            "host": db["host"],
            "port": db.get("port", 5432),
            "user": db["user"],
            "password": db["password"],
            "database": db.get("database", db.get("name", "")),
            "sslmode": db.get("sslmode"),
        }
        if not db_payload["database"]:
            raise ValueError("Для live mode требуется имя базы данных.")

    return {
        "template_html": template_html,
        "report_request": report_request or DEFAULT_REPORT_REQUEST,
        "db_schema": {
            "tables": [
                {
                    "name": fixture["table_name"],
                    "columns": [{"name": column["name"], "type": column["type"]} for column in fixture["columns"]],
                }
            ],
            "relations": [],
        },
        "function_catalog": function_catalog or DEFAULT_FUNCTION_CATALOG,
        "db": db_payload,
        "debug": debug,
    }


def build_form_d_diagnostic_request() -> Dict[str, Any]:
    return build_form_d_diagnostic_request_from_files(mode="stub", debug=True)
