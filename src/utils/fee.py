import math
from constants import TRANSFER_FEE_PERCENTAGE

def calculate_transfer_fee(amount: int) -> int:
    """1% do valor transferido, em centavos, sempre arredondado
    pra CIMA — nunca pro banco perder centavo por arredondamento
    a favor do cliente. `math.ceil` existe exatamente por isso.
    """
    return math.ceil(amount * TRANSFER_FEE_PERCENTAGE)