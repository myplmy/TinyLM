#!/usr/bin/env python3
"""P106B Stage1cW fixed parent/student evidence and paired error census.

Check-only is CPU/read-only. The default mode reads user-produced public
benchmark per-item JSONL; it never runs a model or claims causal improvement.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diag_p106b_online_pseudo_sft import (  # noqa: E402
    CANONICAL_OUT, INPUT_MANIFEST_OUT, PSEUDO_OUT, RESULT_MANIFEST_OUT,
    OUTPUT_CKPT, OUTPUT_META, STUDENT, RUN_TAG, digest,
)
from scripts.diag_p106_bonsai_assets import regular  # noqa: E402

PARENT_TAG = "p076_b3_ag2_mean_s1337"
TASKS = ("klue_ynat", "klue_nli", "arc_easy")
OUT = ROOT / "runs/bench/p106b_stage1c_p100_parent_student.jsonl"
ITEMS = {task: ROOT / f"runs/bench/p106b_stage1c_{task}_items.jsonl" for task in TASKS}
ASSETS = {task: ROOT / f"datasets/bench/{task}.jsonl" for task in TASKS}


def verify_training_lineage() -> dict:
    for path in (CANONICAL_OUT, INPUT_MANIFEST_OUT, PSEUDO_OUT,
                 RESULT_MANIFEST_OUT, OUTPUT_CKPT, OUTPUT_META, STUDENT, *ASSETS.values()):
        if not regular(path):
            raise FileNotFoundError(f"required regular file absent or linked: {path}")
    source = json.loads(INPUT_MANIFEST_OUT.read_text(encoding="utf-8"))
    result = json.loads(RESULT_MANIFEST_OUT.read_text(encoding="utf-8"))
    if (source.get("schema") != "P106B_ONLINE_PSEUDO_INPUT_V1"
            or result.get("schema") != "P106B_STAGE1BW_ONLINE_PSEUDO_SFT_V1"
            or source.get("formal_train_ready") is not False
            or result.get("formal_train_ready") is not False
            or result.get("pseudo_label_status") != "UNVERIFIED_NOT_P106_ACCEPT"
            or result.get("tag") != RUN_TAG
            or result.get("checkpoint_written") is not True):
        raise ValueError("Stage1bW manifest/label-state contract differs")
    checks = ((PSEUDO_OUT, source.get("raw_teacher_sha256")),
              (CANONICAL_OUT, source.get("canonical_train_sha256")),
              (OUTPUT_CKPT, result.get("checkpoint_sha256")),
              (STUDENT, source.get("student_checkpoint_sha256")))
    if any(digest(path) != expected for path, expected in checks):
        raise ValueError("teacher, canonical or checkpoint SHA differs from Stage1bW")
    if (source["canonical_train_sha256"] != result["canonical_train_sha256"]
            or source["student_checkpoint_sha256"] != result["student_checkpoint_sha256"]):
        raise ValueError("Stage1bW input/result manifest lineage differs")
    if digest(OUTPUT_META) != result.get("paired_training_metadata_sha256"):
        raise ValueError("P100 paired training metadata SHA differs from Stage1bW")
    meta = json.loads(OUTPUT_META.read_text(encoding="utf-8"))
    if (meta.get("schema") != "P106B_DIAGNOSTIC_TRAIN_METADATA_V1"
            or meta.get("tag") != OUTPUT_META.stem or meta.get("arch") != "tied"
            or meta.get("preset") != "m100R1c" or meta.get("data") != "ko-en"
            or meta.get("final", {}).get("val_loss") is not None
            or meta.get("checkpoint_sha256") != result["checkpoint_sha256"]
            or meta.get("quality") != "NOT_RUN"):
        raise ValueError("P100 metadata would misstate pseudo-SFT lineage or validation")
    return {"schema": "P106B_STAGE1CW_PREFLIGHT_V1",
            "parent_tag": PARENT_TAG, "student_tag": RUN_TAG,
            "parent_sha256": source["student_checkpoint_sha256"],
            "student_sha256": result["checkpoint_sha256"],
            "data_label_state": "PSEUDO_UNVERIFIED",
            "canonical_train_rows": source["canonical_train_rows"],
            "benchmark_assets": list(TASKS),
            "model_evaluation": "NOT_RUN"}


def _rows(path: Path) -> list[dict]:
    if not regular(path):
        raise FileNotFoundError(f"per-item result missing or linked: {path}")
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def paired_error_counts(rows: list[dict], task: str) -> dict:
    by_id: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        if row.get("task") != task or row.get("model") not in (PARENT_TAG, RUN_TAG):
            raise ValueError("unexpected task/model in per-item evidence")
        identifier = row.get("id")
        if not isinstance(identifier, (str, int)) or str(identifier) in by_id and row["model"] in by_id[str(identifier)]:
            raise ValueError("missing or duplicate per-item ID/model")
        by_id[str(identifier)][row["model"]] = row
    counts = Counter()
    regressions = []
    for identifier, pair in sorted(by_id.items()):
        if set(pair) != {PARENT_TAG, RUN_TAG}:
            raise ValueError("parent/student item pairing incomplete")
        left, right = pair[PARENT_TAG], pair[RUN_TAG]
        if left.get("skipped") or right.get("skipped"):
            if bool(left.get("skipped")) != bool(right.get("skipped")):
                raise ValueError("parent/student skip asymmetry")
            counts["both_skipped"] += 1
            continue
        if left.get("gold") != right.get("gold"):
            raise ValueError("paired gold label differs")
        for key in ("pred_internal", "pred_harness"):
            if not isinstance(left.get(key), int) or not isinstance(right.get(key), int):
                raise ValueError("paired prediction is missing")
        counts["evaluated"] += 1
        parent_ok = left["pred_internal"] == left["gold"]
        student_ok = right["pred_internal"] == right["gold"]
        counts["parent_correct"] += int(parent_ok)
        counts["student_correct"] += int(student_ok)
        counts["improved"] += int(not parent_ok and student_ok)
        counts["regressed"] += int(parent_ok and not student_ok)
        counts["both_correct"] += int(parent_ok and student_ok)
        counts["both_wrong"] += int(not parent_ok and not student_ok)
        if parent_ok and not student_ok:
            regressions.append(identifier)
    if not counts["evaluated"]:
        raise ValueError("zero paired evaluated items")
    n = counts["evaluated"]
    return {"task": task, "items": len(by_id), **dict(counts),
            "parent_accuracy": counts["parent_correct"] / n,
            "student_accuracy": counts["student_correct"] / n,
            "parent_error_rate": 1 - counts["parent_correct"] / n,
            "student_error_rate": 1 - counts["student_correct"] / n,
            "regressed_item_ids_for_review": regressions[:32],
            "meaning_analysis": "MANUAL_REQUIRED"}


def self_test() -> None:
    rows = []
    for ident, gold, left, right in (("a", 0, 0, 1), ("b", 1, 0, 1),
                                    ("c", 1, 1, 1), ("d", 0, 1, 1)):
        for model, pred in ((PARENT_TAG, left), (RUN_TAG, right)):
            rows.append({"task": "klue_ynat", "model": model, "id": ident,
                         "gold": gold, "pred_internal": pred, "pred_harness": pred})
    result = paired_error_counts(rows, "klue_ynat")
    assert result["improved"] == 1 and result["regressed"] == 1
    assert result["both_correct"] == 1 and result["both_wrong"] == 1
    try:
        paired_error_counts(rows[:-1], "klue_ynat")
    except ValueError:
        pass
    else:
        raise AssertionError("missing paired item accepted")
    print("[PASS] P106B paired correct/wrong/regression and incomplete-pair fixtures; model/GPU NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    try:
        report = verify_training_lineage()
        if args.check_only:
            if OUT.exists() or OUT.is_symlink() or any(p.exists() or p.is_symlink() for p in ITEMS.values()):
                raise FileExistsError("Stage1cW output exists; never append a new evaluation to old evidence")
            print(json.dumps(report, sort_keys=True))
            print("[CHECK_ONLY] parent/student SHA and public assets PASS; model evaluation NOT_RUN")
            return 0
        summary = {task: paired_error_counts(_rows(path), task)
                   for task, path in ITEMS.items()}
        if not regular(OUT):
            raise FileNotFoundError("P100 raw parent/student answers absent")
        print(json.dumps({"schema": "P106B_STAGE1CW_POSTHOC_V1",
                          "lineage": report, "paired": summary,
                          "claim": "SAMPLED_PAIRED_SIGNALS_ONLY; semantically review raw P100 and regression IDs"},
                         ensure_ascii=False, sort_keys=True))
        print("[PASS] paired error rates and regression IDs recorded; SFT causality/general intelligence NOT_DECIDED")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P106B Stage1cW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
