from typing import Optional

from core.db import get_connection
from models.enums import CategoriaProduto, StatusComanda, UnidadeProducao
from services import logging_service, production_service
from services.product_service import obter


class ComandaFechadaError(Exception):
    pass


def abrir_comanda(mesa_numero: int, usuario: str) -> int:
    conn = get_connection()
    mesa = conn.execute("SELECT id FROM mesas WHERE numero = ?", (mesa_numero,)).fetchone()
    if not mesa:
        raise ValueError("Mesa inexistente")
    cursor = conn.execute(
        "INSERT INTO comandas(mesa_id, aberta_por, status) VALUES (?, ?, ?)",
        (mesa["id"], usuario, StatusComanda.ABERTA.value),
    )
    conn.execute(
        "UPDATE mesas SET status = 'OCUPADA' WHERE id = ?",
        (mesa["id"],),
    )
    conn.commit()
    logging_service.registrar("ABRIR_COMANDA", usuario, f"Mesa {mesa_numero} aberta")
    return cursor.lastrowid


def _validar_aberta(conn, comanda_id: int) -> None:
    comanda = conn.execute(
        "SELECT status FROM comandas WHERE id = ?", (comanda_id,)
    ).fetchone()
    if not comanda or comanda["status"] != StatusComanda.ABERTA.value:
        raise ComandaFechadaError("Comanda fechada ou inexistente")


def adicionar_item(
    comanda_id: int,
    produto_id: int,
    quantidade: float,
    usuario: str,
    peso_gramas: Optional[float] = None,
    desconto: float = 0.0,
    motivo_desconto: Optional[str] = None,
    autorizado_por: Optional[str] = None,
) -> int:
    conn = get_connection()
    _validar_aberta(conn, comanda_id)
    produto = obter(produto_id)
    if not produto:
        raise ValueError("Produto inexistente")

    preco_unitario = produto["preco"]
    if produto["categoria"] in {
        CategoriaProduto.SOBREMESA_PESO.value,
        CategoriaProduto.OPCIONAL_PESO.value,
    }:
        if peso_gramas is None:
            raise ValueError("Peso obrigatorio para itens por quilo")
        preco_unitario = (produto["preco_por_kg"] or produto["preco"]) * (peso_gramas / 1000)
        quantidade = 1

    cursor = conn.execute(
        """
        INSERT INTO itens_comanda(
            comanda_id, produto_id, quantidade, peso_gramas, preco_unitario,
            desconto_valor, motivo_desconto, autorizado_por
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            comanda_id,
            produto_id,
            quantidade,
            peso_gramas,
            preco_unitario,
            desconto,
            motivo_desconto,
            autorizado_por,
        ),
    )
    conn.commit()
    logging_service.registrar(
        "ADICIONAR_ITEM",
        usuario,
        f"Item {produto_id} adicionado na comanda {comanda_id} peso={peso_gramas} desconto={desconto}",
    )

    unidade = (
        UnidadeProducao.KG
        if produto["categoria"]
        in {CategoriaProduto.OPCIONAL_PESO.value, CategoriaProduto.SOBREMESA_PESO.value}
        else UnidadeProducao.PORCAO
    )
    consumo = peso_gramas / 1000 if unidade == UnidadeProducao.KG and peso_gramas else quantidade
    production_service.registrar_consumo_venda(produto_id, consumo, unidade)
    return cursor.lastrowid


def aplicar_desconto_comanda(
    comanda_id: int,
    valor: float,
    usuario: str,
    motivo: str,
    autorizado_por: str,
) -> None:
    conn = get_connection()
    _validar_aberta(conn, comanda_id)
    conn.execute(
        "UPDATE comandas SET desconto_total = ?, motivo_desconto = ?, autorizador = ? WHERE id = ?",
        (valor, motivo, autorizado_por, comanda_id),
    )
    conn.commit()
    logging_service.registrar(
        "DESCONTO_COMANDA", usuario, f"Desconto {valor} aplicado na comanda {comanda_id} motivo {motivo}",
    )


def fechar_comanda(comanda_id: int, usuario: str) -> None:
    conn = get_connection()
    _validar_aberta(conn, comanda_id)
    conn.execute(
        "UPDATE comandas SET status = ?, fechado_em = datetime('now') WHERE id = ?",
        (StatusComanda.FECHADA.value, comanda_id),
    )
    conn.commit()
    logging_service.registrar("FECHAR_COMANDA", usuario, f"Comanda {comanda_id} fechada")


def totalizar(comanda_id: int) -> float:
    conn = get_connection()
    totais = conn.execute(
        "SELECT IFNULL(SUM(preco_unitario - desconto_valor),0) as total FROM itens_comanda WHERE comanda_id = ?",
        (comanda_id,),
    ).fetchone()
    comanda = conn.execute(
        "SELECT desconto_total FROM comandas WHERE id = ?",
        (comanda_id,),
    ).fetchone()
    total_itens = totais["total"] or 0
    desconto_comanda = comanda["desconto_total"] if comanda else 0
    return max(total_itens - desconto_comanda, 0)


def registrar_envio_cozinha(item_id: int, usuario: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE itens_comanda SET enviado_cozinha = 1 WHERE id = ?",
        (item_id,),
    )
    conn.commit()
    logging_service.registrar("ENVIAR_COZINHA", usuario, f"Item {item_id} enviado para cozinha")


__all__ = [
    "abrir_comanda",
    "adicionar_item",
    "aplicar_desconto_comanda",
    "fechar_comanda",
    "totalizar",
    "registrar_envio_cozinha",
    "ComandaFechadaError",
]
