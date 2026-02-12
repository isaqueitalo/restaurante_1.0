from sqlalchemy.orm import Session
from models.user import User

class UserRepository:

    def __init__(self, session: Session):
        self.session = session

    def criar(self, user: User):
        self.session.add(user)
        self.session.commit()

    def buscar_por_username(self, username: str):
        return self.session.query(User).filter_by(username=username).first()
