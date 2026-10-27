#!/usr/bin/env python3
"""Next-run MTP/verified-reasoning experiments using existing tested SFT engine.

No dates or original namespaces are rewritten. New corpus/metadata are separate.
MTP uses explicit-context QA + existing role replay + public general TRAIN;
reasoning uses code-verified4096 roots, never public benchmark answers.
Unreviewed Luna translations are not silently promoted to training data.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
import copy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
VERSION = "P101A_CLEAN_BILINGUAL_PREPARATION_V3"
TAGS = dict(mtp="p101a_sft_mtp_cleanbilingual_v3_s1337",
            direct="p101a_sft_mtp_verified_direct_v3_s1337",
            trace="p101a_sft_mtp_verified_trace_v3_s1337")
NATURAL = ROOT / "HF/sft_ready/p106b_night_grounded_v1_s1337/corpus"
COURSE = ROOT / "data_cache/p106b_broad_curriculum_v2_s1337/course.json"
PUBLIC = ROOT / "HF/sft_ready/p090_public_v3_train.canonical.jsonl"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""): h.update(block)
    return h.hexdigest().upper()


def masked_record(row, tok):
    """Respect explicit corrected-turn supervision, also in MTP horizons."""
    from tinylm.train import mtp_sft as core
    record = core.encode_record(row, tok, context=1024)
    allowed = row.get("meta", {}).get("supervised_assistant_turns")
    if allowed is None: return record
    if not allowed or any(type(v) is not int or v <= 0 for v in allowed):
        raise ValueError("positive explicit assistant turn allowlist required")
    y = [v if owner in allowed else -100 for v, owner in zip(record.y, record.segments)]
    owners = [owner if target != -100 else 0 for owner, target in zip(record.segments, y)]
    result = core.Record(record.x, y, owners)
    if not result.targets: raise ValueError("zero supervised targets")
    return result


def rows_for(family):
    from scripts.p106b_shards import verify
    if family in ("direct", "trace"):
        from scripts.p106b_verified_trace_data import build_course
        course = build_course()
        return {"train": course["train"][family], "val": course["dev"][family],
                "test": course["test"][family]}, dict(producer="p106b_verified_trace_data.build_course",
                  report=course["report"], quality="CODE_CHECKED_RULES_NOT_GENERAL_INTELLIGENCE")
    report = json.loads((NATURAL / "report.json").read_text())
    selected = json.loads(COURSE.read_text())["general_admission"]["selected_source_indices"]
    train, val = [], []
    def stream(stem):
        manifest = report["manifests"][stem]; verify(NATURAL, manifest)
        for shard in manifest["shards"]:
            with (NATURAL / shard["path"]).open(encoding="utf-8") as source:
                for line in source: yield json.loads(line)
    for pair in stream("train"):
        train.extend(pair["views"][v] for v in ("0", "1"))
    for pair in stream("dev"): val.append(pair["views"]["2"])
    train.extend(stream("replay"))
    wanted = set(selected)
    with PUBLIC.open(encoding="utf-8") as source:
        for i, line in enumerate(source):
            if i in wanted: train.append(json.loads(line))
    if len(train) != 22528 or len(val) != 512:
        raise ValueError("fixed complete22528TRAIN/512DEV source required")
    return {"train": train, "val": val}, dict(producer="exact public train selection plus explicit-context QA/replay",
        course_sha256=digest(COURSE), natural_report_sha256=digest(NATURAL / "report.json"),
        public_train_sha256=digest(PUBLIC), old_contextless_teacher4473_rows=0,
        luna_drafts_admitted=0, official_eval_gold_inputs=0,
        official_train_annotation_gold_inputs="KorQuAD/SQuAD TRAIN annotations are supervised targets",
        benchmark_contamination="WHOLE_PRETRAINING_AND_PARAPHRASE_OVERLAP_NOT_AUDITED",
        quality="SOURCE_ANNOTATION_NOT_FULL_SEMANTIC_REVIEW")


def prepare(family):
    from tokenizers import Tokenizer
    from scripts import diag_p101a_sft_mtp as engine
    from scripts.p106b_shards import ShardWriter, verify
    from tinylm.chat.canonical import normalize, validate
    from tinylm.train import mtp_sft as core
    from scripts.p106b_source_cleanup import safe
    corpus, evidence = engine.paths(TAGS[family]); safe(corpus); safe(evidence)
    if corpus.exists(): raise FileExistsError("write-once new corpus exists")
    if digest(engine.data.TOKENIZER) != engine.data.TOK_SHA: raise ValueError("tokenizer changed")
    tok = Tokenizer.from_file(str(engine.data.TOKENIZER)); datasets, sources = rows_for(family)
    corpus.mkdir(parents=True, exist_ok=False)
    manifests, counts, language = {}, {}, {}
    for split, rows in datasets.items():
        writer = ShardWriter(corpus, split, limit=19_999_999); total = Counter(); langs = Counter()
        for row in rows:
            row = validate(normalize(copy.deepcopy(row)))
            record = masked_record(row, tok)
            total.update(x_tokens=record.x_tokens, assistant_targets=record.targets, rows=1)
            langs[row.get("meta", {}).get("language", "UNKNOWN")] += 1
            writer.append(row)
        if not writer._total_rows: raise ValueError("zero-row split is not prepared")
        manifests[split] = writer.close(lineage=dict(family=family, source=sources)); verify(corpus, manifests[split])
        counts[split], language[split] = dict(total), dict(langs)
    report = dict(schema=engine.data.VERSION, preparation_schema=VERSION, status="CORPUS_READY", family=family,
        tag=TAGS[family], tokenizer_sha256=engine.data.TOK_SHA, epochs=4, manifests=manifests,
        actual_unique_train_x_tokens=counts["train"]["x_tokens"],
        target_processed_x_tokens=4 * counts["train"]["x_tokens"], counts=counts, language_rows=language,
        sources=sources, supervised_wrong_turns="EXCLUDED_BY_EXPLICIT_ALLOWLIST",
        code_sha256={"scripts/diag_p101a_clean_bilingual.py": digest(__file__)},
        generic_engine_schema_reused=True, original_frozen8m_changed=False,
        semantic_quality="CODE_CHECKED_ONLY" if family != "mtp" else "SOURCE_ANNOTATION_NOT_FULL_REVIEW",
        formal_train_ready=False, public_benchmark_contamination="NOT_AUDITED_ALL_PRETRAINING",
        learning_updates=4 * ((counts["train"]["rows"] + 127) // 128))
    engine.write(corpus / "report.json", report)
    print("[NEW_CORPUS] " + json.dumps({k: report[k] for k in ("family", "counts", "language_rows", "learning_updates", "formal_train_ready")}, ensure_ascii=False))
    return report


def encoded(corpus, report, tok):
    from scripts.p101a_sft_mtp_data import stream_rows
    return {split: [masked_record(row, tok) for row in stream_rows(corpus, report["manifests"][split])]
            for split in ("train", "val")}


def optimizers(model):
    from scripts import diag_p101a_sft_mtp as engine
    # Invoke the saved original factory, never recursively call a patched name.
    adam, muon = ORIGINAL_OPTIMIZERS(model)
    for group in adam.param_groups: group["lr"] = 5e-5
    for group in muon.param_groups: group["lr"] = 2e-4
    return adam, muon


ORIGINAL_OPTIMIZERS = None


def info(args, report=None):
    from scripts import diag_p101a_sft_mtp as engine
    value = engine.info(args)
    value.update(preparation_schema=VERSION, family=args.family, lr=5e-5, muon_lr=2e-4,
        unique_train_x_target=report["actual_unique_train_x_tokens"] if report else None,
        processed_x_target_approx=report["target_processed_x_tokens"] if report else None,
        independent_variable="auxiliary MTP objective" if args.family == "mtp" else "verified short trace vs direct answer",
        source_scope="explicit-context public TRAIN; not final benchmark correction",
        train_wrong_assistant=False, unreviewed_luna_admitted=False)
    value["code_sha256"].update({"scripts/diag_p101a_clean_bilingual.py": digest(__file__),
                                  "scripts/test_p101a_clean_bilingual.py": digest(ROOT / "scripts/test_p101a_clean_bilingual.py")})
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=tuple(TAGS), required=True)
    parser.add_argument("--mode", choices=("prepare", "calibrate", "train", "compare", "infer"), required=True)
    parser.add_argument("--arm", choices=("scratch_ntp", "scratch_mtp", "parent_ntp", "parent_mtp"), default="parent_ntp")
    parser.add_argument("--max-wall-sec", type=int, default=14400)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execute", action="store_true"); group.add_argument("--check-only", action="store_true")
    args = parser.parse_args(); args.tag = TAGS[args.family]
    if not 60 <= args.max_wall_sec <= 21600: parser.error("window60..21600 required")
    if args.family != "mtp" and args.arm != "parent_ntp": parser.error("reasoning pair uses the same parent/NTP-only")
    if args.family != "mtp" and args.mode in ("infer", "compare"): parser.error("use matched direct/trace reports; no four-arm MTP compare")
    from scripts import diag_p101a_sft_mtp as engine
    corpus, evidence = engine.paths(args.tag)
    if args.check_only:
        print("[CHECK_ONLY] " + json.dumps(info(args), ensure_ascii=False)); return 0
    if args.mode == "prepare": prepare(args.family); return 0
    report = engine.corpus_report(corpus)
    if report.get("preparation_schema") != VERSION or report.get("code_sha256", {}).get("scripts/diag_p101a_clean_bilingual.py") != digest(__file__):
        raise ValueError("same new controller/corpus required")
    metadata = info(args, report)
    if args.mode == "compare": return engine.compare(args, evidence)
    if args.mode == "infer":
        from scripts.p101a_sft_mtp_infer import run
        return run(args, corpus, evidence, metadata)
    global ORIGINAL_OPTIMIZERS
    ORIGINAL_OPTIMIZERS = engine.optimizers
    with patch.object(engine, "encoded", encoded), patch.object(engine, "optimizers", optimizers):
        return engine.train_arm(args, corpus, evidence, metadata, calibrate=args.mode == "calibrate")


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (FileNotFoundError, FileExistsError) as exc:
        print("[HOLD] " + str(exc)); raise SystemExit(8)
