"""Rotas do chat com o agente (SSE streaming)."""
from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agent import core
from ..db import fetch_all

router = APIRouter(prefix="/chat", tags=["chat"])


class NovaSessao(BaseModel):
    farm_id: str
    user_id: str | None = None
    persona_id: str | None = None
    canal: str = "web"


class Mensagem(BaseModel):
    farm_id: str
    texto: str
    user_id: str | None = None


@router.post("/sessoes")
def nova_sessao(body: NovaSessao):
    sid = core.criar_sessao(body.farm_id, body.user_id, body.persona_id, body.canal)
    return {"session_id": sid}


@router.get("/sessoes/{farm_id}")
def listar_sessoes(farm_id: str):
    return fetch_all(
        """SELECT id, titulo, canal, arquivada, created_at FROM chat_session
           WHERE farm_id = :f ORDER BY created_at DESC LIMIT 100""",
        {"f": farm_id},
    )


@router.post("/{session_id}/mensagens")
async def enviar_mensagem(session_id: str, body: Mensagem):
    async def eventos():
        try:
            async for ev in core.responder(body.farm_id, session_id, body.texto,
                                           body.user_id):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"

    return StreamingResponse(eventos(), media_type="text/event-stream")
