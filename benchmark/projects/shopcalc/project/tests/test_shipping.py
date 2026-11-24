from shopcalc.shipping import delivery_days, shipping_cost


def test_domestic_light_parcel():
    assert shipping_cost(1.0, "domestic") == 4.9


def test_eu_heavy_parcel():
    assert shipping_cost(5.0, "eu") == 14.4


def test_delivery_days_standard():
    assert delivery_days("eu") == 5
