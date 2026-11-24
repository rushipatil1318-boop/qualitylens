"""Letter grades, GPA points and weighted course scores."""

GRADE_BOUNDS = ((90, "A"), (80, "B"), (70, "C"), (60, "D"))
GPA_POINTS = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}
WEIGHTS = (0.5, 0.3, 0.2)


class GradeError(ValueError):
    """Raised for scores or letters outside the allowed range."""


def letter_grade(score: float) -> str:
    if score < 0 or score > 100:
        raise GradeError("score must be between 0 and 100")
    for bound, letter in GRADE_BOUNDS:
        if score >= bound:
            return letter
    return "F"


def gpa_points(letter: str) -> float:
    if letter not in GPA_POINTS:
        raise GradeError(f"unknown letter {letter}")
    return GPA_POINTS[letter]


def weighted_score(exam: float, project: float, homework: float) -> float:
    for part in (exam, project, homework):
        if part < 0 or part > 100:
            raise GradeError("each part must be between 0 and 100")
    w_exam, w_project, w_homework = WEIGHTS
    return round(w_exam * exam + w_project * project + w_homework * homework, 1)
