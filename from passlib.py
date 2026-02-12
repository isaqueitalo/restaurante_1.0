from passlib.hash import bcrypt
from models.user import User
from repositories.user_repository import UserRepository

class CredenciaisInvalidas(Exception):
    pass

class PermissaoNegada(Exception):
    pass

class UserService:

    def __init__(self, repository: UserRepository):
        self.repository = repository

    def criar_usuario(self, username: str, senha: str, role: str):
        senha_hash = bcrypt.hash(senha)
        user = User(username=username, password_hash=senha_hash, role=role)
        self.repository.criar(user)

    def autenticar(self, username: str, senha: str):
        user = self.repository.buscar_por_username(username)
        if not user or not bcrypt.verify(senha, user.password_hash):
            raise CredenciaisInvalidas("Usuário ou senha inválidos")
        return user
