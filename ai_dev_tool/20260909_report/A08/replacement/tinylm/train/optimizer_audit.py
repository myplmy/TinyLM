"""A08 opt-in update 계측. 기본 학습에서는 인스턴스를 만들지 않는다."""
from __future__ import annotations
import math
from pathlib import Path
from ..eval.audit_io import write_json_new


def matrix_decay_groups(model, lr, matrix_weight_decay=None):
    """행렬 집합은 Muon 정본 split_params, LR/비행렬 WD는 model.param_groups를 유지."""
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


class OptimizerAudit:
    def __init__(self, path, model, optimizers, *, every, max_matrices=8, contract=None):
        import json
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
                if any(n.rsplit(".", 1)[-1].startswith("lrm") for n in ns):
                    if self.lrm_group is not None:
                        raise ValueError("LRM이 여러 그룹에 나뉨: LR history 규약 확장 필요")
                    self.lrm_group = group
        write_json_new(self.path.with_suffix(".contract.json"),
                       {"schema": "tinylm.optimizer-audit.v1", "contract": contract,
                        "groups": self.groups, "selected_matrices": [n for n, _ in self.selected],
                        "sample_note": "이름 순서에 고르게 고른 최대 8개; 전체 행렬 통계로 일반화 불가",
                        "timing_note": "CPU 복사/계측 시간이 step timing에 포함; 별도 성능 결과로 쓰지 않음"})
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
        import json
        stats = []
        if applied:
            for name, p, before, grad_rms in self.before_values:
                after = p.detach().float().cpu()
                update = after - before
                rms = float(update.square().mean().sqrt())
                wrms = float(before.square().mean().sqrt())
                stats.append({"name": name, "elements": p.numel(), "gradient_rms_after_clip": grad_rms,
                              "update_rms_including_wd": rms, "weight_rms_before": wrms,
                              "update_weight_ratio": rms / wrms if wrms else None})
        self.before_values = []
        row = {"step": step, "applied": bool(applied), "matrices": stats,
               "lr_groups": [{"optimizer": n, "lr": [g["lr"] for g in o.param_groups],
                               "weight_decay": [g.get("weight_decay", 0) for g in o.param_groups]}
                              for n, o in self.optimizers],
               "lrm_lr": self.lrm_group["lr"] if self.lrm_group is not None else 0.0,
               "lrm_weight_decay": self.lrm_group.get("weight_decay", 0)
                                   if self.lrm_group is not None else 0.0}
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
