"""
Motor de Cruzamento — BoiAI
Port 1:1 do scoring.ts do CattleGen (src/lib/scoring.ts).

Regras preservadas:
- Nunca somar escalas heterogêneas.
- Valor esperado da progênie = (sire + dam) / 2, traço equivalente, mesmo programa/base.
- Score de decisão normalizado (0–100) e ponderado por objetivo.
- Tudo aceita nulo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

PoliticaAusencia = Literal["ESTRITA", "MEDIA_DISPONIVEL", "IMPUTACAO_MEDIA_PROGRAMA"]
PerfilObjetivo = Literal["NOVILHAS", "REPOSICAO", "TERMINAL"]

# Pesos por perfil de objetivo (idênticos ao CattleGen)
PERFIS: dict[str, list[tuple[str, float]]] = {
    "NOVILHAS": [
        ("IPP", 1.5), ("PES", 1.2), ("PE_450D", 1.0), ("HP_STAY", 1.2),
        ("TMD", 0.8), ("PN", 0.8), ("PD", 0.6), ("PS", 0.5),
        ("AOL", 0.3), ("EGS", 0.2), ("MAR", 0.2),
    ],
    "REPOSICAO": [
        ("TMD", 1.2), ("IPP", 1.0), ("PES", 1.0), ("HP_STAY", 1.0),
        ("PD", 0.8), ("PS", 0.7), ("PN", 0.7), ("AOL", 0.5),
        ("EGS", 0.3), ("MAR", 0.3), ("PE_450D", 0.5),
    ],
    "TERMINAL": [
        ("AOL", 1.5), ("EGS", 1.2), ("MAR", 1.2), ("PS", 1.0),
        ("PD", 0.8), ("PES", 0.6), ("PE_450D", 0.4), ("IPP", 0.3),
        ("HP_STAY", 0.4), ("TMD", 0.3), ("PN", 0.5),
    ],
}


@dataclass
class EvaluationTrait:
    """DEP de uma característica (espelha a tabela evaluation_trait)."""
    code: str = ""
    value: Optional[float] = None
    accuracy: Optional[float] = None
    rank_type: str = "NENHUM"          # PERCENTIL | DECA | TOP | CLASSE | NENHUM
    rank_value: Optional[float] = None


def clamp0100(val: float) -> float:
    return max(0.0, min(100.0, val))


def normalize(trait: Optional[EvaluationTrait],
              stats: Optional[dict] = None) -> Optional[float]:
    """Normaliza um traço para escala 0–100 (maior = melhor)."""
    if trait is None:
        return None
    if trait.rank_type == "PERCENTIL" and trait.rank_value is not None:
        return clamp0100(100 - trait.rank_value)
    if trait.rank_type == "TOP" and trait.rank_value is not None:
        return clamp0100(100 - trait.rank_value)
    if trait.rank_type == "DECA" and trait.rank_value is not None:
        return clamp0100((11 - trait.rank_value) * 10)
    if trait.value is not None and stats and stats.get("sd", 0) > 0:
        return clamp0100(50 + 10 * ((trait.value - stats["mean"]) / stats["sd"]))
    return None  # ausente


def expected_progeny(sire: Optional[EvaluationTrait],
                     dam: Optional[EvaluationTrait]) -> tuple[Optional[float], Optional[float]]:
    """Valor esperado da progênie = (pai + mãe)/2; confiança = média das acurácias."""
    sv = sire.value if sire else None
    dv = dam.value if dam else None
    expected = (sv + dv) / 2 if sv is not None and dv is not None else None
    sa = sire.accuracy if sire else None
    da = dam.accuracy if dam else None
    confidence = (sa + da) / 2 if sa is not None and da is not None else None
    return expected, confidence


def score_peso_nascer(expected_value: float, alvo_kg: float = 32.0) -> float:
    """Peso ao nascer: penaliza desvio do alvo em qualquer direção."""
    desvio = abs(expected_value - alvo_kg)
    k = 5  # penalidade por kg de desvio
    return clamp0100(100 - k * desvio)


@dataclass
class TraitResult:
    concept_key: str
    sire_value: Optional[float] = None
    dam_value: Optional[float] = None
    expected_value: Optional[float] = None
    normalized_score: Optional[float] = None
    weight: float = 0.0
    confidence: Optional[float] = None


@dataclass
class CruzamentoResult:
    score_composto: Optional[float] = None
    confianca_media: Optional[float] = None
    traits: list[TraitResult] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    coverage_pct: float = 0.0
    politica_usada: str = "MEDIA_DISPONIVEL"


def calcular_cruzamento(
    sire_traits: dict[str, EvaluationTrait],
    dam_traits: dict[str, EvaluationTrait],
    perfil: PerfilObjetivo,
    politica: PoliticaAusencia = "MEDIA_DISPONIVEL",
    consanguinidade_pct: Optional[float] = None,
) -> CruzamentoResult:
    pesos = PERFIS[perfil]
    results: list[TraitResult] = []
    alertas: list[str] = []
    soma_scores = soma_pesos = soma_confianca = 0.0
    count_confianca = 0
    faltantes = obrigatorios_faltantes = 0

    for concept_key, peso in pesos:
        s = sire_traits.get(concept_key)
        d = dam_traits.get(concept_key)

        sire_value = s.value if s else None
        dam_value = d.value if d else None
        expected, confidence = expected_progeny(s, d)

        normalized_score: Optional[float] = None

        if expected is not None:
            if concept_key == "PN":
                normalized_score = score_peso_nascer(expected)
            else:
                # Placeholder: substituir por stats reais (média/DP do programa/edição)
                stats = {"mean": 0.0, "sd": 1.0}
                sire_norm = normalize(s, stats)
                dam_norm = normalize(d, stats)
                if sire_norm is not None and dam_norm is not None:
                    normalized_score = (sire_norm + dam_norm) / 2
                elif sire_norm is not None:
                    normalized_score = sire_norm
                elif dam_norm is not None:
                    normalized_score = dam_norm

        if normalized_score is None:
            faltantes += 1
            if politica == "ESTRITA":
                obrigatorios_faltantes += 1
            elif politica == "IMPUTACAO_MEDIA_PROGRAMA":
                normalized_score = 50.0
                alertas.append(f"Traço {concept_key} ausente — imputado com média do programa.")

        if normalized_score is not None:
            soma_scores += peso * normalized_score
            soma_pesos += peso

        if confidence is not None:
            soma_confianca += confidence
            count_confianca += 1

        results.append(TraitResult(
            concept_key=concept_key,
            sire_value=sire_value,
            dam_value=dam_value,
            expected_value=expected,
            normalized_score=normalized_score,
            weight=peso,
            confidence=confidence,
        ))

    # Score composto
    score_composto: Optional[float] = None
    if politica == "ESTRITA" and obrigatorios_faltantes > 0:
        alertas.append(
            f"Modo ESTRITA: {obrigatorios_faltantes} traço(s) obrigatório(s) ausente(s). Score não calculado."
        )
    elif soma_pesos > 0:
        score_composto = soma_scores / soma_pesos

    confianca_media = soma_confianca / count_confianca if count_confianca > 0 else None

    if confianca_media is not None and confianca_media < 50:
        alertas.append(
            f"Confiança média baixa ({confianca_media:.1f}%). Verifique acurácias das avaliações."
        )
    elif confianca_media is not None and confianca_media < 70:
        alertas.append(f"Confiança média razoável ({confianca_media:.1f}%).")

    if consanguinidade_pct is not None:
        if consanguinidade_pct > 12.5:
            alertas.append(
                f"Consanguinidade ALTA ({consanguinidade_pct}%). Acasalamento não recomendado."
            )
        elif consanguinidade_pct > 6.25:
            alertas.append(f"Consanguinidade moderada ({consanguinidade_pct}%). Atenção.")

    total = len(pesos)
    coverage_pct = ((total - faltantes) / total) * 100 if total > 0 else 0.0
    if faltantes > 0:
        alertas.append(f"{faltantes} de {total} traços ausentes. Política: {politica}.")

    return CruzamentoResult(
        score_composto=score_composto,
        confianca_media=confianca_media,
        traits=results,
        alertas=alertas,
        coverage_pct=coverage_pct,
        politica_usada=politica,
    )


def agrupar_por_grupo(traits: list[TraitResult],
                      group_map: dict[str, str]) -> dict[str, list[TraitResult]]:
    grupos: dict[str, list[TraitResult]] = {}
    for t in traits:
        g = group_map.get(t.concept_key, "OUTROS")
        grupos.setdefault(g, []).append(t)
    return grupos
