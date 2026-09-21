#!/usr/bin/env python3
"""Open P092 Stage3 only when a 100M dynamic arm survives the registered gap."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "runs" / "logs"
TAGS = ("p092_s2_dense100", "p092_s2_dynamic50", "p092_s2_dynamic25")


def one(tag: str) -> dict:
    hits = list(LOGS.glob(f"*_{tag}.json"))
    if len(hits) != 1:
        raise ValueError(f"tag={tag} json_count={len(hits)} expected=1")
    return json.loads(hits[0].read_text(encoding="utf-8"))


def main() -> int:
    try:
        rows = {tag: one(tag) for tag in TAGS}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[GATE FAIL] {type(exc).__name__}: {exc}")
        return 2
    dense = float(rows[TAGS[0]]["final"]["val_loss"])
    survivors = []
    for tag in TAGS[1:]:
        row = rows[tag]
        val = float(row["final"]["val_loss"])
        gap = val - dense
        mode = row.get("connectivity_mode")
        density = row.get("connectivity_density")
        ok = (mode == "dynamic" and int(row.get("n_skip", 0)) == 0 and gap <= 0.07)
        print(f"tag={tag} mode={mode} density={density} val={val:.6f} "
              f"dense_gap={gap:+.6f} skip={row.get('n_skip')} eligible={int(ok)}")
        if ok:
            survivors.append(tag)
    if not survivors:
        print("[GATE NEGATIVE] no dynamic 100M arm has dense gap <= +0.07 with skip0")
        return 8
    print(f"[GATE PASS] Stage3 may run; survivors={','.join(survivors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
