import os
import sqlite3
from pathlib import Path
from typing import Optional


def _default_db_dir() -> Path:
    # Coloca o banco fora do repositório por padrão para evitar binários acidentalmente
    # incluídos em PRs. Pode ser sobrescrito por RESTAURANTE_DB_DIR.
    configured = os.environ.get("RESTAURANTE_DB_DIR")
    if configured:
        return Path(configured)
    return Path.home() / ".restaurante"


DEFAULT_DB_DIR = _default_db_dir()
DEFAULT_DB_NAME = os.environ.get("RESTAURANTE_DB_NAME", "restaurante.db")
DB_PATH = Path(os.environ.get("RESTAURANTE_DB_PATH", DEFAULT_DB_DIR / DEFAULT_DB_NAME))


def get_connection(path: Optional[Path] = None) -> sqlite3.Connection:
    database = Path(path) if path else DB_PATH
    if not database.parent.exists():
        database.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    return conn


def _execute_script(conn: sqlite3.Connection, script: str) -> None:
    cursor = conn.cursor()
    cursor.executescript(script)
    conn.commit()


def init_db(path: Optional[Path] = None) -> None:
    conn = get_connection(path)
    schema = """
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        categoria TEXT NOT NULL,
        preco REAL NOT NULL,
        preco_por_kg REAL,
        ativo INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS mesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero INTEGER UNIQUE NOT NULL,
        status TEXT DEFAULT 'LIVRE'
    );

    CREATE TABLE IF NOT EXISTS comandas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mesa_id INTEGER NOT NULL,
        aberta_por TEXT NOT NULL,
        desconto_total REAL DEFAULT 0,
        motivo_desconto TEXT,
        autorizador TEXT,
        status TEXT DEFAULT 'ABERTA',
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        fechado_em TEXT,
        FOREIGN KEY (mesa_id) REFERENCES mesas(id)
    );

    CREATE TABLE IF NOT EXISTS itens_comanda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comanda_id INTEGER NOT NULL,
        produto_id INTEGER NOT NULL,
        quantidade REAL DEFAULT 1,
        peso_gramas REAL,
        preco_unitario REAL NOT NULL,
        desconto_valor REAL DEFAULT 0,
        motivo_desconto TEXT,
        autorizado_por TEXT,
        enviado_cozinha INTEGER DEFAULT 0,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (comanda_id) REFERENCES comandas(id),
        FOREIGN KEY (produto_id) REFERENCES produtos(id)
    );

    CREATE TABLE IF NOT EXISTS lotes_producao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        quantidade REAL NOT NULL,
        unidade TEXT NOT NULL,
        estimativa_pratos INTEGER,
        consumido_porcoes REAL DEFAULT 0,
        consumido_kg REAL DEFAULT 0,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produto_id) REFERENCES produtos(id)
    );

    CREATE TABLE IF NOT EXISTS perdas_estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote_id INTEGER,
        produto_id INTEGER NOT NULL,
        quantidade REAL NOT NULL,
        unidade TEXT NOT NULL,
        motivo TEXT NOT NULL,
        registrado_por TEXT NOT NULL,
        registrado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (lote_id) REFERENCES lotes_producao(id),
        FOREIGN KEY (produto_id) REFERENCES produtos(id)
    );

    CREATE TABLE IF NOT EXISTS caixas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aberto_por TEXT NOT NULL,
        aberto_em TEXT DEFAULT CURRENT_TIMESTAMP,
        valor_inicial REAL NOT NULL,
        fechado_em TEXT,
        fechado_por TEXT,
        valor_fechamento REAL,
        diferenca REAL
    );

    CREATE TABLE IF NOT EXISTS movimentos_caixa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caixa_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        valor REAL NOT NULL,
        forma_pagamento TEXT,
        referencia TEXT,
        registrado_por TEXT NOT NULL,
        registrado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (caixa_id) REFERENCES caixas(id)
    );

    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acao TEXT NOT NULL,
        usuario TEXT,
        detalhes TEXT,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """
    _execute_script(conn, schema)
    _seed_default_data(conn)


def _seed_default_data(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    # Seed mesas
    existing = cursor.execute("SELECT COUNT(*) as total FROM mesas").fetchone()[0]
    if existing < 20:
        for numero in range(1, 21):
            cursor.execute(
                "INSERT OR IGNORE INTO mesas(numero, status) VALUES (?, 'LIVRE')",
                (numero,),
            )
    # Seed admin
    admin = cursor.execute(
        "SELECT id FROM usuarios WHERE username = ?", ("admin",)
    ).fetchone()
    if not admin:
        from services.auth_service import hash_password  # local import to avoid cycle

        cursor.execute(
            "INSERT INTO usuarios(username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", hash_password("admin"), "admin"),
        )
    conn.commit()


def reset_database(path: Optional[Path] = None) -> None:
    database = Path(path) if path else DB_PATH
    if database.exists():
        database.unlink()
    init_db(database)


__all__ = ["get_connection", "init_db", "reset_database", "DB_PATH"]
