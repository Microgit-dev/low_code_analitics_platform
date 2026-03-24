import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from app.interfaces.api.v1.routes.report_configuration import router as report_configuration_router
from app.interfaces.api.v1.routes.table_data_record import router as table_data_record_router
from app.interfaces.api.v1.routes.table_structure import router as table_structure_router
from app.interfaces.api.v1.routes.workspace import router as workspace_router


app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
