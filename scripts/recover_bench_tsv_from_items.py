#!/usr/bin/env python3
"""Recover local benchmark summary rows from a preserved per-item JSONL.

This is a local-only repair path for evaluations that omitted ``--wandb`` in
the launcher.  It never loads a model and never contacts W&B.  The default is
plan-only; ``--apply`` performs the bounded upsert into
``test_result/bench_results.tsv``.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

import bench_tsv


def summarize(path: Path, *, seed: int, pmi: bool) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        model = str(row.get("model") or "")
        task = str(row.get("task") or "")
        item_id = str(row.get("id") or "")
        if not model or not task or not item_id:
            raise ValueError(f"line {line_no}: model/task/id required")
        identity = (model, task, item_id)
        if identity in seen:
            raise ValueError(f"line {line_no}: duplicate item {identity}")
        seen.add(identity)
        grouped[(model, task)].append(row)

    output: list[dict] = []
    for (model, task), rows in sorted(grouped.items()):
        valid = [row for row in rows if not row.get("skipped")]
        if not valid:
            raise ValueError(f"{model}/{task}: no valid rows")
        required = {"gold", "pred_internal", "pred_internal_norm", "mean_nll"}
        for row in valid:
            missing = required - set(row)
            if missing:
                raise ValueError(f"{model}/{task}/{row['id']}: missing {sorted(missing)}")
        rec = {
            "acc": statistics.fmean(
                int(row["pred_internal"] == row["gold"]) for row in valid
            ),
            "acc_norm": statistics.fmean(
                int(row["pred_internal_norm"] == row["gold"]) for row in valid
            ),
            "gold_ce": statistics.fmean(
                float(row["mean_nll"][int(row["gold"])]) for row in valid
            ),
            "n": len(valid),
            "n_asked": len(rows),
            "skipped": len(rows) - len(valid),
        }
        output.extend(bench_tsv.rows_from_rec(model, task, rec, len(rows), seed, pmi))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--no-pmi", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    path = Path(args.items).expanduser().resolve()
    try:
        rows = summarize(path, seed=args.seed, pmi=not args.no_pmi)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[STOP] {type(exc).__name__}: {exc}")
        return 2
    keys = sorted({(row["model"], row["task"]) for row in rows})
    print(f"[bench-recover] source={path} groups={len(keys)} long_rows={len(rows)}")
    for model, task in keys:
        metrics = {row["metric"]: row["value"] for row in rows
                   if row["model"] == model and row["task"] == task}
        print(f"  {model} {task}: acc={metrics.get('acc'):.4f} "
              f"acc_norm={metrics.get('acc_norm'):.4f} gold_ce={metrics.get('gold_ce'):.4f}")
    if not args.apply:
        print("[PLAN ONLY] local TSV unchanged; add --apply to upsert these exact rows")
        return 0
    updated, inserted = bench_tsv.upsert(rows)
    print(f"[PASS] updated={updated} inserted={inserted} -> {bench_tsv.TSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
