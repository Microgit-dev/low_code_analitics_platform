<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ReportUseCase } from '../../application/usecases/ReportUseCase'
import { TableSchemaUseCase } from '../../application/usecases/TableSchemaUseCase'
import type {
  DocumentTemplateConverterRule,
  DocumentTemplateSettings,
  DocumentTemplateVisualBlock,
  ReportConfiguration,
} from '../../domain/entities/Report'
import type { ColumnDefinition, TableStructure } from '../../domain/entities/TableSchema'
import { useAuthStore } from '../stores/authStore'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const workspaceId = computed(() => Number(route.params.workspaceId))
const reportId = computed(() => Number(route.params.reportId))

const reportUseCase = new ReportUseCase(authStore.token || '')
const tableSchemaUseCase = new TableSchemaUseCase()

const loading = ref(false)
const saving = ref(false)
const exportLoading = ref<'docx' | 'pdf' | null>(null)
const error = ref('')
const dragBlockIndex = ref<number | null>(null)
const draggedBlockId = ref<string | null>(null)
const docCanvasRef = ref<HTMLElement | null>(null)

const reportName = ref('')
const reportDescription = ref('')
const reportIsPublished = ref(false)

const tables = ref<TableStructure[]>([])

const settings = ref<DocumentTemplateSettings>({
  table_id: null,
  template_mode: 'visual',
  visual_blocks: [{ type: 'text', value: 'Новый документ' }],
  jinja_template: '{% for row in rows %}{{ row }}\\n{% endfor %}',
  data_converter: []
})

const selectedTable = computed(() =>
  tables.value.find((table: TableStructure) => table.id === settings.value.table_id) ?? null
)

const tableColumns = computed(() => selectedTable.value?.columns ?? [])

type BlockType = DocumentTemplateVisualBlock['type']
type BlockLayout = { x: number; y: number; w: number; h: number }
type OrderedBlockItem = { block: DocumentTemplateVisualBlock; index: number; layout: BlockLayout }

const docGridCols = ref(12)
const docGridRows = ref(24)
const docCellSize = ref(58)

const docCanvasStyle = computed(() => ({
  gridTemplateColumns: `repeat(${docGridCols.value}, ${docCellSize.value}px)`,
  gridTemplateRows: `repeat(${docGridRows.value}, ${docCellSize.value}px)`,
  width: `${docGridCols.value * docCellSize.value}px`,
  minHeight: `${docGridRows.value * docCellSize.value}px`
}))

const visualBlockTypeOptions: Array<{ id: BlockType; title: string }> = [
  { id: 'text', title: 'Текст' },
  { id: 'field', title: 'Поле first.*' },
  { id: 'section_title', title: 'Секция' },
  { id: 'line_break', title: 'Перенос строки' },
  { id: 'if_row', title: 'Условие по first.*' },
  { id: 'table', title: 'Таблица rows.*' },
  { id: 'nested_table', title: 'Вложенная таблица' },
]

const defaultLayoutForType = (type: BlockType, index: number): BlockLayout => {
  const baseX = (index * 3) % docGridCols.value
  const baseY = Math.floor(index / 4) * 3

  if (type === 'text') return { x: baseX, y: baseY, w: 5, h: 2 }
  if (type === 'section_title') return { x: baseX, y: baseY, w: 6, h: 2 }
  if (type === 'line_break') return { x: baseX, y: baseY, w: 3, h: 1 }
  if (type === 'table') return { x: baseX, y: baseY, w: 7, h: 4 }
  if (type === 'nested_table') return { x: baseX, y: baseY, w: 7, h: 4 }
  if (type === 'if_row') return { x: baseX, y: baseY, w: 6, h: 3 }
  return { x: baseX, y: baseY, w: 4, h: 2 }
}

const ensureBlockLayout = (block: DocumentTemplateVisualBlock, index: number): BlockLayout => {
  if (!block.config || typeof block.config !== 'object') {
    block.config = { layout: defaultLayoutForType(block.type, index) }
  }

  const config = block.config as Record<string, unknown>
  const layoutRaw = config.layout && typeof config.layout === 'object' ? (config.layout as Record<string, unknown>) : {}
  const fallback = defaultLayoutForType(block.type, index)

  const layout: BlockLayout = {
    x: typeof layoutRaw.x === 'number' ? layoutRaw.x : fallback.x,
    y: typeof layoutRaw.y === 'number' ? layoutRaw.y : fallback.y,
    w: typeof layoutRaw.w === 'number' ? layoutRaw.w : fallback.w,
    h: typeof layoutRaw.h === 'number' ? layoutRaw.h : fallback.h,
  }

  layout.w = Math.max(2, Math.min(docGridCols.value, Math.floor(layout.w)))
  layout.h = Math.max(1, Math.min(docGridRows.value, Math.floor(layout.h)))
  layout.x = Math.max(0, Math.min(docGridCols.value - layout.w, Math.floor(layout.x)))
  layout.y = Math.max(0, Math.min(docGridRows.value - layout.h, Math.floor(layout.y)))

  config.layout = layout
  block.config = config
  return layout
}

const rectsOverlap = (a: BlockLayout, b: BlockLayout): boolean =>
  a.x < b.x + b.w &&
  a.x + a.w > b.x &&
  a.y < b.y + b.h &&
  a.y + a.h > b.y

const isPlacementFree = (candidate: BlockLayout, skipIndex: number | null): boolean => {
  if (candidate.x < 0 || candidate.y < 0) return false
  if (candidate.x + candidate.w > docGridCols.value) return false
  if (candidate.y + candidate.h > docGridRows.value) return false

  for (let i = 0; i < settings.value.visual_blocks.length; i += 1) {
    if (skipIndex !== null && i === skipIndex) continue
    const current = settings.value.visual_blocks[i]
    if (!current) continue
    const currentLayout = ensureBlockLayout(current, i)
    if (rectsOverlap(candidate, currentLayout)) return false
  }

  return true
}

const findNearestFreeSpot = (origin: BlockLayout, skipIndex: number | null): BlockLayout => {
  if (isPlacementFree(origin, skipIndex)) return origin

  const maxRadius = Math.max(docGridCols.value, docGridRows.value)
  for (let radius = 1; radius <= maxRadius; radius += 1) {
    for (let dx = -radius; dx <= radius; dx += 1) {
      for (let dy = -radius; dy <= radius; dy += 1) {
        if (Math.abs(dx) !== radius && Math.abs(dy) !== radius) continue

        const candidate: BlockLayout = {
          x: Math.max(0, Math.min(docGridCols.value - origin.w, origin.x + dx)),
          y: Math.max(0, Math.min(docGridRows.value - origin.h, origin.y + dy)),
          w: origin.w,
          h: origin.h,
        }

        if (isPlacementFree(candidate, skipIndex)) {
          return candidate
        }
      }
    }
  }

  return origin
}

const applyBlockLayout = (index: number, layout: BlockLayout) => {
  const block = settings.value.visual_blocks[index]
  if (!block) return
  if (!block.config || typeof block.config !== 'object') block.config = {}
  ;(block.config as Record<string, unknown>).layout = layout
}

const placeBlockWithCollision = (index: number, desired: BlockLayout) => {
  const snapped = findNearestFreeSpot(desired, index)
  applyBlockLayout(index, snapped)
}

const autoArrangeBlocks = () => {
  let cursorX = 0
  let cursorY = 0
  let rowHeight = 0

  settings.value.visual_blocks.forEach((block: DocumentTemplateVisualBlock, index: number) => {
    const layout = ensureBlockLayout(block, index)
    const width = Math.max(2, Math.min(docGridCols.value, layout.w))
    const height = Math.max(1, Math.min(docGridRows.value, layout.h))

    if (cursorX + width > docGridCols.value) {
      cursorX = 0
      cursorY += Math.max(1, rowHeight)
      rowHeight = 0
    }

    const candidate: BlockLayout = {
      x: cursorX,
      y: Math.min(docGridRows.value - height, cursorY),
      w: width,
      h: height,
    }

    placeBlockWithCollision(index, candidate)

    const placed = ensureBlockLayout(block, index)
    cursorX = placed.x + placed.w
    rowHeight = Math.max(rowHeight, placed.h)
  })
}

const resolveCollisionsKeepOrder = () => {
  settings.value.visual_blocks.forEach((block: DocumentTemplateVisualBlock, index: number) => {
    const current = ensureBlockLayout(block, index)
    placeBlockWithCollision(index, { ...current })
  })
}

const orderedVisualBlocks = computed(() =>
  settings.value.visual_blocks
    .map((block: DocumentTemplateVisualBlock, index: number): OrderedBlockItem => ({ block, index, layout: ensureBlockLayout(block, index) }))
    .sort((a: OrderedBlockItem, b: OrderedBlockItem) => (a.layout.y - b.layout.y) || (a.layout.x - b.layout.x))
)

const createDefaultBlock = (type: BlockType): DocumentTemplateVisualBlock => {
  if (type === 'field') {
    return { type, value: tableColumns.value[0]?.key ?? '' }
  }

  if (type === 'section_title') {
    return { type, value: 'Новая секция' }
  }

  if (type === 'line_break') {
    return { type, value: '' }
  }

  if (type === 'if_row') {
    return {
      type,
      value: 'Условный блок',
      config: {
        field: tableColumns.value[0]?.key ?? '',
        operator: 'not_empty',
        compare_to: ''
      }
    }
  }

  if (type === 'table') {
    return {
      type,
      value: 'Таблица',
      config: {
        columns: tableColumns.value.slice(0, 3).map((column: ColumnDefinition) => column.key)
      }
    }
  }

  if (type === 'nested_table') {
    return {
      type,
      value: 'Вложенная таблица',
      config: {
        iter_expr: 'row.items',
        row_alias: 'item',
        columns: []
      }
    }
  }

  return { type: 'text', value: 'Новый текст' }
}

const getIfConfig = (block: DocumentTemplateVisualBlock) => {
  if (!block.config || typeof block.config !== 'object') {
    block.config = { field: '', operator: 'not_empty', compare_to: '', else_text: '' }
  }
  return block.config as { field?: string; operator?: string; compare_to?: string; else_text?: string }
}

const getTableColumnsConfig = (block: DocumentTemplateVisualBlock): string[] => {
  if (!block.config || typeof block.config !== 'object') {
    block.config = { columns: [] }
  }
  const config = block.config as { columns?: unknown }
  if (!Array.isArray(config.columns)) {
    config.columns = []
  }
  return config.columns as string[]
}

const toggleTableColumn = (block: DocumentTemplateVisualBlock, key: string, enabled: boolean) => {
  const columns = getTableColumnsConfig(block)
  if (enabled) {
    if (!columns.includes(key)) columns.push(key)
    return
  }
  block.config = {
    ...(block.config || {}),
    columns: columns.filter((item) => item !== key)
  }
}

const getNestedTableConfig = (block: DocumentTemplateVisualBlock) => {
  if (!block.config || typeof block.config !== 'object') {
    block.config = { iter_expr: 'row.items', row_alias: 'item', columns: [] }
  }
  const config = block.config as { iter_expr?: string; row_alias?: string; columns?: unknown }
  if (!Array.isArray(config.columns)) {
    config.columns = []
  }
  return config as { iter_expr?: string; row_alias?: string; columns: string[] }
}

const generatedJinjaFromVisual = computed(() => {
  const chunks: string[] = []
  orderedVisualBlocks.value.forEach(({ block }: OrderedBlockItem) => {
    if (block.type === 'text') {
      chunks.push(block.value)
      return
    }

    if (block.type === 'section_title') {
      chunks.push(`## ${block.value}`)
      return
    }

    if (block.type === 'line_break') {
      chunks.push('')
      return
    }

    const key = block.value.trim()

    if (block.type === 'field') {
      if (!key) return
      chunks.push(`{{ first.${key} }}`)
      return
    }

    if (block.type === 'if_row') {
      const ifConfig = getIfConfig(block)
      const field = String(ifConfig.field || '').trim()
      const operator = String(ifConfig.operator || 'not_empty')
      const compareTo = String(ifConfig.compare_to || '')
      const elseText = String(ifConfig.else_text || '')
      if (!field) return

      let condition = `first.${field}`
      if (operator === 'eq') condition = `first.${field} == "${compareTo}"`
      if (operator === 'contains') condition = `"${compareTo}" in (first.${field} | string)`

      chunks.push(`{% if ${condition} %}`)
      chunks.push(block.value || `Поле ${field} соответствует условию`)
      if (elseText.trim()) {
        chunks.push('{% else %}')
        chunks.push(elseText)
      }
      chunks.push('{% endif %}')
      return
    }

    if (block.type === 'table') {
      const columns = getTableColumnsConfig(block)
      const safeColumns = columns.filter((item) => item.trim().length > 0)
      if (safeColumns.length === 0) return

      chunks.push('{% for row in rows %}')
      chunks.push(safeColumns.map((column) => `{{ row.${column} }}`).join(' | '))
      chunks.push('{% endfor %}')
      return
    }

    if (block.type === 'nested_table') {
      const nested = getNestedTableConfig(block)
      const iterExpr = String(nested.iter_expr || '').trim() || 'row.items'
      const rowAlias = String(nested.row_alias || '').trim() || 'item'
      const columns = nested.columns.filter((item) => item.trim().length > 0)
      if (columns.length === 0) return

      chunks.push(`{% for ${rowAlias} in ${iterExpr} %}`)
      chunks.push(columns.map((column) => `{{ ${rowAlias}.${column} }}`).join(' | '))
      chunks.push('{% endfor %}')
      return
    }
  })
  return chunks.join('\\n')
})

const visualPreviewLines = computed(() => {
  const source = generatedJinjaFromVisual.value
  if (!source.trim()) return ['(Пустой шаблон)']
  return source.split(/\r?\n/).slice(0, 45)
})

const effectiveJinja = computed(() =>
  settings.value.template_mode === 'visual' ? generatedJinjaFromVisual.value : settings.value.jinja_template
)

const addVisualBlock = (type: DocumentTemplateVisualBlock['type']) => {
  const next = createDefaultBlock(type)
  ensureBlockLayout(next, settings.value.visual_blocks.length)
  settings.value.visual_blocks.push(next)
  const newIndex = settings.value.visual_blocks.length - 1
  const current = ensureBlockLayout(next, newIndex)
  placeBlockWithCollision(newIndex, { ...current })
}

const onBlockDragStart = (index: number) => {
  dragBlockIndex.value = index
  draggedBlockId.value = `block-${index}`
}

const onBlockDrop = (targetIndex: number) => {
  if (dragBlockIndex.value === null) return
  const sourceIndex = dragBlockIndex.value
  dragBlockIndex.value = null
  if (sourceIndex === targetIndex) return

  const next = [...settings.value.visual_blocks]
  const [moved] = next.splice(sourceIndex, 1)
  if (!moved) return
  next.splice(targetIndex, 0, moved)
  settings.value.visual_blocks = next
}

const onBlockDragEnd = () => {
  dragBlockIndex.value = null
  draggedBlockId.value = null
}

const onCanvasDragOver = (event: DragEvent) => {
  event.preventDefault()
}

const onCanvasDrop = (event: DragEvent) => {
  event.preventDefault()
  if (dragBlockIndex.value === null) return
  const block = settings.value.visual_blocks[dragBlockIndex.value]
  if (!block || !docCanvasRef.value) return

  const rect = docCanvasRef.value.getBoundingClientRect()
  const rawX = Math.floor((event.clientX - rect.left) / docCellSize.value)
  const rawY = Math.floor((event.clientY - rect.top) / docCellSize.value)

  const layout = ensureBlockLayout(block, dragBlockIndex.value)
  const target: BlockLayout = {
    x: Math.max(0, Math.min(docGridCols.value - layout.w, rawX)),
    y: Math.max(0, Math.min(docGridRows.value - layout.h, rawY)),
    w: layout.w,
    h: layout.h,
  }
  placeBlockWithCollision(dragBlockIndex.value, target)

  dragBlockIndex.value = null
  draggedBlockId.value = null
}

const resizeBlock = (index: number, key: 'w' | 'h', delta: number) => {
  const block = settings.value.visual_blocks[index]
  if (!block) return
  const layout = ensureBlockLayout(block, index)

  const candidate: BlockLayout = { ...layout }
  if (key === 'w') {
    candidate.w = Math.max(2, Math.min(docGridCols.value, layout.w + delta))
    candidate.x = Math.max(0, Math.min(docGridCols.value - candidate.w, layout.x))
  } else {
    candidate.h = Math.max(1, Math.min(docGridRows.value, layout.h + delta))
    candidate.y = Math.max(0, Math.min(docGridRows.value - candidate.h, layout.y))
  }
  placeBlockWithCollision(index, candidate)
}

const syncLayouts = () => {
  settings.value.visual_blocks.forEach((block: DocumentTemplateVisualBlock, index: number) => {
    ensureBlockLayout(block, index)
  })
  resolveCollisionsKeepOrder()
}

watch([docGridCols, docGridRows], () => {
  resolveCollisionsKeepOrder()
})

const removeVisualBlock = (index: number) => {
  settings.value.visual_blocks = settings.value.visual_blocks.filter((_: DocumentTemplateVisualBlock, idx: number) => idx !== index)
}

const addConverterRule = () => {
  settings.value.data_converter.push({
    output_key: '',
    source_field: tableColumns.value[0]?.key ?? '',
    transform: 'none'
  })
}

const removeConverterRule = (index: number) => {
  settings.value.data_converter = settings.value.data_converter.filter((_: DocumentTemplateConverterRule, idx: number) => idx !== index)
}

const normalizeSettings = (raw: Record<string, unknown>): DocumentTemplateSettings => {
  const visualBlocks: DocumentTemplateVisualBlock[] = Array.isArray(raw.visual_blocks)
    ? raw.visual_blocks
        .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
        .map((item) => ({
          type:
            item.type === 'field' ||
            item.type === 'section_title' ||
            item.type === 'line_break' ||
            item.type === 'if_row' ||
            item.type === 'table' ||
            item.type === 'nested_table'
              ? item.type
              : 'text',
          value: String(item.value ?? ''),
          config:
            item.config && typeof item.config === 'object'
              ? (item.config as Record<string, unknown>)
              : undefined
        }))
    : [{ type: 'text', value: 'Новый документ' }]

  const converter: DocumentTemplateConverterRule[] = Array.isArray(raw.data_converter)
    ? raw.data_converter
        .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
        .map((item) => ({
          output_key: String(item.output_key ?? ''),
          source_field: String(item.source_field ?? ''),
          transform:
            item.transform === 'upper' ||
            item.transform === 'lower' ||
            item.transform === 'date' ||
            item.transform === 'number'
              ? (item.transform as DocumentTemplateConverterRule['transform'])
              : 'none'
        }))
    : []

  return {
    table_id: typeof raw.table_id === 'number' ? raw.table_id : null,
    template_mode: raw.template_mode === 'jinja2' ? 'jinja2' : 'visual',
    visual_blocks: visualBlocks,
    jinja_template: String(raw.jinja_template ?? '{% for row in rows %}{{ row }}\\n{% endfor %}'),
    data_converter: converter
  }
}

const parseSupportedJinjaToBlocks = (jinja: string): DocumentTemplateVisualBlock[] => {
  type JinjaNode =
    | { type: 'text'; content: string }
    | { type: 'expr'; content: string }
    | { type: 'for'; itemVar: string; iterExpr: string; body: JinjaNode[] }
    | { type: 'if'; condition: string; thenBody: JinjaNode[]; elseBody: JinjaNode[] }

  type Token =
    | { kind: 'text'; value: string }
    | { kind: 'expr'; value: string }
    | { kind: 'stmt'; value: string }

  const tokens: Token[] = []
  const pattern = /(\{\{[\s\S]*?\}\}|\{%[\s\S]*?%\})/g
  let cursor = 0
  for (const match of jinja.matchAll(pattern)) {
    const token = match[0]
    const tokenIndex = match.index ?? 0
    const textChunk = jinja.slice(cursor, tokenIndex)
    if (textChunk) tokens.push({ kind: 'text', value: textChunk })

    if (token.startsWith('{{')) {
      tokens.push({ kind: 'expr', value: token.slice(2, -2).trim() })
    } else {
      tokens.push({ kind: 'stmt', value: token.slice(2, -2).trim() })
    }
    cursor = tokenIndex + token.length
  }
  if (cursor < jinja.length) {
    tokens.push({ kind: 'text', value: jinja.slice(cursor) })
  }

  let pointer = 0

  const parseNodes = (stopWords: string[] = []): JinjaNode[] => {
    const nodes: JinjaNode[] = []

    while (pointer < tokens.length) {
      const token = tokens[pointer]
      if (!token) break

      if (token.kind === 'stmt') {
        const stmt = token.value
        const head = stmt.split(/\s+/)[0] || ''

        if (stopWords.includes(head)) {
          break
        }

        const forMatch = stmt.match(/^for\s+([a-zA-Z0-9_]+)\s+in\s+(.+)$/)
        if (forMatch) {
          pointer += 1
          const body = parseNodes(['endfor'])
          if (tokens[pointer]?.kind === 'stmt' && tokens[pointer]?.value.startsWith('endfor')) {
            pointer += 1
          }
          nodes.push({ type: 'for', itemVar: forMatch[1], iterExpr: forMatch[2].trim(), body })
          continue
        }

        const ifMatch = stmt.match(/^if\s+(.+)$/)
        if (ifMatch) {
          pointer += 1
          const thenBody = parseNodes(['else', 'endif'])

          let elseBody: JinjaNode[] = []
          if (tokens[pointer]?.kind === 'stmt' && tokens[pointer]?.value === 'else') {
            pointer += 1
            elseBody = parseNodes(['endif'])
          }
          if (tokens[pointer]?.kind === 'stmt' && tokens[pointer]?.value.startsWith('endif')) {
            pointer += 1
          }

          nodes.push({ type: 'if', condition: ifMatch[1].trim(), thenBody, elseBody })
          continue
        }

        pointer += 1
        continue
      }

      if (token.kind === 'expr') {
        nodes.push({ type: 'expr', content: token.value })
        pointer += 1
        continue
      }

      nodes.push({ type: 'text', content: token.value })
      pointer += 1
    }

    return nodes
  }

  const flattenNodeText = (nodes: JinjaNode[]): string => {
    const lines: string[] = []
    nodes.forEach((node) => {
      if (node.type === 'text') {
        lines.push(node.content)
        return
      }
      if (node.type === 'expr') {
        lines.push(`{{ ${node.content} }}`)
        return
      }
      if (node.type === 'for') {
        lines.push(`{% for ${node.itemVar} in ${node.iterExpr} %}`)
        lines.push(flattenNodeText(node.body))
        lines.push('{% endfor %}')
        return
      }
      lines.push(`{% if ${node.condition} %}`)
      lines.push(flattenNodeText(node.thenBody))
      if (node.elseBody.length > 0) {
        lines.push('{% else %}')
        lines.push(flattenNodeText(node.elseBody))
      }
      lines.push('{% endif %}')
    })
    return lines.join('')
  }

  const convertNodesToBlocks = (nodes: JinjaNode[]): DocumentTemplateVisualBlock[] => {
    const result: DocumentTemplateVisualBlock[] = []

    nodes.forEach((node) => {
      if (node.type === 'text') {
        const lines = node.content.split(/\r?\n/)
        lines.forEach((line) => {
          if (line.startsWith('## ')) {
            result.push({ type: 'section_title', value: line.slice(3) })
            return
          }
          if (!line.trim()) {
            result.push({ type: 'line_break', value: '' })
            return
          }
          result.push({ type: 'text', value: line })
        })
        return
      }

      if (node.type === 'expr') {
        const firstFieldMatch = node.content.match(/^first\.([a-zA-Z0-9_]+)$/)
        if (firstFieldMatch) {
          result.push({ type: 'field', value: firstFieldMatch[1] })
          return
        }
        result.push({ type: 'text', value: `{{ ${node.content} }}` })
        return
      }

      if (node.type === 'for') {
        const bodyRaw = flattenNodeText(node.body)
        const rowColumns = Array.from(bodyRaw.matchAll(/\{\{\s*row\.([a-zA-Z0-9_]+)\s*\}\}/g)).map((item) => item[1])
        if (node.itemVar === 'row' && node.iterExpr === 'rows' && rowColumns.length > 0) {
          result.push({ type: 'table', value: 'Таблица', config: { columns: rowColumns } })
          return
        }

        const nestedColumns = Array.from(
          bodyRaw.matchAll(new RegExp(`\\{\\{\\s*${node.itemVar}\\.([a-zA-Z0-9_]+)\\s*\\}\\}`, 'g'))
        ).map((item) => item[1])

        result.push({
          type: 'nested_table',
          value: 'Вложенная таблица',
          config: {
            iter_expr: node.iterExpr,
            row_alias: node.itemVar,
            columns: nestedColumns
          }
        })
        return
      }

      const condition = node.condition.trim()
      let field = ''
      let operator = 'not_empty'
      let compare_to = ''

      const eqMatch = condition.match(/^first\.([a-zA-Z0-9_]+)\s*==\s*"(.*)"$/)
      if (eqMatch) {
        field = eqMatch[1]
        operator = 'eq'
        compare_to = eqMatch[2]
      } else {
        const containsMatch = condition.match(/^"(.*)"\s+in\s+\(first\.([a-zA-Z0-9_]+)\s*\|\s*string\)$/)
        if (containsMatch) {
          compare_to = containsMatch[1]
          field = containsMatch[2]
          operator = 'contains'
        } else {
          const simpleMatch = condition.match(/^first\.([a-zA-Z0-9_]+)$/)
          if (simpleMatch) field = simpleMatch[1]
        }
      }

      result.push({
        type: 'if_row',
        value: flattenNodeText(node.thenBody).trim() || 'Условный блок',
        config: {
          field,
          operator,
          compare_to,
          else_text: flattenNodeText(node.elseBody).trim()
        }
      })
    })

    return result
  }

  pointer = 0
  const ast = parseNodes([])
  return convertNodesToBlocks(ast)
}

const syncJinjaToVisual = () => {
  settings.value.visual_blocks = parseSupportedJinjaToBlocks(settings.value.jinja_template)
  syncLayouts()
}

const syncVisualToJinja = () => {
  settings.value.jinja_template = generatedJinjaFromVisual.value
}

const load = async () => {
  if (!authStore.token || !workspaceId.value || !reportId.value) return
  loading.value = true
  error.value = ''

  try {
    tables.value = await tableSchemaUseCase.listTables(authStore.token, workspaceId.value)
    const report: ReportConfiguration = await reportUseCase.getReport(workspaceId.value, reportId.value)

    if (report.report_type !== 'docx_template') {
      throw new Error('Неверный тип отчета для docx-редактора')
    }

    reportName.value = report.name
    reportDescription.value = report.description || ''
    reportIsPublished.value = report.is_published
    settings.value = normalizeSettings((report.settings ?? {}) as Record<string, unknown>)
    syncLayouts()
    if (settings.value.template_mode === 'jinja2' && settings.value.visual_blocks.length === 0) {
      syncJinjaToVisual()
    }
  } catch (err) {
    console.error(err)
    error.value = 'Не удалось загрузить docx шаблон'
  } finally {
    loading.value = false
  }
}

const save = async () => {
  if (!workspaceId.value || !reportId.value || !reportName.value.trim()) return

  saving.value = true
  try {
    await reportUseCase.updateReport(
      workspaceId.value,
      reportId.value,
      reportName.value.trim(),
      reportDescription.value.trim(),
      'docx_template',
      {
        ...settings.value,
        jinja_template: effectiveJinja.value
      },
      reportIsPublished.value
    )
  } catch (err) {
    console.error(err)
    error.value = 'Не удалось сохранить docx шаблон'
  } finally {
    saving.value = false
  }
}

const exportTemplate = async (format: 'docx' | 'pdf') => {
  if (!workspaceId.value || !reportId.value) return
  exportLoading.value = format
  try {
    const blob = await reportUseCase.downloadDocumentReport(workspaceId.value, reportId.value, format)
    const url = window.URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = format === 'docx' ? `document_${reportId.value}.docx` : `document_${reportId.value}.pdf`
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error(err)
    error.value = 'Не удалось выполнить экспорт документа'
  } finally {
    exportLoading.value = null
  }
}

onMounted(load)
</script>

<template>
  <main class="docx-editor editor-shell">
    <header class="docx-editor-head editor-shell-header">
      <div>
        <button class="small ghost" @click="router.push({ name: 'dashboard' })">Назад</button>
        <h2>DOCX шаблон</h2>
      </div>
      <div class="docx-editor-actions editor-shell-actions">
        <button class="small" :disabled="exportLoading !== null" @click="exportTemplate('docx')">
          {{ exportLoading === 'docx' ? 'Экспорт...' : 'Экспорт DOCX' }}
        </button>
        <button class="small" :disabled="exportLoading !== null" @click="exportTemplate('pdf')">
          {{ exportLoading === 'pdf' ? 'Экспорт...' : 'Экспорт PDF' }}
        </button>
        <button class="small" :disabled="saving" @click="save">
          {{ saving ? 'Сохранение...' : 'Сохранить' }}
        </button>
      </div>
    </header>

    <p v-if="loading">Загрузка...</p>
    <p v-else-if="error" class="error-text">{{ error }}</p>

    <section v-else class="docx-editor-grid editor-shell-grid columns-3">
      <article class="panel editor-shell-panel">
        <h3>Параметры</h3>
        <label>Название</label>
        <input v-model="reportName" />

        <label>Описание</label>
        <input v-model="reportDescription" />

        <label>Таблица</label>
        <select v-model.number="settings.table_id">
          <option :value="null">Не выбрана</option>
          <option v-for="table in tables" :key="table.id" :value="table.id">{{ table.name }}</option>
        </select>

        <label>Режим редактора</label>
        <select v-model="settings.template_mode">
          <option value="visual">Визуальный</option>
          <option value="jinja2">Jinja2</option>
        </select>

        <label class="checkbox-inline">
          <input v-model="reportIsPublished" type="checkbox" /> Опубликован
        </label>
      </article>

      <article class="panel editor-shell-panel">
        <h3>Шаблон</h3>

        <template v-if="settings.template_mode === 'visual'">
          <div class="toolbar-row">
            <button
              v-for="option in visualBlockTypeOptions"
              :key="`add-${option.id}`"
              class="small"
              @click="addVisualBlock(option.id)"
            >
              + {{ option.title }}
            </button>
            <button class="small ghost" @click="syncVisualToJinja">Синхр. в Jinja</button>
          </div>

          <div class="toolbar-row">
            <label>Колонки: {{ docGridCols }}</label>
            <input v-model.number="docGridCols" type="range" min="6" max="24" step="1" />
            <label>Строки: {{ docGridRows }}</label>
            <input v-model.number="docGridRows" type="range" min="8" max="60" step="1" />
            <label>Клетка: {{ docCellSize }} px</label>
            <input v-model.number="docCellSize" type="range" min="42" max="96" step="2" />
            <button class="small ghost" type="button" @click="autoArrangeBlocks">Авто-раскладка</button>
          </div>

          <div class="docx-canvas-wrap">
            <div ref="docCanvasRef" class="docx-canvas" :style="docCanvasStyle" @dragover="onCanvasDragOver" @drop="onCanvasDrop">
            <div
              v-for="item in orderedVisualBlocks"
              :key="`block-${item.index}`"
              class="block-row docx-canvas-block"
              :style="{
                gridColumn: `${item.layout.x + 1} / span ${item.layout.w}`,
                gridRow: `${item.layout.y + 1} / span ${item.layout.h}`,
              }"
              draggable="true"
              @dragstart="onBlockDragStart(item.index)"
              @dragend="onBlockDragEnd"
            >
              <div class="block-tools">
                <span class="muted">x:{{ item.layout.x }} y:{{ item.layout.y }} w:{{ item.layout.w }} h:{{ item.layout.h }}</span>
                <div class="block-tools-actions">
                  <button class="small" type="button" @click="resizeBlock(item.index, 'w', -1)">W-</button>
                  <button class="small" type="button" @click="resizeBlock(item.index, 'w', 1)">W+</button>
                  <button class="small" type="button" @click="resizeBlock(item.index, 'h', -1)">H-</button>
                  <button class="small" type="button" @click="resizeBlock(item.index, 'h', 1)">H+</button>
                </div>
              </div>

              <select v-model="item.block.type">
                <option value="text">Текст</option>
                <option value="field">Поле</option>
                <option value="section_title">Секция</option>
                <option value="line_break">Перенос строки</option>
                <option value="if_row">Условие</option>
                <option value="table">Таблица</option>
                <option value="nested_table">Вложенная таблица</option>
              </select>
              <input
                v-if="item.block.type === 'text' || item.block.type === 'section_title'"
                v-model="item.block.value"
                placeholder="Текст документа"
              />
              <select v-else-if="item.block.type === 'field'" v-model="item.block.value">
                <option value="">Выберите поле</option>
                <option v-for="column in tableColumns" :key="`column-${column.key}`" :value="column.key">
                  {{ column.name }} ({{ column.key }})
                </option>
              </select>
              <div v-else-if="item.block.type === 'line_break'" class="line-break-label">Пустая строка</div>
              <div v-else-if="item.block.type === 'if_row'" class="if-block-editor">
                <input v-model="item.block.value" placeholder="Текст внутри условия" />
                <div class="if-config-row">
                  <label>Поле</label>
                  <select v-model="getIfConfig(item.block).field">
                    <option value="">Поле</option>
                    <option v-for="column in tableColumns" :key="`if-col-${column.key}`" :value="column.key">{{ column.key }}</option>
                  </select>
                  <label>Оператор</label>
                  <select v-model="getIfConfig(item.block).operator">
                    <option value="not_empty">not_empty</option>
                    <option value="eq">eq</option>
                    <option value="contains">contains</option>
                  </select>
                  <label>Значение</label>
                  <input v-model="getIfConfig(item.block).compare_to" placeholder="сравнение" />
                </div>
              </div>
              <div v-else-if="item.block.type === 'table'" class="table-block-editor">
                <p class="muted">Колонки таблицы</p>
                <label v-for="column in tableColumns" :key="`tbl-col-${column.key}`" class="checkbox-inline">
                  <input
                    type="checkbox"
                    :checked="getTableColumnsConfig(item.block).includes(column.key)"
                    @change="toggleTableColumn(item.block, column.key, ($event.target as HTMLInputElement).checked)"
                  />
                  <span>{{ column.key }}</span>
                </label>
              </div>
              <div v-else-if="item.block.type === 'nested_table'" class="table-block-editor">
                <label>Итератор</label>
                <input v-model="getNestedTableConfig(item.block).iter_expr" placeholder="row.items" />
                <label>Переменная</label>
                <input v-model="getNestedTableConfig(item.block).row_alias" placeholder="item" />
                <label>Колонки</label>
                <input
                  :value="getNestedTableConfig(item.block).columns.join(', ')"
                  placeholder="name, amount"
                  @input="getNestedTableConfig(item.block).columns = ($event.target as HTMLInputElement).value.split(',').map((raw) => raw.trim()).filter(Boolean)"
                />
              </div>
              <button class="small danger" @click="removeVisualBlock(item.index)">Удалить</button>
            </div>
          </div>
          </div>

          <label>Сгенерированный Jinja2 (по layout сверху-вниз)</label>
          <textarea :value="generatedJinjaFromVisual" readonly rows="8" />
        </template>

        <template v-else>
          <div class="toolbar-row">
            <button class="small ghost" @click="syncJinjaToVisual">Синхр. в Visual</button>
          </div>
          <label>Jinja2 шаблон</label>
          <textarea v-model="settings.jinja_template" rows="14" placeholder="Используйте rows, first, meta" />
        </template>
      </article>

      <article class="panel editor-shell-panel">
        <h3>Конвертер данных</h3>
        <p class="muted">Преобразует поля перед подстановкой в шаблон.</p>

        <div class="toolbar-row">
          <button class="small" @click="addConverterRule">+ Правило</button>
        </div>

        <div class="converter-list" v-if="settings.data_converter.length > 0">
          <div v-for="(rule, index) in settings.data_converter" :key="`rule-${index}`" class="converter-row">
            <input v-model="rule.output_key" placeholder="output_key" />
            <select v-model="rule.source_field">
              <option value="">Поле источника</option>
              <option v-for="column in tableColumns" :key="`source-${column.key}`" :value="column.key">{{ column.key }}</option>
            </select>
            <select v-model="rule.transform">
              <option value="none">none</option>
              <option value="upper">upper</option>
              <option value="lower">lower</option>
              <option value="date">date</option>
              <option value="number">number</option>
            </select>
            <button class="small danger" @click="removeConverterRule(index)">Удалить</button>
          </div>
        </div>
        <p v-else class="muted">Правила пока не добавлены.</p>
      </article>

      <article class="panel doc-preview-panel editor-shell-panel">
        <h3>Мини-превью страницы</h3>
        <div class="doc-preview-sheet">
          <p v-for="(line, index) in visualPreviewLines" :key="`preview-line-${index}`">{{ line }}</p>
        </div>
      </article>
    </section>
  </main>
</template>

<style scoped>
.docx-editor {
  min-height: 100vh;
  padding: 16px;
  display: grid;
  gap: 12px;
  background: var(--bg);
}

.docx-editor-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.docx-editor-head h2 {
  margin: 8px 0 0;
}

.docx-editor-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.docx-editor-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.panel {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--bg-panel);
  padding: 12px;
  display: grid;
  gap: 8px;
  align-content: start;
}

.toolbar-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.block-list,
.converter-list {
  display: grid;
  gap: 8px;
}

.docx-canvas-wrap {
  border: 1px dashed var(--line);
  border-radius: 12px;
  background:
    var(--bg-grid),
    repeating-linear-gradient(0deg, color-mix(in srgb, var(--line-strong) 24%, transparent) 0, color-mix(in srgb, var(--line-strong) 24%, transparent) 1px, transparent 1px, transparent 28px),
    repeating-linear-gradient(90deg, color-mix(in srgb, var(--line-strong) 24%, transparent) 0, color-mix(in srgb, var(--line-strong) 24%, transparent) 1px, transparent 1px, transparent 28px);
  overflow: auto;
  padding: 8px;
}

.docx-canvas {
  display: grid;
  gap: 8px;
  position: relative;
}

.docx-canvas-block {
  align-content: start;
}

.block-tools {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
}

.block-tools-actions {
  display: inline-flex;
  gap: 4px;
}

.block-row,
.converter-row {
  display: grid;
  grid-template-columns: 120px 1fr auto;
  gap: 8px;
  align-items: center;
}

.block-row {
  border: 1px dashed color-mix(in srgb, var(--line-strong) 60%, transparent);
  border-radius: 10px;
  padding: 8px;
  background: color-mix(in srgb, var(--bg-soft) 82%, var(--bg-panel));
  cursor: grab;
}

.block-row:active {
  cursor: grabbing;
}

.converter-row {
  grid-template-columns: 1fr 1fr 120px auto;
}

.line-break-label {
  color: var(--text-muted);
  font-style: italic;
}

.if-block-editor,
.table-block-editor {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 8px;
  display: grid;
  gap: 8px;
  background: var(--bg-soft);
}

.if-config-row {
  display: grid;
  grid-template-columns: auto 1fr auto 140px auto 1fr;
  gap: 6px;
  align-items: center;
}

.muted {
  color: var(--text-muted);
}

.error-text {
  color: var(--danger);
}

.doc-preview-panel {
  grid-column: 1 / -1;
}

.doc-preview-sheet {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: linear-gradient(180deg, #fff, #f8fafc);
  color: #0f172a;
  padding: 16px;
  min-height: 320px;
  max-height: 420px;
  overflow: auto;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, #fff 70%, transparent);
}

.doc-preview-sheet p {
  margin: 0 0 6px;
  font-family: 'Times New Roman', Georgia, serif;
  font-size: 14px;
  line-height: 1.42;
}

@media (max-width: 1200px) {
  .docx-editor-grid {
    grid-template-columns: 1fr;
  }

  .if-config-row {
    grid-template-columns: 1fr;
  }

  .docx-canvas {
    width: 100% !important;
    min-width: 100%;
  }
}
</style>
