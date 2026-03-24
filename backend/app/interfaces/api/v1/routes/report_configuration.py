from datetime import datetime
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
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
    ReportConfigurationCreateRequest,
    ReportConfigurationResponse,
    ReportConfigurationUpdateRequest,
)

router = APIRouter()


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
