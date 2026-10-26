#!/usr/bin/env python3
"""CPU end-to-end invariants for cleanup admission and sharded serialization."""
from array import array
from collections import Counter
from contextlib import ExitStack
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_corpus_cache as cache
from scripts import p106b_corpus_cleanup as corpus


class ShardContracts(unittest.TestCase):
    def test_boundary_slices_and_hashes_reconstruct_order(self):
        with tempfile.TemporaryDirectory(prefix="cleanup_token_shards_") as temp:
            directory=Path(temp)/"tokens"
            writer=cache.TokenWriter(directory,limit=12)
            first=array("H",[30,31,2]).tobytes()
            second=array("H",[40,41,42,2]).tobytes()
            writer.append(first);writer.append(second)
            manifest=writer.close()
            self.assertEqual(len(manifest["shards"]),2)
            bank=cache.ShardedTokens(directory,manifest)
            self.assertEqual(bank[1:6].tolist(),[31,2,40,41,42])
            self.assertEqual(bank[-1],2)
            self.assertEqual(bank[:].tobytes(),first+second)
            self.assertTrue(all(s["bytes"]<20_000_000 for s in manifest["shards"]))

    def test_split_document_cannot_exceed_file_bound(self):
        with tempfile.TemporaryDirectory(prefix="cleanup_bound_") as temp:
            writer=cache.TokenWriter(Path(temp)/"tokens",limit=4)
            with self.assertRaises(ValueError):writer.append(array("H",[3,4,2]).tobytes())

    def test_new_control_risks_preserve_technical_code(self):
        self.assertIn("MISSING_PARENTHETICAL_OR_TITLE_CONTEXT",cache.independent_control_risks("Name() is blank."))
        self.assertIn("PAGE_NAVIGATION_OR_SUBSCRIPTION_CONTEXT",cache.independent_control_risks("Subscribe to our newsletter\nArticle."))
        self.assertEqual(cache.independent_control_risks("Example: `function()`\n```py\nfunction()\n```"),[])

    def test_nfc_must_not_change_literal_code_bytes(self):
        old='```py\nname="e\u0301"\n```\nReferences\n'
        candidate=corpus.propose(old)[0]
        self.assertTrue(cache.protected_code_changed(old,candidate))
        self.assertFalse(cache.protected_code_changed(old,old.replace("References\n", "")))

    def test_exact_reviewed_decoration_exception_cannot_modify_real_code(self):
        old="```py\nprint(42)\n```\n~~~~~~~~~~ 0 ~~~~~~~~~~\nReaders also read:\n"
        cleaned="```py\nprint(42)\n```\n"
        manual=dict(decorative_rule_removed="~~~~~~~~~~ 0 ~~~~~~~~~~")
        self.assertTrue(cache.code_preserved(old,cleaned,manual))
        self.assertFalse(cache.code_preserved(old,cleaned.replace("42","43"),manual))
        self.assertFalse(cache.code_preserved(old,cleaned,None))


class RealTokenizerRoundTrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=corpus.read(corpus.TOKENIZER)

    def fixture(self,root):
        codec=cache.native.ByteCodec(self.config)
        base=root/"data_cache/cleanup"
        base.mkdir(parents=True)
        tokenizer=root/"data_cache/tokenizer.json"
        corpus.write_json(tokenizer,self.config)
        metadata=root/"data_cache/meta.json"
        corpus.write_json(metadata,{"synthetic":True})
        examples={
            "validation":["prefixFragmentOnly", "Unique validation article sentence.", "suffixFragmentOnly"],
            "expanded_train":["Clean source prose.\nReferences\n", "Unique validation article sentence.",
                "Repeated context line.\nRepeated context line.", "Unchanged independent source prose.",
                "Previous explicit hold article."],
            "historical_train":["Clean source prose.\nReferences\n", "Another independent historical source."]}
        inputs=[]
        for name,texts in examples.items():
            data=b""
            row_values=[]
            for index,text in enumerate(texts):
                complete=not(name=="validation" and index==len(texts)-1)
                ids=codec.backend.encode(text,add_special_tokens=False).ids+([2] if complete else [])
                raw=cache.native.ids_bytes(ids)
                candidate,removed,info,risk=corpus.propose(text)
                if not complete:risk.append("INCOMPLETE_SOURCE_TAIL")
                if name=="validation" and index==0:risk.append("UNKNOWN_VALIDATION_PREFIX_FRAGMENT")
                decision="HOLD" if risk else "EDIT" if candidate!=text else "KEEP"
                row_values.append(dict(id=name+":"+str(index),source=name,split="val" if name=="validation" else "train",
                    ordinal=index,source_ids=[len(data)//2,(len(data)+len(raw))//2],complete_eos=complete,
                    valid_utf8=True,text=text,input_ids=len(ids),source_ids_sha256=cache.hashlib.sha256(raw).hexdigest().upper(),
                    original_text_sha256=corpus.sha(text),candidate_text_sha256=corpus.sha(candidate),
                    automatic_decision=decision,review_reasons=risk))
                data+=raw
            path=root/"data_cache"/(name+".bin");path.write_bytes(data)
            spec=dict(name=name,split="val" if name=="validation" else "train",path=str(path.relative_to(root)),
                sha256=cache.file_sha(path),metadata=str(metadata.relative_to(root)),metadata_sha256=cache.file_sha(metadata),
                ids=len(data)//2,intervals=len(texts))
            inputs.append(spec)
            directory=base/"scan"/name/"unit_000000_attempt_000"
            writer=cache.ShardWriter(directory/"records","documents",limit=1_000_000)
            for row in row_values:writer.append(row)
            manifest=writer.close(lineage={"source_sha256":spec["sha256"]})
            counts=Counter(r["automatic_decision"] for r in row_values)
            counts.update(documents=len(texts),input_ids=len(data)//2)
            corpus.write_json(directory/"complete.json",dict(start_ids=0,end_ids=len(data)//2,
                start_ordinal=0,end_ordinal=len(texts),source_sha256=spec["sha256"],manifest=manifest,
                counts=dict(counts),before_signals={},before_proxy={}))
        corpus.write_json(base/"scope.json",dict(inputs=inputs,tokenizer=dict(path=str(tokenizer.relative_to(root)),sha256=cache.file_sha(tokenizer))))
        adoptions=base/"adoptions.json"
        corpus.write_json(adoptions,dict(schema="P106B_ROOT_TEXT_ADOPTIONS_V1",rows=[],reviews=[]))
        previous=root/"data_cache/previous_holds.json"
        source=next(s for s in inputs if s["name"]=="expanded_train")
        corpus.write_json(previous,dict(source_sha256=source["sha256"],holds=[dict(id="previous",
            original_text_sha256=corpus.sha("Previous explicit hold article."),match_scope="ALL_IDENTICAL_ORIGINAL_TEXT")]))
        return base,adoptions,previous

    def run_fixture(self,root,action):
        base,adoptions,holds=self.fixture(root)
        with ExitStack() as stack:
            stack.enter_context(patch.object(cache,"ROOT",root))
            stack.enter_context(patch.object(cache,"HOLDS",holds))
            stack.enter_context(patch.object(cache,"HOLD_SHA",cache.file_sha(holds)))
            stack.enter_context(patch.object(cache,"safe",lambda p:Path(p)))
            stack.enter_context(patch.object(corpus,"safe",lambda p:Path(p)))
            return action(base,adoptions)

    def test_full_build_duplicate_leakage_holds_and_independent_regeneration(self):
        with tempfile.TemporaryDirectory(prefix="cleanup_roundtrip_") as temp:
            def action(base,adoptions):
                report=cache.build(base,adoptions)
                self.assertEqual(report["counts"]["documents"],10)
                self.assertEqual(report["counts"]["EXCLUDE"],2)
                self.assertEqual(report["accepted"]["val"]["documents"],1)
                self.assertEqual(report["accepted"]["train"]["documents"],3)
                self.assertGreaterEqual(report["counts"]["HOLD"],4)
                proof=cache.verify_cache(base)
                self.assertTrue(proof["every_adopted_document_regenerated"])
                self.assertEqual(proof["exact_train_val_text_overlap"],0)
                self.assertFalse(proof["training_authorized"])
            self.run_fixture(Path(temp),action)

    def test_tampered_source_is_rejected_before_cache_creation(self):
        with tempfile.TemporaryDirectory(prefix="cleanup_source_tamper_") as temp:
            def action(base,adoptions):
                source=cache.read(base/"scope.json")["inputs"][0]
                (Path(temp)/source["path"]).write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError,"input or metadata changed"):
                    cache.build(base,adoptions)
                self.assertFalse((base/"cache_v1").exists())
            self.run_fixture(Path(temp),action)

    def test_completed_scan_is_required_and_partial_is_not_success(self):
        with tempfile.TemporaryDirectory(prefix="cleanup_missing_scope_") as temp:
            def action(base,adoptions):
                scope=cache.read(base/"scope.json")
                scope["inputs"][0]["ids"]+=1
                with self.assertRaisesRegex(ValueError,"full target is not scanned"):
                    cache.scan_coverage(base,scope)
            self.run_fixture(Path(temp),action)

    def test_cache_corruption_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="cleanup_cache_tamper_") as temp:
            def action(base,adoptions):
                report=cache.build(base,adoptions)
                first=report["manifests"]["tokens_train"]["shards"][0]
                path=base/"cache_v1/tokens/train"/first["path"]
                data=bytearray(path.read_bytes());data[0]^=1;path.write_bytes(data)
                with self.assertRaisesRegex(ValueError,"token shard dimensions/hash/order differ"):
                    cache.verify_cache(base)
            self.run_fixture(Path(temp),action)


if __name__=="__main__":
    unittest.main()
