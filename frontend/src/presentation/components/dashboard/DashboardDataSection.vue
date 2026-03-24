<script setup lang="ts">
import { computed } from 'vue'
import type { ColumnType } from '../../../domain/entities/TableSchema'
import UiStatusText from '../common/UiStatusText.vue'

interface TableColumn {
  key: string
  name: string
  type: ColumnType
}

interface TableOption {
  id: number
  name: string
}

interface DataTable {
  id: number
  name: string
  columns: TableColumn[]
}

interface DataRecord {
  id: number
  data: Record<string, unknown>
  submitted_at?: string | null
  created_at?: string | null
  submitter_email?: string | null
}

const props = defineProps<{
  selectedDataTable: DataTable | null
  tableDataRecords: DataRecord[]
  dataPagination: { skip: number; limit: number; total: number }
  dataLoading: boolean
  dataError: string
  totalPages: number
  currentPage: number
  allTableOptions: TableOption[]
  selectedDataTableId: number | null
  formatDataValue: (value: unknown, columnType: ColumnType) => string
  formatDate: (value: string) => string
}>()

const emit = defineEmits<{
  (event: 'update:selectedDataTableId', value: number | null): void
  (event: 'update:dataLimit', value: number): void
  (event: 'data-table-change'): void
  (event: 'data-limit-change'): void
  (event: 'delete-record', recordId: number): void
  (event: 'go-to-page', page: number): void
}>()

const selectedDataTableIdModel = computed({
  get: () => props.selectedDataTableId,
  set: (value: number | null) => emit('update:selectedDataTableId', value)
})

const dataLimitModel = computed({
  get: () => props.dataPagination.limit,
  set: (value: number) => emit('update:dataLimit', value)
})
</script>

<template>
  <section class="data-section">
    <div class="data-header">
      <h3>{{ selectedDataTable ? selectedDataTable.name : 'Таблица' }}: Данные</h3>
      <p v-if="selectedDataTable">Показано {{ tableDataRecords.length }} из {{ dataPagination.total }} записей</p>
    </div>

    <div class="field-settings-row">
      <select v-model.number="selectedDataTableIdModel" @change="emit('data-table-change')">
        <option :value="null">Выберите таблицу</option>
        <option v-for="table in allTableOptions" :key="`data-t-${table.id}`" :value="table.id">
          {{ table.name }}
        </option>
      </select>
      <select v-model.number="dataLimitModel" @change="emit('data-limit-change')">
        <option :value="10">10 записей</option>
        <option :value="25">25 записей</option>
        <option :value="50">50 записей</option>
        <option :value="100">100 записей</option>
      </select>
    </div>

    <UiStatusText v-if="dataLoading" as="div">Загрузка данных...</UiStatusText>
    <UiStatusText v-if="dataError" as="div" variant="error">{{ dataError }}</UiStatusText>

    <div v-if="tableDataRecords.length > 0 && selectedDataTable" class="data-table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th>
            <th v-for="column in selectedDataTable.columns" :key="column.key">{{ column.name }}</th>
            <th>Отправлено</th>
            <th>Email</th>
            <th>Действие</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(record, index) in tableDataRecords" :key="record.id">
            <td>{{ dataPagination.skip + index + 1 }}</td>
            <td v-for="column in selectedDataTable.columns" :key="column.key">
              <span :title="JSON.stringify(record.data[column.key])">
                {{ formatDataValue(record.data[column.key], column.type) }}
              </span>
            </td>
            <td>{{ formatDate((record.submitted_at || record.created_at || '') as string) }}</td>
            <td>{{ record.submitter_email || '—' }}</td>
            <td>
              <button class="small danger" @click="emit('delete-record', record.id)">Удалить</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <UiStatusText v-else-if="!dataLoading && selectedDataTable" class="empty-table-state" as="div">
      Нет записей в этой таблице
    </UiStatusText>

    <div v-if="totalPages > 1" class="pagination">
      <button @click="emit('go-to-page', currentPage - 1)" :disabled="currentPage === 1">← Назад</button>
      <span>Страница {{ currentPage }} из {{ totalPages }}</span>
      <button @click="emit('go-to-page', currentPage + 1)" :disabled="currentPage === totalPages">Вперёд →</button>
    </div>
  </section>
</template>

<style scoped src="../../styles/dashboard/dashboard-data-section.css"></style>
