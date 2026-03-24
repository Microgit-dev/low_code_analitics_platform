import { httpClient } from "./httpClient";
import {
  FormConfiguration,
  FormField,
  PublicFormSubmitResult,
  TableDataRecord,
  TableDataRecordsListResponse,
} from "../../domain/entities/FormBuilder";

export const formBuilderApi = {
  // Form Configuration API
  listForms: async (token: string, workspaceId: number, tableId?: number) => {
    const query = typeof tableId === "number" ? `?table_id=${tableId}` : "";
    const response = await httpClient.get<FormConfiguration[]>(
      `/workspaces/${workspaceId}/forms${query}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  },

  createForm: async (
    token: string,
    workspaceId: number,
    payload: {
      table_id: number;
      name: string;
      description: string;
      fields: FormField[];
      collect_email: boolean;
    }
  ) => {
    const response = await httpClient.post<FormConfiguration>(
      `/workspaces/${workspaceId}/forms`,
      payload,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  },

  getForm: async (token: string, workspaceId: number, formId: number) => {
    const response = await httpClient.get<FormConfiguration>(
      `/workspaces/${workspaceId}/forms/${formId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  },

  updateForm: async (
    token: string,
    workspaceId: number,
    formId: number,
    payload: {
      name: string;
      description: string;
      fields: FormField[];
      is_published: boolean;
      collect_email: boolean;
    }
  ) => {
    const response = await httpClient.put<FormConfiguration>(
      `/workspaces/${workspaceId}/forms/${formId}`,
      payload,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  },

  deleteForm: async (token: string, workspaceId: number, formId: number) => {
    await httpClient.delete(`/workspaces/${workspaceId}/forms/${formId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  },

  // Table Data API
  listTableData: async (
    token: string,
    workspaceId: number,
    tableId: number,
    skip: number = 0,
    limit: number = 50
  ) => {
    const response = await httpClient.get<TableDataRecordsListResponse>(
      `/workspaces/${workspaceId}/tables/${tableId}/data?skip=${skip}&limit=${limit}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  },

  getTableDataRecord: async (
    token: string,
    workspaceId: number,
    tableId: number,
    recordId: number
  ) => {
    const response = await httpClient.get<TableDataRecord>(
      `/workspaces/${workspaceId}/tables/${tableId}/data/${recordId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  },

  updateTableDataRecord: async (
    token: string,
    workspaceId: number,
    tableId: number,
    recordId: number,
    payload: {
      data: Record<string, unknown>;
      submitter_email?: string | null;
    }
  ) => {
    const response = await httpClient.put<TableDataRecord>(
      `/workspaces/${workspaceId}/tables/${tableId}/data/${recordId}`,
      payload,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  },

  submitForm: async (
    workspaceId: number,
    tableId: number,
    data: Record<string, unknown>,
    submitterEmail?: string
  ) => {
    // Публичный endpoint без auth
    const response = await httpClient.post<PublicFormSubmitResult>(
      `/workspaces/${workspaceId}/tables/${tableId}/data/submit`,
      {
        data,
        submitter_email: submitterEmail,
      }
    );
    return response.data;
  },

  deleteTableDataRecord: async (
    token: string,
    workspaceId: number,
    tableId: number,
    recordId: number
  ) => {
    await httpClient.delete(
      `/workspaces/${workspaceId}/tables/${tableId}/data/${recordId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
  },
};
