## QualityLens hotspots

_Demo: scripted history of 12 commits by placeholder authors on the shopcalc sample code._

Files that change often and are complex are where defects concentrate. Bug-fix commits and untested functions show where tests would pay off first.

| File | Hotspot | Commits | Bug fixes | Complexity | Most complex | Untested functions |
|---|---|---|---|---|---|---|
| `shopcalc/pricing.py` | 100.0 | 7 | 3 (43%) | 14 | apply_discount (6) | - |
| `shopcalc/shipping.py` | 36.7 | 4 | 2 (50%) | 9 | shipping_cost (7) | - |
| `shopcalc/inventory.py` | 18.4 | 2 | 0 (0%) | 9 | reorder_needed (3) | reorder_needed |
| `shopcalc/utils.py` | 10.2 | 2 | 0 (0%) | 5 | clamp (2) | clamp, percent |
| `shopcalc/orders.py` | 2.0 | 2 | 0 (0%) | 1 | order_total (1) | - |
