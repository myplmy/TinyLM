#!/usr/bin/env python3
"""Versioned adapter for resolving the current cache's remaining HOLD.

Reuse the frozen corpus builder and independent full consumer. Preserve every
previously admitted body and exclusion, use only a fully approved residual
roster, and represent a genuinely empty HOLD manifest without a dummy document.
No original stream, old rule or previous cache is modified.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import p106b_hold_cache as engine
from scripts import p106b_hold_revision as prior
from scripts import p106b_hold_resolution_inventory as inventory

BASE = inventory.BASE
PARENT = inventory.PARENT
PREVIOUS_ADOPTIONS = ROOT / "handoff/audit/hold_recovery_20261026_goalc/root_adoptions_v3.json"
SCHEMA = "P106B_RESIDUAL_HOLD_RESOLUTIONS_V1"
RULES = "RESIDUAL_HOLD_ROOT_REVIEWED_ROSTER_V1"
EXTRA_CODE = prior.EXTRA_CODE + ["scripts/p106b_hold_resolution_inventory.py",
                                "scripts/p106b_hold_resolution_cache.py",
                                "scripts/p106b_hold_resolution_policy.py",
                                "scripts/p106b_hold_resolution_proposals.py"]
OriginalEngine = engine.RecoveryEngine
OriginalIndex = engine.ParentIndex
OriginalWriter = engine.cache.ShardWriter
require = engine.require


class LatestIndex(OriginalIndex):
    """Reuse the original index interface with the verified current parent."""

    def __init__(self, base):
        self.base = base
        self.old = PARENT
        self.scope = engine.cache.read(base / "scope.json")
        self.report = engine.cache.read(self.old / "built.json")
        require(engine.file_sha(base / "scope.json") == self.report["lineage"]["scope_sha256"], "latest parent scope differs")
        proof = engine.cache.read(self.old / "recovery_verified.json")
        require(proof.get("status") == "CPU_FULL_RECOVERY_CACHE_VERIFIED"
                and proof["built_sha256"] == engine.file_sha(self.old / "built.json")
                and proof["core_verified_sha256"] == engine.file_sha(self.old / "verified.json"), "latest parent proof differs")
        code_root = Path(__file__).resolve().parents[1]
        for name, digest in self.report["source_code_sha256"].items():
            require(engine.file_sha(code_root / name) == digest, "latest parent's frozen code differs")
        engine.cache.verify(self.old / "ledger", self.report["manifests"]["ledger"])
        self.states = {s["name"]: bytearray(s["intervals"]) for s in self.scope["inputs"]}
        self.clean = {s["name"]: bytearray(s["intervals"] * 32) for s in self.scope["inputs"]}
        self.owners = {"train": {}, "val": {}}
        self.duplicates = {}
        self.overlaps = {}
        self.counts = Counter()
        for row in engine.cache.rows(self.old / "ledger", self.report["manifests"]["ledger"]):
            source = row["source"]
            ordinal = int(row["id"].rsplit(":", 1)[1])
            require(self.states[source][ordinal] == 0, "latest parent repeats an ID")
            code = {"KEEP": 1, "EDIT": 2, "HOLD": 3, "EXCLUDE": 4}[row["decision"]]
            if code == 4 and row["reasons"] == ["TRAIN_VAL_CONTENT_OVERLAP"]:
                code = 5
            self.states[source][ordinal] = code
            self.counts.update([row["decision"]])
            if code in (1, 2):
                digest = bytes.fromhex(row["clean_text_sha256"])
                self.clean[source][ordinal * 32:(ordinal + 1) * 32] = digest
                require(digest not in self.owners[row["split"]], "latest parent has exact duplicates")
                self.owners[row["split"]][digest] = row["id"]
            if row.get("duplicate_of"):
                self.duplicates[row["id"]] = row["duplicate_of"]
            if row.get("validation_overlap"):
                self.overlaps[row["id"]] = row["validation_overlap"]
        require(all(0 not in value for value in self.states.values()), "latest parent has missing positions")
        require(all(self.counts[k] == self.report["counts"].get(k, 0) for k in ["KEEP", "EDIT", "HOLD", "EXCLUDE"]), "latest parent counts differ")


class EmptyHoldWriter(OriginalWriter):
    """Allow zero rows only for the explicitly named HOLD side of a new cache."""

    def close(self, *, lineage):
        if self._total_rows or self.directory.name != "hold" or self.stem != "positions":
            return super().close(lineage=lineage)
        require(not self.shards and self._file is None, "empty HOLD writer contains data")
        manifest = dict(schema="P106B_WRITE_ONCE_SHARDS_V1", limit_bytes=self.limit, rows=0,
                        bytes=0, concat_sha256=hashlib.sha256(b"").hexdigest().upper(),
                        lineage=lineage, shards=[])
        with self.manifest_path.open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write(chr(10))
        return manifest


def load_roster(path, index):
    document = engine.cache.read(path)
    require(document.get("schema") == SCHEMA
            and document.get("status") == "ROOT_REVIEWED_FULL_RESIDUAL_RESOLUTION"
            and document.get("unprocessed") == 0 and document.get("remaining_hold") == 0,
            "full approved residual resolution is required")
    require(document["parent_built_sha256"] == engine.file_sha(index.old / "built.json"), "resolution parent differs")
    directory = path.parent / document["records_directory"]
    require(directory.resolve().is_relative_to(path.parent.resolve()), "resolution records escape their version")
    engine.cache.verify(directory, document["manifest"])
    result = {}
    verified_evidence = {}
    for row in engine.cache.rows(directory, document["manifest"]):
        key = row["original_text_sha256"]
        require(key not in result and row["decision"] in ["KEEP", "EDIT", "EXCLUDE"], "duplicate or unresolved residual proposal")
        require(row.get("root_approved") is True and row.get("reason") and row.get("evidence"), "resolution lacks reviewed evidence")
        evidence = row["evidence"]
        require(isinstance(evidence, dict) and evidence.get("path") and evidence.get("sha256"), "resolution evidence must be hash-linked")
        evidence_path = ROOT / evidence["path"]
        allowed_evidence = [index.base / "agents", ROOT / "handoff/audit/hold_resolution_20261027_goalc"]
        require(any(evidence_path.resolve().is_relative_to(p.resolve()) for p in allowed_evidence), "resolution evidence escapes approved review paths")
        if evidence["path"] not in verified_evidence:
            verified_evidence[evidence["path"]] = engine.file_sha(evidence_path)
        require(verified_evidence[evidence["path"]] == evidence["sha256"], "reviewed resolution evidence changed")
        if row["decision"] == "EDIT":
            require(isinstance(row.get("text"), str) and row["text"].strip()
                    and engine.sha(row["text"]) == row["clean_text_sha256"]
                    and not engine.corpus.MEMOS.search(row["text"]), "resolution body differs or contains a review memo")
        elif row["decision"] == "KEEP":
            require(row["clean_text_sha256"] == key, "KEEP changes the original body")
        result[key] = row
    keys = set()
    counts = Counter()
    engine.cache.verify(index.old / "hold", index.report["manifests"]["hold"])
    for row in engine.cache.rows(index.old / "hold", index.report["manifests"]["hold"]):
        key = row["original_text_sha256"]
        require(key in result, "residual source has no actual resolution")
        keys.add(key)
        counts.update(documents=1, input_ids=row["input_ids"])
    require(keys == set(result), "resolution includes outside sources")
    require(dict(counts) == document["counts"] and counts["documents"] == index.counts["HOLD"], "full residual coverage differs")
    return document, result


class ResolutionEngine(OriginalEngine):
    def __init__(self, base, adoptions, roster):
        # Construct this before patching the public class/index bindings. The
        # old engine remains an independent reproducer of the previous bodies.
        self.baseline = OriginalEngine(inventory.PARENT_BASE, PREVIOUS_ADOPTIONS)
        self.base = base
        self.index = LatestIndex(base)
        self.roster_document, self.roster = load_roster(roster, self.index)
        self.roster_sha256 = engine.file_sha(roster)
        self.new_document, self.new_overrides = engine.cache.manual_overrides(base, adoptions)
        self.current = None
        self.extra = {}
        self.val_blocked = {}
        self.baseline_checked = 0
        self.recovered = Counter()

    def pick(self, row, overrides, known=False):
        state = self.index.state(row)
        self.current = (row, state)
        self.extra = {}
        if state in (1, 2):
            value = self.baseline.pick(row, self.baseline.new_overrides, known)
            require(value[0] in ("KEEP", "EDIT") and engine.sha(value[1]) == self.index.digest(row), "latest admitted body changed")
            return value
        if state in (4, 5):
            return "EXCLUDE", row["text"], ["TRAIN_VAL_CONTENT_OVERLAP" if state == 5 else "EXACT_CLEAN_TEXT_DUPLICATE"], None
        proposal = self.roster[row["original_text_sha256"]]
        decision = proposal["decision"]
        text = proposal["text"] if decision == "EDIT" else row["text"]
        require(decision not in ("KEEP", "EDIT") or engine.sha(text) == proposal["clean_text_sha256"], "resolution text changed")
        manual = proposal.get("manual")
        self.extra = dict(resolution_roster_sha256=self.roster_sha256,
                          resolution_evidence=proposal["evidence"])
        if decision in ("KEEP", "EDIT"):
            digest = bytes.fromhex(engine.sha(text))
            owner = self.index.owners[row["split"]].get(digest)
            if owner:
                self.extra["duplicate_of"] = owner
                return "EXCLUDE", text, ["EXACT_CLEAN_TEXT_DUPLICATE_WITH_PRESERVED_BASELINE"], manual
            if row["split"] == "val" and (digest in self.index.owners["train"] or row["id"] in self.val_blocked):
                self.extra["validation_overlap"] = self.val_blocked.get(row["id"], dict(kind="EXACT_PRESERVED_TRAIN_TEXT", id=self.index.owners["train"].get(digest)))
                return "EXCLUDE", text, ["RECOVERED_VALIDATION_CONFLICTS_WITH_PRESERVED_TRAIN"], manual
        return decision, text, [proposal["reason"]], manual

    def code_guard(self, original, cleaned, manual=None):
        if self.current[1] in (1, 2):
            return prior.reviewed_code_guard(self.baseline, original, cleaned, manual)
        return engine.policy.unicode_examples_preserved(original, cleaned) and engine.policy.code_preserved(original, cleaned)


@contextmanager
def revision(prepared=None):
    policy = SimpleNamespace(RULES=RULES, propose=prior.policy.propose,
                             code_preserved=prior.policy.code_preserved,
                             unicode_examples_preserved=prior.policy.unicode_examples_preserved)
    with prior.revision(), patch.object(engine, "policy", policy), patch.object(engine, "ParentIndex", LatestIndex), \
            patch.object(engine, "CODE_FILES", EXTRA_CODE), \
            patch.object(engine.cache, "ShardWriter", EmptyHoldWriter):
        if prepared is None:
            yield
        else:
            with patch.object(engine, "RecoveryEngine", lambda _base, _adoptions: prepared):
                yield


def build(base, adoptions, roster, output_name="cache_v1", proposal_name="proposals_v1"):
    require(not (base / output_name).exists(), "cache namespace already exists")
    prepared = ResolutionEngine(base, adoptions, roster)
    with revision(prepared):
        result = engine.build(base, adoptions, output_name, proposal_name)
    require(result["counts"].get("HOLD", 0) == 0, "a code/boundary guard still holds a proposed recovery")
    return result


def verify(base, roster, output_name="cache_v1"):
    with revision():
        result = engine.verify(base, output_name)
    index = LatestIndex(base)
    document, proposals = load_roster(roster, index)
    report = engine.cache.read(base / output_name / "built.json")
    require(report["counts"].get("HOLD", 0) == 0, "unresolved HOLD remains")
    roster_sha256 = engine.file_sha(roster)
    checked = Counter()
    for row in engine.cache.rows(base / output_name / "ledger", report["manifests"]["ledger"]):
        if index.state(row) != 3:
            continue
        proposal = proposals[row["original_text_sha256"]]
        if proposal["decision"] == "EXCLUDE":
            require(row["decision"] == "EXCLUDE", "excluded source was admitted")
        elif row["decision"] in ("KEEP", "EDIT"):
            require(row["clean_text_sha256"] == proposal["clean_text_sha256"], "new body differs from approved text")
        else:
            require(row["decision"] == "EXCLUDE" and (row.get("duplicate_of") or row.get("validation_overlap")), "admitted proposal lost without an exclusion cause")
        require(row.get("resolution_roster_sha256") == roster_sha256, "resolution reference differs")
        checked.update(documents=1, input_ids=row["input_ids"])
    require(dict(checked) == document["counts"], "independent residual coverage differs")
    proof = dict(schema=SCHEMA, status="CPU_FULL_RESIDUAL_RESOLUTION_CACHE_VERIFIED",
                 roster_sha256=engine.file_sha(roster), checked=dict(checked), remaining_hold=0,
                 core_recovery_verified_sha256=engine.file_sha(base / output_name / "recovery_verified.json"),
                 all_previous_adopted_text_preserved=True, training_authorized=False)
    engine.write_json(base / output_name / "resolution_verified.json", proof)
    return dict(result, residual_resolution=proof)


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES="", TOKENIZERS_PARALLELISM="false", RAYON_NUM_THREADS="1",
                      OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--base", type=Path, default=BASE)
    parser.add_argument("--adoptions", type=Path)
    parser.add_argument("--roster", type=Path, required=True)
    parser.add_argument("--proposal-name", default="proposals_v1")
    parser.add_argument("--output-name", default="cache_v1")
    args = parser.parse_args()
    base = engine.safe(args.base)
    roster = engine.safe(args.roster)
    if args.command == "build":
        require(args.adoptions is not None, "exact adoptions manifest required")
        result = build(base, engine.safe(args.adoptions), roster, args.output_name, args.proposal_name)
    else:
        result = verify(base, roster, args.output_name)
    print(json.dumps({k: v for k, v in result.items() if k in ["status", "counts", "recovery_outcomes", "residual_resolution"]}), flush=True)


if __name__ == "__main__":
    main()
