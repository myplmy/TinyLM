"""Summarize an actually verified recovery cache, with explicit denominators."""
from collections import Counter
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_recovery as recovery
from scripts import p106b_corpus_cache as cache
from scripts.p106b_native_text_audit import file_sha, write_json


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def summed(mapping):
    result = Counter()
    for values in mapping.values():
        result.update(values)
    return dict(result)


def percent(numerator, denominator):
    return 100 * numerator / denominator if denominator else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-name", default="cache_v4")
    parser.add_argument("--receipt-name", default="verified_recovery_measurement_v2")
    args = parser.parse_args()
    assert all(v.isascii() and v.replace("_", "").isalnum() for v in (args.output_name, args.receipt_name))
    base = recovery.BASE
    parent = recovery.PARENT / "cache_v1"
    out = base / args.output_name
    old = read(parent / "built.json")
    built = read(out / "built.json")
    verified = read(out / "verified.json")
    recovery_verified = read(out / "recovery_verified.json")
    assert recovery_verified["status"] == "CPU_FULL_RECOVERY_CACHE_VERIFIED"
    assert recovery_verified["all_previous_adopted_text_preserved"]
    assert recovery_verified["built_sha256"] == file_sha(out / "built.json")
    assert recovery_verified["core_verified_sha256"] == file_sha(out / "verified.json")
    assert built["recovery"]["parent_built_sha256"] == file_sha(parent / "built.json")
    assert built["recovery"]["parent_verified_sha256"] == file_sha(parent / "verified.json")
    assert built["counts"]["documents"] == old["counts"]["documents"] == 2_154_912
    assert built["counts"]["input_ids"] == old["counts"]["input_ids"] == 1_792_116_192
    outcomes = built["recovery_outcomes"]
    assert outcomes == recovery_verified["recovery_outcomes"]
    assert outcomes["documents"] == old["counts"]["HOLD"] == 817_494
    assert outcomes["input_ids"] == old["counts"]["HOLD_input_ids"] == 632_318_138
    assert sum(outcomes.get(k, 0) for k in ["KEEP", "EDIT", "HOLD", "EXCLUDE"]) == outcomes["documents"]
    assert built["counts"]["HOLD"] == outcomes["HOLD"]
    assert all(built["counts"].get(k, 0) == old["counts"].get(k, 0) + outcomes.get(k, 0) for k in ["KEEP", "EDIT", "EXCLUDE"])
    hold_reasons, primary_reasons, hold_sources = Counter(), Counter(), Counter()
    actual_holds = 0
    for row in cache.rows(out / "hold", built["manifests"]["hold"]):
        assert row["decision"] == "HOLD" and row["parent_decision"] == "HOLD"
        actual_holds += 1
        hold_sources.update([row["source"]])
        reasons = row["reasons"]
        # Individual text judgments have prose reasons. Keep the full reasons in
        # the original ledger and group only their display in this summary.
        labels = [reason if reason.replace("_", "").isalnum() and reason.isascii() else "INDIVIDUAL_CONTEXT_HOLD" for reason in reasons]
        hold_reasons.update(set(labels))
        primary_reasons.update(labels[:1])
    assert actual_holds == built["counts"]["HOLD"]
    assert sum(primary_reasons.values()) == actual_holds
    inventory = []
    for directory in [base, Path(__file__).parent]:
        for path in directory.rglob("*"):
            assert not path.is_symlink(), str(path)
            if path.is_file():
                inventory.append(dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size))
    assert inventory and max(r["bytes"] for r in inventory) < 20_000_000
    old_docs = sum(v["documents"] for v in old["accepted"].values())
    new_docs = sum(v["documents"] for v in built["accepted"].values())
    assert new_docs - old_docs == outcomes.get("KEEP", 0) + outcomes.get("EDIT", 0)
    same = built["same_adopted_roster_before"]
    same_before_tokens = sum(v["tokens"] for v in same["counts"].values())
    adopted_tokens = sum(v["tokens"] for v in built["accepted"].values())
    assert adopted_tokens - same_before_tokens == built["counts"]["edited_content_ids_delta"]
    original_docs = old["counts"]["documents"]
    signal_counts = {
        "full_original_document_signals": old["original_documents_with_signal"],
        "parent_adopted_document_signals": summed(old["accepted_documents_with_signal"]),
        "new_adopted_document_signals": summed(built["accepted_documents_with_signal"]),
        "same_new_adopted_roster_before_lines": summed(same["structure_signals"]),
        "new_adopted_lines": summed(built["accepted_structure_signals"]),
    }
    document_signal_percentages = {}
    for key in ["standalone_heading_lines", "empty_or_adjacent_heading_lines", "within_doc_repeated_line_extras"]:
        document_signal_percentages[key] = dict(
            full_original=percent(signal_counts["full_original_document_signals"].get(key, 0), original_docs),
            parent_adopted=percent(signal_counts["parent_adopted_document_signals"].get(key, 0), old_docs),
            new_adopted=percent(signal_counts["new_adopted_document_signals"].get(key, 0), new_docs))
    language = {}
    for name, value in [("parent_train", old["accepted_language_proxy"]["train"]), ("new_train", built["accepted_language_proxy"]["train"])]:
        language[name] = dict(value, hangul_syllables_per_codepoints_percent=percent(value.get("hangul_syllables", 0), value["codepoints"]))
    report = dict(schema="P106B_VERIFIED_RECOVERY_MEASUREMENT_V1",
        output_name=args.output_name,
        parent_built_sha256=file_sha(parent / "built.json"), built_sha256=file_sha(out / "built.json"),
        verified_sha256=file_sha(out / "verified.json"), recovery_verified_sha256=file_sha(out / "recovery_verified.json"),
        total_input_documents=original_docs, total_input_ids=built["counts"]["input_ids"],
        parent_counts=old["counts"], new_counts=built["counts"], recovery_outcomes=outcomes,
        unprocessed=0, baseline_adopted_documents_preserved=old_docs,
        parent_accepted=old["accepted"], new_accepted=built["accepted"],
        newly_adopted_documents=new_docs - old_docs,
        hold_reduction=old["counts"]["HOLD"] - built["counts"]["HOLD"],
        hold_reduction_percent_of_previous_hold=percent(old["counts"]["HOLD"] - built["counts"]["HOLD"], old["counts"]["HOLD"]),
        hold_percent_of_full_input_before=percent(old["counts"]["HOLD"], original_docs),
        hold_percent_of_full_input_after=percent(built["counts"]["HOLD"], original_docs),
        same_new_adopted_roster_before_tokens=same_before_tokens, adopted_tokens=adopted_tokens,
        pure_edit_ids_delta=adopted_tokens - same_before_tokens,
        selected_input_ids=built["counts"].get("KEEP_input_ids", 0) + built["counts"].get("EDIT_input_ids", 0),
        held_original_input_ids=built["counts"].get("HOLD_input_ids", 0),
        excluded_original_input_ids=built["counts"].get("EXCLUDE_input_ids", 0),
        signals=signal_counts, document_signal_percentages=document_signal_percentages,
        hold_reasons_may_overlap=dict(hold_reasons), mutually_exclusive_first_hold_reason=dict(primary_reasons), hold_sources=dict(hold_sources),
        language_character_proxy=language, true_language_labels="UNKNOWN", source_kind=built["source_kind"],
        exact_unique_original_texts=built["exact_unique_original_texts"],
        global_original_article_leakage=built["global_original_article_leakage"],
        cache_overlap_check=built["overlap_check"], cache_overlap_limit=built["overlap_limit"],
        structure_signals_are_not_error_rates=True,
        new_session_artifacts=dict(files=len(inventory), total_bytes=sum(r["bytes"] for r in inventory), maximum_bytes=max(r["bytes"] for r in inventory)),
        build_seconds=built["seconds"], core_verification_seconds=verified["seconds"],
        model_loads=0, gpu_calls=0, original_writes=0, training_authorized=False)
    target = Path(__file__).with_name(args.receipt_name + ".json")
    write_json(target, report)
    print(json.dumps({k: report[k] for k in ["new_counts", "recovery_outcomes", "new_accepted", "hold_reduction", "newly_adopted_documents", "language_character_proxy"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
