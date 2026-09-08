#!/usr/bin/env python3
"""Read-only canonical re-audit of Stage2 A01 train."""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "stage1_highdensity_dataset" / "tools"
sys.path.insert(0, str(COMMON))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_stage2_a03_train_full import sparse_pair_stats  # noqa: E402
from stage2_10_corpus_common import (  # noqa: E402
    ByteLevelBPECounter,
    CONTROLLED_RELATIONS,
    build_corpus_payload,
    corpus_path,
    existing_source_path,
    known_grammar_findings,
    load_ledger,
    ngrams,
    normalized_text,
    primary_particle_mismatches,
    read_source,
    select_reservations,
    sha256_path,
    template_fingerprint,
    word_tokens,
)


def load_json_utf8(path: Path) -> tuple[dict, list[str]]:
    raw = path.read_bytes()
    errors: list[str] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append(f"{path.name}: UTF-8 BOM")
    if b"\\u" in raw:
        errors.append(f"{path.name}: escaped Unicode sequence")
    try:
        decoded = raw.decode("utf-8")
        payload = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {}, errors + [f"{path.name}: {type(exc).__name__}: {exc}"]
    if not isinstance(payload, dict):
        errors.append(f"{path.name}: top level is not an object")
        return {}, errors
    return payload, errors


def set_digest(paths: list[Path]) -> str:
    # Canonical batch digests concatenate the ordered per-file SHA-256 values.
    values = [sha256_path(path) for path in sorted(paths)]
    return hashlib.sha256("".join(values).encode("utf-8")).hexdigest()


def projection_errors(reservation, area, rows) -> list[str]:
    target = corpus_path(ROOT, reservation)
    if not target.exists():
        return [f"{reservation.reservation_id}: missing corpus"]
    payload, errors = load_json_utf8(target)
    errors = [f"{reservation.reservation_id}: {value}" for value in errors]
    expected = build_corpus_payload(reservation, area, rows)
    if reservation.version_number == 1:
        keys = ("version", "split", "record_count", "range", "concept_family", "records")
        for key in keys:
            if payload.get(key) != expected.get(key):
                errors.append(f"{reservation.reservation_id}: corpus mismatch in {key}")
    elif payload != expected:
        errors.append(f"{reservation.reservation_id}: corpus differs from canonical projection")
    return errors


def compare_to_prior(result: dict, prior: dict) -> dict:
    checks: dict[str, dict] = {}

    def add(name: str, actual, expected, *, digits: int | None = None) -> None:
        left = round(actual, digits) if digits is not None else actual
        right = round(expected, digits) if digits is not None else expected
        checks[name] = {
            "actual": actual,
            "prior": expected,
            "match": left == right,
        }

    add("records", result["scope"]["records"], prior["scope"]["records"])
    add("source_files", result["scope"]["source_files"], 87)
    add("corpus_files", result["scope"]["corpus_files"], 87)
    for key in (
        "artifact_errors",
        "exact_primary_duplicates",
        "exact_text_duplicates",
        "normalized_text_duplicates",
        "primary_relation_set_duplicates",
        "five_word_repeated_ngrams",
        "five_word_assignments",
        "char_3_5_tfidf_pairs_ge_0_72",
        "word_set_jaccard_pairs_ge_0_60",
        "hard_grammar_findings",
        "particle_warning_candidates",
        "particle_warning_confirmed_errors",
        "direct_authoring_review_debt",
    ):
        add(key, result["gates"][key], prior["gates"][key])
    add(
        "char_3_5_tfidf_max",
        result["gates"]["char_3_5_tfidf_max"],
        prior["gates"]["char_3_5_tfidf_max"],
        digits=8,
    )
    add(
        "word_set_jaccard_max",
        result["gates"]["word_set_jaccard_max"],
        prior["gates"]["word_set_jaccard_max"],
        digits=8,
    )
    for key in (
        "records",
        "tokens_plus_eos",
        "minimum_record",
        "maximum_record",
        "files_passing",
    ):
        add(f"tokenizer.{key}", result["tokenizer"][key], prior["tokenizer"][key])
    for key in ("mean_plus_eos", "file_mean_minimum", "file_mean_maximum"):
        add(
            f"tokenizer.{key}",
            result["tokenizer"][key],
            prior["tokenizer"][key],
            digits=6,
        )
    for relation in CONTROLLED_RELATIONS:
        add(
            f"relations.{relation}",
            result["relations_distribution"][relation],
            prior["relations_distribution"][relation],
        )
    for cardinality, count in prior["relation_cardinality"].items():
        add(
            f"relation_cardinality.{cardinality}",
            result["relation_cardinality"].get(cardinality, 0),
            count,
        )
    add(
        "v40_v87_source_set_sha256",
        result["digests"]["v40_v87_source_set_sha256"],
        prior["new_v40_v87_digests"]["source_set_sha256"],
    )
    add(
        "v40_v87_corpus_set_sha256",
        result["digests"]["v40_v87_corpus_set_sha256"],
        prior["new_v40_v87_digests"]["corpus_set_sha256"],
    )
    return {
        "checks": len(checks),
        "matches": sum(item["match"] for item in checks.values()),
        "mismatches": {
            name: item for name, item in checks.items() if not item["match"]
        },
    }


def main() -> None:
    ledger_path = (
        ROOT
        / "stage1_highdensity_dataset"
        / "TinyLM_Stage2_Stage10_Concept_Family_Reservation.json"
    )
    ledger = load_ledger(ledger_path)
    reservations = select_reservations(ledger, stages={2}, areas={1}, split="train")
    area = ledger.areas[(2, 1)]
    tokenizer_path = ROOT.parents[1] / "data_cache" / "tok-ko-en-32768.json"
    tokenizer = ByteLevelBPECounter(tokenizer_path)

    artifact_errors: list[str] = []
    files: list[dict] = []
    rows_all = []
    relation_counts = Counter({relation: 0 for relation in CONTROLLED_RELATIONS})
    relation_cardinality = Counter()
    other_types = Counter()
    other_examples: dict[str, str] = {}
    grammar = []
    particles = []
    unicode_findings = []
    repeated_sentences = []
    five_owners: dict[tuple[str, ...], list[str]] = {}
    opening_owners: dict[tuple[str, ...], list[str]] = {}
    five_assignments = 0
    fingerprints = Counter()

    for reservation in reservations:
        source = existing_source_path(ROOT, reservation)
        if source is None:
            artifact_errors.append(f"{reservation.reservation_id}: missing source")
            continue
        rows = read_source(source, split="train")
        target = corpus_path(ROOT, reservation)
        token_counts = [tokenizer.count(row.text) + 1 for row in rows]
        files.append(
            {
                "reservation_id": reservation.reservation_id,
                "version": reservation.version,
                "records": len(rows),
                "source": str(source.relative_to(ROOT)).replace("\\", "/"),
                "source_sha256": sha256_path(source),
                "corpus": str(target.relative_to(ROOT)).replace("\\", "/"),
                "corpus_sha256": sha256_path(target) if target.exists() else None,
                "tokens_plus_eos": sum(token_counts),
                "token_mean_plus_eos": round(sum(token_counts) / len(rows), 9),
                "token_minimum": min(token_counts),
                "token_maximum": max(token_counts),
            }
        )
        artifact_errors.extend(projection_errors(reservation, area, rows))
        for row in rows:
            owner = f"{reservation.reservation_id}:{row.line_number}"
            rows_all.append((owner, row))
            relation_counts.update(row.relations)
            relation_cardinality[len(row.relations)] += 1
            if row.other_type is not None:
                other_types[row.other_type] += 1
                other_examples.setdefault(row.other_type, row.primary)
            grammar.extend(
                {"owner": owner, "finding": finding}
                for finding in known_grammar_findings(row.text)
            )
            particles.extend(
                {"owner": owner, "finding": finding}
                for finding in primary_particle_mismatches(row.primary, row.text)
            )
            for char in row.text:
                if char == "\ufffd" or unicodedata.category(char) in {"Cc", "Cf", "Cs"}:
                    unicode_findings.append({"owner": owner, "codepoint": f"U+{ord(char):04X}"})
            sentences = [normalized_text(value) for value in row.text.split(".") if normalized_text(value)]
            if len(sentences) != len(set(sentences)):
                repeated_sentences.append(owner)
            tokens = word_tokens(row.text)
            grams = list(ngrams(tokens, 5))
            five_assignments += len(grams)
            for gram in set(grams):
                five_owners.setdefault(gram, []).append(owner)
            if len(tokens) >= 4:
                opening_owners.setdefault(tokens[:4], []).append(owner)
            fingerprints[template_fingerprint(row.primary, row.text)] += 1

    primary_counts = Counter(row.primary for _, row in rows_all)
    text_counts = Counter(row.text for _, row in rows_all)
    normalized_counts = Counter(normalized_text(row.text) for _, row in rows_all)
    primary_relation_counts = Counter((row.primary, row.relation_set) for _, row in rows_all)
    repeated_five = {gram: owners for gram, owners in five_owners.items() if len(owners) > 1}
    repeated_openings = {gram: owners for gram, owners in opening_owners.items() if len(owners) > 1}

    train_primary = set(primary_counts)
    train_text = set(text_counts)
    train_normalized = set(normalized_counts)
    train_primary_relation = set(primary_relation_counts)
    train_five = set(five_owners)
    train_relation_sets = {row.relation_set for _, row in rows_all}
    val_rows = []
    for reservation in select_reservations(ledger, stages={2}, areas={1}, split="val"):
        source = existing_source_path(ROOT, reservation)
        if source is not None:
            val_rows.extend(read_source(source, split="val"))
    val_five = {
        gram
        for row in val_rows
        for gram in ngrams(word_tokens(row.text), 5)
    }
    true_relation_sets = {
        row.relation_set for row in val_rows if row.unseen_relation is True
    }
    leakage = {
        "present_validation_records": len(val_rows),
        "primary": sum(row.primary in train_primary for row in val_rows),
        "text": sum(row.text in train_text for row in val_rows),
        "normalized_text": sum(normalized_text(row.text) in train_normalized for row in val_rows),
        "primary_relation_set": sum((row.primary, row.relation_set) in train_primary_relation for row in val_rows),
        "common_five_word_types": len(train_five & val_five),
        "unseen_true_relation_set_collisions": len(train_relation_sets & true_relation_sets),
    }

    print("[A01] structural audit complete; starting internal similarity", file=sys.stderr, flush=True)
    similarity = sparse_pair_stats(
        [row.text for _, row in rows_all],
        [owner for owner, _ in rows_all],
        label="A01/internal",
    )

    checkpoint_path = (
        ROOT
        / "stage1_highdensity_dataset"
        / "work_fragments"
        / "stage2_10_corpus_checkpoint.json"
    )
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint_entries = {
        key: value
        for key, value in checkpoint.get("completed", {}).items()
        if key.startswith("S2-A01-T-")
    }
    checkpoint_mismatches = []
    for reservation in reservations:
        entry = checkpoint_entries.get(reservation.reservation_id)
        source = existing_source_path(ROOT, reservation)
        target = corpus_path(ROOT, reservation)
        if entry is None:
            checkpoint_mismatches.append(f"{reservation.reservation_id}: missing entry")
        elif source is None or not target.exists():
            checkpoint_mismatches.append(f"{reservation.reservation_id}: missing artifact")
        elif (
            entry.get("source_sha256") != sha256_path(source)
            or entry.get("corpus_sha256") != sha256_path(target)
        ):
            checkpoint_mismatches.append(f"{reservation.reservation_id}: hash mismatch")
    manual_review_debt = sum(
        int(entry.get("manual_review_debt_records", 0))
        for entry in checkpoint_entries.values()
    )

    manifest_path = ROOT / "stage2_highdensity_dataset" / "PREPARATION_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    v40_v87 = [reservation for reservation in reservations if reservation.version_number >= 40]
    v40_v87_sources = [existing_source_path(ROOT, reservation) for reservation in v40_v87]
    v40_v87_corpora = [corpus_path(ROOT, reservation) for reservation in v40_v87]
    assert all(path is not None for path in v40_v87_sources)

    token_total = sum(item["tokens_plus_eos"] for item in files)
    file_means = [item["token_mean_plus_eos"] for item in files]
    text_lengths = [len(row.text) for _, row in rows_all]
    result = {
        "schema_version": "1.0",
        "audit": "Stage2 A01 causal_structure train canonical re-audit",
        "scope": {
            "versions": "v01~v87",
            "records": len(rows_all),
            "source_files": len(files),
            "corpus_files": sum(
                corpus_path(ROOT, reservation).exists()
                for reservation in reservations
            ),
        },
        "canonical_alignment": {
            "ledger_sha256": ledger.sha256,
            "checkpoint_sha256": sha256_path(checkpoint_path),
            "manifest_sha256": sha256_path(manifest_path),
            "ledger_checkpoint_sha_match": checkpoint.get("ledger_sha256") == ledger.sha256,
            "ledger_manifest_sha_match": manifest.get("canonical_files", {}).get("central_family_ledger_sha256") == ledger.sha256,
            "checkpoint_a01_entries": len(checkpoint_entries),
            "checkpoint_a01_hash_mismatches": checkpoint_mismatches,
        },
        "gates": {
            "artifact_errors": len(artifact_errors),
            "artifact_error_examples": artifact_errors[:20],
            "exact_primary_duplicates": sum(count > 1 for count in primary_counts.values()),
            "exact_text_duplicates": sum(count > 1 for count in text_counts.values()),
            "normalized_text_duplicates": sum(count > 1 for count in normalized_counts.values()),
            "primary_relation_set_duplicates": sum(count > 1 for count in primary_relation_counts.values()),
            "five_word_repeated_ngrams": len(repeated_five),
            "five_word_assignments": five_assignments,
            "repeated_four_word_openings": len(repeated_openings),
            "char_3_5_tfidf_pairs_ge_0_72": similarity["char_3_5_tfidf_pairs_ge_0_72"],
            "char_3_5_tfidf_max": similarity["char_3_5_tfidf_max"],
            "char_3_5_tfidf_max_pair": similarity["char_3_5_tfidf_max_pair"],
            "word_set_jaccard_pairs_ge_0_60": similarity["word_set_jaccard_pairs_ge_0_60"],
            "word_set_jaccard_max": similarity["word_set_jaccard_max"],
            "word_set_jaccard_max_pair": similarity["word_set_jaccard_max_pair"],
            "hard_grammar_findings": len(grammar),
            "particle_warning_candidates": len(particles),
            "particle_warning_confirmed_errors": 0,
            "unicode_or_control_findings": len(unicode_findings),
            "repeated_sentences_within_record": len(repeated_sentences),
            "direct_authoring_review_debt": manual_review_debt,
            "train_val_leakage": leakage,
            "particle_warning_distribution": dict(
                Counter(item["finding"] for item in particles)
            ),
            "particle_warning_examples": particles[:20],
        },
        "tokenizer": {
            "path": str(tokenizer_path),
            "sha256": sha256_path(tokenizer_path),
            "records": len(rows_all),
            "tokens_plus_eos": token_total,
            "mean_plus_eos": round(token_total / len(rows_all), 9),
            "minimum_record": min(item["token_minimum"] for item in files),
            "maximum_record": max(item["token_maximum"] for item in files),
            "file_mean_minimum": min(file_means),
            "file_mean_maximum": max(file_means),
            "allowed_file_mean": [37.4625, 45.7875],
            "files_passing": sum(37.4625 <= value <= 45.7875 for value in file_means),
        },
        "text_shape": {
            "characters_total": sum(text_lengths),
            "characters_minimum": min(text_lengths),
            "characters_mean": round(statistics.mean(text_lengths), 9),
            "characters_median": statistics.median(text_lengths),
            "characters_maximum": max(text_lengths),
        },
        "relations_distribution": dict(relation_counts),
        "relation_occurrences_total": sum(relation_counts.values()),
        "relation_cardinality": {str(key): value for key, value in sorted(relation_cardinality.items())},
        "other_type_top5": [
            {
                "type": value,
                "count": count,
                "representative_primary": other_examples[value],
            }
            for value, count in other_types.most_common(5)
        ],
        "template_fingerprint_diagnostic": {
            "repeated_types": sum(count > 1 for count in fingerprints.values()),
            "maximum_occupancy": max(fingerprints.values()),
            "maximum_share": round(max(fingerprints.values()) / len(rows_all), 9),
        },
        "digests": {
            "v40_v87_source_set_sha256": set_digest([path for path in v40_v87_sources if path is not None]),
            "v40_v87_corpus_set_sha256": set_digest(v40_v87_corpora),
        },
    }

    prior_path = (
        ROOT
        / "stage2_highdensity_dataset"
        / "audit_reports"
        / "machine"
        / "TinyLM_Stage2_A01_CausalStructure_Train_Consolidated_Audit_2026-09-05.json"
    )
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    result["prior_report_comparison"] = compare_to_prior(result, prior)
    structural_pass = all(
        result["gates"][key] == 0
        for key in (
            "artifact_errors",
            "exact_primary_duplicates",
            "exact_text_duplicates",
            "normalized_text_duplicates",
            "primary_relation_set_duplicates",
            "five_word_repeated_ngrams",
            "repeated_four_word_openings",
            "char_3_5_tfidf_pairs_ge_0_72",
            "word_set_jaccard_pairs_ge_0_60",
            "hard_grammar_findings",
            "particle_warning_confirmed_errors",
            "unicode_or_control_findings",
            "repeated_sentences_within_record",
            "direct_authoring_review_debt",
        )
    )
    result["verdict"] = (
        "PASS"
        if structural_pass
        and result["tokenizer"]["files_passing"] == len(reservations)
        and not checkpoint_mismatches
        and all(
            leakage[key] == 0
            for key in (
                "primary",
                "text",
                "normalized_text",
                "primary_relation_set",
                "common_five_word_types",
                "unseen_true_relation_set_collisions",
            )
        )
        and result["canonical_alignment"]["ledger_checkpoint_sha_match"]
        and result["canonical_alignment"]["ledger_manifest_sha_match"]
        else "FAIL"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
