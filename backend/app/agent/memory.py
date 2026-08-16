"""Gestão de memória do agente: 3 camadas configuráveis por fazenda."""
from __future__ import annotations

from ..db import execute, fetch_all, fetch_one

DEFAULT_CONFIG = {
    "memoria_sessao_on": 1,
    "memoria_perfil_on": 1,
    "memoria_semantica_on": 1,
    "extracao_automatica": 1,
    "janela_contexto_msgs": 20,
    "rag_top_k": 5,
}


def get_config(farm_id: str) -> dict:
    row = fetch_one("SELECT * FROM agent_config WHERE farm_id = :f", {"f": farm_id})
    if row:
        return {**DEFAULT_CONFIG, **row}
    execute("INSERT INTO agent_config (farm_id) VALUES (:f)", {"f": farm_id})
    return DEFAULT_CONFIG.copy()


def update_config(farm_id: str, **campos) -> dict:
    get_config(farm_id)  # garante existência
    if campos:
        sets = ", ".join(f"{k} = :{k}" for k in campos)
        execute(f"UPDATE agent_config SET {sets} WHERE farm_id = :f",
                {**campos, "f": farm_id})
    return get_config(farm_id)


def listar(farm_id: str, tipo: str | None = None) -> list[dict]:
    sql = """SELECT id, tipo, conteudo, fixada, expira_em, origem, created_at
             FROM agent_memory WHERE farm_id = :f"""
    params: dict = {"f": farm_id}
    if tipo:
        sql += " AND tipo = :t"
        params["t"] = tipo
    return fetch_all(sql + " ORDER BY fixada DESC, created_at DESC", params)


def esquecer(mem_id: str, farm_id: str) -> bool:
    # TODO: remover também o vetor do Qdrant (coleção agent_memory)
    return execute(
        "DELETE FROM agent_memory WHERE id = :id AND farm_id = :f",
        {"id": mem_id, "f": farm_id},
    ) > 0


def fixar(mem_id: str, farm_id: str, fixada: bool = True) -> bool:
    return execute(
        "UPDATE agent_memory SET fixada = :v WHERE id = :id AND farm_id = :f",
        {"v": 1 if fixada else 0, "id": mem_id, "f": farm_id},
    ) > 0
