"""학습 루프: 삼진 어닐 + LR 코사인 + NaN 가드 + 체크포인트.

v5 안정화: NaN/inf 그라디언트 스킵, warmup 비율 수정, compile 안전 set_anneal.
"""
from __future__ import annotations

import json
import math
import time

import torch
import torch.nn.functional as F

from .. import paths
from ..config import build_config
from ..model import TiedMLPTransformer
from ..data import prepare, Loader
from ..eval import evaluate

CKPT = paths.RUNS / "ckpt"
LOGS = paths.RUNS / "logs"


def train(preset, arch, data, n_tokens, steps, micro_bs, seq, accum, lr, eval_every,
          resume=False, ckpt=True, compile_=False):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(1337)
    CKPT.mkdir(parents=True, exist_ok=True); LOGS.mkdir(parents=True, exist_ok=True)

    meta = prepare(data, n_tokens)
    cfg = build_config(preset, arch, seq, ckpt)
    model = TiedMLPTransformer(cfg).to(device)
    if compile_:
        print('[compile] torch.compile 첫 스텝은 수 분 걸릴 수 있습니다')
        model = torch.compile(model)
    print(model.report())
    eff = micro_bs * accum * seq
    print(f"[{arch}] device={device}  {steps}step x {eff/1e3:.0f}K tok = "
          f"{steps*eff/1e6:.0f}M 토큰\n")

    opt = torch.optim.AdamW(model.param_groups(lr), betas=(0.9, 0.95), eps=1e-8)
    base_lrs = [g["lr"] for g in opt.param_groups]
    warm = max(5, min(steps // 10, 100))       # v5: 짧은 런에서 warmup 과다 방지

    start = 0
    ck = CKPT / f"{arch}.pt"
    if resume and ck.exists():
        st = torch.load(ck, map_location=device)
        model.load_state_dict(st["model"]); opt.load_state_dict(st["opt"]); start = st["step"]
        print(f"[{arch}] step {start}에서 재개")

    tr = Loader("train", micro_bs, seq, device, meta["dir"], seed=1234)
    va = Loader("val", micro_bs, seq, device, meta["dir"], seed=99)
    hist, t0, gmax, n_skip = [], time.time(), 0.0, 0

    for s in range(start, steps):
        a0 = warm / steps + 0.05
        anneal = min(1.0, max(0.0, (s / steps - a0) / max(0.60 - a0, 1e-6)))
        model.set_anneal(anneal)
        f = (s + 1) / warm if s < warm else \
            0.1 + 0.45 * (1 + math.cos(math.pi * (s - warm) / max(steps - warm, 1)))
        for g, b in zip(opt.param_groups, base_lrs):
            g["lr"] = b * f

        model.train()
        tot = 0.0
        for _ in range(accum):
            x, y = tr()
            with torch.autocast(device, dtype=torch.bfloat16, enabled=(device == "cuda")):
                logits = model(x)
                loss = F.cross_entropy(logits.reshape(-1, cfg.vocab_size), y.reshape(-1)) / accum
            loss.backward()
            tot += loss.item()
        gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

        if not torch.isfinite(gn):             # v5: NaN 가드 — 오염된 step을 버린다
            opt.zero_grad(set_to_none=True); model.clear_quant()
            n_skip += 1
            print(f"  [skip] step {s}: non-finite grad ({n_skip}회째)  "
                  f"anneal {model.cfg.quant_anneal:.2f}  lr {opt.param_groups[1]['lr']:.2e}")
            if n_skip > 20:
                print("  !! non-finite 그라디언트 20회 초과. LR을 낮추고 재시작하세요."); break
            continue

        gmax = max(gmax, float(gn))
        opt.step(); opt.zero_grad(set_to_none=True)
        model.clear_quant()

        if s % 10 == 0 or s == steps - 1:
            el = time.time() - t0
            print(f"  step {s:>5}/{steps}  loss {tot:.4f}  |g| {gn:.2f}  "
                  f"anneal {model.cfg.quant_anneal:.2f}  lr {opt.param_groups[1]['lr']:.2e}  "
                  f"{el/(s-start+1)*1000:.0f} ms/step")
        if (s + 1) % eval_every == 0 or s == steps - 1:
            m = evaluate(model, va, 20, device)
            m.update(step=s + 1, train_loss=tot)
            hist.append(m)
            print(f"    >> val_loss {m['val_loss']:.4f}  ppl {m['ppl']:.2f}")
            torch.save({"model": model.state_dict(), "opt": opt.state_dict(),
                        "step": s + 1, "cfg": cfg.__dict__}, ck)

    final = evaluate(model, va, 100, device)
    n_par = sum(p.numel() for p in model.parameters())
    res = {"arch": arch, "preset": preset, "data": data, "params": n_par, "steps": steps,
           "tokens": steps * eff, "final": final, "history": hist, "grad_max": gmax,
           "n_skip": n_skip, "wall_sec": time.time() - t0}
    (LOGS / f"{arch}.json").write_text(json.dumps(res, indent=2))
    print(f"\n[{arch}] 최종 val_loss {final['val_loss']:.4f}  ppl {final['ppl']:.2f}  "
          f"({n_par/1e6:.1f}M 파라미터, {(time.time()-t0)/60:.1f}분, skip {n_skip}회)")
    return res
