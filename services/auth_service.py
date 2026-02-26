import hashlib
from typing import Optional

from core.db import get_connection
from models.enums import UserRole
from services import logging_service


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
    
def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

def create_user(username: str, password: str, role: UserRole, actor: str) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO usuarios(username, password_hash, role) VALUES (?, ?, ?)",
        (username, hash_password(password), role.value),
    )
    conn.commit()
    logging_service.registrar("CRIAR_USUARIO", actor, f"Usuario {username} criado com papel {role.value}")
    return cursor.lastrowid


def login(username: str, password: str) -> Optional[dict]:
    conn = get_connection()
    user = conn.execute(
        "SELECT id, username, password_hash, role FROM usuarios WHERE username = ?",
        (username,),
    ).fetchone()
    if user and user["password_hash"] == hash_password(password):
        logging_service.registrar("LOGIN", username, "Login realizado")
        return {"id": user["id"], "username": user["username"], "role": user["role"]}
    return None


def validate_permission(user: dict, allowed_roles: list[UserRole]) -> bool:
    return user.get("role") in {role.value for role in allowed_roles}


__all__ = ["hash_password", "create_user", "login", "validate_permission"]
