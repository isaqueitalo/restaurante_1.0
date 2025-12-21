"""Regras de negócio para controle de caixa.

A implementação usa o ``MemoryDB`` existente, mas concentra as regras
em uma classe dedicada para facilitar futura troca por SQLite ou ORM.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Optional

from models import Caixa, DescontoLog, MovimentoCaixa, StatusCaixa, TipoMovimento
from services.database import MemoryDB


class CaixaError(RuntimeError):
    """Erro base para operações de caixa."""


class CaixaJaAbertoError(CaixaError):
    pass


class CaixaNaoAbertoError(CaixaError):
    pass


class CaixaNaoEncontradoError(CaixaError):
    pass


class PagamentoInsuficienteError(CaixaError):
    pass


class CaixaService:
    def __init__(self, db: MemoryDB, usuario: str = "operador") -> None:
        self.db = db
        self.usuario = usuario

    def _persist(self) -> None:
        if hasattr(self.db, "persist"):
            self.db.persist()

    # --- helpers ---------------------------------------------------------
    def _caixa_por_id(self, caixa_id: int) -> Caixa:
        caixa = next((c for c in self.db.caixas if c.id == caixa_id), None)
        if not caixa:
            raise CaixaNaoEncontradoError(f"Caixa {caixa_id} não encontrado")
        return caixa

    def _caixa_aberto(self) -> Caixa:
        caixa = self.db.caixa_aberto()
        if not caixa:
            raise CaixaNaoAbertoError("Não há caixa aberto")
        return caixa

    def _registrar_movimento(
        self,
        caixa_id: int,
        tipo: TipoMovimento,
        valor: float,
        descricao: str,
        valor_dinheiro_impacto: float,
        forma_pagamento: Optional[str] = None,
    ) -> MovimentoCaixa:
        mov = MovimentoCaixa(
            id=self.db.next_id(),
            caixa_id=caixa_id,
            tipo=tipo,
            valor=valor,
            forma_pagamento=forma_pagamento,
            descricao=descricao,
            criado_em=datetime.now(),
            usuario=self.usuario,
            valor_dinheiro_impacto=valor_dinheiro_impacto,
        )
        self.db.movimentos_caixa.append(mov)
        self._persist()
        return mov

    # --- Abertura --------------------------------------------------------
    def abrir_caixa(self, valor_inicial_dinheiro: float) -> Caixa:
        if self.db.caixa_aberto():
            raise CaixaJaAbertoError("Já existe um caixa aberto")
        caixa = Caixa(
            id=self.db.next_id(),
            data_hora_abertura=datetime.now(),
            usuario_abertura_id=self.usuario,
            valor_inicial_dinheiro=valor_inicial_dinheiro,
        )
        self.db.caixas.append(caixa)
        self._persist()
        return caixa

    # --- Movimentações ---------------------------------------------------
    def registrar_suprimento(self, valor: float, descricao: str = "Suprimento") -> MovimentoCaixa:
        caixa = self._caixa_aberto()
        return self._registrar_movimento(
            caixa_id=caixa.id,
            tipo=TipoMovimento.SUPRIMENTO,
            valor=valor,
            descricao=descricao,
            valor_dinheiro_impacto=abs(valor),
        )

    def registrar_sangria(self, valor: float, descricao: str = "Sangria") -> MovimentoCaixa:
        caixa = self._caixa_aberto()
        return self._registrar_movimento(
            caixa_id=caixa.id,
            tipo=TipoMovimento.SANGRIA,
            valor=valor,
            descricao=descricao,
            valor_dinheiro_impacto=-abs(valor),
        )

    def registrar_venda(
        self,
        valor_total_venda: float,
        tipo_pagamento: str,
        valor_recebido_em_dinheiro: Optional[float] = None,
    ) -> MovimentoCaixa:
        caixa = self._caixa_aberto()
        tp = tipo_pagamento.upper()
        if tp == "DINHEIRO":
            if valor_recebido_em_dinheiro is None:
                raise PagamentoInsuficienteError("Informe o valor recebido em dinheiro")
            troco = valor_recebido_em_dinheiro - valor_total_venda
            if troco < 0:
                raise PagamentoInsuficienteError("Valor recebido insuficiente")
            impacto = valor_recebido_em_dinheiro - troco
            return self._registrar_movimento(
                caixa_id=caixa.id,
                tipo=TipoMovimento.VENDA_DINHEIRO,
                valor=valor_total_venda,
                descricao=f"Venda dinheiro (troco {troco:.2f})",
                valor_dinheiro_impacto=impacto,
                forma_pagamento="dinheiro",
            )
        tipo_map: Dict[str, TipoMovimento] = {
            "DEBITO": TipoMovimento.VENDA_DEBITO,
            "CREDITO": TipoMovimento.VENDA_CREDITO,
            "PIX": TipoMovimento.VENDA_PIX,
        }
        if tp not in tipo_map:
            raise CaixaError(f"Tipo de pagamento não suportado: {tipo_pagamento}")
        return self._registrar_movimento(
            caixa_id=caixa.id,
            tipo=tipo_map[tp],
            valor=valor_total_venda,
            descricao=f"Venda {tp.lower()}",
            valor_dinheiro_impacto=0.0,
            forma_pagamento=tp.lower(),
        )

    # --- Cálculos --------------------------------------------------------
    def calcular_saldo_dinheiro(self, caixa_id: int) -> float:
        caixa = self._caixa_por_id(caixa_id)
        soma_movimentos = sum(m.valor_dinheiro_impacto for m in self.db.movimentos_caixa if m.caixa_id == caixa.id)
        return caixa.valor_inicial_dinheiro + soma_movimentos

    # --- Fechamento ------------------------------------------------------
    def fechar_caixa(self, valor_contado_dinheiro_fechamento: float, usuario_fechamento_id: Optional[str] = None) -> Caixa:
        caixa = self._caixa_aberto()
        esperado = self.calcular_saldo_dinheiro(caixa.id)
        caixa.valor_esperado_dinheiro_fechamento = esperado
        caixa.valor_contado_dinheiro_fechamento = valor_contado_dinheiro_fechamento
        caixa.diferenca_dinheiro = valor_contado_dinheiro_fechamento - esperado
        caixa.status = StatusCaixa.FECHADO
        caixa.usuario_fechamento_id = usuario_fechamento_id or self.usuario
        caixa.data_hora_fechamento = datetime.now()
        self.db.log(
            "fechar_caixa",
            (
                "Caixa {cid} fechado | esperado R$ {esp:.2f} | "
                "contado R$ {cont:.2f} | dif {dif:+.2f}"
            ).format(
                cid=caixa.id, esp=esperado, cont=valor_contado_dinheiro_fechamento, dif=caixa.diferenca_dinheiro
            ),
            self.usuario,
        )
        self._persist()
        return caixa

    # --- Relatórios ------------------------------------------------------
    def totais_por_pagamento(self, caixa_id: int) -> Dict[str, float]:
        self._caixa_por_id(caixa_id)
        totais: Dict[str, float] = {"DINHEIRO": 0.0, "DEBITO": 0.0, "CREDITO": 0.0, "PIX": 0.0}
        for mov in self.db.movimentos_caixa:
            if mov.caixa_id != caixa_id:
                continue
            if mov.tipo == TipoMovimento.VENDA_DINHEIRO:
                totais["DINHEIRO"] += mov.valor
            elif mov.tipo == TipoMovimento.VENDA_DEBITO:
                totais["DEBITO"] += mov.valor
            elif mov.tipo == TipoMovimento.VENDA_CREDITO:
                totais["CREDITO"] += mov.valor
            elif mov.tipo == TipoMovimento.VENDA_PIX:
                totais["PIX"] += mov.valor
        return totais

    def totais_extras(self, caixa_id: int) -> Dict[str, float]:
        self._caixa_por_id(caixa_id)
        suprimentos = 0.0
        sangrias = 0.0
        for mov in self.db.movimentos_caixa:
            if mov.caixa_id != caixa_id:
                continue
            if mov.tipo == TipoMovimento.SUPRIMENTO:
                suprimentos += mov.valor
            elif mov.tipo == TipoMovimento.SANGRIA:
                sangrias += mov.valor
        return {"suprimentos": suprimentos, "sangrias": sangrias}

    def _total_descontos_do_periodo(self, caixa: Caixa) -> float:
        """Soma descontos aplicados durante o período do caixa."""

        inicio = caixa.data_hora_abertura
        fim = caixa.data_hora_fechamento or datetime.now()
        total = 0.0
        for log in self.db.descontos_log:
            if isinstance(log, DescontoLog) and log.criado_em:
                if inicio <= log.criado_em <= fim:
                    total += log.valor
        return total

    def _resumo_caixa(self, caixa: Caixa) -> Dict[str, float]:
        esperado_registrado = caixa.valor_esperado_dinheiro_fechamento
        esperado = esperado_registrado if esperado_registrado is not None else self.calcular_saldo_dinheiro(caixa.id)
        totais_pagamento = self.totais_por_pagamento(caixa.id)
        extras = self.totais_extras(caixa.id)
        total_descontos = self._total_descontos_do_periodo(caixa)
        impactos = [m.valor_dinheiro_impacto for m in self.db.movimentos_caixa if m.caixa_id == caixa.id]
        total_positivo = sum(v for v in impactos if v > 0)
        total_negativo = sum(v for v in impactos if v < 0)
        # valor contado pode estar ausente em caixas antigos; nesse caso, reconstrói
        if caixa.valor_contado_dinheiro_fechamento is not None:
            valor_contado = caixa.valor_contado_dinheiro_fechamento
        else:
            # tenta derivar a partir de esperado + diferença (se existir), ou assume esperado
            delta = caixa.diferenca_dinheiro if caixa.diferenca_dinheiro is not None else 0.0
            base = caixa.valor_esperado_dinheiro_fechamento if caixa.valor_esperado_dinheiro_fechamento is not None else esperado
            valor_contado = base + delta

        # calcula diferença sempre que houver base para comparação
        if caixa.status == StatusCaixa.FECHADO or caixa.valor_contado_dinheiro_fechamento is not None or caixa.diferenca_dinheiro is not None:
            diferenca = valor_contado - esperado
        else:
            diferenca = None
        return {
            "caixa_id": caixa.id,
            "abertura": caixa.data_hora_abertura,
            "fechamento": caixa.data_hora_fechamento,
            "valor_inicial": caixa.valor_inicial_dinheiro,
            "esperado_dinheiro": esperado,
            "valor_contado": valor_contado,
            "diferenca": diferenca,
            "pagamentos": totais_pagamento,
            "suprimentos": extras["suprimentos"],
            "sangrias": extras["sangrias"],
            "descontos": total_descontos,
            "total_movimentos_positivos": total_positivo,
            "total_movimentos_negativos": total_negativo,
        }

    def resumo_fechamento(self, caixa_id: int) -> Dict[str, float]:
        caixa = self._caixa_por_id(caixa_id)
        return self._resumo_caixa(caixa)

    def resumo_ultimo_fechamento(self) -> Dict[str, float]:
        fechados = [c for c in self.db.caixas if c.status == StatusCaixa.FECHADO]
        if not fechados:
            raise CaixaNaoEncontradoError("Nenhum caixa fechado encontrado")
        caixa = max(fechados, key=lambda c: c.data_hora_fechamento or c.data_hora_abertura)
        return self._resumo_caixa(caixa)

    def fechamentos_por_data(self, data_referencia: date) -> list[Dict[str, float]]:
        fechados = [
            c
            for c in self.db.caixas
            if (c.data_hora_fechamento or c.data_hora_abertura).date() == data_referencia
            and c.status == StatusCaixa.FECHADO
        ]
        return [self._resumo_caixa(caixa) for caixa in fechados]

    def movimentos_do_dia(self, data_referencia: date) -> Dict[str, object]:
        """Lista os movimentos do caixa na data informada, com totais.

        O cálculo considera o campo ``criado_em`` dos movimentos e não exige
        que o caixa esteja aberto, apenas que os movimentos pertençam a algum
        caixa existente.
        """

        movimentos = [
            m
            for m in self.db.movimentos_caixa
            if isinstance(m.criado_em, datetime) and m.criado_em.date() == data_referencia
        ]
        movimentos.sort(key=lambda m: m.criado_em)
        total_valor = sum(m.valor for m in movimentos)
        total_positivo = sum(m.valor_dinheiro_impacto for m in movimentos if m.valor_dinheiro_impacto > 0)
        total_negativo = sum(m.valor_dinheiro_impacto for m in movimentos if m.valor_dinheiro_impacto < 0)
        return {
            "movimentos": movimentos,
            "total_valor": total_valor,
            "total_dinheiro_positivo": total_positivo,
            "total_dinheiro_negativo": total_negativo,
        }