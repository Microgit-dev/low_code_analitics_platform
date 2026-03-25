<script setup lang="ts">
import { ref, computed } from 'vue'
import SideBar        from './components/SideBar.vue'
import TopBar         from './components/TopBar.vue'
import WorkspaceModal from './components/WorkspaceModal.vue'
import WelcomeScreen  from './components/WelcomeScreen.vue'
import TableView      from './components/TableView.vue'
import FormsView      from './components/FormsView.vue'
import DataView       from './components/DataView.vue'
import ReportsView    from './components/ReportsView.vue'
import ReportModal    from './components/ReportModal.vue'
import type { Workspace, Table, ColumnType, Form, FormRecord, Report, OutputType } from './types'

/* ── Workspaces ── */
const workspaces      = ref<Workspace[]>([])
const activeWorkspace = ref<Workspace | null>(null)
const showModal       = ref(false)
const activeNavItem   = ref('tables')

const nextWorkspaceName = computed(() => `WorkSpace ${workspaces.value.length + 1}`)

function handleCreateWorkspace(name: string, description: string) {
  const ws: Workspace = { id: Date.now(), name, description }
  workspaces.value.push(ws)
  if (!activeWorkspace.value) activeWorkspace.value = ws
  showModal.value = false
}

function handleDeleteWorkspace(id: number) {
  const idx = workspaces.value.findIndex(w => w.id === id)
  if (idx === -1) return
  workspaces.value.splice(idx, 1)
  delete workspaceTables.value[id]
  delete workspaceForms.value[id]
  delete workspaceRecords.value[id]
  if (activeWorkspace.value?.id === id) {
    activeWorkspace.value = workspaces.value[idx] ?? workspaces.value[idx - 1] ?? null
  }
}

/* ── Tables (per workspace) ── */
const workspaceTables = ref<Record<number, Table[]>>({})
const selectedTableId = ref<number | null>(null)

const activeTables = computed<Table[]>(() =>
  activeWorkspace.value ? (workspaceTables.value[activeWorkspace.value.id] ?? []) : []
)

function tablesFor(wsId: number): Table[] {
  if (!workspaceTables.value[wsId]) workspaceTables.value[wsId] = []
  return workspaceTables.value[wsId]
}

function handleCreateTable(name: string, description: string) {
  if (!activeWorkspace.value) return
  const tables = tablesFor(activeWorkspace.value.id)
  const table: Table = {
    id: Date.now(),
    name: name || `Таблица ${tables.length + 1}`,
    description,
    columns: [],
    x: 20 + (tables.length % 3) * 300,
    y: 20 + Math.floor(tables.length / 3) * 260,
  }
  tables.push(table)
  selectedTableId.value = table.id
}

function handleUpdateTable(id: number, name: string, description: string) {
  if (!activeWorkspace.value) return
  const t = tablesFor(activeWorkspace.value.id).find(t => t.id === id)
  if (t) { t.name = name; t.description = description }
}

function handleDeleteTable(id: number) {
  if (!activeWorkspace.value) return
  const tables = tablesFor(activeWorkspace.value.id)
  const idx = tables.findIndex(t => t.id === id)
  if (idx !== -1) tables.splice(idx, 1)
  if (selectedTableId.value === id) selectedTableId.value = null
}

function handleAddColumn(tableId: number, name: string, type: ColumnType, required: boolean) {
  if (!activeWorkspace.value) return
  const t = tablesFor(activeWorkspace.value.id).find(t => t.id === tableId)
  if (t) t.columns.push({ id: Date.now(), name, type, required })
}

function handleMoveTable(id: number, x: number, y: number) {
  if (!activeWorkspace.value) return
  const t = tablesFor(activeWorkspace.value.id).find(t => t.id === id)
  if (t) { t.x = x; t.y = y }
}

function handleTopBarCreateTable() {
  if (!activeWorkspace.value) return
  handleCreateTable(`Таблица ${activeTables.value.length + 1}`, '')
}

/* ── Forms (per workspace) ── */
const workspaceForms = ref<Record<number, Form[]>>({})

const activeForms = computed<Form[]>(() =>
  activeWorkspace.value ? (workspaceForms.value[activeWorkspace.value.id] ?? []) : []
)

function formsFor(wsId: number): Form[] {
  if (!workspaceForms.value[wsId]) workspaceForms.value[wsId] = []
  return workspaceForms.value[wsId]
}

function handleCreateForm() {
  if (!activeWorkspace.value) return
  const forms = formsFor(activeWorkspace.value.id)
  forms.push({
    id: Date.now(),
    name: `Форма ${forms.length + 1}`,
    description: '',
    tableIds: [],
    isPublic: false,
    collectEmail: false,
  })
}

function handleUpdateForm(updated: Form) {
  if (!activeWorkspace.value) return
  const forms = formsFor(activeWorkspace.value.id)
  const idx = forms.findIndex(f => f.id === updated.id)
  if (idx !== -1) forms[idx] = updated
}

function handleDeleteForm(id: number) {
  if (!activeWorkspace.value) return
  const forms = formsFor(activeWorkspace.value.id)
  const idx = forms.findIndex(f => f.id === id)
  if (idx !== -1) forms.splice(idx, 1)
}

/* ── Form Records (per workspace) ── */
const workspaceRecords = ref<Record<number, FormRecord[]>>({})

const activeRecords = computed<FormRecord[]>(() =>
  activeWorkspace.value ? (workspaceRecords.value[activeWorkspace.value.id] ?? []) : []
)

function handleSubmitRecord(formId: number, values: Record<string, unknown>) {
  if (!activeWorkspace.value) return
  const wsId = activeWorkspace.value.id
  if (!workspaceRecords.value[wsId]) workspaceRecords.value[wsId] = []
  workspaceRecords.value[wsId].push({
    id: Date.now(),
    formId,
    values,
    submittedAt: new Date().toISOString(),
  })
}

/* ── Reports (per workspace) ── */
const workspaceReports = ref<Record<number, Report[]>>({})
const showReportModal  = ref(false)

const activeReports = computed<Report[]>(() =>
  activeWorkspace.value ? (workspaceReports.value[activeWorkspace.value.id] ?? []) : []
)

function reportsFor(wsId: number): Report[] {
  if (!workspaceReports.value[wsId]) workspaceReports.value[wsId] = []
  return workspaceReports.value[wsId]
}

function handleCreateReport(
  name: string,
  description: string,
  formIds: number[],
  outputType: OutputType,
) {
  if (!activeWorkspace.value) return
  reportsFor(activeWorkspace.value.id).push({
    id: Date.now(),
    name,
    description,
    formIds,
    outputType,
  })
  showReportModal.value = false
}

function handleDeleteReport(id: number) {
  if (!activeWorkspace.value) return
  const reports = reportsFor(activeWorkspace.value.id)
  const idx = reports.findIndex(r => r.id === id)
  if (idx !== -1) reports.splice(idx, 1)
}

const nextReportName = computed(() => `Отчёт ${activeReports.value.length + 1}`)

/* ── View logic ── */
const showTableView = computed(
  () => workspaces.value.length > 0 && activeNavItem.value === 'tables'
)
const showFormsView = computed(
  () => workspaces.value.length > 0 && activeNavItem.value === 'forms'
)
const showDataView = computed(
  () => workspaces.value.length > 0 && activeNavItem.value === 'data'
)
const showReportsView = computed(
  () => workspaces.value.length > 0 && activeNavItem.value === 'reports'
)
</script>

<template>
  <div class="app">
    <SideBar :active-item="activeNavItem" @nav-click="activeNavItem = $event" />

    <div class="right">
      <TopBar
        :workspaces="workspaces"
        :active-workspace="activeWorkspace"
        :active-nav-item="activeNavItem"
        @select-workspace="activeWorkspace = $event; selectedTableId = null"
        @open-modal="showModal = true"
        @delete-workspace="handleDeleteWorkspace"
        @create-table="handleTopBarCreateTable"
        @import-table="() => {}"
        @create-form="handleCreateForm"
        @import-data="() => {}"
        @create-report="showReportModal = true"
      />

      <main class="content">
        <WelcomeScreen
          v-if="workspaces.length === 0"
          @open-modal="showModal = true"
        />

        <TableView
          v-else-if="showTableView"
          :tables="activeTables"
          :selected-table-id="selectedTableId"
          @create-table="handleCreateTable"
          @update-table="handleUpdateTable"
          @delete-table="handleDeleteTable"
          @add-column="handleAddColumn"
          @select-table="selectedTableId = $event"
          @move-table="handleMoveTable"
        />

        <FormsView
          v-else-if="showFormsView"
          :forms="activeForms"
          :tables="activeTables"
          @update-form="handleUpdateForm"
          @delete-form="handleDeleteForm"
          @submit-record="handleSubmitRecord"
        />

        <DataView
          v-else-if="showDataView"
          :forms="activeForms"
          :tables="activeTables"
          :records="activeRecords"
        />

        <ReportsView
          v-else-if="showReportsView"
          :reports="activeReports"
          :forms="activeForms"
          @delete-report="handleDeleteReport"
        />
      </main>
    </div>

    <Teleport to="body">
      <ReportModal
        v-if="showReportModal"
        :forms="activeForms"
        :default-name="nextReportName"
        @create="handleCreateReport"
        @close="showReportModal = false"
      />
      <WorkspaceModal
        v-if="showModal"
        :default-name="nextWorkspaceName"
        @create="handleCreateWorkspace"
        @close="showModal = false"
      />
    </Teleport>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: row;
  height: 100vh;
  background: #eef4f6;
}

.right {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  min-width: 0;
}

.content {
  flex: 1;
  overflow: hidden;
  display: flex;
}
</style>
