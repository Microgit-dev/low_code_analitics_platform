from __future__ import annotations
import logging
from typing import Dict, Any

from fastapi import FastAPI, HTTPException

from .config import settings
from .dto import ReportGenerationRequest, ReportGenerationResponse
from .service import ReportGenerationService
from .llm_client import LLMError
from .sql_validator import SqlValidationError
from .db_executor import DbExecutionError
from .html_guard import HtmlPostCheckError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

app = FastAPI(title=settings.app_name)
service = ReportGenerationService()

@app.post("/reports/generate", response_model=ReportGenerationResponse)
def generate_report(req: ReportGenerationRequest):
    try:
        sql, rows, html, debug_info = service.run(req)
        resp = ReportGenerationResponse(sql=sql, rows=rows, html=html)
        if req.debug or settings.debug:
            resp.debug_info = debug_info
        return resp
    except (LLMError, SqlValidationError, DbExecutionError, HtmlPostCheckError) as e:
        logger.exception("Ошибка генерации отчёта")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Неожиданная ошибка")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
