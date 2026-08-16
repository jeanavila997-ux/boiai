"""Importador: MySQL externo (Hostinger/legado), dumps .sql e planilhas.
Fluxo: conectar → inspecionar → mapear → dry-run → executar (transação)."""
from __future__ import annotations

import uuid

import pymysql
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import execute, fetch_one

router = APIRouter(prefix="/importar", tags=["importacao"])


class ConexaoMysql(BaseModel):
    farm_id: str
    host: str
    port: int = 3306
    user: str
    password: str
    database: str


def _conectar(c: ConexaoMysql) -> pymysql.connections.Connection:
    try:
        return pymysql.connect(host=c.host, port=c.port, user=c.user,
                               password=c.password, database=c.database,
                               connect_timeout=10, charset="utf8mb4")
    except pymysql.MySQLError as e:
        raise HTTPException(502, f"Falha ao conectar no MySQL externo: {e}")


@router.post("/mysql/inspecionar")
def inspecionar_mysql(body: ConexaoMysql):
    """Lista tabelas e colunas do banco de origem."""
    with _conectar(body) as conn, conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        tabelas = [r[0] for r in cur.fetchall()]
        estrutura = {}
        for t in tabelas:
            cur.execute(f"DESCRIBE `{t}`")
            estrutura[t] = [
                {"coluna": r[0], "tipo": r[1], "nulo": r[2], "chave": r[3]}
                for r in cur.fetchall()
            ]
            cur.execute(f"SELECT COUNT(*) FROM `{t}`")
            estrutura[t].append({"_linhas": cur.fetchone()[0]})
    return {"tabelas": tabelas, "estrutura": estrutura}


class JobIn(BaseModel):
    farm_id: str
    origem_tipo: str  # mysql | mysql_dump | excel | csv | indexeddb_json
    origem_detalhe: str | None = None


@router.post("/jobs", status_code=201)
def criar_job(body: JobIn):
    jid = str(uuid.uuid4())
    execute(
        """INSERT INTO import_job (id, farm_id, origem_tipo, origem_detalhe, status)
           VALUES (:id, :f, :t, :d, 'mapeando')""",
        {"id": jid, "f": body.farm_id, "t": body.origem_tipo, "d": body.origem_detalhe},
    )
    return {"job_id": jid}


@router.get("/jobs/{job_id}")
def status_job(job_id: str):
    job = fetch_one("SELECT * FROM import_job WHERE id = :id", {"id": job_id})
    if not job:
        raise HTTPException(404, "Job não encontrado.")
    return job


# TODO(Fase 1): endpoints de mapeamento coluna-a-coluna (com sugestão do
# agente de IA), dry-run com relatório de validação e execução em transação
# com rollback — espelhando a trilha em import_job.relatorio.
