import type { ImportApplyConfig, ImportApplyResult, ImportScanResult } from '../../domain/entities/Import'
import { httpClient } from './httpClient'

export const importApi = {
  async scanFile(
    token: string,
    workspaceId: number,
    file: File,
    options: {
      sheet_name?: string | null
      header_row_start?: number | null
      header_row_end?: number | null
      data_row_start?: number | null
      data_row_end?: number | null
      list_split_delimiters: string[]
    }
  ): Promise<ImportScanResult> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('options_json', JSON.stringify(options))

    const { data } = await httpClient.post<ImportScanResult>(`/workspaces/${workspaceId}/import/scan`, formData, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'multipart/form-data'
      }
    })

    return data
  },

  async applyImport(
    token: string,
    workspaceId: number,
    file: File,
    config: ImportApplyConfig
  ): Promise<ImportApplyResult> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('config_json', JSON.stringify(config))

    const { data } = await httpClient.post<ImportApplyResult>(`/workspaces/${workspaceId}/import/apply`, formData, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'multipart/form-data'
      }
    })

    return data
  }
}
