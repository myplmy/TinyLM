#!/usr/bin/env python3
"""P028 단계 0.6 — **문서 단위** val 손실 분해. "거대 문서 하나가 val 을 지배하는가"

★왜 이게 다음 단계인가 (단계 0.5 결과)
  ko-edu-en 의 val−뒤(미관측 순수비용)가 **+2.198** 이었다. 대조군 ko-en 은 **+0.153**.
  **14배**다. 같은 코퍼스에서 뽑은 미관측 텍스트가 이만큼 비쌀 이유가 없다.
  그런데 같은 단계에서 **val 의 23.5% 가 단일 문서**(352,399 토큰)라는 게 드러났다.
  → **"본 적 없어서 비싼 것"과 "그 한 문서가 이상해서 비싼 것"이 구분되지 않았다.**

  이 스크립트는 그걸 분리한다. `prepare()` 를 고치기 **전에** 해야 한다 —
  원인에 따라 **고치는 방법이 완전히 다르기 때문**이다:
      한 문서가 지배  → **필터링 문제**(길이 상한·문서 비중 상한). 좁은 수정
      전 문서가 고르게 나쁨 → **분할 문제**(무작위 분할). 전 데이터셋 영향, 큰 수정

사용법
  python scripts/diag_val_docs.py --data ko-edu-en --tokens 300M --arch dense
  python scripts/diag_val_docs.py --data ko-en     --tokens 300M --arch dense   # 대조군
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser(description="P028 단계0.6 문서단위 val 손실 분해")
    ap.add_argument("--data", default="ko-edu-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--arch", default="dense", choices=["dense", "tied"])
    ap.add_argument("--tag", default=None)
    ap.add_argument("--preset", default="m100")
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--max-docs", type=int, default=0, help="0=전부")
    ap.add_argument("--top", type=int, default=15, help="기여 상위 몇 개를 인쇄할지")
    a = ap.parse_args()

    import numpy as np
    import torch
    import torch.nn.functional as F
    from tinylm import paths
    from tinylm.data import prepare, tokenizer_path
    from tinylm.infer.generate import load_model
    from tokenizers import Tokenizer

    n_tok = int(float(a.tokens.rstrip("MmBb")) * (1e9 if a.tokens[-1] in "Bb" else 1e6))
    meta = prepare(a.data, n_tok)
    val = np.memmap(Path(meta["dir"]) / "val.bin", dtype=np.uint16, mode="r")
    tok = Tokenizer.from_file(str(tokenizer_path(a.data)))
    eos = tok.token_to_id("<eos>")
    if eos is None:
        eos = 2

    base = f"{a.preset}_{a.data}_{a.tokens}"
    ck = paths.RUNS / "ckpt" / f"{base}_{a.tag or a.arch}.pt"
    if not ck.exists():
        print(f"[!] 체크포인트 없음: {ck}")
        return 1
    model, cfg, dev = load_model(arch=a.arch, ckpt_path=str(ck))

    # --- 문서 경계 분해 (<eos> 기준) ---
    arr = np.asarray(val)
    cuts = np.flatnonzero(arr == eos)
    starts = np.concatenate([[0], cuts + 1])
    ends = np.concatenate([cuts + 1, [len(arr)]])
    docs = [(int(s), int(e)) for s, e in zip(starts, ends) if e - s >= 2]
    if a.max_docs:
        docs = docs[:a.max_docs]

    print("=" * 88)
    print(f"  P028 단계0.6 — 문서단위 val 손실 : {a.data} / {a.tag or a.arch}")
    print(f"  val {len(arr):,} 토큰, 문서 {len(docs):,}개, eos id={eos}")
    print("=" * 88)

    # --- 문서별 손실(토큰수 가중) ---
    rows = []
    with torch.no_grad():
        for (s, e) in docs:
            ids = arr[s:e]
            tot, ntok = 0.0, 0
            for off in range(0, len(ids) - 1, a.seq):
                chunk = ids[off:off + a.seq + 1]
                if len(chunk) < 2:
                    break
                x = torch.tensor(chunk[:-1].astype(np.int64), device=dev)[None]
                y = torch.tensor(chunk[1:].astype(np.int64), device=dev)[None]
                with torch.autocast(dev if isinstance(dev, str) else dev.type,
                                    dtype=torch.bfloat16, enabled=(str(dev) == "cuda")):
                    lg = model(x)
                l = F.cross_entropy(lg.reshape(-1, lg.size(-1)).float(),
                                    y.reshape(-1), reduction="sum").item()
                tot += l
                ntok += y.numel()
            if ntok:
                rows.append((s, e, ntok, tot))

    N = sum(r[2] for r in rows)
    L = sum(r[3] for r in rows)
    overall = L / N
    print(f"\n  전체 val 손실(토큰 가중) = {overall:.4f}   (총 {N:,} 토큰)")

    # --- 기여도 = 그 문서가 총 손실합에서 차지하는 비율 ---
    rows_by_contrib = sorted(rows, key=lambda r: -r[3])
    print(f"\n  기여 상위 {a.top}개 문서")
    print(f"  {'#':>3} {'토큰수':>9} {'토큰비중':>8} {'문서손실':>9} {'손실기여':>8}")
    print("  " + "-" * 46)
    for i, (s, e, n, t) in enumerate(rows_by_contrib[:a.top], 1):
        print(f"  {i:>3} {n:>9,} {n/N:>7.1%} {t/n:>9.4f} {t/L:>7.1%}")

    # --- ★핵심: 상위 문서를 빼면 val 이 어떻게 되나 ---
    print("\n  " + "=" * 60)
    print("  ★상위 기여 문서를 제외하면 val 손실이 어떻게 되는가")
    print("  " + "=" * 60)
    print(f"  {'제외':>10} {'남은토큰':>11} {'val손실':>9} {'변화':>9}")
    print("  " + "-" * 44)
    print(f"  {'없음':>10} {N:>11,} {overall:>9.4f} {'—':>9}")
    for k in (1, 2, 5, 10):
        if k >= len(rows_by_contrib):
            break
        rest = rows_by_contrib[k:]
        n2 = sum(r[2] for r in rest)
        l2 = sum(r[3] for r in rest) / n2
        print(f"  {'상위 '+str(k)+'개':>10} {n2:>11,} {l2:>9.4f} {l2-overall:>+9.4f}")

    # --- 분포 ---
    per = sorted(r[3] / r[2] for r in rows)
    def q(p):
        return per[min(len(per) - 1, int(len(per) * p))]
    print(f"\n  문서별 손실 분포(비가중): 중위 {q(.5):.3f}  "
          f"25% {q(.25):.3f}  75% {q(.75):.3f}  95% {q(.95):.3f}  최대 {per[-1]:.3f}")

    # --- 판정 ---
    top1 = rows_by_contrib[0]
    rest1 = rows_by_contrib[1:]
    l_wo1 = sum(r[3] for r in rest1) / sum(r[2] for r in rest1) if rest1 else overall
    drop = overall - l_wo1
    print("\n  " + "=" * 60)
    print("  판정")
    print("  " + "=" * 60)
    if drop > 0.5:
        print(f"    → ★**단일 문서가 지배한다**(제외 시 {drop:.3f} nats 하락).")
        print("       이건 말뭉치 품질이 아니라 **필터링 문제**다.")
        print("       고칠 것: 문서 길이 상한 + val 내 단일문서 비중 상한.")
        print("       **무작위 분할(전 데이터셋 영향)까지 갈 필요가 없을 수 있다.**")
    elif drop > 0.15:
        print(f"    → 단일 문서 영향이 **있으나 지배적이지 않다**({drop:.3f}).")
        print("       필터링과 분할을 **둘 다** 고쳐야 한다.")
    else:
        print(f"    → 단일 문서로 설명되지 않는다({drop:.3f}).")
        print("       **전 문서가 고르게 어렵다** = 분포 자체의 문제.")
        print("       → 무작위 분할(P028 부록 A, 전 데이터셋 영향)이 필요하다.")
    print("""
  ★한계
    · 문서 경계를 <eos> 로 잡는다. prepare() 가 문서마다 eos 를 붙이므로 타당하지만,
      원문에 eos 문자열이 있었다면 과분할된다.
    · 이 모델은 **이 val 로 평가돼 온 모델**이다. 절대 난이도가 아니라
      "이 모델이 이 문서를 얼마나 못 맞히나"를 잰다.
    · 문서 손실은 청크 경계에서 컨텍스트가 끊긴다(긴 문서에 약간 불리).""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
