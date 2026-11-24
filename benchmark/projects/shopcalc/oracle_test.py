"""Hidden specification tests. Never shown to QualityLens; used only to label benchmark cases.

A change is labelled as a defect when any of these tests fails at head.
"""
import pytest

from shopcalc.inventory import reorder_needed, reorder_quantity, stock_status
from shopcalc.orders import order_total
from shopcalc.pricing import PricingError, apply_discount, bulk_discount_rate, line_total, tax_for
from shopcalc.shipping import delivery_days, shipping_cost
from shopcalc.utils import clamp, percent, round_money


@pytest.mark.parametrize("value,expected", [(2.675, 2.68), (2.665, 2.67), (1.005, 1.01), (10.0, 10.0),
                                            (-1.005, -1.01), (0.0, 0.0)])
def test_round_money(value, expected):
    assert round_money(value) == expected


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10
    assert clamp(0, 0, 0) == 0
    with pytest.raises(ValueError):
        clamp(1, 5, 0)


def test_percent():
    assert percent(1, 4) == 25.0
    assert percent(1, 3) == 33.3
    assert percent(5, 0) == 0.0
    assert percent(0, 7) == 0.0


@pytest.mark.parametrize("price,code,expected", [
    (100.0, "", 100.0), (100.0, "SAVE10", 90.0), (100.0, "SAVE20", 80.0), (100.0, "VIP", 70.0),
    (49.99, "VIP", 42.49), (50.0, "VIP", 35.0), (0.0, "SAVE10", 0.0), (19.99, "SAVE20", 15.99),
])
def test_apply_discount(price, code, expected):
    assert apply_discount(price, code) == expected


def test_apply_discount_errors():
    with pytest.raises(PricingError):
        apply_discount(-0.01, "")
    with pytest.raises(PricingError):
        apply_discount(10.0, "save10")


@pytest.mark.parametrize("amount,country,expected", [(100.0, "DE", 19.0), (100.0, "AT", 20.0),
                                                     (100.0, "FR", 20.0), (100.0, "IN", 18.0),
                                                     (9.99, "DE", 1.9), (0.0, "AT", 0.0)])
def test_tax_for(amount, country, expected):
    assert tax_for(amount, country) == expected


def test_tax_unknown_country():
    with pytest.raises(PricingError):
        tax_for(10.0, "US")


@pytest.mark.parametrize("qty,rate", [(1, 0.0), (9, 0.0), (10, 0.05), (49, 0.05), (50, 0.10), (99, 0.10),
                                      (100, 0.15), (1000, 0.15)])
def test_bulk_discount_rate(qty, rate):
    assert bulk_discount_rate(qty) == rate


def test_line_total():
    assert line_total(2.0, 5) == 10.0
    assert line_total(2.0, 10) == 19.0
    assert line_total(1.0, 50) == 45.0
    assert line_total(1.0, 100) == 85.0
    with pytest.raises(PricingError):
        line_total(2.0, 0)
    with pytest.raises(PricingError):
        line_total(2.0, -1)


@pytest.mark.parametrize("w,zone,value,expected", [
    (1.0, "domestic", 0.0, 4.9), (2.0, "domestic", 0.0, 4.9), (3.0, "domestic", 0.0, 6.4),
    (1.0, "domestic", 75.0, 0.0), (1.0, "domestic", 74.99, 4.9), (1.0, "eu", 100.0, 9.9),
    (5.0, "eu", 0.0, 14.4), (20.0, "world", 0.0, 46.9), (21.0, "world", 0.0, 73.4), (0.5, "world", 0.0, 19.9),
])
def test_shipping_cost(w, zone, value, expected):
    assert shipping_cost(w, zone, value) == expected


def test_shipping_errors():
    with pytest.raises(ValueError):
        shipping_cost(0, "eu")
    with pytest.raises(ValueError):
        shipping_cost(-1.0, "eu")
    with pytest.raises(ValueError):
        shipping_cost(1.0, "moon")


@pytest.mark.parametrize("zone,express,days", [("domestic", False, 2), ("domestic", True, 1), ("eu", False, 5),
                                               ("eu", True, 2), ("world", False, 10), ("world", True, 5)])
def test_delivery_days(zone, express, days):
    assert delivery_days(zone, express) == days


def test_delivery_days_unknown_zone():
    with pytest.raises(KeyError):
        delivery_days("moon")


def test_reorder_needed():
    assert reorder_needed(15, 2, 5) is True        # point = 15
    assert reorder_needed(16, 2, 5) is False
    assert reorder_needed(5, 0, 0) is True
    assert reorder_needed(6, 0, 0) is False
    assert reorder_needed(20, 2, 5, safety_stock=10) is True
    with pytest.raises(ValueError):
        reorder_needed(1, -1, 1)
    with pytest.raises(ValueError):
        reorder_needed(1, 1, -1)


def test_reorder_quantity():
    assert reorder_quantity(3, 10) == 7
    assert reorder_quantity(3, 10, pack_size=4) == 8
    assert reorder_quantity(2, 10, pack_size=4) == 8
    assert reorder_quantity(1, 10, pack_size=4) == 12
    assert reorder_quantity(10, 10) == 0
    assert reorder_quantity(12, 10) == 0
    with pytest.raises(ValueError):
        reorder_quantity(1, 2, pack_size=0)


def test_stock_status():
    assert stock_status(0, 10) == "out_of_stock"
    assert stock_status(-2, 10) == "out_of_stock"
    assert stock_status(1, 10) == "low"
    assert stock_status(10, 10) == "low"
    assert stock_status(11, 10) == "ok"


def test_order_total():
    assert order_total(10.0, 3, "SAVE10", "DE", 1.0, "domestic") == 37.03
    assert order_total(10.0, 10, "", "DE", 3.0, "domestic") == 113.05
    assert order_total(10.0, 10, "VIP", "AT", 3.0, "eu") == 91.2
    assert order_total(2.0, 50, "SAVE20", "IN", 25.0, "world") == 164.36
