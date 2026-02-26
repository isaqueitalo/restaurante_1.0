from dataclasses import dataclass
from typing import Optional

from core.db import get_connection
from models.entities import User
from models.enums import UserRole
from services.auth_service import verify_password



class UserError(RuntimeError):
    pass


class CredenciaisInvalidas(UserError):
    pass


class PermissaoNegada(UserError):
    pass


@dataclass
class Usuario:
    id: int
    username: str
    role: UserRole


from models.enums import UserRole
from services.auth_service import verify_password

class UserService:
    def __init__(self, db):
        self.db = db

    def listar(self) -> list[User]:
        return list(self.db.users.values())

    def autenticar(self, username: str, password: str) -> Usuario:
        conn = self.db._connect()

        row = conn.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if not row:
            raise CredenciaisInvalidas("Usuário ou senha inválidos")

        if not verify_password(password, row["password_hash"]):
            raise CredenciaisInvalidas("Usuário ou senha inválidos")

        return Usuario(
            id=row["id"],
            username=row["username"],
            role=UserRole(row["role"]),  # <-- agora vem direto do banco
        )

    def verificar_permissao(self, usuario: Usuario, roles_permitidos: list[UserRole]) -> None:
        if usuario.role not in roles_permitidos:
            raise PermissaoNegada("Usuário sem permissão para esta operação")
