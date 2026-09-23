from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='../.env', extra='ignore',
        secrets_dir='/run/secrets' if Path('/run/secrets').is_dir() else None,
    )
    database_url: str = 'postgresql+psycopg://planner:planner@localhost:5432/flightplanner'
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    flight_provider: str = 'mock'
    duffel_access_token: str = ''
    duffel_require_test_mode: bool = False

    @field_validator('database_url', mode='before')
    @classmethod
    def use_psycopg(cls, value):
        # Neon supplies a standard PostgreSQL URI; this app uses psycopg 3.
        for prefix in ('postgres://', 'postgresql://'):
            if isinstance(value, str) and value.startswith(prefix):
                return 'postgresql+psycopg://' + value[len(prefix):]
        return value


settings = Settings()
