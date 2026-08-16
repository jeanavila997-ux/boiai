"""
Ferramentas do BoiAI — usadas pelo agente interno E expostas via MCP.
Escritas sempre pedem confirmação humana na camada do agente.
"""
from __future__ import annotations

import re

from ..db import execute, fetch_all, fetch_one
from ..services.scoring import (
    EvaluationTrait, calcular_cruzamento, PoliticaAusencia, PerfilObjetivo,
)

_SQL_BLOQUEADO = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b", re.I
)


def query_db(sql: str, farm_id: str | None = None, limite: int = 50) -> list[dict]:
    """Consulta SOMENTE LEITURA no banco da fazenda (SELECT/WITH)."""
    if _SQL_BLOQUEADO.search(sql):
        raise ValueError("Apenas consultas de leitura (SELECT) são permitidas.")
    if not re.match(r"^\s*(SELECT|WITH|SHOW|DESCRIBE|EXPLAIN)\b", sql, re.I):
        raise ValueError("A consulta deve começar com SELECT, WITH, SHOW, DESCRIBE ou EXPLAIN.")
    if "limit" not in sql.lower():
        sql = f"{sql.rstrip().rstrip(';')} LIMIT {int(limite)}"
    return fetch_all(sql)


def get_animal(termo: str, farm_id: str) -> dict | None:
    """Busca animal por nome, brinco/registro ou id, com pedigree."""
    animal = fetch_one(
        """SELECT * FROM animal
           WHERE farm_id = :f AND (
                 id = :t OR nome_exibicao LIKE :like OR rgd = :t
                 OR rgn = :t OR registro_composto = :t)
           LIMIT 1""",
        {"f": farm_id, "t": termo, "like": f"%{termo}%"},
    )
    if not animal:
        return None
    animal["pedigree"] = fetch_all(
        "SELECT relation_type, related_name, related_animal_id FROM animal_relation WHERE animal_id = :a",
        {"a": animal["id"]},
    )
    animal["avaliacoes"] = fetch_all(
        """SELECT e.programa, e.edicao, e.indice_resumo_nome, e.indice_resumo_valor,
                  t.code, t.value, t.accuracy, t.rank_type, t.rank_value
           FROM evaluation e
           LEFT JOIN evaluation_trait t ON t.evaluation_id = e.id
           WHERE e.animal_id = :a ORDER BY e.data_ref DESC""",
        {"a": animal["id"]},
    )
    return animal


def _carregar_traits(animal_id: str, programa: str) -> dict[str, EvaluationTrait]:
    """Carrega DEPs do animal mapeadas para concept_key via trait_dictionary."""
    rows = fetch_all(
        """SELECT td.concept_key, t.value, t.accuracy, t.rank_type, t.rank_value
           FROM evaluation e
           JOIN evaluation_trait t ON t.evaluation_id = e.id
           JOIN trait_dictionary td
             ON (td.code_geneplus = t.code AND e.programa = 'GENEPLUS')
             OR (td.code_pmgz = t.code AND e.programa = 'PMGZ')
             OR (td.code_ancp = t.code AND e.programa = 'ANCP')
           WHERE e.animal_id = :a AND e.programa = :p
           ORDER BY e.data_ref DESC""",
        {"a": animal_id, "p": programa},
    )
    return {
        r["concept_key"]: EvaluationTrait(
            code=r["concept_key"], value=r["value"], accuracy=r["accuracy"],
            rank_type=r["rank_type"] or "NENHUM", rank_value=r["rank_value"],
        )
        for r in rows
    }


def simular_cruzamento(sire_id: str, dam_id: str, programa: str,
                       perfil: PerfilObjetivo = "REPOSICAO",
                       politica: PoliticaAusencia = "MEDIA_DISPONIVEL") -> dict:
    """Roda o motor de scoring para um par touro × fêmea."""
    sire = fetch_one("SELECT consanguinidade_pct FROM animal WHERE id = :i", {"i": sire_id})
    result = calcular_cruzamento(
        _carregar_traits(sire_id, programa),
        _carregar_traits(dam_id, programa),
        perfil=perfil, politica=politica,
        consanguinidade_pct=sire["consanguinidade_pct"] if sire else None,
    )
    return {
        "score_composto": result.score_composto,
        "confianca_media": result.confianca_media,
        "coverage_pct": result.coverage_pct,
        "alertas": result.alertas,
        "politica_usada": result.politica_usada,
        "traits": [t.__dict__ for t in result.traits],
    }


def listar_lotes(farm_id: str, dias: int = 90) -> list[dict]:
    return fetch_all(
        """SELECT l.id, l.data, l.nome_lote, l.origem, p.nome AS produtor,
                  COUNT(i.id) AS animais, SUM(i.valor_total) AS valor_total
           FROM lote_compra l
           LEFT JOIN produtor p ON p.id = l.produtor_id
           LEFT JOIN item_lote i ON i.lote_id = l.id
           WHERE l.farm_id = :f AND l.data >= DATE_SUB(CURDATE(), INTERVAL :dias DAY)
           GROUP BY l.id ORDER BY l.data DESC""",
        {"f": farm_id, "dias": dias},
    )


def registrar_pesagem(animal_id: str, peso_kg: float, data: str,
                      origem: str = "balanca", observacoes: str | None = None) -> str:
    """ESCRITA: registra pesagem. O agente deve confirmar antes de chamar."""
    execute(
        """INSERT INTO pesagem (animal_id, data, peso_kg, origem, observacoes)
           VALUES (:a, :d, :p, :o, :obs)""",
        {"a": animal_id, "d": data, "p": peso_kg, "o": origem, "obs": observacoes},
    )
    return f"Pesagem de {peso_kg} kg registrada em {data}."


def status_rebanho(farm_id: str) -> dict:
    """Resumo: totais por categoria/sexo, avaliações e lotes recentes."""
    animais = fetch_all(
        """SELECT sexo, categoria, COUNT(*) AS total FROM animal
           WHERE farm_id = :f AND status = 'ativo' GROUP BY sexo, categoria""",
        {"f": farm_id},
    )
    avaliacoes = fetch_one(
        """SELECT COUNT(DISTINCT e.id) AS avaliacoes, COUNT(t.id) AS deps
           FROM evaluation e LEFT JOIN evaluation_trait t ON t.evaluation_id = e.id
           JOIN animal a ON a.id = e.animal_id WHERE a.farm_id = :f""",
        {"f": farm_id},
    )
    return {"animais_ativos": animais, **(avaliacoes or {}),
            "lotes_recentes": listar_lotes(farm_id, dias=30)}
