from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from app import db_executor
from app.db_executor import execute_safe_select
from app.dto import DbConnection
from app.form_d_pipeline import (
    DEFAULT_CONFIG_PATH,
    load_pipeline_config,
    main as pipeline_main,
    parse_cli_config,
    run_form_d_pipeline,
)
from app import service as service_module


def _make_workspace_temp_dir(name: str) -> Path:
    path = DEFAULT_CONFIG_PATH.parents[1] / "out" / f"pytest-{name}-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def test_load_pipeline_config_reads_example():
    config = load_pipeline_config(DEFAULT_CONFIG_PATH)

    assert config.template.name == "form_d.html"
    assert config.prompt.name == "prompt_conversion_dps_new_2026.txt"
    assert config.mode == "stub"
    assert config.db.host == "172.20.10.3"
    assert config.db.name == "dashboard"
    assert any(item["name"] == "sum" for item in config.function_catalog)
    assert any(item["name"] == "value" for item in config.function_catalog)


def test_parse_cli_config_applies_overrides():
    out_dir = _make_workspace_temp_dir("cli-overrides")
    try:
        config = parse_cli_config(
            [
                "--config",
                str(DEFAULT_CONFIG_PATH),
                "--mode",
                "live",
                "--out-dir",
                str(out_dir),
                "--db-host",
                "10.10.10.10",
                "--db-name",
                "custom_db",
                "--db-user",
                "readonly",
            ]
        )

        assert config.mode == "live"
        assert config.out_dir == out_dir.resolve()
        assert config.db.host == "10.10.10.10"
        assert config.db.name == "custom_db"
        assert config.db.user == "readonly"
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def test_entrypoint_stub_run_creates_all_artifacts():
    out_dir = _make_workspace_temp_dir("stub-run")
    try:
        exit_code = pipeline_main(
            [
                "--config",
                str(DEFAULT_CONFIG_PATH),
                "--out-dir",
                str(out_dir),
                "--print-summary",
            ]
        )

        expected_files = [
            "01_input_template.html",
            "02_run_config.json",
            "03_diagnostic_payload.json",
            "04_sql_prompt.txt",
            "05_sql_raw.txt",
            "06_sql_validated.txt",
            "07_rows.json",
            "08_html_prompt.txt",
            "09_html_raw.txt",
            "10_html_extracted.html",
            "11_html_after_guard.html",
            "12_final_result.json",
            "13_final_result.html",
            "14_run_summary.txt",
        ]

        assert exit_code == 0
        for name in expected_files:
            assert (out_dir / name).exists(), name

        final_html = (out_dir / "13_final_result.html").read_text(encoding="utf-8")
        final_result = json.loads((out_dir / "12_final_result.json").read_text(encoding="utf-8"))

        assert "<table" in final_html.lower()
        assert final_result["status"] == "OK"
        assert final_result["mode"] == "stub"
        assert final_result["rows_count"] > 0
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def test_live_pipeline_blocks_unsafe_sql_and_saves_validation_artifact(monkeypatch):
    calls = {"count": 0}

    def fake_generate_text(self, prompt: str) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return "DELETE FROM DPS_NEW_2026"
        return "<html><body>should not happen</body></html>"

    monkeypatch.setattr(service_module.DeepSeekClient, "generate_text", fake_generate_text)

    out_dir = _make_workspace_temp_dir("live-validation")
    try:
        config = load_pipeline_config(DEFAULT_CONFIG_PATH).model_copy(
            update={
                "mode": "live",
                "out_dir": out_dir.resolve(),
                "fail_on_validation_error": False,
            }
        )

        result = run_form_d_pipeline(config)

        assert result.status == "SQL_VALIDATION_ERROR"
        assert result.exit_code == 0
        assert (config.out_dir / "06_sql_validation_error.txt").exists()
        assert "Запрещ" in (config.out_dir / "06_sql_validation_error.txt").read_text(encoding="utf-8")
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def test_execute_safe_select_uses_read_only_guards(monkeypatch):
    executed_sql: list[str] = []
    captured: dict[str, object] = {}

    class DummyRow:
        def __init__(self, mapping):
            self._mapping = mapping

    class DummyResult:
        def __init__(self, rows):
            self._rows = rows

        def keys(self):
            return list(self._rows[0]._mapping.keys())

        def __iter__(self):
            return iter(self._rows)

    class DummyConnection:
        def execute(self, statement):
            sql = str(statement)
            executed_sql.append(sql)
            if sql == "SELECT 1 AS value":
                return DummyResult([DummyRow({"value": 1})])
            return DummyResult([DummyRow({"ok": True})])

    class DummyBegin:
        def __enter__(self):
            return DummyConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyEngine:
        def begin(self):
            return DummyBegin()

        def dispose(self):
            return None

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return DummyEngine()

    monkeypatch.setattr(db_executor, "create_engine", fake_create_engine)

    conn = DbConnection(
        host="172.20.10.3",
        port=5432,
        user="postgres",
        password="postgres",
        database="dashboard",
    )

    rows, columns = execute_safe_select("SELECT 1 AS value", conn)

    assert rows == [{"value": 1}]
    assert columns == ["value"]
    assert captured["url"] == "postgresql+psycopg://postgres:postgres@172.20.10.3:5432/dashboard"
    assert captured["kwargs"]["connect_args"]["options"] == "-c default_transaction_read_only=on"
    assert "SET LOCAL statement_timeout = " in executed_sql[0]
    assert executed_sql[1] == "SET LOCAL default_transaction_read_only = on"
    assert executed_sql[2] == "SELECT 1 AS value"
