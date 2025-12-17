from pathlib import Path

import pytest

from core import db
from models.enums import CategoriaProduto, FormaPagamento, TipoMovimentoCaixa, UnidadeProducao
from services import (
    caixa_service,
    comanda_service,
    production_service,
    product_service,
)
from services.logging_service import listar


@pytest.fixture(autouse=True)
def reset_db(temp_db_path):
    db.DB_PATH = Path(temp_db_path)
    db.reset_database(temp_db_path)
    yield
    if Path(temp_db_path).exists():
        Path(temp_db_path).unlink()


def criar_produto_basico(nome: str, categoria: CategoriaProduto) -> int:
    return product_service.criar_produto(nome, categoria, 10.0, 50.0, "admin")


def test_consumo_producao_por_lote():
    produto_id = criar_produto_basico("Prato", CategoriaProduto.PRATO_FIXO)
    lote_id = production_service.criar_lote(
        produto_id, quantidade=10, unidade=UnidadeProducao.PORCAO, estimativa_pratos=10, usuario="admin"
    )
    comanda = comanda_service.abrir_comanda(1, "admin")
    comanda_service.adicionar_item(comanda, produto_id, quantidade=2, usuario="admin")

    conn = db.get_connection()
    lote = conn.execute("SELECT consumido_porcoes FROM lotes_producao WHERE id = ?", (lote_id,)).fetchone()
    assert lote["consumido_porcoes"] == 2


def test_item_por_peso_valor_totaliza():
    produto_id = criar_produto_basico("Bolo", CategoriaProduto.SOBREMESA_PESO)
    comanda = comanda_service.abrir_comanda(2, "admin")
    comanda_service.adicionar_item(comanda, produto_id, quantidade=1, peso_gramas=200, usuario="admin")

    total = comanda_service.totalizar(comanda)
    # preco_por_kg=50 -> 0.2kg => 10
    assert pytest.approx(total, 0.01) == 10


def test_fechamento_caixa_calcula_diferenca():
    caixa = caixa_service.abrir_caixa("admin", 100)
    caixa_service.registrar_movimento(caixa, TipoMovimentoCaixa.SUPRIMENTO, 20, "admin")
    caixa_service.registrar_movimento(caixa, TipoMovimentoCaixa.SANGRIA, 30, "admin")
    caixa_service.registrar_venda(caixa, 50, FormaPagamento.DINHEIRO, "admin")

    resumo = caixa_service.fechar_caixa(caixa, "admin", contagem_final=150)
    assert resumo["esperado"] == 140
    assert pytest.approx(resumo["diferenca"], 0.01) == 10


def test_log_desconto_comanda_registrado():
    produto_id = criar_produto_basico("Refrigerante", CategoriaProduto.BEBIDA)
    comanda = comanda_service.abrir_comanda(3, "admin")
    comanda_service.adicionar_item(comanda, produto_id, quantidade=1, usuario="admin")

    comanda_service.aplicar_desconto_comanda(
        comanda_id=comanda,
        valor=2.0,
        usuario="admin",
        motivo="Cliente vip",
        autorizado_por="gerente",
    )
    logs = listar(limit=5)
    assert any("DESCONTO_COMANDA" in log["acao"] for log in logs)
