"""
RAG — ingestão e busca de conhecimento + memória semântica.
Embeddings via Ollama (bge-m3); vetores no Qdrant; metadados no MySQL.
"""
from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from ..config import settings
from ..db import execute, fetch_all
from .ollama import embed

_client: QdrantClient | None = None


def qdrant() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def ensure_collections() -> None:
    q = qdrant()
    for col in (settings.qdrant_col_knowledge, settings.qdrant_col_memory):
        if not q.collection_exists(col):
            q.create_collection(
                col,
                vectors_config=VectorParams(size=settings.embed_dim, distance=Distance.COSINE),
            )


# ---------- Conhecimento (RAG) ----------

async def ingest_document(farm_id: str | None, fonte: str, titulo: str,
                          conteudo: str, url: str | None = None,
                          metadata: dict | None = None) -> str:
    """Grava o chunk no MySQL e o embedding no Qdrant."""
    doc_id = str(uuid.uuid4())
    execute(
        """INSERT INTO knowledge_document (id, farm_id, fonte, titulo, conteudo, url, metadata)
           VALUES (:id, :farm_id, :fonte, :titulo, :conteudo, :url, CAST(:metadata AS JSON))""",
        {"id": doc_id, "farm_id": farm_id, "fonte": fonte, "titulo": titulo,
         "conteudo": conteudo, "url": url, "metadata": _json(metadata or {})},
    )
    [vec] = await embed([f"{titulo}\n\n{conteudo}"])
    qdrant().upsert(
        settings.qdrant_col_knowledge,
        [PointStruct(id=doc_id, vector=vec,
                     payload={"farm_id": farm_id, "fonte": fonte, "titulo": titulo})],
    )
    return doc_id


async def search_knowledge(query: str, top_k: int = 5,
                           farm_id: str | None = None) -> list[dict]:
    """Busca semântica: retorna chunks com conteúdo e score."""
    [vec] = await embed([query])
    hits = qdrant().query_points(
        settings.qdrant_col_knowledge, query=vec, limit=top_k, with_payload=True
    ).points
    if not hits:
        return []
    ids = [str(h.id) for h in hits]
    placeholders = ",".join(f":id{i}" for i in range(len(ids)))
    rows = fetch_all(
        f"""SELECT id, fonte, titulo, conteudo, url FROM knowledge_document
            WHERE id IN ({placeholders})""",
        {f"id{i}": v for i, v in enumerate(ids)},
    )
    by_id = {r["id"]: r for r in rows}
    return [
        {**by_id[str(h.id)], "score": h.score}
        for h in hits if str(h.id) in by_id
    ]


# ---------- Memória semântica ----------

async def remember(farm_id: str, tipo: str, conteudo: str,
                   user_id: str | None = None, origem: str = "manual") -> str:
    mem_id = str(uuid.uuid4())
    execute(
        """INSERT INTO agent_memory (id, farm_id, user_id, tipo, conteudo, origem)
           VALUES (:id, :farm_id, :user_id, :tipo, :conteudo, :origem)""",
        {"id": mem_id, "farm_id": farm_id, "user_id": user_id,
         "tipo": tipo, "conteudo": conteudo, "origem": origem},
    )
    [vec] = await embed([conteudo])
    qdrant().upsert(
        settings.qdrant_col_memory,
        [PointStruct(id=mem_id, vector=vec,
                     payload={"farm_id": farm_id, "tipo": tipo})],
    )
    return mem_id


async def recall(farm_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Recupera memórias relevantes (fixadas sempre entram)."""
    fixadas = fetch_all(
        """SELECT id, tipo, conteudo FROM agent_memory
           WHERE farm_id = :f AND fixada = 1
             AND (expira_em IS NULL OR expira_em >= CURDATE())""",
        {"f": farm_id},
    )
    [vec] = await embed([query])
    hits = qdrant().query_points(
        settings.qdrant_col_memory, query=vec, limit=top_k, with_payload=True
    ).points
    semanticas: list[dict] = []
    if hits:
        ids = [str(h.id) for h in hits]
        placeholders = ",".join(f":id{i}" for i in range(len(ids)))
        rows = fetch_all(
            f"""SELECT id, tipo, conteudo FROM agent_memory
                WHERE id IN ({placeholders}) AND farm_id = :f
                  AND (expira_em IS NULL OR expira_em >= CURDATE())""",
            {**{f"id{i}": v for i, v in enumerate(ids)}, "f": farm_id},
        )
        by_id = {r["id"]: r for r in rows}
        semanticas = [
            {**by_id[str(h.id)], "score": h.score}
            for h in hits if str(h.id) in by_id
        ]
    vistos = {m["id"] for m in semanticas}
    return semanticas + [m for m in fixadas if m["id"] not in vistos]


def _json(d: dict) -> str:
    import json
    return json.dumps(d, ensure_ascii=False)
