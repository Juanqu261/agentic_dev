from __future__ import annotations

import pytest
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from fastapi.testclient import TestClient

from pod_memory.server import app


@pytest.fixture(scope="session")
def ef():
    # Loaded once per session — the model download is expensive
    return SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


@pytest.fixture
def chroma(tmp_path):
    return chromadb.PersistentClient(path=str(tmp_path / "chroma"))


@pytest.fixture
def collection(chroma, ef):
    return chroma.get_or_create_collection("pod-memory", embedding_function=ef)


@pytest.fixture
def sample_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "auth.py").write_text(
        "def authenticate(user, password):\n    return check_credentials(user, password)\n"
    )
    (repo / "database.py").write_text(
        "def connect(url):\n    return create_engine(url)\n\ndef query(sql):\n    pass\n"
    )
    (repo / "README.md").write_text(
        "# My App\nHandles user authentication and database access.\n"
    )
    return repo


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    monkeypatch.setattr("pod_memory.config.settings.chroma_path", str(tmp_path / "chroma"))
    monkeypatch.setattr("pod_memory.config.settings.chroma_host", None)
    with TestClient(app) as client:
        yield client
