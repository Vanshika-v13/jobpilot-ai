import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the project root directory (where .env typically is located)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017/jobpilot"
    host: str = "127.0.0.1"
    port: int = 8000
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    vite_api_base_url: str = "http://localhost:8000"
    headless: bool = True

    model_config = SettingsConfigDict(
        env_file=os.path.join(PROJECT_ROOT, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
