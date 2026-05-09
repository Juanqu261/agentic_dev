from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from pod_memory import indexer, retriever

router = APIRouter()


class IndexRequest(BaseModel):
    repo_path: str
    repo_id: str


class QueryRequest(BaseModel):
    repo_id: str
    query: str
    n_results: int = 5


class DeleteRequest(BaseModel):
    repo_id: str


def _get_collection(request: Request):
    client = request.app.state.chroma
    ef = request.app.state.ef
    return client.get_or_create_collection(
        name="pod-memory",
        embedding_function=ef,
    )


@router.post("/index")
def index_repo(body: IndexRequest, request: Request):
    collection = _get_collection(request)
    count = indexer.index_repo(
        repo_path=body.repo_path,
        repo_id=body.repo_id,
        collection=collection,
        ef=request.app.state.ef,
    )
    return {"indexed": count, "repo_id": body.repo_id}


@router.post("/query")
def query_repo(body: QueryRequest, request: Request):
    collection = _get_collection(request)
    results = retriever.query(
        repo_id=body.repo_id,
        text=body.query,
        collection=collection,
        n_results=body.n_results,
    )
    return {"results": results}


@router.delete("/index")
def delete_index(body: DeleteRequest, request: Request):
    collection = _get_collection(request)
    collection.delete(where={"repo": body.repo_id})
    return {"deleted": True, "repo_id": body.repo_id}
