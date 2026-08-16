"""BoiAI Backend — ponto de entrada FastAPI."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import agent_config, animals, chat, imports
from .config import settings
from .services import rag
from .services.ollama import list_models

app = FastAPI(title="BoiAI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringir em produção
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(animals.router)
app.include_router(chat.router)
app.include_router(agent_config.router)
app.include_router(imports.router)


@app.on_event("startup")
def startup() -> None:
    rag.ensure_collections()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ollama_models": await list_models(),
        "modelo_padrao": settings.ollama_chat_model,
        "embed_model": settings.ollama_embed_model,
    }
