"""Rotas de configuração do agente: memórias, personas, parâmetros."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..agent import memory as mem_store, persona as persona_store
from ..services import rag

router = APIRouter(prefix="/agente", tags=["agente"])


# ---------- Configuração ----------

@router.get("/config/{farm_id}")
def get_config(farm_id: str):
    return mem_store.get_config(farm_id)


class ConfigIn(BaseModel):
    memoria_sessao_on: bool | None = None
    memoria_perfil_on: bool | None = None
    memoria_semantica_on: bool | None = None
    extracao_automatica: bool | None = None
    janela_contexto_msgs: int | None = None
    rag_top_k: int | None = None


@router.put("/config/{farm_id}")
def put_config(farm_id: str, body: ConfigIn):
    campos = {k: (1 if isinstance(v, bool) and v else 0 if isinstance(v, bool) else v)
              for k, v in body.model_dump(exclude_none=True).items()}
    return mem_store.update_config(farm_id, **campos)


# ---------- Memórias ----------

@router.get("/memorias/{farm_id}")
def listar_memorias(farm_id: str, tipo: str | None = None):
    return mem_store.listar(farm_id, tipo)


class MemoriaIn(BaseModel):
    tipo: str = "fato"  # perfil | fato | preferencia | decisao
    conteudo: str
    user_id: str | None = None


@router.post("/memorias/{farm_id}", status_code=201)
async def criar_memoria(farm_id: str, body: MemoriaIn):
    mem_id = await rag.remember(farm_id, body.tipo, body.conteudo, body.user_id)
    return {"id": mem_id}


@router.delete("/memorias/{farm_id}/{mem_id}")
def apagar_memoria(farm_id: str, mem_id: str):
    if not mem_store.esquecer(mem_id, farm_id):
        raise HTTPException(404, "Memória não encontrada.")
    return {"ok": True}


@router.post("/memorias/{farm_id}/{mem_id}/fixar")
def fixar_memoria(farm_id: str, mem_id: str, fixada: bool = True):
    if not mem_store.fixar(mem_id, farm_id, fixada):
        raise HTTPException(404, "Memória não encontrada.")
    return {"ok": True, "fixada": fixada}


# ---------- Personas ----------

@router.get("/personas/{farm_id}")
def listar_personas(farm_id: str):
    return persona_store.listar(farm_id)


class PersonaIn(BaseModel):
    nome: str
    system_prompt: str
    descricao: str | None = None
    tom: str = "direto"
    verbosidade: str = "medio"
    proatividade: str = "sugere"
    modelo: str | None = None
    think_level: str = "medium"
    tools_ativas: list[str] | None = None


@router.post("/personas/{farm_id}", status_code=201)
def criar_persona(farm_id: str, body: PersonaIn):
    pid = persona_store.criar(farm_id, **body.model_dump())
    return {"id": pid}


@router.put("/personas/{persona_id}")
def atualizar_persona(persona_id: str, body: PersonaIn):
    if not persona_store.atualizar(persona_id, **body.model_dump()):
        raise HTTPException(404, "Persona não encontrada.")
    return {"ok": True}


@router.delete("/personas/{persona_id}")
def excluir_persona(persona_id: str):
    if not persona_store.excluir(persona_id):
        raise HTTPException(404, "Persona não encontrada ou é padrão.")
    return {"ok": True}
