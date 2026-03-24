export type ReportType = "table_export" | "dashboard";

export type MetricAggregation = "count" | "sum" | "avg" | "min" | "max";
export type WidgetMetricAggregation = MetricAggregation;
export type DashboardWidgetType = "text" | "metric" | "table" | "chart" | "gauge" | "map";

export interface ExcelReportColumn {
  key: string;
  label: string;
  header_group?: string | null;
  aggregation?: MetricAggregation | null;
}

export interface AggregatedColumn {
  key: string;
  label: string;
  aggregation: MetricAggregation;
  source_field?: string | null;
}

export interface TableStructureOption {
  id: number;
  name: string;
}

export interface WidgetFieldOption {
  key: string;
  name: string;
  type: string;
}

export interface WidgetLayoutItem {
  widget_id: string;
  i?: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface DashboardWidgetFilter {
  id: string;
  field: string;
  operator: string;
  value: unknown;
}

export interface DashboardWidget {
  id: string;
  type: DashboardWidgetType;
  title: string;
  description?: string;
  source: {
    table_id: number | null;
  };
  query: {
    aggregation?: WidgetMetricAggregation;
    field_key?: string | null;
    group_by_key?: string | null;
    sort_by?: string | null;
    sort_direction?: "asc" | "desc";
    limit?: number;
    filters?: DashboardWidgetFilter[];
  };
  presentation: {
    show_title?: boolean;
    format?: string;
    color?: string;
  };
  config: Record<string, any>;
}

export interface DashboardReportSettings {
  widgets: DashboardWidget[];
  layout: WidgetLayoutItem[];
  global_filters: Array<Record<string, unknown>>;
  canvas: {
    columns: number;
    row_height: number;
  };
}

export type TableReportExportMode = "xlsx" | "csv";

export interface TableReportDataset {
  id: string;
  title: string;
  sheet_name: string;
  table_id: number | null;
  columns: ExcelReportColumn[];
  aggregated_columns?: AggregatedColumn[];
  group_by_columns?: string[];
  sorting: Array<{ field: string; direction: "asc" | "desc" }>;
  filters: Array<Record<string, unknown>>;
}

export interface TableReportSettings {
  datasets: TableReportDataset[];
}

export interface DashboardMetricConfig {
  label: string;
  aggregation: MetricAggregation;
  field_key?: string;
}

export interface DashboardChartConfig {
  title: string;
  chart_type: "bar";
  group_by_key: string;
  aggregation: MetricAggregation;
  value_key?: string;
  limit?: number;
}

export interface ReportConfiguration {
  id: number;
  workspace_id: number;
  name: string;
  description: string;
  report_type: ReportType;
  settings: Record<string, unknown>;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface PublicDashboardMetric {
  label: string;
  value: number;
}

export interface PublicDashboardChartPoint {
  label: string;
  value: number;
}

export interface PublicDashboardChart {
  title: string;
  chart_type: "bar";
  color?: string | null;
  points: PublicDashboardChartPoint[];
}

export interface PublicDashboardWidget {
  id: string;
  type: "text" | "metric" | "table" | "chart" | "gauge" | "map";
  title: string;
  description?: string | null;
  width: "half" | "full";
  grid_x?: number | null;
  grid_y?: number | null;
  grid_width?: number | null;
  grid_height?: number | null;
  color?: string | null;
  content?: string | null;
  value?: number | null;
  columns?: Array<{ key: string; label: string }>;
  rows?: Array<Record<string, unknown>>;
  page_size?: number | null;
  total_rows?: number | null;
  points?: PublicDashboardChartPoint[];
  map_points?: Array<{ lat: number; lng: number; label: string }>;
}

export interface PublicDashboardData {
  id: number;
  name: string;
  description?: string | null;
  table_id: number;
  generated_at: string;
  metrics: PublicDashboardMetric[];
  charts: PublicDashboardChart[];
  widgets: PublicDashboardWidget[];
  recent_records: Array<{
    id: number;
    data: Record<string, unknown>;
    submitted_at?: string | null;
    created_at: string;
    submitter_email?: string | null;
  }>;
}
