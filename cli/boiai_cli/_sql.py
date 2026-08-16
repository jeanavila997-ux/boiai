"""Acesso direto ao MySQL local para os comandos `boiai db`."""
from __future__ import annotations

import os
import re

import pymysql
from rich.console import Console
from rich.table import Table

console = Console()
_BLOQUEADO = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT)\b", re.I)


def _conn():
    url = os.getenv("BOIAI_MYSQL", "mysql://boiai:boiai_secret@localhost:3306/boiai")
    m = re.match(r"mysql://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)", url)
    if not m:
        raise SystemExit("BOIAI_MYSQL inválida. Formato: mysql://user:pass@host:porta/db")
    user, pw, host, port, dbname = m.groups()
    return pymysql.connect(host=host, port=int(port), user=user, password=pw,
                           database=dbname, charset="utf8mb4")


def run_select(sql: str, limite: int = 50) -> None:
    if _BLOQUEADO.search(sql) or not re.match(r"^\s*(SELECT|SHOW|DESCRIBE|EXPLAIN)\b", sql, re.I):
        console.print("[red]Somente leitura: SELECT / SHOW / DESCRIBE / EXPLAIN.[/red]")
        raise SystemExit(1)
    if "limit" not in sql.lower() and sql.strip().upper().startswith("SELECT"):
        sql = f"{sql.rstrip().rstrip(';')} LIMIT {limite}"
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description or []]
    if not cols:
        console.print("(sem colunas)")
        return
    t = Table(*cols)
    for row in rows:
        t.add_row(*["" if v is None else str(v) for v in row])
    console.print(t)
    console.print(f"[dim]{len(rows)} linha(s)[/dim]")
