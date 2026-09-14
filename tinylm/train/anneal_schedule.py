# -*- coding: utf-8 -*-
"""TinyLM 학습에서 서로 다른 세 스케줄의 순수 수학 계약.

이 모듈은 모델이나 GPU를 import하지 않는다. ``trainer``가 2026-09-15 이전에
직접 계산하던 식을 그대로 옮겨, LR cooldown·삼진 전이·보조경로 제거를 서로
다른 함수로 고정한다. 기본 인자에서 수치와 분기 순서는 종전과 같다.
"""
from __future__ import annotations

import math


def lr_factor(step, warm, steps, sched, decay_frac=0.2):
    """cosine/WSD/stable/decay 학습률 배율(종전 ``trainer._lr_factor``)."""
    if sched == "decay":
        return 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * step / max(steps, 1)))
    if step < warm:
        return (step + 1) / warm
    progress = (step - warm) / max(steps - warm, 1)
    if sched == "stable":
        return 1.0
    if sched == "wsd":
        if progress < 1.0 - decay_frac:
            return 1.0
        cooldown = (progress - (1.0 - decay_frac)) / decay_frac
        return 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * cooldown))
    return 0.1 + 0.45 * (1 + math.cos(math.pi * progress))


def resolve_quant_start(warm, steps, anneal_start=None):
    """명시값이 없을 때 쓰던 ``warm / steps + 0.05`` 계약을 한 곳에 둔다."""
    if steps <= 0:
        raise ValueError("steps는 양수여야 한다")
    return (warm / steps + 0.05) if anneal_start is None else float(anneal_start)


def quant_anneal_factor(step, steps, sched, shape, start, end):
    """FP(0)에서 완전 삼진(1)으로 가는 전이 계수.

    ``sched=decay``는 이미 학습된 plateau에서 분기하므로 종전처럼 항상 1이다.
    ``shape=step``에서 ``end``는 직렬화되는 실험 조건이지만 전이점은 ``start``다.
    """
    if steps <= 0:
        raise ValueError("steps는 양수여야 한다")
    if sched == "decay":
        return 1.0
    if shape == "step":
        return 1.0 if (step / steps) >= start else 0.0
    if shape != "linear":
        raise ValueError(f"지원하지 않는 quant anneal shape: {shape}")
    return min(1.0, max(0.0, (step / steps - start) / max(end - start, 1e-6)))


def auxiliary_decay_factor(step, steps, end):
    """Arenas/LoRA 보조경로의 1→0 선형 제거 계수(종전 식과 동일)."""
    if steps <= 0:
        raise ValueError("steps는 양수여야 한다")
    return max(0.0, 1.0 - (step / steps) / max(end, 1e-6))
