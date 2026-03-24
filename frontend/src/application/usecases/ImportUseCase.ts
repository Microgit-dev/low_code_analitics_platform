import type { ImportApplyConfig, ImportApplyResult, ImportScanResult } from '../../domain/entities/Import'
import { importApi } from '../../infrastructure/api/importApi'

export class ImportUseCase {
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
    return importApi.scanFile(token, workspaceId, file, options)
  }

  async applyImport(
    token: string,
    workspaceId: number,
    file: File,
    config: ImportApplyConfig
  ): Promise<ImportApplyResult> {
    return importApi.applyImport(token, workspaceId, file, config)
  }
}
