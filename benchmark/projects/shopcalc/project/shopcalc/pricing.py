"""Price, voucher and tax rules."""
from shopcalc.utils import round_money

TAX_RATES = {"DE": 0.19, "AT": 0.20, "FR": 0.20, "IN": 0.18}
VOUCHERS = {"SAVE10": 0.10, "SAVE20": 0.20, "VIP": 0.30}


class PricingError(ValueError):
    """Raised for invalid prices, quantities or codes."""


def apply_discount(price: float, code: str) -> float:
    if price < 0:
        raise PricingError("price must be non-negative")
    if code == "":
        return round_money(price)
    if code not in VOUCHERS:
        raise PricingError(f"unknown voucher {code}")
    rate = VOUCHERS[code]
    if code == "VIP" and price < 50:
        rate = 0.15
    return round_money(price * (1 - rate))


def tax_for(amount: float, country: str) -> float:
    if country not in TAX_RATES:
        raise PricingError(f"unsupported country {country}")
    return round_money(amount * TAX_RATES[country])


def bulk_discount_rate(quantity: int) -> float:
    if quantity >= 100:
        return 0.15
    if quantity >= 50:
        return 0.10
    if quantity >= 10:
        return 0.05
    return 0.0


def line_total(unit_price: float, quantity: int) -> float:
    if quantity <= 0:
        raise PricingError("quantity must be positive")
    gross = unit_price * quantity
    return round_money(gross * (1 - bulk_discount_rate(quantity)))
