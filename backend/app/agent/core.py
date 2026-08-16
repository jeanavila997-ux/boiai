"""
Agent Core — cérebro do BoiAI usado igualmente pelo chat web e pelo CLI.

Pipeline por mensagem:
  1. carrega persona + config de memória da fazenda
  2. recall de memórias (semântica + fixadas) e busca RAG
  3. monta system prompt composto
  4. chama o modelo Ollama com tool calling (loop LangGraph)
  5. persiste a conversa; extrai fatos para memória (se habilitado)

Escritas no banco passam por confirmação humana antes da execução.
"""
from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

from ..db import execute, fetch_all, fetch_one
from ..services import rag
from ..services.ollama import stream_chat
from ..mcp_server import tools as boiai_tools
from . import memory as mem_store, persona as persona_store
from .prompts import montar_system_prompt

# Catálogo de ferramentas disponíveis para o modelo (function calling)
TOOL_SPECS = [
    {"name": "query_db", "fn": boiai_tools.query_db,
     "description": "Consulta SQL somente leitura no banco da fazenda",
     "parameters": {"sql": "string", "limite": "integer"}},
    {"name": "get_animal", "fn": boiai_tools.get_animal,
     "description": "Busca animal por nome/brinco/registro com pedigree e DEPs",
     "parameters": {"termo": "string"}},
    {"name": "simular_cruzamento", "fn": boiai_tools.simular_cruzamento,
     "description": "Simula acasalamento touro × fêmea com score composto",
     "parameters": {"sire_id": "string", "dam_id": "string",
                    "programa": "string", "perfil": "string"}},
    {"name": "listar_lotes", "fn": boiai_tools.listar_lotes,
     "description": "Lista lotes de compra recentes",
     "parameters": {"dias": "integer"}},
    {"name": "status_rebanho", "fn": boiai_tools.status_rebanho,
     "description": "Resumo do rebanho: totais, avaliações, lotes",
     "parameters": {}},
    {"name": "buscar_conhecimento", "fn": rag.search_knowledge,
     "description": "Busca semântica na base de conhecimento técnico",
     "parameters": {"query": "string"}},
]

# Tools que escrevem no banco — exigem confirmação explícita
TOOLS_ESCRITA = {"registrar_pesagem"}


def criar_sessao(farm_id: str, user_id: str | None = None,
                 persona_id: str | None = None, canal: str = "web") -> str:
    sid = str(uuid.uuid4())
    execute(
        """INSERT INTO chat_session (id, farm_id, user_id, persona_id, canal)
           VALUES (:id, :f, :u, :p, :c)""",
        {"id": sid, "f": farm_id, "u": user_id, "p": persona_id, "c": canal},
    )
    return sid


def _historico(session_id: str, limite: int) -> list[dict]:
    rows = fetch_all(
        """SELECT role, content FROM chat_message
           WHERE session_id = :s AND role IN ('user','assistant')
           ORDER BY created_at DESC LIMIT :n""",
        {"s": session_id, "n": limite},
    )
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def _salvar_msg(session_id: str, role: str, content: str,
                thinking: str | None = None, tool_calls: list | None = None) -> None:
    execute(
        """INSERT INTO chat_message (session_id, role, content, thinking, tool_calls)
           VALUES (:s, :r, :c, :t, CAST(:tc AS JSON))""",
        {"s": session_id, "r": role, "c": content, "t": thinking,
         "tc": json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None},
    )


async def responder(farm_id: str, session_id: str, texto: str,
                    user_id: str | None = None) -> AsyncIterator[dict]:
    """
    Gera deltas de streaming: {"type": "delta", "content": ...},
    {"type": "thinking", "content": ...}, {"type": "tool", ...},
    {"type": "done"}.
    """
    sessao = fetch_one("SELECT * FROM chat_session WHERE id = :s", {"s": session_id})
    if not sessao:
        raise ValueError("Sessão não encontrada.")

    cfg = mem_store.get_config(farm_id)
    persona = persona_store.obter(sessao["persona_id"]) if sessao.get("persona_id") else None

    # Recall: memória semântica + RAG (paralelizável)
    memorias, docs = [], []
    if cfg["memoria_semantica_on"]:
        memorias = await rag.recall(farm_id, texto, top_k=5)
    docs = await rag.search_knowledge(texto, top_k=cfg["rag_top_k"], farm_id=farm_id)

    system = montar_system_prompt(
        persona_prompt=persona["system_prompt"] if persona else None,
        memorias=memorias if cfg["memoria_semantica_on"] else None,
        docs_rag=docs,
    )

    mensagens: list[dict] = [{"role": "system", "content": system}]
    if cfg["memoria_sessao_on"]:
        mensagens += _historico(session_id, cfg["janela_contexto_msgs"])
    mensagens.append({"role": "user", "content": texto})
    _salvar_msg(session_id, "user", texto)

    think: bool | str | None = None
    if persona and persona.get("think_level"):
        tl = persona["think_level"]
        think = {"false": False, "true": True}.get(tl, tl)

    modelo = (persona or {}).get("modelo")  # None = modelo padrão do settings

    content_acc, thinking_acc = "", ""
    async for delta in stream_chat(mensagens, model=modelo, think=think):
        if "content" in delta:
            content_acc += delta["content"]
            yield {"type": "delta", "content": delta["content"]}
        if "thinking" in delta:
            thinking_acc += delta["thinking"]
            yield {"type": "thinking", "content": delta["thinking"]}

    _salvar_msg(session_id, "assistant", content_acc, thinking_acc or None)
    yield {"type": "done"}

    # TODO(Fase 4): tool calling loop via LangGraph (create_react_agent +
    # ChatOllama.bind_tools(TOOL_SPECS)) e extração automática de fatos
    # para agent_memory quando cfg["extracao_automatica"].
