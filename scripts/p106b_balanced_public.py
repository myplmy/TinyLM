#!/usr/bin/env python3
"""User-run, order-independent public C selection; source token caps, no models.

Scan every eligible source row before selecting. Store only source locators and
counts in a disk index; reconstruct selected content in a second pass. Original
HF inputs are read-only. A new version stores <=20MB canonical shards and an
honest language shortfall, without repeating data to manufacture a token target.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_mixed_scale import (TOK_SHA, TOKENIZER, GOAL, Selector, digest,
    source_specs, rows_for, safe_repo_path, COLLECTION_EXCLUDED)
from scripts.p106b_shards import ShardWriter, verify
from tinylm.chat.canonical import normalize

OUTPUT = ROOT / "HF/sft_ready/p106b_mixed_public_v2_balanced"


def family_bucket(family):
    if family.startswith("aya:") or family == "Aya-Dataset":
        return "aya_dataset"
    if family in {"oasst1", "oasst2"}:
        return "openassistant"
    # Translated and original/template variants do not evade a source cap.
    return family.removesuffix(" (T)")


def initialize_index(connection):
    connection.execute("CREATE TABLE candidates (prompt TEXT PRIMARY KEY, rank TEXT NOT NULL, "
                       "choice TEXT NOT NULL, source INTEGER NOT NULL, ordinal INTEGER NOT NULL, "
                       "split TEXT NOT NULL, language TEXT NOT NULL, family TEXT NOT NULL, "
                       "tokens INTEGER NOT NULL, targets INTEGER NOT NULL, selected INTEGER NOT NULL DEFAULT 0)")


def index_row(connection, row, source, ordinal):
    meta = row["meta"]
    prompt = meta["parent_concept_id"]
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    choice = hashlib.sha256(payload.encode()).hexdigest()
    rank = hashlib.sha256(("P106B_C_BALANCED_V1:" + prompt).encode()).hexdigest()
    connection.execute("INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?,?,?,0) "
                       "ON CONFLICT(prompt) DO UPDATE SET choice=excluded.choice,source=excluded.source,"
                       "ordinal=excluded.ordinal,split=excluded.split,language=excluded.language,"
                       "family=excluded.family,tokens=excluded.tokens,targets=excluded.targets "
                       "WHERE excluded.choice<candidates.choice",
                       (prompt, rank, choice, source, ordinal, meta["source_split"], meta["language"],
                        family_bucket(meta["source_family"]), meta["processed_x_tokens"], meta["assistant_targets"]))


def select_index(connection, goal=GOAL):
    connection.execute("CREATE INDEX rank_order ON candidates(rank,prompt)")
    tokens, targets, rows, family_tokens, rejected = Counter(), Counter(), Counter(), Counter(), Counter()
    for prompt, split, language, family, size, supervised in connection.execute(
            "SELECT prompt,split,language,family,tokens,targets FROM candidates ORDER BY rank,prompt"):
        quota = goal if split == "train" else max(1, goal // 19)
        key, family_key = split + ":" + language, split + ":" + language + ":" + family
        cap = max(1, quota // 4)
        if tokens[key] >= quota:
            rejected["language_quota_filled"] += 1
            continue
        if family_tokens[family_key] + size > cap:
            rejected["source_token_cap"] += 1
            continue
        connection.execute("UPDATE candidates SET selected=1 WHERE prompt=?", (prompt,))
        tokens[key] += size
        targets[key] += supervised
        rows[key] += 1
        family_tokens[family_key] += size
    connection.commit()
    actual_shares = {k: value / tokens[":".join(k.split(":")[:2])]
                     for k, value in family_tokens.items()}
    return {"rows": dict(rows), "nonpadding_tokens": dict(tokens), "assistant_targets": dict(targets),
            "family_tokens": dict(family_tokens), "selection_rejected": dict(rejected),
            "actual_selected_family_shares": actual_shares,
            "partial_source_balance_warning": any(v > .25 for v in actual_shares.values()),
            "teacher_deficit_tokens": {lang: max(0, goal - tokens["train:" + lang]) for lang in ("ko", "en")},
            "token_target_ready": all(tokens["train:" + lang] >= goal for lang in ("ko", "en")),
            "cap_basis": "25 percent of target tokens per language/split; partial shortfall can exceed25 percent of actual selected tokens, reported separately",
            "source_cap_tokens_train": goal // 4, "unique_prompt_groups": connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]}


def check():
    for path in (OUTPUT, TOKENIZER):
        safe_repo_path(path)
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError("preserve balanced output; new retry needs a new version")
    if digest(TOKENIZER) != TOK_SHA:
        raise ValueError("tokenizer identity differs")
    specs = sorted(source_specs(), key=lambda s: (s["path"], s["sha256"]))
    if shutil.disk_usage(ROOT / "HF/sft_ready").free < 8 * 2**30:
        raise ValueError("need8GiB free for source index and new output shards")
    return specs


def execute(specs):
    from tokenizers import Tokenizer
    from scripts.p106b_education_followup import PROBES
    from tinylm.data.sft import conversation_split_key
    began = time.perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    con = sqlite3.connect(OUTPUT / "candidate_index.sqlite")
    initialize_index(con)
    tok = Tokenizer.from_file(str(TOKENIZER))
    probes = [conversation_split_key(normalize({"messages": [{"role": "user", "content": q},
              {"role": "assistant", "content": "probe"}]})) for _, q in PROBES]
    validation = Selector(tok, goal=2**60, probe_keys=probes)
    census = Counter()
    try:
        for source, spec in enumerate(specs):
            for ordinal, row in enumerate(rows_for(spec)):
                census["candidate_rows"] += 1
                validation.seen.clear()  # SQLite chooses duplicates independently of arrival order.
                item = validation.consider(row)
                if item:
                    index_row(con, item[1], source, ordinal)
                    census["technical_rows"] += 1
                if ordinal % 5000 == 0:
                    con.commit()
            print("[SOURCE_CENSUS] " + json.dumps({"family": spec["family"], **census}), flush=True)
        con.commit()
        selected = select_index(con)
        con.execute("CREATE TABLE selected_content (prompt TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        for source, spec in enumerate(specs):
            wanted = {r[0]: r[1:] for r in con.execute(
                "SELECT ordinal,prompt,split,tokens,targets,choice FROM candidates WHERE selected=1 AND source=?", (source,))}
            if not wanted:
                continue
            for ordinal, row in enumerate(rows_for(spec)):
                if ordinal not in wanted:
                    continue
                prompt_key, split, size, targets, choice = wanted.pop(ordinal)
                row["meta"].update(source_split=split, parent_concept_id=prompt_key,
                                   processed_x_tokens=size, assistant_targets=targets)
                payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                if hashlib.sha256(payload.encode()).hexdigest() != choice:
                    raise ValueError("source row changed between index and reconstruction")
                row["meta"]["selection_family"] = family_bucket(row["meta"]["source_family"])
                con.execute("INSERT INTO selected_content VALUES (?,?)", (prompt_key, json.dumps(row, ensure_ascii=False)))
                if len(wanted) % 5000 == 0:
                    con.commit()
            if wanted:
                raise ValueError("selected source locator missing in second pass")
        con.commit()
        writers = {s: ShardWriter(OUTPUT, s) for s in ("train", "val")}
        for split, payload in con.execute("SELECT c.split,s.payload FROM candidates c JOIN selected_content s USING(prompt) ORDER BY c.rank,c.prompt"):
            writers[split].append(json.loads(payload))
        report = {"schema": "P106B_MIXED_PUBLIC_C_V1", "selection_version": "HASH_SOURCE_CAP_V2",
                  "status": "PUBLIC_C_TOKEN_TARGET_READY" if selected["token_target_ready"] else "PUBLIC_C_PREPARED_WITH_DEFICIT",
                  "sources": specs, "tokenizer_sha256": TOK_SHA, "goal_train_tokens_per_language": GOAL,
                  "student_micro": 8, "student_accum": 16, "checkpoint_on": True, "epochs": 4,
                  "target_processed_tokens": 300_000_000, "split": "normalized first user hash modulo20",
                  "selection": "global prompt hash rank; content-SHA tie break; source caps before admission",
                  "excluded_source_families": sorted(COLLECTION_EXCLUDED), "technical_rejections": dict(validation.rejections),
                  "census": dict(census), **selected, "whole_wall_sec": time.perf_counter() - began,
                  "formal_train_ready": False, "semantic_quality": "NOT_REVIEWED",
                  "broad_benchmark_contamination": "NOT_RUN", "student_training": "NOT_RUN"}
        for split, writer in writers.items():
            if writer._total_rows:
                spec = writer.close(lineage={"sources": specs, "tokenizer_sha256": TOK_SHA, "selection_version": "HASH_SOURCE_CAP_V2"})
                verify(OUTPUT, spec)
                report[split + "_concat_sha256"] = spec["concat_sha256"]
        report["index_bytes"] = (OUTPUT / "candidate_index.sqlite").stat().st_size
        with (OUTPUT / "report.json").open("x", encoding="utf-8") as f:
            f.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print("[BALANCED_PUBLIC_SUMMARY] " + json.dumps(report, ensure_ascii=False), flush=True)
        return 0 if selected["rows"] else 8
    finally:
        con.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check-only", action="store_true")
    g.add_argument("--execute", action="store_true")
    args = p.parse_args()
    specs = check()
    if args.check_only:
        print(json.dumps({"sources": specs, "output": str(OUTPUT.relative_to(ROOT)), "source_cap_fraction": .25,
                          "gpu": "NOT_RUN", "selection": "HASH_SOURCE_CAP_V2"}, ensure_ascii=False))
        return 0
    return execute(specs)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("[INTERRUPTED] new partial index preserved; existing corpora unchanged", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(9)
