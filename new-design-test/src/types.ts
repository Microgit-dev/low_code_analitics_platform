export interface Workspace {
  id: number
  name: string
  description: string
}

export type ColumnType =
  | 'text'
  | 'longText'
  | 'number'
  | 'datetime'
  | 'radio'
  | 'checkbox'
  | 'select'
  | 'multiselect'
  | 'geoPoint'

export interface Column {
  id: number
  name: string
  type: ColumnType
  required: boolean
}

export interface Table {
  id: number
  name: string
  description: string
  columns: Column[]
  x: number
  y: number
}

export interface Form {
  id: number
  name: string
  description: string
  tableIds: number[]
  isPublic: boolean
  collectEmail: boolean
}

export type OutputType = 'excel' | 'word' | 'dashboard'

export interface Report {
  id: number
  name: string
  description: string
  formIds: number[]
  outputType: OutputType
}

export interface FormRecord {
  id: number
  formId: number
  values: Record<string, unknown>   // { columnName: value }
  submittedAt: string               // ISO date string
}
