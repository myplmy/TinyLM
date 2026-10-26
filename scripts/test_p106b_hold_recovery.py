#!/usr/bin/env python3
"""CPU guards for HOLD inventory families and immutable parent conservation."""
from collections import Counter
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_recovery as recovery


def record(text,ident="expanded_train:0"):
    info,_=recovery.signals(text)
    return dict(id=ident,text=text,complete_eos=True,valid_utf8=True,
        original_text_sha256=recovery.sha(text),candidate_text_sha256=recovery.sha(text),
        original_signals=info,language_bucket=recovery.corpus.language_bucket(text),
        language_proxy=recovery.corpus.proxy(text))


class FamilyTests(unittest.TestCase):
    def features(self,text,**kwargs):
        return recovery.family_features(record(text),dict(reasons=[],**kwargs),set())

    def test_populated_reference_is_review_family_not_automatic_admission(self):
        x=self.features("A complete article.\nReferences\nSmith, A. Example research (2001).")
        self.assertEqual(x["family"],"REFERENCE_OR_APPENDIX_WITH_CONTENT")
        self.assertEqual(x["flags"],[])

    def test_missing_internal_table_section_is_distinct(self):
        x=self.features("선수에 대한 설명이다.\n통산 기록\n각주\n참고 문헌\n인물 사전 (2001).")
        self.assertIn("EMPTY_INTERNAL_OR_STRUCTURED_SECTION",x["flags"])

    def test_empty_optional_name_and_missing_opening_name_are_retained_risks(self):
        self.assertIn("MISSING_PARENTHETICAL_OR_TITLE_CONTEXT",self.features("서울()은 도시이다.")["flags"])
        self.assertIn("MISSING_OPENING_NAME_OR_TERM",self.features("이름(, 1991년 출생)은 선수이다.")["flags"])

    def test_literal_code_does_not_become_a_blank_name_or_html_risk(self):
        x=self.features("Example.\n```py\nfunction()\nprint('<div>')\n```\nReferences\nA valid source.")
        self.assertEqual(x["flags"],[])

    def test_previous_individual_hold_is_not_lost(self):
        row=record("A previously reviewed broken passage.")
        x=recovery.family_features(row,dict(reasons=[]),{row["original_text_sha256"]})
        self.assertEqual(x["family"],"PREVIOUS_INDIVIDUAL_OR_EXPLICIT")

    def test_source_fragment_is_never_treated_as_complete_reference(self):
        row=record("Partial prose.");row["complete_eos"]=False
        x=recovery.family_features(row,dict(reasons=[]),set())
        self.assertEqual(x["family"],"BOUNDARY_FRAGMENT")


class InventoryTests(unittest.TestCase):
    def test_full_parent_roster_is_conserved_and_write_once(self):
        with tempfile.TemporaryDirectory(prefix="hold_inventory_") as folder:
            root=Path(folder);parent=root/"data_cache/parent";old_cache=parent/"cache_v1"
            base=root/"data_cache/recovery";old_cache.mkdir(parents=True)
            row=record("Valid prose.\nReferences\nA complete citation.")
            row.update(source="expanded_train",split="train",ordinal=0,source_ids=[0,12],
                source_ids_sha256="A"*64,input_ids=12)
            event=dict(id=row["id"],decision="HOLD",original_text_sha256=row["original_text_sha256"],
                source_ids_sha256=row["source_ids_sha256"],reasons=["APPENDIX_OR_NAVIGATION_CONTEXT"])
            unit=parent/"scan/expanded_train/unit_000000_attempt_000"
            writer=recovery.ShardWriter(unit/"records","documents",limit=10000);writer.append(row)
            manifest=writer.close(lineage={})
            recovery.write_json(unit/"complete.json",dict(start_ids=0,end_ids=12,start_ordinal=0,end_ordinal=1,manifest=manifest))
            holds=recovery.ShardWriter(old_cache/"hold","positions",limit=10000);holds.append(event)
            hm=holds.close(lineage={})
            recovery.write_json(old_cache/"built.json",dict(counts=dict(HOLD=1,HOLD_input_ids=12),manifests=dict(hold=hm)))
            recovery.write_json(old_cache/"verified.json",dict(every_adopted_document_regenerated=True))
            recovery.write_json(parent/"scope.json",dict(inputs=[dict(name="expanded_train",ids=12,intervals=1)]))
            adoptions=root/"adoptions.json";recovery.write_json(adoptions,dict(rows=[]))
            with ExitStack() as stack:
                for key,value in [("ROOT",root),("PARENT",parent),("OLD_CACHE",old_cache),("OLD_ADOPTIONS",adoptions),("safe",lambda p:Path(p))]:
                    stack.enter_context(patch.object(recovery,key,value))
                report=recovery.inventory(base)
                self.assertTrue(report["full_parent_hold_coverage"])
                self.assertEqual(report["unprocessed"],0)
                self.assertEqual(report["counts"],dict(documents=1,input_ids=12))
                rows=list(recovery.inventory_rows(base));self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]["recovery_decision"],"NOT_REVIEWED")
                with self.assertRaisesRegex(ValueError,"inventory complete already"):recovery.inventory(base)


if __name__=="__main__":unittest.main()
