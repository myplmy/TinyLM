#!/usr/bin/env python3
"""★벤치 결과의 **정본 파일** — `test_result/bench_results.tsv` 를 읽고 쓴다.

## 왜 이 파일이 있나 (제안서 `proposal/20260904_wandb-벤치마크-시각화-구조.md` §5.2)

W&B 는 **뷰**다. 뷰가 정본이면 재구성이 불가능하다 — `runs/registry.tsv` 를 만든 것과
**같은 원리**다. 그래서 벤치 결과의 정본은 **디스크의 TSV** 이고, W&B 표는 매번
**그 TSV 에서 전량 재구성**한다.

## 디스크는 long, 뷰는 wide — **일부러 다르다**

| | 모양 | 왜 |
|---|---|---|
| 디스크(`bench_results.tsv`) | **long** (`model·task·metric·value`+메타) | ★**지표를 추가해도 스키마가 안 바뀐다.** 행만 는다 |
| W&B 표(`bench/table_wide`) | **wide** (`model·task·acc·acc_norm·gold_ce`+메타) | ★W&B 의 공식 `${field:...}` 셀렉터가 **열**만 고를 수 있다 |

★**사용자 판정(2026-09-06, 제안서 §4.2.3)**: long 에서는 `params` 셀렉터가 W&B 화면에서
안 먹었고 **wide 에서 해결**됐다. → **안 A + wide 표**로 확정.

🚫**스키마를 두 곳에 적지 않는다**(함정 18) — `COLS_WIDE`·`METRICS`·`KEY_WIDE` 의
정본은 **이 파일**이고 `wandb_table_probe.py` 와 `eval_bench_suite.py` 가 여기서 읽는다.

## 갱신 규약 — 🚫스칼라와 표는 다르다 (제안서 §3.2, 함정 28)

- **summary 스칼라**(`bench/<과제>/<지표>`)는 **덮어쓴다** — 최신값 하나만 뜻이 있다.
- **표**는 **upsert 후 전량 재구성**한다 — 이번에 안 돈 과제의 행이 사라지면 안 된다.

사용:

    python scripts/bench_tsv.py                 # 정본을 표로 인쇄한다(읽기 전용)
    python scripts/bench_tsv.py --model d12_cla2_r20 --wide
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "test_result" / "bench_results.tsv"

# ── ★스키마 정본 ────────────────────────────────────────────────────────────
META = ["n", "n_asked", "skipped", "seed", "pmi"]
METRICS = ["acc", "acc_norm", "gold_ce"]
COLS_LONG = ["model", "task", "metric", "value"] + META
COLS_WIDE = ["model", "task"] + METRICS + META

KEY_LONG = "bench/table"
KEY_WIDE = "bench/table_wide"

_NUM = {"value", "n", "n_asked", "skipped", "seed"}


def _fmt(col, v):
    if v is None:
        return ""
    if col == "pmi":
        return "true" if v else "false"
    if col == "value":
        return f"{float(v):.6f}"
    return str(v)


def _parse(col, s):
    if s == "":
        return None
    if col == "pmi":
        return s.lower() == "true"
    if col == "value":
        return float(s)
    if col in _NUM:
        try:
            return int(s)
        except ValueError:
            return float(s)
    return s


def load() -> list[dict]:
    """정본 전량을 dict 목록으로 읽는다. 파일이 없으면 빈 목록."""
    if not TSV.exists():
        return []
    lines = TSV.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    head = lines[0].split("\t")
    out = []
    for ln in lines[1:]:
        if not ln.strip():
            continue
        cells = ln.split("\t")
        cells += [""] * (len(head) - len(cells))
        out.append({c: _parse(c, cells[i]) for i, c in enumerate(head)})
    return out


def save(rows: list[dict]) -> None:
    """`(model, task, metric)` 로 정렬해 원자적으로 쓴다."""
    rows = sorted(rows, key=lambda r: (str(r.get("model")), str(r.get("task")),
                                       METRICS.index(r["metric"])
                                       if r.get("metric") in METRICS else 99,
                                       str(r.get("metric"))))
    body = ["\t".join(COLS_LONG)]
    for r in rows:
        body.append("\t".join(_fmt(c, r.get(c)) for c in COLS_LONG))
    data = ("\n".join(body) + "\n").encode("utf-8")
    tmp = TSV.with_suffix(".tsv.tmp")
    tmp.write_bytes(data)                    # ★encode-first(함정 35: write_text 는 먼저 지운다)
    assert tmp.stat().st_size == len(data), "정본 TSV 쓰기 크기 불일치"
    tmp.replace(TSV)


def upsert(new_rows: list[dict]) -> tuple[int, int]:
    """`(model, task, metric)` 을 열쇠로 갱신·삽입한다. 반환 `(갱신, 삽입)`."""
    cur = load()
    idx = {(r.get("model"), r.get("task"), r.get("metric")): i for i, r in enumerate(cur)}
    upd = ins = 0
    for r in new_rows:
        k = (r.get("model"), r.get("task"), r.get("metric"))
        if k in idx:
            cur[idx[k]] = r
            upd += 1
        else:
            idx[k] = len(cur)
            cur.append(r)
            ins += 1
    save(cur)
    return upd, ins


def rows_from_rec(model: str, task: str, rec: dict, n, seed, pmi) -> list[dict]:
    """한 `(model, task)` 의 계측 dict 를 long 행들로 편다.

    🚫**과제별 분기가 없다**(제안서 검증 ⑯) — `METRICS` 에 있는 키만 그대로 편다.
    """
    out = []
    for m in METRICS:
        if m not in rec:
            continue
        out.append({"model": model, "task": task, "metric": m, "value": rec[m],
                    "n": rec.get("n", n), "n_asked": rec.get("n_asked"),
                    "skipped": rec.get("skipped"), "seed": seed, "pmi": bool(pmi)})
    return out


def to_wide(rows: list[dict]) -> list[list]:
    """long 행들을 `(model, task)` 로 묶어 **wide 행 목록**(리스트의 리스트)으로."""
    grouped: dict[tuple, dict] = {}
    for r in rows:
        g = grouped.setdefault((r.get("model"), r.get("task")), {})
        g[r.get("metric")] = r.get("value")
        for c in META:
            g.setdefault(c, r.get(c))
    out = []
    for (model, task), g in sorted(grouped.items(), key=lambda kv: (str(kv[0][0]),
                                                                   str(kv[0][1]))):
        out.append([model, task] + [g.get(m) for m in METRICS]
                   + [g.get(c) for c in META])
    return out


def rows_for(model: str, wide: bool = True):
    """한 모델의 **누적 전량**을 표로. W&B 에 올릴 때 쓰는 진입점."""
    mine = [r for r in load() if r.get("model") == model]
    if wide:
        return to_wide(mine)
    return [[r.get(c) for c in COLS_LONG] for r in mine]


def main() -> int:
    ap = argparse.ArgumentParser(description="벤치 정본 TSV 조회(읽기 전용)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--wide", action="store_true")
    a = ap.parse_args()
    rows = load()
    if not TSV.exists():
        print(f"  정본이 아직 없다: {TSV.relative_to(ROOT)}")
        print("  ★`eval_bench_suite.py --wandb` 가 처음 돌 때 생긴다.")
        return 0
    if a.model:
        data = rows_for(a.model, wide=a.wide)
        cols = COLS_WIDE if a.wide else COLS_LONG
    else:
        data = to_wide(rows) if a.wide else [[r.get(c) for c in COLS_LONG] for r in rows]
        cols = COLS_WIDE if a.wide else COLS_LONG
    print("  " + " | ".join(cols))
    for d in data:
        print("  " + " | ".join("" if v is None else str(v) for v in d))
    print(f"\n  행 {len(data)}개 · 정본 {TSV.relative_to(ROOT)} ({len(rows)} long 행)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
