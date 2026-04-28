from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://propfinder:propfinder@localhost:5432/propfinder"
    api_key: str = "dev-secret-key"

    class Config:
        env_file = ".env"


settings = Settings()
