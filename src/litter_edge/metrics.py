from __future__ import annotations

import math
import statistics


def _nearest_rank(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return ordered[index]


def summarize_samples(values: list[float]) -> dict[str, float | int | None]:
    """Summarize an observed sample using population standard deviation."""
    if not values:
        return {
            "count": 0,
            "mean": None,
            "standard_deviation": None,
            "median": None,
            "p95": None,
            "p99": None,
            "min": None,
            "max": None,
        }
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "standard_deviation": statistics.pstdev(values),
        "median": statistics.median(values),
        "p95": _nearest_rank(values, 0.95),
        "p99": _nearest_rank(values, 0.99),
        "min": min(values),
        "max": max(values),
    }
