"""Assemble reviewed versions and preflight manual serialization, without a cache.

Only --approve marks the coordinator's selected final decisions as approved.
All output names are write-once. Earlier reviews and negative findings survive.
"""
from collections import Counter
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_revision as revision
from scripts.p106b_native_text_audit import file_sha, write_json

spec = importlib.util.spec_from_file_location("saved_reviews", Path(__file__).with_name("prepare_final_reviews.py"))
reviews = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reviews)
BASE = reviews.BASE
AUDIT = Path(__file__).parent


def collect(final, postbuild=False):
    sources = reviews.catalog()
    selected = {}
    def overlay(rows):
        for row in rows:
            selected[row["id"]] = dict(row)
    overlay(json.loads((BASE / "initial_adoption_candidates.json").read_text())["rows"])
    for role in reviews.recovery.ROLE_NAMES:
        review = BASE / "agents" / role / "keep_controls.md"
        for item in reviews.tables.rows(review):
            if reviews.decision(item) == "HOLD":
                ident = item["ID"]
                reason = next(v for k, v in item.items() if "근거" in k or "사유" in k)
                overlay([dict(id=ident, role=role, decision="HOLD", review=str(review.relative_to(ROOT)), reason=reason)])
        review = BASE / "agents" / role / "proposal_controls_v1.md"
        for item in reviews.tables.rows(review):
            if item["판정"] in ("HOLD", "UNRESOLVED"):
                ident = item["ID"]
                reason = next(v for k, v in item.items() if "근거" in k or "사유" in k)
                overlay([dict(id=ident, role=role, decision="HOLD", review=str(review.relative_to(ROOT)), reason=reason)])
    for name in ["repair_candidates_v2.json", "context_candidates_wave1.json", "context_candidates_wave2.json", "version_candidates_wave3.json", "versions_wave4_candidates.json", "versions_final_wave5_candidates.json"]:
        overlay(json.loads((BASE / name).read_text())["rows"])
    for role, phase in [("context_hangul", "repair_v3"), ("context_latin", "repair_v3"), ("legacy_review", "repair_v3")]:
        overlay(reviews.artifacts(role, phase, sources))
    overlay(reviews.artifacts("context_hangul", "recovery_context_v4", sources))
    overlay(reviews.artifacts("legacy_review", "context_repair_v5", sources,
        {"expanded_train:388100", "expanded_train:275683"}))
    overlay(reviews.artifacts("context_latin", "context_repair_v4", sources))
    validation = json.loads((BASE / "validation_v3_complete_review.json").read_text())["rows"]
    overlay([r for r in validation if r["decision"] in ("KEEP", "EDIT", "HOLD")])
    for role in reviews.recovery.ROLE_NAMES:
        if not final and role in ("historical_review", "context_controls"):
            continue
        items = reviews.artifacts(role, "validation_v5", sources)
        assert len(items) == {"context_hangul": 5, "context_latin": 5, "historical_review": 19, "legacy_review": 4, "context_controls": 6}[role]
        overlay(items)
    if final:
        overlay(reviews.artifacts("context_controls", "root_extra_v2", sources, {"expanded_train:250733"}))
        overlay(reviews.artifacts("context_hangul", "decorative_markers_v1", sources))
        overlay(reviews.artifacts("historical_review", "validation_v6", sources,
            {"expanded_train:237167", "expanded_train:1160140", "expanded_train:664", "expanded_train:658980"}))
    if postbuild:
        previous = {r["id"]: r for r in json.loads((AUDIT / "root_adoptions_v1.json").read_text())["rows"]}
        for role, ids in {
            "context_controls": {"expanded_train:1415117", "expanded_train:384984", "expanded_train:950001", "expanded_train:1170731", "expanded_train:1389144", "expanded_train:1008442", "validation:44"},
            "historical_review": {"expanded_train:783522"},
            "legacy_review": {"expanded_train:995468"},
        }.items():
            items = reviews.artifacts(role, "postbuild_residual_v1", sources, ids)
            for item in items:
                old = previous[item["id"]]
                item["superseded_decision"] = {k: old[k] for k in ["path", "sha256", "review", "reason", "sidecar_path", "sidecar_sha256"] if k in old}
                if not item.get("sidecar_path") and old.get("path"):
                    sidecar = (ROOT / old["path"]).with_name(Path(old["path"]).stem + "_hold.md")
                    if sidecar.is_file():
                        item.update(sidecar_path=str(sidecar.relative_to(ROOT)), sidecar_sha256=file_sha(sidecar), sidecar_inherited_unchanged=True)
            overlay(items)
        for role, ids in {"context_controls": {"validation:44"}, "historical_review": {"expanded_train:783522"}}.items():
            items = reviews.artifacts(role, "postbuild_residual_v2", sources, ids)
            for item in items:
                old = previous[item["id"]]
                item["superseded_decision"] = {k: old[k] for k in ["path", "sha256", "review", "reason", "sidecar_path", "sidecar_sha256"] if k in old}
            overlay(items)
    output = []
    for ident, raw in selected.items():
        source = sources[ident]
        row = dict(raw, input_text_sha256=source["original_text_sha256"], original_path=source["original_path"],
            source=source["source"], source_ids=source["source_ids"], source_ids_sha256=source["source_ids_sha256"],
            root_reviewed=False, recovery_review=True, resolves_inherited_hold=True,
            source_proof=str((AUDIT / "review_source_proof_all_v3.json").relative_to(ROOT)),
            coordinator_resolution=str((AUDIT / "ROOT_CASE_RESOLUTION.md").relative_to(ROOT)))
        assert row["decision"] in ("KEEP", "EDIT", "HOLD")
        if row["decision"] == "EDIT":
            path = ROOT / row["path"]
            assert path.is_relative_to(BASE / "agents") and path.is_file()
            row["sha256"] = file_sha(path)
            if path.read_bytes() == (ROOT / row["original_path"]).read_bytes():
                row["decision"] = "KEEP"
                row["unchanged_saved_draft"] = row.pop("path")
                row.pop("sha256")
        if ident == "expanded_train:1422568" and row["decision"] == "EDIT":
            original = (ROOT / row["original_path"]).read_text(encoding="utf-8")
            lo = original.index("``` ")
            hi = original.index("Call Communication and Reporting Officer")
            row["code_exception"] = dict(kind="UNWRAP_EXTRACTED_UNIT_TABLE",
                original_text_sha256=revision.engine.sha(original), original_table_characters=[lo, hi],
                original_table_sha256=revision.engine.sha(original[lo:hi]))
        if ident in {"expanded_train:100340", "expanded_train:722973", "expanded_train:1393097", "expanded_train:629198", "expanded_train:1011519", "expanded_train:209344", "expanded_train:434723", "expanded_train:480211", "expanded_train:541336"} and row["decision"] in ("KEEP", "EDIT"):
            original = (ROOT / row["original_path"]).read_text(encoding="utf-8")
            lines = [line for line in original.splitlines() if re.match(r"^~{3,}[^~]", line)]
            assert lines, (ident, lines)
            row["code_exception"] = dict(kind="DECORATIVE_TILDE_MARKERS",
                original_text_sha256=revision.engine.sha(original), decorative_lines=lines)
        if ident == "expanded_train:250733":
            row["source_quote_exception"] = "Verbatim source quotation and conditional clause retained; damaged FAR reference punctuation is not factually reconstructed."
        if ident == "expanded_train:783522":
            row["format_structure_exception"] = "Populated parent reference heading followed by a bibliography subsection; retain actual source titles."
        if ident in ("expanded_train:912185", "expanded_train:998546"):
            row["birth_guard_false_positive"] = "Birth year only precedes a full death date; do not misread that death date as the birth date."
        output.append(row)
    assert len({r["input_text_sha256"] for r in output}) == len(output)
    return sorted(output, key=lambda r: r["id"])


def preflight(rows):
    codec = revision.engine.cache.native.ByteCodec(revision.engine.cache.read(ROOT / "data_cache/tok-ko-en-32768-chat32.json"))
    engine = revision.engine.RecoveryEngine.__new__(revision.engine.RecoveryEngine)
    results = []
    with revision.revision():
        for row in rows:
            original = (ROOT / row["original_path"]).read_text(encoding="utf-8")
            assert revision.engine.sha(original) == row["input_text_sha256"], row["id"]
            if row["decision"] == "HOLD":
                continue
            text = (ROOT / row["path"]).read_text(encoding="utf-8") if row["decision"] == "EDIT" else original
            engine.current = (dict(text=original), 3)
            code = engine.code_guard(original, text, row)
            ids = codec.backend.encode(text, add_special_tokens=False).ids
            decoded, body = codec.text(ids)
            valid = decoded == text and body == text.encode("utf-8") and not any(v in codec.specials for v in ids)
            results.append(dict(id=row["id"], code_unicode_guard=code, native_roundtrip=valid,
                memo_free=not bool(revision.engine.corpus.MEMOS.search(text)),
                original_text_sha256=row["input_text_sha256"], clean_text_sha256=revision.engine.sha(text), encoded_body_ids=len(ids),
                characters=len(text), bytes=len(text.encode("utf-8"))))
    failures = [r for r in results if not (r["code_unicode_guard"] and r["native_roundtrip"] and r["memo_free"])]
    return dict(schema="P106B_RECOVERY_MANUAL_PREFLIGHT_V1", actual_model_loads=0, rows=results,
        positive_rows=len(results), failed_rows=failures,
        note="Identity, serialization, Unicode and literal code checks; semantic review is separately linked.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--postbuild", action="store_true")
    args = parser.parse_args()
    assert args.name.isascii() and args.name.replace("_", "").isalnum()
    assert not args.approve or args.final
    assert not args.postbuild or args.final
    rows = collect(args.final, args.postbuild)
    report = preflight(rows)
    if args.approve:
        assert not report["failed_rows"], report["failed_rows"]
        for row in rows:
            row["root_reviewed"] = True
    target = AUDIT / (args.name + ".json")
    with revision.revision():
        pins = revision.engine.code_pins()
    document = dict(schema="P106B_ROOT_TEXT_ADOPTIONS_V1", rows=rows,
        root_decisions_approved=args.approve, cache_created=False, training_authorized=False,
        source_code_sha256=pins, counts=dict(Counter(r["decision"] for r in rows)))
    if args.postbuild:
        document.update(supersedes_adoptions=str((AUDIT / "root_adoptions_v1.json").relative_to(ROOT)),
            supersedes_adoptions_sha256=file_sha(AUDIT / "root_adoptions_v1.json"))
    write_json(target, document)
    write_json(AUDIT / (args.name + "_preflight.json"), dict(report, adoptions_path=str(target.relative_to(ROOT)), adoptions_sha256=file_sha(target)))
    print(dict(rows=len(rows), decisions=dict(Counter(r["decision"] for r in rows)), positive_rows=report["positive_rows"], failures=report["failed_rows"], approved=args.approve))


if __name__ == "__main__":
    main()
