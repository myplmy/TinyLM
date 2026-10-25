#!/usr/bin/env python3
"""Explicit text-draft admission, without models, automatic review or splitting.

The ``freeze`` adapter consumes the real p106b_text_batches.import_packet V5
report and authoring/review/triage shard manifests, plus exact successful
p106b_publish_text_draft V1 receipts and published response objects. It never
calls the importer (which would reopen the canonical corpus). A parent packet
must be covered in full, including triage-only IDs. A smaller child packet is
not evidence of coverage of its parent.

``prepare`` requires SHA-bound, per-candidate reviews and a supplied root split
and exposure ledger. No split ratio, random seed, semantic verdict or rights
decision is selected here. ChatML SFT uses mtp_sft.encode_record and its exact
assistant segments, then restricts them to explicitly reviewed source turns.
Native text has a separate, explicit EOS/NTP contract and no assistant targets.
Over-context records fail; this tool never truncates, chunks or trains them.

Every output namespace/file is exclusive and every file is below20,000,000B.
An interrupted output is preserved and has no valid completion manifest.
Preparation does not merge a corpus into an existing trainer or run a model.
Paths are explicit local files; protected TinyDataset and symlinks are refused.
The publisher dependency uses POSIX file APIs; this entry point targets WSL.

Publication index (all paths are literal, relative to cwd or absolute)::

  {"schema":"P106B_ADMISSION_PUBLICATIONS_V1", "kind":"sft",
   "parent_packet_sha256":"...", "entries":[
     {"source_id":7,"receipt":".../receipt.json","published":".../7.json"}],
   "response_file":".../response.json"}

``response_file`` is required only for FILE_BYTES imports. For the existing
SORTED_FILENAME_TO_FILE_SHA256_BUNDLE import, published bytes must match every
entry in report.response_files. No directory discovery or source corpus read
is needed. The frozen bundle retains exact imported rows and receipt SHAs and
is rebuilt from these explicit artifacts before use, detecting stale inputs.

Review document::

  {"schema":"P106B_ADMISSION_REVIEWS_V1", "parent_packet_sha256":"...",
   "bundle_sha256":"...", "decisions":[
     {"candidate_id":"sft:7:ko_translation","candidate_sha256":"...",
      "decision":"ACCEPT", "supervised_assistant_turns":[2],
      "reviews":{"meaning":{"decision":"ACCEPT","reviewer":"...","reason":"...",
                    "evidence":{"source_sha256":"...","reference":"...","context":"..."}},
                 "terminology":{...},"provenance":{...},"rights":{...},
                "supervision":{...}}}]}

All five dimensions must be explicitly ACCEPT for an ACCEPT request. HOLD and
REJECT remain excluded. Native decisions use supervised_assistant_turns=[].

Root ledger::

  {"schema":"P106B_ADMISSION_ROOT_SPLITS_V1","parent_packet_sha256":"...",
   "split_policy_reference":"existing owner document and immutable version",
   "roots":[{"root_id":"...","group_id":"same original document group",
     "split":"train","source_history":[
     {"source_id":7,"source_sha256":"...","source_split":"train",
      "source_document_id":"immutable original document identity",
      "prior_exposure_splits":["train"],"evidence":"..."}]}]}

Explicit prior TRAIN exposure pins a root to train; source val/test or prior
val/test exposure forbids train. Public source_split=train alone is not prior
training exposure. With an explicit empty prior history and evidence, the owner
can assign that unused source to local val/test without changing source_split.
History assertions are not independently verified or called unseen evaluation.
Conflicting exposures are a contamination error. Unknown origin cannot be admitted.
Originals and all variants inherit one root assignment. Equal original-source
identities also cannot appear under different splits through different roots.

The explicit ROOT_SPLITS_TRAIN_REUSE_V2 alternative accepts a missing upstream
document identity only for a source record matched by SHA/root to a pinned
historical TRAIN readback. It requires SOURCE_RECORD_TRAIN_ONLY, a missing
document identity and UNVERIFIED global document overlap. It cannot assign
val/test, erase known evaluation exposure or claim document-level leakage zero.

Encoding contract::

  {"schema":"P106B_ADMISSION_ENCODING_V1","template":"chatml","context":1024,
   "tokenizer":{"path":"...json","sha256":"..."},
   "native_eos":{"policy":"APPEND_ONE","token":"</s>","id":2}}

Native EOS policy is APPEND_ONE or ALREADY_PRESENT, checked against the fixed
tokenizer vocabulary. native_eos is unnecessary for SFT. The API's injected
synthetic tokenizer always produces SYNTHETIC_ONLY_NOT_ADMITTED outputs.

``iter_sft_records(output, manifest_sha256, split="train")`` verifies the pinned
manifest and yields (audit_row, mtp_sft.Record) for the existing count_record /
pad_records APIs. It refuses synthetic output unless explicitly requested for
CPU tests. No generic trainer consumes this new manifest automatically.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_publish_text_draft as publication
from scripts import p106b_text_batches as batches
from scripts.p106b_shards import MAX_BYTES, ShardWriter, verify as verify_shards

LIMIT = MAX_BYTES - 1
BUNDLE_SCHEMA = "P106B_ADMISSION_FROZEN_IMPORT_V1"
PUBLICATIONS_SCHEMA = "P106B_ADMISSION_PUBLICATIONS_V1"
REVIEWS_SCHEMA = "P106B_ADMISSION_REVIEWS_V1"
SPLITS_SCHEMA = "P106B_ADMISSION_ROOT_SPLITS_V1"
TRAIN_REUSE_SCHEMA = "P106B_ADMISSION_ROOT_SPLITS_TRAIN_REUSE_V2"
ENCODING_SCHEMA = "P106B_ADMISSION_ENCODING_V1"
MANIFEST_SCHEMA = "P106B_ADMISSION_MANIFEST_V1"
DIMENSIONS = ("meaning", "terminology", "provenance", "rights", "supervision")
VERDICTS = ("ACCEPT", "HOLD", "REJECT")
SPLITS = ("train", "val", "test")
CODE = ("scripts/p106b_admission.py", "scripts/p106b_text_batches.py",
        "scripts/p106b_publish_text_draft.py", "scripts/p106b_native_text_audit.py",
        "scripts/p106b_text_policy_revision.py", "scripts/p106b_source_cleanup.py",
        "scripts/p106b_shards.py", "tinylm/train/mtp_sft.py", "tinylm/data/sft.py",
        "tinylm/chat/serialize.py", "tinylm/chat/canonical.py")


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def sha_value(value):
    return publication.object_sha(value)


def sha_string(value):
    if (not isinstance(value, str) or len(value) != 64
            or any(c not in "0123456789abcdefABCDEF" for c in value)):
        raise ValueError("explicit SHA256 required")
    return value.upper()


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + " must be explicit nonempty text")
    return value


def ident(value):
    if type(value) is not int or value < 0:
        raise ValueError("source ID must be a nonnegative integer")
    return value


def local_path(value):
    """Refuse protected paths and every symlink component before any read."""
    path = Path(value)
    if ".." in path.parts:
        raise ValueError("path traversal refused")
    if not path.is_absolute():
        path = Path.cwd() / path
    if any(path.parts[i:i+2] == ("datasets", "TinyDataset")
           for i in range(len(path.parts)-1)):
        raise ValueError("protected TinyDataset path refused without reading")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("linked input/output path refused")
    return path


def read_artifact(value):
    path = local_path(value)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > LIMIT:
        raise ValueError("regular input file below20MB required")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(MAX_BYTES)
        after = os.fstat(stream.fileno())
    current = path.stat()
    stamp = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if (len(raw) > LIMIT or len(raw) != before.st_size
            or not stamp(before) == stamp(opened) == stamp(after) == stamp(current)):
        raise ValueError("input changed during bounded read")
    return raw, dict(path=str(path), bytes=len(raw), sha256=digest(raw))


def read_json(value):
    raw, artifact = read_artifact(value)
    return publication.parse(raw), artifact


def json_bytes(value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                      allow_nan=False) + "\n").encode("utf-8")
    if len(raw) > LIMIT:
        raise ValueError("individual JSON exceeds below20MB contract; no partial coverage")
    return raw


def exclusive_json(path, value):
    path = local_path(path)
    raw = json_bytes(value)
    with path.open("xb") as stream:
        if stream.write(raw) != len(raw):
            raise OSError("short exclusive write; incomplete file preserved")
        stream.flush()
        os.fsync(stream.fileno())
    return dict(path=str(path), bytes=len(raw), sha256=digest(raw))


def source_code_hashes():
    return {name: read_artifact(CODE_ROOT / name)[1]["sha256"] for name in CODE}


def indexed(rows, field, description):
    if not isinstance(rows, list):
        raise ValueError(description + " array required")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(description + " object required")
        key = ident(row.get(field))
        if key in result:
            raise ValueError(description + " duplicate source ID")
        result[key] = row
    return result


def exact_keys(actual, expected, description):
    if set(actual) != set(expected):
        raise ValueError(description + " exact coverage mismatch: missing="
                         + str(sorted(set(expected)-set(actual))) + " foreign="
                         + str(sorted(set(actual)-set(expected))))


def import_rows(directory, stem, report, artifacts):
    manifest_path = directory / (stem + "_shards_manifest.json")
    manifest, artifact = read_json(manifest_path)
    artifacts.append(artifact)
    expected = {k: report[k] for k in ("packet_sha256", "response_sha256", "kind", "training_admission")}
    lineage = manifest.get("lineage", {})
    if any(lineage.get(k) != v for k, v in expected.items()):
        raise ValueError("import manifest lineage differs from import report")
    for spec in manifest.get("shards", []):
        name = spec.get("path")
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("unsafe import shard name")
        local_path(directory / name)
    verify_shards(directory, manifest)
    rows = []
    for spec in manifest["shards"]:
        raw, artifact = read_artifact(directory / spec["path"])
        if (artifact["sha256"] != spec["sha256"] or artifact["bytes"] != spec["bytes"]):
            raise ValueError("import shard changed after verification")
        artifacts.append(artifact)
        for line in raw.splitlines():
            row = publication.parse(line)
            if not isinstance(row, dict):
                raise ValueError("import shard row must be an object")
            rows.append(row)
    if len(rows) != manifest["rows"]:
        raise ValueError("import shard row count differs")
    return rows


def publication_rows(packet, packet_artifact, report, index, artifacts):
    if index.get("schema") != PUBLICATIONS_SCHEMA or index.get("kind") != report["kind"]:
        raise ValueError("explicit publication index schema/kind required")
    if sha_string(index.get("parent_packet_sha256")) != packet_artifact["sha256"]:
        raise ValueError("publication index parent packet SHA differs")
    key, collection = (("source_index", "sources") if report["kind"] == "sft" else ("id", "documents"))
    sources = indexed(packet[collection], key, "parent packet")
    entries = indexed(index.get("entries"), "source_id", "publication index")
    exact_keys(entries, sources, "publication parent source IDs")
    published, receipts, file_shas = {}, {}, {}
    for source_id, entry in sorted(entries.items()):
        receipt, receipt_artifact = read_json(entry["receipt"])
        raw, published_artifact = read_artifact(entry["published"])
        row = publication.parse(raw)
        artifacts.extend((receipt_artifact, published_artifact))
        if (receipt.get("schema") != publication.SCHEMA
                or receipt.get("status") != "PUBLISHED_COPY_ONLY_DRAFT"
                or type(receipt.get("exit_code")) is not int or receipt["exit_code"] != 0
                or receipt.get("published_by_this_attempt") is not True
                or receipt.get("training_admission") != "NOT_ADMITTED"
                or receipt.get("kind") != report["kind"]):
            raise ValueError("successful copy-only publication receipt required")
        final = Path(text(receipt.get("final"), "receipt final path"))
        final = final if final.is_absolute() else ROOT / final
        if local_path(final) != local_path(entry["published"]):
            raise ValueError("publication final path differs from explicit index")
        for name in ("packet_before", "packet_after", "packet_raw_reference"):
            observed = receipt.get(name, {})
            if (observed.get("sha256") != packet_artifact["sha256"]
                    or observed.get("bytes") != packet_artifact["bytes"]):
                raise ValueError("publication parent packet SHA/bytes differs")
        if receipt["packet_before"] != receipt["packet_after"]:
            raise ValueError("publication packet changed during attempt")
        for name in ("input_before", "input_after", "final_observation"):
            observed = receipt.get(name, {})
            if (observed.get("sha256") != published_artifact["sha256"]
                    or observed.get("bytes") != published_artifact["bytes"]):
                raise ValueError("publication candidate SHA/bytes differs")
        if receipt["input_before"] != receipt["input_after"]:
            raise ValueError("publication input changed during attempt")
        code = receipt.get("code_sha256_before")
        if not isinstance(code, dict) or not code or code != receipt.get("code_sha256_after"):
            raise ValueError("publication code provenance absent/changed")
        for value in code.values():
            sha_string(value)
        proof = publication.validate(packet, row, report["kind"])
        if (row.get(key) != source_id or receipt.get("source_before") != proof
                or receipt.get("source_after") != proof):
            raise ValueError("publication source identity/proof differs")
        published[source_id], receipts[source_id] = row, receipt_artifact["sha256"]
        file_shas[str(source_id) + ".json"] = published_artifact["sha256"]
    response_kind = report.get("response_identity_kind")
    if response_kind == "SORTED_FILENAME_TO_FILE_SHA256_BUNDLE":
        if (report.get("response_files") != file_shas
                or report["response_sha256"] != batches.sha(json.dumps(file_shas, sort_keys=True))):
            raise ValueError("import response bundle differs from published bytes")
    elif response_kind == "FILE_BYTES":
        response, artifact = read_json(index["response_file"])
        artifacts.append(artifact)
        if artifact["sha256"] != report["response_sha256"]:
            raise ValueError("import response file SHA differs")
        response = indexed(response, key, "import response file")
        exact_keys(response, sources, "import response file")
        if any(sha_value(response[i]) != sha_value(published[i]) for i in sources):
            raise ValueError("import response file differs from published objects")
    else:
        raise ValueError("supported explicit importer response identity required")
    return published, receipts


def build_bundle(packet_path, import_directory, publications_path):
    """Convert existing importer V5 artifacts; never read CANONICAL/source cache."""
    packet, packet_artifact = read_json(packet_path)
    directory = local_path(import_directory)
    report, report_artifact = read_json(directory / "report.json")
    index, index_artifact = read_json(publications_path)
    artifacts = [packet_artifact, report_artifact, index_artifact]
    if (report.get("schema") != "P106B_TEXT_WORK_IMPORT_V5"
            or report.get("kind") not in ("sft", "native")
            or report.get("training_admission") != "NOT_ADMITTED"
            or report.get("semantic_review") != "PENDING"):
        raise ValueError("existing V5 NOT_ADMITTED import report required")
    kind = report["kind"]
    schemas = (("P106B_LUNA_SFT_TEXT_PACKET_V3",) if kind == "sft" else
               ("P106B_NATIVE_REVIEW_TEXT_PACKET_V2", "P106B_NATIVE_REVIEW_TEXT_PACKET_V5"))
    if packet.get("schema") not in schemas or packet.get("training_admission") != "NOT_ADMITTED":
        raise ValueError("supported sealed NOT_ADMITTED parent packet required")
    if report.get("packet_sha256") != packet_artifact["sha256"]:
        raise ValueError("import parent packet SHA differs; a child is not full parent coverage")
    sha_string(report.get("response_sha256"))
    key, collection = ("source_index", "sources") if kind == "sft" else ("id", "documents")
    sources = indexed(packet.get(collection), key, "parent packet")
    if not sources or type(report.get("source_rows")) is not int or report["source_rows"] != len(sources):
        raise ValueError("import parent source count/coverage differs")
    published, receipts = publication_rows(packet, packet_artifact, report, index, artifacts)
    count = report.get("output_rows")
    if type(count) is not int or count < 0:
        raise ValueError("explicit nonnegative import output count required")
    rows = import_rows(directory, "authoring" if kind == "sft" else "review", report, artifacts) if count else []
    if len(rows) != count:
        raise ValueError("import output row count differs")
    triage_count = report.get("triage_only_source_rows", 0)
    if type(triage_count) is not int or triage_count < 0 or (kind != "sft" and triage_count):
        raise ValueError("invalid triage-only count")
    triage = import_rows(directory, "triage", report, artifacts) if triage_count else []
    if len(triage) != triage_count:
        raise ValueError("triage row count differs")
    by_source = defaultdict(list)
    for row in rows:
        source_id = ident(row.get(key) if kind == "sft" else row.get("source", {}).get("id"))
        by_source[source_id].append(row)
    triaged = indexed(triage, "source_index", "triage-only import")
    if set(by_source) & set(triaged):
        raise ValueError("source has both variants and triage-only rows")
    exact_keys(set(by_source) | set(triaged), sources, "import parent source IDs")
    expected_held = {i for i, row in published.items() if
                     (row.get("triage_reason") if kind == "sft" else row.get("decision") == "HOLD")}
    held = report.get("held_source_ids")
    if not isinstance(held, list) or len(held) != len(set(held)) or set(held) != expected_held:
        raise ValueError("import held-source history differs")
    candidates, source_table = [], []
    for source_id, source in sorted(sources.items()):
        if kind == "sft":
            source_sha = sha_string(source.get("source_line_sha256"))
            root_id = text(source.get("root_id"), "sealed source root_id")
            source_split = source.get("source_split")
            if source_split not in SPLITS:
                raise ValueError("sealed SFT source split required")
            original = [dict(role=m["role"], content=batches.plain_content(m["content"]))
                        for m in source["messages"]]
            original_identity = sha_value(original)
        else:
            source_sha = sha_string(source.get("sha256"))
            root_id = source.get("root_id", "native:" + source_sha)
            text(root_id, "native root_id")
            source_split = source.get("source_split", packet.get("source_split"))
            if source_split is not None and source_split not in SPLITS:
                raise ValueError("declared native source split invalid")
            original_identity = source_sha
        source_table.append(dict(source_id=source_id, root_id=root_id, source_sha256=source_sha,
            source_object_sha256=sha_value(source), source_split=source_split,
            original_identity=original_identity, source_metadata=source.get("meta", {}),
            published_receipt_sha256=receipts[source_id], author_hold=source_id in expected_held,
            triage_only=source_id in triaged))
        if source_id in triaged:
            row = triaged[source_id]
            if (published[source_id].get("variants") != []
                    or row.get("classification") != "NOT_AUTHORED_TRIAGE_ONLY"
                    or row.get("training_admission") != "NOT_ADMITTED"
                    or row.get("source_line_sha256") != source_sha
                    or row.get("root_id") != root_id or row.get("original_messages") != original
                    or row.get("source_metadata") != source.get("meta", {})):
                raise ValueError("triage-only imported source identity differs")
            continue
        authored = by_source[source_id]
        if kind == "sft":
            variants = {v["kind"]: batches.validate_variant_conversation(original, v)
                        for v in published[source_id]["variants"]}
            if (len(authored) != 3 or {r.get("variant_kind") for r in authored} != set(batches.KINDS)):
                raise ValueError("SFT import requires exact three-variant coverage")
            for row in authored:
                if (row.get("source_id") != source["source_id"] or row.get("root_id") != root_id
                        or row.get("source_line_sha256") != source_sha
                        or row.get("source_split") != source_split
                        or row.get("original_messages") != original
                        or row.get("source_metadata") != source.get("meta", {})
                        or row.get("messages") != variants[row["variant_kind"]]
                        or row.get("training_admission") != "NOT_ADMITTED"):
                    raise ValueError("SFT import row differs from sealed/published source")
                payload = dict(messages=row["messages"])
                candidates.append(dict(candidate_id="sft:" + str(source_id) + ":" + row["variant_kind"],
                    source_id=source_id, root_id=root_id, objective="ASSISTANT_SFT", payload=payload,
                    imported_row_sha256=sha_value(row), payload_sha256=sha_value(payload),
                    source_sha256=source_sha, published_receipt_sha256=receipts[source_id]))
        else:
            if len(authored) != 1:
                raise ValueError("native import requires exactly one row per source")
            row = authored[0]
            published_row = published[source_id]
            if packet.get("edit_contract") == batches.LINE_EDIT_CONTRACT:
                proposed, ranges = batches.apply_positioned_edits(source["text"], published_row["changes"])
                draft = dict(published_row, root_resolved_source_ranges=ranges)
            else:
                proposed = batches.apply_spans(source["text"], published_row["changes"])
                draft = dict(published_row)
            draft.update(proposed_text=proposed, reconstructed_from_exact_spans=True)
            if (row.get("source") != source or row.get("draft") != draft
                    or row.get("training_admission") != "NOT_ADMITTED"):
                raise ValueError("native import row differs from sealed/published positioned edits")
            payload = dict(text=draft["proposed_text"])
            candidates.append(dict(candidate_id="native:" + str(source_id), source_id=source_id,
                root_id=root_id, objective="NATIVE_NTP", payload=payload,
                imported_row_sha256=sha_value(row), payload_sha256=sha_value(payload),
                source_sha256=source_sha, published_receipt_sha256=receipts[source_id]))
    for candidate in candidates:
        candidate["candidate_sha256"] = sha_value(candidate)
    if kind == "sft":
        if (sorted(report.get("triage_only_source_ids", [])) != sorted(triaged)
                or report.get("authored_source_rows") != len(by_source)):
            raise ValueError("SFT report authored/triage coverage differs")
    # Detect artifacts replaced during conversion before any frozen file exists.
    for artifact in artifacts:
        if read_artifact(artifact["path"])[1] != artifact:
            raise ValueError("artifact changed while freezing import")
    return dict(schema=BUNDLE_SCHEMA, training_admission="NOT_ADMITTED", kind=kind,
        parent_packet_sha256=packet_artifact["sha256"], import_receipt_sha256=report_artifact["sha256"],
        recipe=dict(packet=str(local_path(packet_path)), import_directory=str(directory),
                    publications=str(local_path(publications_path))),
        source_ids=sorted(sources), sources=source_table,
        candidates=sorted(candidates, key=lambda row: row["candidate_id"]),
        artifacts=artifacts, code_sha256=source_code_hashes())


def freeze(packet, import_directory, publications, output):
    result = build_bundle(packet, import_directory, publications)
    artifact = exclusive_json(output, result)
    return dict(schema=BUNDLE_SCHEMA, bundle=artifact, source_rows=len(result["sources"]),
                candidate_rows=len(result["candidates"]), training_admission="NOT_ADMITTED")


def checked_bundle(path):
    bundle, artifact = read_json(path)
    if bundle.get("schema") != BUNDLE_SCHEMA or bundle.get("training_admission") != "NOT_ADMITTED":
        raise ValueError("frozen NOT_ADMITTED bundle required")
    recipe = bundle["recipe"]
    rebuilt = build_bundle(recipe["packet"], recipe["import_directory"], recipe["publications"])
    if sha_value(bundle) != sha_value(rebuilt):
        raise ValueError("frozen bundle is stale or differs from actual importer/publication artifacts")
    return bundle, artifact


def train_reuse_evidence(document, bundle):
    """Bind record-level TRAIN reuse without inventing upstream article IDs."""
    if (document.get("identity_scope") != "SOURCE_RECORD_TRAIN_ONLY"
            or document.get("global_document_overlap") != "UNVERIFIED"
            or document.get("source_document_identity") != "MISSING"):
        raise ValueError("TRAIN reuse requires explicit record-only/unknown document limits")
    spec = document.get("train_exposure_readback", {})
    readback, artifact = read_json(spec.get("path"))
    if artifact["sha256"] != sha_string(spec.get("sha256")):
        raise ValueError("historical TRAIN readback SHA differs")
    events = readback.get("actual_step_events")
    if (type(events) is not int or events <= 0
            or readback.get("exact_source_id_messages_license_revision_matching") is not True):
        raise ValueError("actual matched TRAIN execution evidence required")
    matches = indexed(readback.get("matched_sources"), "canonical_source_index", "historical TRAIN sources")
    for source in bundle["sources"]:
        match = matches.get(source["source_id"], {})
        if (source["source_split"] != "train" or match.get("current_root") != source["root_id"]
                or sha_string(match.get("canonical_source_line_sha256")) != source["source_sha256"]):
            raise ValueError("source record/root differs from actual TRAIN readback")
        text(match.get("past_root"), "historical TRAIN root")
        sha_string(match.get("record_sha256"))
    return artifact


def root_assignments(document, bundle):
    reuse = document.get("schema") == TRAIN_REUSE_SCHEMA
    if (document.get("schema") not in (SPLITS_SCHEMA, TRAIN_REUSE_SCHEMA)
            or sha_string(document.get("parent_packet_sha256")) != bundle["parent_packet_sha256"]):
        raise ValueError("root split ledger parent/schema differs")
    text(document.get("split_policy_reference"), "existing split policy reference")
    if reuse:
        train_reuse_evidence(document, bundle)
    wanted = defaultdict(dict)
    for source in bundle["sources"]:
        wanted[source["root_id"]][source["source_id"]] = source
    roots = {}
    for row in document.get("roots", []):
        root_id = text(row.get("root_id"), "root ledger root_id")
        if root_id in roots or row.get("split") not in SPLITS:
            raise ValueError("duplicate root or unknown supplied split")
        roots[root_id] = row
    exact_keys(roots, wanted, "root assignments")
    identity_splits, source_splits, group_splits, document_splits = {}, {}, {}, {}
    for root_id, root in roots.items():
        group_id = text(root.get("group_id"), "explicit source group_id")
        if reuse and root["split"] != "train":
            raise ValueError("record-only TRAIN reuse cannot create evaluation splits")
        if group_id in group_splits and group_splits[group_id] != root["split"]:
            raise ValueError("same source-document group leaks across root splits")
        group_splits[group_id] = root["split"]
        history = indexed(root.get("source_history"), "source_id", "root source history")
        exact_keys(history, wanted[root_id], "root source history")
        for source_id, source in wanted[root_id].items():
            entry = history[source_id]
            if sha_string(entry.get("source_sha256")) != source["source_sha256"]:
                raise ValueError("source history SHA differs")
            declared = entry.get("source_split")
            if declared not in SPLITS or (source["source_split"] is not None and declared != source["source_split"]):
                raise ValueError("source split/exposure history absent or differs")
            prior = entry.get("prior_exposure_splits")
            if (not isinstance(prior, list) or len(prior) != len(set(prior))
                    or any(split not in SPLITS for split in prior)):
                raise ValueError("explicit source prior-exposure split history required")
            text(entry.get("evidence"), "source exposure evidence")
            if reuse:
                if (declared != "train" or prior != ["train"]
                        or entry.get("source_document_id", "absent") is not None
                        or sha_string(entry.get("source_record_sha256")) != source["source_object_sha256"]):
                    raise ValueError("TRAIN reuse record identity/exposure contract differs")
                document_id = "source-record:" + source["source_object_sha256"]
            else:
                document_id = text(entry.get("source_document_id"), "source document lineage identity")
            if document_id in document_splits and document_splits[document_id] != root["split"]:
                raise ValueError("same original document leaks across root splits")
            document_splits[document_id] = root["split"]
            exposures = set(prior)
            if "train" in exposures and root["split"] != "train":
                raise ValueError("TRAIN-exposed source cannot be held out")
            if (declared in ("val", "test") or exposures & {"val", "test"}) and root["split"] == "train":
                raise ValueError("evaluation source cannot enter train")
            for mapping, identity in ((identity_splits, source["original_identity"]),
                                      (source_splits, source["source_sha256"])):
                if identity in mapping and mapping[identity] != root["split"]:
                    raise ValueError("same original/root source leaks across splits")
                mapping[identity] = root["split"]
    return roots


def reviewed_candidates(document, bundle, bundle_sha256):
    if (document.get("schema") != REVIEWS_SCHEMA
            or sha_string(document.get("parent_packet_sha256")) != bundle["parent_packet_sha256"]
            or sha_string(document.get("bundle_sha256")) != bundle_sha256):
        raise ValueError("review parent/bundle SHA differs")
    decisions = {}
    for row in document.get("decisions", []):
        key = text(row.get("candidate_id"), "review candidate_id")
        if key in decisions:
            raise ValueError("duplicate review candidate ID")
        decisions[key] = row
    wanted = {row["candidate_id"]: row for row in bundle["candidates"]}
    exact_keys(decisions, wanted, "per-candidate reviews")
    sources = {source["source_id"]: source for source in bundle["sources"]}
    for key, row in decisions.items():
        candidate = wanted[key]
        if sha_string(row.get("candidate_sha256")) != candidate["candidate_sha256"]:
            raise ValueError("review candidate SHA is stale")
        if row.get("decision") not in VERDICTS:
            raise ValueError("explicit ACCEPT/HOLD/REJECT decision required")
        reviews = row.get("reviews")
        if not isinstance(reviews, dict) or set(reviews) != set(DIMENSIONS):
            raise ValueError("all five explicit review dimensions required")
        for dimension in DIMENSIONS:
            review = reviews[dimension]
            if not isinstance(review, dict) or review.get("decision") not in VERDICTS:
                raise ValueError("explicit review dimension verdict required")
            text(review.get("reviewer"), dimension + " reviewer")
            text(review.get("reason"), dimension + " review reason")
            evidence = review.get("evidence")
            if (not isinstance(evidence, dict)
                    or sha_string(evidence.get("source_sha256")) != candidate["source_sha256"]):
                raise ValueError("review contextual evidence source SHA absent/differs")
            text(evidence.get("reference"), dimension + " source-context evidence reference")
            text(evidence.get("context"), dimension + " source-context evidence")
        if row["decision"] != "ACCEPT":
            continue
        if any(review["decision"] != "ACCEPT" for review in reviews.values()):
            raise ValueError("ACCEPT request contains HOLD/REJECT review dimension")
        source = sources[candidate["source_id"]]
        # An author hold is history, not an immutable semantic veto. Overriding
        # it requires a new, explicit rationale bound to this candidate SHA.
        if source["author_hold"]:
            text(row.get("author_hold_resolution"), "explicit author HOLD resolution")
        turns = row.get("supervised_assistant_turns")
        if candidate["objective"] == "NATIVE_NTP":
            if turns != []:
                raise ValueError("native NTP requires explicit empty assistant turn list")
        else:
            total = sum(m["role"] == "assistant" for m in candidate["payload"]["messages"])
            if (not isinstance(turns, list) or not turns or len(turns) != len(set(turns))
                    or any(type(turn) is not int or not 1 <= turn <= total for turn in turns)):
                raise ValueError("explicit nonempty valid supervised assistant turns required")
            inherited = source["source_metadata"].get("supervised_assistant_turns")
            if inherited is not None and not set(turns) <= set(inherited):
                raise ValueError("review cannot broaden inherited source supervision allowlist")
    return decisions


def encoding_contract(path, bundle):
    contract, artifact = read_json(path)
    if (contract.get("schema") != ENCODING_SCHEMA or contract.get("template") != "chatml"
            or type(contract.get("context")) is not int or contract["context"] < 1):
        raise ValueError("fixed ChatML template and positive integer context required")
    tokenizer = contract.get("tokenizer", {})
    _, tokenizer_artifact = read_artifact(tokenizer["path"])
    if sha_string(tokenizer.get("sha256")) != tokenizer_artifact["sha256"]:
        raise ValueError("fixed tokenizer SHA differs")
    if bundle["kind"] == "native":
        eos = contract.get("native_eos", {})
        if (eos.get("policy") not in ("APPEND_ONE", "ALREADY_PRESENT")
                or type(eos.get("id")) is not int or eos["id"] < 0):
            raise ValueError("explicit native EOS policy/id required")
        text(eos.get("token"), "native EOS token")
    return contract, artifact, tokenizer_artifact


def load_tokenizer(path):
    import tinylm  # owns local dependency/cache routing; no model is loaded
    from tokenizers import Tokenizer
    return Tokenizer.from_file(str(path))


def encode_candidate(candidate, decision, source, contract, tokenizer):
    """Use existing shifted SFT encoding; masking never alters conversation."""
    if candidate["objective"] == "ASSISTANT_SFT":
        from tinylm.train.mtp_sft import Record, count_record, encode_record
        from tinylm.data.sft import IGNORE
        canonical = dict(messages=candidate["payload"]["messages"],
                         meta=dict(source["source_metadata"]))
        kind = candidate["candidate_id"].rsplit(":", 1)[-1]
        if kind not in batches.KINDS:
            raise ValueError("unknown declared SFT variant kind")
        if "language" in canonical["meta"]:
            canonical["meta"]["source_language"] = canonical["meta"]["language"]
        canonical["meta"].update(variant_kind=kind, language=kind.split("_", 1)[0])
        canonical["meta"]["supervised_assistant_turns"] = decision["supervised_assistant_turns"]
        original = encode_record(canonical, tokenizer, context=contract["context"])
        allowed = set(decision["supervised_assistant_turns"])
        y = [value if segment in allowed else IGNORE for value, segment in zip(original.y, original.segments)]
        segments = [segment if segment in allowed else 0 for segment in original.segments]
        record = Record(original.x, y, segments)
        if not record.targets or set(s for s in segments if s) != allowed:
            raise ValueError("reviewed assistant turn has no actual tokenizer targets")
        return dict(canonical=canonical, x=record.x, y=record.y, segments=record.segments,
                    input_tokens=record.x_tokens, assistant_target_tokens=record.targets,
                    ntp_target_tokens=0, mtp_target_tokens={str(k): v for k, v in count_record(record).items()})
    content = candidate["payload"]["text"]
    text(content, "native content")
    ids = list(tokenizer.encode(content).ids)
    eos = contract["native_eos"]
    if tokenizer.token_to_id(eos["token"]) != eos["id"]:
        raise ValueError("native EOS token/id differs from fixed tokenizer")
    if eos["policy"] == "APPEND_ONE":
        if ids and ids[-1] == eos["id"]:
            raise ValueError("native already ends in EOS; APPEND_ONE would duplicate it")
        ids.append(eos["id"])
    elif not ids or ids[-1] != eos["id"]:
        raise ValueError("native ALREADY_PRESENT EOS is absent")
    if not 1 < len(ids) <= contract["context"] + 1:
        raise ValueError("native context contract; no automatic truncation/chunking")
    return dict(text=content, x=ids[:-1], y=ids[1:], input_tokens=len(ids)-1,
                assistant_target_tokens=0, ntp_target_tokens=len(ids)-1)


def prepare(bundle_path, reviews_path, splits_path, contract_path, output, *, synthetic_tokenizer=None):
    output = local_path(output)
    if output.exists():
        raise FileExistsError("exclusive admission output already exists")
    if not output.parent.is_dir():
        raise ValueError("explicit existing output parent required")
    bundle, bundle_artifact = checked_bundle(bundle_path)
    reviews, reviews_artifact = read_json(reviews_path)
    splits, splits_artifact = read_json(splits_path)
    roots = root_assignments(splits, bundle)
    split_contract = dict(split_ledger_schema=splits["schema"])
    if splits["schema"] == TRAIN_REUSE_SCHEMA:
        split_contract.update(identity_scope=splits["identity_scope"],
            global_document_overlap=splits["global_document_overlap"],
            source_document_identity=splits["source_document_identity"])
    decisions = reviewed_candidates(reviews, bundle, bundle_artifact["sha256"])
    contract, contract_artifact, tokenizer_artifact = encoding_contract(contract_path, bundle)
    tokenizer = synthetic_tokenizer if synthetic_tokenizer is not None else load_tokenizer(tokenizer_artifact["path"])
    if getattr(tokenizer, "truncation", None) is not None:
        raise ValueError("tokenizer truncation is enabled; disable explicitly before freezing tokenizer")
    if getattr(tokenizer, "padding", None) is not None:
        raise ValueError("tokenizer padding is enabled; raw record counts must be fixed")
    sources = {row["source_id"]: row for row in bundle["sources"]}
    grouped = defaultdict(list)
    totals = Counter()
    accepted_ids, excluded, payload_splits = [], [], {}
    mode = "SYNTHETIC_ONLY_NOT_ADMITTED" if synthetic_tokenizer is not None else "READY_BY_EXPLICIT_REVIEW"
    for candidate in bundle["candidates"]:
        decision = decisions[candidate["candidate_id"]]
        if decision["decision"] != "ACCEPT":
            excluded.append(dict(candidate_id=candidate["candidate_id"], candidate_sha256=candidate["candidate_sha256"],
                                 decision=decision["decision"], review=decision))
            continue
        source = sources[candidate["source_id"]]
        root = roots[candidate["root_id"]]
        payload_sha = candidate["payload_sha256"]
        if payload_sha in payload_splits and payload_splits[payload_sha] != root["split"]:
            raise ValueError("exact duplicate candidate payload leaks across splits")
        payload_splits[payload_sha] = root["split"]
        encoded = encode_candidate(candidate, decision, source, contract, tokenizer)
        if any(type(value) is not int or value < 0 for value in encoded["x"]):
            raise ValueError("tokenizer input IDs must be nonnegative integers")
        if any(type(value) is not int or (value < 0 and value != -100) for value in encoded["y"]):
            raise ValueError("tokenizer labels must be integer IDs or the existing ignore index")
        if len(encoded["x"]) != len(encoded["y"]) or len(encoded["x"]) > contract["context"]:
            raise ValueError("shifted token shape/context differs")
        row = dict(schema="P106B_ADMISSION_TOKEN_RECORD_V1", **encoded,
            candidate_id=candidate["candidate_id"], candidate_sha256=candidate["candidate_sha256"],
            root_id=candidate["root_id"], source_id=candidate["source_id"], source_sha256=source["source_sha256"],
            source_split=source["source_split"],
            original_identity=source["original_identity"], source_history=root["source_history"],
            author_hold=source["author_hold"], objective=candidate["objective"], split=root["split"],
            parent_packet_sha256=bundle["parent_packet_sha256"], import_receipt_sha256=bundle["import_receipt_sha256"],
            published_receipt_sha256=candidate["published_receipt_sha256"],
            imported_row_sha256=candidate["imported_row_sha256"], review_sha256=reviews_artifact["sha256"],
            tokenizer_sha256=tokenizer_artifact["sha256"], training_admission=mode,
            admission_review=decision)
        if "canonical" in row:
            row["canonical"]["meta"]["training_admission"] = mode
        # Preflight every serialized row before claiming the new namespace.
        if len((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()) > LIMIT:
            raise ValueError("one token record exceeds below20MB shard contract")
        grouped[(candidate["objective"], root["split"])].append(row)
        accepted_ids.append(candidate["candidate_id"])
        totals.update({key: encoded[key] for key in ("input_tokens", "assistant_target_tokens", "ntp_target_tokens")})
    if not accepted_ids:
        raise ValueError("zero accepted candidates; training corpus was not created")
    inputs = [bundle_artifact, reviews_artifact, splits_artifact, contract_artifact, tokenizer_artifact, *bundle["artifacts"]]
    if splits["schema"] == TRAIN_REUSE_SCHEMA:
        inputs.append(train_reuse_evidence(splits, bundle))
    for artifact in inputs:
        if read_artifact(artifact["path"])[1] != artifact:
            raise ValueError("input changed during preparation")
    if source_code_hashes() != bundle["code_sha256"]:
        raise ValueError("admission/encoder code changed after freeze")
    lineage = dict(parent_packet_sha256=bundle["parent_packet_sha256"], bundle_sha256=bundle_artifact["sha256"],
        reviews_sha256=reviews_artifact["sha256"], root_splits_sha256=splits_artifact["sha256"],
        encoding_contract_sha256=contract_artifact["sha256"], tokenizer_sha256=tokenizer_artifact["sha256"],
        template=contract["template"], context=contract["context"], training_admission=mode, **split_contract)
    output.mkdir(exist_ok=False)
    corpora = []
    for (objective, split), records in sorted(grouped.items()):
        stem = ("sft_" if objective == "ASSISTANT_SFT" else "native_ntp_") + split
        writer = ShardWriter(output, stem, limit=LIMIT)
        for row in records:
            writer.append(row)
        manifest = writer.close(lineage=dict(lineage, objective=objective, split=split))
        verify_shards(output, manifest)
        _, artifact = read_artifact(output / (stem + "_shards_manifest.json"))
        corpora.append(dict(stem=stem, objective=objective, split=split, manifest_sha256=artifact["sha256"], manifest=manifest))
    for artifact in inputs:
        if read_artifact(artifact["path"])[1] != artifact:
            raise ValueError("input changed while writing; incomplete output preserved without completion manifest")
    if source_code_hashes() != bundle["code_sha256"]:
        raise ValueError("source code changed while writing; incomplete output preserved")
    manifest = dict(schema=MANIFEST_SCHEMA, **lineage, inputs=inputs,
        code_sha256=bundle["code_sha256"], roots=splits["roots"],
        native_eos=contract.get("native_eos") if bundle["kind"] == "native" else None,
        split_policy_reference=splits["split_policy_reference"], source_ids=bundle["source_ids"],
        triage_only_source_ids=[row["source_id"] for row in bundle["sources"] if row["triage_only"]],
        accepted_candidate_ids=accepted_ids, excluded=excluded, accepted_rows=len(accepted_ids),
        total_candidates=len(bundle["candidates"]), counts=dict(totals), corpora=corpora,
        model_calls=0, training_runs=0, automatic_semantic_reviews=0, truncations=0,
        limitation="Explicit review assertions, not independent semantic/rights or model-quality verification; no trainer/corpus merge.")
    artifact = exclusive_json(output / "admission_manifest.json", manifest)
    verify_admission(output, artifact["sha256"])
    return dict(manifest=artifact, training_admission=mode, accepted_rows=len(accepted_ids),
                excluded_rows=len(excluded), counts=dict(totals), model_calls=0, training_runs=0)


def verify_admission(output, manifest_sha256):
    """Verify a pinned completion manifest and all exact writer-produced shards."""
    output = local_path(output)
    manifest, artifact = read_json(output / "admission_manifest.json")
    if artifact["sha256"] != sha_string(manifest_sha256) or manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("admission manifest SHA/schema differs")
    if manifest.get("training_admission") not in ("READY_BY_EXPLICIT_REVIEW", "SYNTHETIC_ONLY_NOT_ADMITTED"):
        raise ValueError("unknown admission completion state")
    train_reuse = manifest.get("split_ledger_schema") == TRAIN_REUSE_SCHEMA
    if train_reuse and (manifest.get("identity_scope") != "SOURCE_RECORD_TRAIN_ONLY"
            or manifest.get("global_document_overlap") != "UNVERIFIED"
            or manifest.get("source_document_identity") != "MISSING"
            or any(root["split"] != "train" for root in manifest["roots"])):
        raise ValueError("TRAIN reuse output lost record-only/unknown document limits")
    expected = manifest["accepted_candidate_ids"]
    if not expected or len(expected) != len(set(expected)):
        raise ValueError("nonempty unique admitted candidate IDs required")
    seen, counts, identities = [], Counter(), {}
    excluded = {row["candidate_id"] for row in manifest["excluded"]}
    for corpus in manifest["corpora"]:
        if train_reuse and corpus["split"] != "train":
            raise ValueError("TRAIN reuse output cannot contain evaluation data")
        stem = corpus["stem"]
        if (not isinstance(stem, str) or Path(stem).name != stem
                or not stem.isascii() or not stem.replace("_", "").isalnum()):
            raise ValueError("unsafe output shard manifest name")
        stored, stored_artifact = read_json(output / (stem + "_shards_manifest.json"))
        if stored_artifact["sha256"] != corpus["manifest_sha256"] or stored != corpus["manifest"]:
            raise ValueError("output shard manifest SHA differs")
        for spec in stored.get("shards", []):
            local_path(output / spec["path"])
        verify_shards(output, stored)
        for spec in stored["shards"]:
            raw, shard_artifact = read_artifact(output / spec["path"])
            if (shard_artifact["sha256"] != spec["sha256"]
                    or shard_artifact["bytes"] != spec["bytes"]):
                raise ValueError("admission shard changed after verification")
            for line in raw.splitlines():
                row = publication.parse(line)
                key = row["candidate_id"]
                if key in excluded or row["split"] != corpus["split"] or row["objective"] != corpus["objective"]:
                    raise ValueError("excluded candidate or objective/root split differs")
                if (len(row["x"]) != row["input_tokens"] or len(row["y"]) != len(row["x"])
                        or len(row["x"]) > manifest["context"]):
                    raise ValueError("output shifted token/context contract differs")
                if row["objective"] == "ASSISTANT_SFT":
                    actual = sum(token != -100 for token in row["y"])
                    segments = row.get("segments")
                    if (not isinstance(segments, list) or len(segments) != len(row["x"])
                            or any(type(segment) is not int or segment < 0 for segment in segments)
                            or any((token != -100) != (segment > 0) for token, segment in zip(row["y"], segments))
                            or actual != row["assistant_target_tokens"] or row["ntp_target_tokens"] != 0):
                        raise ValueError("assistant target count differs")
                elif row["objective"] == "NATIVE_NTP":
                    if row["assistant_target_tokens"] != 0 or row["ntp_target_tokens"] != len(row["y"]):
                        raise ValueError("native NTP was mixed with assistant targets")
                else:
                    raise ValueError("unknown output objective")
                for identity in (row["root_id"], row["original_identity"], row["source_sha256"]):
                    if identity in identities and identities[identity] != row["split"]:
                        raise ValueError("output source/root leaks across splits")
                    identities[identity] = row["split"]
                seen.append(key)
                counts.update({name: row[name] for name in ("input_tokens", "assistant_target_tokens", "ntp_target_tokens")})
    if (len(seen) != len(set(seen)) or set(seen) != set(expected)
            or len(seen) != manifest["accepted_rows"] or dict(counts) != manifest["counts"]):
        raise ValueError("admission output exact candidate/count coverage differs")
    return dict(verified_rows=len(seen), training_admission=manifest["training_admission"], manifest_sha256=artifact["sha256"])


def iter_sft_records(output, manifest_sha256, *, split="train", allow_synthetic=False):
    """A narrow reader for existing Record consumers, with no trainer/model."""
    if split not in SPLITS:
        raise ValueError("explicit train/val/test record split required")
    output = local_path(output)
    verified = verify_admission(output, manifest_sha256)
    if verified["training_admission"] == "SYNTHETIC_ONLY_NOT_ADMITTED" and not allow_synthetic:
        raise ValueError("synthetic output is not admitted to a training consumer")
    manifest, artifact = read_json(output / "admission_manifest.json")
    if artifact["sha256"] != sha_string(manifest_sha256):
        raise ValueError("admission manifest changed after verification")
    from tinylm.train.mtp_sft import Record
    emitted = 0
    for corpus in manifest["corpora"]:
        if corpus["objective"] != "ASSISTANT_SFT" or corpus["split"] != split:
            continue
        for spec in corpus["manifest"]["shards"]:
            raw, artifact = read_artifact(output / spec["path"])
            if artifact["sha256"] != spec["sha256"] or artifact["bytes"] != spec["bytes"]:
                raise ValueError("SFT shard changed after verification")
            for line in raw.splitlines():
                row = publication.parse(line)
                emitted += 1
                yield row, Record(row["x"], row["y"], row["segments"])
    if not emitted:
        raise ValueError("no admitted SFT records for requested objective/split")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    frozen = sub.add_parser("freeze", help="adapt a full existing import and explicit publication receipts")
    frozen.add_argument("--packet", required=True)
    frozen.add_argument("--import-directory", required=True)
    frozen.add_argument("--publications", required=True)
    frozen.add_argument("--output", required=True)
    prepared = sub.add_parser("prepare", help="apply explicit reviews/root ledger and fixed tokenizer on CPU")
    prepared.add_argument("--bundle", required=True)
    prepared.add_argument("--reviews", required=True)
    prepared.add_argument("--root-splits", required=True)
    prepared.add_argument("--encoding-contract", required=True)
    prepared.add_argument("--output", required=True)
    verified = sub.add_parser("verify", help="verify an externally pinned new admission manifest")
    verified.add_argument("--output", required=True)
    verified.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            result = freeze(args.packet, args.import_directory, args.publications, args.output)
        elif args.command == "prepare":
            result = prepare(args.bundle, args.reviews, args.root_splits, args.encoding_contract, args.output)
        else:
            result = verify_admission(args.output, args.manifest_sha256)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("[ADMISSION_ERROR] " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 9
    print("[ADMISSION] " + json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
