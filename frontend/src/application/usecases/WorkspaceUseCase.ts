import type { Workspace } from '../../domain/entities/Auth'
import { workspaceApi } from '../../infrastructure/api/workspaceApi'

export class WorkspaceUseCase {
  async list(token: string): Promise<Workspace[]> {
    return workspaceApi.list(token)
  }

  async create(token: string, name: string, description?: string): Promise<Workspace> {
    return workspaceApi.create(token, name, description)
  }

  async delete(token: string, workspaceId: number): Promise<void> {
    return workspaceApi.delete(token, workspaceId)
  }
}
