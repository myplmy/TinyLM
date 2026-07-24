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
    p.add_argument("--compile-mode", choices=["default", "reduce-overhead", "max-autotune"],
                   default="default", help="reduce-overhead=CUDA그래프(런치 오버헤드↓)")
    # --- v6: 효율/실험 ---
    p.add_argument("--sched", choices=["cosine", "wsd", "stable", "decay"], default="cosine",
                   help="stable=plateau 생성(감쇠X), decay=plateau에서 cooldown 분기")
    p.add_argument("--decay-from", default=None, help="decay 분기 시 불러올 plateau 체크포인트 경로")
    p.add_argument("--snapshot-at", default=None, help="토큰 마크에서 명명 스냅샷 저장(콤마, 예: 100M,300M,600M)")
    p.add_argument("--ema", type=float, default=0.0, help="EMA decay(0=끔, 예: 0.999)")
    p.add_argument("--early-stop", type=int, default=0, help="val 개선 없이 N회 eval시 종료(0=끔)")
    p.add_argument("--init-from", action="store_true", help="tied를 dense.pt로 부모초기화")
    p.add_argument("--kd", action="store_true", help="dense.pt를 교사로 KD")
    p.add_argument("--kd-best", action="store_true", help="KD 교사를 dense_best.pt로(더 강한 교사)")
    p.add_argument("--ema-start", type=float, default=0.0, help="EMA를 steps의 이 비율 이후부터 누적(0=처음부터)")
    p.add_argument("--kd-alpha", type=float, default=0.5)
    p.add_argument("--kd-temp", type=float, default=2.0)
    p.add_argument("--lora-rank", type=int, default=0, help="공유 MLP 층별 LoRA rank(0=끔)")
    p.add_argument("--lora-bits", type=int, default=2, choices=[2, 16])
    p.add_argument("--tag", default=None, help="체크포인트/로그 파일명(실험 조건 구분용)")
    p.add_argument("--vs", default=None, help="compare에서 tied vs tied 비교할 상대 태그")
    p.add_argument("--mlp-group", type=int, default=None, help="MLP 타잉 g 오버라이드(프리셋값 대체, g-스윕용)")
    p.add_argument("--mlp-film", action="store_true", help="공유 MLP에 층별 FiLM(거의 공짜 조건화)")
    p.add_argument("--center-weights", action="store_true", help="(실험) g128 그룹 latent weight centering")
    p.add_argument("--force-dense", action="store_true", help="all 실행 시 dense 재학습 강제(기본은 재사용)")
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
    tokstr = f"{n_tok//1_000_000}M" if n_tok >= 10**6 else str(n_tok)
    base = f"{preset}_{a.data}_{tokstr}"        # 스케일별 이름 프리픽스
    dense_ck = paths.RUNS / "ckpt" / f"{base}_dense.pt"
    dense_best_ck = paths.RUNS / "ckpt" / f"{base}_dense_best.pt"   # P3: 더 강한 교사 옵션

    if a.cmd == "prepare":
        from .data import prepare
        prepare(a.data, n_tok)

    elif a.cmd == "train":
        from .train import train
        train(preset, a.arch, a.data, n_tok, a.steps, a.micro_bs, a.seq, a.accum,
              a.lr, a.eval_every, a.resume, ckpt, a.compile,
              sched=a.sched, ema=a.ema, early_stop=a.early_stop,
              init_from=(str(dense_ck) if a.init_from else None),
              kd=((str(dense_best_ck) if a.kd_best else str(dense_ck)) if a.kd else False),
              kd_alpha=a.kd_alpha, kd_temp=a.kd_temp,
              lora_rank=a.lora_rank, lora_bits=a.lora_bits, mlp_film=a.mlp_film,
              tag=a.tag, tokstr=tokstr, compile_mode=a.compile_mode, mlp_group=a.mlp_group,
              ema_start=a.ema_start, center_weights=a.center_weights, decay_from=a.decay_from,
              snapshots=([_tok(x) for x in a.snapshot_at.split(',')] if a.snapshot_at else None))

    elif a.cmd == "all":
        from .train import train
        from .eval import compare
        import json as _json
        dlog = paths.RUNS / "logs" / f"{base}_dense.json"
        # dense 재사용: 같은 (preset,data,steps) 의 dense 로그·체크포인트가 있으면 재학습 생략.
        # (seq·lr 은 로그에 있으면 함께 대조. --force-dense 로 강제 재학습.)
        reuse = False
        if not a.force_dense and dense_ck.exists() and dlog.exists():
            try:
                dj = _json.loads(dlog.read_text())
                reuse = (dj.get("preset") == preset and dj.get("data") == a.data
                         and dj.get("steps") == a.steps
                         and dj.get("seq", a.seq) == a.seq
                         and abs(dj.get("lr", a.lr) - a.lr) < 1e-12)
            except Exception:
                reuse = False
        for arch in ("dense", "tied"):
            if arch == "dense" and reuse:
                dj = _json.loads(dlog.read_text())
                print("\n" + "#" * 68 + "\n#  dense (재사용)\n" + "#" * 68)
                print(f"[dense] 기존 학습 재사용: val {dj['final']['val_loss']:.4f} "
                      f"(preset={dj.get('preset')} data={dj.get('data')} steps={dj.get('steps')}). "
                      f"재학습하려면 --force-dense")
                continue
            print("\n" + "#" * 68 + f"\n#  {arch}\n" + "#" * 68)
            is_tied = arch == "tied"
            train(preset, arch, a.data, n_tok, a.steps, a.micro_bs, a.seq, a.accum,
                  a.lr, a.eval_every, a.resume, ckpt, a.compile,
                  sched=a.sched, ema=a.ema, early_stop=a.early_stop,
                  init_from=(str(dense_ck) if (is_tied and a.init_from) else None),
                  kd=((str(dense_best_ck) if a.kd_best else str(dense_ck)) if (is_tied and a.kd) else False),
                  kd_alpha=a.kd_alpha, kd_temp=a.kd_temp,
                  lora_rank=(a.lora_rank if is_tied else 0), lora_bits=a.lora_bits,
                  mlp_film=(a.mlp_film if is_tied else False), tokstr=tokstr,
                  compile_mode=a.compile_mode, mlp_group=(a.mlp_group if is_tied else None),
                  ema_start=a.ema_start, center_weights=(a.center_weights if is_tied else False),
                  decay_from=a.decay_from)
        print(); compare(base)

    elif a.cmd == "eval":
        import torch
        from .data import prepare, Loader
        from .eval import evaluate
        from .infer import load_model
        meta = prepare(a.data, n_tok)
        ckp = a.ckpt_path or str(paths.RUNS / "ckpt" / (f"{base}_{a.tag}.pt" if a.tag else f"{base}_{a.arch}.pt"))
        model, cfg, device = load_model(a.arch, ckp)
        print(model.report())
        va = Loader("val", a.micro_bs, a.seq, device, meta["dir"], seed=99)
        print(evaluate(model, va, 100, device))

    elif a.cmd == "compare":
        from .eval import compare
        compare(base, a.tag, a.vs)

    elif a.cmd == "lrfind":
        from .train import lr_find
        grid_lrs = tuple(float(x) for x in a.lrs.split(","))
        lr_find(method=a.method, preset=preset, arch=a.arch, data=a.data,
                n_tokens=a.tokens, micro_bs=a.micro_bs, seq=a.seq, accum=a.accum,
                ckpt=ckpt, range_steps=a.lrfind_steps, lr_min=a.lr_min, lr_max=a.lr_max,
                grid_lrs=grid_lrs)

    elif a.cmd == "generate":
        from .infer import generate
        if not a.prompt:
            p.error("generate 에는 --prompt 가 필요합니다")
        gckp = a.ckpt_path or str(paths.RUNS / "ckpt" / (f"{base}_{a.tag}.pt" if a.tag else f"{base}_{a.arch}.pt"))
        generate(a.prompt, arch=a.arch, data=a.data, max_new=a.max_new,
                 temperature=a.temp, top_k=a.top_k, ckpt_path=gckp)


if __name__ == "__main__":
    main()
