#!/usr/bin/env python3
"""CPU-only regression fixtures for multi-answer/parallel/queue/C4/prerequisite gates."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_multi_answer as multi
from scripts import p106b_pipeline as pipeline
from scripts import p106b_repeat4_gate as c4
from scripts import diag_p106b_parallel_gate as parallel
from scripts import diag_p106b_overlap_gate as overlap
from scripts import diag_p106b_integrated_gate as integrated
from scripts.p106b_gate_runtime import GateNegative, ToolFailure
from scripts.p106b_shards import verify
from tinylm.data.prepare import SyntheticTokenizer
from tinylm.data.sft import encode_conversation, sft_targets, IGNORE


def job(language="en"):
    return {"job_id": "fixture", "source_id": "fixture:1", "source_sha256": "A"*64,
        "source_license": "fixture-only", "target_language": language, "teacher_task": "repair",
        "source_payload": {"question": "What is2+2?", "answer": "4"},
        "source_repo": "fixture/repo", "source_revision": "fixture-revision",
        "source_transform": "teacher_repair", "parent_concept_id": "B"*64,
        "rights_status": "CARD_ONLY", "split": "train"}


def response(count=1, finish="stop"):
    final = "[[QUESTION]]\nWhat is2+2?\n[[/QUESTION]]\n"
    if count == 1:
        final += "[[ANSWER]]\n4 is the sum.\n[[/ANSWER]]"
    else:
        final += "\n".join(f"[[ANSWER_{i}]]\n4 is the sum; variant{i}.\n[[/ANSWER_{i}]]" for i in range(1, count+1))
    return {"choices": [{"finish_reason": finish, "message": {
        "content": final, "reasoning_content": "PRIVATE_SIDE_CAR"}}],
        "usage": {"completion_tokens": 40}}


class FakeSession:
    key = "fixture-key"
    def count_prompt(self, *_args):
        return {"decision": "DIRECT"}
    def complete(self, _messages, seed, _maximum):
        reply = response()
        reply["choices"][0]["message"]["content"] = reply["choices"][0]["message"]["content"].replace(
            "4 is the sum.", f"4 is the sum. variant{seed}.")
        return reply


class Tests(unittest.TestCase):
    def test_wire_rejects_extra_and_duplicate(self):
        parsed = multi.parse_multi(response(2), 2, "en")
        self.assertEqual(parsed["status"], "MULTI_FORMAT_READY")
        bad = response(2)
        bad["choices"][0]["message"]["content"] += "\nextra"
        self.assertIsNone(multi.parse_multi(bad, 2, "en")["parsed"])
        bad = response(2)
        bad["choices"][0]["message"]["content"] = bad["choices"][0]["message"]["content"].replace("variant2", "variant1")
        self.assertIsNone(multi.parse_multi(bad, 2, "en")["parsed"])

    def test_truncation_not_candidate(self):
        self.assertIsNone(multi.parse_multi(response(4, "length"), 4, "en")["parsed"])

    def test_variants_keep_concept_reasoning_outside_targets(self):
        parsed = multi.parse_multi(response(2), 2, "en")
        rows = multi.wrap_multi(job(), parsed, "fixture_generation", "C"*64, "HF/fixture/raw.jsonl#1")
        self.assertEqual({r["meta"]["parent_concept_id"] for r in rows}, {"B"*64})
        self.assertEqual({r["meta"]["source_split"] for r in rows}, {"train"})
        for row in rows:
            ids, labels, text = encode_conversation(row, SyntheticTokenizer(), "chatml")
            _, targets = sft_targets(ids, labels)
            self.assertNotIn("PRIVATE_SIDE_CAR", text)
            self.assertTrue(any(t == IGNORE for t in targets))
            self.assertTrue(any(t != IGNORE for t in targets))

    def test_single_wire_pipeline_and_thread_safe_shards(self):
        with tempfile.TemporaryDirectory(prefix="p106b_gate_fixture_") as temporary:
            base = Path(temporary)
            directory = base / "new"
            directory.mkdir()
            with patch.object(pipeline, "ROOT", base), patch("tokenizers.Tokenizer.from_file", return_value=SyntheticTokenizer()):
                writer = pipeline.CandidateWriter(directory, {"fixture": True})
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(lambda i: writer.request(FakeSession(), job(), f"fixture{i}", i), range(4)))
                duplicate = writer.request(FakeSession(), job(), "fixture_duplicate", 0)
                self.assertEqual(duplicate, [])
                summary = writer.close()
            self.assertEqual(summary["canonical_rows"], 4)
            self.assertEqual(summary["status_counts"]["EXACT_DUPLICATE"], 1)
            self.assertTrue(all(len(r) == 1 for r in results))
            for stem in ("raw", "canonical"):
                spec = json.loads((directory / f"{stem}_shards_manifest.json").read_text())
                verify(directory, spec)
            raw = json.loads((directory / "raw_000000.jsonl").read_text().splitlines()[0])
            self.assertFalse(raw["accepted_for_training"])

    def test_parallel_requires_both_order_pairs(self):
        parallel.self_test()

    def test_queue_bounds_cancel_and_text_identity(self):
        overlap.self_test()
        q = overlap.BoundedRows(threading.Event(), 64)
        with self.assertRaises(ValueError):
            q.put({"large": "x"*128})

    def test_same_prompt_different_concepts_do_not_cross_split(self):
        from tinylm.chat.canonical import normalize
        rows = [normalize({"messages": [{"role": "user", "content": f"question{i//2}"},
                 {"role": "assistant", "content": f"answer{i}"}],
                 "meta": {"source": "fixture", "source_id": str(i), "parent_concept_id": f"{i:064X}"}})
                for i in range(40)]
        train, val = c4.group_split(rows)
        self.assertFalse({json.dumps(r["messages"][0]["content"], sort_keys=True) for r in train}
                         & {json.dumps(r["messages"][0]["content"], sort_keys=True) for r in val})
        self.assertEqual(4*len(train), sum(len(train) for _ in range(4)))

    def test_stale_or_changed_parent_prerequisite_rejected(self):
        integrated.self_test()
        spec = integrated.GATES[0]
        with self.assertRaises(GateNegative):
            integrated.evidence_contract({"input": {"code_sha256": {}}}, spec, {}, "wrong")

    def test_monitor_failure_prevents_optimizer(self):
        obj = object.__new__(pipeline.StudentAccumulator)
        obj.targets, obj.rows, obj.micro_seconds = 100, 128, [0.1]*16
        touched = []
        obj.adam = SimpleNamespace(step=lambda: touched.append("adam"))
        obj.muon = SimpleNamespace(step=lambda: touched.append("muon"))
        def failed():
            raise ToolFailure("synthetic sampler timeout")
        obj.monitor = failed
        with self.assertRaises(ToolFailure):
            obj.finish(require_full=True)
        self.assertEqual(touched, [])

    def test_partial_accumulation_cannot_be_full_update(self):
        obj = object.__new__(pipeline.StudentAccumulator)
        obj.targets, obj.rows, obj.micro_seconds = 100, 120, [0.1]*15
        with self.assertRaises(ToolFailure):
            obj.finish(require_full=True)


if __name__ == "__main__":
    unittest.main()
