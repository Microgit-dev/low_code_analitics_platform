from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from app.llm_client import DeepSeekClient
from app.html_guard import validate_generated_html, auto_patch_html, HtmlPostCheckError
from app.prompt_templates import EXAMPLE_CONVERSION_PROMPT_TEMPLATE


SCRIPT_PATH = Path(__file__).resolve()
REQUIRED_INPUT_FILENAMES = ("form_d.html", "prompt_conversion_dps_new_2026.txt")


def _candidate_roots(script_path: Path | None = None, cwd: Path | None = None) -> List[Path]:
    resolved_script = (script_path or SCRIPT_PATH).resolve()
    resolved_cwd = (cwd or Path.cwd()).resolve()

    candidates: List[Path] = []
    for candidate in (resolved_script.parent.parent, Path("/app"), resolved_cwd):
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _resolve_project_root(script_path: Path | None = None, cwd: Path | None = None) -> Path:
    checked: List[str] = []
    for candidate in _candidate_roots(script_path=script_path, cwd=cwd):
        missing = [name for name in REQUIRED_INPUT_FILENAMES if not (candidate / name).exists()]
        if not missing:
            return candidate
        checked.append(f"{candidate} missing: {', '.join(missing)}")

    raise RuntimeError(
        "Не удалось определить корень проекта для form_d_example_trace.py. "
        f"Проверены каталоги: {'; '.join(checked)}"
    )


def _resolve_required_input(root: Path, filename: str) -> Path:
    path = root / filename
    if path.exists():
        return path

    raise RuntimeError(
        f"Не найден обязательный входной файл trace-сценария: {path}. "
        "Проверьте Dockerfile/compose и наличие fixture-файлов в образе."
    )


ROOT = _resolve_project_root()
OUT_DIR = ROOT / "out"
FORM_PATH = _resolve_required_input(ROOT, "form_d.html")
PROMPT_TXT_PATH = _resolve_required_input(ROOT, "prompt_conversion_dps_new_2026.txt")


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def parse_fixture_from_txt(txt: str) -> Dict[str, Any]:
    """
    Максимально простой и детерминированный парсер под текущий формат.
    Извлекает:
      - table_name по строке вида: "- table_name: DPS_NEW_2026" (допускает '=' вместо ':')
      - columns по строкам вида: "- key=name, name=name, type=text" (допускает ';')
      - rows по строкам вида: "- {...}" или "- row_1: {...}"
    Никакого NLP — только регулярки и разбор токенов в 1 строке.
    """
    table_name = None
    columns: List[Dict[str, str]] = []
    rows: List[Dict[str, Any]] = []

    # table_name
    m = re.search(r"^\s*-\s*table_name\s*[:=]\s*([A-Za-z0-9_]+)\s*$", txt, flags=re.IGNORECASE | re.MULTILINE)
    if m:
        table_name = m.group(1)

    # columns: ищем все строки, где встречается шаблон key=..., name=..., type=...
    for line in txt.splitlines():
        if re.search(r"^\s*-\s*key\s*[:=]", line, flags=re.IGNORECASE):
            # удаляем префикс '- '
            s = re.sub(r"^\s*-\s*", "", line.strip())
            # разделители: ',' или ';'
            parts = re.split(r"\s*[,;]\s*", s)
            kv: Dict[str, str] = {}
            for part in parts:
                mm = re.match(r"(?i)(key|name|type)\s*[:=]\s*([A-Za-z0-9_]+)", part.strip())
                if mm:
                    kv[mm.group(1).lower()] = mm.group(2)
            if {"key", "name", "type"}.issubset(kv.keys()):
                columns.append({"key": kv["key"], "name": kv["name"], "type": kv["type"]})

    # rows: любая строка вида '- {...}' или '- row_X: {...}'
    for mrow in re.finditer(r"^\s*-\s*(?:row_\d+\s*[:=]\s*)?(\{.*\})\s*$", txt, flags=re.MULTILINE):
        obj_txt = mrow.group(1)
        try:
            obj = json.loads(obj_txt)
            if isinstance(obj, dict):
                rows.append(obj)
        except Exception:
            # намеренно молча пропускаем, если это не json
            pass

    if not table_name:
        raise RuntimeError("Не удалось извлечь table_name из txt.")
    if not columns:
        raise RuntimeError("Не удалось извлечь columns из txt.")
    if not rows:
        raise RuntimeError("Не удалось извлечь preview rows из txt.")

    return {
        "table_name": table_name,
        "columns": columns,
        "rows": rows,
    }


def build_prompt(base_prompt_text: str, template_html: str, fixture: Dict[str, Any]) -> str:
    fixture_json = json.dumps(fixture, ensure_ascii=False, indent=2)
    return EXAMPLE_CONVERSION_PROMPT_TEMPLATE.format(
        base_prompt_text=base_prompt_text,
        template_html=template_html,
        fixture_json=fixture_json,
    )


def save_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def build_template_fallback_html(template_html: str, row_keys: List[str]) -> str:
    # Preserve the original table structure exactly and only patch missing values.
    return auto_patch_html(template_html, template_html, row_keys=row_keys)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Читаем исходники: HTML-шаблон и базовый промпт
    template_html = _read_text(FORM_PATH)
    base_prompt_text = _read_text(PROMPT_TXT_PATH)

    # 2) Извлекаем test fixture строго из txt
    fixture = parse_fixture_from_txt(base_prompt_text)

    # 3) Собираем финальный промпт
    prompt = build_prompt(base_prompt_text, template_html, fixture)
    save_text(OUT_DIR / "example_fixture.json", json.dumps(fixture, ensure_ascii=False, indent=2))
    save_text(OUT_DIR / "conversion_prompt.txt", prompt)

    # 4) Генерируем HTML через LLM
    llm = DeepSeekClient()
    html_raw = llm.generate_text(prompt).strip()
    save_text(OUT_DIR / "html_raw.html", html_raw)

    status = "OK"
    result_html: str | None = None

    try:
        result_html = validate_generated_html(template_html, html_raw)
        status = "OK"
    except HtmlPostCheckError:
        # 5) Пытаемся autopatch
        row_keys = [c.get("name", "value") for c in fixture.get("columns", [])] or ["value"]
        patched = auto_patch_html(template_html, html_raw, row_keys=row_keys)
        save_text(OUT_DIR / "html_patched.html", patched)
        try:
            result_html = validate_generated_html(template_html, patched)
            status = "OK_AFTER_AUTOPATCH"
        except HtmlPostCheckError as e:
            print("VALIDATION ERROR:", e)
            fallback = build_template_fallback_html(template_html, row_keys=row_keys)
            save_text(OUT_DIR / "html_fallback.html", fallback)
            result_html = validate_generated_html(template_html, fallback)
            status = "OK_AFTER_TEMPLATE_FALLBACK"

    if result_html is not None:
        save_text(OUT_DIR / "result.html", result_html)

    print(status)


if __name__ == "__main__":
    main()
