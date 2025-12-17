#!/usr/bin/env python3
"""Detecta artefatos binários comuns (SQLite, logs, backups) antes de abrir PRs.

O script verifica arquivos versionados e não versionados com extensões
que normalmente geram avisos de incompatibilidade de binários em plataformas
como GitHub. Ele não remove nada automaticamente: apenas lista e usa códigos
de saída para facilitar automação em CI ou pre-commit hooks.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List, Tuple

BINARY_EXTS = [
    ".db",
    ".db-journal",
    ".db-wal",
    ".db-shm",
    ".sqlite",
    ".sqlite3",
    ".sqlite-wal",
    ".sqlite-shm",
    ".bak",
    ".log",
]


def list_tracked() -> List[Path]:
    """Lista arquivos rastreados pelo git."""
    result = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True)
    return [Path(line) for line in result.stdout.strip().splitlines() if line.strip()]


def list_untracked() -> List[Path]:
    """Lista arquivos não rastreados que aparecem no status."""
    result = subprocess.run(["git", "status", "--porcelain"], check=True, capture_output=True, text=True)
    untracked = []
    for line in result.stdout.strip().splitlines():
        if line.startswith("?? "):
            untracked.append(Path(line[3:]))
    return untracked


def filter_binaries(paths: Iterable[Path]) -> List[Path]:
    return [p for p in paths if p.suffix.lower() in BINARY_EXTS]


def summarize(label: str, items: List[Path]) -> None:
    if not items:
        print(f"{label}: nenhum arquivo suspeito encontrado")
        return
    print(f"{label} ({len(items)}):")
    for path in sorted(items):
        print(f"  - {path}")


def main() -> int:
    tracked = filter_binaries(list_tracked())
    untracked = filter_binaries(list_untracked())

    print("Verificação de binários potencialmente incompatíveis\n")
    summarize("Rastreados", tracked)
    summarize("Não rastreados", untracked)

    if tracked or untracked:
        print("\nAção sugerida:")
        if tracked:
            print("  - Remova-os do índice com 'git rm --cached <arquivo>' se não deveriam ir para o PR.")
        if untracked:
            print("  - Exclua-os ou mova-os para fora do repositório antes de criar o PR.")
        return 1

    print("\nNenhum artefato binário detectado. Seguro para abrir o PR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
