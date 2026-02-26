"""Persistência do PDV.

Por padrão os serviços usam ``MemoryDB`` (em memória). Para manter dados de
forma persistente entre execuções, utilize ``SQLiteDB``, que salva os
registros em disco em um banco SQLite. A API exposta é a mesma, permitindo
alternar a implementação sem mudar os serviços.
"""
from __future__ import annotations

import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from models.enums import UserRole

from models import (
    Caixa,
    Comanda,
    DescontoLog,
    ItemComanda,
    LogEntry,
    Mesa,
    MotivoDesconto,
    MotivoPerda,
    PerdaEstoque,
    MovimentoCaixa,
    Produto,
    StatusCaixa,
    StatusComanda,
    TipoMovimento,
    User,
)


class MemoryDB:
    def __init__(self) -> None:
        self.produtos: Dict[str, Produto] = {}
        self.motivos_desconto: List[MotivoDesconto] = []
        self.motivos_perda: List[MotivoPerda] = []
        self.mesas: List[Mesa] = [Mesa(numero=i + 1) for i in range(20)]
        self.comandas: Dict[int, Comanda] = {}
        self.itens: List[ItemComanda] = []
        self.descontos_log: List[DescontoLog] = []
        self.perdas_estoque: List[PerdaEstoque] = []
        self.caixas: List[Caixa] = []
        self.movimentos_caixa: List[MovimentoCaixa] = []
        self.logs: List[LogEntry] = []
        self.users: Dict[str, User] = {}

        self._seq = 1
        self._garantir_admin_padrao()

    def next_id(self) -> int:
        atual = self._seq
        self._seq += 1
        return atual

    def log(self, acao: str, detalhes: str, usuario: str) -> None:
        self.logs.append(
            LogEntry(id=self.next_id(), acao=acao, detalhes=detalhes, usuario=usuario, criado_em=datetime.now())
        )

    # Persistência -----------------------------------------------------
    def persist(self) -> None:
        """Gancho para persistência. ``MemoryDB`` não persiste nada."""
        return

    def caixa_aberto(self) -> Caixa | None:
        return next((c for c in self.caixas if getattr(c, "status", None) == StatusCaixa.ABERTO), None)

    def carregar_dados_demo(self) -> None:
        if self.produtos:
            return
        self.produtos.update(
            {
                "001": Produto(codigo="001", descricao="Café expresso", preco=5.0, estoque=200),
                "002": Produto(codigo="002", descricao="Pão de queijo", preco=7.5, estoque=150),
                "003": Produto(codigo="003", descricao="Suco natural", preco=12.0, estoque=80),
                "100": Produto(
                    codigo="100", descricao="Bife na balança (kg)", preco=85.0, por_quilo=True, estoque=35
                ),
            }
        )
        self.motivos_desconto.extend(
            [
                MotivoDesconto(id=self.next_id(), descricao="Cortesia"),
                MotivoDesconto(id=self.next_id(), descricao="Reclamação do cliente"),
                MotivoDesconto(id=self.next_id(), descricao="Programa de fidelidade"),
            ]
        )
        self.motivos_perda.extend(
            [
                MotivoPerda(id=self.next_id(), descricao="Quebra"),
                MotivoPerda(id=self.next_id(), descricao="Validade expirada"),
            ]
        )

    # Usuários --------------------------------------------------------
    def _garantir_admin_padrao(self) -> None:
        if self.users:
            return
        admin = User(id=self.next_id(), username="admin", password_hash=self._hash_password("admin"), role=UserRole.ADMIN)
        self.users[admin.username] = admin

    @staticmethod
    def _hash_password(senha: str) -> str:
        return hashlib.sha256(senha.encode("utf-8")).hexdigest()


class SQLiteDB(MemoryDB):
    """Versão do repositório que salva os dados em disco via SQLite."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path or Path("data") / "pdv.sqlite")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__()
        self._init_db()
        self._load()

    # SQLite helpers ----------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    chave TEXT PRIMARY KEY,
                    valor TEXT
                );
                CREATE TABLE IF NOT EXISTS produtos (
                    codigo TEXT PRIMARY KEY,
                    descricao TEXT,
                    preco REAL,
                    por_quilo INTEGER,
                    estoque REAL
                );
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    role TEXT
                );
                CREATE TABLE IF NOT EXISTS motivos_desconto (
                    id INTEGER PRIMARY KEY,
                    descricao TEXT
                );
                CREATE TABLE IF NOT EXISTS motivos_perda (
                    id INTEGER PRIMARY KEY,
                    descricao TEXT
                );
                CREATE TABLE IF NOT EXISTS mesas (
                    numero INTEGER PRIMARY KEY,
                    comanda_id INTEGER
                );
                CREATE TABLE IF NOT EXISTS comandas (
                    id INTEGER PRIMARY KEY,
                    mesa INTEGER,
                    status TEXT,
                    itens TEXT,
                    desconto_total REAL
                );
                CREATE TABLE IF NOT EXISTS itens (
                    id INTEGER PRIMARY KEY,
                    comanda_id INTEGER,
                    produto_codigo TEXT,
                    quantidade REAL,
                    preco_unitario REAL,
                    cancelado INTEGER,
                    desconto REAL
                );
                CREATE TABLE IF NOT EXISTS descontos_log (
                    id INTEGER PRIMARY KEY,
                    comanda_id INTEGER,
                    item_id INTEGER,
                    motivo_id INTEGER,
                    usuario TEXT,
                    valor REAL,
                    criado_em TEXT
                );
                CREATE TABLE IF NOT EXISTS perdas_estoque (
                    id INTEGER PRIMARY KEY,
                    produto_codigo TEXT,
                    quantidade REAL,
                    motivo_id INTEGER,
                    usuario TEXT,
                    valor_total REAL,
                    criado_em TEXT
                );
                CREATE TABLE IF NOT EXISTS caixas (
                    id INTEGER PRIMARY KEY,
                    data_hora_abertura TEXT,
                    usuario_abertura_id TEXT,
                    valor_inicial_dinheiro REAL,
                    status TEXT,
                    data_hora_fechamento TEXT,
                    usuario_fechamento_id TEXT,
                    valor_esperado_dinheiro_fechamento REAL,
                    valor_contado_dinheiro_fechamento REAL,
                    diferenca_dinheiro REAL
                );
                CREATE TABLE IF NOT EXISTS movimentos_caixa (
                    id INTEGER PRIMARY KEY,
                    caixa_id INTEGER,
                    tipo TEXT,
                    valor REAL,
                    forma_pagamento TEXT,
                    descricao TEXT,
                    criado_em TEXT,
                    usuario TEXT,
                    valor_dinheiro_impacto REAL
                );
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY,
                    acao TEXT,
                    detalhes TEXT,
                    usuario TEXT,
                    criado_em TEXT
                );
                """
            )
            # garante 20 mesas
            cur = conn.execute("SELECT COUNT(*) as total FROM mesas")
            total = cur.fetchone()["total"]
            if total == 0:
                conn.executemany("INSERT INTO mesas (numero, comanda_id) VALUES (?, NULL)", [(i + 1,) for i in range(20)])

    # Serialização -----------------------------------------------------
    def _dt(self, value: Optional[str]) -> Optional[datetime]:
        return datetime.fromisoformat(value) if value else None

    def _load(self) -> None:
        if not self.db_path.exists():
            return
        with self._connect() as conn:
            seq_row = conn.execute("SELECT valor FROM metadata WHERE chave='seq'").fetchone()
            self._seq = int(seq_row["valor"]) if seq_row else 1

            self.users = {
                row["username"]: User(
                    id=row["id"],
                    username=row["username"],
                    password_hash=row["password_hash"],
                    role=UserRole(row["role"]),
                )
                for row in conn.execute("SELECT * FROM users")
            }

            self.produtos = {
                row["codigo"]: Produto(
                    codigo=row["codigo"],
                    descricao=row["descricao"],
                    preco=row["preco"],
                    por_quilo=bool(row["por_quilo"]),
                    estoque=row["estoque"],
                )
                for row in conn.execute("SELECT * FROM produtos")
            }
            self.motivos_desconto = [MotivoDesconto(**dict(row)) for row in conn.execute("SELECT * FROM motivos_desconto")]
            self.motivos_perda = [MotivoPerda(**dict(row)) for row in conn.execute("SELECT * FROM motivos_perda")]
            self.mesas = [Mesa(**dict(row)) for row in conn.execute("SELECT * FROM mesas ORDER BY numero")] or [Mesa(numero=i + 1) for i in range(20)]

            self.comandas = {}
            for row in conn.execute("SELECT * FROM comandas"):
                itens = json.loads(row["itens"]) if row["itens"] else []
                self.comandas[row["id"]] = Comanda(
                    id=row["id"],
                    mesa=row["mesa"],
                    status=StatusComanda(row["status"]),
                    itens=itens,
                    desconto_total=row["desconto_total"],
                )

            self.itens = []
            for row in conn.execute("SELECT * FROM itens"):
                item = ItemComanda(
                    id=row["id"],
                    comanda_id=row["comanda_id"],
                    produto_codigo=row["produto_codigo"],
                    quantidade=row["quantidade"],
                    preco_unitario=row["preco_unitario"],
                    cancelado=bool(row["cancelado"]),
                    desconto=row["desconto"],
                )
                self.itens.append(item)
                if item.comanda_id in self.comandas:
                    if item.id not in self.comandas[item.comanda_id].itens:
                        self.comandas[item.comanda_id].itens.append(item.id)

            self.descontos_log = [
                DescontoLog(
                    id=row["id"],
                    comanda_id=row["comanda_id"],
                    item_id=row["item_id"],
                    motivo_id=row["motivo_id"],
                    usuario=row["usuario"],
                    valor=row["valor"],
                    criado_em=self._dt(row["criado_em"]),
                )
                for row in conn.execute("SELECT * FROM descontos_log")
            ]

            self.perdas_estoque = [
                PerdaEstoque(
                    id=row["id"],
                    produto_codigo=row["produto_codigo"],
                    quantidade=row["quantidade"],
                    motivo_id=row["motivo_id"],
                    usuario=row["usuario"],
                    valor_total=row["valor_total"],
                    criado_em=self._dt(row["criado_em"]),
                )
                for row in conn.execute("SELECT * FROM perdas_estoque")
            ]

            self.caixas = [
                Caixa(
                    id=row["id"],
                    data_hora_abertura=self._dt(row["data_hora_abertura"]),
                    usuario_abertura_id=row["usuario_abertura_id"],
                    valor_inicial_dinheiro=row["valor_inicial_dinheiro"],
                    status=StatusCaixa(row["status"]),
                    data_hora_fechamento=self._dt(row["data_hora_fechamento"]),
                    usuario_fechamento_id=row["usuario_fechamento_id"],
                    valor_esperado_dinheiro_fechamento=row["valor_esperado_dinheiro_fechamento"],
                    valor_contado_dinheiro_fechamento=row["valor_contado_dinheiro_fechamento"],
                    diferenca_dinheiro=row["diferenca_dinheiro"] or 0.0,
                )
                for row in conn.execute("SELECT * FROM caixas")
            ]

            self.movimentos_caixa = [
                MovimentoCaixa(
                    id=row["id"],
                    caixa_id=row["caixa_id"],
                    tipo=TipoMovimento(row["tipo"]),
                    valor=row["valor"],
                    forma_pagamento=row["forma_pagamento"],
                    descricao=row["descricao"],
                    criado_em=self._dt(row["criado_em"]),
                    usuario=row["usuario"],
                    valor_dinheiro_impacto=row["valor_dinheiro_impacto"],
                )
                for row in conn.execute("SELECT * FROM movimentos_caixa")
            ]

            self.logs = [
                LogEntry(
                    id=row["id"],
                    acao=row["acao"],
                    detalhes=row["detalhes"],
                    usuario=row["usuario"],
                    criado_em=self._dt(row["criado_em"]),
                )
                for row in conn.execute("SELECT * FROM logs")
            ]

            # se não houver dados mínimos, carregar demo
            if not self.produtos:
                self.carregar_dados_demo()

            # garante usuário admin padrão e salva qualquer seed inicial
            if not self.users:
                self._garantir_admin_padrao()

            # grava o estado atual (incluindo seeds) para evitar falhas de indentação
            self.persist()

    def _encode_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    def persist(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM metadata")
            conn.execute("INSERT INTO metadata (chave, valor) VALUES ('seq', ?)", (self._seq,))

            conn.execute("DELETE FROM users")
            conn.executemany(
                "INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)",
                [(u.id, u.username, u.password_hash, u.role.value) for u in self.users.values()],
            )

            conn.execute("DELETE FROM produtos")
            conn.executemany(
                "INSERT INTO produtos (codigo, descricao, preco, por_quilo, estoque) VALUES (?, ?, ?, ?, ?)",
                [(p.codigo, p.descricao, p.preco, int(p.por_quilo), p.estoque) for p in self.produtos.values()],
            )

            conn.execute("DELETE FROM motivos_desconto")
            conn.executemany(
                "INSERT INTO motivos_desconto (id, descricao) VALUES (?, ?)",
                [(m.id, m.descricao) for m in self.motivos_desconto],
            )

            conn.execute("DELETE FROM motivos_perda")
            conn.executemany(
                "INSERT INTO motivos_perda (id, descricao) VALUES (?, ?)",
                [(m.id, m.descricao) for m in self.motivos_perda],
            )

            conn.execute("DELETE FROM mesas")
            conn.executemany(
                "INSERT INTO mesas (numero, comanda_id) VALUES (?, ?)",
                [(m.numero, m.comanda_id) for m in self.mesas],
            )

            conn.execute("DELETE FROM comandas")
            conn.executemany(
                "INSERT INTO comandas (id, mesa, status, itens, desconto_total) VALUES (?, ?, ?, ?, ?)",
                [
                    (c.id, c.mesa, c.status.value, json.dumps(c.itens), c.desconto_total)
                    for c in self.comandas.values()
                ],
            )

            conn.execute("DELETE FROM itens")
            conn.executemany(
                """
                INSERT INTO itens (id, comanda_id, produto_codigo, quantidade, preco_unitario, cancelado, desconto)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        i.id,
                        i.comanda_id,
                        i.produto_codigo,
                        i.quantidade,
                        i.preco_unitario,
                        int(i.cancelado),
                        i.desconto,
                    )
                    for i in self.itens
                ],
            )

            conn.execute("DELETE FROM descontos_log")
            conn.executemany(
                "INSERT INTO descontos_log (id, comanda_id, item_id, motivo_id, usuario, valor, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        d.id,
                        d.comanda_id,
                        d.item_id,
                        d.motivo_id,
                        d.usuario,
                        d.valor,
                        self._encode_datetime(d.criado_em),
                    )
                    for d in self.descontos_log
                ],
            )

            conn.execute("DELETE FROM perdas_estoque")
            conn.executemany(
                "INSERT INTO perdas_estoque (id, produto_codigo, quantidade, motivo_id, usuario, valor_total, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        p.id,
                        p.produto_codigo,
                        p.quantidade,
                        p.motivo_id,
                        p.usuario,
                        p.valor_total,
                        self._encode_datetime(p.criado_em),
                    )
                    for p in self.perdas_estoque
                ],
            )

            conn.execute("DELETE FROM caixas")
            conn.executemany(
                """
                INSERT INTO caixas (id, data_hora_abertura, usuario_abertura_id, valor_inicial_dinheiro, status, data_hora_fechamento,
                usuario_fechamento_id, valor_esperado_dinheiro_fechamento, valor_contado_dinheiro_fechamento, diferenca_dinheiro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        c.id,
                        self._encode_datetime(c.data_hora_abertura),
                        c.usuario_abertura_id,
                        c.valor_inicial_dinheiro,
                        c.status.value,
                        self._encode_datetime(c.data_hora_fechamento),
                        c.usuario_fechamento_id,
                        c.valor_esperado_dinheiro_fechamento,
                        c.valor_contado_dinheiro_fechamento,
                        c.diferenca_dinheiro,
                    )
                    for c in self.caixas
                ],
            )

            conn.execute("DELETE FROM movimentos_caixa")
            conn.executemany(
                """
                INSERT INTO movimentos_caixa (id, caixa_id, tipo, valor, forma_pagamento, descricao, criado_em, usuario, valor_dinheiro_impacto)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        m.id,
                        m.caixa_id,
                        m.tipo.value,
                        m.valor,
                        m.forma_pagamento,
                        m.descricao,
                        self._encode_datetime(m.criado_em),
                        m.usuario,
                        m.valor_dinheiro_impacto,
                    )
                    for m in self.movimentos_caixa
                ],
            )

            conn.execute("DELETE FROM logs")
            conn.executemany(
                "INSERT INTO logs (id, acao, detalhes, usuario, criado_em) VALUES (?, ?, ?, ?, ?)",
                [
                    (l.id, l.acao, l.detalhes, l.usuario, self._encode_datetime(l.criado_em))
                    for l in self.logs
                ],
            )

