"""Course statistics."""


def mean(values: list) -> float:
    if not values:
        raise ValueError("values must not be empty")
    return round(sum(values) / len(values), 2)


def median(values: list) -> float:
    if not values:
        raise ValueError("values must not be empty")
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2


def pass_rate(scores: list, pass_mark: float = 60.0) -> float:
    if not scores:
        return 0.0
    passed = sum(1 for s in scores if s >= pass_mark)
    return round(100.0 * passed / len(scores), 1)


def curve(score: float, top_score: float, target_top: float = 100.0) -> float:
    if top_score <= 0:
        raise ValueError("top_score must be positive")
    if score > top_score:
        raise ValueError("score cannot exceed top_score")
    return round(min(target_top, score * target_top / top_score), 1)
