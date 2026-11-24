from shopcalc.inventory import reorder_quantity, stock_status


def test_reorder_quantity_packs():
    assert reorder_quantity(3, 10, pack_size=4) == 8


def test_stock_status_ok():
    assert stock_status(50, 10) == "ok"
