from __future__ import annotations

import chromadb


def query(
    repo_id: str,
    text: str,
    collection: chromadb.Collection,
    n_results: int = 5,
) -> list[dict]:
    results = collection.query(
        query_texts=[text],
        n_results=n_results,
        where={"repo": repo_id},
        include=["documents", "metadatas", "distances"],
    )
    output: list[dict] = []
    docs = results.get("documents") or [[]]
    metas = results.get("metadatas") or [[]]
    dists = results.get("distances") or [[]]
    for doc, meta, dist in zip(docs[0], metas[0], dists[0]):
        output.append({"path": meta.get("path", ""), "content": doc, "distance": dist})
    return output
