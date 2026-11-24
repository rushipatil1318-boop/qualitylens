from shopcalc.orders import order_total


def test_order_total_end_to_end():
    assert order_total(10.0, 3, "SAVE10", "DE", 1.0, "domestic") == 37.03
