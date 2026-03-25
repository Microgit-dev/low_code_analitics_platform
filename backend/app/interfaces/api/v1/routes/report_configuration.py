import logging
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
import zipfile

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import func, select
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
from app.application.services.template_aggregation import render_template_content
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
    ReportConfigurationCreateRequest,
    ReportConfigurationResponse,
    ReportConfigurationUpdateRequest,
)

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


def get_report_repo(session: Session = Depends(get_db)) -> ReportConfigurationRepository:
    return SQLAlchemyReportConfigurationRepository(session)


def _map_report(report: ReportConfiguration) -> ReportConfigurationResponse:
    now = datetime.utcnow()
    return ReportConfigurationResponse(
        id=report.id,
        workspace_id=report.workspace_id,
        name=report.name,
        description=report.description,
        report_type=report.report_type,
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


def _find_llm_bible_dir() -> Path | None:
    source_path = Path(__file__).resolve()
    checked_paths: set[str] = set()

    for parent in source_path.parents:
        candidate = parent / "data" / "llm_bible"
        candidate_key = str(candidate)
        if candidate_key in checked_paths:
            continue
        checked_paths.add(candidate_key)
        if candidate.is_dir():
            return candidate
    return None


def _load_llm_bible_documents() -> list[tuple[str, str]]:
    llm_bible_dir = _find_llm_bible_dir()
    if not llm_bible_dir:
        logger.warning("[prompt-conversion] llm_bible directory not found")
        return []

    docs: list[tuple[str, str]] = []
    for file_path in sorted(llm_bible_dir.glob("*.txt"), key=lambda item: item.name):
        try:
            text = file_path.read_text(encoding="utf-8").strip()
        except OSError as error:
            logger.warning(
                "[prompt-conversion] failed to read llm_bible file=%s error=%s",
                file_path,
                error,
            )
            continue
        if text:
            docs.append((file_path.name, text))
            logger.info("[prompt-conversion] loaded llm_bible file=%s", file_path)

    if not docs:
        logger.warning("[prompt-conversion] llm_bible directory has no non-empty .txt files")
    return docs


def _format_preview_rows(preview_rows: list[dict[str, Any]]) -> str:
    if not preview_rows:
        return "- (no records found in selected table)"

    lines: list[str] = []
    for idx, row in enumerate(preview_rows, start=1):
        payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
        if len(payload) > 1500:
            payload = f"{payload[:1500]} ...<truncated>"
        lines.append(f"- row_{idx}: {payload}")
    return "\n".join(lines)


def _build_conversion_prompt_text(
    table: TableStructureModel,
    total_rows: int,
    preview_rows: list[dict[str, Any]],
) -> str:
    columns = table.columns_json or []
    if columns:
        columns_description = "\n".join(
            [
                (
                    f"- key: {str(column.get('key') or '')}; "
                    f"name: {str(column.get('name') or column.get('key') or '')}; "
                    f"type: {str(column.get('type') or 'unknown')}; "
                    f"required: {bool(column.get('required', False))}; "
                    f"settings: {column.get('settings') if column.get('settings') is not None else '{}'}"
                )
                for column in columns
                if isinstance(column, dict) and column.get("key")
            ]
        )
    else:
        columns_description = "- (нет колонок)"

    llm_bible_documents = _load_llm_bible_documents()
    if llm_bible_documents:
        llm_bible_reference = "\n\n".join(
            [
                f"[BEGIN LLM_BIBLE FILE: {filename}]\n{content}\n[END LLM_BIBLE FILE: {filename}]"
                for filename, content in llm_bible_documents
            ]
        )
    else:
        llm_bible_reference = "\n".join(
            [
                "[LLM_BIBLE FILES NOT FOUND]",
                "Fallback summary:",
                "- Use {{ aggregation_func(key[, condition]) }}.",
                "- V4 arithmetic is supported: +, -, *, / with parentheses.",
                "- Scalar selectors are supported: first(key[, condition]), last(key[, condition]).",
                "- Date helpers are supported in conditions: date(day, month, year), add_years(date_value, years).",
                "- Variables are supported: set(name, value), var(name).",
                "- Use where(field, condition) for cross-column filtering.",
                '- Division by zero/undefined division renders as "-".',
            ]
        )

    data_preview = _format_preview_rows(preview_rows)

    return "\n".join(
        [
            "PROMPT FOR LLM: REPORT PLACEHOLDER CONVERSION",
            "Prompt version: 2026-03-25.v10",
            "",
            "Your task:",
            "Fill empty report fields with expressions inside double curly braces {{ ... }}.",
            "Each expression will be computed on rows of selected table_data_records.data_json.",
            "",
            "LLM bible reference (full documents):",
            llm_bible_reference,
            "",
            "Expression syntax:",
            "- {{ aggregation_func(key) }}",
            "- {{ aggregation_func(key, condition_expr) }}",
            "- {{ first(key) }} / {{ last(key) }}",
            "- {{ add_years(date(25, 3, 2026), -1) }} (for condition arguments)",
            "- {{ set(my_var, first(key)) }} then {{ var(my_var) }}",
            "- {{ aggregation_expr + aggregation_expr }}",
            "- {{ (aggregation_expr + aggregation_expr) / 2 }}",
            "",
            "Computation notes:",
            "- If filtering by another column, use where(field, condition).",
            "- For row count use count(*).",
            "- Numeric aggregations use numeric-convertible values.",
            "- Numeric conversion: bool=true->1, false->0; numeric strings are parsed; non-numeric values are ignored.",
            "- Date conversion supports ISO date and ISO datetime (including Z suffix).",
            "- Strings in conditions should be quoted.",
            "",
            "Selected table context:",
            f"- table_id: {table.id}",
            f"- table_name: {table.name}",
            f"- table_description: {table.description or ''}",
            "- columns:",
            columns_description,
            "",
            "Selected table data description:",
            f"- total_rows_in_table_data_records: {total_rows}",
            f"- preview_rows_count: {len(preview_rows)}",
            "- preview_rows_order: newest first by created_at",
            "- preview_rows_data_json:",
            data_preview,
            "",
            "Examples:",
            "- {{ count(*) }}",
            "- {{ sum(suffer_people) }}",
            "- {{ first(населенный_пункт_наименование) }}",
            '- {{ sum(suffer_people, where(status, eq("injured"))) }}',
            "- {{ sum(suffer_people, where(region_id, eq(5))) }}",
            '- {{ count(*, where(created_at, date_between("2026-03-01", "2026-03-31"))) }}',
            "- {{ sum(suffer_people) + count(*) }}",
            "",
            "Output requirement:",
            "For each empty report field provide exactly one expression in {{ ... }} and nothing else.",
        ]
    )


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

    settings = report.settings or {}
    table_id = settings.get("table_id")
    if not isinstance(table_id, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dashboard table is not configured")

    rows = (
        session.execute(
            select(TableDataRecordModel)
            .where(
                TableDataRecordModel.workspace_id == report.workspace_id,
                TableDataRecordModel.table_id == table_id,
            )
            .order_by(TableDataRecordModel.created_at.desc())
        )
        .scalars()
        .all()
    )

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
        charts.append(DashboardChartResponse(title=title, chart_type="bar", points=points))

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

    return PublicDashboardResponse(
        id=report.id,
        name=report.name,
        description=report.description,
        table_id=table_id,
        generated_at=datetime.utcnow(),
        metrics=metrics,
        charts=charts,
        recent_records=recent_records,
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

    if report.report_type != "excel_export":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report type is not excel_export")

    settings = report.settings or {}
    table_id = settings.get("table_id")
    if not isinstance(table_id, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report table is not configured")

    table = session.execute(
        select(TableStructureModel).where(
            TableStructureModel.workspace_id == workspace_id,
            TableStructureModel.id == table_id,
        )
    ).scalar()
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

    columns_config = settings.get("columns")
    if isinstance(columns_config, list) and columns_config:
        columns: list[tuple[str, str]] = []
        for column in columns_config:
            if not isinstance(column, dict):
                continue
            key = column.get("key")
            if not isinstance(key, str) or not key:
                continue
            label_raw = column.get("label")
            label = str(label_raw) if isinstance(label_raw, (str, int, float)) else key
            columns.append((key, label))
    else:
        columns = [
            (str(column.get("key")), str(column.get("name") or column.get("key")))
            for column in (table.columns_json or [])
            if isinstance(column, dict) and column.get("key")
        ]

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

    wb = Workbook()
    ws = wb.active
    ws.title = "Report"

    headers = [label for _, label in columns]
    ws.append(headers)

    for row in rows:
        row_data = row.data_json or {}
        ws.append([row_data.get(key) for key, _ in columns])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"report_{report.id}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/workspaces/{workspace_id}/reports/prompt/conversion")
def download_conversion_prompt(
    workspace_id: int,
    table_id: int = Query(..., ge=1),
    current_user=Depends(get_current_user),
    session: Session = Depends(get_db),
):
    _assert_workspace_owner(session, workspace_id, current_user.id)

    table = session.execute(
        select(TableStructureModel).where(
            TableStructureModel.workspace_id == workspace_id,
            TableStructureModel.id == table_id,
        )
    ).scalar()
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

    total_rows = (
        session.execute(
            select(func.count())
            .select_from(TableDataRecordModel)
            .where(
                TableDataRecordModel.workspace_id == workspace_id,
                TableDataRecordModel.table_id == table_id,
            )
        )
        .scalar_one()
    )

    preview_rows_raw = (
        session.execute(
            select(TableDataRecordModel.data_json)
            .where(
                TableDataRecordModel.workspace_id == workspace_id,
                TableDataRecordModel.table_id == table_id,
            )
            .order_by(TableDataRecordModel.created_at.desc())
            .limit(5)
        )
        .scalars()
        .all()
    )
    preview_rows = [row for row in preview_rows_raw if isinstance(row, dict)]

    prompt_text = _build_conversion_prompt_text(
        table=table,
        total_rows=int(total_rows),
        preview_rows=preview_rows,
    )
    payload = BytesIO(prompt_text.encode("utf-8"))
    payload.seek(0)

    filename = f"prompt_conversion_table_{table.id}.txt"
    return StreamingResponse(
        payload,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
    rows_data = [(row.data_json or {}) for row in rows]

    try:
        source_buffer = BytesIO(template_bytes)
        with zipfile.ZipFile(source_buffer, mode="r") as source_archive:
            if "content.xml" not in source_archive.namelist():
                raise ValueError("Файл шаблона не содержит content.xml")

            content_xml = source_archive.read("content.xml").decode("utf-8")
            rendered_content = render_template_content(content_xml, rows_data).encode("utf-8")

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
