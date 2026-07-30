#!/usr/bin/env python3
"""P030 추론 속도 벤치 — **CPU/GPU tok/s 와 TTFT**. 프로젝트 타깃(저사양 CPU)의 첫 측정.

★왜: 지금까지 측정한 것은 전부 **GPU 학습 속도**(결과 007·P021B·010)다.
   `CLAUDE.md` 첫 줄이 "저사양 CPU·엣지" 인데 **CPU 추론은 0회 측정**했다.
   즉 30.9MB → 11.7MB 로 줄인 것이 실제로 무슨 이득인지 아직 모른다.

★2026-07-31 갱신 (P030 단계1 반영) — 결과 014 는 이 두 결함으로 **무효**였다
   (1) `load_model` 이 삼진화를 고정하지 않아 **매 forward 재양자화**했다(CPU 시간의 ~79%).
       → `freeze_quant()` 로 1회만 계산. sparse34 가 dense 보다 느려 보인 원인이 이것이다.
   (2) **KV 캐시가 없어** 매 토큰 전체 시퀀스를 재계산했다(O(T²)).
       → `use_cache=True` 가 기본. `--no-cache` 로 옛 경로와 대조할 수 있다.
   여전히 남는 한계: 삼진 가중치는 추론 시 **dequant 후 fp/bf16 GEMM** 이라
   11.7MB 는 "저장" 크기다. **실행시 메모리는 P034 가 따로 잰다.**

사용법
  python scripts/bench_infer.py                                   # 기본 3모델, CPU+GPU
  python scripts/bench_infer.py --device cpu --threads 1 2 4 8     # 스레드 스윕
  python scripts/bench_infer.py --models mA_g4s34_k4 --max-new 32
"""
from __future__ import annotations
import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_MODELS = [
    ("p6d", "dense", 30.9),
    ("mC_g8_k4", "tied", 14.9),
    ("mA_g4s34_k4", "tied", 11.7),
]
PROMPT = "대한민국의 수도 서울은"          # 학습 분포 안. 길이는 --prompt-tokens 로 패딩


def bench_one(model, cfg, tok, prompt, max_new, device, reps, use_cache=True):
    """(tok/s, TTFT_ms) 를 reps 회 재서 중위값. 첫 회는 warmup 으로 버린다."""
    import torch
    from tinylm.infer.generate import sample
    rates, ttfts = [], []
    for r in range(reps + 1):
        # TTFT: 프롬프트 1회 forward
        ids = tok.encode(prompt).ids
        x = torch.tensor([ids], dtype=torch.long, device=device)
        if device == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        with torch.no_grad():
            dev_t = device if isinstance(device, str) else device.type
            with torch.autocast(dev_t, dtype=torch.bfloat16, enabled=(dev_t == "cuda")):
                _ = model(x[:, -cfg.max_seq_len:])
        if device == "cuda":
            torch.cuda.synchronize()
        ttft = (time.perf_counter() - t0) * 1000

        if device == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        _ = sample(model, cfg, tok, prompt, max_new=max_new, temperature=0.7,
                   top_k=40, device=device, use_cache=use_cache,
                   stop_at_eos=False)      # ★속도 측정은 항상 max_new 토큰을 다 생성해야 공정
        if device == "cuda":
            torch.cuda.synchronize()
        el = time.perf_counter() - t0
        if r == 0:
            continue                       # warmup 버림
        rates.append(max_new / el)
        ttfts.append(ttft)
    return statistics.median(rates), statistics.median(ttfts)


def main():
    ap = argparse.ArgumentParser(description="P030 추론 속도 벤치")
    ap.add_argument("--models", nargs="*")
    ap.add_argument("--device", nargs="*", default=["cuda", "cpu"])
    ap.add_argument("--threads", nargs="*", type=int, default=[0],
                    help="CPU 스레드 수(0=torch 기본). 엣지는 코어가 적으니 1 이 가장 현실적")
    ap.add_argument("--max-new", type=int, default=128,
                    help="KV 캐시 구현 후 기본 128(캐시 이득은 길수록 커진다)")
    ap.add_argument("--no-cache", action="store_true",
                    help="KV 캐시 off. 결과 014 조건 재현용 대조군")
    ap.add_argument("--both-cache", action="store_true",
                    help="캐시 on/off 를 같은 표에 나란히 측정(캐시 이득 배수를 직접 본다)")
    ap.add_argument("--check-cache", action="store_true",
                    help="먼저 캐시 유/무 그리디 출력 일치를 검증한다(불일치면 중단)")
    ap.add_argument("--reps", type=int, default=3, help="반복(중위값). Windows 는 노이즈가 크다")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--preset", default="m100")
    a = ap.parse_args()

    import torch
    from tinylm import paths
    from tinylm.infer.generate import load_model
    from tinylm.data import tokenizer_path
    from tokenizers import Tokenizer

    models = ([(t, "dense" if t.startswith(("p6d", "dense", "p12d")) else "tied", 0.0)
               for t in a.models] if a.models else DEFAULT_MODELS)
    tok = Tokenizer.from_file(str(tokenizer_path(a.data)))
    base = f"{a.preset}_{a.data}_{a.tokens}"

    modes = [True, False] if a.both_cache else [not a.no_cache]
    print("=" * 92)
    print("  P030 추론 속도 벤치 (단계1: KV 캐시 + eos + 삼진 1회계산 반영)")
    print(f"  max_new={a.max_new}  reps={a.reps}(중위값)  프롬프트={PROMPT!r}")
    print(f"  캐시 모드={['on' if m else 'off' for m in modes]}   (off = 결과 014 조건)")
    print("=" * 92)
    print(f"\n{'device':>8} {'threads':>8} {'model':>16} {'배포MB':>7} {'캐시':>5} "
          f"{'tok/s':>9} {'TTFT ms':>9}")
    print("-" * 92)

    rows = []
    for dev in a.device:
        if dev == "cuda" and not torch.cuda.is_available():
            print("  (cuda 없음 — 건너뜀)")
            continue
        thread_list = a.threads if dev == "cpu" else [0]
        for nt in thread_list:
            if dev == "cpu" and nt > 0:
                torch.set_num_threads(nt)
            for tag, arch, mb in models:
                ck = paths.RUNS / "ckpt" / f"{base}_{tag}.pt"
                if not ck.exists():
                    print(f"{dev:>8} {nt:>8} {tag:>16}  체크포인트 없음 — 건너뜀")
                    continue
                try:
                    model, cfg, _ = load_model(arch=arch, ckpt_path=str(ck), device=dev)
                except Exception as e:
                    print(f"{dev:>8} {nt:>8} {tag:>16}  로드 실패: {type(e).__name__}: {e}")
                    continue
                if a.check_cache:
                    from tinylm.infer.generate import check_cache_equivalence
                    if not check_cache_equivalence(model, cfg, tok, PROMPT, 16, dev):
                        print("  [중단] 캐시 출력이 불일치한다 — 속도를 재는 의미가 없다.")
                        return 2
                for use_c in modes:
                    try:
                        r, t = bench_one(model, cfg, tok, PROMPT, a.max_new, dev, a.reps, use_c)
                    except Exception as e:
                        print(f"{dev:>8} {nt:>8} {tag:>16}  실패: {type(e).__name__}: {e}")
                        continue
                    print(f"{dev:>8} {nt if nt else '기본':>8} {tag:>16} {mb:>7.1f} "
                          f"{'on' if use_c else 'off':>5} {r:>9.2f} {t:>9.1f}")
                    rows.append((dev, nt, tag, mb, r, t, use_c))
                del model
                if dev == "cuda":
                    torch.cuda.empty_cache()

    print("-" * 84)
    if rows:
        print("\n★핵심 질문: 메모리를 줄이면 CPU 추론이 빨라지는가?")
        for dev in {r[0] for r in rows}:
            sub = [r for r in rows if r[0] == dev and r[3] > 0 and r[6]]   # 캐시 on 만
            if len(sub) < 2:
                continue
            sub.sort(key=lambda r: -r[3])          # 메모리 큰 것부터
            base_rate = sub[0][4]
            print(f"\n  [{dev}] 기준 = {sub[0][2]}({sub[0][3]:.1f}MB) {base_rate:.2f} tok/s")
            for _, nt, tag, mb, r, _t, _c in sub[1:]:
                print(f"    {tag:16} {mb:5.1f}MB  {r:7.2f} tok/s  = {r/base_rate:5.2f}x "
                      f"(메모리는 {sub[0][3]/mb:.2f}x 작음)")
        print("\n  해석: 속도비 ≈ 메모리비 면 '메모리→속도 전이'가 성립.")
        print("        속도비 ≈ 1.0 이면 전이가 없다 → 5비트 패킹 커널(P030 단계3)이 필요하다는 근거.")
        if a.both_cache:
            print("\n★캐시 이득(같은 모델, on/off):")
            for dev, nt, tag, mb, r, _t, c in rows:
                if not c:
                    on = [q for q in rows if q[:4] == (dev, nt, tag, mb) and q[6]]
                    if on:
                        print(f"    [{dev} t{nt}] {tag:16} off {r:6.2f} -> on {on[0][4]:6.2f} "
                              f"tok/s = {on[0][4]/r:5.2f}x")
    print("\n★한계: 삼진은 dequant 후 GEMM(저장≠실행 크기 — 실행시 메모리는 P034) /")
    print("        Windows CPU 측정은 노이즈 큼(중위값 사용, 1~2% 차이는 읽지 않는다) /")
    print("        batch 1 단일요청. 서버 처리량은 다른 주제다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
