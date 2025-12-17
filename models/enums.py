from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    GERENTE = "gerente"
    CAIXA = "caixa"
    GARCOM = "garcom"


class CategoriaProduto(str, Enum):
    PRATO_FIXO = "PRATO_FIXO"
    SOBREMESA_PESO = "SOBREMESA_PESO"
    OPCIONAL_PESO = "OPCIONAL_PESO"
    BEBIDA = "BEBIDA"
    ADICIONAL_FIXO = "ADICIONAL_FIXO"


class UnidadeProducao(str, Enum):
    PORCAO = "PORCAO"
    KG = "KG"


class StatusComanda(str, Enum):
    ABERTA = "ABERTA"
    FECHADA = "FECHADA"


class TipoMovimentoCaixa(str, Enum):
    SUPRIMENTO = "SUPRIMENTO"
    SANGRIA = "SANGRIA"
    VENDA = "VENDA"


class FormaPagamento(str, Enum):
    DINHEIRO = "DINHEIRO"
    DEBITO = "DEBITO"
    CREDITO = "CREDITO"
    PIX = "PIX"
