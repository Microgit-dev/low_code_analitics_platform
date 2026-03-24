# Dashboard Structure Analysis

Полный анализ структуры проекта, связанный с дашбордами и отчётами.

## 📋 Содержание

1. [Обзор архитектуры](#обзор-архитектуры)
2. [Frontend компоненты](#frontend-компоненты)
3. [Backend архитектура](#backend-архитектура)
4. [Типы графиков и виджетов](#типы-графиков-и-виджетов)
5. [Модели данных](#модели-данных)
6. [Use Cases](#use-cases)
7. [API endpoints](#api-endpoints)
8. [Полный список файлов](#полный-список-файлов)

---

## 🏗️ Обзор архитектуры

Проект реализует **чистую архитектуру** с разделением:

```
┌─────────────────────────────────────────┐
│         PRESENTATION LAYER              │
│  (Vue.js Views & Components)            │
├─────────────────────────────────────────┤
│         APPLICATION LAYER               │
│  (Use Cases & Business Logic)           │
├─────────────────────────────────────────┤
│           DOMAIN LAYER                  │
│  (Entities & Repository Interfaces)     │
├─────────────────────────────────────────┤
│        INFRASTRUCTURE LAYER             │
│  (SQLAlchemy, Database Models)          │
└─────────────────────────────────────────┘
```

---

## 🎨 Frontend компоненты

### Views (Основные экраны)

#### 1. **DashboardView.vue**
Главный интерфейс управления workspace'ами и отчётами.

```
ФУНКЦИОНАЛЬНОСТЬ:
- Управление workspace'ами (создание, выбор)
- Управление tables (CRUD операции)
- Управление forms (создание форм)
- Data viewer (просмотр данных таблиц)
- Import (импорт данных из CSV/XLSX)
- Reports (управление отчётами и дашбордами)
```

**Основные табы:**
- `tables` - Управление структурой таблиц
- `forms` - Создание форм для заполнения
- `data` - Просмотр данных таблиц
- `import` - Импорт данных
- `reports` - Управление отчётами

---

#### 2. **ReportDetailView.vue**
Редактор дашбордов (конструктор виджетов).

```typescript
ТИПЫ ВИДЖЕТОВ:
- text      // Статический текст
- metric    // Агрегированное значение
- chart     // График (bar chart)
- table     // Таблица с данными
- map       // Карта с координатами

ФУНКЦИИ АГРЕГАЦИИ:
- count  // Количество записей
- sum    // Сумма
- avg    // Среднее
- min    // Минимум
- max    // Максимум
```

**Компоненты:**
- Палитра виджетов (5 типов)
- Редактор свойств виджета
- Живой preview виджетов
- Выбор таблицы источника
- Настройка полей агрегации

---

#### 3. **PublicDashboardView.vue**
Публичный просмотр дашборда (read-only для поделившихся).

```typescript
ОТОБРАЖАЕМЫЕ ЭЛЕМЕНТЫ:
- Metrics      // Агрегированные значения
- Charts       // Bar charts (ECharts)
- Widgets      // Все типы виджетов
- Recent Data  // Таблица последних записей
- Map          // Карта с точками

ФУНКЦИИ:
- Фильтрация по колонкам
- Поиск по всем полям
- Сортировка
- Pagination для таблиц
```

**Технологии:**
- Vue 3 Composition API
- ECharts для графиков
- MapLibre GL для карт
- Полная интерактивность

---

#### 4. **TableReportView.vue**
Просмотр и экспорт табличных отчётов.

```
ФУНКЦИИ:
- Просмотр данных из таблиц
- Multi-dataset поддержка
- Фильтрация и поиск
- Сортировка
- Экспорт в XLSX/CSV
```

---

### Components (dashboard/)

#### **DashboardTileCard.vue**
Обобщённый контейнер для карточек.

```vue
<template>
  <article class="dashboard-tile-card" :class="{ active }">
    <header>
      <div class="title"><slot name="title" /></div>
      <div class="badge"><slot name="badge" /></div>
    </header>
    <div class="body"><slot /></div>
    <div class="actions"><slot name="actions" /></div>
  </article>
</template>
```

---

#### **DashboardDataSection.vue**
Компонент для просмотра данных таблиц.

```
ФУНКЦИОНАЛЬНОСТЬ:
- Выбор таблицы
- Выбор количества строк (10, 25, 50, 100)
- Таблица с данными
- Pagination
- Удаление записей
- Форматирование значений по типу
```

---

#### **DashboardSidebar.vue**
Боковая панель с workspace'ами.

```
ФУНКЦИИ:
- Создание нового workspace
- Список workspace'ов
- Быстрый переключатель
- Email пользователя
- Logout
```

---

#### **DashboardImportSection.vue**
Импорт данных (CSV/XLSX).

```
ФУНКЦИИ:
- Загрузка файла
- Сканирование структуры
- Выбор диапазонов (header, data rows)
- Выбор разделителей списков
- Маппинг колонок
- Preview данных
```

---

#### **DashboardTemplateModal.vue**
Расчёты по шаблонам (.odt файлы).

```
ПОДДЕРЖИВАЕМЫЕ ФУНКЦИИ:
- {{ count(key) }}      // Количество
- {{ sum(key) }}        // Сумма
- {{ avg(key) }}        // Среднее
- {{ min(key) }}        // Минимум
- {{ max(key) }}        // Максимум
```

---

### Entities (Domain Models)

#### **Report.ts**

```typescript
// ТИПЫ
export type ReportType = "table_export" | "dashboard"
export type DashboardWidgetType = "text" | "metric" | "table" | "chart" | "map"
export type MetricAggregation = "count" | "sum" | "avg" | "min" | "max"

// ОСНОВНЫЕ ИНТЕРФЕЙСЫ
export interface ReportConfiguration {
  id: number
  workspace_id: number
  name: string
  description: string
  report_type: ReportType
  settings: Record<string, unknown>
  is_published: boolean
  created_at: string
  updated_at: string
}

export interface DashboardWidget {
  id: string
  type: DashboardWidgetType
  title: string
  description?: string
  
  source: {
    table_id: number | null
  }
  
  query: {
    aggregation?: MetricAggregation
    field_key?: string | null          // Для метрик/агрегаций
    group_by_key?: string | null       // Для группировки в графиках
    sort_by?: string | null
    sort_direction?: "asc" | "desc"
    limit?: number
    filters?: DashboardWidgetFilter[]
  }
  
  presentation: {
    show_title?: boolean
    format?: string
    color?: string
  }
  
  config: Record<string, any>          // Специфичные для типа
}

export interface DashboardWidgetFilter {
  id: string
  field: string
  operator: string
  value: unknown
}

export interface WidgetLayoutItem {
  widget_id: string
  x: number
  y: number
  w: number
  h: number
}

export interface DashboardReportSettings {
  widgets: DashboardWidget[]
  layout: WidgetLayoutItem[]
  global_filters: Array<Record<string, unknown>>
  canvas: {
    columns: number
    row_height: number
  }
}

// ТАБЛИЦА ЭКСПОРТА
export interface TableReportDataset {
  id: string
  title: string
  sheet_name: string
  table_id: number | null
  columns: ExcelReportColumn[]
  aggregated_columns?: AggregatedColumn[]
  group_by_columns?: string[]
  sorting: Array<{ field: string; direction: "asc" | "desc" }>
  filters: Array<Record<string, unknown>>
}

// ПУБЛИЧНОЕ ОТОБРАЖЕНИЕ
export interface PublicDashboardData {
  id: number
  name: string
  description?: string | null
  table_id: number
  generated_at: string
  
  metrics: PublicDashboardMetric[]
  charts: PublicDashboardChart[]
  widgets: PublicDashboardWidget[]
  recent_records: Array<{
    id: number
    data: Record<string, unknown>
    submitted_at?: string | null
    created_at: string
    submitter_email?: string | null
  }>
}

export interface PublicDashboardMetric {
  label: string
  value: number
}

export interface PublicDashboardChartPoint {
  label: string
  value: number
}

export interface PublicDashboardChart {
  title: string
  chart_type: "bar"
  color?: string | null
  points: PublicDashboardChartPoint[]
}

export interface PublicDashboardWidget {
  id: string
  type: "text" | "metric" | "table" | "chart" | "map"
  title: string
  description?: string | null
  width: "half" | "full"
  color?: string | null
  content?: string | null
  value?: number | null
  columns?: Array<{ key: string; label: string }>
  rows?: Array<Record<string, unknown>>
  page_size?: number | null
  total_rows?: number | null
  points?: PublicDashboardChartPoint[]
  map_points?: Array<{ lat: number; lng: number; label: string }>
}
```

---

### Use Cases

#### **ReportUseCase.ts**

```typescript
export class ReportUseCase {
  constructor(private token: string) {}

  // Список всех отчётов workspace'а
  async listReports(workspaceId: number): Promise<ReportConfiguration[]>

  // Получить отчёт
  async getReport(workspaceId: number, reportId: number): Promise<ReportConfiguration>

  // Создать отчёт
  async createReport(
    workspaceId: number,
    name: string,
    description: string,
    reportType: ReportType,
    settings: Record<string, unknown>,
    isPublished: boolean
  ): Promise<ReportConfiguration>

  // Обновить отчёт
  async updateReport(
    workspaceId: number,
    reportId: number,
    name: string,
    description: string,
    reportType: ReportType,
    settings: Record<string, unknown>,
    isPublished: boolean
  ): Promise<ReportConfiguration>

  // Удалить отчёт
  async deleteReport(workspaceId: number, reportId: number): Promise<void>

  // Скачать как XLSX/CSV
  async downloadExcelReport(
    workspaceId: number,
    reportId: number,
    format: "xlsx" | "csv"
  ): Promise<Blob>

  // Расчёты по шаблону
  async calculateByTemplate(
    workspaceId: number,
    tableId: number,
    file: File
  ): Promise<Blob>

  // Получить публичный дашборд
  static async getPublicDashboard(reportId: number): Promise<PublicDashboardData>
}
```

---

### API Client

#### **reportApi.ts**

```typescript
export const reportApi = {
  // ОТЧЁТЫ
  listReports: (token: string, workspaceId: number) => GET []
  getReport: (token: string, workspaceId: number, reportId: number) => GET ReportConfiguration
  createReport: (token: string, workspaceId: number, payload) => POST ReportConfiguration
  updateReport: (token: string, workspaceId: number, reportId: number, payload) => PUT ReportConfiguration
  deleteReport: (token: string, workspaceId: number, reportId: number) => DELETE void
  
  // ЭКСПОРТ/РАСЧЁТЫ
  downloadExcelReport: (token: string, workspaceId: number, reportId: number, format) => GET Blob
  calculateByTemplate: (token: string, workspaceId: number, tableId: number, file: File) => POST Blob
  
  // ПУБЛИЧНЫЙ ДАШБОРД
  getPublicDashboard: (reportId: number) => GET PublicDashboardData
}
```

---

## ⚙️ Backend архитектура

### Domain Layer

#### **entities/report_configuration.py**

```python
@dataclass
class ReportConfiguration:
    id: int | None
    workspace_id: int
    name: str
    description: str | None
    report_type: str                    # "dashboard" или "table_export"
    settings: dict[str, Any]            # JSON конфигурация
    is_published: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

---

#### **repositories/report_configuration_repository.py**

```python
class ReportConfigurationRepository(ABC):
    @abstractmethod
    def list_by_workspace(self, workspace_id: int) -> list[ReportConfiguration]

    @abstractmethod
    def get_by_id(self, workspace_id: int, report_id: int) -> ReportConfiguration | None

    @abstractmethod
    def get_public_by_id(self, report_id: int) -> ReportConfiguration | None

    @abstractmethod
    def create(self, report: ReportConfiguration, owner_id: int) -> ReportConfiguration

    @abstractmethod
    def update(self, report: ReportConfiguration, owner_id: int) -> ReportConfiguration

    @abstractmethod
    def delete(self, workspace_id: int, report_id: int, owner_id: int) -> None
```

---

### Application Layer

#### **use_cases/workspace/manage_reports.py**

```python
# СОЗДАНИЕ
class CreateReportConfigurationUseCase:
    def execute(self, report: ReportConfiguration, owner_id: int) -> ReportConfiguration

# СПИСОК
class ListReportConfigurationsUseCase:
    def execute(self, workspace_id: int) -> list[ReportConfiguration]

# ПОЛУЧЕНИЕ
class GetReportConfigurationUseCase:
    def execute(self, workspace_id: int, report_id: int) -> ReportConfiguration

# ПУБЛИЧНОЕ ПОЛУЧЕНИЕ
class GetPublicReportConfigurationUseCase:
    def execute(self, report_id: int) -> ReportConfiguration

# ОБНОВЛЕНИЕ
class UpdateReportConfigurationUseCase:
    def execute(self, report: ReportConfiguration, owner_id: int) -> ReportConfiguration

# УДАЛЕНИЕ
class DeleteReportConfigurationUseCase:
    def execute(self, workspace_id: int, report_id: int, owner_id: int) -> None
```

---

### Infrastructure Layer

#### **db/models/report_configuration_model.py**

```python
class ReportConfigurationModel(Base):
    __tablename__ = "report_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)
    settings_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

---

#### **repositories/sqlalchemy_report_configuration_repository.py**

```python
class SQLAlchemyReportConfigurationRepository(ReportConfigurationRepository):
    def __init__(self, session: Session):
        self.session = session

    def list_by_workspace(self, workspace_id: int) -> list[ReportConfiguration]:
        stmt = select(ReportConfigurationModel).where(
            ReportConfigurationModel.workspace_id == workspace_id
        )
        rows = self.session.execute(stmt).scalars().all()
        return [self._to_entity(row) for row in rows]

    def get_by_id(self, workspace_id: int, report_id: int) -> ReportConfiguration | None:
        stmt = select(ReportConfigurationModel).where(
            ReportConfigurationModel.id == report_id,
            ReportConfigurationModel.workspace_id == workspace_id,
        )
        row = self.session.execute(stmt).scalar()
        return self._to_entity(row) if row else None

    def get_public_by_id(self, report_id: int) -> ReportConfiguration | None:
        stmt = select(ReportConfigurationModel).where(
            ReportConfigurationModel.id == report_id,
            ReportConfigurationModel.is_published.is_(True),
        )
        row = self.session.execute(stmt).scalar()
        return self._to_entity(row) if row else None

    # ... create, update, delete
```

---

### Interface Layer (API Routes)

#### **routes/report_configuration.py (Key Endpoints)**

```python
# ПУБЛИЧНЫЙ ДАШБОРД
@router.get("/reports/{report_id}/dashboard", response_model=PublicDashboardResponse)
def get_public_dashboard(
    report_id: int,
    session: Session = Depends(get_db),
    repo: ReportConfigurationRepository = Depends(get_report_repo),
)
    """Получить публичный дашборд"""
    
    report = use_case.execute(report_id)
    settings = _normalize_dashboard_settings(report.settings or {})
    
    # Нормализация настроек
    # Загрузка данных из таблицы
    # Построение метрик
    # Построение графиков
    # Построение виджетов
    
    return PublicDashboardResponse(...)

# УПРАВЛЕНИЕ ОТЧЁТАМИ (authenticated)
@router.get("/workspaces/{workspace_id}/reports")
def list_reports(workspace_id: int, ...)

@router.post("/workspaces/{workspace_id}/reports", status_code=status.HTTP_201_CREATED)
def create_report(workspace_id: int, payload: ReportConfigurationCreateRequest, ...)

@router.get("/workspaces/{workspace_id}/reports/{report_id}")
def get_report(workspace_id: int, report_id: int, ...)

@router.put("/workspaces/{workspace_id}/reports/{report_id}")
def update_report(workspace_id: int, report_id: int, payload: ReportConfigurationUpdateRequest, ...)

@router.delete("/workspaces/{workspace_id}/reports/{report_id}")
def delete_report(workspace_id: int, report_id: int, ...)

# ЭКСПОРТ
@router.get("/workspaces/{workspace_id}/reports/{report_id}/export")
def download_excel_report(workspace_id: int, report_id: int, format: str = "xlsx", ...)
```

---

#### **schemas/report_configuration.py (Pydantic Models)**

```python
class ReportConfigurationCreateRequest(BaseModel):
    name: str                           # max 255 chars
    description: str = ""
    report_type: ReportType             # "dashboard" или "table_export"
    settings: dict[str, Any] = {}
    is_published: bool = False

class ReportConfigurationResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    description: str | None
    report_type: ReportType
    settings: dict[str, Any]
    is_published: bool
    created_at: datetime
    updated_at: datetime

# ПУБЛИЧНЫЕ МОДЕЛИ
class DashboardMetricResponse(BaseModel):
    label: str
    value: float | int

class DashboardChartPointResponse(BaseModel):
    label: str
    value: float | int

class DashboardChartResponse(BaseModel):
    title: str
    chart_type: Literal["bar"]
    color: str | None = None
    points: list[DashboardChartPointResponse]

class PublicDashboardWidgetResponse(BaseModel):
    id: str
    type: Literal["text", "metric", "table", "chart", "map"]
    title: str
    description: str | None = None
    width: Literal["half", "full"] = "full"
    color: str | None = None
    content: str | None = None
    value: float | int | None = None
    columns: list[dict[str, str]] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    page_size: int | None = None
    total_rows: int | None = None
    points: list[DashboardChartPointResponse] = Field(default_factory=list)
    map_points: list[dict[str, Any]] = Field(default_factory=list)

class PublicDashboardResponse(BaseModel):
    id: int
    name: str
    description: str | None
    table_id: int
    generated_at: datetime
    metrics: list[DashboardMetricResponse]
    charts: list[DashboardChartResponse]
    recent_records: list[dict[str, Any]]
    widgets: list[PublicDashboardWidgetResponse] = Field(default_factory=list)
```

---

## 📊 Типы графиков и виджетов

### Поддерживаемые типы виджетов

| Тип | Описание | Конфиг | Query |
|-----|---------|--------|-------|
| **text** | Статический текст | `{ content: string }` | — |
| **metric** | Агрегированное значение | — | `{ aggregation, field_key }` |
| **chart** | Bar chart | `{ chartType: "bar" }` | `{ group_by_key, aggregation, field_key, limit }` |
| **table** | Таблица данных | `{ columns: string[] }` | `{ limit }` |
| **map** | Карта с точками | `{ latField, lngField, labelField }` | `{ limit }` |

### Функции агрегации

```
count:  Количество записей / значений
sum:    Сумма значений в числовом поле
avg:    Среднее значение
min:    Минимальное значение
max:    Максимальное значение
```

### Примеры конфигураций

#### Metric Widget
```json
{
  "id": "metric_1",
  "type": "metric",
  "title": "Total Records",
  "source": { "table_id": 123 },
  "query": {
    "aggregation": "count",
    "field_key": null
  },
  "presentation": {
    "color": "#2b8f86"
  }
}
```

#### Chart Widget
```json
{
  "id": "chart_1",
  "type": "chart",
  "title": "Orders by Status",
  "source": { "table_id": 123 },
  "query": {
    "aggregation": "count",
    "group_by_key": "status",
    "field_key": null,
    "limit": 10
  },
  "presentation": {
    "color": "#1c8c83"
  }
}
```

#### Table Widget
```json
{
  "id": "table_1",
  "type": "table",
  "title": "Recent Orders",
  "source": { "table_id": 123 },
  "config": {
    "columns": ["id", "name", "status", "date"]
  },
  "query": {
    "limit": 20
  }
}
```

---

## 📦 Модели данных

### Dashboard Settings (JSON Storage)

```json
{
  "table_id": 123,
  "metrics": [
    {
      "label": "Total Orders",
      "aggregation": "count",
      "field_key": null
    },
    {
      "label": "Revenue",
      "aggregation": "sum",
      "field_key": "amount"
    }
  ],
  "charts": [
    {
      "title": "Orders by City",
      "chart_type": "bar",
      "color": "#2b8f86",
      "group_by_key": "city",
      "aggregation": "count",
      "limit": 10
    }
  ],
  "recent_limit": 10,
  "widgets": [
    {
      "id": "widget_1",
      "type": "metric",
      "title": "Total",
      "source": { "table_id": 123 },
      "query": { "aggregation": "count" },
      "presentation": { "color": "#2b8f86" }
    }
  ],
  "layout": [
    {
      "widget_id": "widget_1",
      "x": 0,
      "y": 0,
      "w": 2,
      "h": 1
    }
  ],
  "canvas": {
    "columns": 12,
    "row_height": 100
  }
}
```

### Table Export Settings (JSON Storage)

```json
{
  "datasets": [
    {
      "id": "dataset_1",
      "title": "Sales Report",
      "sheet_name": "Report",
      "table_id": 123,
      "columns": [
        {
          "key": "id",
          "label": "ID",
          "header_group": null
        },
        {
          "key": "name",
          "label": "Customer Name",
          "header_group": "Customer"
        },
        {
          "key": "amount",
          "label": "Amount",
          "header_group": "Sales"
        }
      ],
      "sorting": [
        { "field": "created_at", "direction": "desc" }
      ],
      "filters": []
    }
  ]
}
```

---

## 🎯 Use Cases

### User Story 1: Создание Dashboard'а

```
1. Пользователь открывает DashboardView
2. Переходит на табу "reports"
3. Нажимает "Создать отчёт" → выбирает "dashboard"
4. Выбирает таблицу источника
5. Открывается ReportDetailView (редактор)
6. Добавляет виджеты (перетаскиванием из палитры)
7. Для каждого виджета:
   - Выбирает тип
   - Выбирает поле для агрегации
   - Устанавливает цвет
8. Сохраняет отчёт (POST /workspaces/{id}/reports)
9. Dashboard сохранится с settings в JSON
```

### User Story 2: Просмотр публичного Dashboard'а

```
1. Пользователь получает ссылку на дашборд
2. Открывает PublicDashboardView (/dashboard/{reportId})
3. Frontend запрашивает GET /reports/{reportId}/dashboard
4. Backend:
   - Загружает ReportConfiguration
   - Нормализует settings
   - Получает данные из таблицы
   - Строит метрики (агрегирует данные)
   - Строит графики (группирует и агрегирует)
   - Строит виджеты (с фильтрацией и лимитами)
5. Frontend отображает: метрики, графики, таблицу, карту
6. Пользователь может фильтровать, сортировать, искать
```

### User Story 3: Экспорт таблицы в Excel

```
1. Пользователь на TableReportView выбирает dataset'ы
2. Нажимает "Скачать как XLSX"
3. Frontend: POST /workspaces/{id}/reports/{id}/export?format=xlsx
4. Backend:
   - Нормализует Table Report Settings
   - Для каждого dataset'а:
     - Загружает данные из таблицы
     - Применяет фильтры и сортировку
   - Создаёт Excel с multiple sheets
   - Применяет grouped headers
5. Возвращает Blob → скачивание
```

---

## 🔌 API endpoints

### Public Endpoints

```
GET /reports/{report_id}/dashboard
  Response: PublicDashboardResponse
  
  Нет auth требуется, но только если report.is_published = true
```

### Protected Endpoints (требуют Bearer token)

```
# УПРАВЛЕНИЕ ОТЧЁТАМИ
GET    /workspaces/{workspace_id}/reports
POST   /workspaces/{workspace_id}/reports
GET    /workspaces/{workspace_id}/reports/{report_id}
PUT    /workspaces/{workspace_id}/reports/{report_id}
DELETE /workspaces/{workspace_id}/reports/{report_id}

# ЭКСПОРТ
GET    /workspaces/{workspace_id}/reports/{report_id}/export?format=xlsx|csv

# РАСЧЁТЫ ПО ШАБЛОНАМ
POST   /workspaces/{workspace_id}/reports/template-calc?table_id={id}
       (multipart/form-data с template_file: .odt)
```

---

## 📁 Полный список файлов

### Frontend

```
frontend/src/
│
├── domain/entities/
│   └── Report.ts ........................ Типы и интерфейсы для отчётов
│
├── application/usecases/
│   └── ReportUseCase.ts ................. Бизнес-логика отчётов
│
├── infrastructure/api/
│   └── reportApi.ts ..................... HTTP клиент для API
│
└── presentation/
    ├── views/
    │   ├── DashboardView.vue ............ Главный интерфейс (workspace/reports)
    │   ├── ReportDetailView.vue ........ Редактор дашборда (widget builder)
    │   ├── TableReportView.vue ......... Просмотр табличного отчёта
    │   └── PublicDashboardView.vue ..... Публичный дашборд (read-only)
    │
    └── components/dashboard/
        ├── DashboardTileCard.vue ....... Универсальная карточка
        ├── DashboardTileActions.vue .... Контейнер для кнопок действий
        ├── DashboardDataSection.vue .... Просмотр данных таблицы
        ├── DashboardSidebar.vue ........ Боковая панель (workspace'ы)
        ├── DashboardImportSection.vue .. Импорт данных
        └── DashboardTemplateModal.vue .. Расчёты по шаблонам
```

### Backend

```
backend/app/
│
├── domain/
│   ├── entities/
│   │   └── report_configuration.py .... ReportConfiguration dataclass
│   │
│   └── repositories/
│       └── report_configuration_repository.py ... Repository interface
│
├── application/use_cases/
│   └── workspace/
│       └── manage_reports.py ......... CreateReportUseCase, GetReportUseCase, etc.
│
├── infrastructure/
│   ├── repositories/
│   │   └── sqlalchemy_report_configuration_repository.py ... SQLAlchemy impl
│   │
│   └── db/models/
│       └── report_configuration_model.py ... SQLAlchemy ORM model
│
└── interfaces/api/v1/
    ├── routes/
    │   └── report_configuration.py ... FastAPI роуты
    │
    └── schemas/
        └── report_configuration.py ... Pydantic request/response models
```

---

## 🔄 Data Flow

### Создание Dashboard'а

```
Frontend (ReportDetailView)
  ↓ 
ReportUseCase.createReport()
  ↓
reportApi.createReport()
  ↓ POST /workspaces/{id}/reports
Backend (FastAPI)
  ↓
CreateReportConfigurationUseCase.execute()
  ↓
SQLAlchemyReportConfigurationRepository.create()
  ↓
ReportConfigurationModel (Insert to DB)
  ↓ Response
ReportConfigurationResponse
  ↓
Frontend: Report сохранён
```

### Отображение публичного Dashboard'а

```
Frontend (PublicDashboardView)
  ↓
ReportUseCase.getPublicDashboard()
  ↓
reportApi.getPublicDashboard(reportId)
  ↓ GET /reports/{id}/dashboard
Backend (FastAPI)
  ↓
GetPublicReportConfigurationUseCase.execute()
  ↓
SQLAlchemyReportConfigurationRepository.get_public_by_id()
  ↓
Normalize Settings → Load Data → Build Metrics/Charts/Widgets
  ↓ Response
PublicDashboardResponse
  ↓
Frontend: Отображает виджеты, графики, таблицу
```

---

## 🚀 Расширение функционала

### Добавить новый тип виджета

1. **Frontend**:
   - Update `DashboardWidgetType` in `Report.ts`
   - Add builder UI in `ReportDetailView.vue`
   - Add renderer in `PublicDashboardView.vue`

2. **Backend**:
   - Update response handler in `report_configuration.py`
   - Add data aggregation logic if needed

### Добавить новую функцию агрегации

1. **Frontend** (`Report.ts`):
   - Add to `MetricAggregation` type
   - Update `aggregate()` helper

2. **Backend** (`report_configuration.py`):
   - Update `_build_chart_points()`
   - Update `_build_widget_metric_value()`

### Добавить новый тип графика

1. Update `DashboardChartConfig.chart_type` to support new types
2. Add chart rendering in `PublicDashboardView.vue`
3. Add chart builder UI in `ReportDetailView.vue`
4. Backend already supports generic point aggregation

---

## 📚 Ключевые функции

✅ **Реализовано**:
- CRUD операции над отчётами
- 5 типов виджетов (text, metric, chart, table, map)
- 5 функций агрегации (count, sum, avg, min, max)
- Bar charts (ECharts)
- Карты (MapLibre GL)
- Публичный экспорт
- Excel/CSV экспорт таблиц
- Расчёты по шаблонам (.odt)
- Фильтрация и поиск
- Pagination
- Публичный доступ (is_published flag)

🔄 **В разработке / Расширяемо**:
- Глобальные фильтры (каркас есть)
- Фильтры на уровне виджета (каркас есть)
- Дополнительные типы графиков (line, pie, etc.)
- Dashboard layout (сетка, перетаскивание)

---

## 🔐 Безопасность

- ✅ Bearer token authentication для всех защищённых методов
- ✅ Workspace ownership validation
- ✅ Published flag для публичного доступа
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Input validation (Pydantic)

---

Дата анализа: 2026-03-24
