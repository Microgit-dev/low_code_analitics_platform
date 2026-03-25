import { httpClient } from "./httpClient";
import { PublicDashboardData, ReportConfiguration, ReportType } from "../../domain/entities/Report";

export const reportApi = {
  listReports: async (token: string, workspaceId: number) => {
    const response = await httpClient.get<ReportConfiguration[]>(`/workspaces/${workspaceId}/reports`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  },

  getReport: async (token: string, workspaceId: number, reportId: number) => {
    const response = await httpClient.get<ReportConfiguration>(`/workspaces/${workspaceId}/reports/${reportId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  },

  createReport: async (
    token: string,
    workspaceId: number,
    payload: {
      name: string;
      description: string;
      report_type: ReportType;
      settings: Record<string, unknown>;
      is_published: boolean;
    }
  ) => {
    const response = await httpClient.post<ReportConfiguration>(`/workspaces/${workspaceId}/reports`, payload, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  },

  updateReport: async (
    token: string,
    workspaceId: number,
    reportId: number,
    payload: {
      name: string;
      description: string;
      report_type: ReportType;
      settings: Record<string, unknown>;
      is_published: boolean;
    }
  ) => {
    const response = await httpClient.put<ReportConfiguration>(
      `/workspaces/${workspaceId}/reports/${reportId}`,
      payload,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  },

  deleteReport: async (token: string, workspaceId: number, reportId: number) => {
    await httpClient.delete(`/workspaces/${workspaceId}/reports/${reportId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  },

  downloadExcelReport: async (
    token: string,
    workspaceId: number,
    reportId: number,
    format: "xlsx" | "csv" = "xlsx"
  ) => {
    const response = await httpClient.get<Blob>(`/workspaces/${workspaceId}/reports/${reportId}/export?format=${format}`, {
      headers: { Authorization: `Bearer ${token}` },
      responseType: "blob",
    });
    return response.data;
  },

  calculateByTemplate: async (token: string, workspaceId: number, tableId: number, file: File) => {
    const formData = new FormData();
    formData.append("template_file", file);
    const response = await httpClient.post<Blob>(
      `/workspaces/${workspaceId}/reports/template-calc?table_id=${tableId}`,
      formData,
      {
        headers: { Authorization: `Bearer ${token}` },
        responseType: "blob",
      }
    );
    return response.data;
  },

  generateHtmlByTemplate: async (token: string, workspaceId: number, file: File, tableIds: number[]) => {
    const formData = new FormData();
    formData.append("template_file", file);
    if (tableIds.length > 0) {
      formData.append("table_ids", tableIds.join(","));
    }
    const response = await httpClient.post<Blob>(
      `/workspaces/${workspaceId}/reports/template-generate`,
      formData,
      {
        headers: { Authorization: `Bearer ${token}` },
        responseType: "blob",
      }
    );
    return response.data;
  },

  downloadConversionPrompt: async (token: string, workspaceId: number, tableId: number) => {
    const response = await httpClient.get<Blob>(
      `/workspaces/${workspaceId}/reports/prompt/conversion?table_id=${tableId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        responseType: "blob",
      }
    );
    return response.data;
  },

  getPublicDashboard: async (reportId: number) => {
    const response = await httpClient.get<PublicDashboardData>(`/reports/${reportId}/dashboard`);
    return response.data;
  },
};
