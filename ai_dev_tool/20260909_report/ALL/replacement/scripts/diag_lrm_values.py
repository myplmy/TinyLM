#!/usr/bin/env python3
"""A09: cfg의 실제 WD와 checkpoint step으로 LRM을 재진단한다. 학습하지 않는다."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tinylm.model.checkpoint_io import read_checkpoint
from tinylm.eval.audit_io import read_records, sha256_file, write_json_new
from tinylm.eval.lrm_diagnostics import describe_motion, history_floor


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--ckpt")
    src.add_argument("--tag")
    ap.add_argument("--meta", help="참고용 학습 JSON; 없으면 runs/logs/<stem>.json")
    ap.add_argument("--lr-history", help="step/applied/lrm_lr/lrm_weight_decay JSONL")
    ap.add_argument("--initial-one", action="store_true",
                    help="해당 history 시작 때 LRM=1이고 중간 재초기화가 없었음을 명시")
    ap.add_argument("--out", help="새 JSON 경로; 미지정이면 stdout만")
    a = ap.parse_args(argv)
    if a.tag:
        matches = sorted((ROOT / "runs/ckpt").glob(f"*_{a.tag}.pt"))
        if len(matches) != 1:
            ap.error(f"tag가 정확히 1개 checkpoint를 가리켜야 함: {matches}")
        path = matches[0]
    else:
        path = Path(a.ckpt)
    state, cfg, obj = read_checkpoint(path)
    rows = {k: v for k, v in state.items()
            if k.rsplit(".", 1)[-1] in ("lrm", "lrm_gate", "lrm_up", "lrm_down")}
    if not rows:
        raise ValueError("주 대상 LRM tensor 0개")
    wd = float(cfg.mlp_lrm_wd)
    if wd < 0:
        raise ValueError("음수 WD")
    meta_path = Path(a.meta) if a.meta else ROOT / "runs/logs" / (
        path.stem.removesuffix("_best") + ".json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else None
    if meta and meta.get("mlp_lrm_wd") is not None and float(meta["mlp_lrm_wd"]) != wd:
        raise ValueError("학습 JSON과 checkpoint cfg의 WD 불일치; 자동 판정 중지")
    floor, origin = None, "unresolved_without_applied_lr_history"
    if wd == 0:
        floor, origin = 1.0, "wd_zero_identity_conditional_on_initial_one"
    elif a.lr_history:
        if not a.initial_one:
            ap.error("LR history 보정에는 --initial-one 근거 확인 필요")
        history = read_records(a.lr_history)
        relevant = history[:int(obj.get("step", -1))]
        if any(float(r["lrm_weight_decay"]) != wd for r in relevant):
            raise ValueError("history WD와 cfg WD 불일치")
        floor = history_floor(history, obj.get("step"))
        origin = "explicit_applied_lr_history"
    result = {"schema": "tinylm.lrm-diagnostic.v2", "checkpoint": str(path.resolve()),
              "checkpoint_sha256": sha256_file(path), "checkpoint_step": obj.get("step"),
              "cfg_lrm_mode": cfg.mlp_lrm_mode, "cfg_lrm_weight_decay": wd,
              "training_meta": str(meta_path) if meta else None,
              "planned_steps": meta.get("steps") if meta else None,
              "n_skip": meta.get("n_skip") if meta else None,
              "floor_source": origin,
              "initial_one_explicit": a.initial_one,
              "rows": {k: describe_motion(v.detach().float().reshape(-1).tolist(), floor)
                       for k, v in rows.items()},
              "limitations": [
                  "WD=0의 기준 1은 초기 LRM=1 조건. 이식/재개 초기값이 다르면 이동량으로 해석 불가.",
                  "WD-only 비율은 optimizer 상호작용을 제거한 gradient 인과 분해가 아니다.",
                  "이동량 임계값은 품질 유무, 미학습 여부, 기존 paired 결론의 자동 철회 기준이 아니다.",
                  "planned steps로 best checkpoint의 WD를 역산하지 않는다."]}
    if a.lr_history:
        result["lr_history_sha256"] = sha256_file(a.lr_history)
    if a.out:
        write_json_new(a.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 2 if floor is None else 0


if __name__ == "__main__":
    raise SystemExit(main())
