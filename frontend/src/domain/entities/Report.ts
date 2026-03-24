export type ReportType = "excel_export" | "dashboard";

export type MetricAggregation = "count" | "sum" | "avg" | "min" | "max";

export interface ExcelReportColumn {
  key: string;
  label: string;
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
  points: PublicDashboardChartPoint[];
}

export interface PublicDashboardData {
  id: number;
  name: string;
  description?: string | null;
  table_id: number;
  generated_at: string;
  metrics: PublicDashboardMetric[];
  charts: PublicDashboardChart[];
  recent_records: Array<{
    id: number;
    data: Record<string, unknown>;
    submitted_at?: string | null;
    created_at: string;
    submitter_email?: string | null;
  }>;
}
