"""Final course result for one student."""
from gradekit.grades import gpa_points, letter_grade, weighted_score
from gradekit.penalties import apply_penalties


def final_result(exam: float, project: float, homework: float, days_late: int, missed: int, total: int) -> dict:
    raw = weighted_score(exam, project, homework)
    final = apply_penalties(raw, days_late, missed, total)
    letter = letter_grade(final)
    return {"score": final, "letter": letter, "gpa": gpa_points(letter), "passed": letter != "F"}
