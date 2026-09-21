#!/usr/bin/env python3
"""Plan or push a bounded benchmark-only W&B backfill."""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import bench_tsv  # noqa: E402
from wandb_sync import collect, read_key  # noqa: E402

DEFAULT_MANIFEST = ROOT / "scripts" / "wandb_bench_backfill_tags.tsv"


def load_manifest(path: Path) -> list[tuple[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    result = []
    seen = set()
    for line_no, row in enumerate(rows, 2):
        tag = (row.get("tag") or "").strip()
        reason = (row.get("reason") or "").strip()
        if not tag or not reason:
            raise ValueError(f"manifest line {line_no}: tag and reason required")
        if tag in seen:
            raise ValueError(f"manifest line {line_no}: duplicate tag {tag}")
        seen.add(tag)
        result.append((tag, reason))
    if not result:
        raise ValueError("manifest is empty")
    return result


def local_targets(manifest: list[tuple[str, str]]):
    all_rows = bench_tsv.load()
    targets = []
    errors = []
    for tag, reason in manifest:
        runs = collect(tag, exact=True)
        rows = [row for row in all_rows if row.get("model") == tag]
        if len(runs) != 1:
            errors.append(f"tag={tag} eligible_local_runs={len(runs)} expected=1")
            continue
        if not rows:
            errors.append(f"tag={tag} benchmark_rows=0")
            continue
        targets.append((tag, reason, runs[0][0], rows))
    return targets, errors


def _summary(rows: list[dict]) -> dict:
    output = {}
    by_task: dict[str, list[dict]] = {}
    for row in rows:
        by_task.setdefault(str(row["task"]), []).append(row)
        output[f"bench/{row['task']}/{row['metric']}"] = row["value"]
    for task, task_rows in by_task.items():
        sample = task_rows[0]
        for key in ("n", "n_asked", "skipped", "seed", "pmi"):
            if sample.get(key) is not None:
                output[f"bench/{task}/{key}"] = sample[key]
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--project", default=os.environ.get("TL_WB_PROJECT", "tinylm"))
    parser.add_argument("--entity", default=os.environ.get("TL_WB_ENTITY") or None)
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()
    try:
        manifest = load_manifest(Path(args.manifest).expanduser().resolve())
        targets, errors = local_targets(manifest)
    except (OSError, ValueError) as exc:
        print(f"[STOP] {type(exc).__name__}: {exc}")
        return 2
    for error in errors:
        print(f"[STOP] {error}")
    if errors:
        return 2
    print(f"[bench-backfill] targets={len(targets)} project={args.project}")
    for tag, reason, run_id, rows in targets:
        print(f"  tag={tag} run_id={run_id} long_rows={len(rows)} reason={reason}")
    if not args.push:
        print("[PLAN ONLY] network 0; add --push to update the four existing training runs")
        return 0
    try:
        import wandb

        key = read_key()
        wandb.login(key=key)
        for tag, _reason, run_id, rows in targets:
            run = wandb.init(
                project=args.project, entity=args.entity, id=run_id, name=run_id,
                resume="allow", reinit=True,
            )
            run.summary.update(_summary(rows))
            wide = bench_tsv.rows_for(tag, wide=True)
            run.log({bench_tsv.KEY_WIDE: wandb.Table(
                columns=bench_tsv.COLS_WIDE, data=wide,
            )})
            run.finish()
            print(f"  [PASS] {run_id}: summary={len(_summary(rows))} table_rows={len(wide)}")
        return 0
    except Exception as exc:  # noqa: BLE001 - external service boundary
        print(f"[FAIL] benchmark backfill: {type(exc).__name__}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
