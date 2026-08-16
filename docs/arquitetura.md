# Arquitetura do BoiAI

Documento-resumo. A análise completa dos projetos de origem e o plano por fases
estão no relatório "Análise e Plano — Sistema de Gestão Bovina com IA".

## Decisões-chave

1. **Backend próprio (FastAPI)** — resolve a limitação do CattleGen (chat Ollama
   só funcionava em dev/localhost). Agora o daemon Ollama fica atrás do backend;
   mobile, desktop e CLI usam o mesmo agente.
2. **MySQL 8 relacional + Qdrant vetorial** — MySQL não tem tipo vetorial nativo
   (o tipo VECTOR chegou no MySQL 9). Qdrant roda em container ao lado e guarda
   embeddings de `knowledge_document` e `agent_memory` (payload = id da linha).
3. **MCP server `boiai-tools`** — as ferramentas do agente interno são expostas
   via Model Context Protocol, então clientes MCP externos também podem plugar
   no sistema (Claude Desktop, Cursor, etc.).
4. **Memória em 3 camadas configuráveis** — sessão (janela de contexto), perfil
   (fatos estáveis da fazenda) e semântica (fatos extraídos, com embedding e TTL).
   Tudo listável/editável/apagável na tela de configuração.
5. **Personas configuráveis** — system prompt, tom, verbosidade, proatividade,
   modelo Ollama e nível de think por persona; seed com 3 personas padrão.
6. **Scoring portado 1:1** — `backend/app/services/scoring.py` replica o
   `scoring.ts` do CattleGen com suíte de testes equivalente.

## Ferramentas do agente (MCP)

| Tool | Tipo | Função |
|---|---|---|
| `query_db` | leitura | SQL SELECT com whitelist |
| `get_animal` | leitura | Animal + pedigree + DEPs |
| `simular_cruzamento` | leitura | Motor de scoring touro × fêmea |
| `listar_lotes` | leitura | Lotes de compra recentes |
| `status_rebanho` | leitura | Resumo do rebanho |
| `buscar_conhecimento` | leitura | RAG na base de conhecimento |
| `registrar_pesagem` | escrita* | Registra pesagem (*confirmação humana) |
| `ingest_document` | escrita* | Alimenta a base de conhecimento |

## Modelos Ollama sugeridos

- Chat/agente: `qwen3:8b` (tool calling), `qwen3:32b` se houver GPU
- Embeddings: `bge-m3` (1024 dims, bom em português)
- Visão (opcional): `qwen2.5vl`

## Pendências herdadas dos projetos de origem

- Stats reais de normalização de DEPs (média/DP por programa/edição) — hoje placeholder
- Importação dos dados atuais: IndexedDB do BoiControl e Supabase do CattleGen
- Sumários oficiais para validar códigos do trait_dictionary
