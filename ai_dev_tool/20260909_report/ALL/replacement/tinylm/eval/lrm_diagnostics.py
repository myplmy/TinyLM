"""A09: WD-only 기준은 인과 분해가 아닌 명시적 초기값 대비 counterfactual이다."""
from __future__ import annotations
import math


def history_floor(rows, completed_steps):
    if not isinstance(completed_steps, int) or completed_steps < 0:
        raise ValueError("checkpoint step은 완료한 loop 수여야 함")
    if len(rows) < completed_steps:
        raise ValueError("checkpoint 시점까지의 LR history가 없음")
    value = 1.0
    for expected, row in enumerate(rows[:completed_steps]):
        if row.get("step") != expected or not isinstance(row.get("applied"), bool):
            raise ValueError("history는 step=0부터 연속, applied는 bool")
        lr, wd = float(row["lrm_lr"]), float(row["lrm_weight_decay"])
        if not all(math.isfinite(x) and x >= 0 for x in (lr, wd)):
            raise ValueError("유한한 LR/WD 필요")
        if row["applied"]:
            factor = 1.0 - lr * wd
            if factor <= 0:
                raise ValueError("WD factor가 양수가 아님")
            value *= factor
    if value <= 0:
        raise ValueError("WD 기준 underflow")
    return value


def describe_motion(values, floor):
    if not values or not all(math.isfinite(x) for x in values):
        raise ValueError("유효 LRM 값 0개 또는 nonfinite")
    raw = max(abs(x - 1.0) for x in values)
    corrected = None if floor is None else max(abs(x / floor - 1.0) for x in values)
    return {"elements": len(values), "mean": sum(values) / len(values),
            "min": min(values), "max": max(values), "max_abs_from_one": raw,
            "wd_only_floor": floor, "max_abs_ratio_from_wd_only": corrected,
            "motion_band": ("unresolved" if corrected is None else
                            "at_least_1pct" if corrected >= 1e-2 else
                            "below_1pct" if corrected >= 1e-4 else "below_1e-4"),
            "quality_verdict": None}
