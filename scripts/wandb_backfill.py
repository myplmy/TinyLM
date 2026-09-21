#!/usr/bin/env python3
"""Plan or perform a bounded W&B backfill from an approved tag manifest."""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from wandb_sync import collect, read_key, upload_runs  # noqa: E402

DEFAULT_MANIFEST = ROOT / "scripts" / "wandb_backfill_tags.tsv"


def load_manifest(path: Path) -> list[tuple[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line_no, row in enumerate(rows, 2):
        tag = (row.get("tag") or "").strip()
        reason = (row.get("reason") or "").strip()
        if not tag or not reason:
            raise ValueError(f"manifest line {line_no}: tag and reason are required")
        if tag in seen:
            raise ValueError(f"manifest line {line_no}: duplicate tag {tag}")
        seen.add(tag)
        result.append((tag, reason))
    if not result:
        raise ValueError("backfill manifest is empty")
    return result


def local_targets(manifest: list[tuple[str, str]]):
    selected = []
    errors = []
    for tag, reason in manifest:
        hits = collect(tag, exact=True)
        if len(hits) != 1:
            errors.append(f"tag={tag} eligible_local={len(hits)} expected=1")
            continue
        name, data = hits[0]
        selected.append((tag, reason, name, data))
    return selected, errors


def remote_ids(api, *, entity: str, project: str, names: list[str]) -> set[str]:
    if not names:
        return set()
    runs = api.runs(
        f"{entity}/{project}",
        filters={"name": {"$in": names}},
        per_page=max(50, len(names)),
    )
    return {str(run.id) for run in runs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--project", default=os.environ.get("TL_WB_PROJECT", "tinylm"))
    parser.add_argument("--entity", default=os.environ.get("TL_WB_ENTITY") or None)
    parser.add_argument("--push", action="store_true",
                        help="query remote IDs and upload only missing manifest targets")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    try:
        manifest = load_manifest(manifest_path)
        targets, errors = local_targets(manifest)
    except (OSError, ValueError) as exc:
        print(f"[STOP] {type(exc).__name__}: {exc}")
        return 2
    for error in errors:
        print(f"[STOP] {error}")
    if errors:
        return 2

    print(f"[backfill] manifest={manifest_path} targets={len(targets)} project={args.project}")
    for tag, reason, name, _data in targets:
        print(f"  local tag={tag} run_id={name} reason={reason}")
    if not args.push:
        print("[PLAN ONLY] remote 조회·업로드 0건. 실제 누락 복구: tool_wandb_backfill.sh --push")
        return 0

    try:
        import wandb

        key = read_key()
        wandb.login(key=key)
        api = wandb.Api(api_key=key)
        entity = args.entity or api.default_entity
        if not entity:
            raise ValueError("W&B default entity를 확인할 수 없다; --entity를 명시할 것")
        names = [name for _tag, _reason, name, _data in targets]
        existing = remote_ids(api, entity=entity, project=args.project, names=names)
        missing = [(name, data) for _tag, _reason, name, data in targets if name not in existing]
        for name in names:
            print(f"  remote run_id={name} status={'EXISTS' if name in existing else 'MISSING'}")
        if not missing:
            print("[PASS] manifest targets are already present remotely; upload 0")
            return 0
        upload_runs(wandb, missing, project=args.project, entity=entity)
        print(f"[PASS] uploaded_missing={len(missing)} skipped_existing={len(existing & set(names))}")
        return 0
    except Exception as exc:  # noqa: BLE001 - external service boundary
        # Authentication exceptions are intentionally not echoed: an SDK must
        # never get a chance to reflect credential material into the terminal.
        print(f"[FAIL] W&B backfill: {type(exc).__name__} (credential value suppressed)")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
