from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Reports Service"
    debug: bool = False
    service_port: int = 8085

    deepseek_api_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_default_model: str = "deepseek-chat"
    deepseek_timeout_seconds: int = 90

    db_default_statement_timeout_ms: int = 15000
    db_max_rows: int = 10000

    sql_disallowed_keywords: str = (
        "INSERT,UPDATE,DELETE,DROP,ALTER,TRUNCATE,CREATE,GRANT,REVOKE,CALL,EXEC,EXECUTE"
    )

    html_max_retries: int = 2
    html_auto_patch: bool = False

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production", ""}:
                return False
        return value


settings = Settings()
