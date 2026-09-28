#!/usr/bin/env python3
"""P106B dictionary-derived candidate quarantine; no model or protected I/O.

This is a storage/lineage adapter, not a legal determination. It accepts only
already-generated teacher content for a SHA-pinned KRDict locator. A later
producer may call it after user-owned teacher execution; this module itself
never resolves a protected definition/example or marks a row TRAIN_READY.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_p106b_multisource_deck import DICT_REPO  # noqa: E402
from scripts.p106b_shards import ShardWriter, verify  # noqa: E402
from scripts.p106b_teacher_wrapper import wrap_turns  # noqa: E402

QUARANTINE_DIR = ROOT / "HF/sft_ready/p106b_krdict_by_sa_quarantine_v1/candidates"
PUBLIC_JOB_DIR = ROOT / "HF/sft_ready/p106b_public_job_deck_v1"
POLICY_URL = "https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo"
RIGHTS_FAMILY = "CC_BY_SA_2_0_KR_CANDIDATE"
LOCATOR_KEYS = {"source_namespace", "file", "entry_ordinal", "sense_ordinal",
                "target_code", "lexical_unit", "sense_id", "definition_sha256",
                "headword_sha256"}


def _locator(job: dict) -> dict:
    locator = job.get("protected_locator")
    if (job.get("source_family") != "krdict" or job.get("source_repo") != DICT_REPO
            or job.get("source_payload") is not None or not isinstance(locator, dict)
            or set(locator) != LOCATOR_KEYS or not re.fullmatch(
                r"[A-Fa-f0-9]{64}", str(job.get("parent_concept_id") or ""))):
        raise ValueError("only an exact dictionary locator can enter the quarantine")
    if any(not isinstance(value, (str, int)) or isinstance(value, bool)
           for value in locator.values()):
        raise ValueError("dictionary locator contains non-scalar or original text")
    if (not re.fullmatch(r"[A-Fa-f0-9]{64}", str(locator["definition_sha256"]))
            or not re.fullmatch(r"[A-Fa-f0-9]{64}", str(locator["headword_sha256"]))):
        raise ValueError("dictionary locator lacks exact source hashes")
    return locator


def candidate_row(job: dict, teacher_content: dict, *, generation_id: str,
                  teacher_model_sha256: str) -> dict:
    """Construct a quarantined *candidate*, never a public training row."""
    locator = _locator(job)
    if (not isinstance(teacher_content, dict)
            or set(teacher_content) != {"user_text", "assistant_text", "correction_note"}
            or not all(isinstance(teacher_content[key], str) for key in teacher_content)):
        raise ValueError("teacher content fields differ; teacher cannot write dataset metadata")
    canonical = wrap_turns([{"user_text": teacher_content["user_text"],
                             "assistant_text": teacher_content["assistant_text"]}],
                           source_id=job["source_id"],
                           source_sha256=job["source_sha256"],
                           teacher_model_sha256=teacher_model_sha256,
                           language="ko", source_license="CC-BY-SA-2.0-KR_candidate",
                           generation_id=generation_id,
                           correction_note=teacher_content["correction_note"],
                           source_repo=job["source_repo"],
                           source_revision=job["source_revision"],
                           source_object_id=job["source_id"],
                           source_transform="dictionary_grounded_qa",
                           parent_concept_id=job["parent_concept_id"],
                           source_rights_status="CC_BY_SA_2_0_KR_QUARANTINE")
    canonical["meta"].update({
        "rights_family": RIGHTS_FAMILY,
        "source_policy_url": POLICY_URL,
        "protected_locator": locator,
        "release_status": "LOCAL_QUARANTINE_NOT_REVIEWED",
        "training_eligible": False,
        "independent_expression_status": "NOT_DETERMINED",
    })
    # Deliberately NOT a top-level canonical conversation: the ordinary SFT
    # loader must not accept this file as training data by path alone.
    return {"schema": "P106B_RESTRICTED_CANDIDATE_V1",
            "candidate": canonical,
            "rights_family": RIGHTS_FAMILY,
            "release_status": "LOCAL_QUARANTINE_NOT_REVIEWED",
            "training_eligible": False}


def _candidate_valid(row: dict) -> bool:
    canonical = row.get("candidate", {}) if isinstance(row, dict) else {}
    meta = canonical.get("meta", {}) if isinstance(canonical, dict) else {}
    return (isinstance(meta, dict) and isinstance(canonical.get("messages"), list)
            and row.get("schema") == "P106B_RESTRICTED_CANDIDATE_V1"
            and row.get("rights_family") == RIGHTS_FAMILY
            and row.get("release_status") == "LOCAL_QUARANTINE_NOT_REVIEWED"
            and row.get("training_eligible") is False
            and meta.get("source_repo") == DICT_REPO
            and meta.get("rights_family") == RIGHTS_FAMILY
            and meta.get("source_rights_status") == "CC_BY_SA_2_0_KR_QUARANTINE"
            and meta.get("release_status") == "LOCAL_QUARANTINE_NOT_REVIEWED"
            and meta.get("training_eligible") is False
            and meta.get("student_training") == "NOT_RUN"
            and meta.get("label_status") == "PSEUDO_UNVERIFIED"
            and isinstance(meta.get("protected_locator"), dict)
            and meta.get("source_policy_url") == POLICY_URL)


def write_candidates(rows: list[dict], *, directory: Path | None = None) -> dict:
    """Write a bounded pilot only into the configured ignored quarantine path."""
    target = directory if directory is not None else QUARANTINE_DIR
    hf_root = ROOT / "HF"
    if (target != QUARANTINE_DIR or target == PUBLIC_JOB_DIR
            or hf_root.is_symlink() or (hf_root / "sft_ready").is_symlink()
            or target.parent.is_symlink() or not target.resolve().is_relative_to(hf_root.resolve())
            or target.is_symlink() or target.exists()):
        raise ValueError("quarantine output path differs or already exists")
    if not 1 <= len(rows) <= 128 or any(not _candidate_valid(row) for row in rows):
        raise ValueError("pilot must contain 1..128 quarantined dictionary candidates only")
    if len({row["candidate"]["meta"]["generation_id"] for row in rows}) != len(rows):
        raise ValueError("candidate generation IDs must be unique")
    writer = ShardWriter(target, "krdict_candidates")
    for row in rows:
        writer.append(row)
    manifest = writer.close(lineage={"rights_family": RIGHTS_FAMILY,
                                     "source_policy_url": POLICY_URL,
                                     "training_eligible": False,
                                     "independent_expression_status": "NOT_DETERMINED",
                                     "public_job_directory": PUBLIC_JOB_DIR.relative_to(ROOT).as_posix()})
    verify(target, manifest)
    return {"manifest": writer.manifest_path.relative_to(ROOT).as_posix(),
            "rows": manifest["rows"], "bytes": manifest["bytes"],
            "concat_sha256": manifest["concat_sha256"],
            "release_status": "LOCAL_QUARANTINE_NOT_REVIEWED"}


def self_test() -> None:
    sha = "A" * 64
    locator = {"source_namespace": "krdict/20260819", "file": "1_5000_20260819.json",
               "entry_ordinal": 1, "sense_ordinal": 0, "target_code": "123",
               "lexical_unit": "단어", "sense_id": "456",
               "definition_sha256": sha, "headword_sha256": sha}
    job = {"source_family": "krdict", "source_repo": DICT_REPO,
           "source_payload": None, "protected_locator": locator,
           "parent_concept_id": sha, "source_id": "B" * 64,
           "source_sha256": sha, "source_revision": "20260819"}
    content = {"user_text": "새로운 질문은?", "assistant_text": "새로운 답입니다.",
               "correction_note": "합성 fixture"}
    row = candidate_row(job, content, generation_id="fixture:g1",
                        teacher_model_sha256=sha)
    assert (_candidate_valid(row)
            and row["candidate"]["messages"][1]["content"][0]["text"] == content["assistant_text"])
    assert "reasoning_content" not in json.dumps(row, ensure_ascii=False)
    try:
        candidate_row(dict(job, source_family="aya_dataset"), content,
                      generation_id="bad", teacher_model_sha256=sha)
    except ValueError:
        pass
    else:
        raise AssertionError("public row entered dictionary quarantine")
    with tempfile.TemporaryDirectory(prefix="p106b_krdict_quarantine_") as temporary:
        root = Path(temporary)
        target = root / "HF" / "sft_ready" / "quarantine" / "candidates"
        with (patch.dict(globals(), ROOT=root, QUARANTINE_DIR=target,
                         PUBLIC_JOB_DIR=root / "HF" / "sft_ready" / "public_job_deck")):
            report = write_candidates([row])
            assert report["rows"] == 1 and report["release_status"] == "LOCAL_QUARANTINE_NOT_REVIEWED"
            assert not (root / "HF" / "sft_ready" / "public_job_deck").exists()
            from tinylm.data.sft import load_canonical
            try:
                load_canonical(target / "krdict_candidates_000000.jsonl")
            except ValueError:
                pass
            else:
                raise AssertionError("ordinary SFT loader accepted a quarantined candidate envelope")
            try:
                write_candidates([row])
            except ValueError:
                pass
            else:
                raise AssertionError("quarantine write-once output was overwritten")
    print("[PASS] synthetic KRDict CC BY-SA quarantine is separate/write-once/not training-ready; protected/model NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("library-only rights adapter; no protected source or teacher execution here")
    self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
