import warnings
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve repo root from this file's location:
# config.py → pod_brain/ → pod-brain/ → packages/ → repo root
_REPO_ROOT = Path(__file__).parents[3]


class PodBrainSettings(BaseSettings):
    gemini_model: str = "gemini-2.5-pro"
    gemini_api_key: str = ""
    pod_mcp_url: str = "http://localhost:8001"
    chroma_url: str = "http://localhost:8000"
    # Accepts ":memory:", a SQLite file path, or a "postgres://..." URL
    checkpointer_db: str = ":memory:"
    max_builder_loops: int = 3
    max_architect_loops: int = 2
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        # Check local .env first, fall back to repo-root .env
        env_file=(".env", str(_REPO_ROOT / ".env")),
        env_file_encoding="utf-8",
        env_prefix="POD_BRAIN_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _warn_missing_api_key(self) -> "PodBrainSettings":
        if not self.gemini_api_key:
            warnings.warn(
                "POD_BRAIN_GEMINI_API_KEY is not set — LLM calls will fail at runtime. "
                "Set it in your environment or in a .env file at the repo root.",
                stacklevel=2,
            )
        return self


settings = PodBrainSettings()
