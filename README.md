# Low Code Analytics Platform

**Стартовый каркас платформы с разделением на backend/frontend и изоляцией логики.**

Платформа предоставляет основу для быстрой разработки аналитических приложений с низким кодом. Архитектура построена на принципах чистой архитектуры и модульности, обеспечивая гибкость и расширяемость.

---

## 🎯 Назначение

- **Разработчики** — для создания аналитических решений с минимальным объемом кода.
- **Аналитики и бизнес-пользователи** — для конструирования форм, отчетов и дашбордов без глубоких знаний программирования.
- **Организации** — для сбора, хранения и анализа данных с удобным веб-интерфейсом.

---

## ✨ Особенности

- **Аутентификация и авторизация** — Регистрация и вход пользователей с JWT токенами.
- **Изоляция данных** — Пользователи видят только свои рабочие области (`workspaces`).
- **Управление рабочими областями** — CRUD-операции для `workspaces`.
- **Чистая архитектура** — Четкое разделение на слои: домен, приложение, инфраструктура, интерфейсы.
- **Контейнеризация** — Удобное развертывание с помощью Docker и Docker Compose.
- **Конструкторы** — Возможность визуального создания структур таблиц, форм ввода и отчетов (планируется).
- **DeepSeek AI Module** — Интеграция с ИИ для расширенного анализа (описание в `backend/DEEPSEEK_MODULE.md`).

---

## 🏗️ Архитектура

low_code_analitics_platform/
├── backend/                  # Backend приложение (Python + FastAPI)
│   ├── app/
│   │   ├── domain/          # Сущности и интерфейсы репозиториев
│   │   ├── application/     # Use cases и доменные сервисы
│   │   ├── infrastructure/  # SQLAlchemy, Postgres, реализация репозиториев
│   │   └── interfaces/      # API слой (роуты, схемы, зависимости)
│   └── DEEPSEEK_MODULE.md   # Документация по модулю ИИ
├── frontend/                # Frontend приложение (React/Vue - структура не указана)
│   ├── src/
│   │   ├── domain/          # Типы/сущности
│   │   ├── application/     # Use case слой
│   │   ├── infrastructure/  # API клиенты
│   │   └── presentation/    # Роутер, store, UI страницы
└── docker-compose.yml       # Оркестрация сервисов

---

## 🚀 Запуск

1. Клонируйте репозиторий:
    ```bash
    git clone https://github.com/Microgit-dev/low_code_analitics_platform.git
    cd low_code_analitics_platform
    ```

2. Запустите приложение с помощью Docker Compose:
    ```bash
    docker compose up --build
    ```

### Сервисы будут доступны:

- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs

---

## 📦 Планируемые возможности

- **Конструктор структуры таблиц** — Настройка таблиц в PostgreSQL с использованием JSONB для метаданных.
- **Конструктор форм ввода** — Создание форм с возможностью публикации по внешним ссылкам и импорта данных из CSV/Excel.
- **Конструктор отчетов/дашбордов** — Визуальное создание отчетов с возможностью экспорта в Excel/Word/PDF.

---

## 🛠️ Технологии

- **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: (Не указано, предположительно React/Vue)
- **DevOps**: Docker, Docker Compose

---

## 🤝 Участие в разработке

Вклады в проект приветствуются! Пожалуйста, следуйте стандартным практикам:

1. Форкните репозиторий
2. Создайте ветку для вашей функции (`feature/AmazingFeature`)
3. Зафиксируйте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Отправьте в репозиторий (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

---

## 📄 Лицензия

Этот проект распространяется под лицензией **MIT**.

MIT License
Copyright (c) 2024 Microgit-dev
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

---

**Сделано с ❤️**  
**Low Code Analytics Platform** | Команда Microgit-dev
