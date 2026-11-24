import pytest

from shopcalc.pricing import PricingError, apply_discount, bulk_discount_rate, tax_for


def test_save10_discount():
    assert apply_discount(100.0, "SAVE10") == 90.0


def test_unknown_voucher_raises():
    with pytest.raises(PricingError):
        apply_discount(20.0, "BOGUS")


def test_tax_germany():
    assert tax_for(100.0, "DE") == 19.0


def test_bulk_rate_small_and_large():
    assert bulk_discount_rate(5) == 0.0
    assert bulk_discount_rate(150) == 0.15
