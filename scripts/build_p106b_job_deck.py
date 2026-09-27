#!/usr/bin/env python3
"""P106B Stage2eW: bounded local public-v3 bilingual teacher job deck.

Each existing source concept is used at most once per target language. Jobs are
finite and split before teacher generation. They are not teacher answers and
not a 300M corpus. Topic labels are heuristics for coverage audit, never
proof of semantic quality. Output is a new ignored HF version in <=20MB
write-once JSONL shards with exact reconstruction hashes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_shards import ShardWriter, verify  # noqa: E402

READY = ROOT / "HF/sft_ready"
SOURCE_MANIFEST = READY / "p090_public_v3_manifest.json"
SOURCES = {split: READY / f"p090_public_v3_{split}.canonical.jsonl"
           for split in ("train", "val")}
OUTPUT = READY / "p106b_bilingual_v1/jobs"
OUTPUT_MANIFEST = OUTPUT / "job_deck_manifest.json"
TOPIC_RULES = (
    ("math_logic", r"\b(math|calculate|number|equation|logic|proof|reason)\b|수학|논리|계산"),
    ("code", r"\b(code|python|javascript|program|debug|algorithm)\b|코드|프로그래밍"),
    ("format_following", r"\b(email|letter|table|json|format|list|summarize)\b|이메일|형식|표로"),
    ("culture_art", r"\b(movie|film|music|painting|poem|literature|art)\b|영화|음악|시|문학"),
    ("politics_society", r"\b(election|government|law|policy|society|president)\b|정치|사회|대통령"),
    ("game_trpg_meme", r"\b(game|rpg|trpg|dungeon|meme|gaming)\b|게임|밈|주사위"),
    ("daily_dialogue", r"\b(hello|how are you|thank you|feel|conversation)\b|안녕|대화|기분"),
)


def digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(f"source absent or linked: {path}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def plain(message: dict) -> str:
    parts = message.get("content")
    if not isinstance(parts, list) or any(
            not isinstance(part, dict) or part.get("type") != "text"
            or not isinstance(part.get("text"), str) for part in parts):
        raise ValueError("public seed has non-text or invalid content")
    text = "\n".join(part["text"] for part in parts).strip()
    if not text:
        raise ValueError("public seed has empty content")
    return text


def family(question: str) -> str:
    for name, pattern in TOPIC_RULES:
        if re.search(pattern, question, re.I):
            return name
    return "general_knowledge_or_other"


def source_contract() -> dict:
    if SOURCE_MANIFEST.is_symlink() or not SOURCE_MANIFEST.is_file():
        raise FileNotFoundError("public-v3 manifest absent or linked")
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema") != "TINYLM_PUBLIC_SFT_V1":
        raise ValueError("public-v3 manifest schema differs")
    for split, path in SOURCES.items():
        if digest(path) != manifest.get("output_sha256", {}).get(split):
            raise ValueError(f"public-v3 {split} SHA differs")
    return {"public_manifest_sha256": digest(SOURCE_MANIFEST),
            "source_sha256": manifest["output_sha256"],
            "source_card_licenses": {key: value.get("license")
                                     for key, value in manifest.get("sources", {}).items()}}


def jobs_for_row(row: dict, *, split: str) -> list[dict]:
    meta = row.get("meta")
    messages = row.get("messages")
    if not isinstance(meta, dict) or not isinstance(messages, list):
        raise ValueError("public canonical source malformed")
    source_id = meta.get("source_id")
    source_language = meta.get("language")
    if (not isinstance(source_id, str) or not source_id
            or source_language not in {"ko", "en"}
            or not isinstance(meta.get("source_license"), str)):
        raise ValueError("public source id, language or license absent")
    if len(messages) < 2 or len(messages) % 2 or len(messages) > 8:
        raise ValueError("public source turn count outside 1..4 pairs")
    if [m.get("role") for m in messages] != [role for _ in range(len(messages)//2)
                                               for role in ("user", "assistant")]:
        raise ValueError("public source roles do not alternate user/assistant")
    turns = [{"user_text": plain(messages[i]), "assistant_text": plain(messages[i+1])}
             for i in range(0, len(messages), 2)]
    first_question = turns[0]["user_text"]
    if len(turns) == 1:
        targets = ("ko", "en")
    else:
        # A multilingual multi-turn translation needs every prior turn
        # translated consistently. Do not silently mix languages here.
        targets = (source_language,)
    jobs = []
    for target_language in targets:
        task = ("next_turn" if len(turns) > 1 else
                "repair" if target_language == source_language else "translate")
        key = f"{split}:{meta.get('source')}:{source_id}:{target_language}:{task}"
        job_id = hashlib.sha256(key.encode("utf-8")).hexdigest().upper()
        jobs.append({"schema": "P106B_STAGE2EW_TEACHER_JOB_V1",
                     "job_id": job_id, "split": split,
                     "source": meta.get("source"), "source_id": source_id,
                     "source_revision": meta.get("source_revision"),
                     "source_license": meta["source_license"],
                     "source_language": source_language,
                     "target_language": target_language,
                     "family_heuristic": family(first_question),
                     "topic_label_status": "HEURISTIC_UNVERIFIED",
                     "concept_id": f"{meta.get('source')}:{source_id}",
                     "variant_index": 0, "max_variants_for_concept": 1,
                     "task": task, "source_turns": turns,
                     "intentional_history_only": len(turns) > 1,
                     "teacher_truth_status": "PSEUDO_UNVERIFIED"})
    return jobs


def census(*, write: bool) -> dict:
    provenance = source_contract()
    if write and (OUTPUT.is_symlink() or OUTPUT.exists()):
        raise FileExistsError("job deck output already exists; use new version")
    counts: Counter[str] = Counter()
    unique_ids = set()
    writers = ({split: ShardWriter(OUTPUT, split) for split in SOURCES} if write else {})
    for split, path in SOURCES.items():
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line)
                for job in jobs_for_row(row, split=split):
                    if job["job_id"] in unique_ids:
                        raise ValueError("duplicate teacher job id/source")
                    unique_ids.add(job["job_id"])
                    counts[f"{split}:{job['target_language']}"] += 1
                    counts[f"topic:{job['family_heuristic']}"] += 1
                    counts[f"task:{job['task']}"] += 1
                    if write:
                        writers[split].append(job)
    result = {"schema": "P106B_STAGE2EW_JOB_DECK_V1", "source": provenance,
              "jobs": len(unique_ids), "counts": dict(sorted(counts.items())),
              "job_policy": "finite local public-v3 source; one variant per concept+language, no budget-filling seed loop",
              "language_target": "actual student nonpadding tokens must be checked after teacher output; row counts are not 50:50 tokens",
              "topic_limit": "heuristic labels only; missing families require new source plan, not repeated prompts"}
    if write:
        result["splits"] = {}
        for split, writer in writers.items():
            manifest = writer.close(lineage=provenance | {"split": split})
            verify(OUTPUT, manifest)
            result["splits"][split] = {"manifest": writer.manifest_path.relative_to(ROOT).as_posix(),
                                        "rows": manifest["rows"],
                                        "concat_sha256": manifest["concat_sha256"]}
        with OUTPUT_MANIFEST.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def self_test() -> None:
    row = {"meta": {"source": "fixture", "source_id": "x", "language": "en",
                    "source_license": "fixture-only"},
           "messages": [{"role": "user", "content": [{"type": "text", "text": "Write Python code"}]},
                        {"role": "assistant", "content": [{"type": "text", "text": "print(1)"}]}]}
    jobs = jobs_for_row(row, split="train")
    assert len(jobs) == 2 and {job["target_language"] for job in jobs} == {"ko", "en"}
    assert all(job["family_heuristic"] == "code" for job in jobs)
    row["messages"] += row["messages"]
    assert len(jobs_for_row(row, split="train")) == 1
    print("[PASS] finite source/concept schedule, fixed train/val split and bilingual single-turn; model/GPU NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        else:
            print(json.dumps(census(write=args.execute), ensure_ascii=False, sort_keys=True))
            print("[PASS] versioned finite public-v3 job deck" if args.execute
                  else "[CHECK_ONLY] local source census; new job files/model/GPU NOT_RUN")
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"[FAIL] P106B Stage2eW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
