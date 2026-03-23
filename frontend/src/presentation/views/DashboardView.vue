<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { TableSchemaUseCase } from '../../application/usecases/TableSchemaUseCase'
import { WorkspaceUseCase } from '../../application/usecases/WorkspaceUseCase'
import type { Workspace } from '../../domain/entities/Auth'
import type { ColumnType, TableRelation, TableStructure } from '../../domain/entities/TableSchema'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()
const router = useRouter()
const workspaceUseCase = new WorkspaceUseCase()
const tableSchemaUseCase = new TableSchemaUseCase()

type WorkspaceTab = 'details' | 'tables'
type TablePosition = { x: number; y: number }

const workspaces = ref<Workspace[]>([])
const loading = ref(false)
const deleting = ref(false)
const schemaLoading = ref(false)
const schemaError = ref('')
const workspaceTab = ref<WorkspaceTab>('tables')

const workspaceName = ref('')
const workspaceDescription = ref('')
const selectedWorkspaceId = ref<number | null>(null)

const tableStructures = ref<TableStructure[]>([])
const relations = ref<TableRelation[]>([])
const activeTableId = ref<number | null>(null)
const selectedColumnRef = ref<{ tableId: number; columnKey: string } | null>(null)
const tablePositions = ref<Record<number, TablePosition>>({})
const tableDragging = ref<{ tableId: number; offsetX: number; offsetY: number } | null>(null)

const newTableName = ref('')
const newTableDescription = ref('')

const newColumnName = ref('')
const newColumnType = ref<ColumnType>('text')
const newColumnRequired = ref(false)
const newColumnEnumOptions = ref('')
const newColumnListItemType = ref<'text' | 'number' | 'boolean' | 'enum'>('text')
const newColumnGeoSrid = ref(4326)
const newColumnGeoAllowHoles = ref(false)

const relationName = ref('')
const relationSourceTableId = ref('')
const relationTargetTableId = ref('')
const relationType = ref<'one_to_one' | 'one_to_many' | 'many_to_many'>('one_to_many')
const relationSourceColumn = ref('')
const relationTargetColumn = ref('')

const dragState = ref<{ sourceTableId: number; columnKey: string } | null>(null)

const selectedWorkspace = computed(() => {
  if (selectedWorkspaceId.value === null) return null
  return workspaces.value.find((workspace) => workspace.id === selectedWorkspaceId.value) ?? null
})

const activeTable = computed(() => {
  if (activeTableId.value === null) return null
  return tableStructures.value.find((table) => table.id === activeTableId.value) ?? null
})

const selectedColumnParent = computed(() => {
  if (selectedColumnRef.value === null) return null
  return tableStructures.value.find((table) => table.id === selectedColumnRef.value?.tableId) ?? null
})

const selectedColumn = computed(() => {
  if (selectedColumnRef.value === null) return null
  const parent = selectedColumnParent.value
  if (!parent) return null
  return parent.columns.find((column) => column.key === selectedColumnRef.value?.columnKey) ?? null
})

const allTableOptions = computed(() => tableStructures.value.map((table) => ({ id: table.id, name: table.name })))

const relationSourceColumns = computed(() => {
  const sourceId = Number(relationSourceTableId.value)
  if (!sourceId) return []
  return tableStructures.value.find((table) => table.id === sourceId)?.columns ?? []
})

const relationTargetColumns = computed(() => {
  const targetId = Number(relationTargetTableId.value)
  if (!targetId) return []
  return tableStructures.value.find((table) => table.id === targetId)?.columns ?? []
})

const loadWorkspaces = async () => {
  if (!authStore.token) return
  loading.value = true
  try {
    await authStore.fetchMe()
    workspaces.value = await workspaceUseCase.list(authStore.token)
    if (workspaces.value.length > 0) {
      const selectedExists = workspaces.value.some((workspace) => workspace.id === selectedWorkspaceId.value)
      selectedWorkspaceId.value = selectedExists ? selectedWorkspaceId.value : workspaces.value[0].id
    } else {
      selectedWorkspaceId.value = null
    }
  } finally {
    loading.value = false
  }
}

const loadSchema = async () => {
  if (!authStore.token || !selectedWorkspace.value) {
    tableStructures.value = []
    relations.value = []
    activeTableId.value = null
    selectedColumnRef.value = null
    tablePositions.value = {}
    return
  }

  schemaLoading.value = true
  schemaError.value = ''
  try {
    tableStructures.value = await tableSchemaUseCase.listTables(authStore.token, selectedWorkspace.value.id)
    relations.value = await tableSchemaUseCase.listRelations(authStore.token, selectedWorkspace.value.id)
    if (tableStructures.value.length > 0) {
      const hasActive = tableStructures.value.some((table) => table.id === activeTableId.value)
      activeTableId.value = hasActive ? activeTableId.value : tableStructures.value[0].id
    } else {
      activeTableId.value = null
    }

    if (selectedColumnRef.value) {
      const parent = tableStructures.value.find((table) => table.id === selectedColumnRef.value?.tableId)
      const hasColumn = parent?.columns.some((column) => column.key === selectedColumnRef.value?.columnKey)
      if (!hasColumn) {
        selectedColumnRef.value = null
      }
    }

    const nextPositions: Record<number, TablePosition> = {}
    for (const [index, table] of tableStructures.value.entries()) {
      nextPositions[table.id] = tablePositions.value[table.id] ?? {
        x: 36 + (index % 3) * 310,
        y: 36 + Math.floor(index / 3) * 260
      }
    }
    tablePositions.value = nextPositions
  } catch {
    schemaError.value = 'Не удалось загрузить low-code структуры.'
  } finally {
    schemaLoading.value = false
  }
}

const createWorkspace = async () => {
  if (!authStore.token || !workspaceName.value.trim()) return

  await workspaceUseCase.create(authStore.token, workspaceName.value.trim(), workspaceDescription.value.trim())
  workspaceName.value = ''
  workspaceDescription.value = ''
  await loadWorkspaces()
  await loadSchema()
}

const deleteWorkspace = async () => {
  if (!authStore.token || !selectedWorkspace.value || deleting.value) return

  const shouldDelete = window.confirm(
    `Удалить workspace \"${selectedWorkspace.value.name}\"? Это действие нельзя отменить.`
  )
  if (!shouldDelete) return

  deleting.value = true
  try {
    await workspaceUseCase.delete(authStore.token, selectedWorkspace.value.id)
    await loadWorkspaces()
    await loadSchema()
  } finally {
    deleting.value = false
  }
}

const selectWorkspace = async (workspaceId: number) => {
  selectedWorkspaceId.value = workspaceId
  workspaceTab.value = 'tables'
  await loadSchema()
}

const selectTable = (tableId: number) => {
  activeTableId.value = tableId
  selectedColumnRef.value = null
}

const selectColumn = (tableId: number, columnKey: string) => {
  activeTableId.value = tableId
  selectedColumnRef.value = { tableId, columnKey }
}

const getTablePosition = (tableId: number): TablePosition => {
  const fallback = { x: 40, y: 40 }
  if (!tablePositions.value[tableId]) {
    tablePositions.value[tableId] = fallback
  }
  return tablePositions.value[tableId] ?? fallback
}

const onCanvasPointerMove = (event: PointerEvent) => {
  const drag = tableDragging.value
  if (!drag) return

  tablePositions.value = {
    ...tablePositions.value,
    [drag.tableId]: {
      x: Math.max(16, event.clientX - drag.offsetX),
      y: Math.max(16, event.clientY - drag.offsetY)
    }
  }
}

const stopTableDrag = () => {
  tableDragging.value = null
}

const onTableGripPointerDown = (event: PointerEvent, tableId: number) => {
  const position = getTablePosition(tableId)
  tableDragging.value = {
    tableId,
    offsetX: event.clientX - position.x,
    offsetY: event.clientY - position.y
  }
  selectTable(tableId)
}

const saveSelectedColumn = async () => {
  const parent = selectedColumnParent.value
  if (!parent) return
  await saveTable(parent)
}

const createTable = async () => {
  if (!authStore.token || !selectedWorkspace.value || !newTableName.value.trim()) return

  await tableSchemaUseCase.createTable(authStore.token, selectedWorkspace.value.id, {
    name: newTableName.value.trim(),
    description: newTableDescription.value.trim() || null,
    columns: []
  })
  newTableName.value = ''
  newTableDescription.value = ''
  await loadSchema()
}

const saveTable = async (table: TableStructure) => {
  if (!authStore.token || !selectedWorkspace.value) return
  await tableSchemaUseCase.updateTable(authStore.token, selectedWorkspace.value.id, table.id, {
    name: table.name,
    description: table.description,
    columns: table.columns
  })
  await loadSchema()
}

const slugify = (value: string): string =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9а-я]+/gi, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 60)

const buildColumnSettings = (): Record<string, unknown> => {
  if (newColumnType.value === 'enum') {
    return {
      options: newColumnEnumOptions.value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
    }
  }

  if (newColumnType.value === 'list') {
    const settings: Record<string, unknown> = {
      itemType: newColumnListItemType.value
    }
    if (newColumnListItemType.value === 'enum') {
      settings.options = newColumnEnumOptions.value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
    }
    return settings
  }

  if (newColumnType.value === 'geoPoint') {
    return { srid: Number(newColumnGeoSrid.value) || 4326 }
  }

  if (newColumnType.value === 'geoPolygon') {
    return {
      srid: Number(newColumnGeoSrid.value) || 4326,
      allowHoles: newColumnGeoAllowHoles.value
    }
  }

  return {}
}

const addColumnToActiveTable = async () => {
  if (!activeTable.value || !newColumnName.value.trim()) return

  const baseKey = slugify(newColumnName.value)
  const fallbackKey = baseKey || `column_${Date.now()}`
  let key = fallbackKey
  let index = 2
  while (activeTable.value.columns.some((col) => col.key === key)) {
    key = `${fallbackKey}_${index}`
    index += 1
  }

  activeTable.value.columns.push({
    key,
    name: newColumnName.value.trim(),
    type: newColumnType.value,
    required: newColumnRequired.value,
    settings: buildColumnSettings()
  })

  newColumnName.value = ''
  newColumnType.value = 'text'
  newColumnRequired.value = false
  newColumnEnumOptions.value = ''
  newColumnListItemType.value = 'text'
  newColumnGeoSrid.value = 4326
  newColumnGeoAllowHoles.value = false

  await saveTable(activeTable.value)
}

const removeColumnFromActiveTable = async (columnKey: string) => {
  if (!activeTable.value) return
  activeTable.value.columns = activeTable.value.columns.filter((column) => column.key !== columnKey)
  if (selectedColumnRef.value?.columnKey === columnKey && selectedColumnRef.value.tableId === activeTable.value.id) {
    selectedColumnRef.value = null
  }
  await saveTable(activeTable.value)
}

const startDraggingColumn = (sourceTableId: number, columnKey: string) => {
  dragState.value = { sourceTableId, columnKey }
}

const onDropColumnToTable = async (targetTableId: number) => {
  if (!authStore.token || !selectedWorkspace.value || dragState.value === null) return

  const sourceTableId = dragState.value.sourceTableId
  const columnKey = dragState.value.columnKey
  dragState.value = null

  if (sourceTableId === targetTableId) return

  await tableSchemaUseCase.moveColumn(authStore.token, selectedWorkspace.value.id, sourceTableId, targetTableId, columnKey)
  await loadSchema()
}

const createRelation = async () => {
  if (!authStore.token || !selectedWorkspace.value) return
  const sourceTableId = Number(relationSourceTableId.value)
  const targetTableId = Number(relationTargetTableId.value)

  if (!relationName.value.trim() || !sourceTableId || !targetTableId) return
  if (!relationSourceColumn.value.trim() || !relationTargetColumn.value.trim()) return

  await tableSchemaUseCase.createRelation(authStore.token, selectedWorkspace.value.id, {
    name: relationName.value.trim(),
    source_table_id: sourceTableId,
    target_table_id: targetTableId,
    relation_type: relationType.value,
    mapping: { [relationSourceColumn.value.trim()]: relationTargetColumn.value.trim() },
    properties: {}
  })

  relationName.value = ''
  relationSourceTableId.value = ''
  relationTargetTableId.value = ''
  relationSourceColumn.value = ''
  relationTargetColumn.value = ''
  await loadSchema()
}

const deleteRelation = async (relationId: number) => {
  if (!authStore.token || !selectedWorkspace.value) return
  await tableSchemaUseCase.deleteRelation(authStore.token, selectedWorkspace.value.id, relationId)
  await loadSchema()
}

const formatDate = (value: string): string => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

const logout = () => {
  authStore.logout()
  router.push({ name: 'login' })
}

onMounted(async () => {
  window.addEventListener('pointermove', onCanvasPointerMove)
  window.addEventListener('pointerup', stopTableDrag)
  await loadWorkspaces()
  await loadSchema()
})

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onCanvasPointerMove)
  window.removeEventListener('pointerup', stopTableDrag)
})
</script>

<template>
  <main class="dashboard">
    <aside class="sidebar">
      <header class="sidebar-header">
        <h1>Workspace</h1>
        <p>{{ authStore.me?.email }}</p>
      </header>

      <section class="create-widget">
        <h2>Новый workspace</h2>
        <div class="fields">
          <input v-model="workspaceName" type="text" placeholder="Название" maxlength="255" />
          <textarea v-model="workspaceDescription" rows="3" placeholder="Описание (опционально)" maxlength="2000" />
          <button @click="createWorkspace">Создать</button>
        </div>
      </section>

      <section class="workspace-nav">
        <div class="nav-title">
          <h2>Список</h2>
          <span>{{ workspaces.length }}</span>
        </div>
        <p v-if="loading" class="muted">Загрузка...</p>
        <p v-else-if="workspaces.length === 0" class="muted">Пока нет workspace</p>

        <ul v-else>
          <li v-for="workspace in workspaces" :key="workspace.id">
            <button class="workspace-link" :class="{ active: selectedWorkspaceId === workspace.id }" @click="selectWorkspace(workspace.id)">
              <strong>{{ workspace.name }}</strong>
              <span>{{ workspace.description || 'Без описания' }}</span>
            </button>
          </li>
        </ul>
      </section>

      <button class="ghost" @click="logout">Выйти</button>
    </aside>

    <section class="content">
      <article v-if="selectedWorkspace" class="workspace-content">
        <header>
          <h2>{{ selectedWorkspace.name }}</h2>
          <p>{{ selectedWorkspace.description || 'Описание пока не добавлено' }}</p>
        </header>

        <div class="workspace-tabs">
          <button class="tab" :class="{ active: workspaceTab === 'details' }" @click="workspaceTab = 'details'">Детали</button>
          <button class="tab" :class="{ active: workspaceTab === 'tables' }" @click="workspaceTab = 'tables'">Таблицы</button>
        </div>

        <div class="actions-row" v-if="workspaceTab === 'details'">
          <button class="danger" :disabled="deleting" @click="deleteWorkspace">
            {{ deleting ? 'Удаляем...' : 'Удалить workspace' }}
          </button>
        </div>

        <section v-if="workspaceTab === 'tables'" class="designer">
          <div class="designer-header">
            <h3>Low-code структуры таблиц</h3>
            <p>SQL Canvas: перемещайте таблицы по полю и переносите колонки drag-and-drop между таблицами.</p>
          </div>

          <div class="create-table">
            <input v-model="newTableName" type="text" placeholder="Новая таблица: название" maxlength="255" />
            <input v-model="newTableDescription" type="text" placeholder="Описание таблицы" maxlength="255" />
            <button @click="createTable">Добавить таблицу</button>
          </div>

          <p v-if="schemaLoading" class="muted">Загрузка структуры...</p>
          <p v-if="schemaError" class="error">{{ schemaError }}</p>

          <div class="schema-layout">
            <div class="schema-canvas-wrap">
              <div class="schema-canvas">
                <article
                  v-for="table in tableStructures"
                  :key="table.id"
                  class="table-card"
                  :class="{ active: activeTableId === table.id }"
                  :style="{ left: `${getTablePosition(table.id).x}px`, top: `${getTablePosition(table.id).y}px` }"
                  @dragover.prevent
                  @drop="onDropColumnToTable(table.id)"
                >
                  <div class="table-head" @click="selectTable(table.id)">
                    <button class="table-grip" @pointerdown.prevent="onTableGripPointerDown($event, table.id)">::: </button>
                    <strong>{{ table.name }}</strong>
                  </div>
                  <p class="table-sub">{{ table.description || 'Без описания' }}</p>

                  <ul class="column-list">
                    <li
                      v-for="column in table.columns"
                      :key="column.key"
                      class="column-item"
                      draggable="true"
                      @dragstart="startDraggingColumn(table.id, column.key)"
                      @dragend="dragState = null"
                      @click="selectColumn(table.id, column.key)"
                    >
                      <div>
                        <strong>{{ column.name }}</strong>
                        <span>{{ column.key }}</span>
                      </div>
                      <em>{{ column.type }}</em>
                    </li>
                  </ul>
                </article>
              </div>
            </div>

            <aside class="object-sidebar">
              <section v-if="activeTable" class="object-card">
                <h4>Выделенная таблица</h4>
                <input v-model="activeTable.name" placeholder="Имя таблицы" />
                <input v-model="activeTable.description" placeholder="Описание таблицы" />
                <button class="small" @click="saveTable(activeTable)">Сохранить таблицу</button>
              </section>

              <section class="object-card" v-if="activeTable">
                <h4>Добавить колонку</h4>
                <div class="new-column-form">
                  <input v-model="newColumnName" placeholder="Название колонки" />
                  <select v-model="newColumnType">
                    <option value="text">text</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="date">date</option>
                    <option value="datetime">datetime</option>
                    <option value="enum">enum</option>
                    <option value="list">list</option>
                    <option value="geoPoint">geoPoint</option>
                    <option value="geoPolygon">geoPolygon</option>
                  </select>
                  <label class="checkbox-inline"><input v-model="newColumnRequired" type="checkbox" />required</label>
                </div>

                <div v-if="newColumnType === 'enum'" class="type-settings">
                  <input v-model="newColumnEnumOptions" placeholder="Enum options через запятую" />
                </div>

                <div v-if="newColumnType === 'list'" class="type-settings">
                  <select v-model="newColumnListItemType">
                    <option value="text">text</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="enum">enum</option>
                  </select>
                  <input v-if="newColumnListItemType === 'enum'" v-model="newColumnEnumOptions" placeholder="List enum options" />
                </div>

                <div v-if="newColumnType === 'geoPoint' || newColumnType === 'geoPolygon'" class="type-settings">
                  <input v-model.number="newColumnGeoSrid" type="number" min="1" placeholder="SRID" />
                  <label v-if="newColumnType === 'geoPolygon'" class="checkbox-inline">
                    <input v-model="newColumnGeoAllowHoles" type="checkbox" />allow holes
                  </label>
                </div>

                <button class="small" @click="addColumnToActiveTable">Добавить в таблицу</button>
              </section>

              <section v-if="selectedColumn && selectedColumnParent" class="object-card">
                <h4>Выделенная колонка</h4>
                <p class="muted">Таблица: {{ selectedColumnParent.name }}</p>
                <input v-model="selectedColumn.name" placeholder="Название" />
                <input v-model="selectedColumn.key" placeholder="Ключ" />
                <select v-model="selectedColumn.type">
                  <option value="text">text</option>
                  <option value="number">number</option>
                  <option value="boolean">boolean</option>
                  <option value="date">date</option>
                  <option value="datetime">datetime</option>
                  <option value="enum">enum</option>
                  <option value="list">list</option>
                  <option value="geoPoint">geoPoint</option>
                  <option value="geoPolygon">geoPolygon</option>
                </select>
                <label class="checkbox-inline"><input v-model="selectedColumn.required" type="checkbox" />required</label>
                <div class="row-actions">
                  <button class="small" @click="saveSelectedColumn">Сохранить</button>
                  <button class="small danger" @click="removeColumnFromActiveTable(selectedColumn.key)">Удалить</button>
                </div>
              </section>

              <section class="object-card relations">
                <h4>Связи таблиц</h4>
                <div class="relation-form">
                  <input v-model="relationName" placeholder="Название связи" />
                  <select v-model="relationSourceTableId">
                    <option value="">Источник</option>
                    <option v-for="table in allTableOptions" :key="`s-${table.id}`" :value="String(table.id)">{{ table.name }}</option>
                  </select>
                  <select v-model="relationSourceColumn">
                    <option value="">Колонка источника</option>
                    <option v-for="column in relationSourceColumns" :key="`sc-${column.key}`" :value="column.key">{{ column.name }}</option>
                  </select>
                  <select v-model="relationTargetTableId">
                    <option value="">Цель</option>
                    <option v-for="table in allTableOptions" :key="`t-${table.id}`" :value="String(table.id)">{{ table.name }}</option>
                  </select>
                  <select v-model="relationTargetColumn">
                    <option value="">Колонка цели</option>
                    <option v-for="column in relationTargetColumns" :key="`tc-${column.key}`" :value="column.key">{{ column.name }}</option>
                  </select>
                  <select v-model="relationType">
                    <option value="one_to_one">one_to_one</option>
                    <option value="one_to_many">one_to_many</option>
                    <option value="many_to_many">many_to_many</option>
                  </select>
                  <button @click="createRelation">Добавить связь</button>
                </div>

                <ul class="relation-list">
                  <li v-for="relation in relations" :key="relation.id">
                    <div>
                      <strong>{{ relation.name }}</strong>
                      <span>{{ relation.relation_type }}: {{ relation.source_table_id }} -> {{ relation.target_table_id }}</span>
                    </div>
                    <button class="small danger" @click="deleteRelation(relation.id)">Удалить</button>
                  </li>
                </ul>
              </section>
            </aside>
          </div>
        </section>

        <section class="info-grid" v-if="workspaceTab === 'details'">
          <section class="info-card">
            <h3>Детали workspace</h3>
            <dl>
              <div>
                <dt>ID</dt>
                <dd>#{{ selectedWorkspace.id }}</dd>
              </div>
              <div>
                <dt>Владелец</dt>
                <dd>{{ authStore.me?.email }}</dd>
              </div>
              <div>
                <dt>Создан</dt>
                <dd>{{ formatDate(selectedWorkspace.created_at) }}</dd>
              </div>
            </dl>
          </section>
        </section>
      </article>

      <article v-else class="empty-content">
        <h2>Выберите workspace</h2>
        <p>Создайте новое пространство в боковой панели или выберите существующее из списка.</p>
      </article>
    </section>
  </main>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  padding: 18px;
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
}

.sidebar {
  background: var(--bg-panel);
  border-radius: 18px;
  border: 1px solid var(--line);
  padding: 16px;
  display: grid;
  gap: 14px;
  align-content: start;
}

.sidebar-header h1 {
  margin: 0;
  letter-spacing: 0.02em;
}

.sidebar-header p {
  margin: 6px 0 0;
  color: var(--text-muted);
}

h2,
h3,
h4 {
  margin: 0;
}

.create-widget,
.workspace-nav {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--bg-soft);
  padding: 12px;
}

.fields {
  display: grid;
  gap: 10px;
  margin-top: 10px;
}

input,
textarea,
select {
  border: 1px solid var(--line);
  background: #edf4f5;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--text-main);
  font: inherit;
}

textarea {
  resize: vertical;
}

button {
  border: none;
  background: var(--accent);
  color: #e8fbff;
  border-radius: 10px;
  padding: 10px 16px;
  font-weight: 700;
}

button.small {
  padding: 7px 10px;
  font-size: 0.84rem;
}

button.ghost {
  background: #d9e3e5;
  color: #1f353b;
}

button.danger {
  background: var(--danger);
  color: #fff;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.workspace-nav ul {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.workspace-link {
  width: 100%;
  text-align: left;
  background: #dbe8ea;
  color: var(--text-main);
  border: 1px solid transparent;
  padding: 10px;
  border-radius: 10px;
  display: grid;
  gap: 4px;
}

.workspace-link.active {
  background: linear-gradient(135deg, #3c6f7f, #2b8f86);
  color: #f0fffd;
  border-color: #70ada5;
}

.workspace-link span,
.muted {
  color: var(--text-muted);
}

.workspace-link.active span {
  color: #c6f7f0;
}

.nav-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-title span {
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 0.82rem;
  padding: 2px 9px;
  color: var(--text-muted);
}

.content {
  border-radius: 18px;
  border: 1px solid var(--line);
  background: var(--bg-panel);
  padding: 20px;
}

.workspace-content header p {
  color: var(--text-muted);
  margin: 8px 0 0;
}

.workspace-tabs {
  margin-top: 14px;
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 4px;
  background: #e9f1f3;
}

.workspace-tabs .tab {
  background: transparent;
  color: var(--text-main);
  padding: 8px 14px;
  border-radius: 8px;
}

.workspace-tabs .tab.active {
  background: linear-gradient(135deg, #3d6f7d, #2b8e84);
  color: #effffd;
}

.actions-row {
  margin: 12px 0;
}

.designer {
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  background: var(--bg-soft);
  display: grid;
  gap: 14px;
}

.designer-header p {
  margin: 6px 0 0;
  color: var(--text-muted);
}

.create-table {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
}

.schema-layout {
  display: grid;
  grid-template-columns: minmax(620px, 1fr) 360px;
  gap: 12px;
}

.schema-canvas-wrap {
  border: 1px dashed var(--line);
  border-radius: 12px;
  background: linear-gradient(180deg, #ebf2f3 0%, #e4edf0 100%);
  overflow: auto;
}

.schema-canvas {
  position: relative;
  min-height: 640px;
  min-width: 940px;
}

.table-card {
  position: absolute;
  width: 280px;
  border: 1px solid #8ca8b1;
  border-radius: 12px;
  padding: 10px;
  background: #f3f8f9;
  display: grid;
  gap: 8px;
  box-shadow: 0 6px 14px rgba(38, 74, 85, 0.12);
}

.table-card.active {
  border-color: #2b8f86;
  box-shadow: inset 0 0 0 1px #2b8f86;
}

.table-head {
  display: flex;
  gap: 8px;
  align-items: center;
  cursor: pointer;
}

.table-grip {
  background: #dce8ea;
  color: #45676f;
  border-radius: 6px;
  padding: 4px 6px;
  font-size: 0.74rem;
}

.table-sub {
  margin: 0;
  font-size: 0.83rem;
  color: var(--text-muted);
}

.table-name-input,
.table-description-input {
  width: 100%;
}

.column-list {
  display: grid;
  gap: 6px;
}

.column-item {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 8px;
  background: #f4f9fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: grab;
}

.column-item div {
  display: grid;
  gap: 2px;
}

.column-item span {
  color: var(--text-muted);
  font-size: 0.82rem;
}

.column-item:hover {
  border-color: #7ea4ad;
}

.object-sidebar {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #eef5f7;
  padding: 10px;
  display: grid;
  gap: 10px;
  align-content: start;
  max-height: 640px;
  overflow: auto;
}

.object-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
  background: #f7fbfc;
  display: grid;
  gap: 10px;
}

.new-column-form,
.type-settings,
.relation-form {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  align-items: center;
}

.checkbox-inline {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  color: var(--text-muted);
}

.add-column {
  width: fit-content;
}

.row-actions {
  display: flex;
  gap: 8px;
}

.relations {
  background: #edf5f7;
  display: grid;
  gap: 10px;
}

.relation-list {
  display: grid;
  gap: 8px;
}

.relation-list li {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 9px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  background: #f7fbfb;
}

.relation-list span {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.info-grid {
  margin-top: 14px;
}

.info-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  background: var(--bg-soft);
}

dl {
  margin: 0;
  display: grid;
  gap: 10px;
}

dt {
  font-size: 0.85rem;
  color: var(--text-muted);
}

dd {
  margin: 0;
  font-weight: 600;
}

.empty-content {
  min-height: 320px;
  display: grid;
  place-content: center;
  text-align: center;
  gap: 6px;
}

.error {
  color: var(--danger);
}

@media (max-width: 1100px) {
  .create-table {
    grid-template-columns: 1fr;
  }

  .schema-layout {
    grid-template-columns: 1fr;
  }

  .schema-canvas {
    min-width: 100%;
  }
}

@media (max-width: 760px) {
  .dashboard {
    grid-template-columns: 1fr;
  }

  .content {
    padding: 16px;
  }
}
</style>
