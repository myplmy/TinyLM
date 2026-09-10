# -*- coding: utf-8 -*-
"""★A08 — **행렬 weight decay 라우팅**과 **opt-in 업데이트 계측**.

## 출처 — 외부 조치 패키지 A08 (2026-09-10 도입)

`ai_dev_tool/20260909_report/A08/replacement/tinylm/train/optimizer_audit.py`.
[적용 보고서](../../docs/20260910_외부-조치-패키지-적용-보고서.md) §A08.

★**가져오면서 고친 것 셋**:

| # | 원본 | ★우리 판 | 왜 |
|---|---|---|---|
| **1** | `from ..eval.audit_io import write_json_new` | ★`from ..audit_io import ...` | 함정 18 — 재수출 파일을 안 만들었다 |
| **2** | 계측 인스턴스가 **없어도** `matrix_decay_groups` 를 무조건 호출 | 그대로(값이 `None` 이면 **원본 그룹을 그대로 돌려준다**) | ✅**비트 동일**을 코드로 확인했다 |
| **3** | `OptimizerAudit` 이 `contract` 를 그대로 `json.dump` | ★**직렬화 불가 값을 `str()` 로 낮춘다** | `cfg.__dict__` 에 dataclass·tuple 이 섞이면 `allow_nan=False` 덤프가 죽는다 |

## 🚫이 파일이 하지 않는 것

- **기본 학습에서는 인스턴스를 만들지 않는다.** `--optimizer-audit` 이 없으면
  `OptimizerAudit` 은 import 조차 안 된다.
- ★**`matrix_weight_decay=None` 이면 `param_groups()` 를 손대지 않는다** — 반환값이
  `model.param_groups(lr)` **그 객체**다. 그래서 종전 런과 **비트 동일**이다.
- 🚫**선택 행렬 8개는 전체 행렬의 표본이 아니다** — 이름 순서에서 고르게 골랐을 뿐이다.
  ⚠️**분포로 일반화하지 않는다**(계약 json 이 그 문장을 함께 적는다).
- ⚠️**CPU 복사·계측 시간이 `ms/step` 에 섞인다** — 🚫**속도 판정 팔과 같이 켜지 않는다.**
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from ..audit_io import write_json_new


def matrix_decay_groups(model, lr, matrix_weight_decay=None):
    """행렬 집합은 Muon 정본 `split_params`, LR·비행렬 WD 는 `model.param_groups` 를 유지한다.

    반환 `(groups, matrices)`.

    ★**`matrix_weight_decay is None` 이면 아무것도 안 바꾼다** — 종전 경로 그대로다.
    ⚠️★**값을 주면 그룹 수가 늘어난다**(행렬/비행렬로 쪼개므로). LR 스케줄러는
    `zip(opt.param_groups, base_lrs)` 라 개수 변화에 안전하지만,
    🚫**인쇄용 `opt.param_groups[1]` 은 인덱스로 잡는다** — 그 자리는 `trainer` 가 따로 고른다.
    """
    from .muon import split_params
    matrices, _ = split_params(model)
    groups = model.param_groups(lr)
    if matrix_weight_decay is None:
        return groups, matrices
    if not math.isfinite(matrix_weight_decay) or matrix_weight_decay < 0:
        raise ValueError("matrix_weight_decay는 유한한 비음수")
    ids = {id(p) for p in matrices}
    result = []
    for group in groups:
        matrix = [p for p in group["params"] if id(p) in ids]
        other = [p for p in group["params"] if id(p) not in ids]
        if matrix:
            result.append(dict(group, params=matrix, weight_decay=matrix_weight_decay))
        if other:
            result.append(dict(group, params=other))
    return result, matrices


def _jsonable(value):
    """계약 json 에 넣기 전에 **직렬화 불가 값을 문자열로 낮춘다**(수정 3)."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    return str(value)


class OptimizerAudit:
    """매 update 의 LR·WD 와 **선택 행렬의 gradient/update/weight RMS** 를 JSONL 로 남긴다."""

    def __init__(self, path, model, optimizers, *, every, max_matrices=8, contract=None):
        from .muon import split_params
        self.path = Path(path)
        if self.path.exists() or self.path.with_suffix(".contract.json").exists():
            raise FileExistsError("optimizer-audit 출력이 이미 있음")
        if every < 1 or max_matrices < 1:
            raise ValueError("audit every/max_matrices는 양수")
        self.optimizers, self.every, self.before_values = optimizers, every, []
        names = {id(p): n for n, p in model.named_parameters()}
        matrices, _ = split_params(model)
        candidates = sorted([(names[id(p)], p) for p in matrices], key=lambda x: x[0])
        n = min(max_matrices, len(candidates))
        indices = sorted({round(i * (len(candidates) - 1) / max(1, n - 1)) for i in range(n)})
        self.selected = [candidates[i] for i in indices]
        self.groups = []
        self.lrm_group = None
        for opt_name, opt in optimizers:
            for i, group in enumerate(opt.param_groups):
                ns = [names[id(p)] for p in group["params"]]
                row = {"optimizer": opt_name, "group": i, "lr": group["lr"],
                       "weight_decay": group.get("weight_decay", 0), "names": ns,
                       "elements": sum(p.numel() for p in group["params"])}
                self.groups.append(row)
                if any(x.rsplit(".", 1)[-1].startswith("lrm") for x in ns):
                    if self.lrm_group is not None:
                        raise ValueError("LRM이 여러 그룹에 나뉨: LR history 규약 확장 필요")
                    self.lrm_group = group
        write_json_new(self.path.with_suffix(".contract.json"),
                       {"schema": "tinylm.optimizer-audit.v1",
                        "contract": _jsonable(contract),
                        "groups": self.groups,
                        "selected_matrices": [x for x, _ in self.selected],
                        "sample_note": "이름 순서에 고르게 고른 최대 8개; 전체 행렬 통계로 일반화 불가",
                        "timing_note": "CPU 복사/계측 시간이 step timing 에 포함; 별도 성능 결과로 쓰지 않음"})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("x", encoding="utf-8"):
            pass

    def before(self, step):
        self.before_values = []
        if step % self.every:
            return
        for name, p in self.selected:
            before = p.detach().float().cpu().clone()
            grad = p.grad
            grad_rms = None if grad is None else float(grad.detach().float().square().mean().sqrt())
            self.before_values.append((name, p, before, grad_rms))

    def after(self, step, applied):
        stats = []
        if applied:
            for name, p, before, grad_rms in self.before_values:
                after = p.detach().float().cpu()
                update = after - before
                rms = float(update.square().mean().sqrt())
                wrms = float(before.square().mean().sqrt())
                stats.append({"name": name, "elements": p.numel(),
                              "gradient_rms_after_clip": grad_rms,
                              "update_rms_including_wd": rms, "weight_rms_before": wrms,
                              "update_weight_ratio": rms / wrms if wrms else None})
        self.before_values = []
        row = {"step": step, "applied": bool(applied), "matrices": stats,
               "lr_groups": [{"optimizer": n, "lr": [g["lr"] for g in o.param_groups],
                              "weight_decay": [g.get("weight_decay", 0) for g in o.param_groups]}
                             for n, o in self.optimizers],
               "lrm_lr": self.lrm_group["lr"] if self.lrm_group is not None else 0.0,
               "lrm_weight_decay": (self.lrm_group.get("weight_decay", 0)
                                    if self.lrm_group is not None else 0.0)}
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
