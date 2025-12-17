from typing import Optional

from core.db import get_connection


def registrar(acao: str, usuario: Optional[str], detalhes: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO logs(acao, usuario, detalhes, criado_em) VALUES (?, ?, ?, datetime('now'))",
        (acao, usuario, detalhes),
    )
    conn.commit()


def listar(limit: int = 100):
    conn = get_connection()
    cursor = conn.execute(
        "SELECT id, acao, usuario, detalhes, criado_em FROM logs ORDER BY criado_em DESC LIMIT ?",
        (limit,),
    )
    return cursor.fetchall()


__all__ = ["registrar", "listar"]
