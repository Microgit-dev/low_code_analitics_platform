import { reportApi } from "../../infrastructure/api/reportApi";
import {
  DashboardChartConfig,
  DashboardMetricConfig,
  ExcelReportColumn,
  PublicDashboardData,
  ReportConfiguration,
  ReportType,
} from "../../domain/entities/Report";

export class ReportUseCase {
  constructor(private token: string) {}

  async listReports(workspaceId: number): Promise<ReportConfiguration[]> {
    return reportApi.listReports(this.token, workspaceId);
  }

  async createReport(
    workspaceId: number,
    name: string,
    description: string,
    reportType: ReportType,
    settings: {
      table_id: number;
      columns?: ExcelReportColumn[];
      metrics?: DashboardMetricConfig[];
      charts?: DashboardChartConfig[];
      recent_limit?: number;
    },
    isPublished: boolean
  ): Promise<ReportConfiguration> {
    return reportApi.createReport(this.token, workspaceId, {
      name,
      description,
      report_type: reportType,
      settings,
      is_published: isPublished,
    });
  }

  async updateReport(
    workspaceId: number,
    reportId: number,
    name: string,
    description: string,
    reportType: ReportType,
    settings: {
      table_id: number;
      columns?: ExcelReportColumn[];
      metrics?: DashboardMetricConfig[];
      charts?: DashboardChartConfig[];
      recent_limit?: number;
    },
    isPublished: boolean
  ): Promise<ReportConfiguration> {
    return reportApi.updateReport(this.token, workspaceId, reportId, {
      name,
      description,
      report_type: reportType,
      settings,
      is_published: isPublished,
    });
  }

  async deleteReport(workspaceId: number, reportId: number): Promise<void> {
    return reportApi.deleteReport(this.token, workspaceId, reportId);
  }

  async downloadExcelReport(workspaceId: number, reportId: number): Promise<Blob> {
    return reportApi.downloadExcelReport(this.token, workspaceId, reportId);
  }

  async calculateByTemplate(workspaceId: number, tableId: number, file: File): Promise<Blob> {
    return reportApi.calculateByTemplate(this.token, workspaceId, tableId, file);
  }

  async downloadConversionPrompt(workspaceId: number, tableId: number): Promise<Blob> {
    return reportApi.downloadConversionPrompt(this.token, workspaceId, tableId);
  }

  static async getPublicDashboard(reportId: number): Promise<PublicDashboardData> {
    return reportApi.getPublicDashboard(reportId);
  }
}
