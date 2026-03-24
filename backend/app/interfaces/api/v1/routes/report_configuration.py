import logging
import csv
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
import re
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile
import zipfile
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.use_cases.workspace.manage_reports import (
    CreateReportConfigurationUseCase,
    DeleteReportConfigurationUseCase,
    GetPublicReportConfigurationUseCase,
    GetReportConfigurationUseCase,
    ListReportConfigurationsUseCase,
    ReportConfigurationNotFoundError,
    UpdateReportConfigurationUseCase,
)
from app.domain.entities.report_configuration import ReportConfiguration
from app.domain.repositories.report_configuration_repository import ReportConfigurationRepository
from app.infrastructure.db.models.table_data_record_model import TableDataRecordModel
from app.infrastructure.db.models.table_structure_model import TableStructureModel
from app.infrastructure.db.models.workspace_model import WorkspaceModel
from app.infrastructure.repositories.sqlalchemy_report_configuration_repository import (
    SQLAlchemyReportConfigurationRepository,
)
from app.interfaces.api.dependencies.auth import get_current_user
from app.interfaces.api.dependencies.db import get_db
from app.interfaces.api.v1.schemas.report_configuration import (
    DashboardChartPointResponse,
    DashboardChartResponse,
    DashboardMetricResponse,
    PublicDashboardResponse,
    PublicDashboardWidgetResponse,
    ReportConfigurationCreateRequest,
    ReportConfigurationResponse,
    ReportConfigurationUpdateRequest,
)

router = APIRouter()
logger = logging.getLogger("uvicorn.error")
TEMPLATE_FIELD_PATTERN = re.compile(r"\{\{\s*(.*?)\s*\}\}")
TEMPLATE_AGGREGATION_PATTERN = re.compile(r"^(?P<func>[a-zA-Z_]\w*)\s*\(\s*(?P<key>[^()]+)\s*\)$")


def get_report_repo(session: Session = Depends(get_db)) -> ReportConfigurationRepository:
    return SQLAlchemyReportConfigurationRepository(session)


def _map_report(report: ReportConfiguration) -> ReportConfigurationResponse:
    now = datetime.utcnow()
    # Backward compatibility: convert old 'excel_export' type to new 'table_export'
    report_type = report.report_type
    if report_type == 'excel_export':
        report_type = 'table_export'
    
    return ReportConfigurationResponse(
        id=report.id,
        workspace_id=report.workspace_id,
        name=report.name,
        description=report.description,
        report_type=report_type,
        settings=report.settings,
        is_published=report.is_published,
        created_at=report.created_at or now,
        updated_at=report.updated_at or now,
    )


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


def _extract_metric_values(rows: list[TableDataRecordModel], field_key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        number = _to_number((row.data_json or {}).get(field_key))
        if number is not None:
            values.append(number)
    return values


def _build_chart_points(
    rows: list[TableDataRecordModel],
    group_by_key: str,
    aggregation: str,
    value_key: str | None,
    limit: int,
) -> list[DashboardChartPointResponse]:
    buckets: dict[str, list[float]] = {}
    counts: dict[str, int] = {}

    for row in rows:
        raw_group = (row.data_json or {}).get(group_by_key)
        if raw_group is None:
            continue

        group = str(raw_group)
        counts[group] = counts.get(group, 0) + 1

        if value_key:
            value_number = _to_number((row.data_json or {}).get(value_key))
            if value_number is not None:
                buckets.setdefault(group, []).append(value_number)

    if aggregation == "count":
        sorted_items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        return [
            DashboardChartPointResponse(label=label, value=value)
            for label, value in sorted_items[:limit]
        ]

    calculated: list[tuple[str, float]] = []
    for label, values in buckets.items():
        if not values:
            continue
        if aggregation == "sum":
            result = sum(values)
        elif aggregation == "avg":
            result = sum(values) / len(values)
        elif aggregation == "min":
            result = min(values)
        elif aggregation == "max":
            result = max(values)
        else:
            result = 0.0
        calculated.append((label, round(result, 2)))

    sorted_items = sorted(calculated, key=lambda item: item[1], reverse=True)
    return [DashboardChartPointResponse(label=label, value=value) for label, value in sorted_items[:limit]]


def _assert_workspace_owner(session: Session, workspace_id: int, owner_id: int) -> None:
    workspace = session.execute(
        select(WorkspaceModel).where(
            WorkspaceModel.id == workspace_id,
            WorkspaceModel.owner_id == owner_id,
        )
    ).scalar()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _normalize_dashboard_settings(settings: dict[str, Any]) -> dict[str, Any]:
    table_id = settings.get("table_id")
    metrics = settings.get("metrics")
    charts = settings.get("charts")
    recent_limit = settings.get("recent_limit")

    if isinstance(table_id, int) and isinstance(metrics, list) and isinstance(charts, list):
        return {
            "table_id": table_id,
            "metrics": metrics,
            "charts": charts,
            "recent_limit": recent_limit if isinstance(recent_limit, int) and recent_limit > 0 else 10,
        }

    widgets = settings.get("widgets")
    if not isinstance(widgets, list):
        return {
            "table_id": table_id,
            "metrics": metrics if isinstance(metrics, list) else [],
            "charts": charts if isinstance(charts, list) else [],
            "recent_limit": recent_limit if isinstance(recent_limit, int) and recent_limit > 0 else 10,
        }

    normalized_metrics: list[dict[str, Any]] = []
    normalized_charts: list[dict[str, Any]] = []
    normalized_table_id: int | None = table_id if isinstance(table_id, int) else None
    normalized_recent_limit = recent_limit if isinstance(recent_limit, int) and recent_limit > 0 else 10

    for widget in widgets:
        if not isinstance(widget, dict):
            continue

        widget_type = str(widget.get("type") or "")
        source = widget.get("source")
        source_table_id = source.get("table_id") if isinstance(source, dict) else None
        query = widget.get("query") if isinstance(widget.get("query"), dict) else {}
        presentation = widget.get("presentation") if isinstance(widget.get("presentation"), dict) else {}

        if normalized_table_id is None and isinstance(source_table_id, int):
            normalized_table_id = source_table_id

        if widget_type == "table" and isinstance(source_table_id, int):
            normalized_table_id = source_table_id
            limit_raw = query.get("limit")
            if isinstance(limit_raw, int) and limit_raw > 0:
                normalized_recent_limit = limit_raw

        if widget_type == "metric":
            aggregation = str(query.get("aggregation") or "count")
            field_key = query.get("field_key")
            normalized_metrics.append(
                {
                    "label": str(widget.get("title") or ""),
                    "aggregation": aggregation,
                    "field_key": field_key if isinstance(field_key, str) and field_key else None,
                }
            )

        if widget_type == "chart":
            group_by_key = query.get("group_by_key")
            if not isinstance(group_by_key, str) or not group_by_key:
                continue

            aggregation = str(query.get("aggregation") or "count")
            value_key = query.get("field_key")
            limit_raw = query.get("limit")
            normalized_charts.append(
                {
                    "title": str(widget.get("title") or ""),
                    "chart_type": "bar",
                    "color": presentation.get("color") if isinstance(presentation.get("color"), str) else None,
                    "group_by_key": group_by_key,
                    "aggregation": aggregation,
                    "value_key": value_key if isinstance(value_key, str) and value_key else None,
                    "limit": limit_raw if isinstance(limit_raw, int) and limit_raw > 0 else 10,
                }
            )

    return {
        "table_id": normalized_table_id,
        "metrics": normalized_metrics,
        "charts": normalized_charts,
        "recent_limit": normalized_recent_limit,
    }


def _normalize_table_report_settings(settings: dict[str, Any]) -> list[dict[str, Any]]:
    datasets = settings.get("datasets")
    if isinstance(datasets, list) and datasets:
        normalized: list[dict[str, Any]] = []
        for index, dataset in enumerate(datasets):
            if not isinstance(dataset, dict):
                continue
            table_id = dataset.get("table_id")
            if not isinstance(table_id, int):
                continue
            columns_raw = dataset.get("columns")
            columns: list[dict[str, Any]] = []
            if isinstance(columns_raw, list):
                for column in columns_raw:
                    if not isinstance(column, dict):
                        continue
                    key = column.get("key")
                    if not isinstance(key, str) or not key:
                        continue
                    label_raw = column.get("label")
                    label = str(label_raw) if isinstance(label_raw, (str, int, float)) else key
                    header_group_raw = column.get("header_group")
                    header_group = (
                        str(header_group_raw)
                        if isinstance(header_group_raw, (str, int, float)) and str(header_group_raw).strip()
                        else None
                    )
                    columns.append({"key": key, "label": label, "header_group": header_group})
            normalized.append(
                {
                    "id": str(dataset.get("id") or f"dataset_{index + 1}"),
                    "title": str(dataset.get("title") or f"Dataset {index + 1}"),
                    "sheet_name": str(dataset.get("sheet_name") or f"Sheet{index + 1}")[:31] or f"Sheet{index + 1}",
                    "table_id": table_id,
                    "columns": columns,
                    "aggregated_columns": dataset.get("aggregated_columns", []) if isinstance(dataset.get("aggregated_columns"), list) else [],
                    "group_by_columns": dataset.get("group_by_columns", []) if isinstance(dataset.get("group_by_columns"), list) else [],
                }
            )
        if normalized:
            return normalized

    table_id = settings.get("table_id")
    if not isinstance(table_id, int):
        return []

    columns_raw = settings.get("columns")
    columns: list[dict[str, Any]] = []
    if isinstance(columns_raw, list):
        for column in columns_raw:
            if not isinstance(column, dict):
                continue
            key = column.get("key")
            if not isinstance(key, str) or not key:
                continue
            label_raw = column.get("label")
            label = str(label_raw) if isinstance(label_raw, (str, int, float)) else key
            header_group_raw = column.get("header_group")
            header_group = (
                str(header_group_raw)
                if isinstance(header_group_raw, (str, int, float)) and str(header_group_raw).strip()
                else None
            )
            columns.append({"key": key, "label": label, "header_group": header_group})

    return [
        {
            "id": "dataset_1",
            "title": "Report",
            "sheet_name": "Report",
            "table_id": table_id,
            "columns": columns,
            "aggregated_columns": [],
            "group_by_columns": [],
        }
    ]


def _build_widget_metric_value(widget: dict[str, Any], rows: list[TableDataRecordModel]) -> float | int | None:
    query = widget.get("query") if isinstance(widget.get("query"), dict) else {}
    aggregation = str(query.get("aggregation") or "count")
    if aggregation == "count":
        return len(rows)

    field_key = query.get("field_key")
    if not isinstance(field_key, str) or not field_key:
        return None

    values = _extract_metric_values(rows, field_key)
    if not values:
        return None
    if aggregation == "sum":
        return round(sum(values), 2)
    if aggregation == "avg":
        return round(sum(values) / len(values), 2)
    if aggregation == "min":
        return round(min(values), 2)
    if aggregation == "max":
        return round(max(values), 2)
    return None


def _build_group_header_row(columns: list[dict[str, Any]]) -> list[str]:
    return [str(column.get("header_group") or "") for column in columns]


def _has_group_headers(columns: list[dict[str, Any]]) -> bool:
    return any(str(column.get("header_group") or "").strip() for column in columns)


def _apply_xlsx_group_merges(ws, columns: list[dict[str, Any]]) -> None:
    if not _has_group_headers(columns):
        return

    index = 0
    while index < len(columns):
        label = str(columns[index].get("header_group") or "").strip()
        start = index
        index += 1
        while index < len(columns) and str(columns[index].get("header_group") or "").strip() == label:
            index += 1

        if label and index - start > 1:
            start_col = get_column_letter(start + 1)
            end_col = get_column_letter(index)
            ws.merge_cells(f"{start_col}1:{end_col}1")


def _build_widget_map_points(widget: dict[str, Any], rows: list[TableDataRecordModel]) -> list[dict[str, Any]]:
    config = widget.get("config") if isinstance(widget.get("config"), dict) else {}
    query = widget.get("query") if isinstance(widget.get("query"), dict) else {}
    lat_field = config.get("latField")
    lng_field = config.get("lngField")
    label_field = config.get("labelField")
    if not isinstance(lat_field, str) or not lat_field or not isinstance(lng_field, str) or not lng_field:
        return []

    limit_raw = query.get("limit")
    limit = limit_raw if isinstance(limit_raw, int) and limit_raw > 0 else 30
    points: list[dict[str, Any]] = []
    for row in rows[:limit]:
        row_data = row.data_json or {}
        lat = _to_number(row_data.get(lat_field))
        lng = _to_number(row_data.get(lng_field))
        if lat is None or lng is None:
            continue
        label = row_data.get(label_field) if isinstance(label_field, str) and label_field else None
        points.append(
            {
                "lat": lat,
                "lng": lng,
                "label": str(label or f"({lat}, {lng})"),
            }
        )
    return points


def _format_export_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return ", ".join(str(_format_export_value(item)) for item in value)
    if isinstance(value, dict):
        return str({key: _format_export_value(item) for key, item in value.items()})
    return str(value)


def _make_unique_name(base_name: str, used_names: set[str], suffix: str = "") -> str:
    candidate = (base_name or "sheet").strip() or "sheet"
    if suffix and candidate.lower().endswith(suffix.lower()):
        raw_candidate = candidate[: -len(suffix)]
    else:
        raw_candidate = candidate

    raw_candidate = raw_candidate.strip() or "sheet"
    candidate_full = f"{raw_candidate}{suffix}"
    counter = 2
    while candidate_full in used_names:
        candidate_full = f"{raw_candidate}_{counter}{suffix}"
        counter += 1
    used_names.add(candidate_full)
    return candidate_full


def _extract_row_data(row: Any) -> dict[str, Any]:
    """Extract data from either a TableDataRecordModel or a dict."""
    if isinstance(row, dict):
        return row
    if hasattr(row, "data_json"):
        return row.data_json or {}
    return {}


def _get_row_value(row: Any, key: str) -> Any:
    """Get a value from either a TableDataRecordModel or a dict."""
    if isinstance(row, dict):
        return row.get(key)
    row_data = _extract_row_data(row)
    return row_data.get(key)


def _aggregate_rows(
    rows: list[TableDataRecordModel],
    group_by_columns: list[str],
    aggregated_columns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Group rows and apply aggregation functions."""
    if not group_by_columns or not aggregated_columns:
        return []

    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        row_data = row.data_json or {}
        key = tuple(row_data.get(col) for col in group_by_columns)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(row_data)

    results = []
    for key_values, group_rows in grouped.items():
        result_row = {}
        for col_name, key_value in zip(group_by_columns, key_values):
            result_row[col_name] = key_value

        for agg_col in aggregated_columns:
            key = agg_col.get("key", "")
            agg_type = agg_col.get("aggregation", "count")
            source_field = agg_col.get("source_field", key)

            if agg_type == "count":
                result_row[key] = len(group_rows)
            elif agg_type == "sum":
                total = sum(
                    float(row.get(source_field, 0)) if isinstance(row.get(source_field), (int, float)) else 0
                    for row in group_rows
                )
                result_row[key] = total
            elif agg_type == "avg":
                values = [
                    float(row.get(source_field))
                    for row in group_rows
                    if isinstance(row.get(source_field), (int, float))
                ]
                result_row[key] = sum(values) / len(values) if values else None
            elif agg_type == "min":
                values = [
                    row.get(source_field)
                    for row in group_rows
                    if isinstance(row.get(source_field), (int, float))
                ]
                result_row[key] = min(values) if values else None
            elif agg_type == "max":
                values = [
                    row.get(source_field)
                    for row in group_rows
                    if isinstance(row.get(source_field), (int, float))
                ]
                result_row[key] = max(values) if values else None

        results.append(result_row)

    return results

def _normalize_template_key(raw_key: str) -> str:
    key = raw_key.strip()
    if (key.startswith("'") and key.endswith("'")) or (key.startswith('"') and key.endswith('"')):
        key = key[1:-1].strip()
    return key


def _format_template_value(value: float | int) -> str:
    if isinstance(value, float):
        normalized = round(value, 2)
        if normalized.is_integer():
            return str(int(normalized))
        return f"{normalized:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _calculate_template_aggregation(rows: list[TableDataRecordModel], func_name: str, key: str) -> float | int:
    function_name = func_name.lower()
    normalized_key = _normalize_template_key(key)
    if not normalized_key:
        raise ValueError("Ключ в выражении шаблона не может быть пустым")

    if function_name == "count":
        if normalized_key == "*":
            return len(rows)
        return sum(
            1
            for row in rows
            if (row.data_json or {}).get(normalized_key) not in (None, "")
        )

    numeric_values: list[float] = []
    for row in rows:
        number = _to_number((row.data_json or {}).get(normalized_key))
        if number is not None:
            numeric_values.append(number)

    if not numeric_values:
        return 0

    if function_name == "sum":
        return sum(numeric_values)
    if function_name == "avg":
        return sum(numeric_values) / len(numeric_values)
    if function_name == "min":
        return min(numeric_values)
    if function_name == "max":
        return max(numeric_values)

    raise ValueError(
        f"Неподдерживаемая функция '{func_name}' в шаблоне. Допустимо: count, sum, avg, min, max."
    )


def _render_template_content(content_xml: str, rows: list[TableDataRecordModel]) -> str:
    def replace_field(match: re.Match[str]) -> str:
        expression = match.group(1).strip()
        parsed = TEMPLATE_AGGREGATION_PATTERN.match(expression)
        if not parsed:
            raise ValueError(
                f"Некорректное выражение шаблона '{{{{ {expression} }}}}'. Ожидается aggregation_func(key)."
            )
        value = _calculate_template_aggregation(rows, parsed.group("func"), parsed.group("key"))
        return _format_template_value(value)

    return TEMPLATE_FIELD_PATTERN.sub(replace_field, content_xml)

@router.get("/reports/{report_id}/dashboard", response_model=PublicDashboardResponse)
def get_public_dashboard(
    report_id: int,
    session: Session = Depends(get_db),
    repo: ReportConfigurationRepository = Depends(get_report_repo),
):
    use_case = GetPublicReportConfigurationUseCase(repo)
    try:
        report = use_case.execute(report_id)
    except ReportConfigurationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")

    if report.report_type != "dashboard":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report type is not dashboard")

    raw_settings = report.settings or {}
    settings = _normalize_dashboard_settings(raw_settings)
    table_id = settings.get("table_id")
    if not isinstance(table_id, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dashboard table is not configured")

    rows_cache: dict[int, list[TableDataRecordModel]] = {}

    def get_rows_for_table(table_id_value: int) -> list[TableDataRecordModel]:
        if table_id_value not in rows_cache:
            rows_cache[table_id_value] = (
                session.execute(
                    select(TableDataRecordModel)
                    .where(
                        TableDataRecordModel.workspace_id == report.workspace_id,
                        TableDataRecordModel.table_id == table_id_value,
                    )
                    .order_by(TableDataRecordModel.created_at.desc())
                )
                .scalars()
                .all()
            )
        return rows_cache[table_id_value]

    rows = get_rows_for_table(table_id)

    metrics_config = settings.get("metrics") or []
    metrics: list[DashboardMetricResponse] = []

    for metric in metrics_config:
        if not isinstance(metric, dict):
            continue

        label = str(metric.get("label") or "Метрика")
        aggregation = str(metric.get("aggregation") or "count")
        field_key = metric.get("field_key")

        if aggregation == "count":
            metrics.append(DashboardMetricResponse(label=label, value=len(rows)))
            continue

        if not isinstance(field_key, str) or not field_key:
            metrics.append(DashboardMetricResponse(label=label, value=0))
            continue

        values = _extract_metric_values(rows, field_key)
        if not values:
            metrics.append(DashboardMetricResponse(label=label, value=0))
            continue

        if aggregation == "sum":
            result: float | int = sum(values)
        elif aggregation == "avg":
            result = sum(values) / len(values)
        elif aggregation == "min":
            result = min(values)
        elif aggregation == "max":
            result = max(values)
        else:
            result = 0

        metrics.append(DashboardMetricResponse(label=label, value=round(result, 2)))

    charts_config = settings.get("charts") or []
    charts: list[DashboardChartResponse] = []
    for chart in charts_config:
        if not isinstance(chart, dict):
            continue

        title = str(chart.get("title") or "График")
        chart_type = str(chart.get("chart_type") or "bar")
        color = chart.get("color")
        group_by_key = chart.get("group_by_key")
        aggregation = str(chart.get("aggregation") or "count")
        value_key = chart.get("value_key")
        limit_raw = chart.get("limit")
        limit = limit_raw if isinstance(limit_raw, int) and limit_raw > 0 else 10

        if chart_type != "bar" or not isinstance(group_by_key, str) or not group_by_key:
            continue

        points = _build_chart_points(
            rows=rows,
            group_by_key=group_by_key,
            aggregation=aggregation,
            value_key=value_key if isinstance(value_key, str) and value_key else None,
            limit=limit,
        )
        charts.append(
            DashboardChartResponse(
                title=title,
                chart_type="bar",
                color=color if isinstance(color, str) and color else None,
                points=points,
            )
        )

    recent_limit_raw = settings.get("recent_limit", 10)
    recent_limit = recent_limit_raw if isinstance(recent_limit_raw, int) and recent_limit_raw > 0 else 10
    recent_records = [
        {
            "id": row.id,
            "data": row.data_json,
            "submitted_at": row.submitted_at,
            "created_at": row.created_at,
            "submitter_email": row.submitter_email,
        }
        for row in rows[:recent_limit]
    ]

    widgets: list[PublicDashboardWidgetResponse] = []
    raw_widgets = raw_settings.get("widgets")
    if isinstance(raw_widgets, list):
        for index, widget in enumerate(raw_widgets):
            if not isinstance(widget, dict):
                continue

            widget_type = str(widget.get("type") or "")
            widget_id = str(widget.get("id") or f"widget_{index + 1}")
            title = str(widget.get("title") or "")
            description = str(widget.get("description") or "").strip() or None
            presentation = widget.get("presentation") if isinstance(widget.get("presentation"), dict) else {}
            source = widget.get("source") if isinstance(widget.get("source"), dict) else {}
            query = widget.get("query") if isinstance(widget.get("query"), dict) else {}
            config = widget.get("config") if isinstance(widget.get("config"), dict) else {}
            widget_table_id = source.get("table_id") if isinstance(source.get("table_id"), int) else table_id
            widget_rows = get_rows_for_table(widget_table_id) if isinstance(widget_table_id, int) else rows
            width = presentation.get("width")
            color = presentation.get("color") if isinstance(presentation.get("color"), str) else None

            if widget_type == "metric":
                widgets.append(
                    PublicDashboardWidgetResponse(
                        id=widget_id,
                        type="metric",
                        title=title,
                        description=description,
                        width="half" if width == "half" else "full",
                        color=color,
                        value=_build_widget_metric_value(widget, widget_rows),
                    )
                )
                continue

            if widget_type == "chart":
                group_by_key = query.get("group_by_key")
                aggregation = str(query.get("aggregation") or "count")
                value_key = query.get("field_key")
                limit_raw = query.get("limit")
                limit = limit_raw if isinstance(limit_raw, int) and limit_raw > 0 else 10
                points = []
                if isinstance(group_by_key, str) and group_by_key:
                    points = _build_chart_points(
                        rows=widget_rows,
                        group_by_key=group_by_key,
                        aggregation=aggregation,
                        value_key=value_key if isinstance(value_key, str) and value_key else None,
                        limit=limit,
                    )
                widgets.append(
                    PublicDashboardWidgetResponse(
                        id=widget_id,
                        type="chart",
                        title=title,
                        description=description,
                        width="half" if width == "half" else "full",
                        color=color,
                        points=points,
                    )
                )
                continue

            if widget_type == "table":
                config_columns = config.get("columns")
                column_keys = [str(item) for item in config_columns if isinstance(item, (str, int, float))] if isinstance(config_columns, list) else []
                table_model = session.execute(
                    select(TableStructureModel).where(
                        TableStructureModel.workspace_id == report.workspace_id,
                        TableStructureModel.id == widget_table_id,
                    )
                ).scalar()
                table_columns = table_model.columns_json if table_model and isinstance(table_model.columns_json, list) else []
                selected_columns = [
                    {
                        "key": str(column.get("key")),
                        "label": str(column.get("name") or column.get("key")),
                    }
                    for column in table_columns
                    if isinstance(column, dict)
                    and column.get("key")
                    and (not column_keys or str(column.get("key")) in column_keys)
                ]
                limit_raw = query.get("limit")
                page_size = limit_raw if isinstance(limit_raw, int) and limit_raw > 0 else 20
                table_rows = []
                for row in widget_rows:
                    row_data = row.data_json or {}
                    table_rows.append({column["key"]: row_data.get(column["key"]) for column in selected_columns})

                widgets.append(
                    PublicDashboardWidgetResponse(
                        id=widget_id,
                        type="table",
                        title=title,
                        description=description,
                        width="half" if width == "half" else "full",
                        columns=selected_columns,
                        rows=table_rows,
                        page_size=page_size,
                        total_rows=len(table_rows),
                    )
                )
                continue

            if widget_type == "map":
                widgets.append(
                    PublicDashboardWidgetResponse(
                        id=widget_id,
                        type="map",
                        title=title,
                        description=description,
                        width="half" if width == "half" else "full",
                        map_points=_build_widget_map_points(widget, widget_rows),
                    )
                )
                continue

            if widget_type == "text":
                widgets.append(
                    PublicDashboardWidgetResponse(
                        id=widget_id,
                        type="text",
                        title=title,
                        description=description,
                        width="half" if width == "half" else "full",
                        content=str(config.get("content") or ""),
                    )
                )

    return PublicDashboardResponse(
        id=report.id,
        name=report.name,
        description=report.description,
        table_id=table_id,
        generated_at=datetime.utcnow(),
        metrics=metrics,
        charts=charts,
        recent_records=recent_records,
        widgets=widgets,
    )


@router.get("/workspaces/{workspace_id}/reports", response_model=list[ReportConfigurationResponse])
def list_reports(
    workspace_id: int,
    current_user=Depends(get_current_user),
    repo: ReportConfigurationRepository = Depends(get_report_repo),
    session: Session = Depends(get_db),
):
    _assert_workspace_owner(session, workspace_id, current_user.id)
    use_case = ListReportConfigurationsUseCase(repo)
    reports = use_case.execute(workspace_id)
    return [_map_report(report) for report in reports]


@router.post(
    "/workspaces/{workspace_id}/reports",
    response_model=ReportConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report(
    workspace_id: int,
    payload: ReportConfigurationCreateRequest,
    current_user=Depends(get_current_user),
    repo: ReportConfigurationRepository = Depends(get_report_repo),
):
    report = ReportConfiguration(
        id=None,
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description,
        report_type=payload.report_type,
        settings=payload.settings,
        is_published=payload.is_published,
    )
    use_case = CreateReportConfigurationUseCase(repo)
    try:
        return _map_report(use_case.execute(report, current_user.id))
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get(
    "/workspaces/{workspace_id}/reports/{report_id}",
    response_model=ReportConfigurationResponse,
)
def get_report(
    workspace_id: int,
    report_id: int,
    current_user=Depends(get_current_user),
    repo: ReportConfigurationRepository = Depends(get_report_repo),
    session: Session = Depends(get_db),
):
    _assert_workspace_owner(session, workspace_id, current_user.id)
    use_case = GetReportConfigurationUseCase(repo)
    try:
        return _map_report(use_case.execute(workspace_id, report_id))
    except ReportConfigurationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")


@router.put(
    "/workspaces/{workspace_id}/reports/{report_id}",
    response_model=ReportConfigurationResponse,
)
def update_report(
    workspace_id: int,
    report_id: int,
    payload: ReportConfigurationUpdateRequest,
    current_user=Depends(get_current_user),
    repo: ReportConfigurationRepository = Depends(get_report_repo),
):
    report = ReportConfiguration(
        id=report_id,
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description,
        report_type=payload.report_type,
        settings=payload.settings,
        is_published=payload.is_published,
    )

    use_case = UpdateReportConfigurationUseCase(repo)
    try:
        return _map_report(use_case.execute(report, current_user.id))
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except ReportConfigurationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")


@router.delete(
    "/workspaces/{workspace_id}/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_report(
    workspace_id: int,
    report_id: int,
    current_user=Depends(get_current_user),
    repo: ReportConfigurationRepository = Depends(get_report_repo),
):
    use_case = DeleteReportConfigurationUseCase(repo)
    try:
        use_case.execute(workspace_id, report_id, current_user.id)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except ReportConfigurationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")


@router.get("/workspaces/{workspace_id}/reports/{report_id}/export")
def download_excel_report(
    workspace_id: int,
    report_id: int,
    format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    current_user=Depends(get_current_user),
    repo: ReportConfigurationRepository = Depends(get_report_repo),
    session: Session = Depends(get_db),
):
    _assert_workspace_owner(session, workspace_id, current_user.id)
    use_case = GetReportConfigurationUseCase(repo)
    try:
        report = use_case.execute(workspace_id, report_id)
    except ReportConfigurationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if report.report_type != "table_export":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report type is not table_export")

    datasets = _normalize_table_report_settings(report.settings or {})
    if not datasets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report table is not configured")

    prepared_datasets: list[dict[str, Any]] = []
    used_sheet_names: set[str] = set()
    for index, dataset in enumerate(datasets):
        table = session.execute(
            select(TableStructureModel).where(
                TableStructureModel.workspace_id == workspace_id,
                TableStructureModel.id == dataset["table_id"],
            )
        ).scalar()
        if not table:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

        columns = dataset["columns"]
        if not columns:
            columns = [
                {
                    "key": str(column.get("key")),
                    "label": str(column.get("name") or column.get("key")),
                    "header_group": None,
                }
                for column in (table.columns_json or [])
                if isinstance(column, dict) and column.get("key")
            ]

        rows = (
            session.execute(
                select(TableDataRecordModel)
                .where(
                    TableDataRecordModel.workspace_id == workspace_id,
                    TableDataRecordModel.table_id == dataset["table_id"],
                )
                .order_by(TableDataRecordModel.created_at.desc())
            )
            .scalars()
            .all()
        )

        # Handle aggregated columns
        group_by_columns = dataset.get("group_by_columns", [])
        aggregated_columns = dataset.get("aggregated_columns", [])
        final_columns = columns
        final_rows = rows
        
        if group_by_columns and aggregated_columns:
            # Build columns list: group_by columns + aggregated columns
            group_col_dicts = [{"key": col, "label": col} for col in group_by_columns]
            agg_col_dicts = aggregated_columns if isinstance(aggregated_columns, list) else []
            final_columns = group_col_dicts + agg_col_dicts
            
            # Aggregate the data
            aggregated_rows = _aggregate_rows(rows, group_by_columns, aggregated_columns)
            # Convert dicts to a row-like format that can be iterated
            final_rows = aggregated_rows

        prepared_datasets.append(
            {
                "title": dataset["title"],
                "sheet_name": _make_unique_name((dataset["sheet_name"] or f"Sheet{index + 1}")[:31], used_sheet_names),
                "columns": final_columns,
                "rows": final_rows,
                "is_aggregated": bool(group_by_columns and aggregated_columns),
            }
        )

    if format == "csv":
        if len(prepared_datasets) == 1:
            output = StringIO()
            writer = csv.writer(output)
            if _has_group_headers(prepared_datasets[0]["columns"]):
                writer.writerow(_build_group_header_row(prepared_datasets[0]["columns"]))
            writer.writerow([str(column.get("label") or column.get("key") or "") for column in prepared_datasets[0]["columns"]])
            for row in prepared_datasets[0]["rows"]:
                writer.writerow([
                    _format_export_value(_get_row_value(row, str(column.get("key") or "")))
                    for column in prepared_datasets[0]["columns"]
                ])

            return StreamingResponse(
                iter([output.getvalue().encode("utf-8-sig")]),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="report_{report.id}.csv"'},
            )

        archive = BytesIO()
        used_csv_names: set[str] = set()
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zip_file:
            for index, dataset in enumerate(prepared_datasets):
                output = StringIO()
                writer = csv.writer(output)
                if _has_group_headers(dataset["columns"]):
                    writer.writerow(_build_group_header_row(dataset["columns"]))
                writer.writerow([str(column.get("label") or column.get("key") or "") for column in dataset["columns"]])
                for row in dataset["rows"]:
                    writer.writerow([
                        _format_export_value(_get_row_value(row, str(column.get("key") or "")))
                        for column in dataset["columns"]
                    ])
                safe_name = _make_unique_name(dataset["sheet_name"] or f"sheet_{index + 1}", used_csv_names, ".csv")
                zip_file.writestr(safe_name, output.getvalue().encode("utf-8-sig"))

        archive.seek(0)
        return StreamingResponse(
            archive,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="report_{report.id}_csv.zip"'},
        )

    wb = Workbook()
    first_sheet = True
    for index, dataset in enumerate(prepared_datasets):
        ws = wb.active if first_sheet else wb.create_sheet()
        first_sheet = False
        ws.title = (dataset["sheet_name"] or f"Sheet{index + 1}")[:31]
        if _has_group_headers(dataset["columns"]):
            ws.append(_build_group_header_row(dataset["columns"]))
            ws.append([str(column.get("label") or column.get("key") or "") for column in dataset["columns"]])
            _apply_xlsx_group_merges(ws, dataset["columns"])
        else:
            ws.append([str(column.get("label") or column.get("key") or "") for column in dataset["columns"]])
        for row in dataset["rows"]:
            ws.append([
                _format_export_value(_get_row_value(row, str(column.get("key") or "")))
                for column in dataset["columns"]
            ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="report_{report.id}.xlsx"'},
    )


@router.post("/workspaces/{workspace_id}/reports/template-calc")
async def calculate_template_report(
    workspace_id: int,
    table_id: int = Query(..., ge=1),
    template_file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    session: Session = Depends(get_db),
):
    logger.info(
        "[template-calc] incoming workspace_id=%s table_id=%s filename=%s file_content_type=%s",
        workspace_id,
        table_id,
        template_file.filename,
        template_file.content_type,
    )
    _assert_workspace_owner(session, workspace_id, current_user.id)

    original_name = template_file.filename or "template.odt"
    if not original_name.lower().endswith(".odt"):
        logger.warning(
            "[template-calc] rejected by extension workspace_id=%s table_id=%s filename=%s",
            workspace_id,
            table_id,
            original_name,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Разрешены только .odt файлы")

    table = session.execute(
        select(TableStructureModel).where(
            TableStructureModel.workspace_id == workspace_id,
            TableStructureModel.id == table_id,
        )
    ).scalar()
    if not table:
        logger.warning(
            "[template-calc] table not found workspace_id=%s table_id=%s",
            workspace_id,
            table_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

    template_bytes = await template_file.read()
    logger.info(
        "[template-calc] file loaded workspace_id=%s table_id=%s filename=%s bytes=%s",
        workspace_id,
        table_id,
        original_name,
        len(template_bytes),
    )
    if not template_bytes:
        logger.warning(
            "[template-calc] empty file workspace_id=%s table_id=%s filename=%s",
            workspace_id,
            table_id,
            original_name,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл шаблона пустой")

    rows = (
        session.execute(
            select(TableDataRecordModel)
            .where(
                TableDataRecordModel.workspace_id == workspace_id,
                TableDataRecordModel.table_id == table_id,
            )
            .order_by(TableDataRecordModel.created_at.desc())
        )
        .scalars()
        .all()
    )
    logger.info(
        "[template-calc] table rows loaded workspace_id=%s table_id=%s rows=%s",
        workspace_id,
        table_id,
        len(rows),
    )

    try:
        source_buffer = BytesIO(template_bytes)
        with zipfile.ZipFile(source_buffer, mode="r") as source_archive:
            if "content.xml" not in source_archive.namelist():
                raise ValueError("Файл шаблона не содержит content.xml")

            content_xml = source_archive.read("content.xml").decode("utf-8")
            rendered_content = _render_template_content(content_xml, rows).encode("utf-8")

            output = BytesIO()
            with zipfile.ZipFile(output, mode="w") as target_archive:
                for archive_entry in source_archive.infolist():
                    if archive_entry.is_dir():
                        target_archive.writestr(archive_entry, b"")
                        continue
                    if archive_entry.filename == "content.xml":
                        target_archive.writestr(archive_entry, rendered_content)
                    else:
                        target_archive.writestr(
                            archive_entry,
                            source_archive.read(archive_entry.filename),
                        )
    except zipfile.BadZipFile:
        logger.warning(
            "[template-calc] invalid odt archive workspace_id=%s table_id=%s filename=%s",
            workspace_id,
            table_id,
            original_name,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Некорректный .odt файл")
    except UnicodeDecodeError:
        logger.warning(
            "[template-calc] decode error in content.xml workspace_id=%s table_id=%s filename=%s",
            workspace_id,
            table_id,
            original_name,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось прочитать content.xml внутри .odt",
        )
    except ValueError as error:
        logger.warning(
            "[template-calc] template validation error workspace_id=%s table_id=%s filename=%s error=%s",
            workspace_id,
            table_id,
            original_name,
            str(error),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except Exception:
        logger.exception(
            "[template-calc] unexpected error workspace_id=%s table_id=%s filename=%s",
            workspace_id,
            table_id,
            original_name,
        )
        raise

    output.seek(0)
    output_name = f"{Path(original_name).stem}_calculated.odt"
    logger.info(
        "[template-calc] success workspace_id=%s table_id=%s source_filename=%s output_filename=%s",
        workspace_id,
        table_id,
        original_name,
        output_name,
    )
    return StreamingResponse(
        output,
        media_type="application/vnd.oasis.opendocument.text",
        headers={"Content-Disposition": f'attachment; filename="{output_name}"'},
    )
