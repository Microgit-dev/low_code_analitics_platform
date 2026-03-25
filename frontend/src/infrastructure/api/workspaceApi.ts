import type { Workspace } from '../../domain/entities/Auth'
import { httpClient } from './httpClient'

export const workspaceApi = {
  async list(token: string): Promise<Workspace[]> {
    const { data } = await httpClient.get<Workspace[]>('/workspaces', {
      headers: { Authorization: `Bearer ${token}` }
    })
    return data
  },

  async create(token: string, name: string, description?: string): Promise<Workspace> {
    const { data } = await httpClient.post<Workspace>(
      '/workspaces',
      { name, description },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return data
  },

  async update(token: string, workspaceId: number, name: string, description?: string): Promise<Workspace> {
    const { data } = await httpClient.put<Workspace>(
      `/workspaces/${workspaceId}`,
      { name, description },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return data
  },

  async delete(token: string, workspaceId: number): Promise<void> {
    await httpClient.delete(`/workspaces/${workspaceId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
  }
}
