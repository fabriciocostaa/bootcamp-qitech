from decimal import Decimal, ROUND_CEILING
from os import environ


# O percentual da taxa de transferencia. A API le TRANSFER_FEE_PERCENTAGE
# do ambiente e, sem ele, usa 0.02. O teste nao importa nada de src/, entao
# repete aqui o mesmo combinado: variavel de ambiente, com o mesmo padrao.
TRANSFER_FEE_PERCENTAGE = Decimal(environ.get("TRANSFER_FEE_PERCENTAGE", "0.02"))


def to_cents(money: str) -> int:
    """'20.00' -> 2000. A API devolve dinheiro como texto com 2 casas."""
    return int((Decimal(money) * 100).to_integral_value())


def to_money(cents: int) -> str:
    """2000 -> '20.00'."""
    return f"{Decimal(cents) / 100:.2f}"


def expected_transfer_fee(amount_cents: int) -> int:
    """Taxa da transferencia: percentual do valor, arredondado SEMPRE pra cima.

    Calculada com Decimal (exato) de proposito: o teste nao pode repetir o
    mesmo float que a API usa, senao um erro de ponto flutuante passaria
    despercebido dos dois lados.
    """
    fee = Decimal(amount_cents) * TRANSFER_FEE_PERCENTAGE
    return int(fee.to_integral_value(rounding=ROUND_CEILING))
