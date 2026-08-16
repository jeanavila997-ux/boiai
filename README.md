# BoiAI — Gestão Bovina com Agente de IA

Sistema unificado de gestão bovina (comercial, genética e manejo) com agente de IA
local (Ollama), RAG, memória configurável, MCP server, CLI de terminal e PWA mobile.

Sucessório de dois projetos:
- **[BoiControl](https://github.com/jeanavila997-ux/boicontrol)** — compras/lotes, PWA offline, exportações
- **[CattleGen](https://github.com/avila2026/app-cruzamento-bovinos)** — genética, DEPs (Geneplus/PMGZ/ANCP), simulador de cruzamento

## Arquitetura

```
web/ (PWA React) ──┐
cli/ (terminal) ───┼──► backend/ (FastAPI) ──► MySQL 8   (dados relacionais)
                   │        │                ──► Qdrant   (vetores do RAG/memória)
                   │        │                ──► Ollama   (chat + embeddings locais)
                   │        └─► mcp_server/ "boiai-tools" (Model Context Protocol)
                   └─ clientes MCP externos (Claude Desktop, Cursor...)
```

## Quickstart

```bash
cp .env.example .env          # ajuste senhas e modelo
docker compose up -d          # MySQL + Qdrant + backend
ollama pull qwen3:8b          # modelo de chat (no host)
ollama pull bge-m3            # modelo de embeddings
curl localhost:8000/health    # verifica API + modelos

# CLI
pip install -e ./cli
export BOIAI_FARM_ID=<uuid-da-fazenda>
boiai chat

# Testes do motor de scoring
cd backend && pip install -r requirements.txt && pytest
```

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `db/` | Schema MySQL unificado + seed do dicionário de DEPs e personas |
| `backend/app/services/scoring.py` | Motor de cruzamento (port 1:1 do CattleGen, com testes) |
| `backend/app/services/ollama.py` | Cliente Ollama streaming SSE + embeddings |
| `backend/app/services/rag.py` | RAG e memória semântica (Ollama + Qdrant + MySQL) |
| `backend/app/agent/` | Agent Core, prompts, memória (3 camadas), personas |
| `backend/app/mcp_server/` | Servidor MCP `boiai-tools` (query_db, simular_cruzamento, etc.) |
| `backend/app/api/` | REST: animais, chat (SSE), configuração do agente, importações |
| `cli/` | `boiai` — chat, db, memory, persona, import |
| `web/` | PWA React (Fase 3) |

## Segurança

- Consultas do agente ao banco são **somente leitura** (whitelist SELECT/SHOW/DESCRIBE)
- Escritas (pesagem, importação) exigem **confirmação humana**
- Credenciais ficam no servidor — nunca no front/PWA

## Roadmap

- [x] Fase 0 — fundação: monorepo, Docker Compose, schema unificado
- [ ] Fase 1 — CRUDs completos + importador MySQL/planilha com dry-run
- [ ] Fase 2 — agente v1: tool calling (LangGraph), RAG semeado, memória de sessão/perfil
- [ ] Fase 3 — PWA completo + telas de configuração do agente e memórias
- [ ] Fase 4 — memória semântica com extração automática + módulo de manejo
- [ ] Fase 5 — backups, acesso externo seguro, Electron desktop
