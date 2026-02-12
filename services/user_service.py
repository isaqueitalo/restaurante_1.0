from passlib.hash import bcrypt
from sqlalchemy.exc import IntegrityError

from database.db import SessionLocal
from models.user import User


class UserError(Exception):
    pass


class CredenciaisInvalidas(UserError):
    pass


class PermissaoNegada(UserError):
    pass


def criar_usuario(username: str, senha: str, role: str):
    db = SessionLocal()
    try:
        senha_hash = bcrypt.hash(senha)
        user = User(
            username=username,
            password_hash=senha_hash,
            role=role
        )
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise UserError("Usuário já existe")
    finally:
        db.close()


def autenticar(username: str, senha: str) -> User:
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()

    if not user or not bcrypt.verify(senha, user.password_hash):
        raise CredenciaisInvalidas("Usuário ou senha inválidos")

    return user
