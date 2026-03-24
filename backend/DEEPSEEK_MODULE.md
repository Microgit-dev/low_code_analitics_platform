# DeepSeek AI Module

## Назначение

Модуль позволяет вызывать DeepSeek API через backend проекта в формате готовых AI-методов.

Под AI-методом понимается типовой сценарий с уже заданным назначением и внутренним prompt.

Примеры:

- создание структуры таблицы по текстовому описанию
- заполнение шаблона документа по переданному контексту

Модуль встроен в текущую архитектуру проекта:

- `domain` описывает сущности и контракты
- `application` содержит use case-логику
- `infrastructure` хранит реестр шаблонов и клиент DeepSeek API
- `interfaces` предоставляет HTTP API

## Что уже реализовано

Сейчас доступны два готовых метода:

- `table_structure_from_description`
- `document_template_fill`

## Как работает модуль

Поток выполнения:

1. Клиент вызывает endpoint backend.
2. Backend находит AI-метод по `template_id`.
3. Реестр шаблонов собирает внутренний prompt на основе входных данных.
4. Backend отправляет запрос в DeepSeek API.
5. Ответ модели возвращается клиенту.

## Конфигурация

Нужно задать переменные окружения:

```env
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_DEFAULT_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=60
```

Они уже добавлены в:

- [config.py](C:\Users\sokol\PycharmProjects\low_code_analitics_platform\backend\app\config.py)
- [\.env.example](C:\Users\sokol\PycharmProjects\low_code_analitics_platform\backend\.env.example)
- [docker-compose.yml](C:\Users\sokol\PycharmProjects\low_code_analitics_platform\docker-compose.yml)

## HTTP API

### 1. Получить список доступных AI-методов

`GET /api/v1/ai/deepseek/templates`

Ответ содержит:

- `template_id`
- `name`
- `description`
- `input_fields`
- `default_model`

### 2. Выполнить AI-метод

`POST /api/v1/ai/deepseek/templates/{template_id}/execute`

Тело запроса:

```json
{
  "input": {},
  "model": "deepseek-chat",
  "temperature": 0.2,
  "max_tokens": 1000
}
```

Поля:

- `input` — входные данные для выбранного метода
- `model` — необязательное переопределение модели
- `temperature` — необязательная температура генерации
- `max_tokens` — необязательный лимит токенов ответа

## Доступные AI-методы

### `table_structure_from_description`

Назначение:

Создаёт JSON структуры таблицы для low-code платформы по текстовому описанию.

Входные поля:

- `description` — обязательное текстовое описание таблицы и её полей
- `table_name` — необязательное желаемое имя таблицы
- `workspace_context` — необязательный бизнес-контекст
- `constraints` — необязательные ограничения по типам и правилам

Пример запроса:

```json
{
  "input": {
    "description": "Нужна таблица клиентов с именем, телефоном, email, сегментом, датой регистрации и статусом",
    "table_name": "Клиенты",
    "workspace_context": "CRM для отдела продаж",
    "constraints": "Используй enum для статуса и сегмента, ключи колонок в snake_case"
  },
  "model": "deepseek-chat",
  "temperature": 0.2,
  "max_tokens": 1200
}
```

Ожидаемый результат:

Текстовый ответ модели в формате JSON со структурой:

```json
{
  "name": "Клиенты",
  "description": "Описание таблицы",
  "columns": [
    {
      "key": "status",
      "name": "Статус",
      "type": "enum",
      "required": true,
      "settings": {
        "options": ["new", "active", "archived"]
      }
    }
  ]
}
```

Этот JSON спроектирован так, чтобы быть совместимым с моделью структуры таблиц проекта.

### `document_template_fill`

Назначение:

Заполняет шаблон документа по входному контексту и возвращает готовый текст.

Входные поля:

- `document_template` — обязательный шаблон документа
- `context` — обязательные данные для заполнения
- `instructions` — необязательные требования к стилю и содержанию
- `output_format` — необязательный формат результата

Пример запроса:

```json
{
  "input": {
    "document_template": "Коммерческое предложение\n\nКлиент: ...\nЦель проекта: ...\nСроки: ...\nБюджет: ...",
    "context": "Клиент: ООО Ромашка. Цель: автоматизировать отчётность. Сроки: 6 недель. Бюджет: 1.2 млн рублей.",
    "instructions": "Сделай документ деловым, коротким и готовым к отправке",
    "output_format": "markdown"
  },
  "model": "deepseek-chat",
  "temperature": 0.3,
  "max_tokens": 1500
}
```

Ожидаемый результат:

Готовый текст документа без пояснений от модели.

## Формат ответа

Ответ `execute` содержит:

- `template_id`
- `template_name`
- `normalized_input`
- `model`
- `finish_reason`
- `request_id`
- `content`
- `usage`

Основное поле результата:

- `content` — итоговый текст, который сгенерировал DeepSeek

## Где находится код

Основные файлы модуля:

- API-роуты: [deepseek.py](C:\Users\sokol\PycharmProjects\low_code_analitics_platform\backend\app\interfaces\api\v1\routes\deepseek.py)
- API-схемы: [deepseek.py](C:\Users\sokol\PycharmProjects\low_code_analitics_platform\backend\app\interfaces\api\v1\schemas\deepseek.py)
- Реестр AI-методов: [deepseek_template_registry.py](C:\Users\sokol\PycharmProjects\low_code_analitics_platform\backend\app\infrastructure\templates\deepseek_template_registry.py)
- Клиент DeepSeek API: [deepseek_api_client.py](C:\Users\sokol\PycharmProjects\low_code_analitics_platform\backend\app\infrastructure\clients\deepseek_api_client.py)
- Use case-слой: [execute_ai_template.py](C:\Users\sokol\PycharmProjects\low_code_analitics_platform\backend\app\application\use_cases\deepseek\execute_ai_template.py)

## Как добавить новый AI-метод

Минимальный порядок действий:

1. Описать новый метод в реестре [deepseek_template_registry.py](C:\Users\sokol\PycharmProjects\low_code_analitics_platform\backend\app\infrastructure\templates\deepseek_template_registry.py).
2. Добавить список его входных полей.
3. Реализовать сборку внутреннего prompt.
4. При необходимости добавить пост-обработку результата.

По текущей реализации новый AI-метод добавляется без изменения HTTP API.

## Практический сценарий запуска

1. Указать `DEEPSEEK_API_KEY`.
2. Поднять backend.
3. Открыть Swagger по адресу `/docs`.
4. Вызвать `GET /api/v1/ai/deepseek/templates`.
5. Выбрать нужный `template_id`.
6. Вызвать `POST /api/v1/ai/deepseek/templates/{template_id}/execute`.

## Ограничения текущей версии

- шаблоны пока хранятся в коде, а не в базе данных
- нет frontend-интерфейса для работы с модулем
- ответ модели возвращается как текст в `content`
- структурная валидация JSON-ответа модели пока не добавлена