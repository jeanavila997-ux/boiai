"""System prompts do agente BoiAI (base: useChat.ts do CattleGen, ampliado)."""

BASE_PROMPT = (
    "Você é o agente do BoiAI, sistema de gestão bovina (comercial, genética e manejo) "
    "focado em Nelore e raças zebuínas no Brasil. "
    "Ajude o pecuarista a: interpretar DEPs e índices (Geneplus, PMGZ, ANCP), "
    "comparar touros e matrizes, sugerir acasalamentos dirigidos segundo o objetivo "
    "(novilhas precoces, reposição, terminal), acompanhar lotes, pesagens e custos, "
    "e explicar conceitos de forma simples e prática. "
    "Responda sempre em português do Brasil, de forma objetiva. "
    "Quando faltar dado, diga qual informação é necessária. Não invente números de DEP."
)

FERRAMENTAS_PROMPT = (
    "\n\nVocê tem ferramentas para consultar o banco de dados da fazenda, "
    "simular cruzamentos, registrar pesagens e eventos, buscar conhecimento técnico "
    "e gerar relatórios. Use-as sempre que a pergunta depender de dados reais. "
    "Antes de qualquer escrita (registro, importação), confirme com o usuário."
)

MEMORIA_HEADER = "\n\n### Memórias relevantes sobre esta fazenda:\n"
CONTEXTO_RAG_HEADER = "\n\n### Conhecimento técnico recuperado:\n"


def montar_system_prompt(persona_prompt: str | None = None,
                         memorias: list[dict] | None = None,
                         docs_rag: list[dict] | None = None) -> str:
    """Compõe o system prompt: persona (ou base) + memórias + RAG."""
    prompt = (persona_prompt or BASE_PROMPT) + FERRAMENTAS_PROMPT
    if memorias:
        linhas = "\n".join(f"- [{m['tipo']}] {m['conteudo']}" for m in memorias)
        prompt += MEMORIA_HEADER + linhas
    if docs_rag:
        blocos = "\n\n---\n\n".join(
            f"[{d.get('fonte', 'doc')}] {d.get('titulo') or ''}\n{d['conteudo']}"
            for d in docs_rag
        )
        prompt += CONTEXTO_RAG_HEADER + blocos
    return prompt
