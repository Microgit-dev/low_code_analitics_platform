export interface ImportScanField {
  key: string;
  path: string[];
  columns: number[];
  is_multi_value: boolean;
}

export interface ImportDetectedColumn {
  source_key: string;
  suggested_key: string;
  suggested_name: string;
  suggested_type: string;
  settings: Record<string, unknown>;
}

export interface ImportScanResult {
  sheet_name: string;
  source_format: string;
  region: Record<string, number>;
  structure: Record<string, number>;
  fields: ImportScanField[];
  merged_cells: Array<Record<string, number>>;
  artifacts: {
    merged_cells_count: number;
    sections_count: number;
    detected_sections: string[];
  };
  preview_rows: Array<Record<string, unknown>>;
  detected_columns: ImportDetectedColumn[];
}

export interface ImportTargetConfig {
  mode: "existing" | "new";
  table_id?: number | null;
  table_name?: string;
  table_description?: string;
  column_mappings: Record<string, string | null>;
  column_names?: Record<string, string | null>;
  column_types?: Record<string, string | null>;
  map_section_to_field: boolean;
  section_field_name: string;
}

export interface ImportApplyConfig {
  scan: {
    sheet_name?: string | null;
    header_row_start?: number | null;
    header_row_end?: number | null;
    data_row_start?: number | null;
    data_row_end?: number | null;
    list_split_delimiters: string[];
  };
  targets: ImportTargetConfig[];
}

export interface ImportApplyResult {
  imported_tables: Array<{
    table_id: number;
    table_name: string;
    created_records: number;
  }>;
}
