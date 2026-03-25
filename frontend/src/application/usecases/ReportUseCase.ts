import { reportApi } from "../../infrastructure/api/reportApi";
import { PublicDashboardData, ReportConfiguration, ReportType } from "../../domain/entities/Report";

export class ReportUseCase {
  constructor(private token: string) {}

  async listReports(workspaceId: number): Promise<ReportConfiguration[]> {
    return reportApi.listReports(this.token, workspaceId);
  }

  async getReport(workspaceId: number, reportId: number): Promise<ReportConfiguration> {
    return reportApi.getReport(this.token, workspaceId, reportId);
  }

  async createReport(
    workspaceId: number,
    name: string,
    description: string,
    reportType: ReportType,
    settings: Record<string, unknown>,
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
    settings: Record<string, unknown>,
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

  async downloadExcelReport(workspaceId: number, reportId: number, format: "xlsx" | "csv" = "xlsx"): Promise<Blob> {
    return reportApi.downloadExcelReport(this.token, workspaceId, reportId, format);
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
