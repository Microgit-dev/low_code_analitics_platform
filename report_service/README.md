# Reports Service

FastAPI-сервис для генерации HTML-отчётов через SQL + HTML pipeline.

Важно: все команды ниже нужно запускать из каталога `report_service`. Если запускать `docker compose ...` из родительской папки `low_code_platform`, compose-файл не будет найден.

## Быстрый старт

```powershell
cd report_service
docker compose build --no-cache
docker compose up -d
```

Документация после старта:

- `http://localhost:8085/docs`
- `http://localhost:8085/redoc`
- `http://localhost:8085/openapi.json`

## Trace сценарий формы Д

```powershell
cd report_service
docker compose exec -T reports_service python -m scripts.form_d_example_trace
docker compose exec -T reports_service sh -lc "ls -la /app/out || true"
```

## Минимальный валидный POST /reports/generate

Готовый payload лежит в [examples/report_generation_request.min.json](/c:/Users/kolac/Desktop/ml/low_code_platform/report_service/examples/report_generation_request.min.json).

Этот payload использует явный diagnostic stub mode:

- `debug=true`
- `db.driver=stub`
- `db.host=stub`

Такой режим не меняет публичный API-контракт, но позволяет локально прогнать `/reports/generate` без живой БД и без внешней ручной подготовки.

### PowerShell

```powershell
cd report_service
$body = Get-Content .\examples\report_generation_request.min.json -Raw
Invoke-RestMethod `
  -Uri "http://localhost:8085/reports/generate" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

### Python requests

```powershell
cd report_service
python -c "import json, requests; data=json.load(open('examples/report_generation_request.min.json', encoding='utf-8')); resp=requests.post('http://localhost:8085/reports/generate', json=data, timeout=60); print(resp.status_code); print(resp.text[:1000])"
```

### Готовый smoke-скрипт

```powershell
cd report_service
python src/scripts/smoke_generate_report.py
```

В контейнере:

```powershell
cd report_service
docker compose exec -T reports_service python /app/scripts/smoke_generate_report.py
```

## Тесты

Тесты доступны и на хосте, и в контейнере, потому что `tests/`, `examples/` и `pytest.ini` копируются в image.

На хосте:

```powershell
cd report_service
pytest -q
```

В контейнере:

```powershell
cd report_service
docker compose exec -T reports_service pytest -q
```

## Form D unified run

Единая точка запуска лежит в [src/scripts/run_form_d_pipeline.py](/c:/Users/kolac/Desktop/ml/low_code_platform/report_service/src/scripts/run_form_d_pipeline.py), а пример конфига в [examples/form_d_run_config.json](/c:/Users/kolac/Desktop/ml/low_code_platform/report_service/examples/form_d_run_config.json).

Локально:

```powershell
cd report_service
python src/scripts/run_form_d_pipeline.py --config examples/form_d_run_config.json --mode stub --print-summary
python src/scripts/run_form_d_pipeline.py --config examples/form_d_run_config.json --mode live --print-summary
```

Через Docker Compose:

```powershell
cd report_service
docker compose exec -T reports_service python -m scripts.run_form_d_pipeline --config /app/examples/form_d_run_config.json --mode stub --print-summary
docker compose exec -T reports_service python -m scripts.run_form_d_pipeline --config /app/examples/form_d_run_config.json --mode live --print-summary
```

Все артефакты полного прогона складываются в `out/form_d_run/`:

- `04_sql_prompt.txt`
- `05_sql_raw.txt`
- `07_rows.json`
- `09_html_raw.txt`
- `11_html_after_guard.html`
- `13_final_result.html`
