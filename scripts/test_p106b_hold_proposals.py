#!/usr/bin/env python3
"""Full proposal accounting and source-hash rejection on isolated CPU fixtures."""
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_proposals as proposals


class ProposalCensusTests(unittest.TestCase):
    def fixture(self,root,*,mismatch=False,prior_review=False):
        base=root/"data_cache/recovery";parent=root/"parent/unit_000000"
        base.mkdir(parents=True);(base/"packets_initial_v2").mkdir()
        proposals.write_json(base/"packets_initial_v2/manifest.json",dict(rows=[]))
        scan=proposals.ShardWriter(parent/"records","documents",limit=10000)
        holds=proposals.ShardWriter(base/"inventory/unit/records","holds",limit=10000)
        for i,text in enumerate(["A complete article.\nReferences\nSmith (2001).\n"]*2+["Relation is a subset of .\n"]):
            row=dict(id=f"expanded_train:{i}",source="expanded_train",split="train",ordinal=i,
                text=text,complete_eos=True,valid_utf8=True,source_ids=[i*12,(i+1)*12],input_ids=12,
                source_ids_sha256=str(i)*64,original_text_sha256=proposals.sha(text))
            scan.append(row)
            item={k:v for k,v in row.items() if k not in ["text","complete_eos","valid_utf8"]}
            item.update(source_unit="parent/unit_000000/complete.json",previous_reasons=["APPENDIX_OR_NAVIGATION_CONTEXT"],
                previous_holds=[],features=dict(family="REFERENCE_OR_APPENDIX_WITH_CONTENT",language_bucket="NO_HANGUL",
                    flags=["PREVIOUS_INDIVIDUAL_HOLD"] if prior_review and i==0 else []))
            if mismatch and i==0:item["source_ids_sha256"]="F"*64
            holds.append(item)
        sm=scan.close(lineage={});hm=holds.close(lineage={})
        proposals.write_json(parent/"complete.json",dict(manifest=sm))
        stamp=base/"inventory/unit/complete.json";proposals.write_json(stamp,dict(manifest=hm))
        inventory=dict(counts=dict(documents=3,input_ids=36),units=[str(stamp.relative_to(root))])
        return base,inventory

    def execute(self,root,base,inventory):
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch.object(proposals,"ROOT",root))
        stack.enter_context(patch.object(proposals,"safe",lambda p:Path(p)))
        stack.enter_context(patch.object(proposals,"pin",return_value=(inventory,dict(fixture="frozen"))))
        return proposals.full(base,each=2)

    def test_positions_and_duplicates_conserved_without_cache_admission(self):
        with tempfile.TemporaryDirectory(prefix="hold_proposals_") as folder:
            root=Path(folder);base,inventory=self.fixture(root)
            report=self.execute(root,base,inventory)
            self.assertEqual(report["counts"]["documents"],3)
            self.assertEqual(report["counts"]["KEEP"],2)
            self.assertEqual(report["counts"]["HOLD"],1)
            self.assertEqual(report["unique_original_texts"],2)
            self.assertEqual(report["review_packets"],2)
            self.assertFalse(report["actual_cache_created"])
            rows=list(proposals.cache.rows(base/"proposals_v1/ledger",report["manifest"]))
            self.assertEqual({r["training_admission"] for r in rows},{"NOT_ADMITTED"})
            with self.assertRaisesRegex(ValueError,"write-once"):proposals.full(base)

    def test_source_hash_mismatch_has_no_complete_receipt(self):
        with tempfile.TemporaryDirectory(prefix="hold_proposal_bad_") as folder:
            root=Path(folder);base,inventory=self.fixture(root,mismatch=True)
            with self.assertRaisesRegex(ValueError,"source linkage"):self.execute(root,base,inventory)
            self.assertTrue((base/"proposals_v1/started.json").exists())
            self.assertFalse((base/"proposals_v1/complete.json").exists())

    def test_inherited_individual_hold_needs_an_explicit_new_review(self):
        with tempfile.TemporaryDirectory(prefix="hold_proposal_review_") as folder:
            root=Path(folder);base,inventory=self.fixture(root,prior_review=True)
            report=self.execute(root,base,inventory)
            self.assertEqual(report["counts"]["HOLD"],2)
            self.assertIn("INHERITED_INDIVIDUAL_HOLD_REQUIRES_SOURCE_SHA_REVIEW",report["reasons"])


if __name__=="__main__":unittest.main()
