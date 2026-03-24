export type WidgetType =
  | "text_input"
  | "textarea"
  | "number_input"
  | "date_input"
  | "datetime_input"
  | "select"
  | "checkbox"
  | "radio";

export interface FormField {
  table_id?: number | null;
  column_key: string;
  column_name: string;
  field_label: string;
  widget_type: WidgetType;
  required: boolean;
  placeholder?: string;
  help_text?: string;
  widget_settings: Record<string, unknown>;
}

export interface FormConfiguration {
  id: number;
  workspace_id: number;
  table_id: number;
  name: string;
  description: string;
  fields: FormField[];
  is_published: boolean;
  collect_email: boolean;
  created_at: string;
  updated_at: string;
}

export interface TableDataRecord {
  id: number;
  workspace_id: number;
  table_id: number;
  data: Record<string, unknown>;
  submitter_email?: string | null;
  submitted_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TableDataRecordsListResponse {
  items: TableDataRecord[];
  total: number;
  skip: number;
  limit: number;
  pages: number;
}

export interface PublicFormSubmitResult {
  form_id: number;
  records: Array<{
    table_id: number;
    record_id: number;
  }>;
}
