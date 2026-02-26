from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Produto:
    id: int
    codigo: str
    descricao: str
    preco: float
    preco_por_kg: Optional[float] = None
    estoque: float = 0.0
    ativo: bool = True

    def preco_unitario(self, peso_kg: Optional[float] = None) -> float:
        if peso_kg is not None and self.preco_por_kg is not None:
            return self.preco_por_kg * peso_kg
        return self.preco
