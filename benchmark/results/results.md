| Project | Case | Kind | Change | Score | Coverage before -> after | Mutation before -> after |
|---|---|---|---|---|---|---|
| shopcalc | R01 | refactor | rename local in apply_discount | 88.6 | 67% -> 100% | 75% -> 100% |
| shopcalc | R02 | refactor | extract weight surcharge helper | 91.5 | 83% -> 100% | 86% -> 100% |
| shopcalc | R03 | refactor | math.ceil in reorder_quantity | 98.5 | 100% -> 100% | 100% -> 100% |
| shopcalc | R04 | refactor | docstring for clamp | 99.2 | - -> - | - -> - |
| shopcalc | R05 | refactor | dict.get in tax_for | 97.6 | 100% -> 100% | 100% -> 100% |
| shopcalc | R06 | refactor | elif chain in stock_status | 76.4 | 60% -> 100% | 0% -> 100% |
| shopcalc | R07 | refactor | rename variables in order_total | 97.4 | 100% -> 100% | 100% -> 100% |
| shopcalc | R08 | refactor | module constant for delivery days | 88.1 | 100% -> 100% | 33% -> 100% |
| shopcalc | R09 | refactor | table-driven bulk tiers | 83.4 | 100% -> 100% | 14% -> 100% |
| shopcalc | R10 | refactor | truthiness check in percent | 68.8 | 0% -> 100% | 0% -> 100% |
| shopcalc | R11 | refactor | clearer error message in shipping_cost | 83.3 | 0% -> 100% | - -> - |
| shopcalc | R12 | refactor | constant for cent quantum | 95.6 | 100% -> 100% | - -> - |
| shopcalc | T01 | test | tests for reorder_needed | 100.0 | - -> - | - -> - |
| shopcalc | T02 | test | boundary tests for bulk tiers | 100.0 | - -> - | - -> - |
| shopcalc | T03 | test | free shipping test | 100.0 | - -> - | - -> - |
| shopcalc | F01 | feature | add NL tax rate | 89.3 | 100% -> 100% | 40% -> 80% |
| shopcalc | F02 | feature | WELCOME5 voucher | 90.8 | 100% -> 100% | 50% -> 100% |
| shopcalc | F03 | feature | world express takes 4 days | 88.8 | 100% -> 100% | 40% -> 60% |
| shopcalc | F04 | feature | safety stock default 10 | 98.8 | - -> - | 100% -> 100% |
| shopcalc | F05 | feature | free shipping from 60 | 98.3 | 100% -> 100% | 100% -> 100% |
| shopcalc | F06 | feature | overstock status | 97.8 | 100% -> 100% | 100% -> 100% |
| shopcalc | F07 | feature | percent with 2 decimals | 95.1 | 100% -> 100% | 75% -> 100% |
| shopcalc | F08 | feature | case-insensitive vouchers | 98.7 | 100% -> 100% | - -> - |
| shopcalc | B01 | bug | bulk tier off-by-one | 57.8 | 100% -> 100% | 0% -> 100% |
| shopcalc | B02 | bug | free shipping boundary | 63.3 | 100% -> 100% | 33% -> 67% |
| shopcalc | B03 | bug | VIP small-order rate typo | 43.3 | 0% -> 100% | 0% -> 100% |
| shopcalc | B04 | bug | bankers rounding | 95.8 | 100% -> 100% | - -> - |
| shopcalc | B05 | bug | reorder point exclusive | 43.8 | 0% -> 100% | 0% -> 100% |
| shopcalc | B06 | bug | silent default tax rate | 65.3 | 100% -> 100% | 50% -> 50% |
| shopcalc | B07 | bug | reorder packs rounded down | 43.8 | 100% -> 100% | 100% -> 100% |
| shopcalc | B08 | bug | tax on undiscounted subtotal | 68.8 | 100% -> 100% | - -> - |
| shopcalc | B09 | bug | surcharge on full weight | 43.3 | 100% -> 100% | 100% -> 100% |
| shopcalc | B10 | bug | express divides by 3 | 43.8 | 0% -> 100% | 0% -> 100% |
| shopcalc | B11 | bug | zero quantity accepted | 58.3 | 100% -> 100% | 0% -> 100% |
| shopcalc | B12 | bug | SAVE10 rate typo | 43.3 | 100% -> 100% | 100% -> 100% |
| shopcalc | B13 | bug | clamp rejects equal bounds | 43.8 | 0% -> 100% | 0% -> 100% |
| shopcalc | B14 | bug | percent guards wrong operand | 43.8 | 0% -> 100% | 0% -> 50% |
| shopcalc | B15 | bug | zero stock reported as low | 58.8 | 100% -> 100% | 0% -> 100% |
| shopcalc | B16 | bug | VIP threshold inclusive | 65.8 | 100% -> 100% | 50% -> 75% |
| shopcalc | SG01 | bug | generated: cost += (weight_kg - 2) * 1.5 -> cost += (weight_kg - 2) * 1.55 | 43.3 | 100% -> 100% | 100% -> 100% |
| shopcalc | SG02 | bug | generated: if price < 0: -> if price < 1: | 58.3 | 100% -> 100% | 0% -> 100% |
| shopcalc | SG03 | bug | generated: if quantity >= 50: -> if quantity >= 51: | 57.8 | 100% -> 100% | 0% -> 100% |
| shopcalc | SG04 | bug | generated: days = {"domestic": 2, "eu": 5, "world": 10}[zone] -> days = {"domestic": 3, "eu": 5, "world": 10}[zone] | 63.8 | 100% -> 100% | 33% -> 100% |
| shopcalc | SG05 | bug | generated: return round_money(discounted + tax + shipping) -> return round_money(discounted - tax + shipping) | 61.3 | 100% -> 100% | 50% -> 50% |
| shopcalc | SG06 | bug | generated: if whole == 0: -> if whole == 1: | 43.8 | 0% -> 100% | 0% -> 100% |
| shopcalc | SG07 | bug | generated: days = max(1, days // 2) -> days = max(1, days // 3) | 43.8 | 0% -> 100% | 0% -> 100% |
| shopcalc | SG08 | bug | generated: if zone == "domestic" and order_value >= FREE_SHIPPING_THRESHOLD: -> if zone == "domestic" and order_value > FREE_SHIPPING_THRESHOLD: | 63.3 | 100% -> 100% | 33% -> 67% |
| shopcalc | SG09 | bug | generated: return 0 -> return 1 | 43.8 | 0% -> 100% | 0% -> 100% |
| shopcalc | SG10 | bug | generated: return round_money(price * (1 - rate)) -> return round_money(price * (2 - rate)) | 43.3 | 100% -> 100% | 100% -> 100% |
| shopcalc | SG11 | bug | generated: return round_money(gross * (1 - bulk_discount_rate(quantity))) -> return round_money(gross / (1 - bulk_discount_rate(quantity))) | 63.3 | 100% -> 100% | 33% -> 100% |
| shopcalc | SG12 | bug | generated: return 0.05 -> return 0.10 | 42.8 | 0% -> 100% | 0% -> 100% |
| gradekit | GR01 | refactor | rename loop variables in letter_grade | 97.4 | 100% -> 100% | 100% -> 100% |
| gradekit | GR02 | refactor | dict.get in gpa_points | 97.6 | 100% -> 100% | - -> - |
| gradekit | GR03 | refactor | zip-based weighted sum | 89.5 | 100% -> 100% | 50% -> 100% |
| gradekit | GR04 | refactor | docstring wording in late_penalty | 97.8 | - -> - | - -> - |
| gradekit | GR05 | refactor | named attendance thresholds | 74.4 | 50% -> 100% | 0% -> 25% |
| gradekit | GR06 | refactor | length variable in median | 68.1 | 0% -> 100% | 0% -> 67% |
| gradekit | GR07 | refactor | list comprehension in pass_rate | 83.8 | 100% -> 100% | 0% -> 100% |
| gradekit | GR08 | refactor | reorder guards in curve | 68.3 | 0% -> 100% | 0% -> 100% |
| gradekit | GR09 | refactor | named fields in final_result | 98.3 | 100% -> 100% | 100% -> 100% |
| gradekit | GR10 | refactor | total variable in mean | 91.0 | 100% -> 100% | 50% -> 50% |
| gradekit | GT01 | test | attendance penalty tests | 100.0 | - -> - | - -> - |
| gradekit | GT02 | test | curve tests | 100.0 | - -> - | - -> - |
| gradekit | GF01 | feature | allow up to 7 late days | 97.8 | 100% -> 100% | 100% -> 100% |
| gradekit | GF02 | feature | new weights 40/40/20 | 98.3 | 100% -> 100% | 100% -> 100% |
| gradekit | GF03 | feature | new E grade | 87.3 | 100% -> 100% | 30% -> 70% |
| gradekit | GF04 | feature | pass mark default 50 | 98.8 | - -> - | 100% -> 100% |
| gradekit | GF05 | feature | cap scores above top instead of failing | 98.8 | 100% -> 100% | - -> - |
| gradekit | GF06 | feature | lighter middle attendance tier | 97.8 | 100% -> 100% | 100% -> 100% |
| gradekit | GB01 | bug | grade boundary exclusive | 28.3 | 100% -> 100% | 0% -> 100% |
| gradekit | GB02 | bug | 100 rejected | 61.3 | 100% -> 100% | 20% -> 100% |
| gradekit | GB03 | bug | wrong GPA for D | 64.3 | 100% -> 100% | 40% -> 100% |
| gradekit | GB04 | bug | validation never fires | 58.3 | 100% -> 100% | 0% -> 20% |
| gradekit | GB05 | bug | max late day counted as too late | 57.8 | 100% -> 100% | 0% -> 100% |
| gradekit | GB06 | bug | attendance tier boundary | 57.8 | 100% -> 100% | 0% -> 0% |
| gradekit | GB07 | bug | late penalty applied as points | 58.3 | 100% -> 100% | 0% -> 100% |
| gradekit | GB08 | bug | integer division in median | 68.8 | 0% -> 0% | 0% -> 0% |
| gradekit | GB09 | bug | pass mark exclusive | 66.3 | 100% -> 100% | 50% -> 100% |
| gradekit | GB10 | bug | curve uses max | 43.8 | 0% -> 100% | 0% -> 100% |
| gradekit | GB11 | bug | D treated as fail | 98.8 | 100% -> 100% | 100% -> 100% |
| gradekit | GB12 | bug | mean rounded to 1 decimal | 91.3 | 100% -> 100% | 50% -> 50% |
| gradekit | GG01 | bug | generated: if days_late > MAX_LATE_DAYS: -> if days_late >= MAX_LATE_DAYS: | 57.8 | 100% -> 100% | 0% -> 100% |
| gradekit | GG02 | bug | generated: if rate <= 0.1: -> if rate < 0.1: | 57.8 | 100% -> 100% | 0% -> 0% |
| gradekit | GG03 | bug | generated: return 0.0 -> return 0.05 | 42.8 | 100% -> 100% | 100% -> 100% |
| gradekit | GG04 | bug | generated: if len(ordered) % 2 == 1: -> if len(ordered) % 2 != 1: | 43.8 | 0% -> 100% | 0% -> 75% |
| gradekit | GG05 | bug | generated: if part < 0 or part > 100: -> if part <= 0 or part > 100: | 58.3 | 100% -> 100% | 0% -> 40% |
| gradekit | GG06 | bug | generated: if len(ordered) % 2 == 1: -> if len(ordered) % 3 == 1: | 43.8 | 0% -> 100% | 0% -> 50% |
| gradekit | GG07 | bug | generated: return max(0.0, round(adjusted, 1)) -> return max(0.05, round(adjusted, 1)) | 58.3 | 100% -> 100% | 0% -> 100% |
| gradekit | GG08 | bug | generated: return round(w_exam * exam + w_project * project + w_homework * homework, 1) -> return round(w_exam * exam - w_project * project + w_homework * homework, 1) | 40.8 | 100% -> 100% | 83% -> 100% |
| gradekit | GG09 | bug | generated: return round(100.0 * passed / len(scores), 1) -> return round(100.0 * passed / len(scores), 2) | 43.8 | 100% -> 100% | 100% -> 100% |
| gradekit | GG10 | bug | generated: return 0.0 -> return 0.05 | 43.8 | 0% -> 100% | 0% -> 100% |
| gradekit | GG11 | bug | generated: if missed < 0 or missed > total: -> if missed < 0 or missed >= total: | 65.3 | 100% -> 100% | 50% -> 75% |
| gradekit | GG12 | bug | generated: if score > top_score: -> if score >= top_score: | 43.8 | 0% -> 100% | 0% -> 100% |
