import type { TableRelation, TableStructure } from '../../domain/entities/TableSchema'
import { httpClient } from './httpClient'

export const tableSchemaApi = {
  async listTables(token: string, workspaceId: number): Promise<TableStructure[]> {
    const { data } = await httpClient.get<TableStructure[]>(`/workspaces/${workspaceId}/schema/tables`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    return data
  },

  async createTable(
    token: string,
    workspaceId: number,
    payload: Pick<TableStructure, 'name' | 'description' | 'columns'>
  ): Promise<TableStructure> {
    const { data } = await httpClient.post<TableStructure>(`/workspaces/${workspaceId}/schema/tables`, payload, {
      headers: { Authorization: `Bearer ${token}` }
    })
    return data
  },

  async updateTable(
    token: string,
    workspaceId: number,
    tableId: number,
    payload: Pick<TableStructure, 'name' | 'description' | 'columns'>
  ): Promise<TableStructure> {
    const { data } = await httpClient.put<TableStructure>(
      `/workspaces/${workspaceId}/schema/tables/${tableId}`,
      payload,
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return data
  },

  async moveColumn(
    token: string,
    workspaceId: number,
    sourceTableId: number,
    targetTableId: number,
    columnKey: string
  ): Promise<void> {
    await httpClient.post(
      `/workspaces/${workspaceId}/schema/columns/move`,
      { source_table_id: sourceTableId, target_table_id: targetTableId, column_key: columnKey },
      { headers: { Authorization: `Bearer ${token}` } }
    )
  },

  async listRelations(token: string, workspaceId: number): Promise<TableRelation[]> {
    const { data } = await httpClient.get<TableRelation[]>(`/workspaces/${workspaceId}/schema/relations`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    return data
  },

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
    const { data } = await httpClient.post<TableRelation>(`/workspaces/${workspaceId}/schema/relations`, payload, {
      headers: { Authorization: `Bearer ${token}` }
    })
    return data
  },

  async deleteRelation(token: string, workspaceId: number, relationId: number): Promise<void> {
    await httpClient.delete(`/workspaces/${workspaceId}/schema/relations/${relationId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
  }
}
