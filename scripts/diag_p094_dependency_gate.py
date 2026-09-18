#!/usr/bin/env python3
"""P094 R0: require machine-readable P022C packed/masterless evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", default="runs/evidence/P022C_shadow_storage.json")
    args = parser.parse_args()
    path = Path(args.evidence)
    if not path.is_file():
        print(f"[DEPENDENCY HOLD] missing {path}")
        print("required schema=p022c.shadow-storage.v1 actual_packed=true hidden_fp32_master=false "
              "and a non-empty residual_need_signature")
        return 8
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[GATE FAIL] invalid evidence JSON: {exc}")
        return 3
    errors = []
    if data.get("schema") != "p022c.shadow-storage.v1":
        errors.append("schema")
    if data.get("actual_packed") is not True:
        errors.append("actual_packed")
    if data.get("hidden_fp32_master") is not False:
        errors.append("hidden_fp32_master")
    if not data.get("residual_need_signature"):
        errors.append("residual_need_signature")
    if errors:
        print(f"[DEPENDENCY HOLD] incomplete P022C evidence fields={errors}")
        return 8
    print("[PASS] P094 R0: P022C actual packed/masterless evidence and residual need signature present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
