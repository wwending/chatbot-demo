from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.runtime import is_frozen, runtime_path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Personal Knowledge Chatbot Demo"
    db_path: Path = Field(default=Path("data/chatbot.db"))
    knowledge_dir: Path = Field(default=Path("knowledge"))
    vector_store_path: Path = Field(default=Path("data/vector_store.json"))

    llm_provider: str = "deepseek"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2

    embedding_model: str = "local-hashing-demo"
    weather_api_key: str = ""

    chunk_size: int = 500
    chunk_overlap: int = 80
    rag_top_k: int = 4
    rag_min_score: float = 0.08
    history_turns: int = 6


@lru_cache
def get_settings() -> Settings:
    if is_frozen():
        settings = Settings(_env_file=runtime_path(".env"))
        settings.db_path = runtime_path("data", "chatbot.db")
        settings.knowledge_dir = runtime_path("knowledge")
        settings.vector_store_path = runtime_path("data", "vector_store.json")
        return settings
    settings = Settings()
    return settings
