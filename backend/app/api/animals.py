"""CRUD de animais + avaliações (Fase 1 — expandir)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import execute, fetch_all, fetch_one
from ..mcp_server.tools import get_animal, simular_cruzamento

router = APIRouter(prefix="/animais", tags=["animais"])


class AnimalIn(BaseModel):
    farm_id: str
    nome_exibicao: str
    sexo: str  # M | F
    raca: str
    categoria: str | None = None
    registro_composto: str | None = None
    data_nascimento: str | None = None
    observacoes: str | None = None


@router.get("")
def listar(farm_id: str, status: str = "ativo", busca: str | None = None):
    sql = """SELECT id, nome_exibicao, sexo, raca, categoria, registro_composto,
                    data_nascimento, status FROM animal
             WHERE farm_id = :f AND status = :s"""
    params: dict = {"f": farm_id, "s": status}
    if busca:
        sql += " AND (nome_exibicao LIKE :b OR registro_composto LIKE :b OR rgd LIKE :b)"
        params["b"] = f"%{busca}%"
    return fetch_all(sql + " ORDER BY nome_exibicao LIMIT 200", params)


@router.post("", status_code=201)
def criar(body: AnimalIn):
    aid = str(uuid.uuid4())
    execute(
        """INSERT INTO animal (id, farm_id, nome_exibicao, sexo, raca, categoria,
                               registro_composto, data_nascimento, observacoes)
           VALUES (:id, :f, :nome, :sexo, :raca, :cat, :reg, :nasc, :obs)""",
        {"id": aid, "f": body.farm_id, "nome": body.nome_exibicao, "sexo": body.sexo,
         "raca": body.raca, "cat": body.categoria, "reg": body.registro_composto,
         "nasc": body.data_nascimento, "obs": body.observacoes},
    )
    return {"id": aid}


@router.get("/buscar/{termo}")
def detalhe(termo: str, farm_id: str):
    animal = get_animal(termo, farm_id)
    if not animal:
        raise HTTPException(404, "Animal não encontrado.")
    return animal


class SimulacaoIn(BaseModel):
    sire_id: str
    dam_id: str
    programa: str = "GENEPLUS"
    perfil: str = "REPOSICAO"
    politica: str = "MEDIA_DISPONIVEL"


@router.post("/simular-cruzamento")
def simular(body: SimulacaoIn):
    return simular_cruzamento(body.sire_id, body.dam_id, body.programa,
                              body.perfil, body.politica)
