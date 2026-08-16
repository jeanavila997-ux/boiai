"""
MCP Server "boiai-tools" — expõe as capacidades do sistema via
Model Context Protocol (stdio ou HTTP), para o agente interno e
para clientes MCP externos (Claude Desktop, Cursor, etc.).

Uso:
  python -m app.mcp_server.server            # stdio
  MCP_TRANSPORT=http python -m app.mcp_server.server  # HTTP :8100
"""
from __future__ import annotations

import os

from fastmcp import FastMCP

from .tools import (
    get_animal, listar_lotes, query_db, registrar_pesagem,
    simular_cruzamento, status_rebanho,
)
from ..services.rag import ingest_document, search_knowledge

mcp = FastMCP("boiai-tools")

mcp.tool(query_db)
mcp.tool(get_animal)
mcp.tool(simular_cruzamento)
mcp.tool(listar_lotes)
mcp.tool(registrar_pesagem)
mcp.tool(status_rebanho)
mcp.tool(search_knowledge)
mcp.tool(ingest_document)


if __name__ == "__main__":
    if os.getenv("MCP_TRANSPORT", "stdio") == "http":
        mcp.run(transport="http", host="0.0.0.0", port=8100)
    else:
        mcp.run()
