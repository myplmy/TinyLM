#!/usr/bin/env python3
"""TinyLM 단일 진입점.

  python -m tinylm all --data ko-en --tokens 300M --steps 2289 --lr 1e-3 --compile
  python -m tinylm lrfind --method both
  python -m tinylm generate --arch tied --prompt "안녕하세요"

(호환) 저장소 루트의 run100m.py 도 이 main() 을 호출한다.
"""
from __future__ import annotations

import argparse

from . import paths  # noqa: F401  (HF 리다이렉트 먼저)
from .data import DATASETS


def _tok(s):
    s = str(s)
    return int(float(s.rstrip("MmBb")) * (1e9 if s[-1] in "Bb" else 1e6))


def _preset(a):
    return "tiny" if a.tiny else a.preset


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["prepare", "train", "eval", "compare", "all",
                                   "lrfind", "generate"])
    p.add_argument("--arch", choices=["dense", "tied"], default="tied")
    p.add_argument("--preset", choices=["tiny", "m100"], default="m100")
    p.add_argument("--data", default="ko-en", choices=list(DATASETS) + ["synthetic"])
    p.add_argument("--tokens", default="300M")
    p.add_argument("--steps", type=int, default=3000)
    p.add_argument("--micro-bs", type=int, default=8)
    p.add_argument("--seq", type=int, default=1024)
    p.add_argument("--accum", type=int, default=8)
    p.add_argument("--lr", type=float, default=6e-4)
    p.add_argument("--eval-every", type=int, default=250)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--tiny", action="store_true", help="tiny 프리셋(파이프라인 확인용)")
    p.add_argument("--no-ckpt", action="store_true", help="gradient checkpointing 끄기")
    p.add_argument("--compile", action="store_true", help="torch.compile 사용")
    # lrfind
    p.add_argument("--method", choices=["range", "grid", "both"], default="range")
    p.add_argument("--lrs", default="3e-4,6e-4,1e-3,2e-3", help="grid 스윕 LR 목록(콤마)")
    p.add_argument("--lr-min", type=float, default=1e-5)
    p.add_argument("--lr-max", type=float, default=1e-1)
    p.add_argument("--lrfind-steps", type=int, default=150)
    # generate
    p.add_argument("--prompt", default="")
    p.add_argument("--max-new", type=int, default=100)
    p.add_argument("--temp", type=float, default=0.8)
    p.add_argument("--top-k", type=int, default=40)
    p.add_argument("--ckpt-path", default=None)
    a = p.parse_args()

    n_tok = _tok(a.tokens)
    preset, ckpt = _preset(a), not a.no_ckpt

    if a.cmd == "prepare":
        from .data import prepare
        prepare(a.data, n_tok)

    elif a.cmd == "train":
        from .train import train
        train(preset, a.arch, a.data, n_tok, a.steps, a.micro_bs, a.seq, a.accum,
              a.lr, a.eval_every, a.resume, ckpt, a.compile)

    elif a.cmd == "all":
        from .train import train
        from .eval import compare
        for arch in ("dense", "tied"):
            print("\n" + "#" * 68 + f"\n#  {arch}\n" + "#" * 68)
            train(preset, arch, a.data, n_tok, a.steps, a.micro_bs, a.seq, a.accum,
                  a.lr, a.eval_every, a.resume, ckpt, a.compile)
        print(); compare()

    elif a.cmd == "eval":
        import torch
        from .data import prepare, Loader
        from .eval import evaluate
        from .infer import load_model
        meta = prepare(a.data, n_tok)
        model, cfg, device = load_model(a.arch, a.ckpt_path)
        print(model.report())
        va = Loader("val", a.micro_bs, a.seq, device, meta["dir"], seed=99)
        print(evaluate(model, va, 100, device))

    elif a.cmd == "compare":
        from .eval import compare
        compare()

    elif a.cmd == "lrfind":
        from .train import lr_find
        lrs = tuple(float(x) for x in a.lrs.split(","))
        lr_find(method=a.method, preset=preset, arch=a.arch, data=a.data,
                n_tokens=a.tokens, micro_bs=a.micro_bs, seq=a.seq, accum=a.accum,
                ckpt=ckpt, lrs=lrs, steps=a.lrfind_steps,
                lr_min=a.lr_min, lr_max=a.lr_max)

    elif a.cmd == "generate":
        from .infer import generate
        if not a.prompt:
            p.error("generate 에는 --prompt 가 필요합니다")
        generate(a.prompt, arch=a.arch, data=a.data, max_new=a.max_new,
                 temperature=a.temp, top_k=a.top_k, ckpt_path=a.ckpt_path)


if __name__ == "__main__":
    main()
