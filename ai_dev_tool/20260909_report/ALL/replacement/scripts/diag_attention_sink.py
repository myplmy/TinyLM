#!/usr/bin/env python3
"""A10: 기존 validation bin과 checkpoint의 실제 attention만 재진단한다."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.eval.audit_io import sha256_file, write_json_new
from tinylm.eval.attention_stats import attention_mass
from tinylm.infer.generate import load_model
from tinylm.model.modules import Attention


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--val-bin", required=True, help="기존 validation stream; prepare를 호출하지 않음")
    ap.add_argument("--dtype", choices=("uint16", "uint32"), required=True)
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--sink", type=int, default=4)
    ap.add_argument("--window", type=int, default=256)
    ap.add_argument("--tail-start", type=int, help="기본 seq//2; 전체 query 결과와 따로 출력")
    ap.add_argument("--crops", type=int, default=4)
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.seq < 1 or min(a.sink, a.window) < 0 or a.crops < 1:
        ap.error("seq/crops 양수, sink/window 비음수")
    tail = a.seq // 2 if a.tail_start is None else a.tail_start
    if not 0 <= tail < a.seq:
        ap.error("tail-start 범위 오류")
    import numpy as np
    import torch
    import random
    stream = np.memmap(a.val_bin, mode="r", dtype=a.dtype)
    if len(stream) < a.seq:
        raise ValueError("validation stream이 seq보다 짧음")
    starts = random.Random(a.seed).sample(range(len(stream) - a.seq + 1),
                                          min(a.crops, len(stream) - a.seq + 1))
    model, cfg, _ = load_model(ckpt_path=a.checkpoint, device=a.device)
    if a.seq > cfg.max_seq_len:
        raise ValueError("checkpoint context 초과")
    if cfg.attn_kind != "softmax_cla":
        raise ValueError("현재 이 진단은 실제 Attention softmax_cla 경로만 지원")
    cfg.return_probs = True
    records, handles, current = [], [], {}
    def make_hook(name):
        def hook(module, inputs, output):
            p = getattr(module, "last_probs", None)
            if p is None:
                raise RuntimeError(f"{name}: 실제 확률이 없음")
            try:
                records.append({"crop": current["crop"], "offset": current["offset"],
                                "module": name, "visit": current["visits"],
                                "all": attention_mass(p, a.sink, a.window),
                                "tail": attention_mass(p, a.sink, a.window, tail)})
                current["visits"] += 1
            finally:
                module.last_probs = None
        return hook
    for name, module in model.named_modules():
        if isinstance(module, Attention):
            handles.append(module.register_forward_hook(make_hook(name)))
    if not handles:
        raise ValueError("attention hook 0개")
    try:
        for i, offset in enumerate(starts):
            current.update(crop=i, offset=offset, visits=0)
            ids = torch.tensor(np.asarray(stream[offset:offset+a.seq], dtype=np.int64),
                               device=a.device).unsqueeze(0)
            if int(ids.max()) >= cfg.vocab_size:
                raise ValueError("bin dtype/tokenizer vocabulary 확인 필요")
            dev = torch.device(a.device).type
            with torch.inference_mode(), torch.autocast(dev, dtype=torch.bfloat16,
                                                        enabled=dev == "cuda"):
                model(ids)
            if current["visits"] == 0:
                raise ValueError("측정 visit 0개")
    finally:
        for handle in handles:
            handle.remove()
        cfg.return_probs = False
    write_json_new(a.out, {"schema": "tinylm.attention-sink.v2",
                         "command": vars(a), "checkpoint_sha256": sha256_file(a.checkpoint),
                         "val_sha256": sha256_file(a.val_bin), "starts": starts,
                         "visit_schedule": list(model.visit_schedule()), "rows": records,
                         "quality_or_pruning_verdict": None,
                         "note": "query 위치별 causal null. mass는 실제 KV 삭제의 기능적 품질 검증을 대체하지 않음."})
    print(f"attention visit {len(records)}개 -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
