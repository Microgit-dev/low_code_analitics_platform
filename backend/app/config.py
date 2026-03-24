from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Low Code Analytics Platform"
    debug: bool = False
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/low_code"
    db_startup_max_retries: int = 20
    db_startup_retry_delay_seconds: int = 2
    cors_allowed_origins: str = "http://localhost:5173"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    deepseek_api_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_default_model: str = "deepseek-chat"
    deepseek_timeout_seconds: int = 60


settings = Settings()
