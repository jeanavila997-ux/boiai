"""Personas do agente: personalidades configuráveis por fazenda/usuário."""
from __future__ import annotations

import uuid

from ..db import execute, fetch_all, fetch_one


def listar(farm_id: str | None = None) -> list[dict]:
    """Personas globais + da fazenda."""
    if farm_id:
        return fetch_all(
            """SELECT * FROM agent_persona
               WHERE farm_id IS NULL OR farm_id = :f
               ORDER BY is_default DESC, nome""",
            {"f": farm_id},
        )
    return fetch_all("SELECT * FROM agent_persona WHERE farm_id IS NULL ORDER BY nome")


def obter(persona_id: str) -> dict | None:
    return fetch_one("SELECT * FROM agent_persona WHERE id = :id", {"id": persona_id})


def criar(farm_id: str, nome: str, system_prompt: str, descricao: str | None = None,
          tom: str = "direto", verbosidade: str = "medio",
          proatividade: str = "sugere", modelo: str | None = None,
          think_level: str = "medium", tools_ativas: list[str] | None = None) -> str:
    import json
    pid = str(uuid.uuid4())
    execute(
        """INSERT INTO agent_persona
             (id, farm_id, nome, descricao, system_prompt, tom, verbosidade,
              proatividade, modelo, think_level, tools_ativas)
           VALUES (:id, :f, :nome, :desc, :sp, :tom, :verb, :proat, :modelo, :think,
                   CAST(:tools AS JSON))""",
        {"id": pid, "f": farm_id, "nome": nome, "desc": descricao, "sp": system_prompt,
         "tom": tom, "verb": verbosidade, "proat": proatividade, "modelo": modelo,
         "think": think_level,
         "tools": json.dumps(tools_ativas) if tools_ativas else None},
    )
    return pid


def atualizar(persona_id: str, **campos) -> bool:
    permitidos = {"nome", "descricao", "system_prompt", "tom", "verbosidade",
                  "proatividade", "modelo", "think_level", "tools_ativas"}
    dados = {k: v for k, v in campos.items() if k in permitidos}
    if not dados:
        return False
    if "tools_ativas" in dados and isinstance(dados["tools_ativas"], list):
        import json
        dados["tools_ativas"] = json.dumps(dados["tools_ativas"], ensure_ascii=False)
    sets = ", ".join(f"{k} = :{k}" for k in dados)
    return execute(f"UPDATE agent_persona SET {sets} WHERE id = :id",
                   {**dados, "id": persona_id}) > 0


def excluir(persona_id: str) -> bool:
    return execute("DELETE FROM agent_persona WHERE id = :id AND is_default = 0",
                   {"id": persona_id}) > 0
