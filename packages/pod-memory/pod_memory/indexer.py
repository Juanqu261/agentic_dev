from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".mypy_cache"}
_SKIP_EXTS = {".pyc", ".pyo", ".exe", ".dll", ".so", ".dylib", ".bin"}


def _is_binary(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return b"\x00" in f.read(8192)
    except OSError:
        return True


def _language(path: Path) -> str:
    return path.suffix.lstrip(".") or "text"


def _chunks(text: str, size: int, overlap: int) -> list[str]:
    result = []
    start = 0
    while start < len(text):
        result.append(text[start : start + size])
        start += size - overlap
    return result


def index_repo(
    repo_path: str,
    repo_id: str,
    collection: chromadb.Collection,
    ef: SentenceTransformerEmbeddingFunction,
) -> int:
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise ValueError(f"repo_path is not a directory: {repo_path}")

    from pod_memory.config import settings

    char_size = settings.chunk_size * 4
    char_overlap = settings.chunk_overlap * 4

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for filename in filenames:
            file_path = Path(dirpath) / filename
            if file_path.suffix in _SKIP_EXTS:
                continue
            if _is_binary(file_path):
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = str(file_path.relative_to(root))
            lang = _language(file_path)
            for idx, chunk in enumerate(_chunks(text, char_size, char_overlap)):
                ids.append(f"{repo_id}::{rel}::{idx}")
                documents.append(chunk)
                metadatas.append({"path": rel, "repo": repo_id, "language": lang})

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    return len(ids)
