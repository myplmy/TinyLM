#!/usr/bin/env python3
"""P030 추론 속도 벤치 — **CPU/GPU tok/s 와 TTFT**. 프로젝트 타깃(저사양 CPU)의 첫 측정.

★왜: 지금까지 측정한 것은 전부 **GPU 학습 속도**(결과 007·P021B·010)다.
   `CLAUDE.md` 첫 줄이 "저사양 CPU·엣지" 인데 **CPU 추론은 0회 측정**했다.
   즉 30.9MB → 11.7MB 로 줄인 것이 실제로 무슨 이득인지 아직 모른다.

★현재 상태의 한계 (측정값을 읽을 때 반드시 감안)
   `infer/generate.py:sample()` 은 **KV 캐시가 없다** — 매 토큰마다 전체 시퀀스를 재계산한다.
   따라서 여기서 나오는 tok/s 는 **KV 캐시 구현 후의 값이 아니다.**
   다만 **세 모델에 공통으로 불리**하므로 *모델 간 비교*는 유효하다(절대값만 비관적).
   또 삼진 가중치는 추론 시에도 **dequant 후 fp/bf16 GEMM** 이므로 11.7MB 는 "저장" 크기다.
   → "메모리 감축이 그대로 속도가 되지는 않는다"는 결과가 나올 가능성이 높다. 그것도 정보다.

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


def bench_one(model, cfg, tok, prompt, max_new, device, reps):
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
                   top_k=40, device=device)
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
    ap.add_argument("--max-new", type=int, default=32,
                    help="KV 캐시가 없어 CPU 는 매우 느리다 → 기본 32")
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

    print("=" * 84)
    print("  P030 추론 속도 벤치")
    print(f"  max_new={a.max_new}  reps={a.reps}(중위값)  프롬프트={PROMPT!r}")
    print("  ★KV 캐시 없음 — 매 토큰 전체 재계산. 절대값은 비관적, 모델 간 비교는 유효")
    print("=" * 84)
    print(f"\n{'device':>8} {'threads':>8} {'model':>16} {'배포MB':>7} {'tok/s':>9} {'TTFT ms':>9}")
    print("-" * 84)

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
                    r, t = bench_one(model, cfg, tok, PROMPT, a.max_new, dev, a.reps)
                except Exception as e:
                    print(f"{dev:>8} {nt:>8} {tag:>16}  실패: {type(e).__name__}: {e}")
                    continue
                print(f"{dev:>8} {nt if nt else '기본':>8} {tag:>16} {mb:>7.1f} {r:>9.2f} {t:>9.1f}")
                rows.append((dev, nt, tag, mb, r, t))
                del model
                if dev == "cuda":
                    torch.cuda.empty_cache()

    print("-" * 84)
    if rows:
        print("\n★핵심 질문: 메모리를 줄이면 CPU 추론이 빨라지는가?")
        for dev in {r[0] for r in rows}:
            sub = [r for r in rows if r[0] == dev and r[3] > 0]
            if len(sub) < 2:
                continue
            sub.sort(key=lambda r: -r[3])          # 메모리 큰 것부터
            base_rate = sub[0][4]
            print(f"\n  [{dev}] 기준 = {sub[0][2]}({sub[0][3]:.1f}MB) {base_rate:.2f} tok/s")
            for _, nt, tag, mb, r, _t in sub[1:]:
                print(f"    {tag:16} {mb:5.1f}MB  {r:7.2f} tok/s  = {r/base_rate:5.2f}x "
                      f"(메모리는 {sub[0][3]/mb:.2f}x 작음)")
        print("\n  해석: 속도비 ≈ 메모리비 면 '메모리→속도 전이'가 성립.")
        print("        속도비 ≈ 1.0 이면 전이가 없다 → 5비트 패킹 커널(P030 단계3)이 필요하다는 근거.")
    print("\n★한계: KV 캐시 미구현 / 삼진은 dequant 후 GEMM(저장≠실행 크기) /")
    print("        Windows CPU 측정은 노이즈 큼(중위값 사용, 1~2% 차이는 읽지 않는다).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
