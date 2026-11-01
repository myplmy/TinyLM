#!/usr/bin/env python3
"""CPU admission guards: full coverage, immutable evidence and old-body priority."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_cache as resolution
from scripts import test_p106b_hold_cache as previous_tests

cache = resolution.engine.cache


class AdmissionTests(unittest.TestCase):
    @contextmanager
    def fixture(self, *, pending=False, missing=False):
        with tempfile.TemporaryDirectory(prefix="residual_admission_") as folder:
            root = Path(folder)
            base = root / "new"
            base.mkdir()
            old = root / "old"
            old.mkdir()
            cache.write_json(old / "built.json", dict(fixture=True))
            key = cache.sha("Source article.")
            writer = cache.ShardWriter(old / "hold", "positions", limit=10000)
            for number in range(2):
                writer.append(dict(id="source:" + str(number), original_text_sha256=key, input_ids=10))
            parent_manifest = writer.close(lineage={})
            evidence = root / "handoff/audit/hold_resolution_20261027_goalc/review.md"
            evidence.parent.mkdir(parents=True)
            evidence.write_text("Actual fixture evidence.", encoding="utf-8")
            writer = cache.ShardWriter(base / "roster/records", "decisions", limit=10000)
            writer.append(dict(original_text_sha256=cache.sha("Outside source.") if missing else key,
                               clean_text_sha256=cache.sha("Outside source.") if missing else key,
                               decision="HOLD" if pending else "KEEP", root_approved=True,
                               reason="FIXTURE_LITERAL_BODY", evidence=dict(path=str(evidence.relative_to(root)), sha256=cache.file_sha(evidence))))
            manifest = writer.close(lineage={})
            path = base / "roster/complete.json"
            cache.write_json(path, dict(schema=resolution.SCHEMA, status="ROOT_REVIEWED_FULL_RESIDUAL_RESOLUTION",
                                       unprocessed=0, remaining_hold=0, parent_built_sha256=cache.file_sha(old / "built.json"),
                                       records_directory="records", manifest=manifest, counts=dict(documents=2, input_ids=20)))
            index = SimpleNamespace(base=base, old=old, report=dict(manifests=dict(hold=parent_manifest)), counts=dict(HOLD=2))
            with patch.object(resolution, "ROOT", root):
                yield path, index, evidence

    def test_all_occurrences_share_one_source_linked_resolution(self):
        with self.fixture() as (path, index, evidence):
            document, roster = resolution.load_roster(path, index)
            self.assertEqual(document["counts"]["documents"], 2)
            self.assertEqual(len(roster), 1)

    def test_pending_proposal_is_rejected_before_cache_creation(self):
        with self.fixture(pending=True) as (path, index, evidence):
            with self.assertRaisesRegex(ValueError, "unresolved"):
                resolution.load_roster(path, index)

    def test_missing_source_is_not_hidden_by_matching_counts(self):
        with self.fixture(missing=True) as (path, index, evidence):
            with self.assertRaisesRegex(ValueError, "no actual resolution"):
                resolution.load_roster(path, index)

    def test_changed_review_evidence_is_rejected(self):
        with self.fixture() as (path, index, evidence):
            evidence.write_text("Changed only in this negative fixture.", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "evidence changed"):
                resolution.load_roster(path, index)

    def test_real_zero_hold_manifest_needs_no_dummy_text(self):
        with tempfile.TemporaryDirectory(prefix="empty_hold_") as folder:
            directory = Path(folder) / "hold"
            writer = resolution.EmptyHoldWriter(directory, "positions", limit=10000)
            manifest = writer.close(lineage={})
            self.assertEqual(manifest["rows"], 0)
            self.assertEqual(manifest["shards"], [])
            cache.verify(directory, manifest)
            self.assertEqual(list(cache.rows(directory, manifest)), [])

    def test_empty_training_text_is_still_an_error(self):
        with tempfile.TemporaryDirectory(prefix="empty_train_") as folder:
            writer = resolution.EmptyHoldWriter(Path(folder) / "train", "documents", limit=10000)
            with self.assertRaisesRegex(ValueError, "empty sharded corpus"):
                writer.close(lineage={})

    def test_new_earlier_duplicate_cannot_evict_previous_body(self):
        text = "Previously admitted exact body."
        key = cache.sha(text)
        obj = resolution.ResolutionEngine.__new__(resolution.ResolutionEngine)
        obj.index = SimpleNamespace(state=lambda row: 3, owners={"train": {bytes.fromhex(key): "source:old"}, "val": {}})
        obj.roster = {key: dict(decision="KEEP", clean_text_sha256=key, reason="PRESERVE_LITERAL", evidence={})}
        obj.roster_sha256 = "A" * 64
        obj.val_blocked = {}
        value = obj.pick(dict(id="source:new_earlier", original_text_sha256=key, text=text, split="train"), {})
        self.assertEqual(value[0], "EXCLUDE")
        self.assertEqual(obj.extra["duplicate_of"], "source:old")

    def test_changed_previous_body_fails_instead_of_becoming_a_new_version(self):
        obj = resolution.ResolutionEngine.__new__(resolution.ResolutionEngine)
        obj.index = SimpleNamespace(state=lambda row: 1, digest=lambda row: cache.sha("Original body."))
        obj.baseline = SimpleNamespace(pick=lambda *args: ("EDIT", "Changed body.", [], None), new_overrides={})
        with self.assertRaisesRegex(ValueError, "latest admitted body changed"):
            obj.pick(dict(id="source:old", text="Original body."), {})


class FullAdapterIntegration(previous_tests.RecoveryIntegration):
    def test_latest_parent_and_true_zero_hold_round_trip(self):
        with tempfile.TemporaryDirectory(prefix="residual_full_roundtrip_") as folder:
            root = Path(folder)

            def action(previous_base, previous_adoptions, parent, unused_report):
                previous = resolution.engine.build(previous_base, previous_adoptions)
                resolution.engine.verify(previous_base)
                previous_cache = previous_base / "cache_v2"
                before = cache.file_sha(previous_cache / "built.json")
                base = root / "data_cache/resolution"
                base.mkdir()
                with (base / "scope.json").open("xb") as stream:
                    stream.write((previous_base / "scope.json").read_bytes())
                evidence = base / "agents/test/review.md"
                evidence.parent.mkdir(parents=True)
                evidence.write_text("Isolated review of incomplete fixture boundaries only.", encoding="utf-8")
                old_holds = list(cache.rows(previous_cache / "hold", previous["manifests"]["hold"]))
                self.assertGreater(len(old_holds), 0)
                records = {}
                for row in old_holds:
                    records[row["original_text_sha256"]] = dict(original_text_sha256=row["original_text_sha256"],
                        decision="EXCLUDE", root_approved=True, reason="FIXTURE_DAMAGED_BOUNDARY",
                        evidence=dict(path=str(evidence.relative_to(root)), sha256=cache.file_sha(evidence)))
                writer = cache.ShardWriter(base / "roster/records", "decisions", limit=10000)
                for row in records.values():
                    writer.append(row)
                manifest = writer.close(lineage={})
                roster = base / "roster/complete.json"
                counts = dict(documents=len(old_holds), input_ids=sum(row["input_ids"] for row in old_holds))
                cache.write_json(roster, dict(schema=resolution.SCHEMA, status="ROOT_REVIEWED_FULL_RESIDUAL_RESOLUTION",
                    unprocessed=0, remaining_hold=0, parent_built_sha256=before,
                    records_directory="records", manifest=manifest, counts=counts))
                adoptions = base / "adoptions.json"
                cache.write_json(adoptions, dict(schema="P106B_ROOT_TEXT_ADOPTIONS_V1", rows=[], reviews=[]))
                writer = cache.ShardWriter(base / "proposals_v1/ledger", "proposals", limit=10000)
                for row in old_holds:
                    writer.append(row)
                proposal_manifest = writer.close(lineage={})
                with patch.object(resolution, "ROOT", root), patch.object(resolution, "PARENT", previous_cache), \
                        patch.object(resolution.inventory, "PARENT_BASE", previous_base), \
                        patch.object(resolution, "PREVIOUS_ADOPTIONS", previous_adoptions):
                    with resolution.revision():
                        pins = resolution.engine.code_pins()
                    cache.write_json(base / "proposals_v1/complete.json", dict(unprocessed=0, counts=counts,
                        manifest=proposal_manifest, pin=dict(recovery_revision_source_sha256=pins,
                            parent_built_sha256=before, parent_verified_sha256=cache.file_sha(previous_cache / "verified.json"),
                            scope_sha256=cache.file_sha(base / "scope.json"))))
                    result = resolution.build(base, adoptions, roster)
                    self.assertEqual(result["counts"].get("HOLD", 0), 0)
                    self.assertEqual(result["manifests"]["hold"]["shards"], [])
                    self.assertEqual(result["accepted"], previous["accepted"])
                    proof = resolution.verify(base, roster)
                    self.assertEqual(proof["residual_resolution"]["checked"], counts)
                    self.assertFalse(proof["training_authorized"])
                    self.assertEqual(cache.file_sha(previous_cache / "built.json"), before)
            self.execute(root, action)


if __name__ == "__main__":
    unittest.main()
