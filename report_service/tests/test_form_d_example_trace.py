import shutil
import uuid
from pathlib import Path

import pytest

from app.html_guard import validate_generated_html
from scripts import form_d_example_trace as trace


def _make_workspace_temp_dir(name: str) -> Path:
    path = trace.OUT_DIR / f"pytest-{name}-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def test_repo_inputs_exist_and_are_readable():
    assert trace.ROOT != Path("/")
    assert trace.FORM_PATH == trace.ROOT / "form_d.html"
    assert trace.PROMPT_TXT_PATH == trace.ROOT / "prompt_conversion_dps_new_2026.txt"
    assert trace.FORM_PATH.exists()
    assert trace.PROMPT_TXT_PATH.exists()
    assert trace._read_text(trace.FORM_PATH).lstrip("\ufeff\r\n\t ").startswith("<!doctype html>")
    assert "table_name" in trace._read_text(trace.PROMPT_TXT_PATH)


def test_resolve_project_root_prefers_script_layout_and_never_returns_filesystem_root():
    temp_dir = _make_workspace_temp_dir("script-layout")
    try:
        project_root = temp_dir / "app"
        scripts_dir = project_root / "scripts"
        scripts_dir.mkdir(parents=True)
        (project_root / "form_d.html").write_text("<html></html>", encoding="utf-8")
        (project_root / "prompt_conversion_dps_new_2026.txt").write_text("- table_name: X", encoding="utf-8")
        script_path = scripts_dir / "form_d_example_trace.py"
        script_path.write_text("# placeholder", encoding="utf-8")

        resolved = trace._resolve_project_root(script_path=script_path, cwd=temp_dir / "elsewhere")

        assert resolved == project_root.resolve()
        assert resolved != Path("/")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_resolve_project_root_falls_back_to_cwd_when_script_parent_has_no_assets(monkeypatch):
    temp_dir = _make_workspace_temp_dir("cwd-fallback")
    try:
        cwd_root = temp_dir / "cwd-root"
        cwd_root.mkdir()
        (cwd_root / "form_d.html").write_text("<html></html>", encoding="utf-8")
        (cwd_root / "prompt_conversion_dps_new_2026.txt").write_text("- table_name: X", encoding="utf-8")
        script_path = temp_dir / "broken-layout" / "scripts" / "form_d_example_trace.py"
        script_path.parent.mkdir(parents=True)
        script_path.write_text("# placeholder", encoding="utf-8")

        monkeypatch.setattr(
            trace,
            "_candidate_roots",
            lambda script_path=None, cwd=None: [script_path.parent.parent.resolve(), cwd.resolve()],
        )

        resolved = trace._resolve_project_root(script_path=script_path, cwd=cwd_root)

        assert resolved == cwd_root.resolve()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_resolve_project_root_raises_clear_error_when_assets_missing(monkeypatch):
    temp_dir = _make_workspace_temp_dir("missing-assets")
    try:
        script_path = temp_dir / "missing" / "scripts" / "form_d_example_trace.py"
        script_path.parent.mkdir(parents=True)
        script_path.write_text("# placeholder", encoding="utf-8")

        monkeypatch.setattr(
            trace,
            "_candidate_roots",
            lambda script_path=None, cwd=None: [script_path.parent.parent.resolve(), cwd.resolve()],
        )

        with pytest.raises(RuntimeError, match="Не удалось определить корень проекта"):
            trace._resolve_project_root(script_path=script_path, cwd=temp_dir / "other")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_template_fallback_html_is_valid_for_repo_fixture():
    template_html = trace._read_text(trace.FORM_PATH)
    fixture = trace.parse_fixture_from_txt(trace._read_text(trace.PROMPT_TXT_PATH))
    row_keys = [column["name"] for column in fixture["columns"]]

    fallback_html = trace.build_template_fallback_html(template_html, row_keys=row_keys)

    assert validate_generated_html(template_html, fallback_html)
