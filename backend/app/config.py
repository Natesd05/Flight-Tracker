from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='../.env', extra='ignore')
    database_url: str = 'postgresql+psycopg://planner:planner@localhost:5432/flightplanner'
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    flight_provider: str = 'mock'
    duffel_access_token: str = ''


settings = Settings()
