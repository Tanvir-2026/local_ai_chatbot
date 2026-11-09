from app.core.config import settings
from app.services import ollama_service

_collection = None


def _get_collection():
    """Opens ChromaDB on first use (the import is slow, so it is lazy)."""
    global _collection
    if _collection is None:
        import chromadb

        client = chromadb.PersistentClient(path=settings.chroma_path)
        _collection = client.get_or_create_collection(
            name="messages", metadata={"hnsw:space": "cosine"}
        )
    return _collection


def add_messages(conversation_id: str, messages: list[dict]) -> None:
    """messages: [{"id": int, "role": str, "content": str}]"""
    _get_collection().add(
        ids=[f"{conversation_id}:{m['id']}" for m in messages],
        embeddings=[ollama_service.embed(m["content"]) for m in messages],
        documents=[m["content"] for m in messages],
        metadatas=[
            {"conversation_id": conversation_id, "role": m["role"], "message_id": m["id"]}
            for m in messages
        ],
    )


def search(
    conversation_id: str, query: str, n_results: int, max_distance: float
) -> list[dict]:
    """Messages of one conversation closest in meaning to `query`, best match first."""
    res = _get_collection().query(
        query_embeddings=[ollama_service.embed(query)],
        n_results=n_results,
        where={"conversation_id": conversation_id},
    )
    hits = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        if dist <= max_distance:
            hits.append(
                {"role": meta["role"], "content": doc, "message_id": meta["message_id"]}
            )
    return hits


def delete_conversation(conversation_id: str) -> None:
    _get_collection().delete(where={"conversation_id": conversation_id})