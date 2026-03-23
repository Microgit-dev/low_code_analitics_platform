import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.models.user_model import UserModel  # noqa: F401
from app.infrastructure.db.models.workspace_model import WorkspaceModel  # noqa: F401
from app.infrastructure.db.session import engine
from app.interfaces.api.v1.routes.auth import router as auth_router
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
app.include_router(workspace_router, prefix="/api/v1")
