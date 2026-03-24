import { formBuilderApi } from "../../infrastructure/api/formBuilderApi";
import {
  FormConfiguration,
  FormField,
  PublicFormSubmitResult,
  TableDataRecord,
  TableDataRecordsListResponse,
} from "../../domain/entities/FormBuilder";

export class FormBuilderUseCase {
  constructor(private token: string) {}

  // Form Configuration methods
  async listForms(workspaceId: number, tableId?: number): Promise<FormConfiguration[]> {
    return formBuilderApi.listForms(this.token, workspaceId, tableId);
  }

  async createForm(
    workspaceId: number,
    tableId: number,
    name: string,
    description: string,
    fields: FormField[],
    collectEmail: boolean = false
  ): Promise<FormConfiguration> {
    return formBuilderApi.createForm(this.token, workspaceId, {
      table_id: tableId,
      name,
      description,
      fields,
      collect_email: collectEmail,
    });
  }

  async getForm(workspaceId: number, formId: number): Promise<FormConfiguration> {
    return formBuilderApi.getForm(this.token, workspaceId, formId);
  }

  async updateForm(
    workspaceId: number,
    formId: number,
    name: string,
    description: string,
    fields: FormField[],
    isPublished: boolean = false,
    collectEmail: boolean = false
  ): Promise<FormConfiguration> {
    return formBuilderApi.updateForm(this.token, workspaceId, formId, {
      name,
      description,
      fields,
      is_published: isPublished,
      collect_email: collectEmail,
    });
  }

  async deleteForm(workspaceId: number, formId: number): Promise<void> {
    return formBuilderApi.deleteForm(this.token, workspaceId, formId);
  }

  // Table Data methods
  async listTableData(
    workspaceId: number,
    tableId: number,
    skip: number = 0,
    limit: number = 50
  ): Promise<TableDataRecordsListResponse> {
    return formBuilderApi.listTableData(this.token, workspaceId, tableId, skip, limit);
  }

  async getTableDataRecord(
    workspaceId: number,
    tableId: number,
    recordId: number
  ): Promise<TableDataRecord> {
    return formBuilderApi.getTableDataRecord(this.token, workspaceId, tableId, recordId);
  }

  async submitForm(
    workspaceId: number,
    tableId: number,
    data: Record<string, unknown>,
    submitterEmail?: string
  ): Promise<PublicFormSubmitResult> {
    return formBuilderApi.submitForm(workspaceId, tableId, data, submitterEmail);
  }

  async deleteTableDataRecord(
    workspaceId: number,
    tableId: number,
    recordId: number
  ): Promise<void> {
    return formBuilderApi.deleteTableDataRecord(this.token, workspaceId, tableId, recordId);
  }
}
