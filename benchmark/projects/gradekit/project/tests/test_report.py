from gradekit.report import final_result


def test_final_result_good_student():
    assert final_result(90, 90, 90, 0, 0, 10) == {"score": 90.0, "letter": "A", "gpa": 4.0, "passed": True}
