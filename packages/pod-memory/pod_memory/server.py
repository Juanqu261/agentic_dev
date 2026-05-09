from __future__ import annotations

from contextlib import asynccontextmanager

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from fastapi import FastAPI

from pod_memory.config import settings
from pod_memory.routes.memory import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.chroma_api_key and settings.chroma_tenant and settings.chroma_database:
        client = chromadb.CloudClient(
            tenant=settings.chroma_tenant,
            database=settings.chroma_database,
            api_key=settings.chroma_api_key,
        )
    elif settings.chroma_host:
        client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
    else:
        client = chromadb.PersistentClient(path=settings.chroma_path)

    ef = SentenceTransformerEmbeddingFunction(model_name=settings.embedding_model)

    app.state.chroma = client
    app.state.ef = ef
    yield


app = FastAPI(title="pod-memory", lifespan=lifespan)
app.include_router(router)
