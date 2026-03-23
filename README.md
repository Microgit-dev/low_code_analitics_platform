# Low Code Analytics Platform

Стартовый каркас платформы с разделением на backend/frontend и изоляцией логики.

## Текущий этап

Сделан контур 1 (базовый фундамент):

- Регистрация и вход пользователя (без ролей).
- JWT авторизация.
- Пользователь видит только свои `workspaces`.
- Базовые CRUD-эндпоинты для `workspaces` (создание + список).

## Архитектура

### Backend (`FastAPI`, DDD)

- `app/domain` — сущности и интерфейсы репозиториев.
- `app/application` — use cases и доменные сервисы.
- `app/infrastructure` — SQLAlchemy, Postgres, реализация репозиториев.
- `app/interfaces` — API слой (роуты, схемы, зависимости).

### Frontend (`Vue 3`, Clear Architecture)

- `src/domain` — типы/сущности.
- `src/application` — use case слой.
- `src/infrastructure` — API клиенты.
- `src/presentation` — роутер, store, UI страницы.

## Запуск

```bash
docker compose up --build
```

Приложения:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Swagger: http://localhost:8000/docs

## Следующие контуры

1. Конструктор структуры таблиц (PostgreSQL + JSONB для метаданных)
2. Конструктор форм ввода + внешние публичные ссылки + импорт CSV/Excel
3. Конструктор отчетов/дашбордов + экспорт в Excel/Word/PDF
