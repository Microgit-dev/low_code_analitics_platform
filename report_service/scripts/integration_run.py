from __future__ import annotations
import json
from pathlib import Path

from app.dto import ReportGenerationRequest, DbSchema, TableSchema, ColumnSchema, Relation, FunctionCatalogItem, DbConnection
from app.service import ReportGenerationService


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
            TableSchema(name="roads", columns=[
                ColumnSchema(name="id", type="integer"),
                ColumnSchema(name="road_name", type="text"),
                ColumnSchema(name="region", type="text"),
                ColumnSchema(name="created_at", type="date"),
            ]),
            TableSchema(name="repairs", columns=[
                ColumnSchema(name="id", type="integer"),
                ColumnSchema(name="road_id", type="integer"),
                ColumnSchema(name="total_amount", type="numeric"),
                ColumnSchema(name="repair_date", type="date"),
            ]),
        ],
        relations=[Relation(from_table="roads", from_column="id", to_table="repairs", to_column="road_id")],
    )

    function_catalog = [
        FunctionCatalogItem(name="sum", description="Сумма значений", example="{{sum(total_amount)}}"),
        FunctionCatalogItem(name="count", description="Количество строк", example="{{count(roads)}}"),
        FunctionCatalogItem(name="if", description="Условное выражение", example="{{if(count(roads) > 0, 'Да', 'Нет')}}"),
    ]

    db = DbConnection(host="localhost", port=5432, user="postgres", password="postgres", database="low_code")

    return ReportGenerationRequest(
        template_html=template_html,
        report_request="Сформировать отчёт по дорогам, регионам и суммам ремонтов за 2025 год.",
        db_schema=schema,
        function_catalog=function_catalog,
        db=db,
        debug=True,
    )


def main():
    req = build_request()
    service = ReportGenerationService()
    sql, rows, html, debug = service.run(req)

    out = Path(__file__).resolve().parents[1] / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "sql.txt").write_text(sql, encoding="utf-8")
    (out / "rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "result.html").write_text(html, encoding="utf-8")
    (out / "debug.json").write_text(json.dumps(debug, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved outputs to:", out)


if __name__ == "__main__":
    main()
