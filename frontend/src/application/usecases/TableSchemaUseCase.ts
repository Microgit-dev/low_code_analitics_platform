import type { TableRelation, TableStructure } from '../../domain/entities/TableSchema'
import { tableSchemaApi } from '../../infrastructure/api/tableSchemaApi'

export class TableSchemaUseCase {
  async listTables(token: string, workspaceId: number): Promise<TableStructure[]> {
    return tableSchemaApi.listTables(token, workspaceId)
  }

  async createTable(
    token: string,
    workspaceId: number,
    payload: Pick<TableStructure, 'name' | 'description' | 'columns'>
  ): Promise<TableStructure> {
    return tableSchemaApi.createTable(token, workspaceId, payload)
  }

  async updateTable(
    token: string,
    workspaceId: number,
    tableId: number,
    payload: Pick<TableStructure, 'name' | 'description' | 'columns'>
  ): Promise<TableStructure> {
    return tableSchemaApi.updateTable(token, workspaceId, tableId, payload)
  }

  async moveColumn(
    token: string,
    workspaceId: number,
    sourceTableId: number,
    targetTableId: number,
    columnKey: string
  ): Promise<void> {
    return tableSchemaApi.moveColumn(token, workspaceId, sourceTableId, targetTableId, columnKey)
  }

  async listRelations(token: string, workspaceId: number): Promise<TableRelation[]> {
    return tableSchemaApi.listRelations(token, workspaceId)
  }

  async createRelation(
    token: string,
    workspaceId: number,
    payload: {
      source_table_id: number
      target_table_id: number
      relation_type: 'one_to_one' | 'one_to_many' | 'many_to_many'
      name: string
      mapping: Record<string, string>
      properties: Record<string, unknown>
    }
  ): Promise<TableRelation> {
    return tableSchemaApi.createRelation(token, workspaceId, payload)
  }

  async deleteRelation(token: string, workspaceId: number, relationId: number): Promise<void> {
    return tableSchemaApi.deleteRelation(token, workspaceId, relationId)
  }
}
