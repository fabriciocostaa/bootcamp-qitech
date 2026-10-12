import math
from constants import TRANSFER_FEE_PERCENTAGE

def calculate_transfer_fee(amount: int) -> int:
    return math.ceil(amount * TRANSFER_FEE_PERCENTAGE)