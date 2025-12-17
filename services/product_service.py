from typing import Optional

from core.db import get_connection
from models.enums import CategoriaProduto
from services import logging_service


def criar_produto(
    nome: str,
    categoria: CategoriaProduto,
    preco: float,
    preco_por_kg: Optional[float],
    usuario: str,
) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO produtos(nome, categoria, preco, preco_por_kg) VALUES (?, ?, ?, ?)",
        (nome, categoria.value, preco, preco_por_kg),
    )
    conn.commit()
    logging_service.registrar("CRIAR_PRODUTO", usuario, f"Produto {nome} criado na categoria {categoria.value}")
    return cursor.lastrowid


def atualizar_preco(produto_id: int, preco: float, usuario: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE produtos SET preco = ? WHERE id = ?", (preco, produto_id))
    conn.commit()
    logging_service.registrar("ATUALIZAR_PRODUTO", usuario, f"Preco do produto {produto_id} atualizado")


def obter(produto_id: int):
    conn = get_connection()
    return conn.execute(
        "SELECT id, nome, categoria, preco, preco_por_kg FROM produtos WHERE id = ? AND ativo = 1",
        (produto_id,),
    ).fetchone()


def buscar_por_nome(texto: str):
    conn = get_connection()
    termo = f"%{texto}%"
    return conn.execute(
        "SELECT id, nome, categoria, preco, preco_por_kg FROM produtos WHERE nome LIKE ? AND ativo = 1",
        (termo,),
    ).fetchall()


def desativar(produto_id: int, usuario: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (produto_id,))
    conn.commit()
    logging_service.registrar("DESATIVAR_PRODUTO", usuario, f"Produto {produto_id} desativado")


__all__ = [
    "criar_produto",
    "atualizar_preco",
    "obter",
    "buscar_por_nome",
    "desativar",
]
