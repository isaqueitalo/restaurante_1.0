"""Serviço simples de autenticação e gestão de usuários."""
from __future__ import annotations

import hashlib

from models import User
from services.database import MemoryDB
from models.enums import UserRole

class UserError(RuntimeError):
    pass


class PermissaoNegada(UserError):
    pass


class CredenciaisInvalidas(UserError):
    pass


class UserService:
    def __init__(self, db: MemoryDB):
        self.db = db

    # Utilidades -----------------------------------------------------
    @staticmethod
    def hash_password(senha: str) -> str:
        return hashlib.sha256(senha.encode("utf-8")).hexdigest()

    # Autenticação ---------------------------------------------------
    def login(self, username: str, senha: str) -> User:
        usuario = self.db.users.get(username)
        if not usuario:
            raise CredenciaisInvalidas("Usuário ou senha inválidos")
        if usuario.password_hash != self.hash_password(senha):
            raise CredenciaisInvalidas("Usuário ou senha inválidos")
        return usuario

    # Gestão ---------------------------------------------------------
    def criar_usuario(
        self,
        ator: User,
        username: str,
        senha: str,
        role: UserRole = UserRole.USER
    ) -> User:

        if ator.role != UserRole.ADMIN:
            raise PermissaoNegada("Apenas administradores podem criar usuários")

        if username in self.db.users:
            raise UserError("Já existe um usuário com esse nome")

        novo = User(
            id=self.db.next_id(),
            username=username,
            password_hash=self.hash_password(senha),
            role=role
        )

        self.db.users[username] = novo
        self._persist()
        return novo

    def listar(self) -> list[User]:
        return list(self.db.users.values())

    def _persist(self) -> None:
        if hasattr(self.db, "persist"):
            self.db.persist()