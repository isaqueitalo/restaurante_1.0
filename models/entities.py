
"""Modelos de domínio para o PDV e gestão do restaurante.

As estruturas são simples e mantidas em memória, facilitando a troca
posterior por um banco de dados relacional.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from models.enums import UserRole


class StatusComanda(str, Enum):
    ABERTA = "aberta"
    FECHADA = "fechada"


@dataclass
class Produto:
    codigo: str
    descricao: str
    preco: float
    por_quilo: bool = False
    estoque: float = 0.0


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    role: UserRole = UserRole.USER


@dataclass
class MotivoDesconto:
    id: int
    descricao: str


@dataclass
class MotivoPerda:
    id: int
    descricao: str


@dataclass
class DescontoLog:
    id: int
    comanda_id: int
    item_id: Optional[int]
    motivo_id: int
    usuario: str
    valor: float
    criado_em: datetime


@dataclass
class PerdaEstoque:
    id: int
    produto_codigo: str
    quantidade: float
    motivo_id: int
    usuario: str
    valor_total: float
    criado_em: datetime


@dataclass
class LogEntry:
    id: int
    acao: str
    detalhes: str
    usuario: str
    criado_em: datetime


@dataclass
class ItemComanda:
    id: int
    comanda_id: int
    produto_codigo: str
    quantidade: float
    preco_unitario: float
    cancelado: bool = False
    desconto: float = 0.0

    @property
    def total_bruto(self) -> float:
        return self.quantidade * self.preco_unitario

    @property
    def total_liquido(self) -> float:
        return max(0.0, self.total_bruto - self.desconto)


@dataclass
class Comanda:
    id: int
    mesa: Optional[int]
    status: StatusComanda = StatusComanda.ABERTA
    itens: list[int] = field(default_factory=list)
    desconto_total: float = 0.0

    def total_bruto(self, itens: list[ItemComanda]) -> float:
        return sum(i.total_bruto for i in itens if i.id in self.itens and not i.cancelado)

    def total_liquido(self, itens: list[ItemComanda]) -> float:
        return max(0.0, self.total_bruto(itens) - self.desconto_total - sum(
            i.desconto for i in itens if i.id in self.itens and not i.cancelado
        ))


@dataclass
class Mesa:
    numero: int
    comanda_id: Optional[int] = None

class StatusCaixa(str, Enum):
    ABERTO = "aberto"
    FECHADO = "fechado"

@dataclass
class Caixa:
    id: int
    data_hora_abertura: datetime
    usuario_abertura_id: str
    valor_inicial_dinheiro: float
    status: StatusCaixa = StatusCaixa.ABERTO
    data_hora_fechamento: Optional[datetime] = None
    usuario_fechamento_id: Optional[str] = None
    valor_esperado_dinheiro_fechamento: Optional[float] = None
    valor_contado_dinheiro_fechamento: Optional[float] = None
    diferenca_dinheiro: float = 0.0

    # Compatibilidade com código existente
    @property
    def aberto_por(self) -> str:
        return self.usuario_abertura_id

    @property
    def aberto_em(self) -> datetime:
        return self.data_hora_abertura

    @property
    def fechado_por(self) -> Optional[str]:
        return self.usuario_fechamento_id

    @property
    def fechado_em(self) -> Optional[datetime]:
        return self.data_hora_fechamento

    @property
    def saldo_inicial(self) -> float:
        return self.valor_inicial_dinheiro

    @property
    def saldo_fechamento(self) -> Optional[float]:
        return self.valor_contado_dinheiro_fechamento
    
    @property
    def diferenca(self) -> float:
        """Compatibilidade com chamadas legadas que usam ``caixa.diferenca``.

        Mantém o mesmo valor de ``diferenca_dinheiro`` para evitar erros
        quando relatórios antigos ainda referenciam o atributo antigo.
        """
        return self.diferenca_dinheiro


class TipoMovimento(str, Enum):
    VENDA = "venda"
    VENDA_DINHEIRO = "venda_dinheiro"
    VENDA_DEBITO = "venda_debito"
    VENDA_CREDITO = "venda_credito"
    VENDA_PIX = "venda_pix"
    SANGRIA = "sangria"
    SUPRIMENTO = "suprimento"
    AJUSTE = "ajuste"


@dataclass
class MovimentoCaixa:
    id: int
    caixa_id: int
    tipo: TipoMovimento
    valor: float
    forma_pagamento: Optional[str]
    descricao: str
    criado_em: datetime
    usuario: str
    valor_dinheiro_impacto: float = 0.0
