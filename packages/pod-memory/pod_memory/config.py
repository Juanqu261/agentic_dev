from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class PodMemorySettings(BaseSettings):
    chroma_path: str = "./chroma_data"
    chroma_host: str | None = None
    chroma_port: int = 8000

    embedding_model: str = "all-MiniLM-L6-v2"
    collection_name: str = "target-repo"
    chunk_size: int = 400
    chunk_overlap: int = 50
    port: int = 8000
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_prefix="POD_MEMORY_", extra="ignore")


settings = PodMemorySettings()
