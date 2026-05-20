<div align="center">

# 📊 Low Code Analytics Platform

**Стартовый каркас для быстрой разработки аналитических приложений с низким кодом**

Проект разработан командой в рамках **Hack Tula 2025**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.5-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white)](https://vuejs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Vite](https://img.shields.io/badge/Vite-6.2-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vite.dev)
[![DeepSeek](https://img.shields.io/badge/DeepSeek_AI-FF6F00?style=for-the-badge&logo=openai&logoColor=white)](https://deepseek.com)

</div>

---

## 📋 Описание проекта

Полнофункциональная платформа для **создания аналитических приложений с минимальным объёмом кода**. Архитектура построена на принципах чистой архитектуры (Clean Architecture) и модульности, обеспечивая гибкость и расширяемость. Решение позволяет быстро развернуть систему сбора, хранения и анализа данных с удобным веб-интерфейсом и интеграцией с ИИ.

### 🎯 Целевая аудитория
- **Разработчики** — для создания аналитических решений с минимальным объёмом кода
- **Аналитики и бизнес-пользователи** — для конструирования форм, отчётов и дашбордов без глубоких знаний программирования
- **Организации** — для сбора, хранения и анализа данных с удобным веб-интерфейсом

---

## ✨ Ключевые возможности

### 🤖 Интеграция с ИИ (DeepSeek)
- **AI-шаблоны**: генерация структур таблиц из текстового описания, заполнение шаблонов документов
- **Расширяемый реестр методов** — добавление новых AI-методов без изменения API
- **Гибкая настройка** модели, температуры и лимитов токенов

### 🏗️ Визуальные конструкторы
- **Конструктор структуры таблиц** с поддержкой JSONB-метаданных
- **Конструктор форм ввода** с публичными ссылками и импортом из CSV/Excel
- **Конструктор отчётов и дашбордов** с экспортом в Excel, Word и PDF
- **Grid-дашборды** с настраиваемыми виджетами и публичным доступом

### 🗺️ Карты и визуализация
- **ECharts** для интерактивных графиков и диаграмм
- **Leaflet + MapLibre GL** для визуализации геоданных
- **GeoJSON-редактор** для работы с географическими объектами

### 🔒 Безопасность и изоляция данных
- **JWT-аутентификация** — регистрация, авторизация, обновление токенов, смена пароля
- **Изоляция рабочих областей** — пользователи видят только свои данные
- **CORS-конфигурация** для безопасного взаимодействия frontend и backend

---

## 🏛️ Архитектура системы

```
┌─────────────────────────────────────────────────────────────┐
│                     Клиент (Браузер)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────┐
│               Frontend (Vue 3 + Vite)                       │
│                      :5173                                  │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────────┐│
│  │  domain/    │ │ application/ │ │   presentation/       ││
│  │  entities   │ │  usecases    │ │  views + components   ││
│  └─────────────┘ └──────────────┘ └───────────────────────┘│
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│            Backend (FastAPI + SQLAlchemy)                    │
│                      :8000                                  │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────────┐│
│  │  domain/    │ │ application/ │ │   infrastructure/     ││
│  │  entities   │ │  use_cases   │ │  repositories + DB    ││
│  │  repos (I)  │ │  services    │ │  DeepSeek client      ││
│  └─────────────┘ └──────────────┘ └───────────┬───────────┘│
└──────────────────────────┬────────────────────┼─────────────┘
                           │                    │
                ┌──────────▼───────┐  ┌─────────▼─────────┐
                │  PostgreSQL 16   │  │   DeepSeek API    │
                │      :5432       │  │   (External)      │
                └──────────────────┘  └───────────────────┘
```

### Принципы архитектуры

- **Clean Architecture** — и frontend, и backend построены по одной схеме: domain → application → infrastructure/presentation
- **Docker Compose** — оркестрация трёх сервисов (БД, backend, frontend) одной командой
- **Изоляция слоёв** — доменные сущности не зависят от фреймворков и базы данных

---

## 💻 Технологический стек

### Frontend
![Vue.js](https://img.shields.io/badge/Vue.js-3.5-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6.2-646CFF?style=flat-square&logo=vite&logoColor=white)
![Pinia](https://img.shields.io/badge/Pinia-2.3-FFD859?style=flat-square&logo=vuedotjs&logoColor=black)
![Vue Router](https://img.shields.io/badge/Vue_Router-4.5-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![ECharts](https://img.shields.io/badge/ECharts-6.0-AA344D?style=flat-square&logo=apacheecharts&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-1.9-199900?style=flat-square&logo=leaflet&logoColor=white)
![MapLibre GL](https://img.shields.io/badge/MapLibre_GL-5.21-396CB2?style=flat-square&logo=maplibre&logoColor=white)
![Axios](https://img.shields.io/badge/Axios-1.8-5A29E4?style=flat-square&logo=axios&logoColor=white)

### Backend
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-2.8-E92063?style=flat-square&logo=pydantic&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-0.34-2E303E?style=flat-square&logo=gunicorn&logoColor=white)

### Генерация документов
![openpyxl](https://img.shields.io/badge/openpyxl-3.1-217346?style=flat-square&logo=microsoftexcel&logoColor=white)
![python-docx](https://img.shields.io/badge/python--docx-1.1-2B579A?style=flat-square&logo=microsoftword&logoColor=white)
![ReportLab](https://img.shields.io/badge/ReportLab-4.2-FF0000?style=flat-square&logo=adobeacrobatreader&logoColor=white)
![Jinja2](https://img.shields.io/badge/Jinja2-3.1-B41717?style=flat-square&logo=jinja&logoColor=white)

### AI
![DeepSeek](https://img.shields.io/badge/DeepSeek_API-FF6F00?style=flat-square&logo=openai&logoColor=white)

### Инфраструктура
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker_Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=flat-square&logo=postgresql&logoColor=white)

---

## 🚀 Установка и запуск

### Требования
- **Docker** и **Docker Compose**
- **DeepSeek API Key** (опционально, для AI-функций)

### 1. Клонирование репозитория

```bash
git clone https://github.com/Microgit-dev/low_code_analitics_platform.git
cd low_code_analitics_platform
```

### 2. Настройка окружения (опционально)

Для активации AI-функций укажите ключ DeepSeek API в `docker-compose.yml`:

```yaml
DEEPSEEK_API_KEY: "your_api_key_here"
```

### 3. Запуск

```bash
docker compose up --build
```

### Сервисы будут доступны:

| Сервис | URL |
|--------|-----|
| **Frontend** | http://localhost:5173 |
| **Backend API** | http://localhost:8000 |
| **Swagger UI** | http://localhost:8000/docs |
| **PostgreSQL** | `localhost:5432` |

---

## 📡 API Documentation

**Интерактивная документация:** http://localhost:8000/docs

### Основные группы эндпоинтов

| Группа | Префикс | Описание |
|--------|---------|----------|
| **Auth** | `/api/v1/auth` | Регистрация, авторизация, обновление JWT, смена пароля |
| **Workspaces** | `/api/v1/workspaces` | CRUD рабочих областей |
| **Table Structures** | `/api/v1/workspaces/{id}/schema/tables` | Управление структурой таблиц, колонками, связями |
| **Table Data** | `/api/v1/workspaces/{id}/tables/{id}/data` | CRUD записей в таблицах |
| **Forms** | `/api/v1/workspaces/{id}/forms` | Конструктор форм, публичные формы |
| **Reports** | `/api/v1/workspaces/{id}/reports` | Конфигурация отчётов, экспорт, шаблоны |
| **Import** | `/api/v1/workspaces/{id}/import` | Сканирование и импорт CSV/Excel |
| **DeepSeek AI** | `/api/v1/ai/deepseek` | AI-методы, шаблоны, генерация |

---

## 👥 Команда проекта

<table align="center">
<tr>
<td align="center" width="170">
<b>Кайков Дмитрий Алексеевич</b><br>
<sub>БИВТ-23-9</sub>
</td>
<td align="center" width="170">
<b>Миронов Егор Андреевич</b><br>
<sub>БИВТ-23-сп3</sub>
</td>
<td align="center" width="170">
<b>Заварыкина Татьяна Денисовна</b><br>
<sub>БИВТ-24-2</sub>
</td>
</tr>
<tr>
<td align="center" width="170">
<b>Фортунатов Максим Борисович</b><br>
<sub>БПИ-23-РП-1</sub>
</td>
<td align="center" width="170">
<b>Цупков Николай Олегович</b><br>
<sub>БИВТ-23-9</sub>
</td>
<td align="center" width="170">
<b>Соколов Артём Михайлович</b><br>
<sub>ВШЭ</sub>
</td>
</tr>
</table>

---

## 📁 Структура проекта

```
low_code_analitics_platform/
├── docker-compose.yml                # Оркестрация всех сервисов
├── backend/                          # Backend (Python + FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   ├── DEEPSEEK_MODULE.md            # Документация по модулю ИИ
│   └── app/
│       ├── main.py                   # Точка входа FastAPI
│       ├── config.py                 # Настройки из переменных окружения
│       ├── domain/
│       │   ├── entities/             # User, Workspace, TableStructure, Form, Report
│       │   ├── repositories/         # Интерфейсы репозиториев
│       │   └── gateways/            # Контракты внешних сервисов (DeepSeek)
│       ├── application/
│       │   ├── use_cases/           # Auth, Workspace, Table, Form, Report, DeepSeek
│       │   └── services/            # Хеширование, токены, парсеры, отчёты
│       ├── infrastructure/
│       │   ├── db/                   # SQLAlchemy сессия, модели
│       │   ├── repositories/         # Реализации репозиториев
│       │   ├── clients/              # DeepSeek API клиент
│       │   └── templates/            # Реестр AI-шаблонов
│       └── interfaces/
│           └── api/v1/
│               ├── routes/           # auth, workspace, tables, forms, reports, deepseek, import
│               ├── schemas/          # Pydantic request/response модели
│               └── dependencies/     # Зависимости (auth, db)
├── frontend/                         # Frontend (Vue 3 + Vite)
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── domain/entities/          # TypeScript типы
│       ├── application/usecases/     # Auth, Workspace, Schema, Form, Report, Import
│       ├── infrastructure/
│       │   ├── api/                  # HTTP-клиенты (Axios)
│       │   ├── auth/                 # Хранение токенов
│       │   └── composables/          # useTheme
│       └── presentation/
│           ├── router/               # Vue Router
│           ├── stores/               # Pinia stores
│           ├── views/                # Login, Register, Dashboard, Reports, Forms, PublicForm
│           ├── components/           # UI-компоненты, GeoJsonMapEditor
│           └── styles/               # CSS
└── data/
    ├── exmaples/                     # Примеры шаблонов документов
    └── llm_bible/                    # Справочные материалы для LLM
```

---

## 🗺️ Дальнейшее развитие

- [x] JWT-аутентификация и регистрация пользователей
- [x] CRUD рабочих областей с изоляцией данных
- [x] Конструктор структуры таблиц (PostgreSQL + JSONB-метаданные)
- [x] Конструктор форм ввода с публичными ссылками
- [x] Импорт данных из CSV/Excel
- [x] Интеграция DeepSeek AI (генерация структур, заполнение шаблонов)
- [x] Конструктор отчётов с экспортом в Excel/Word/PDF
- [x] Дашборды с виджетами и публичным доступом
- [x] Визуализация геоданных (Leaflet + MapLibre GL)
- [ ] Ролевая модель доступа внутри рабочих областей
- [ ] Версионирование структур таблиц
- [ ] Визуальный конструктор бизнес-процессов
- [ ] Уведомления и триггеры по событиям
- [ ] Интеграция с внешними источниками данных

---

## 🏆 Достижения

- 🚀 **Hack Tula 2025** — полнофункциональное решение, разработанное в рамках хакатона
- 🏛️ **Clean Architecture** — единая архитектурная схема на frontend и backend
- 🤖 **AI-интеграция** — расширяемая система шаблонов DeepSeek с реестром методов
- 📊 **Визуальные конструкторы** — таблицы, формы, отчёты и дашборды без написания кода
- 📄 **Мультиформатный экспорт** — генерация документов в Excel, Word и PDF

---

## 📄 Лицензия

Этот проект распространяется под лицензией **MIT**.

```
MIT License

Copyright (c) 2025 Microgit-dev

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

**Сделано с ❤️ командой Microgit-dev**

**Hack Tula 2025** | [GitHub](https://github.com/Microgit-dev/low_code_analitics_platform)

</div>
