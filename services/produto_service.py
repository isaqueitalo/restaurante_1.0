from sqlalchemy.exc import IntegrityError
from database.db import SessionLocal
from models.produto import Produto


class ProdutoError(Exception):
    pass


def criar_produto(nome: str, preco: float):
    if preco <= 0:
        raise ProdutoError("O preço deve ser maior que zero.")

    db = SessionLocal()
    try:
        produto = Produto(nome=nome.strip(), preco=preco)
        db.add(produto)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ProdutoError("Já existe um produto com esse nome.")
    finally:
        db.close()


def listar_produtos():
    db = SessionLocal()
    produtos = db.query(Produto).all()
    db.close()
    return produtos


def excluir_produto(produto_id: int):
    db = SessionLocal()
    produto = db.query(Produto).get(produto_id)

    if not produto:
        db.close()
        raise ProdutoError("Produto não encontrado.")

    db.delete(produto)
    db.commit()
    db.close()
