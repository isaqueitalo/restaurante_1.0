from typing import Optional

from core.db import get_connection
from models.enums import UnidadeProducao
from services import logging_service


def criar_lote(
    produto_id: int,
    quantidade: float,
    unidade: UnidadeProducao,
    estimativa_pratos: Optional[int],
    usuario: str,
) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO lotes_producao(produto_id, quantidade, unidade, estimativa_pratos) VALUES (?, ?, ?, ?)",
        (produto_id, quantidade, unidade.value, estimativa_pratos),
    )
    conn.commit()
    logging_service.registrar(
        "CRIAR_LOTE",
        usuario,
        f"Lote criado para produto {produto_id} quantidade {quantidade}{unidade.value}",
    )
    return cursor.lastrowid


def _obter_lotes_abertos(produto_id: int):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM lotes_producao WHERE produto_id = ? ORDER BY criado_em ASC",
        (produto_id,),
    ).fetchall()


def registrar_consumo_venda(produto_id: int, quantidade: float, unidade: UnidadeProducao) -> None:
    """Decrementa o estoque do lote mais antigo."""
    conn = get_connection()
    lotes = _obter_lotes_abertos(produto_id)
    restante = quantidade
    for lote in lotes:
        if unidade == UnidadeProducao.PORCAO:
            disponivel = lote["quantidade"] - lote["consumido_porcoes"]
            uso = min(disponivel, restante)
            conn.execute(
                "UPDATE lotes_producao SET consumido_porcoes = consumido_porcoes + ? WHERE id = ?",
                (uso, lote["id"]),
            )
        else:
            disponivel = lote["quantidade"] - lote["consumido_kg"]
            uso = min(disponivel, restante)
            conn.execute(
                "UPDATE lotes_producao SET consumido_kg = consumido_kg + ? WHERE id = ?",
                (uso, lote["id"]),
            )
        restante -= uso
        if restante <= 0:
            break
    conn.commit()


def registrar_perda(
    produto_id: int,
    quantidade: float,
    unidade: UnidadeProducao,
    motivo: str,
    usuario: str,
    lote_id: Optional[int] = None,
) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO perdas_estoque(lote_id, produto_id, quantidade, unidade, motivo, registrado_por) VALUES (?, ?, ?, ?, ?, ?)",
        (lote_id, produto_id, quantidade, unidade.value, motivo, usuario),
    )
    conn.commit()
    logging_service.registrar("PERDA", usuario, f"Perda registrada produto {produto_id} motivo {motivo}")
    return cursor.lastrowid


def relatorio_resumo():
    conn = get_connection()
    return conn.execute(
        """
        SELECT p.nome, lp.quantidade, lp.unidade, lp.consumido_porcoes, lp.consumido_kg,
               IFNULL(SUM(ic.quantidade),0) as vendido_porcoes,
               IFNULL(SUM(ic.peso_gramas)/1000.0,0) as vendido_kg
        FROM lotes_producao lp
        JOIN produtos p ON p.id = lp.produto_id
        LEFT JOIN itens_comanda ic ON ic.produto_id = p.id
        GROUP BY lp.id
        """
    ).fetchall()


__all__ = [
    "criar_lote",
    "registrar_consumo_venda",
    "registrar_perda",
    "relatorio_resumo",
]
