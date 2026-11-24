"""Hand-written benchmark changes on the gradekit project (same rules as shopcalc/cases.py)."""

G, PE, ST, RE = "gradekit/grades.py", "gradekit/penalties.py", "gradekit/stats.py", "gradekit/report.py"
TG, TP, TS = "tests/test_grades.py", "tests/test_penalties.py", "tests/test_stats.py"
APPEND = None

CASES = [
    # ---------------- refactors ----------------
    ("GR01", "refactor", "rename loop variables in letter_grade", [(G,
        "    for bound, letter in GRADE_BOUNDS:\n        if score >= bound:\n            return letter",
        "    for threshold, grade in GRADE_BOUNDS:\n        if score >= threshold:\n            return grade")]),
    ("GR02", "refactor", "dict.get in gpa_points", [(G,
        "    if letter not in GPA_POINTS:\n        raise GradeError(f\"unknown letter {letter}\")\n"
        "    return GPA_POINTS[letter]",
        "    points = GPA_POINTS.get(letter)\n    if points is None:\n"
        "        raise GradeError(f\"unknown letter {letter}\")\n    return points")]),
    ("GR03", "refactor", "zip-based weighted sum", [(G,
        "    w_exam, w_project, w_homework = WEIGHTS\n"
        "    return round(w_exam * exam + w_project * project + w_homework * homework, 1)",
        "    return round(sum(w * p for w, p in zip(WEIGHTS, (exam, project, homework))), 1)")]),
    ("GR04", "refactor", "docstring wording in late_penalty", [(PE,
        '    """Percentage of the score lost for a late submission."""',
        '    """Return the share of the score (in percent) lost for submitting late."""')]),
    ("GR05", "refactor", "named attendance thresholds", [
        (PE, "MAX_LATE_DAYS = 5\n", "MAX_LATE_DAYS = 5\nLOW_ABSENCE = 0.1\nHIGH_ABSENCE = 0.25\n"),
        (PE, "    if rate <= 0.1:\n        return 0.0\n    if rate <= 0.25:",
             "    if rate <= LOW_ABSENCE:\n        return 0.0\n    if rate <= HIGH_ABSENCE:")]),
    ("GR06", "refactor", "length variable in median", [(ST,
        "    mid = len(ordered) // 2\n    if len(ordered) % 2 == 1:",
        "    n = len(ordered)\n    mid = n // 2\n    if n % 2 == 1:")]),
    ("GR07", "refactor", "list comprehension in pass_rate", [(ST,
        "    passed = sum(1 for s in scores if s >= pass_mark)",
        "    passed = len([s for s in scores if s >= pass_mark])")]),
    ("GR08", "refactor", "reorder guards in curve", [(ST,
        "    if top_score <= 0:\n        raise ValueError(\"top_score must be positive\")\n"
        "    if score > top_score:\n        raise ValueError(\"score cannot exceed top_score\")",
        "    if score > top_score > 0:\n        raise ValueError(\"score cannot exceed top_score\")\n"
        "    if top_score <= 0:\n        raise ValueError(\"top_score must be positive\")")]),
    ("GR09", "refactor", "named fields in final_result", [(RE,
        '    return {"score": final, "letter": letter, "gpa": gpa_points(letter), "passed": letter != "F"}',
        '    passed = letter != "F"\n    gpa = gpa_points(letter)\n'
        '    return {"score": final, "letter": letter, "gpa": gpa, "passed": passed}')]),
    ("GR10", "refactor", "total variable in mean", [(ST,
        "    return round(sum(values) / len(values), 2)",
        "    total = sum(values)\n    return round(total / len(values), 2)")]),
    # ---------------- test-only ----------------
    ("GT01", "test", "attendance penalty tests", [(TP, APPEND,
        "\n\ndef test_attendance_tiers():\n    from gradekit.penalties import attendance_penalty\n"
        "    assert attendance_penalty(1, 10) == 0.0\n    assert attendance_penalty(2, 10) == 5.0\n"
        "    assert attendance_penalty(3, 10) == 15.0\n")]),
    ("GT02", "test", "curve tests", [(TS, APPEND,
        "\n\ndef test_curve():\n    from gradekit.stats import curve\n    assert curve(40, 80) == 50.0\n")]),
    # ---------------- features with tests ----------------
    ("GF01", "feature", "allow up to 7 late days", [(PE, "MAX_LATE_DAYS = 5", "MAX_LATE_DAYS = 7"),
        (TP, APPEND, "\n\ndef test_seven_late_days():\n    assert late_penalty(6) == 60.0\n"
                     "    assert late_penalty(8) == 100.0\n")]),
    ("GF02", "feature", "new weights 40/40/20", [(G, "WEIGHTS = (0.5, 0.3, 0.2)", "WEIGHTS = (0.4, 0.4, 0.2)"),
        (TG, "assert weighted_score(80, 70, 90) == 79.0", "assert weighted_score(80, 70, 90) == 78.0")]),
    ("GF03", "feature", "new E grade", [
        (G, '((90, "A"), (80, "B"), (70, "C"), (60, "D"))', '((90, "A"), (80, "B"), (70, "C"), (60, "D"), (50, "E"))'),
        (G, '"D": 1.0, "F": 0.0}', '"D": 1.0, "E": 0.5, "F": 0.0}'),
        (TG, '    assert letter_grade(50) == "F"', '    assert letter_grade(45) == "F"\n'
                                                  '    assert letter_grade(55) == "E"')]),
    ("GF04", "feature", "pass mark default 50", [(ST, "pass_mark: float = 60.0", "pass_mark: float = 50.0"),
        (TS, "assert pass_rate([50, 70, 90]) == 66.7", "assert pass_rate([50, 70, 90]) == 100.0\n"
                                                       "    assert pass_rate([49, 70]) == 50.0")]),
    ("GF05", "feature", "cap scores above top instead of failing", [(ST,
        "    if score > top_score:\n        raise ValueError(\"score cannot exceed top_score\")",
        "    if score > top_score:\n        score = top_score"),
        (TS, APPEND, "\n\ndef test_curve_caps_above_top():\n    from gradekit.stats import curve\n"
                     "    assert curve(95, 90) == 100.0\n")]),
    ("GF06", "feature", "lighter middle attendance tier", [(PE, "        return 5.0", "        return 3.0"),
        (TP, APPEND, "\n\ndef test_middle_attendance_tier():\n    from gradekit.penalties import attendance_penalty\n"
                     "    assert attendance_penalty(2, 10) == 3.0\n")]),
    # ---------------- bugs ----------------
    ("GB01", "bug", "grade boundary exclusive", [(G, "        if score >= bound:", "        if score > bound:")]),
    ("GB02", "bug", "100 rejected", [(G, "if score < 0 or score > 100:", "if score < 0 or score >= 100:")]),
    ("GB03", "bug", "wrong GPA for D", [(G, '"D": 1.0', '"D": 1.5')]),
    ("GB04", "bug", "validation never fires", [(G, "        if part < 0 or part > 100:",
                                                "        if part < 0 and part > 100:")]),
    ("GB05", "bug", "max late day counted as too late", [(PE, "if days_late > MAX_LATE_DAYS:",
                                                          "if days_late >= MAX_LATE_DAYS:")]),
    ("GB06", "bug", "attendance tier boundary", [(PE, "if rate <= 0.1:", "if rate < 0.1:")]),
    ("GB07", "bug", "late penalty applied as points", [(PE, "score * late_penalty(days_late) / 100",
                                                        "late_penalty(days_late)")]),
    ("GB08", "bug", "integer division in median", [(ST, "(ordered[mid - 1] + ordered[mid]) / 2",
                                                    "(ordered[mid - 1] + ordered[mid]) // 2")]),
    ("GB09", "bug", "pass mark exclusive", [(ST, "if s >= pass_mark", "if s > pass_mark")]),
    ("GB10", "bug", "curve uses max", [(ST, "round(min(target_top,", "round(max(target_top,")]),
    ("GB11", "bug", "D treated as fail", [(RE, '"passed": letter != "F"', '"passed": letter not in ("F", "D")')]),
    ("GB12", "bug", "mean rounded to 1 decimal", [(ST, "return round(sum(values) / len(values), 2)",
                                                   "return round(sum(values) / len(values), 1)")]),
]
