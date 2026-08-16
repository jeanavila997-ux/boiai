"""
Cliente Ollama assíncrono — equivalente ao ollamaClient.ts do CattleGen.
Streaming SSE no endpoint OpenAI-compatível (/v1/chat/completions),
suporte a thinking/reasoning_content, listagem de modelos e embeddings.
"""
from __future__ import annotations

import json
from typing import AsyncIterator, Optional

import httpx

from ..config import settings


async def stream_chat(
    messages: list[dict],
    model: Optional[str] = None,
    think: bool | str | None = None,
) -> AsyncIterator[dict]:
    """
    Gera deltas {"content": ...} e/ou {"thinking": ...} conforme chegam.
    """
    base = settings.ollama_base_url.rstrip("/")
    body: dict = {
        "model": model or settings.ollama_chat_model,
        "messages": messages,
        "stream": True,
    }
    if think is not None:
        body["think"] = think

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        async with client.stream(
            "POST", f"{base}/v1/chat/completions", json=body
        ) as res:
            if res.status_code != 200:
                detail = (await res.aread()).decode(errors="replace")[:300]
                raise RuntimeError(
                    f"Ollama respondeu {res.status_code}. {detail} "
                    "Verifique se o daemon está ativo (ollama serve)."
                )
            async for line in res.aiter_lines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    return
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue  # linha parcial/keep-alive
                choice = (data.get("choices") or [{}])[0]
                delta = choice.get("delta") or {}
                out: dict = {}
                if delta.get("content"):
                    out["content"] = delta["content"]
                # reasoning_content: padrão DeepSeek; thinking: padrão Ollama/Qwen/Llama
                thinking = delta.get("thinking") or delta.get("reasoning_content")
                if thinking:
                    out["thinking"] = thinking
                if out:
                    yield out


async def list_models() -> list[str]:
    base = settings.ollama_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(f"{base}/v1/models")
            res.raise_for_status()
            return [m["id"] for m in res.json().get("data", [])]
    except Exception:
        return [settings.ollama_chat_model]


async def embed(texts: list[str], model: Optional[str] = None) -> list[list[float]]:
    """Gera embeddings via /api/embed (nativo Ollama)."""
    base = settings.ollama_base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=120.0) as client:
        res = await client.post(
            f"{base}/api/embed",
            json={"model": model or settings.ollama_embed_model, "input": texts},
        )
        res.raise_for_status()
        return res.json()["embeddings"]
