from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "CHANGE-ME-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    mes_db_host: str = "10.69.12.20"
    mes_db_port: int = 8000
    mes_db_name: str = "JinchenMES"
    mes_db_user: Optional[str] = None
    mes_db_password: Optional[str] = None
    mes_db_engine: Optional[str] = None
    mes_adapter: str = "mock"
    jinchen_api_url: str = "http://10.69.12.10:8000"
    jinchen_api_token: Optional[str] = None
    jinchen_api_timeout: float = 30.0
    query_timeout_seconds: int = 30
    query_max_rows: int = 10000
    history_days_limit: int = 30
    llm_provider: str = "mock"
    llm_endpoint: str = "http://localhost:11434"
    llm_model: Optional[str] = None
    llm_timeout_seconds: int = 60
    timezone: str = "TBD"
    shift_a_start: str = "07:00"
    shift_a_end: str = "15:00"
    shift_b_start: str = "15:00"
    shift_b_end: str = "23:00"
    shift_c_start: str = "23:00"
    shift_c_end: str = "07:00"
    production_lines: list = ["KM1", "KM2", "KM3"]
    app_db_url: str = "sqlite:///./data/app.db"
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_mask_sensitive: bool = True
    frontend_url: str = "http://localhost:3000"

settings = Settings()
