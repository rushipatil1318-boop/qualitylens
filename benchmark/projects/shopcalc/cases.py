"""Hand-written benchmark changes on the shopcalc sample project.

kind: refactor | test | feature | bug. Labels: bug = 1, everything else = 0.
refactor/test cases must keep the hidden oracle green; bug cases must make it fail (checked at run time).
Feature cases change behaviour on purpose and update a test in the same commit.
"""

P, S, I, U, O = "shopcalc/pricing.py", "shopcalc/shipping.py", "shopcalc/inventory.py", "shopcalc/utils.py", \
    "shopcalc/orders.py"
TP, TS, TI = "tests/test_pricing.py", "tests/test_shipping.py", "tests/test_inventory.py"
APPEND = None  # old=None means append `new` to the file

CASES = [
    # ---------------- refactors (behaviour preserved) ----------------
    ("R01", "refactor", "rename local in apply_discount", [(P,
        '    rate = VOUCHERS[code]\n    if code == "VIP" and price < 50:\n        rate = 0.15\n'
        '    return round_money(price * (1 - rate))',
        '    discount_rate = VOUCHERS[code]\n    if code == "VIP" and price < 50:\n        discount_rate = 0.15\n'
        '    return round_money(price * (1 - discount_rate))')]),
    ("R02", "refactor", "extract weight surcharge helper", [(S,
        "    cost = ZONE_BASE[zone]\n    if weight_kg > 2:\n        cost += (weight_kg - 2) * 1.5\n"
        "    if weight_kg > 20:\n        cost += 25.0\n    return round_money(cost)",
        "    cost = ZONE_BASE[zone] + _weight_surcharge(weight_kg)\n    return round_money(cost)\n\n\n"
        "def _weight_surcharge(weight_kg: float) -> float:\n    surcharge = 0.0\n    if weight_kg > 2:\n"
        "        surcharge += (weight_kg - 2) * 1.5\n    if weight_kg > 20:\n        surcharge += 25.0\n"
        "    return surcharge")]),
    ("R03", "refactor", "math.ceil in reorder_quantity", [
        (I, '"""Stock and reorder rules."""\n', '"""Stock and reorder rules."""\nimport math\n'),
        (I, "    packs = -(-missing // pack_size)", "    packs = math.ceil(missing / pack_size)")]),
    ("R04", "refactor", "docstring for clamp", [(U,
        "def clamp(value: float, low: float, high: float) -> float:\n",
        'def clamp(value: float, low: float, high: float) -> float:\n    """Limit value to [low, high]."""\n')]),
    ("R05", "refactor", "dict.get in tax_for", [(P,
        "    if country not in TAX_RATES:\n        raise PricingError(f\"unsupported country {country}\")\n"
        "    return round_money(amount * TAX_RATES[country])",
        "    rate = TAX_RATES.get(country)\n    if rate is None:\n"
        "        raise PricingError(f\"unsupported country {country}\")\n    return round_money(amount * rate)")]),
    ("R06", "refactor", "elif chain in stock_status", [(I,
        '    if stock <= 0:\n        return "out_of_stock"\n    if stock <= reorder_point:\n        return "low"\n'
        '    return "ok"',
        '    if stock <= 0:\n        status = "out_of_stock"\n    elif stock <= reorder_point:\n'
        '        status = "low"\n    else:\n        status = "ok"\n    return status')]),
    ("R07", "refactor", "rename variables in order_total", [(O,
        "    subtotal = line_total(unit_price, quantity)\n    discounted = apply_discount(subtotal, code)\n"
        "    tax = tax_for(discounted, country)\n    shipping = shipping_cost(weight_kg, zone, discounted)\n"
        "    return round_money(discounted + tax + shipping)",
        "    gross = line_total(unit_price, quantity)\n    net = apply_discount(gross, code)\n"
        "    vat = tax_for(net, country)\n    delivery = shipping_cost(weight_kg, zone, net)\n"
        "    return round_money(net + vat + delivery)")]),
    ("R08", "refactor", "module constant for delivery days", [(S,
        "def delivery_days(zone: str, express: bool = False) -> int:\n"
        "    days = {\"domestic\": 2, \"eu\": 5, \"world\": 10}[zone]",
        "DELIVERY_DAYS = {\"domestic\": 2, \"eu\": 5, \"world\": 10}\n\n\n"
        "def delivery_days(zone: str, express: bool = False) -> int:\n    days = DELIVERY_DAYS[zone]")]),
    ("R09", "refactor", "table-driven bulk tiers", [(P,
        "def bulk_discount_rate(quantity: int) -> float:\n    if quantity >= 100:\n        return 0.15\n"
        "    if quantity >= 50:\n        return 0.10\n    if quantity >= 10:\n        return 0.05\n    return 0.0",
        "BULK_TIERS = ((100, 0.15), (50, 0.10), (10, 0.05))\n\n\n"
        "def bulk_discount_rate(quantity: int) -> float:\n    for min_qty, rate in BULK_TIERS:\n"
        "        if quantity >= min_qty:\n            return rate\n    return 0.0")]),
    ("R10", "refactor", "truthiness check in percent", [(U,
        "    if whole == 0:\n        return 0.0", "    if not whole:\n        return 0.0")]),
    ("R11", "refactor", "clearer error message in shipping_cost", [(S,
        'raise ValueError("weight must be positive")', 'raise ValueError("weight_kg must be greater than 0")')]),
    ("R12", "refactor", "constant for cent quantum", [(U,
        "def round_money(value: float) -> float:\n",
        'CENT = Decimal("0.01")\n\n\ndef round_money(value: float) -> float:\n'),
        (U, 'quantize(Decimal("0.01"), rounding', "quantize(CENT, rounding")]),
    # ---------------- test-only changes ----------------
    ("T01", "test", "tests for reorder_needed", [(TI, APPEND,
        "\n\ndef test_reorder_needed_boundary():\n    from shopcalc.inventory import reorder_needed\n"
        "    assert reorder_needed(15, 2, 5) is True\n    assert reorder_needed(16, 2, 5) is False\n")]),
    ("T02", "test", "boundary tests for bulk tiers", [(TP, APPEND,
        "\n\ndef test_bulk_rate_boundaries():\n    assert bulk_discount_rate(10) == 0.05\n"
        "    assert bulk_discount_rate(50) == 0.10\n    assert bulk_discount_rate(100) == 0.15\n")]),
    ("T03", "test", "free shipping test", [(TS, APPEND,
        "\n\ndef test_free_domestic_shipping():\n    assert shipping_cost(1.0, \"domestic\", 75.0) == 0.0\n")]),
    # ---------------- intended features, test updated in the same commit ----------------
    ("F01", "feature", "add NL tax rate", [(P, '"IN": 0.18}', '"IN": 0.18, "NL": 0.21}'),
        (TP, APPEND, "\n\ndef test_tax_netherlands():\n    assert tax_for(100.0, \"NL\") == 21.0\n")]),
    ("F02", "feature", "WELCOME5 voucher", [(P, '"VIP": 0.30}', '"VIP": 0.30, "WELCOME5": 0.05}'),
        (TP, APPEND, "\n\ndef test_welcome_voucher():\n    assert apply_discount(100.0, \"WELCOME5\") == 95.0\n")]),
    ("F03", "feature", "world express takes 4 days", [(S,
        "    if express:\n        days = max(1, days // 2)",
        "    if express:\n        days = 4 if zone == \"world\" else max(1, days // 2)"),
        (TS, APPEND, "\n\ndef test_world_express():\n    assert delivery_days(\"world\", express=True) == 4\n")]),
    ("F04", "feature", "safety stock default 10", [(I, "safety_stock: int = 5", "safety_stock: int = 10"),
        (TI, APPEND, "\n\ndef test_reorder_default_safety_stock():\n"
                     "    from shopcalc.inventory import reorder_needed\n"
                     "    assert reorder_needed(20, 2, 5) is True\n    assert reorder_needed(21, 2, 5) is False\n")]),
    ("F05", "feature", "free shipping from 60", [(S, "FREE_SHIPPING_THRESHOLD = 75.0", "FREE_SHIPPING_THRESHOLD = 60.0"),
        (TS, APPEND, "\n\ndef test_free_shipping_from_60():\n    assert shipping_cost(1.0, \"domestic\", 60.0) == 0.0\n"
                     "    assert shipping_cost(1.0, \"domestic\", 59.99) == 4.9\n")]),
    ("F06", "feature", "overstock status", [(I, '    if stock <= reorder_point:\n        return "low"\n',
        '    if stock <= reorder_point:\n        return "low"\n    if stock > 5 * reorder_point:\n'
        '        return "overstock"\n'),
        (TI, APPEND, "\n\ndef test_overstock():\n    assert stock_status(51, 10) == \"overstock\"\n")]),
    ("F07", "feature", "percent with 2 decimals", [(U, "    return round(100.0 * part / whole, 1)",
                                                     "    return round(100.0 * part / whole, 2)"),
        ("tests/test_utils.py", APPEND, "from shopcalc.utils import percent\n\n\ndef test_percent_two_decimals():\n"
                                        "    assert percent(1, 3) == 33.33\n")]),
    ("F08", "feature", "case-insensitive vouchers", [(P,
        "    if code not in VOUCHERS:\n", "    code = code.upper()\n    if code not in VOUCHERS:\n"),
        (TP, APPEND, "\n\ndef test_voucher_case_insensitive():\n    assert apply_discount(100.0, \"save10\") == 90.0\n")]),
    # ---------------- bugs ----------------
    ("B01", "bug", "bulk tier off-by-one", [(P, "if quantity >= 50:", "if quantity > 50:")]),
    ("B02", "bug", "free shipping boundary", [(S, "order_value >= FREE_SHIPPING_THRESHOLD",
                                               "order_value > FREE_SHIPPING_THRESHOLD")]),
    ("B03", "bug", "VIP small-order rate typo", [(P, "        rate = 0.15", "        rate = 0.25")]),
    ("B04", "bug", "bankers rounding", [(U, "from decimal import ROUND_HALF_UP, Decimal",
                                         "from decimal import ROUND_HALF_EVEN, Decimal"),
                                        (U, "rounding=ROUND_HALF_UP", "rounding=ROUND_HALF_EVEN")]),
    ("B05", "bug", "reorder point exclusive", [(I, "    return stock <= reorder_point", "    return stock < reorder_point")]),
    ("B06", "bug", "silent default tax rate", [(P,
        "    if country not in TAX_RATES:\n        raise PricingError(f\"unsupported country {country}\")\n"
        "    return round_money(amount * TAX_RATES[country])",
        "    return round_money(amount * TAX_RATES.get(country, 0.19))")]),
    ("B07", "bug", "reorder packs rounded down", [(I, "    packs = -(-missing // pack_size)",
                                                   "    packs = missing // pack_size")]),
    ("B08", "bug", "tax on undiscounted subtotal", [(O, "    tax = tax_for(discounted, country)",
                                                     "    tax = tax_for(subtotal, country)")]),
    ("B09", "bug", "surcharge on full weight", [(S, "cost += (weight_kg - 2) * 1.5", "cost += weight_kg * 1.5")]),
    ("B10", "bug", "express divides by 3", [(S, "days = max(1, days // 2)", "days = max(1, days // 3)")]),
    ("B11", "bug", "zero quantity accepted", [(P, "    if quantity <= 0:", "    if quantity < 0:")]),
    ("B12", "bug", "SAVE10 rate typo", [(P, '"SAVE10": 0.10', '"SAVE10": 0.01')]),
    ("B13", "bug", "clamp rejects equal bounds", [(U, "    if low > high:", "    if low >= high:")]),
    ("B14", "bug", "percent guards wrong operand", [(U, "    if whole == 0:", "    if part == 0:")]),
    ("B15", "bug", "zero stock reported as low", [(I, "    if stock <= 0:", "    if stock < 0:")]),
    ("B16", "bug", "VIP threshold inclusive", [(P, 'if code == "VIP" and price < 50:',
                                                'if code == "VIP" and price <= 50:')]),
]
