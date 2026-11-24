import pytest

from gradekit.grades import GradeError, gpa_points, letter_grade, weighted_score


def test_letter_grade_top_and_fail():
    assert letter_grade(95) == "A"
    assert letter_grade(50) == "F"


def test_gpa_points():
    assert gpa_points("B") == 3.0


def test_weighted_score():
    assert weighted_score(80, 70, 90) == 79.0


def test_out_of_range_score():
    with pytest.raises(GradeError):
        letter_grade(101)
