from gradekit.penalties import apply_penalties, late_penalty


def test_late_penalty_small():
    assert late_penalty(0) == 0.0
    assert late_penalty(2) == 20.0


def test_apply_penalties_on_time():
    assert apply_penalties(80.0, 0, 0, 10) == 80.0
