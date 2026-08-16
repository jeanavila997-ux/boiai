"""Conexão com MySQL via SQLAlchemy + helpers de consulta."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Iterator

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_all(sql: str, params: dict | None = None) -> list[dict]:
    """Consulta genérica (leitura) retornando lista de dicts."""
    with get_session() as s:
        rows = s.execute(text(sql), params or {}).mappings().all()
        return [dict(r) for r in rows]


def fetch_one(sql: str, params: dict | None = None) -> dict | None:
    with get_session() as s:
        row = s.execute(text(sql), params or {}).mappings().first()
        return dict(row) if row else None


def execute(sql: str, params: dict | None = None) -> int:
    """Comando de escrita; retorna nº de linhas afetadas."""
    with get_session() as s:
        result = s.execute(text(sql), params or {})
        return result.rowcount or 0
