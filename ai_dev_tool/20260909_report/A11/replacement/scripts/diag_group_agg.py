#!/usr/bin/env python3
"""A11: 실제 dense 부모 cfg/state와 정본 MLP 그룹 규약으로 집약 기하를 읽는다."""
from __future__ import annotations
import argparse
import dataclasses
import json
import math
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.config import mlp_group_members
from tinylm.model.checkpoint_io import read_checkpoint
from tinylm.eval.audit_io import sha256_file, write_json_new


def group_geometry(weights):
    import torch
    if len(weights) < 2:
        raise ValueError("집약에는 둘 이상의 부모 tensor 필요")
    if len({tuple(w.shape) for w in weights}) != 1:
        raise ValueError("부모 tensor shape 불일치")
    mean = torch.zeros_like(weights[0], dtype=torch.float64)
    unit_sum = torch.zeros_like(mean)
    norms = []
    for weight in weights:
        w = weight.detach().to(dtype=torch.float64, device="cpu")
        norm = float(w.norm())
        if not math.isfinite(norm) or norm <= 0:
            raise ValueError("0 또는 nonfinite norm")
        mean.add_(w, alpha=1.0 / len(weights))
        unit_sum.add_(w, alpha=1.0 / norm)
        norms.append(norm)
    n = len(weights)
    cosine = (float(unit_sum.square().sum()) - n) / (n * (n - 1))
    return {"mean_norm": float(mean.norm()), "mean_parent_norm": sum(norms) / n,
            "shrink_ratio": float(mean.norm()) / (sum(norms) / n),
            "mean_pair_cosine": min(1.0, max(-1.0, cosine)),
            "parent_norms": norms, "elements": weights[0].numel()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", required=True, help="미타잉 dense 부모")
    ap.add_argument("--student-checkpoint", help="집약할 학생 cfg를 읽음; 같은 middle 깊이만 지원")
    ap.add_argument("--group", type=int, help="학생 checkpoint가 없을 때 필수")
    ap.add_argument("--split", type=int, nargs="*", default=[])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    state, parent, _ = read_checkpoint(a.checkpoint)
    if parent.tie_mlp:
        raise ValueError("부모 cfg.tie_mlp=True: 이미 공유된 tensor로 집약 전 상쇄를 잴 수 없음")
    if a.student_checkpoint:
        if a.group is not None or a.split:
            ap.error("student checkpoint와 group/split 혼용 금지")
        _, target, _ = read_checkpoint(a.student_checkpoint)
    else:
        if a.group is None or a.group < 1:
            ap.error("--group 양수 필요")
        if a.split != sorted(set(a.split)) or any(
                s <= 0 or s >= parent.n_middle for s in a.split):
            ap.error("split은 middle 내부의 증가하는 경계")
        target = dataclasses.replace(parent, tie_mlp=True, mlp_group=a.group,
                                     mlp_split=tuple(a.split))
    if not target.tie_mlp or target.n_middle != parent.n_middle:
        raise ValueError("이 도구는 동일 middle 깊이의 dense->tied 집약만 지원; 깊이 이식은 별도 규약")
    if (target.dim, target.ffn_dim) != (parent.dim, parent.ffn_dim):
        raise ValueError("부모/학생 투영 shape가 다름")
    indices = {int(k.split(".")[1]) for k in state
               if k.startswith("mid_mlps.") and k.split(".")[1].isdigit()}
    if indices != set(range(parent.n_middle)):
        raise ValueError(f"mid_mlps 인덱스 불완전: {sorted(indices)}")
    rows, groups, covered = [], [], []
    for gi in range(target.n_mlp_groups):
        members = mlp_group_members(target, gi)
        if not members:
            raise ValueError("정본 함수가 빈 그룹을 반환")
        covered.extend(members)
        groups.append(members)
        if len(members) == 1:
            continue
        for projection in ("gate_proj", "up_proj", "down_proj"):
            keys = [f"mid_mlps.{j}.{projection}.weight" for j in members]
            missing = [k for k in keys if k not in state]
            if missing:
                raise ValueError(f"MLP 투영 key 없음: {missing}")
            rows.append({"group": gi, "members": members, "projection": projection,
                         "source_keys": keys, **group_geometry([state[k] for k in keys])})
    if sorted(covered) != list(range(parent.n_middle)) or not rows:
        raise ValueError("그룹 coverage 불완전 또는 집약할 MLP 0개")
    result = {"schema": "tinylm.group-aggregation.v2",
              "checkpoint_sha256": sha256_file(a.checkpoint),
              "student_checkpoint_sha256": sha256_file(a.student_checkpoint) if a.student_checkpoint else None,
              "parent_cfg": dataclasses.asdict(parent), "target_cfg": dataclasses.asdict(target),
              "groups": groups, "rows": rows,
              "mapping_contract": "동일 middle 깊이; config.mlp_group_members. 방문 순서와 집약 소속은 별개.",
              "scope": "latent weight의 집약 기하; 삼진화 후 기능적 품질/최적 초기화 순위는 미판정"}
    write_json_new(a.out, result)
    print(json.dumps({"groups": len(groups), "measured_mlp_projections": len(rows),
                      "out": a.out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
