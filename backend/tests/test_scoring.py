"""Testes do motor de scoring — casos equivalentes ao scoring.ts do CattleGen."""
from app.services.scoring import (
    EvaluationTrait, calcular_cruzamento, expected_progeny, normalize,
    score_peso_nascer,
)


def test_normalize_percentil_inverte():
    t = EvaluationTrait(rank_type="PERCENTIL", rank_value=10)
    assert normalize(t) == 90


def test_normalize_deca():
    t = EvaluationTrait(rank_type="DECA", rank_value=1)
    assert normalize(t) == 100


def test_normalize_ausente():
    assert normalize(None) is None
    assert normalize(EvaluationTrait()) is None


def test_progênie_media_pais():
    sire = EvaluationTrait(value=20, accuracy=80)
    dam = EvaluationTrait(value=10, accuracy=60)
    esperado, confianca = expected_progeny(sire, dam)
    assert esperado == 15
    assert confianca == 70


def test_pn_penaliza_desvio_do_alvo():
    assert score_peso_nascer(32) == 100
    assert score_peso_nascer(42) == 50  # 10 kg acima do alvo × k=5


def test_politica_estrita_sem_score_quando_falta():
    sire = {"IPP": EvaluationTrait(value=1.5, accuracy=70)}
    dam = {"IPP": EvaluationTrait(value=1.0, accuracy=70)}
    r = calcular_cruzamento(sire, dam, perfil="NOVILHAS", politica="ESTRITA")
    assert r.score_composto is None
    assert any("ESTRITA" in a for a in r.alertas)


def test_imputacao_media_atribui_50():
    r = calcular_cruzamento({}, {}, perfil="TERMINAL",
                            politica="IMPUTACAO_MEDIA_PROGRAMA")
    assert abs(r.score_composto - 50.0) < 1e-9
    assert r.coverage_pct == 0.0


def test_alerta_consanguinidade_alta():
    sire = {"IPP": EvaluationTrait(value=1.5)}
    dam = {"IPP": EvaluationTrait(value=1.0)}
    r = calcular_cruzamento(sire, dam, perfil="REPOSICAO",
                            consanguinidade_pct=15.0)
    assert any("Consanguinidade ALTA" in a for a in r.alertas)
