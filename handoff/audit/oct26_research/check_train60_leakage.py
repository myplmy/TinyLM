"""Read-only source/group overlap audit; no model, split or corpus mutation."""
from collections import Counter
import gzip
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_admission as admission
from scripts import p106b_broad_course as broad
from scripts.diag_p090b_public_preflight import digest, split_counts
from tinylm.chat.canonical import normalize
from tinylm.data.sft import conversation_split_key

BASE = ROOT / "handoff/audit/oct26_research"
PACKET = ROOT / "data_cache/p106b_text_work_20261022/packets/sft_legacy60_recovery_20261025.json"
PREPARED = ROOT / "data_cache/p106b_text_work_20261022/approved_train60_20261025_v2"
EXPOSURE = ROOT / "handoff/audit/WIP_20261025_SFT_EXPOSURE_ROOT_READBACK.json"
COURSE = ROOT / "data_cache/p106b_broad_curriculum_v2_s1337/course.json"


def pin(path):
    path = admission.local_path(path)
    before = path.stat()
    value = dict(path=path.relative_to(ROOT).as_posix(), bytes=before.st_size, sha256=digest(path))
    after = path.stat()
    assert before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns
    return value


def identities(row):
    row = normalize(row)
    meta = row["meta"]
    return dict(source=(meta["source"], str(meta["source_id"])),
                prompt=conversation_split_key(row).hex().upper(), messages=broad.sha(row["messages"]))


def index(rows):
    out = {key: set() for key in ("source", "prompt", "messages")}
    for row in rows:
        for key, value in identities(row).items():
            out[key].add(value)
    return out


def intersections(left, right):
    return {key: len(left[key] & right[key]) for key in left}


def main():
    started = time.monotonic()
    output = BASE / "train60_leakage_readback.json"
    if output.exists():
        raise FileExistsError("exclusive readback already exists")
    packet = json.loads(PACKET.read_text())
    sources = packet["sources"]
    original_rows = [normalize(dict(messages=s["messages"], meta=s["meta"])) for s in sources]
    assert len(original_rows) == 60
    wanted = index(original_rows)
    manifest_path = PREPARED / "corpus/admission_manifest.json"
    manifest_sha = digest(manifest_path)
    admitted = [row for row, record in admission.iter_sft_records(PREPARED / "corpus", manifest_sha)]
    assert len(admitted) == 158 and all(row["split"] == "train" for row in admitted)
    variant_rows = [row["canonical"] for row in admitted]
    variants = index(variant_rows)
    inputs = [pin(p) for p in (PACKET, EXPOSURE, COURSE, PREPARED / "bundle.json",
        PREPARED / "root_splits.json", manifest_path)]
    version_rows, version_reports = {}, {}
    for version in (1, 2, 3):
        prefix = ROOT / "HF/sft_ready" / ("p090_public_v" + str(version))
        paths = {split: Path(str(prefix) + "_" + split + ".canonical.jsonl") for split in ("train", "val")}
        paths["manifest"] = Path(str(prefix) + "_manifest.json")
        rows = {split: [json.loads(line) for line in paths[split].read_text().splitlines() if line.strip()]
                for split in ("train", "val")}
        metadata = json.loads(paths["manifest"].read_text())
        specs = {key: pin(path) for key, path in paths.items()}
        assert all(specs[split]["sha256"] == metadata["output_sha256"][split] for split in ("train", "val"))
        inputs.extend(specs.values())
        source_indices = {split: index(rows[split]) for split in ("train", "val")}
        report = dict(rows={split: len(value) for split, value in rows.items()},
            whole_public_split_counts=split_counts(rows["train"], rows["val"]),
            original60={split: intersections(wanted, idx) for split, idx in source_indices.items()},
            accepted158={split: intersections(variants, idx) for split, idx in source_indices.items()},
            oasst_tree_root_intersection=sum(s[0] == "oasst" for s in
                source_indices["train"]["source"] & source_indices["val"]["source"]))
        version_rows[version] = rows
        version_reports[str(version)] = report
    course = json.loads(COURSE.read_text())
    assert broad.sha(version_rows[3]["train"]) == course["source_input_sha256"]["public_train"]
    selected = course["general_admission"]["selected_sources"]
    # The saved course is a selection over this exact ordered public input.
    actual_rows = []
    for selected_source in selected:
        row = normalize(version_rows[3]["train"][selected_source["source_index"]])
        ident = identities(row)
        assert ident["messages"] == selected_source["messages_sha256"]
        assert row["meta"]["source_id"] == selected_source["source"]["source_id"]
        actual_rows.append(row)
    actual = index(actual_rows)
    exposure = json.loads(EXPOSURE.read_text())
    assert exposure["actual_step_events"] == 704 and exposure["legacy60_found"] == 60
    actual_course = dict(selected_rows=len(actual_rows), actual_training_events=704,
        original60_membership=intersections(wanted, actual),
        vs_public_val={str(version): intersections(actual, index(rows["val"]))
                       for version, rows in version_rows.items()},
        scope="EXACT_SFT_SELECTION_OF_ONE_COMPLETED_COURSE; NOT_ALL_HISTORICAL_MODEL_INPUTS")
    # Recover real tree identities rather than treating a content hash as a document.
    wanted_oasst = {str(s["meta"]["source_id"]): s["source_index"]
                    for s in sources if s["meta"]["source"] == "oasst"}
    tree_path = ROOT / "HF/sft_sources/oasst/2023-04-12_oasst_ready.trees.jsonl.gz"
    inputs.append(pin(tree_path))
    tree_counts, prompt_counts, matched, tree_count = Counter(), Counter(), [], 0
    with gzip.open(tree_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            tree = json.loads(line)
            tree_count += 1
            tree_id = str(tree.get("message_tree_id", ""))
            prompt_id = str(tree.get("prompt", {}).get("message_id", ""))
            if tree_id in wanted_oasst:
                tree_counts[tree_id] += 1
                matched.append(dict(source_index=wanted_oasst[tree_id], tree_id=tree_id,
                    prompt_id=prompt_id, split_field_present="split" in tree))
            if prompt_id in wanted_oasst:
                prompt_counts[prompt_id] += 1
    assert len(wanted_oasst) == 7 and len(matched) == 7
    assert all(tree_counts[key] == prompt_counts[key] == 1 for key in wanted_oasst)
    assert all(row["tree_id"] == row["prompt_id"] for row in matched)
    import pyarrow.parquet as pq
    aya_path = ROOT / "HF/sft_sources/aya/data/train-00000-of-00001.parquet"
    inputs.append(pin(aya_path))
    parquet = pq.ParquetFile(aya_path)
    columns = parquet.schema.names
    assert columns == ["inputs", "targets", "language", "language_code", "annotation_type", "user_id"]
    assert all(pin(ROOT / spec["path"]) == spec for spec in inputs)
    known_val_hits = {str(version): version_reports[str(version)]["accepted158"]["val"]
                      for version in version_rows}
    report = dict(schema="P106B_TRAIN60_DOCUMENT_IDENTITY_READBACK_V1", inputs=inputs,
        original_sources=60, accepted_variants=158,
        by_source=dict(Counter(s["meta"]["source"] for s in sources)),
        public_versions=version_reports, actual_completed_course=actual_course,
        recovered_oasst=dict(raw_trees=tree_count, matched=matched, target_tree_duplicates=0,
            upstream_split_available=False, assertion="REAL_DIALOGUE_ROOT_RECOVERED; NOT_UPSTREAM_SPLIT_RECOVERY"),
        aya=dict(rows=parquet.metadata.num_rows, row_groups=parquet.metadata.num_row_groups,
            columns=columns, document_identity_available=False, user_id_is_not_document_identity=True,
            content_rows_read_for_audit=0),
        accepted_variants_vs_known_public_val=known_val_hits,
        official_benchmark_document_overlap="NOT_MEASURED", global_document_overlap="UNVERIFIED",
        native600m_document_overlap="NOT_MEASURED", all_historical_course_overlap="NOT_MEASURED",
        original_or_accepted_corpus_mutated=False, split_changes=0, new_evaluation_data=0,
        automatic_semantic_reviews=0, model_calls=0, gpu_calls=0, whole_sec=time.monotonic() - started,
        code_pins={name: digest(ROOT / name) for name in ("scripts/prepare_public_sft.py",
            "scripts/diag_p090b_public_preflight.py", "scripts/p106b_broad_course.py",
            "scripts/p106b_admission.py", "tinylm/data/sft.py", "tinylm/chat/canonical.py")})
    admission.exclusive_json(output, report)
    print(json.dumps(dict(output=str(output.relative_to(ROOT)), source_count=60,
        recovered_dialogue_roots=7, aya_document_id_available=False,
        known_public_val_hits=known_val_hits, actual_course=actual_course,
        global_document_overlap="UNVERIFIED", whole_sec=report["whole_sec"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
