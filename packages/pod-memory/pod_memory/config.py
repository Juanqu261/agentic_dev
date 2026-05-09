from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class PodMemorySettings(BaseSettings):
    # ── Local embedded (default) ──────────────────────────────────────────
    chroma_path: str = "./chroma_data"

    # ── Self-hosted remote ChromaDB ───────────────────────────────────────
    chroma_host: str | None = None
    chroma_port: int = 8000

    # ── Chroma Cloud ──────────────────────────────────────────────────────
    chroma_api_key: str | None = None
    chroma_tenant: str | None = None
    chroma_database: str | None = None

    embedding_model: str = "all-MiniLM-L6-v2"
    collection_name: str = "axioms"
    chunk_size: int = 400
    chunk_overlap: int = 50
    port: int = 8000
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_prefix="POD_MEMORY_", extra="ignore")


settings = PodMemorySettings()
