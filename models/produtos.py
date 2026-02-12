from sqlalchemy import Column, Integer, String, Float
from database.db import Base


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), unique=True, nullable=False)
    preco = Column(Float, nullable=False)
