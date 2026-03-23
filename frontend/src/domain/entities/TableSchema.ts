export type ColumnType =
  | 'text'
  | 'number'
  | 'boolean'
  | 'date'
  | 'datetime'
  | 'enum'
  | 'list'
  | 'geoPoint'
  | 'geoPolygon'

export type RelationType = 'one_to_one' | 'one_to_many' | 'many_to_many'

export interface ColumnDefinition {
  key: string
  name: string
  type: ColumnType
  required: boolean
  settings: Record<string, unknown>
}

export interface TableStructure {
  id: number
  workspace_id: number
  name: string
  description: string | null
  columns: ColumnDefinition[]
  created_at: string
  updated_at: string
}

export interface TableRelation {
  id: number
  workspace_id: number
  source_table_id: number
  target_table_id: number
  relation_type: RelationType
  name: string
  mapping: Record<string, string>
  properties: Record<string, unknown>
  created_at: string
}
