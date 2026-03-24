from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ReportType = Literal["excel_export", "dashboard"]


class ReportConfigurationCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    report_type: ReportType
    settings: dict[str, Any] = Field(default_factory=dict)
    is_published: bool = False


class ReportConfigurationUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    report_type: ReportType
    settings: dict[str, Any] = Field(default_factory=dict)
    is_published: bool = False


class ReportConfigurationResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    description: str | None
    report_type: ReportType
    settings: dict[str, Any]
    is_published: bool
    created_at: datetime
    updated_at: datetime


class DashboardMetricResponse(BaseModel):
    label: str
    value: float | int


class DashboardChartPointResponse(BaseModel):
    label: str
    value: float | int


class DashboardChartResponse(BaseModel):
    title: str
    chart_type: Literal["bar"]
    color: str | None = None
    points: list[DashboardChartPointResponse]


class PublicDashboardWidgetResponse(BaseModel):
    id: str
    type: Literal["text", "metric", "table", "chart", "map"]
    title: str
    description: str | None = None
    width: Literal["half", "full"] = "full"
    color: str | None = None
    content: str | None = None
    value: float | int | None = None
    columns: list[dict[str, str]] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    page_size: int | None = None
    total_rows: int | None = None
    points: list[DashboardChartPointResponse] = Field(default_factory=list)
    map_points: list[dict[str, Any]] = Field(default_factory=list)


class PublicDashboardResponse(BaseModel):
    id: int
    name: str
    description: str | None
    table_id: int
    generated_at: datetime
    metrics: list[DashboardMetricResponse]
    charts: list[DashboardChartResponse]
    recent_records: list[dict[str, Any]]
    widgets: list[PublicDashboardWidgetResponse] = Field(default_factory=list)
