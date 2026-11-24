"""Shared numeric helpers."""
from decimal import ROUND_HALF_UP, Decimal


def round_money(value: float) -> float:
    """Round a money amount to cents, half up."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def clamp(value: float, low: float, high: float) -> float:
    if low > high:
        raise ValueError("low must not exceed high")
    return max(low, min(value, high))


def percent(part: float, whole: float) -> float:
    if whole == 0:
        return 0.0
    return round(100.0 * part / whole, 1)
