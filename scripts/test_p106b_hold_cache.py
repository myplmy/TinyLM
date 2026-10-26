#!/usr/bin/env python3
"""CPU integration: preserve the parent roster while recovering held sources."""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_cache as recovery_cache
from scripts import test_p106b_corpus_cache as parent_tests


class RecoveryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent_tests.RealTokenizerRoundTrip.setUpClass()
        cls.helper=parent_tests.RealTokenizerRoundTrip()

    def execute(self,root,action):
        def prepared(parent,original_adoptions):
            cache=recovery_cache.cache
            parent_report=cache.build(parent,original_adoptions)
            cache.verify_cache(parent)
            base=root/"data_cache/recovery";base.mkdir()
            cache.write_json(base/"scope.json",cache.read(parent/"scope.json"))
            agent=base/"agents/test";agent.mkdir(parents=True)
            text=agent/"duplicate.txt";text.write_text("Unchanged independent source prose.",encoding="utf-8")
            review=agent/"review.md";review.write_text("Isolated source-linked fixture review.",encoding="utf-8")
            rows=[dict(input_text_sha256=cache.sha("Repeated context line.\nRepeated context line."),
                decision="EDIT",path=str(text.relative_to(root)),sha256=cache.file_sha(text),
                root_reviewed=True,recovery_review=True,reason="exact test duplicate",review=str(review.relative_to(root))),
                dict(input_text_sha256=cache.sha("Previous explicit hold article."),decision="KEEP",root_reviewed=True,
                    recovery_review=True,resolves_inherited_hold=True,reason="fresh text review",review=str(review.relative_to(root)))]
            adoptions=base/"adoptions.json";cache.write_json(adoptions,dict(schema="P106B_ROOT_TEXT_ADOPTIONS_V1",rows=rows,reviews=[]))
            directory=base/"proposals_v2";writer=cache.ShardWriter(directory/"ledger","proposals",limit=10000)
            for row in cache.rows(parent/"cache_v1/hold",parent_report["manifests"]["hold"]):writer.append(row)
            manifest=writer.close(lineage={})
            cache.write_json(directory/"complete.json",dict(unprocessed=0,counts=dict(documents=parent_report["counts"]["HOLD"],
                input_ids=parent_report["counts"]["HOLD_input_ids"]),manifest=manifest,pin=dict(
                recovery_revision_source_sha256=recovery_cache.code_pins(),parent_built_sha256=cache.file_sha(parent/"cache_v1/built.json"),
                parent_verified_sha256=cache.file_sha(parent/"cache_v1/verified.json"),scope_sha256=cache.file_sha(base/"scope.json"))))
            with ExitStack() as stack:
                for module,key,value in [(recovery_cache,"ROOT",root),(recovery_cache,"safe",lambda p:Path(p)),
                    (recovery_cache.recovery,"PARENT",parent),(recovery_cache.recovery,"OLD_ADOPTIONS",original_adoptions)]:
                    stack.enter_context(patch.object(module,key,value))
                return action(base,adoptions,parent,parent_report)
        return self.helper.run_fixture(root,prepared)

    def test_old_adopted_bodies_and_exclusions_survive_earlier_new_duplicate(self):
        with tempfile.TemporaryDirectory(prefix="recovery_cache_roundtrip_") as folder:
            def action(base,adoptions,parent,old):
                before=recovery_cache.file_sha(parent/"cache_v1/built.json")
                result=recovery_cache.build(base,adoptions)
                self.assertTrue(result["baseline_accepted_preserved"])
                self.assertEqual(result["recovery_outcomes"]["KEEP"],1)
                self.assertEqual(result["accepted"]["train"]["documents"],old["accepted"]["train"]["documents"]+1)
                cache=recovery_cache.cache
                events={r["id"]:r for r in cache.rows(base/"cache_v2/ledger",result["manifests"]["ledger"])}
                self.assertEqual(events["expanded_train:2"]["decision"],"EXCLUDE")
                self.assertEqual(events["expanded_train:2"]["duplicate_of"],"expanded_train:3")
                self.assertEqual(events["expanded_train:3"]["decision"],"KEEP")
                self.assertEqual(events["expanded_train:1"]["decision"],"EXCLUDE")
                proof=recovery_cache.verify(base)
                self.assertTrue(proof["all_previous_adopted_text_preserved"])
                self.assertFalse(proof["training_authorized"])
                self.assertEqual(recovery_cache.file_sha(parent/"cache_v1/built.json"),before)
            self.execute(Path(folder),action)

    def test_false_census_coverage_rejected_before_new_cache(self):
        with tempfile.TemporaryDirectory(prefix="recovery_cache_scope_") as folder:
            def action(base,adoptions,parent,old):
                path=base/"proposals_v2/complete.json";value=recovery_cache.cache.read(path)
                value["counts"]["documents"]-=1
                # This mutation is only a deliberate isolated negative fixture.
                import json
                path.write_text(json.dumps(value),encoding="utf-8")
                with self.assertRaisesRegex(ValueError,"HOLD scope differs"):recovery_cache.build(base,adoptions)
                self.assertFalse((base/"cache_v2").exists())
            self.execute(Path(folder),action)

    def test_technical_table_exception_cannot_modify_retained_values(self):
        original="A mining explanation.\nWEIGHTS AND MEASURES.\n``` Troy Weight. 24 grains 1 pennyweight.\nLong Measure. 12 inches 1 foot.\nCall the company.\n"
        lo=original.index("``` ");hi=original.index("Call the company.")
        literal=original[lo:hi];clean=original[:lo]+literal[4:]
        engine=object.__new__(recovery_cache.RecoveryEngine)
        engine.current=(dict(text=original),3)
        manual=dict(code_exception=dict(kind="UNWRAP_EXTRACTED_UNIT_TABLE",original_text_sha256=recovery_cache.sha(original),
            original_table_characters=[lo,hi],original_table_sha256=recovery_cache.sha(literal)))
        self.assertTrue(engine.code_guard(original,clean,manual))
        self.assertFalse(engine.code_guard(original,clean.replace("24 grains","25 grains"),manual))
        self.assertFalse(engine.code_guard(original,clean,None))

    def test_new_validation_span_is_blocked_before_it_can_evict_parent_train(self):
        with tempfile.TemporaryDirectory(prefix="recovery_val_reservation_") as folder:
            root=Path(folder);old=root/"old";cache=recovery_cache.cache
            codec=cache.native.ByteCodec(self.helper.config)
            text=" ".join("word"+str(i) for i in range(400))+"."
            data=cache.native.ids_bytes(codec.backend.encode(text,add_special_tokens=False).ids+[2])
            self.assertGreater(len(data),512)
            validation=root/"val.bin";validation.write_bytes(data)
            tokens=cache.TokenWriter(old/"tokens/train");loc=tokens.append(data);tm=tokens.close()
            ledger=cache.ShardWriter(old/"ledger","decisions",limit=10000)
            ledger.append(dict(id="expanded_train:7",split="train",decision="KEEP",cache=loc))
            lm=ledger.close(lineage={})
            scope=dict(inputs=[dict(name="validation",split="val",path=str(validation))],
                tokenizer=dict(path=str(recovery_cache.corpus.TOKENIZER)))
            engine=object.__new__(recovery_cache.RecoveryEngine)
            engine.index=SimpleNamespace(scope=scope,old=old,state=lambda row:3,
                report=dict(manifests=dict(tokens_train=tm,ledger=lm)))
            engine.new_overrides={};engine.val_blocked={}
            engine.pick=lambda row,overrides,known:("KEEP",text,[],None)
            row=dict(id="validation:1",text=text,source_ids=[0,len(data)//2])
            with patch.object(recovery_cache.corpus,"iter_scan",return_value=iter([row])):
                engine.validation_preflight()
            self.assertEqual(engine.val_blocked["validation:1"]["id"],"expanded_train:7")
            self.assertEqual(engine.val_blocked["validation:1"]["kind"],"PRESERVED_TRAIN_256_IDS_STRIDE128")


if __name__=="__main__":unittest.main()
