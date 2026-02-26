from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class ItemComanda:
    id: int
    comanda_id: int
    produto_codigo: str
    quantidade: float
    preco_unitario: float
    peso_kg: Optional[float] = None
    desconto: float = 0.0
    cancelado: bool = False

    @property
    def total_bruto(self) -> float:
        return round(self.quantidade * self.preco_unitario, 2)

    @property
    def total_liquido(self) -> float:
        return round(max(0.0, self.total_bruto - self.desconto), 2)
