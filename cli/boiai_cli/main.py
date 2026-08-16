"""
BoiAI CLI — terminal do agente e do banco de dados.

  boiai chat                          # conversa com o agente (streaming)
  boiai db query "SELECT ..."         # SQL somente leitura no MySQL local
  boiai db tables                     # lista tabelas
  boiai import mysql --host H --db D  # importa banco MySQL externo
  boiai memory add "fato..."          # grava memória
  boiai memory list / forget ID       # gerencia memórias
  boiai persona list / set NOME       # gerencia personalidade do agente

Instalação:  pip install -e ./cli   (ou pip install typer rich httpx)
Config:      BOIAI_API (padrão http://localhost:8000), BOIAI_FARM_ID
"""
from __future__ import annotations

import json
import os

import httpx
import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table

API = os.getenv("BOIAI_API", "http://localhost:8000").rstrip("/")
FARM = os.getenv("BOIAI_FARM_ID", "")

app = typer.Typer(help="BoiAI — agente de gestão bovina", no_args_is_help=True)
db_app = typer.Typer(help="Comandos de banco de dados")
memory_app = typer.Typer(help="Memórias do agente")
persona_app = typer.Typer(help="Personas (personalidade do agente)")
import_app = typer.Typer(help="Importação de dados")
app.add_typer(db_app, name="db")
app.add_typer(memory_app, name="memory")
app.add_typer(persona_app, name="persona")
app.add_typer(import_app, name="import")

console = Console()
_session_id: str | None = None


def _farm() -> str:
    if not FARM:
        raise typer.BadParameter("Defina BOIAI_FARM_ID no ambiente.")
    return FARM


# ---------- chat ----------

@app.command()
def chat():
    """Conversa com o agente (mesma sessão acessível no app mobile/web)."""
    global _session_id
    farm = _farm()
    if not _session_id:
        r = httpx.post(f"{API}/chat/sessoes",
                       json={"farm_id": farm, "canal": "cli"}, timeout=30)
        r.raise_for_status()
        _session_id = r.json()["session_id"]
        console.print(f"[dim]Sessão {_session_id} — digite 'sair' para encerrar[/dim]")

    while True:
        texto = Prompt.ask("\n[bold green]você[/bold green]")
        if texto.strip().lower() in ("sair", "exit", "quit"):
            break
        with httpx.stream(
            "POST", f"{API}/chat/{_session_id}/mensagens",
            json={"farm_id": farm, "texto": texto}, timeout=None,
        ) as res:
            console.print("[bold cyan]boiai[/bold cyan] ", end="")
            for line in res.iter_lines():
                if not line.startswith("data:"):
                    continue
                ev = json.loads(line[5:])
                if ev["type"] == "delta":
                    console.print(ev["content"], end="")
                elif ev["type"] == "thinking":
                    console.print(f"[dim]{ev['content']}[/dim]", end="")
                elif ev["type"] == "error":
                    console.print(f"\n[red]Erro: {ev['detail']}[/red]")
            console.print()


# ---------- db ----------

@db_app.command("query")
def db_query(sql: str, limite: int = 50):
    """Executa SELECT somente leitura no MySQL local."""
    from boiai_cli._sql import run_select
    run_select(sql, limite)


@db_app.command("tables")
def db_tables():
    """Lista as tabelas do banco configurado."""
    from boiai_cli._sql import run_select
    run_select("SHOW TABLES", 200)


# ---------- memory ----------

@memory_app.command("add")
def memory_add(conteudo: str, tipo: str = "fato"):
    r = httpx.post(f"{API}/agente/memorias/{_farm()}",
                   json={"conteudo": conteudo, "tipo": tipo}, timeout=60)
    r.raise_for_status()
    console.print(f"[green]Memória gravada: {r.json()['id']}[/green]")


@memory_app.command("list")
def memory_list(tipo: str | None = None):
    r = httpx.get(f"{API}/agente/memorias/{_farm()}",
                  params={"tipo": tipo} if tipo else {}, timeout=30)
    r.raise_for_status()
    t = Table("id", "tipo", "conteudo", "fixada")
    for m in r.json():
        t.add_row(m["id"][:8], m["tipo"], m["conteudo"][:60], "📌" if m["fixada"] else "")
    console.print(t)


@memory_app.command("forget")
def memory_forget(mem_id: str):
    r = httpx.delete(f"{API}/agente/memorias/{_farm()}/{mem_id}", timeout=30)
    r.raise_for_status()
    console.print("[yellow]Memória removida.[/yellow]")


# ---------- persona ----------

@persona_app.command("list")
def persona_list():
    r = httpx.get(f"{API}/agente/personas/{_farm()}", timeout=30)
    r.raise_for_status()
    t = Table("nome", "tom", "verbosidade", "proatividade", "padrão")
    for p in r.json():
        t.add_row(p["nome"], p["tom"], p["verbosidade"], p["proatividade"],
                  "✓" if p["is_default"] else "")
    console.print(t)


# ---------- import ----------

@import_app.command("mysql")
def import_mysql(host: str, database: str, user: str,
                 password: str = typer.Option(..., prompt=True, hide_input=True),
                 port: int = 3306, dry_run: bool = True):
    """Inspeciona um banco MySQL externo (ex.: legado da Hostinger)."""
    r = httpx.post(f"{API}/importar/mysql/inspecionar", json={
        "farm_id": _farm(), "host": host, "port": port,
        "user": user, "password": password, "database": database,
    }, timeout=60)
    r.raise_for_status()
    dados = r.json()
    for tabela in dados["tabelas"]:
        colunas = dados["estrutura"][tabela]
        linhas = next((c["_linhas"] for c in colunas if "_linhas" in c), "?")
        console.print(f"[bold]{tabela}[/bold] — {linhas} linhas")
    console.print("\n[dim]Próximo passo: mapeamento coluna-a-coluna (Fase 1).[/dim]")


if __name__ == "__main__":
    app()
