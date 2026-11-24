"""Order totals combining pricing, tax and shipping."""
from shopcalc.pricing import apply_discount, line_total, tax_for
from shopcalc.shipping import shipping_cost
from shopcalc.utils import round_money


def order_total(unit_price: float, quantity: int, code: str, country: str, weight_kg: float,
                zone: str) -> float:
    subtotal = line_total(unit_price, quantity)
    discounted = apply_discount(subtotal, code)
    tax = tax_for(discounted, country)
    shipping = shipping_cost(weight_kg, zone, discounted)
    return round_money(discounted + tax + shipping)
