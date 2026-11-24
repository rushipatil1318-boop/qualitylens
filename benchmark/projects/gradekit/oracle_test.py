"""Hidden specification tests for gradekit. Never shown to QualityLens; used only to label benchmark cases."""
import pytest

from gradekit.grades import GradeError, gpa_points, letter_grade, weighted_score
from gradekit.penalties import apply_penalties, attendance_penalty, late_penalty
from gradekit.report import final_result
from gradekit.stats import curve, mean, median, pass_rate


@pytest.mark.parametrize("score,letter", [(100, "A"), (90, "A"), (89.9, "B"), (80, "B"), (79.99, "C"), (70, "C"),
                                          (69.5, "D"), (60, "D"), (59.9, "F"), (0, "F")])
def test_letter_grade(score, letter):
    assert letter_grade(score) == letter


def test_letter_grade_range():
    for bad in (-0.1, 100.1, -5):
        with pytest.raises(GradeError):
            letter_grade(bad)


def test_gpa_points():
    assert [gpa_points(x) for x in "ABCDF"] == [4.0, 3.0, 2.0, 1.0, 0.0]
    with pytest.raises(GradeError):
        gpa_points("E")
    with pytest.raises(GradeError):
        gpa_points("a")


def test_weighted_score():
    assert weighted_score(80, 70, 90) == 79.0
    assert weighted_score(100, 100, 100) == 100.0
    assert weighted_score(0, 0, 0) == 0.0
    assert weighted_score(100, 0, 0) == 50.0
    assert weighted_score(0, 100, 0) == 30.0
    assert weighted_score(0, 0, 100) == 20.0
    for bad in ((101, 0, 0), (0, -1, 0), (0, 0, 100.5)):
        with pytest.raises(GradeError):
            weighted_score(*bad)


@pytest.mark.parametrize("days,penalty", [(0, 0.0), (1, 10.0), (3, 30.0), (5, 50.0), (6, 100.0), (30, 100.0)])
def test_late_penalty(days, penalty):
    assert late_penalty(days) == penalty


def test_late_penalty_negative():
    with pytest.raises(ValueError):
        late_penalty(-1)


@pytest.mark.parametrize("missed,total,penalty", [(0, 10, 0.0), (1, 10, 0.0), (2, 10, 5.0), (1, 4, 5.0),
                                                  (3, 10, 15.0), (10, 10, 15.0), (5, 20, 5.0), (6, 20, 15.0)])
def test_attendance_penalty(missed, total, penalty):
    assert attendance_penalty(missed, total) == penalty


def test_attendance_errors():
    for args in ((1, 0), (-1, 10), (11, 10)):
        with pytest.raises(ValueError):
            attendance_penalty(*args)


def test_apply_penalties():
    assert apply_penalties(80.0, 0, 0, 10) == 80.0
    assert apply_penalties(80.0, 2, 0, 10) == 64.0
    assert apply_penalties(80.0, 0, 2, 10) == 75.0
    assert apply_penalties(80.0, 1, 3, 10) == 57.0
    assert apply_penalties(10.0, 0, 5, 10) == 0.0
    assert apply_penalties(90.0, 6, 0, 10) == 0.0


def test_mean_median():
    assert mean([1, 2, 3]) == 2.0
    assert mean([1, 2]) == 1.5
    assert mean([2, 2, 3]) == 2.33
    assert median([3, 1, 2]) == 2.0
    assert median([4, 1, 3, 2]) == 2.5
    assert median([5]) == 5.0
    with pytest.raises(ValueError):
        mean([])
    with pytest.raises(ValueError):
        median([])


def test_pass_rate():
    assert pass_rate([50, 70, 90]) == 66.7
    assert pass_rate([60, 59.9]) == 50.0
    assert pass_rate([]) == 0.0
    assert pass_rate([70, 80], pass_mark=75) == 50.0


def test_curve():
    assert curve(80, 80) == 100.0
    assert curve(40, 80) == 50.0
    assert curve(45, 90, target_top=90) == 45.0
    assert curve(0, 50) == 0.0
    with pytest.raises(ValueError):
        curve(10, 0)
    with pytest.raises(ValueError):
        curve(91, 90)


def test_final_result():
    assert final_result(90, 90, 90, 0, 0, 10) == {"score": 90.0, "letter": "A", "gpa": 4.0, "passed": True}
    assert final_result(80, 70, 90, 1, 0, 10) == {"score": 71.1, "letter": "C", "gpa": 2.0, "passed": True}
    assert final_result(60, 60, 60, 0, 3, 10) == {"score": 45.0, "letter": "F", "gpa": 0.0, "passed": False}
    assert final_result(70, 50, 50, 0, 2, 10) == {"score": 55.0, "letter": "F", "gpa": 0.0, "passed": False}
    assert final_result(70, 60, 60, 0, 0, 10) == {"score": 65.0, "letter": "D", "gpa": 1.0, "passed": True}
