from decimal import Decimal, ROUND_CEILING
from os import environ


TRANSFER_FEE_PERCENTAGE = Decimal(environ.get("TRANSFER_FEE_PERCENTAGE", "0.02"))


def to_cents(money: str) -> int:
    return int((Decimal(money) * 100).to_integral_value())


def to_money(cents: int) -> str:
    return f"{Decimal(cents) / 100:.2f}"


def expected_transfer_fee(amount_cents: int) -> int:
    fee = Decimal(amount_cents) * TRANSFER_FEE_PERCENTAGE
    return int(fee.to_integral_value(rounding=ROUND_CEILING))
