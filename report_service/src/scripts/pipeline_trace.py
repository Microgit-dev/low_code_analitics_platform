from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import List

from app.dto import (
    ReportGenerationRequest,
    DbSchema,
    TableSchema,
    ColumnSchema,
    Relation,
    FunctionCatalogItem,
    DbConnection,
)
from app.prompt_templates import SQL_PROMPT_TEMPLATE, HTML_PROMPT_TEMPLATE
from app.llm_client import DeepSeekClient
from app.sql_validator import SafeSqlValidator
from app.db_executor import execute_safe_select
from app.html_guard import validate_generated_html, auto_patch_html, HtmlPostCheckError


def build_request() -> ReportGenerationRequest:
    template_html = (
        """
        <html><body>
        <h2>Отчёт по ремонтам дорог за 2025</h2>
        <table border="1">
          <thead>
            <tr><th>Дорога</th><th>Регион</th><th>Сумма</th><th>Дата</th></tr>
          </thead>
          <tbody>
            <tr><td>_____</td><td>_____</td><td></td><td>_____</td></tr>
          </tbody>
        </table>
        <p>Итого: ____________</p>
        </body></html>
        """
    ).strip()

    schema = DbSchema(
        tables=[
            TableSchema(
                name="roads",
                columns=[
                    ColumnSchema(name="id", type="integer"),
                    ColumnSchema(name="road_name", type="text"),
                    ColumnSchema(name="region", type="text"),
                    ColumnSchema(name="created_at", type="date"),
                ],
            ),
            TableSchema(
                name="repairs",
                columns=[
                    ColumnSchema(name="id", type="integer"),
                    ColumnSchema(name="road_id", type="integer"),
                    ColumnSchema(name="total_amount", type="numeric"),
                    ColumnSchema(name="repair_date", type="date"),
                ],
            ),
        ],
        relations=[
            Relation(
                from_table="roads",
                from_column="id",
                to_table="repairs",
                to_column="road_id",
            )
        ],
    )

    function_catalog = [
        FunctionCatalogItem(
            name="sum",
            description="Сумма значений",
            example="{{sum(total_amount)}}",
        ),
        FunctionCatalogItem(
            name="count",
            description="Количество строк",
            example="{{count(roads)}}",
        ),
        FunctionCatalogItem(
            name="if",
            description="Условное выражение",
            example="{{if(count(roads) > 0, 'Да', 'Нет')}}",
        ),
    ]

    db = DbConnection(
        host=os.getenv("DB_HOST", "host.docker.internal"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        database=os.getenv("DB_NAME", "low_code"),
    )

    return ReportGenerationRequest(
        template_html=template_html,
        report_request="Сформировать отчёт по дорогам, регионам и суммам ремонтов за 2025 год.",
        db_schema=schema,
        function_catalog=function_catalog,
        db=db,
        debug=True,
    )


def build_total_placeholder(columns: List[str]) -> str:
    if "Сумма" in columns:
        return "{{sum(Сумма)}}"
    if columns:
        return f"{{{{{columns[0]}}}}}"
    return "{{value}}"


def render_fallback_html(template_html: str, columns: List[str], rows_count: int) -> str:
    """
    Детерминированный fallback:
    - сохраняет исходный шаблон
    - расширяет tbody до нужного количества строк
    - заменяет подчёркивания и пустые ячейки на {{...}}
    """
    safe_columns = columns[:] if columns else ["value"]
    placeholder_row = "<tr>" + "".join(f"<td>{{{{{col}}}}}</td>" for col in safe_columns) + "</tr>"
    body_rows = "\n".join(placeholder_row for _ in range(max(1, rows_count)))

    html = template_html

    # Полностью заменяем содержимое tbody на нужное число строк с placeholders
    html = re.sub(
        r"<tbody>.*?</tbody>",
        f"<tbody>\n{body_rows}\n</tbody>",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Подчёркивания в обычном тексте
    total_placeholder = build_total_placeholder(safe_columns)
    html = re.sub(
        r"(Итого:\s*)_{3,}",
        rf"\1{total_placeholder}",
        html,
        flags=re.IGNORECASE,
    )

    # На случай других подчёркиваний вне таблицы
    html = re.sub(r"_{3,}", "{{value}}", html)

    # На случай пустых ячеек, если где-то остались
    html = re.sub(r"<td>\s*</td>", "<td>{{value}}</td>", html, flags=re.IGNORECASE)
    html = re.sub(r"<th>\s*</th>", "<th>{{value}}</th>", html, flags=re.IGNORECASE)

    return html


def save_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def main() -> None:
    req = build_request()
    out_dir = Path(__file__).resolve().parents[1] / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) LLM -> SQL
    schema_json = json.dumps(req.db_schema.model_dump(), ensure_ascii=False, indent=2)
    sql_prompt = SQL_PROMPT_TEMPLATE.format(
        template_html=req.template_html,
        db_schema=schema_json,
        report_request=req.report_request,
    )

    print("=== PROMPT(SQL) HEAD ===")
    print(sql_prompt[:800])
    print()

    llm = DeepSeekClient()
    sql_raw = llm.generate_text(sql_prompt).strip()

    print("=== SQL ===")
    print(sql_raw)

    sql_valid = SafeSqlValidator(req.db_schema).validate(sql_raw)

    print("\n=== SQL(valid) ===")
    print(sql_valid)

    # 2) Execute SQL
    rows, columns = execute_safe_select(sql_valid, req.db)

    print("\n=== COLUMNS ===", columns)
    print("=== ROWS(count) ===", len(rows))
    print("=== ROWS(sample) ===", rows[:3] if rows else [])

    save_text(out_dir / "sql_prompt.txt", sql_prompt)
    save_text(out_dir / "sql_raw.txt", sql_raw)
    save_text(out_dir / "sql.txt", sql_valid)
    save_text(
        out_dir / "rows.json",
        json.dumps(rows, ensure_ascii=False, default=str, indent=2),
    )

    # 3) LLM -> HTML
    rows_json = json.dumps(rows, ensure_ascii=False, default=str)
    func_json = json.dumps(
        [f.model_dump() for f in req.function_catalog],
        ensure_ascii=False,
        indent=2,
    )

    html_prompt = HTML_PROMPT_TEMPLATE.format(
        template_html=req.template_html,
        query_rows_json=rows_json,
        function_catalog=func_json,
    )

    print("\n=== PROMPT(HTML) HEAD ===")
    print(html_prompt[:800])
    print()

    html_raw = llm.generate_text(html_prompt).strip()

    save_text(out_dir / "html_prompt.txt", html_prompt)
    save_text(out_dir / "html_raw.html", html_raw)

    status = "OK"

    try:
        html_ok = validate_generated_html(req.template_html, html_raw)

    except HtmlPostCheckError as e1:
        print("=== HTML VALIDATION ERROR (RAW) ===")
        print(str(e1))

        patched = auto_patch_html(req.template_html, html_raw, row_keys=columns or ["value"])
        save_text(out_dir / "html_patched.html", patched)

        try:
            html_ok = validate_generated_html(req.template_html, patched)
            status = "OK_AFTER_AUTOPATCH"

        except HtmlPostCheckError as e2:
            print("=== HTML VALIDATION ERROR (PATCHED) ===")
            print(str(e2))

            fallback = render_fallback_html(
                template_html=req.template_html,
                columns=columns,
                rows_count=len(rows),
            )
            save_text(out_dir / "html_fallback.html", fallback)

            html_ok = validate_generated_html(req.template_html, fallback)
            status = "OK_AFTER_FALLBACK"

    print("=== HTML STATUS ===", status)
    save_text(out_dir / "result.html", html_ok)
    print("Saved:", out_dir)


if __name__ == "__main__":
    main()