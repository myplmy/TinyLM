#!/usr/bin/env python3
"""Partial cache keeps real HOLD while refusing unapproved admissions."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_partial_cache as partial
from scripts import test_p106b_hold_resolution_cache as final_tests

cache=partial.cache
final=partial.final


class PartialRosterTests(final_tests.AdmissionTests):
    def convert(self,path,*,pending):
        value=cache.read(path)
        directory=path.parent/value["records_directory"]
        rows=list(cache.rows(directory,value["manifest"]))
        # New immutable test roster; never rewrite an existing shard.
        writer=cache.ShardWriter(path.parent/"partial_records","decisions",limit=10000)
        for row in rows:
            if pending:
                row.update(root_approved=False,review_status="UNRESOLVED_NOT_ADMITTED")
                row.pop("clean_text_sha256",None)
            writer.append(row)
        manifest=writer.close(lineage={})
        target=path.parent/"partial.json"
        cache.write_json(target,dict(value,schema=partial.SCHEMA,status="ROOT_REVIEWED_PARTIAL_RESIDUAL_CACHE_ROSTER",
            goal_complete=False,training_authorized=False,records_directory="partial_records",manifest=manifest,
            remaining_hold=2 if pending else 0,unprocessed=2 if pending else 0))
        return target

    def test_real_unresolved_occurrences_stay_hold(self):
        with self.fixture(pending=True) as (path,index,evidence):
            target=self.convert(path,pending=True)
            with patch.object(partial,"ROOT",final.ROOT):
                document,rows=partial.load_roster(target,index)
            self.assertEqual(document["remaining_hold"],2)
            self.assertEqual(next(iter(rows.values()))["decision"],"HOLD")
            self.assertFalse(next(iter(rows.values()))["root_approved"])

    def test_terminal_body_still_needs_root_approval(self):
        with self.fixture() as (path,index,evidence):
            target=self.convert(path,pending=False)
            document=cache.read(target)
            directory=target.parent/"unapproved"
            writer=cache.ShardWriter(directory,"decisions",limit=10000)
            row=next(cache.rows(target.parent/"partial_records",document["manifest"]))
            writer.append(dict(row,root_approved=False))
            manifest=writer.close(lineage={})
            negative=target.parent/"unapproved.json"
            cache.write_json(negative,dict(document,records_directory="unapproved",manifest=manifest))
            with patch.object(partial,"ROOT",final.ROOT):
                with self.assertRaisesRegex(ValueError,"not root-approved"):
                    partial.load_roster(negative,index)

    def test_partial_cannot_claim_zero_remaining_for_real_holds(self):
        with self.fixture(pending=True) as (path,index,evidence):
            target=self.convert(path,pending=True)
            document=cache.read(target)
            negative=target.parent/"fake_zero.json"
            cache.write_json(negative,dict(document,remaining_hold=0,unprocessed=0))
            with patch.object(partial,"ROOT",final.ROOT):
                with self.assertRaisesRegex(ValueError,"occurrence count differs"):
                    partial.load_roster(negative,index)

    def test_a_partial_receipt_cannot_be_final_goal_evidence(self):
        with self.fixture(pending=True) as (path,index,evidence):
            target=self.convert(path,pending=True)
            with self.assertRaisesRegex(ValueError,"full approved"):
                final.load_roster(target,index)


class PartialIntegration(final_tests.previous_tests.RecoveryIntegration):
    def test_actual_partial_build_and_full_consumer_preserve_hold(self):
        with tempfile.TemporaryDirectory(prefix="partial_recovery_roundtrip_") as folder:
            root=Path(folder)

            def action(previous_base,previous_adoptions,parent,unused_report):
                before_report=partial.engine.build(previous_base,previous_adoptions)
                partial.engine.verify(previous_base)
                previous_cache=previous_base/"cache_v2"
                before=cache.file_sha(previous_cache/"built.json")
                base=root/"data_cache/partial_resolution"
                base.mkdir()
                with (base/"scope.json").open("xb") as stream:
                    stream.write((previous_base/"scope.json").read_bytes())
                evidence=base/"agents/test/review.md"
                evidence.parent.mkdir(parents=True)
                evidence.write_text("Fixture unresolved boundaries remain outside training.",encoding="utf-8")
                old_holds=list(cache.rows(previous_cache/"hold",before_report["manifests"]["hold"]))
                records={row["original_text_sha256"]:dict(original_text_sha256=row["original_text_sha256"],decision="HOLD",
                    root_approved=False,review_status="UNRESOLVED_NOT_ADMITTED",reason="FIXTURE_UNRESOLVED_BOUNDARY",
                    evidence=dict(path=str(evidence.relative_to(root)),sha256=cache.file_sha(evidence))) for row in old_holds}
                writer=cache.ShardWriter(base/"roster/records","decisions",limit=10000)
                for row in records.values():
                    writer.append(row)
                manifest=writer.close(lineage={})
                roster=base/"roster/complete.json"
                counts=dict(documents=len(old_holds),input_ids=sum(row["input_ids"] for row in old_holds))
                cache.write_json(roster,dict(schema=partial.SCHEMA,status="ROOT_REVIEWED_PARTIAL_RESIDUAL_CACHE_ROSTER",
                    goal_complete=False,training_authorized=False,parent_built_sha256=before,records_directory="records",
                    manifest=manifest,counts=counts,remaining_hold=len(old_holds),unprocessed=len(old_holds)))
                adoptions=base/"adoptions.json"
                cache.write_json(adoptions,dict(schema="P106B_ROOT_TEXT_ADOPTIONS_V1",rows=[],reviews=[]))
                writer=cache.ShardWriter(base/"partial_proposals_v1/ledger","proposals",limit=10000)
                for row in old_holds:
                    writer.append(row)
                proposal_manifest=writer.close(lineage={})
                with patch.object(partial,"ROOT",root),patch.object(final,"ROOT",root), \
                        patch.object(final,"PARENT",previous_cache),patch.object(final.inventory,"PARENT_BASE",previous_base), \
                        patch.object(final,"PREVIOUS_ADOPTIONS",previous_adoptions):
                    with partial.revision():
                        pins=partial.engine.code_pins()
                    cache.write_json(base/"partial_proposals_v1/complete.json",dict(unprocessed=0,counts=counts,manifest=proposal_manifest,
                        pin=dict(recovery_revision_source_sha256=pins,parent_built_sha256=before,
                            parent_verified_sha256=cache.file_sha(previous_cache/"verified.json"),scope_sha256=cache.file_sha(base/"scope.json"))))
                    report=partial.build(base,adoptions,roster)
                    self.assertEqual(report["counts"]["HOLD"],len(old_holds))
                    proof=partial.verify(base,roster)
                    self.assertFalse(proof["partial_resolution"]["goal_complete"])
                    self.assertEqual(proof["partial_resolution"]["remaining_hold"],len(old_holds))
                    self.assertEqual(cache.file_sha(previous_cache/"built.json"),before)
            self.execute(root,action)


if __name__=="__main__":
    unittest.main()
