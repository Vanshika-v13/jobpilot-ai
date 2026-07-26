import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the backend directory (where .env typically is located)
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Environment Variables:
# MONGODB_URI       (Optional, default: "mongodb://localhost:27017/jobpilot") - MongoDB connection string
# LLM_PROVIDER      (Optional, default: "ollama") - which LLM backend to use ("ollama" or "gemini")
# OLLAMA_BASE_URL   (Optional, default: http://localhost:11434) - Ollama server endpoint
# GEMINI_API_KEY    (Optional, default: "") - required only if LLM_PROVIDER="gemini"
# GEMINI_MODEL      (Optional, default: "gemini-1.5-flash") - which Gemini model to use
# OLLAMA_MODEL      (Optional, default: "llama3.1") - which Ollama model to use for extraction/generation
# HOST              (Optional, default: 127.0.0.1) - server bind address
# PORT              (Optional, default: 8000) - server port
class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017/jobpilot"
    host: str = "127.0.0.1"
    port: int = 8000
    llm_provider: str = "ollama"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    vite_api_base_url: str = "http://localhost:8000"
    headless: bool = True

    model_config = SettingsConfigDict(
        env_file=os.path.join(BACKEND_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

