"""Regras de negócio do PDV e operações de apoio."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, Optional

from models import (
    Caixa,
    Comanda,
    DescontoLog,
    ItemComanda,
    LogEntry,
    MotivoDesconto,
    MotivoPerda,
    PerdaEstoque,
    MovimentoCaixa,
    Produto,
    StatusComanda,
    TipoMovimento,
)
from services.database import MemoryDB


class PdvService:
    def __init__(self, db: MemoryDB, usuario: str = "operador") -> None:
        self.db = db
        self.usuario = usuario

    def _persist(self) -> None:
        if hasattr(self.db, "persist"):
            self.db.persist()

    # --- Comandas ---
    def abrir_comanda(self, mesa_numero: Optional[int] = None) -> Comanda:
        comanda_id = self.db.next_id()
        comanda = Comanda(id=comanda_id, mesa=mesa_numero)
        self.db.comandas[comanda_id] = comanda
        if mesa_numero:
            self.db.mesas[mesa_numero - 1].comanda_id = comanda_id
        self.db.log("abrir_comanda", f"Comanda {comanda_id} na mesa {mesa_numero}", self.usuario)
        self._persist()
        return comanda

    def fechar_comanda(self, comanda_id: int) -> None:
        comanda = self.db.comandas[comanda_id]
        comanda.status = StatusComanda.FECHADA
        if comanda.mesa:
            self.db.mesas[comanda.mesa - 1].comanda_id = None
        self.db.log("fechar_comanda", f"Comanda {comanda_id} fechada", self.usuario)
        self._persist()

    def listar_comandas(self) -> Iterable[Comanda]:
        return self.db.comandas.values()

    # --- Itens ---
    def adicionar_item(self, comanda_id: int, produto_codigo: str, quantidade: float) -> ItemComanda:
        produto = self.db.produtos[produto_codigo]
        item = ItemComanda(
            id=self.db.next_id(),
            comanda_id=comanda_id,
            produto_codigo=produto.codigo,
            quantidade=quantidade,
            preco_unitario=produto.preco,
        )
        self.db.itens.append(item)
        self.db.comandas[comanda_id].itens.append(item.id)
        self.db.log(
            "adicionar_item",
            f"Comanda {comanda_id} adicionou {quantidade}x {produto.descricao}",
            self.usuario,
        )
        self._persist()
        return item

    def cancelar_item(self, item_id: int, motivo: str) -> None:
        for item in self.db.itens:
            if item.id == item_id:
                item.cancelado = True
                produto = self.db.produtos.get(item.produto_codigo)
                nome = produto.descricao if produto else "(produto desconhecido)"
                self.db.log("cancelar_item", f"Item {nome} cancelado: {motivo}", self.usuario)
                self._persist()
                break

    # --- Descontos ---
    def aplicar_desconto_item(self, comanda_id: int, item_id: int, valor: float, motivo_id: int) -> None:
        item = next(i for i in self.db.itens if i.id == item_id)
        produto = self.db.produtos.get(item.produto_codigo)
        nome = produto.descricao if produto else "(produto desconhecido)"
        item.desconto += valor
        log = DescontoLog(
            id=self.db.next_id(),
            comanda_id=comanda_id,
            item_id=item_id,
            motivo_id=motivo_id,
            usuario=self.usuario,
            valor=valor,
            criado_em=datetime.now(),
        )
        self.db.descontos_log.append(log)
        self.db.log("desconto_item", f"Item {nome} desconto {valor:.2f}", self.usuario)
        self._persist()

    def aplicar_desconto_comanda(self, comanda_id: int, valor: float, motivo_id: int) -> None:
        comanda = self.db.comandas[comanda_id]
        comanda.desconto_total += valor
        log = DescontoLog(
            id=self.db.next_id(),
            comanda_id=comanda_id,
            item_id=None,
            motivo_id=motivo_id,
            usuario=self.usuario,
            valor=valor,
            criado_em=datetime.now(),
        )
        self.db.descontos_log.append(log)
        self.db.log("desconto_comanda", f"Comanda {comanda_id} desconto {valor:.2f}", self.usuario)
        self._persist()

    # --- Perdas ---
    def registrar_perda(
        self,
        produto_codigo: str,
        quantidade: float,
        motivo_id: int,
        valor_total: Optional[float] = None,
    ) -> float:
        produto = self.db.produtos[produto_codigo]
        produto.estoque = max(0.0, produto.estoque - quantidade)
        valor_total = valor_total if valor_total is not None else quantidade * produto.preco
        perda = PerdaEstoque(
            id=self.db.next_id(),
            produto_codigo=produto_codigo,
            quantidade=quantidade,
            motivo_id=motivo_id,
            usuario=self.usuario,
            valor_total=valor_total,
            criado_em=datetime.now(),
        )
        self.db.perdas_estoque.append(perda)
        self.db.log("perda", f"Perda {quantidade} de {produto.descricao}", self.usuario)
        self._persist()
        return valor_total

    # --- Caixa ---
    def abrir_caixa(self, saldo_inicial: float) -> Caixa:
        caixa = Caixa(
            id=self.db.next_id(),
            data_hora_abertura=datetime.now(),
            usuario_abertura_id=self.usuario,
            valor_inicial_dinheiro=saldo_inicial,
        )
        self.db.caixas.append(caixa)
        self.db.log("abrir_caixa", f"Caixa {caixa.id} aberto", self.usuario)
        self._persist()
        return caixa

    def sangria(self, caixa_id: int, valor: float, descricao: str) -> MovimentoCaixa:
        mov = MovimentoCaixa(
            id=self.db.next_id(),
            caixa_id=caixa_id,
            tipo=TipoMovimento.SANGRIA,
            valor=abs(valor),
            forma_pagamento=None,
            descricao=descricao,
            criado_em=datetime.now(),
            usuario=self.usuario,
            valor_dinheiro_impacto=-abs(valor),
        )
        self.db.movimentos_caixa.append(mov)
        self.db.log("sangria", f"Caixa {caixa_id} sangria {valor}", self.usuario)
        self._persist()
        return mov

    def suprimento(self, caixa_id: int, valor: float, descricao: str) -> MovimentoCaixa:
        mov = MovimentoCaixa(
            id=self.db.next_id(),
            caixa_id=caixa_id,
            tipo=TipoMovimento.SUPRIMENTO,
            valor=abs(valor),
            forma_pagamento=None,
            descricao=descricao,
            criado_em=datetime.now(),
            usuario=self.usuario,
            valor_dinheiro_impacto=abs(valor),
        )
        self.db.movimentos_caixa.append(mov)
        self.db.log("suprimento", f"Caixa {caixa_id} suprimento {valor}", self.usuario)
        self._persist()
        return mov

    def registrar_venda(
        self,
        caixa_id: int,
        valor: float,
        forma_pagamento: str,
        comanda_id: int,
        valor_recebido_em_dinheiro: float | None = None,
    ) -> MovimentoCaixa:
        forma_normalizada = (forma_pagamento or "").lower()
        valor_dinheiro_impacto = 0.0
        descricao = f"Venda comanda {comanda_id}"

        if forma_normalizada == "dinheiro":
            recebido = valor if valor_recebido_em_dinheiro is None else valor_recebido_em_dinheiro
            troco = recebido - valor
            if troco < 0:
                raise ValueError("Valor recebido insuficiente para pagamento em dinheiro")
            valor_dinheiro_impacto = recebido - max(troco, 0.0)
            descricao += f" (dinheiro, troco {troco:.2f})"

        mov = MovimentoCaixa(
            id=self.db.next_id(),
            caixa_id=caixa_id,
            tipo=TipoMovimento.VENDA,
            valor=valor,
            forma_pagamento=forma_pagamento,
            descricao=descricao,
            criado_em=datetime.now(),
            usuario=self.usuario,
            valor_dinheiro_impacto=valor_dinheiro_impacto,
        )
        self.db.movimentos_caixa.append(mov)
        mensagem = f"Comanda {comanda_id} paga em {forma_pagamento}"
        if forma_normalizada == "dinheiro" and valor_recebido_em_dinheiro is not None:
            mensagem += f" (recebido {valor_recebido_em_dinheiro:.2f})"
        self.db.log("venda", mensagem, self.usuario)
        self._persist()
        return mov

    def fechar_caixa(self, caixa_id: int, contagem_final: float) -> Caixa:
        caixa = next(c for c in self.db.caixas if c.id == caixa_id)
        caixa.usuario_fechamento_id = self.usuario
        caixa.data_hora_fechamento = datetime.now()
        caixa.valor_contado_dinheiro_fechamento = contagem_final
        saldo_movimentos = sum(m.valor_dinheiro_impacto for m in self.db.movimentos_caixa if m.caixa_id == caixa_id)
        esperado = caixa.valor_inicial_dinheiro + saldo_movimentos
        caixa.valor_esperado_dinheiro_fechamento = esperado
        caixa.diferenca_dinheiro = contagem_final - esperado
        self.db.log("fechar_caixa", f"Caixa {caixa_id} fechado", self.usuario)
        self._persist()
        return caixa

    # --- Relatórios ---
    def relatorio_vendas(self) -> dict:
        total_bruto = 0.0
        total_descontos = 0.0
        por_forma = defaultdict(float)
        por_produto = defaultdict(float)
        for mov in self.db.movimentos_caixa:
            if mov.tipo == TipoMovimento.VENDA:
                por_forma[mov.forma_pagamento or ""] += mov.valor
        for item in self.db.itens:
            if item.cancelado:
                continue
            total_bruto += item.total_bruto
            total_descontos += item.desconto
            por_produto[item.produto_codigo] += item.total_liquido
        return {
            "total_bruto": total_bruto,
            "total_descontos": total_descontos,
            "total_liquido": total_bruto - total_descontos,
            "por_forma": dict(por_forma),
            "por_produto": dict(por_produto),
        }

    def relatorio_descontos(self) -> dict:
        por_motivo = defaultdict(float)
        por_usuario = defaultdict(float)
        for log in self.db.descontos_log:
            por_motivo[log.motivo_id] += log.valor
            por_usuario[log.usuario] += log.valor
        return {"por_motivo": dict(por_motivo), "por_usuario": dict(por_usuario)}

    def relatorio_perdas(self) -> dict:
        por_produto = defaultdict(float)
        por_motivo = defaultdict(float)
        total = 0.0
        for perda in self.db.perdas_estoque:
            por_produto[perda.produto_codigo] += perda.valor_total
            por_motivo[perda.motivo_id] += perda.valor_total
            total += perda.valor_total
        return {"por_produto": dict(por_produto), "por_motivo": dict(por_motivo), "total": total}

    def relatorio_caixa(self) -> dict:
        linhas = []
        for caixa in self.db.caixas:
            linhas.append(
                {
                    "id": caixa.id,
                    "aberto_por": caixa.aberto_por,
                    "aberto_em": caixa.aberto_em,
                    "fechado_por": caixa.fechado_por,
                    "fechado_em": caixa.fechado_em,
                    "diferenca": caixa.diferenca,
                }
            )
        return {"caixas": linhas}