"""Stock and reorder rules."""


def reorder_needed(stock: int, daily_demand: int, lead_time_days: int, safety_stock: int = 5) -> bool:
    if daily_demand < 0 or lead_time_days < 0:
        raise ValueError("demand and lead time must be non-negative")
    reorder_point = daily_demand * lead_time_days + safety_stock
    return stock <= reorder_point


def reorder_quantity(stock: int, target: int, pack_size: int = 1) -> int:
    if pack_size <= 0:
        raise ValueError("pack_size must be positive")
    missing = target - stock
    if missing <= 0:
        return 0
    packs = -(-missing // pack_size)
    return packs * pack_size


def stock_status(stock: int, reorder_point: int) -> str:
    if stock <= 0:
        return "out_of_stock"
    if stock <= reorder_point:
        return "low"
    return "ok"
