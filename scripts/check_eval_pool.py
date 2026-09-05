#!/usr/bin/env python3
"""★★정적 게이트 — **판정 도구의 val 이 그 모델의 학습 데이터인가.**(torch 0 · GPU 0)

## 왜 이 게이트가 생겼나 (2026-09-05, 결과 075 §6)

`prepare()` 는 **결정적 스트림**(`_stream` 이 `default_rng(0)`)을 앞에서부터 잘라 캐시를
만들고, val 은 **말미 0.5%**(`arr[-n_val:]`)다. 그래서 **작은 캐시는 큰 캐시의 접두사**이고,
★**작은 캐시의 `val.bin` 은 큰 캐시의 `train.bin` 안에 그대로 들어 있다.**

바이트 단위로 확인했다:

    ko-en_300M/val.bin  == ko-en_600M/train.bin [298,500,000 : 300,000,000]   True (1,500,000)
    ko-en_300M/val.bin  == ko-en_1200M/train.bin[298,500,000 : 300,000,000]   True
    ko-en_600M/val.bin  == ko-en_1200M/train.bin[597,000,000 : 600,000,000]   True (3,000,000)

그런데 `paired_eval` 의 기본값은 **`--tokens 300M`** 이고, 우리 표준 학습은
**`--pool-tokens 600M`** 이다. → ★**지금까지의 모든 `full-val` 이 "본 적 있는 글" 이었다.**
(`pool_tokens=600000000` 인 실런이 **142개**.)

✅**헤드라인은 안 흔들렸다**(결과 075 §6.3 — 깨끗한 학습로그 val 과 0.0003 안에서 일치).
🚫**그래도 다음부터는 막는다.** 이 게이트가 그 자리다.

## 무엇을 검사하나

배치(`*.bat`)에서 **평가 호출**을 찾아 `--tokens X` 와 `--models …` 를 뽑고,
각 태그의 학습 json(`runs/logs/*_{tag}.json`)에서 `pool_tokens` 를 읽어 대조한다.

| 조건 | 판정 |
|---|---|
| `pool_tokens > X` | 🚫**에러** — val 이 그 모델의 학습 데이터다 |
| 한 호출 안에서 `pool_tokens` 가 **서로 다르다** | 🚫**에러** — 오염 정도가 모델마다 달라 짝짓기가 무효다 |
| json 이 없다 / `pool_tokens` 가 없다 | ⚠️경고(구 런은 이 필드가 없다 — 79개) |
| `pool_tokens <= X` | ✅통과 |

🚫**`common_bpb` 는 검사하지 않는다** — 외부 원문이라 어느 풀에도 없다(그것이 §7 의 처방이다).

## 면제

배치 줄에 `REM EVAL-POOL-OK: <사유>` 를 두면 그 배치는 넘어간다. **사유를 적게 하는 것이
목적**이고, 사유 없이 통과시키는 스위치는 두지 않는다.

사용:  python scripts/check_eval_pool.py [--bat run_x.bat]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "runs" / "logs"
NL = chr(10)

# ★val 캐시를 고르는 평가 도구만. 학습(run100m.py train)은 자기 캐시의 val 을 쓰므로 깨끗하다.
EVAL_TOOLS = ("paired_eval.py", "paired_join.py", "eval_slices.py", "diag_val_docs.py")
EXEMPT = re.compile(r"^\s*REM\s+EVAL-POOL-OK\s*:", re.I)


def parse_tokens(s: str):
    """'300M' / '1200M' / '1.2B' -> int"""
    m = re.fullmatch(r"([0-9.]+)\s*([MmBb]?)", s.strip())
    if not m:
        return None
    v = float(m.group(1))
    return int(v * (1e9 if m.group(2) in "Bb" else 1e6 if m.group(2) in "Mm" else 1))


def pool_of(tag: str):
    hits = [p for p in LOGS.glob(f"*_{tag}.json")]
    for p in hits:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("pool_tokens"):
            return int(d["pool_tokens"]), p.name
    return None, (hits[0].name if hits else None)


def scan(path: Path):
    # ★`-done` 은 경고로 낮춘다 — 끝난 배치의 알려진 결함으로 스위트를 빨갛게 두면
    #   **새 문제를 가린다**(`dryrun_batch`·`lint_bat` 규칙 26 과 같은 규약).
    #   🚫그렇다고 숨기지는 않는다 — 인쇄는 그대로 남는다.
    err, warn = [], []
    done = path.name.endswith("-done.bat")
    text = io.open(path, encoding="utf-8", errors="replace").read()
    if any(EXEMPT.match(ln) for ln in text.split(NL)):
        return err, warn
    for ln in text.split(NL):
        s = ln.strip()
        if s.upper().startswith("REM ") or not any(t in s for t in EVAL_TOOLS):
            continue
        mt = re.search(r"--tokens\s+(\S+)", s)
        mm = re.search(r"--models\s+(.+?)(?:\s+--|\s*$)", s)
        if not mt or not mm:
            continue
        n_eval = parse_tokens(mt.group(1))
        if n_eval is None:
            continue
        tags = [t for t in mm.group(1).split() if not t.startswith("-")]
        pools = {}
        for tag in tags:
            pt, src = pool_of(tag)
            if pt is None:
                warn.append(f"{path.name}: `{tag}` 의 학습 json 에 `pool_tokens` 가 없다"
                            f"{'' if src else ' (json 자체가 없다)'}")
                continue
            pools[tag] = pt
            if pt > n_eval:
                err.append(f"{path.name}: ★`{tag}` 는 풀 {pt/1e6:.0f}M 으로 학습됐는데 "
                           f"`--tokens {mt.group(1)}`({n_eval/1e6:.0f}M) 의 val 로 채점한다 — "
                           f"**그 val 은 이 모델의 학습 데이터다**(결과 075 §6)")
        if len(set(pools.values())) > 1:
            err.append(f"{path.name}: ★한 호출에 **풀이 다른 모델**이 섞였다 "
                       f"({', '.join(f'{k}={v/1e6:.0f}M' for k, v in sorted(pools.items()))}) — "
                       f"오염 정도가 달라 짝짓기가 무효다. 풀을 넘는 비교는 `common_bpb` 로")
    if done:
        warn += [f"[-done] {m}" for m in err]
        err = []
    return err, warn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bat", default=None)
    a = ap.parse_args()

    bats = ([Path(a.bat)] if a.bat else
            sorted(list(ROOT.glob("run_*.bat")) + list((ROOT / "scripts" / "batch").glob("*.bat"))))
    err, warn, n = [], [], 0
    for p in bats:
        if not p.is_file():
            continue
        n += 1
        e, w = scan(p)
        err += e
        warn += w

    print("=" * 96)
    print("  평가 val ↔ 학습 풀 대조 — *'채점지가 답안지였는가'*(결과 075 §6)")
    print("=" * 96)
    print(f"  배치 {n}개 검사")
    for m in err:
        print(f"  🚫 {m}")
    for m in warn:
        print(f"  ⚠️ {m}")
    print()
    print(f"  에러 {len(err)}건 · 경고 {len(warn)}건")
    if not err and not warn:
        print("  ✅ 평가 호출의 val 이 전부 학습 풀 밖이다.")
    elif not err:
        # ★함정 38 — 인쇄와 판정이 갈라지면 안 된다. 경고가 있으면 "전부 밖" 이라고 안 쓴다.
        print(f"  ⚠️ 살아 있는 배치에는 에러가 없다. 🚫**경고 {len(warn)}건은 남아 있다** — "
              "위 줄을 읽는다(`-done` 은 낮춘 것이지 없앤 것이 아니다).")
    else:
        print("  ★고치는 법: `--tokens` 를 그 모델의 풀과 같게 하거나, 풀을 넘는 비교면 "
              "`common_bpb.py` 를 쓴다. 의도한 것이면 배치에 `REM EVAL-POOL-OK: <사유>`.")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
