from __future__ import annotations

from pod_memory import indexer, retriever


# ── Test 1: indexer + retriever directly (no HTTP, no FastAPI) ───────────────

def test_index_and_query(sample_repo, collection, ef):
    """Index real files into a real ChromaDB and verify semantic search works."""
    repo_id = "org/test-app"

    count = indexer.index_repo(
        repo_path=str(sample_repo),
        repo_id=repo_id,
        collection=collection,
        ef=ef,
    )
    assert count > 0

    results = retriever.query(
        repo_id=repo_id,
        text="user login authentication",
        collection=collection,
        n_results=3,
    )

    assert len(results) > 0
    paths = [r["path"] for r in results]
    # auth.py should rank highest for an auth query
    assert any("auth" in p for p in paths), f"Expected auth.py in results, got: {paths}"
    assert all("content" in r and "distance" in r for r in results)


# ── Test 2: full API flow via HTTP (index → query → delete → query empty) ────

def test_full_api_flow(api_client, sample_repo):
    """End-to-end: POST /index, POST /query, DELETE /index, confirm deletion."""
    repo_id = "org/api-test"

    # Index
    r = api_client.post("/index", json={"repo_path": str(sample_repo), "repo_id": repo_id})
    assert r.status_code == 200
    body = r.json()
    assert body["repo_id"] == repo_id
    assert body["indexed"] > 0

    # Query
    r = api_client.post(
        "/query",
        json={"repo_id": repo_id, "query": "database connection", "n_results": 3},
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) > 0
    assert any("database" in res["path"] for res in results)

    # Delete
    r = api_client.request(
        "DELETE",
        "/index",
        json={"repo_id": repo_id},
    )
    assert r.status_code == 200
    assert r.json()["deleted"] is True

    # Query after delete — must return empty
    r = api_client.post(
        "/query",
        json={"repo_id": repo_id, "query": "database connection", "n_results": 3},
    )
    assert r.status_code == 200
    assert r.json()["results"] == []


# ── Test 3: repo isolation — querying a different repo_id returns nothing ─────

def test_repo_isolation(sample_repo, collection, ef):
    """Documents indexed under one repo_id must not appear in another repo's query."""
    indexer.index_repo(
        repo_path=str(sample_repo),
        repo_id="org/real-repo",
        collection=collection,
        ef=ef,
    )

    results = retriever.query(
        repo_id="org/different-repo",
        text="authentication",
        collection=collection,
        n_results=5,
    )
    assert results == []
