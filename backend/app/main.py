import logging
import time
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.models.form_configuration_model import FormConfigurationModel  # noqa: F401
from app.infrastructure.db.models.report_configuration_model import ReportConfigurationModel  # noqa: F401
from app.infrastructure.db.models.table_data_record_model import TableDataRecordModel  # noqa: F401
from app.infrastructure.db.models.table_relation_model import TableRelationModel  # noqa: F401
from app.infrastructure.db.models.table_structure_model import TableStructureModel  # noqa: F401
from app.infrastructure.db.models.user_model import UserModel  # noqa: F401
from app.infrastructure.db.models.workspace_model import WorkspaceModel  # noqa: F401
from app.infrastructure.db.session import engine
from app.interfaces.api.v1.routes.auth import router as auth_router
from app.interfaces.api.v1.routes.deepseek import router as deepseek_router
from app.interfaces.api.v1.routes.form_configuration import router as form_configuration_router
from app.interfaces.api.v1.routes.import_parser import router as import_parser_router
from app.interfaces.api.v1.routes.report_configuration import router as report_configuration_router
from app.interfaces.api.v1.routes.table_data_record import router as table_data_record_router
from app.interfaces.api.v1.routes.table_structure import router as table_structure_router
from app.interfaces.api.v1.routes.workspace import router as workspace_router


app = FastAPI(title=settings.app_name, debug=settings.debug)
logger = logging.getLogger("uvicorn.error")


def _normalize_cors_origin(raw_origin: str) -> str:
    candidate = raw_origin.strip()
    if not candidate or candidate == "*":
        return candidate
    parsed = urlparse(candidate)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return candidate


cors_origins = [
    normalized
    for normalized in (_normalize_cors_origin(origin) for origin in settings.cors_allowed_origins.split(","))
    if normalized
]
allow_all_origins = "*" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if allow_all_origins else cors_origins,
    allow_origin_regex=".*" if allow_all_origins else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(
        "HTTP request method=%s path=%s query=%s content_type=%s content_length=%s",
        request.method,
        request.url.path,
        request.url.query,
        request.headers.get("content-type"),
        request.headers.get("content-length"),
    )
    response = await call_next(request)
    logger.info(
        "HTTP response method=%s path=%s status=%s",
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(
        "Validation error method=%s path=%s query=%s content_type=%s errors=%s",
        request.method,
        request.url.path,
        request.url.query,
        request.headers.get("content-type"),
        exc.errors(),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.on_event("startup")
def on_startup() -> None:
    for attempt in range(1, settings.db_startup_max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            if attempt == settings.db_startup_max_retries:
                raise
            time.sleep(settings.db_startup_retry_delay_seconds)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api/v1")
app.include_router(deepseek_router, prefix="/api/v1")
app.include_router(workspace_router, prefix="/api/v1")
app.include_router(table_structure_router, prefix="/api/v1")
app.include_router(form_configuration_router, prefix="/api/v1")
app.include_router(report_configuration_router, prefix="/api/v1")
app.include_router(table_data_record_router, prefix="/api/v1")
app.include_router(import_parser_router, prefix="/api/v1")
