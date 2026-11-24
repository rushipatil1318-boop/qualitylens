"""Shipping cost and delivery time rules."""
from shopcalc.utils import round_money

ZONE_BASE = {"domestic": 4.90, "eu": 9.90, "world": 19.90}
FREE_SHIPPING_THRESHOLD = 75.0


def shipping_cost(weight_kg: float, zone: str, order_value: float = 0.0) -> float:
    if weight_kg <= 0:
        raise ValueError("weight must be positive")
    if zone not in ZONE_BASE:
        raise ValueError(f"unknown zone {zone}")
    if zone == "domestic" and order_value >= FREE_SHIPPING_THRESHOLD:
        return 0.0
    cost = ZONE_BASE[zone]
    if weight_kg > 2:
        cost += (weight_kg - 2) * 1.5
    if weight_kg > 20:
        cost += 25.0
    return round_money(cost)


def delivery_days(zone: str, express: bool = False) -> int:
    days = {"domestic": 2, "eu": 5, "world": 10}[zone]
    if express:
        days = max(1, days // 2)
    return days
