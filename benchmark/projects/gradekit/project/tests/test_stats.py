from gradekit.stats import mean, pass_rate


def test_mean():
    assert mean([1, 2, 3]) == 2.0


def test_pass_rate():
    assert pass_rate([50, 70, 90]) == 66.7
