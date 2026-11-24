"""Late submission and attendance penalties."""

MAX_LATE_DAYS = 5


def late_penalty(days_late: int) -> float:
    """Percentage of the score lost for a late submission."""
    if days_late < 0:
        raise ValueError("days_late must be non-negative")
    if days_late == 0:
        return 0.0
    if days_late > MAX_LATE_DAYS:
        return 100.0
    return 10.0 * days_late


def attendance_penalty(missed: int, total: int) -> float:
    """Points subtracted for missed sessions."""
    if total <= 0:
        raise ValueError("total must be positive")
    if missed < 0 or missed > total:
        raise ValueError("missed must be between 0 and total")
    rate = missed / total
    if rate <= 0.1:
        return 0.0
    if rate <= 0.25:
        return 5.0
    return 15.0


def apply_penalties(score: float, days_late: int, missed: int, total: int) -> float:
    adjusted = score - score * late_penalty(days_late) / 100 - attendance_penalty(missed, total)
    return max(0.0, round(adjusted, 1))
