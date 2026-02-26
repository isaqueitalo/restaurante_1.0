from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from models.enums import StatusComanda


@dataclass
class Comanda:
    id: int
    mesa: Optional[int] = None
    status: StatusComanda = StatusComanda.ABERTA
    desconto_total: float = 0.0
    itens: List[int] = field(default_factory=list)
    criado_em: datetime = field(default_factory=datetime.now)
    fechado_em: Optional[datetime] = None

    def fechar(self) -> None:
        self.status = StatusComanda.FECHADA
        self.fechado_em = datetime.now()
