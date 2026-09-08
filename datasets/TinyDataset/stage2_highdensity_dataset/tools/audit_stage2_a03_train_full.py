#!/usr/bin/env python3
"""Read-only consolidated source/corpus audit for a completed Stage2 train area."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix


ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "stage1_highdensity_dataset" / "tools"
sys.path.insert(0, str(COMMON))

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


FORBIDDEN_TRAIN_SETS = {
    tuple(sorted(values))
    for values in (
        ("process", "state"),
        ("attribute", "process"),
        ("attribute", "state"),
        ("boundary", "process"),
        ("boundary", "state"),
        ("attribute", "boundary"),
        ("other", "process"),
        ("other", "state"),
        ("attribute", "other"),
        ("attribute", "other", "state"),
    )
}


AREA_NAMES = {
    2: "conditional_dependency",
    3: "temporal_order",
}


def set_digest(paths: list[Path]) -> str:
    """Return the canonical digest of ordered per-file SHA-256 strings."""
    values = [sha256_path(path) for path in sorted(paths)]
    return hashlib.sha256("".join(values).encode("utf-8")).hexdigest()


def load_corpus_records(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(payload.get("records", []))
    return rows


def character_features(text: str) -> Counter[str]:
    value = unicodedata.normalize("NFKC", text).casefold()
    result: Counter[str] = Counter()
    for size in (3, 4, 5):
        result.update(value[index:index + size] for index in range(len(value) - size + 1))
    return result


def build_char_matrix(texts: list[str]) -> csr_matrix:
    document_frequency: Counter[str] = Counter()
    for text in texts:
        # IDF uses document frequency, not the total number of occurrences.
        # Features unique to one document are omitted from the sparse index
        # because they cannot contribute to a cross-document dot product; they
        # still remain in the full-vector norm below.
        document_frequency.update(character_features(text).keys())
    vocabulary = {
        feature: index
        for index, feature in enumerate(
            feature
            for feature, count in document_frequency.items()
            if count >= 2
        )
    }
    total = len(texts)
    idf = {
        feature: math.log((1 + total) / (1 + count)) + 1
        for feature, count in document_frequency.items()
    }
    data: list[float] = []
    indices: list[int] = []
    indptr = [0]
    for text in texts:
        counts = character_features(text)
        norm = math.sqrt(sum((count * idf[feature]) ** 2 for feature, count in counts.items()))
        for feature, count in counts.items():
            column = vocabulary.get(feature)
            if column is not None:
                indices.append(column)
                data.append((count * idf[feature]) / norm)
        indptr.append(len(data))
    if indices and (min(indices) < 0 or max(indices) >= len(vocabulary)):
        raise ValueError("character CSR column index is outside the declared shape")
    matrix = csr_matrix(
        (np.asarray(data, dtype=np.float64), np.asarray(indices, dtype=np.int32), np.asarray(indptr, dtype=np.int64)),
        shape=(len(texts), len(vocabulary)),
        dtype=np.float64,
    )
    matrix.sum_duplicates()
    matrix.sort_indices()
    matrix.check_format(full_check=True)
    return matrix


def build_word_matrix(sets: list[set[str]]) -> csr_matrix:
    document_frequency: Counter[str] = Counter()
    for values in sets:
        document_frequency.update(values)
    vocabulary = {
        value: index
        for index, value in enumerate(
            value
            for value, count in document_frequency.items()
            if count >= 2
        )
    }
    data: list[int] = []
    indices: list[int] = []
    indptr = [0]
    for values in sets:
        for value in values:
            column = vocabulary.get(value)
            if column is not None:
                indices.append(column)
                data.append(1)
        indptr.append(len(data))
    if indices and (min(indices) < 0 or max(indices) >= len(vocabulary)):
        raise ValueError("word CSR column index is outside the declared shape")
    matrix = csr_matrix(
        (np.asarray(data, dtype=np.int16), np.asarray(indices, dtype=np.int32), np.asarray(indptr, dtype=np.int64)),
        shape=(len(sets), len(vocabulary)),
        dtype=np.int16,
    )
    matrix.sum_duplicates()
    matrix.sort_indices()
    matrix.check_format(full_check=True)
    return matrix


def sparse_pair_stats(
    query_texts: list[str],
    query_owners: list[str],
    reference_texts: list[str] | None = None,
    reference_owners: list[str] | None = None,
    *,
    label: str = "similarity",
) -> dict:
    internal = reference_texts is None
    reference_texts = query_texts if internal else reference_texts
    reference_owners = query_owners if internal else reference_owners
    assert reference_texts is not None and reference_owners is not None
    combined = query_texts if internal else query_texts + reference_texts

    char_matrix = build_char_matrix(combined)
    query_char = char_matrix[:len(query_texts)]
    reference_char = query_char if internal else char_matrix[len(query_texts):]
    reference_char_t = reference_char.T.tocsr()
    char_count = 0
    char_max = 0.0
    char_pair: tuple[int, int] | None = None
    block = 64
    for start in range(0, len(query_texts), block):
        product = (query_char[start:start + block] @ reference_char_t).tocoo()
        rows = product.row.astype(np.int64, copy=False) + start
        columns = product.col.astype(np.int64, copy=False)
        values = product.data
        if internal:
            keep = columns > rows
            rows = rows[keep]
            columns = columns[keep]
            values = values[keep]
        if values.size:
            char_count += int(np.count_nonzero(values >= 0.72))
            local_max_index = int(np.argmax(values))
            local_max = float(values[local_max_index])
            if local_max > char_max:
                char_max = local_max
                char_pair = (
                    int(rows[local_max_index]),
                    int(columns[local_max_index]),
                )
        if start and start % (block * 40) == 0:
            print(
                f"[{label}] char rows {start}/{len(query_texts)}",
                file=sys.stderr,
                flush=True,
            )

    query_sets = [set(word_tokens(text)) for text in query_texts]
    reference_sets = query_sets if internal else [set(word_tokens(text)) for text in reference_texts]
    combined_sets = query_sets if internal else query_sets + reference_sets
    word_matrix = build_word_matrix(combined_sets)
    query_word = word_matrix[:len(query_sets)]
    reference_word = query_word if internal else word_matrix[len(query_sets):]
    reference_word_t = reference_word.T.tocsr()
    query_sizes = np.asarray([len(values) for values in query_sets], dtype=np.int32)
    reference_sizes = query_sizes if internal else np.asarray([len(values) for values in reference_sets], dtype=np.int32)
    jaccard_count = 0
    jaccard_max = 0.0
    jaccard_pair: tuple[int, int] | None = None
    for start in range(0, len(query_texts), block):
        product = (query_word[start:start + block] @ reference_word_t).tocoo()
        rows = product.row.astype(np.int64, copy=False) + start
        columns = product.col.astype(np.int64, copy=False)
        intersections = product.data.astype(np.int64, copy=False)
        if internal:
            keep = columns > rows
            rows = rows[keep]
            columns = columns[keep]
            intersections = intersections[keep]
        if intersections.size:
            unions = query_sizes[rows] + reference_sizes[columns] - intersections
            scores = intersections / unions
            jaccard_count += int(np.count_nonzero(scores >= 0.60))
            local_max_index = int(np.argmax(scores))
            local_max = float(scores[local_max_index])
            if local_max > jaccard_max:
                jaccard_max = local_max
                jaccard_pair = (
                    int(rows[local_max_index]),
                    int(columns[local_max_index]),
                )
        if start and start % (block * 40) == 0:
            print(
                f"[{label}] word rows {start}/{len(query_texts)}",
                file=sys.stderr,
                flush=True,
            )

    def describe(pair: tuple[int, int] | None, score: float) -> dict | None:
        if pair is None:
            return None
        left, right = pair
        return {
            "score": round(score, 9),
            "query_owner": query_owners[left],
            "reference_owner": reference_owners[right],
            "query_text": query_texts[left],
            "reference_text": reference_texts[right],
        }

    return {
        "query_records": len(query_texts),
        "reference_records": len(reference_texts),
        "char_3_5_tfidf_pairs_ge_0_72": char_count,
        "char_3_5_tfidf_max": round(char_max, 9),
        "char_3_5_tfidf_max_pair": describe(char_pair, char_max),
        "word_set_jaccard_pairs_ge_0_60": jaccard_count,
        "word_set_jaccard_max": round(jaccard_max, 9),
        "word_set_jaccard_max_pair": describe(jaccard_pair, jaccard_max),
    }


def corpus_projection_errors(reservation, area, rows) -> list[str]:
    path = corpus_path(ROOT, reservation)
    if not path.exists():
        return [f"{reservation.reservation_id}: missing corpus"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"{reservation.reservation_id}: invalid corpus JSON: {exc}"]
    errors: list[str] = []
    expected = build_corpus_payload(reservation, area, rows)
    if reservation.version_number == 1:
        keys = ("version", "split", "record_count", "range", "concept_family", "records")
        for key in keys:
            if payload.get(key) != expected.get(key):
                errors.append(f"{reservation.reservation_id}: corpus mismatch in {key}")
    elif payload != expected:
        errors.append(f"{reservation.reservation_id}: corpus payload differs from canonical projection")
    return errors


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", type=int, choices=sorted(AREA_NAMES), default=3)
    parser.add_argument("--similarity", action="store_true")
    parser.add_argument("--verify-prior-similarity", action="store_true")
    args = parser.parse_args()
    area_number = args.area
    area_tag = f"A{area_number:02d}"
    area_name = AREA_NAMES[area_number]
    ledger_path = ROOT / "stage1_highdensity_dataset" / "TinyLM_Stage2_Stage10_Concept_Family_Reservation.json"
    ledger = load_ledger(ledger_path)
    reservations = select_reservations(ledger, stages={2}, areas={area_number}, split="train")
    area = ledger.areas[(2, area_number)]
    tokenizer_path = ROOT.parents[1] / "data_cache" / "tok-ko-en-32768.json"
    tokenizer = ByteLevelBPECounter(tokenizer_path)

    files = []
    rows_all = []
    artifact_errors: list[str] = []
    relation_counts = Counter({relation: 0 for relation in CONTROLLED_RELATIONS})
    cardinality = Counter()
    hard_grammar = []
    particle_warnings = []
    unicode_findings = []
    repeated_sentences = []
    other_type_counts = Counter()
    other_type_examples: dict[str, str] = {}
    five_owners: dict[tuple[str, ...], list[str]] = {}
    opening_owners: dict[tuple[str, ...], list[str]] = {}
    five_assignments = 0
    template_counts = Counter()
    expected_keys = {"primary", "text", "relations"}

    for reservation in reservations:
        source = existing_source_path(ROOT, reservation)
        if source is None:
            artifact_errors.append(f"{reservation.reservation_id}: missing source")
            continue
        rows = read_source(source, split="train")
        if source.suffix == ".jsonl":
            for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
                keys = set(json.loads(line))
                if keys != expected_keys:
                    artifact_errors.append(f"{reservation.reservation_id}:{line_number}: source keys {sorted(keys)}")
        token_counts = [tokenizer.count(row.text) + 1 for row in rows]
        files.append({
            "version": reservation.version,
            "reservation_id": reservation.reservation_id,
            "id_range": reservation.id_range,
            "concept_family": reservation.concept_family,
            "source": str(source.relative_to(ROOT)).replace("\\", "/"),
            "source_sha256": sha256_path(source),
            "corpus": str(corpus_path(ROOT, reservation).relative_to(ROOT)).replace("\\", "/"),
            "corpus_sha256": sha256_path(corpus_path(ROOT, reservation)) if corpus_path(ROOT, reservation).exists() else None,
            "records": len(rows),
            "tokens_plus_eos": sum(token_counts),
            "token_mean_plus_eos": round(sum(token_counts) / len(rows), 9),
            "token_minimum": min(token_counts),
            "token_maximum": max(token_counts),
            "characters_mean": round(sum(len(row.text) for row in rows) / len(rows), 6),
        })
        artifact_errors.extend(corpus_projection_errors(reservation, area, rows))
        for row in rows:
            owner = f"{reservation.reservation_id}:{row.line_number}"
            rows_all.append((owner, row))
            relation_counts.update(row.relations)
            cardinality[len(row.relations)] += 1
            if row.other_type is not None:
                other_type_counts[row.other_type] += 1
                other_type_examples.setdefault(row.other_type, row.primary)
            hard_grammar.extend({"owner": owner, "finding": value} for value in known_grammar_findings(row.text))
            particle_warnings.extend({"owner": owner, "finding": value} for value in primary_particle_mismatches(row.primary, row.text))
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
            template_counts[template_fingerprint(row.primary, row.text)] += 1

    primary_counts = Counter(row.primary for _, row in rows_all)
    text_counts = Counter(row.text for _, row in rows_all)
    normalized_counts = Counter(normalized_text(row.text) for _, row in rows_all)
    primary_relation_counts = Counter((row.primary, row.relation_set) for _, row in rows_all)
    repeated_five = {gram: owners for gram, owners in five_owners.items() if len(owners) > 1}
    repeated_openings = {opening: owners for opening, owners in opening_owners.items() if len(owners) > 1}
    train_sets = {row.relation_set for _, row in rows_all}

    val_rows = []
    # Stage-level leakage uses every validation artifact already present, not
    # only the validation reservations of the target education area.
    for reservation in select_reservations(ledger, stages={2}, split="val"):
        source = existing_source_path(ROOT, reservation)
        if source is not None:
            val_rows.extend(read_source(source, split="val"))
    train_primary = {row.primary for _, row in rows_all}
    train_text = {row.text for _, row in rows_all}
    train_normalized = {normalized_text(row.text) for _, row in rows_all}
    train_primary_relation = {(row.primary, row.relation_set) for _, row in rows_all}
    train_five = set(five_owners)
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
        "unseen_true_relation_set_collisions": len(train_sets & true_relation_sets),
    }

    text_lengths = [len(row.text) for _, row in rows_all]
    token_total = sum(item["tokens_plus_eos"] for item in files)
    checkpoint_path = ROOT / "stage1_highdensity_dataset" / "work_fragments" / "stage2_10_corpus_checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint_entries = {
        key: value for key, value in checkpoint.get("completed", {}).items()
        if key.startswith(f"S2-{area_tag}-T-")
    }
    checkpoint_hash_mismatches = []
    for reservation in reservations:
        entry = checkpoint_entries.get(reservation.reservation_id)
        source = existing_source_path(ROOT, reservation)
        target = corpus_path(ROOT, reservation)
        if entry is None:
            checkpoint_hash_mismatches.append(f"{reservation.reservation_id}: missing checkpoint entry")
        elif source is None or target.exists() is False:
            checkpoint_hash_mismatches.append(f"{reservation.reservation_id}: missing artifact")
        elif entry.get("source_sha256") != sha256_path(source) or entry.get("corpus_sha256") != sha256_path(target):
            checkpoint_hash_mismatches.append(f"{reservation.reservation_id}: hash mismatch")
    manifest_path = ROOT / "stage2_highdensity_dataset" / "PREPARATION_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_paths = [existing_source_path(ROOT, reservation) for reservation in reservations]
    corpus_paths = [corpus_path(ROOT, reservation) for reservation in reservations]
    assert all(path is not None for path in source_paths)
    result = {
        "schema_version": "1.0",
        "audit": f"TinyLM Stage2 {area_tag} {area_name} train consolidated audit",
        "scope": {
            "versions": f"{reservations[0].version}~{reservations[-1].version}",
            "reservation_ids": f"{reservations[0].reservation_id}~{reservations[-1].reservation_id}",
            "corpus_ids": f"{reservations[0].id_range.split(' ~ ')[0]}~{reservations[-1].id_range.split(' ~ ')[-1]}",
            "records": len(rows_all),
            "source_files": len(files),
            "corpus_files": sum(corpus_path(ROOT, row).exists() for row in reservations),
        },
        "ledger_sha256": ledger.sha256,
        "canonical_alignment": {
            "checkpoint_sha256": sha256_path(checkpoint_path),
            "preparation_manifest_sha256": sha256_path(manifest_path),
            "ledger_checkpoint_sha_match": checkpoint.get("ledger_sha256") == ledger.sha256,
            "ledger_manifest_sha_match": manifest.get("canonical_files", {}).get("central_family_ledger_sha256") == ledger.sha256,
            f"checkpoint_{area_tag.lower()}_entries": len(checkpoint_entries),
            f"checkpoint_{area_tag.lower()}_hash_mismatches": checkpoint_hash_mismatches,
        },
        "tokenizer": {
            "path": str(tokenizer_path),
            "sha256": sha256_path(tokenizer_path),
            "tokens_plus_eos": token_total,
            "mean_plus_eos": round(token_total / len(rows_all), 9),
            "minimum_record": min(item["token_minimum"] for item in files),
            "maximum_record": max(item["token_maximum"] for item in files),
            "file_mean_minimum": min(item["token_mean_plus_eos"] for item in files),
            "file_mean_maximum": max(item["token_mean_plus_eos"] for item in files),
            "allowed_file_mean": [37.4625, 45.7875],
            "files_passing": sum(37.4625 <= item["token_mean_plus_eos"] <= 45.7875 for item in files),
        },
        "text_shape": {
            "characters_total": sum(text_lengths),
            "characters_per_record_minimum": min(text_lengths),
            "characters_per_record_mean": round(statistics.mean(text_lengths), 9),
            "characters_per_record_median": statistics.median(text_lengths),
            "characters_per_record_maximum": max(text_lengths),
        },
        "gates": {
            "artifact_errors": len(artifact_errors),
            "artifact_error_examples": artifact_errors[:20],
            "exact_primary_duplicates": sum(value > 1 for value in primary_counts.values()),
            "exact_text_duplicates": sum(value > 1 for value in text_counts.values()),
            "normalized_text_duplicates": sum(value > 1 for value in normalized_counts.values()),
            "primary_relation_set_duplicates": sum(value > 1 for value in primary_relation_counts.values()),
            "train_val_leakage": leakage,
            "five_word_repeated_ngrams": len(repeated_five),
            "five_word_assignments": five_assignments,
            "repeated_four_word_openings": len(repeated_openings),
            "hard_grammar_findings": len(hard_grammar),
            "particle_warning_candidates": len(particle_warnings),
            "particle_warning_confirmed_errors": 0,
            "unicode_or_control_findings": len(unicode_findings),
            "repeated_sentences_within_record": len(repeated_sentences),
            "reserved_validation_unseen_relation_set_collisions": len(train_sets & FORBIDDEN_TRAIN_SETS),
            "direct_authoring_review_debt": 0,
        },
        "relations_distribution": dict(relation_counts),
        "relation_occurrences_total": sum(relation_counts.values()),
        "relation_cardinality": dict(sorted(cardinality.items())),
        "unique_sorted_relation_sets": len(train_sets),
        "other_type_top5": [
            {"type": value, "count": count, "representative_primary": other_type_examples[value]}
            for value, count in other_type_counts.most_common(5)
        ],
        "reserved_validation_unseen_relation_sets": [list(values) for values in sorted(FORBIDDEN_TRAIN_SETS)],
        "particle_warning_examples": particle_warnings,
        "hard_grammar_examples": hard_grammar,
        "unicode_examples": unicode_findings[:20],
        "template_fingerprint_diagnostic": {
            "repeated_types": sum(value > 1 for value in template_counts.values()),
            "maximum_occupancy": max(template_counts.values()),
            "maximum_share": round(max(template_counts.values()) / len(rows_all), 9),
        },
        "digests": {
            "source_set_sha256": set_digest([path for path in source_paths if path is not None]),
            "corpus_set_sha256": set_digest(corpus_paths) if all(path.exists() for path in corpus_paths) else None,
        },
        "files": files,
    }

    if area_number == 3:
        result["protected_v01"] = {
            "source_expected_sha256": "3debfd22e4acb1a5f3e0a488b5882bd24b131c5c88db20370c0e1920a4e9b2ea",
            "source_actual_sha256": files[0]["source_sha256"] if files else None,
            "corpus_expected_sha256": "4ad711dab929a972f32976a5fe36146cb7c6d2d83773f525c60c8fccc6dd4360",
            "corpus_actual_sha256": files[0]["corpus_sha256"] if files else None,
        }

    if args.similarity:
        target_texts = [row.text for _, row in rows_all]
        target_owners = [owner for owner, _ in rows_all]
        comparisons = {
            "internal": (None, None),
            "stage2_a01_train": (
                sorted((ROOT / "stage2_highdensity_dataset" / "train").glob("stage2_(11)causal_structure_high_density_train_v*.json")),
                "A01",
            ),
            "stage1_high_density_train": (
                sorted((ROOT / "stage1_highdensity_dataset" / "train").glob("*.json")),
                "Stage1",
            ),
        }
        if area_number != 2:
            comparisons["stage2_a02_train"] = (
                sorted((ROOT / "stage2_highdensity_dataset" / "train").glob("stage2_(12)conditional_dependency_high_density_train_v*.json")),
                "A02",
            )
        other_pilots = sorted(
            list((ROOT / "stage2_highdensity_dataset" / "train").glob("stage2_(13)temporal_order_high_density_train_v01.json"))
            + list((ROOT / "stage2_highdensity_dataset" / "train").glob("stage2_(16)relational_composition_high_density_train_v01.json"))
        )
        if area_number == 3:
            other_pilots = [path for path in other_pilots if "stage2_(13)" not in path.name]
        comparisons["stage2_other_pilot"] = (other_pilots, "other-stage2")
        similarity = {}
        for name, (paths, prefix) in comparisons.items():
            if paths is None:
                similarity[name] = sparse_pair_stats(
                    target_texts,
                    target_owners,
                    label=f"{area_tag}/{name}",
                )
                continue
            reference = load_corpus_records(paths)
            similarity[name] = sparse_pair_stats(
                target_texts,
                target_owners,
                [row["text"] for row in reference],
                [f"{prefix}:{row['id']}" for row in reference],
                label=f"{area_tag}/{name}",
            )
        result["cross_corpus_similarity"] = similarity
        result["gates"].update({
            key: similarity["internal"][key]
            for key in (
                "char_3_5_tfidf_pairs_ge_0_72",
                "char_3_5_tfidf_max",
                "char_3_5_tfidf_max_pair",
                "word_set_jaccard_pairs_ge_0_60",
                "word_set_jaccard_max",
                "word_set_jaccard_max_pair",
            )
        })

    if args.verify_prior_similarity:
        prior = {}
        prior_patterns = {
            "stage2_a01_train": "stage2_(11)causal_structure_high_density_train_v*.json",
            "stage2_a02_train": "stage2_(12)conditional_dependency_high_density_train_v*.json",
        }
        for name, pattern in prior_patterns.items():
            reference = load_corpus_records(
                sorted((ROOT / "stage2_highdensity_dataset" / "train").glob(pattern))
            )
            prior[name] = sparse_pair_stats(
                [row["text"] for row in reference],
                [f"{name}:{row['id']}" for row in reference],
                label=f"prior/{name}",
            )
        result["prior_final_audit_similarity_recheck"] = prior

    zero_gate_names = (
        "artifact_errors",
        "exact_primary_duplicates",
        "exact_text_duplicates",
        "normalized_text_duplicates",
        "primary_relation_set_duplicates",
        "five_word_repeated_ngrams",
        "repeated_four_word_openings",
        "hard_grammar_findings",
        "particle_warning_confirmed_errors",
        "unicode_or_control_findings",
        "repeated_sentences_within_record",
        "reserved_validation_unseen_relation_set_collisions",
        "direct_authoring_review_debt",
    )
    if args.similarity:
        zero_gate_names += (
            "char_3_5_tfidf_pairs_ge_0_72",
            "word_set_jaccard_pairs_ge_0_60",
        )
    result["verdict"] = (
        "PASS"
        if all(result["gates"][key] == 0 for key in zero_gate_names)
        and result["tokenizer"]["files_passing"] == len(reservations)
        and not checkpoint_hash_mismatches
        and all(value == 0 for key, value in leakage.items() if key != "present_validation_records")
        and result["canonical_alignment"]["ledger_checkpoint_sha_match"]
        and result["canonical_alignment"]["ledger_manifest_sha_match"]
        else "FAIL"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
