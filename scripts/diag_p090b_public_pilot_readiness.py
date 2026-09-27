#!/usr/bin/env python3
"""P090B Stage0eW: read-only, no-text public SFT and named pilot preflight.

The result is evidence for *some* technical gates, never automatic approval of
source rights, semantic quality, broad benchmark contamination, or formal SFT.
Only the explicitly supplied pilot directory and the fixed public-v3 assets are
read; no source row, prompt, or response is printed or copied.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from diag_p090b_public_preflight import (  # noqa: E402
    digest, full_mask_counts, panel_exact_overlap, source_quality_screen,
    split_counts,
)

PUBLIC = ROOT / "HF" / "sft_ready"
LEGACY = ROOT / "data_cache" / "tok-ko-en-32768.json"
CHAT32 = ROOT / "data_cache" / "tok-ko-en-32768-chat32.json"
PILOT_FILES = {
    "train": "train/basic_korean_v1_pilot_train.canonical.jsonl",
    "dev": "dev/basic_korean_v1_pilot_dev.canonical.jsonl",
    "eval": "eval/basic_korean_v1_pilot_eval.canonical.jsonl",
}


def exact_regular(path: Path, root: Path) -> Path:
    """Disallow links and traversal at every component below a named root."""
    if path == root or not path.is_relative_to(root):
        raise ValueError("file must be strictly inside the named root")
    for part in (root, *reversed(path.parents)):
        if part == root or part.is_relative_to(root):
            if part.is_symlink():
                raise ValueError("linked pilot path refused")
    if path.is_symlink() or not path.is_file():
        raise ValueError("named pilot file is absent or linked")
    return path


def load_rows(path: Path) -> list[dict]:
    from tinylm.data.sft import load_canonical

    rows = load_canonical(path)
    if any(not isinstance(row.get("meta"), dict) for row in rows):
        raise ValueError("canonical row without metadata")
    return rows


def prompt_hashes(rows: list[dict]) -> set[bytes]:
    from tinylm.data.sft import conversation_split_key

    return {conversation_split_key(row) for row in rows}


def split_overlap(left: list[dict], right: list[dict]) -> int:
    return len(prompt_hashes(left) & prompt_hashes(right))


def mask_evidence(rows: list[dict], tok) -> dict:
    from tinylm.data.sft import mask_stats

    stats = mask_stats(rows, tok)
    full = full_mask_counts(rows, tok)
    passed = (0.02 <= stats["ratio"] <= 0.90
              and stats["empty_mask"] == 0
              and stats["max_len"] <= 1024
              and full["missing_assistant_body"] == 0
              and full["missing_end_token"] == 0)
    return {
        "gate": "PASS" if passed else "FAIL", "rows": len(rows),
        "tokens": stats["tokens"], "supervised_tokens": stats["supervised"],
        "supervised_ratio": round(stats["ratio"], 8),
        "empty_mask": stats["empty_mask"], "max_len": stats["max_len"],
        "missing_assistant_body": full["missing_assistant_body"],
        "missing_end_token": full["missing_end_token"],
    }


def pilot_summary(rows_by_split: dict[str, list[dict]], manifest: dict) -> dict:
    rows = [row for split in ("train", "dev", "eval") for row in rows_by_split[split]]
    meta = [row["meta"] for row in rows]
    counts = lambda key: dict(sorted(Counter(str(row.get(key, "MISSING")) for row in meta).items()))
    assistant_turns = Counter(
        sum(msg.get("role") == "assistant" for msg in row["messages"]) for row in rows
    )
    train = rows_by_split["train"]
    heldout = rows_by_split["dev"] + rows_by_split["eval"]
    status = str(manifest.get("status", "MISSING"))
    return {
        "rows_by_split": {name: len(group) for name, group in rows_by_split.items()},
        "canonical_bytes": sum(int(item["bytes"])
                               for item in manifest["canonical_files"].values()),
        "planned_p2_canonical_bytes": manifest.get("planned_p2_canonical_bytes"),
        "status_from_manifest": status,
        "semantic_review": manifest.get("semantic_review", "NOT_RUN"),
        "naturalness_review": manifest.get("naturalness_review", "NOT_RUN"),
        "b_alignment_release": manifest.get("preliminary_b_alignment_screen", {}).get(
            "release_status", "NOT_RUN"),
        "task_counts": counts("task"), "track_counts": counts("task_track"),
        "domain_counts": counts("domain"),
        "register_counts": counts("register"),
        "review_status_counts": counts("review_status"),
        "assistant_turn_counts": dict(sorted(assistant_turns.items())),
        "train_dev_first_prompt_overlap": split_overlap(train, rows_by_split["dev"]),
        "train_eval_first_prompt_overlap": split_overlap(train, rows_by_split["eval"]),
        "train_heldout_first_prompt_overlap": split_overlap(train, heldout),
        "dev_eval_first_prompt_overlap": split_overlap(rows_by_split["dev"], rows_by_split["eval"]),
        "trainer_meta_source_present": all(isinstance(row.get("source"), str)
                                           for row in meta),
        "trainer_direct_path_accepted": False,
        "license_or_internal_rights_declared": bool(manifest.get("license")
                                                    or manifest.get("usage_rights")),
        "human_quality_gate": "NOT_RUN",
    }


def audit(pilot_root: Path) -> dict:
    from tokenizers import Tokenizer

    if pilot_root.is_symlink() or not pilot_root.is_dir():
        raise ValueError("named pilot directory is absent or linked")
    pilot = {name: exact_regular(pilot_root / rel, pilot_root)
             for name, rel in PILOT_FILES.items()}
    manifest_file = exact_regular(
        pilot_root / "manifests/basic_korean_v1_pilot_manifest.json", pilot_root)
    pilot_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if (pilot_manifest.get("dataset_name"), pilot_manifest.get("dataset_version")) != (
            "BasicKorean", "v1"):
        raise ValueError("pilot manifest identity differs")
    pilot_sha = {}
    for split, path in pilot.items():
        spec = pilot_manifest["canonical_files"][split]
        if spec.get("path") != PILOT_FILES[split] or spec.get("sha256", "").upper() != digest(path):
            raise ValueError(f"pilot {split} path/SHA differs from manifest")
        if spec.get("bytes") != path.stat().st_size:
            raise ValueError(f"pilot {split} byte size differs from manifest")
        pilot_sha[split] = digest(path)
    pilot_rows = {split: load_rows(path) for split, path in pilot.items()}
    if any(len(pilot_rows[split]) != pilot_manifest["canonical_files"][split]["records"]
           for split in pilot):
        raise ValueError("pilot split row counts differ from manifest")

    public_manifest_file = PUBLIC / "p090_public_v3_manifest.json"
    public_manifest = json.loads(public_manifest_file.read_text(encoding="utf-8"))
    if public_manifest.get("schema") != "TINYLM_PUBLIC_SFT_V1":
        raise ValueError("public manifest schema differs")
    public_files = {name: PUBLIC / f"p090_public_v3_{name}.canonical.jsonl"
                    for name in ("train", "val")}
    for name, path in public_files.items():
        if path.is_symlink() or digest(path) != public_manifest["output_sha256"][name]:
            raise ValueError(f"public {name} canonical SHA differs")
    if digest(LEGACY) != public_manifest["token_filter"]["tokenizer_sha256"]:
        raise ValueError("public legacy tokenizer SHA differs")
    public_rows = {name: load_rows(path) for name, path in public_files.items()}
    public_all = public_rows["train"] + public_rows["val"]
    pilot_all = pilot_rows["train"] + pilot_rows["dev"] + pilot_rows["eval"]
    tokenizers = {"legacy": Tokenizer.from_file(str(LEGACY)),
                  "chat32": Tokenizer.from_file(str(CHAT32))}
    source = source_quality_screen(public_rows["train"], public_rows["val"], public_manifest)
    public_split = split_counts(public_rows["train"], public_rows["val"])
    panel = panel_exact_overlap(public_all)
    pilot_info = pilot_summary(pilot_rows, pilot_manifest)
    pilot_info["canonical_sha256"] = pilot_sha
    pilot_info["manifest_sha256"] = digest(manifest_file)
    pilot_info["mask"] = {lineage: mask_evidence(pilot_all, tok)
                          for lineage, tok in tokenizers.items()}
    pilot_info["public_train_to_pilot_heldout_first_prompt_overlap"] = split_overlap(
        public_rows["train"], pilot_rows["dev"] + pilot_rows["eval"])
    public_mask = {lineage: mask_evidence(public_all, tok)
                   for lineage, tok in tokenizers.items()}
    public_info = {
        "manifest_sha256": digest(public_manifest_file),
        "canonical_sha256": {name: digest(path) for name, path in public_files.items()},
        "tokenizer_sha256": {"legacy": digest(LEGACY), "chat32": digest(CHAT32)},
        "rows_by_split": {name: len(group) for name, group in public_rows.items()},
        "split": public_split,
        "p100_fixed_panel_exact": panel,
        "source_metadata_gate": source["source_metadata_gate"],
        "source_language_counts": source["source_language_counts"],
        "multi_turn_rows": source["multi_turn_rows"],
        "url_rows": source["url_rows"], "email_rows": source["email_rows"],
        "contamination_manifest_gate": public_manifest.get("contamination_gate", "NOT_RUN"),
        "tokenizer_mask_manifest_gate": public_manifest.get("tokenizer_mask_gate", "NOT_RUN"),
        "source_quality_manifest_gate": public_manifest.get("source_quality_gate", "NOT_RUN"),
        "mask": public_mask,
    }
    technical = (source["source_metadata_gate"] == "PASS"
                 and public_split["first_prompt_overlap"] == 0
                 and public_split["source_id_overlap"] == 0
                 and panel["matched_user_messages"] == 0
                 and all(item["gate"] == "PASS" for item in public_mask.values())
    )
    return {
        "schema": "P090B_PUBLIC_PILOT_READINESS_V1",
        "scope": "public-v3+named-BasicKorean-pilot only; no protected held-out or broad eval scan",
        "public": public_info, "pilot": pilot_info,
        "public_technical_gate": "PASS" if technical else "FAIL",
        "formal_train_ready": False,
        "formal_hold_reasons": [
            "public contamination is only checked against named P100 panel and pilot; broad/held-out remains NOT_RUN",
            "public source quality and use rights need independent human adjudication",
            "public manifest three required gates are not all PASS",
            "pilot is review-pending, tiny, lacks trainer source metadata and is outside approved HF/sft_ready manifest",
        ],
    }


def self_test() -> None:
    a = {"messages": [{"role": "user", "content": "same"}], "meta": {}}
    b = {"messages": [{"role": "user", "content": "different"}], "meta": {}}
    assert split_overlap([a], [a]) == 1
    assert split_overlap([a], [b]) == 0
    fixture = {"canonical_files": {"train": {"bytes": 2}, "dev": {"bytes": 3},
                                   "eval": {"bytes": 4}}}
    rows = {"train": [a], "dev": [b], "eval": [b]}
    result = pilot_summary(rows, fixture)
    assert result["canonical_bytes"] == 9
    assert result["train_heldout_first_prompt_overlap"] == 0
    assert result["dev_eval_first_prompt_overlap"] == 1
    assert not result["trainer_meta_source_present"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pilot_root", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("[PASS] P090B split/readiness fixture; original corpora NOT_RUN")
        return 0
    if args.pilot_root is None:
        parser.error("exact pilot_root is required")
    report = audit(args.pilot_root)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if report["public_technical_gate"] != "PASS":
        print("[FAIL] public SFT technical preflight; do not run SFT")
        return 1
    print("[HOLD] public-v3/pilot technical audit done; formal SFT TRAIN_READY=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
