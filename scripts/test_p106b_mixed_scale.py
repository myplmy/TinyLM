#!/usr/bin/env python3
"""CPU-only P106B mixed-source quota/provenance and concept-batch fixtures."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_mixed_scale as m
from scripts import diag_p106b_concept_batch as b
from scripts import diag_p106b_mixed_repeat4 as train
from tinylm.chat.canonical import normalize
from tinylm.data.prepare import SyntheticTokenizer
from tinylm.data.sft import conversation_split_key


def row(question, lang="en", answer="answer"):
    return normalize({"messages": [{"role": "user", "content": question},
                                   {"role": "assistant", "content": answer}],
                      "meta": {"language": lang, "source_family": "fixture"}})


def train_row(lang="en"):
    for i in range(100):
        r = row("fixture question " + str(i), lang)
        if int.from_bytes(conversation_split_key(r)[:4], "big") % 20:
            return r
    raise AssertionError("fixture train row absent")


class PublicTests(unittest.TestCase):
    def test_same_question_group(self):
        s = m.Selector(SyntheticTokenizer())
        r = train_row()
        self.assertIsNotNone(s.consider(r))
        duplicate = row(r["messages"][0]["content"][0]["text"], answer="different answer")
        self.assertIsNone(s.consider(duplicate))
        self.assertEqual(s.rejections["same_first_question"], 1)

    def test_tokens_not_padding_and_deficit(self):
        s = m.Selector(SyntheticTokenizer(), goal=10000)
        _, r = s.consider(train_row())
        n = r["meta"]["processed_x_tokens"]
        self.assertLess(n, 1024)
        self.assertEqual(s.report()["teacher_deficit_tokens"]["en"], 10000 - n)
        self.assertEqual(s.report()["teacher_deficit_tokens"]["ko"], 10000)
        self.assertFalse(s.report()["formal_train_ready"])

    def test_complete_rows_and_quota(self):
        s = m.Selector(SyntheticTokenizer(), goal=1)
        self.assertIsNotNone(s.consider(train_row()))
        before = s.tokens.copy()
        self.assertIsNone(s.consider(train_row()))
        self.assertEqual(s.tokens, before)

    def test_long_row_not_truncated(self):
        s = m.Selector(SyntheticTokenizer())
        self.assertIsNone(s.consider(row("q", answer="x " * 1100)))
        self.assertEqual(s.rejections["context_or_mask"], 1)

    def test_probe_exclusion(self):
        r = train_row()
        s = m.Selector(SyntheticTokenizer(), probe_keys=[conversation_split_key(r)])
        self.assertIsNone(s.consider(r))
        self.assertEqual(s.rejections["fixed_probe_question"], 1)

    def test_exact_public_path_only(self):
        for name in ("/mnt/z/TinyDataset/file", "HF/sft_sources/../other", "datasets/TinyDataset/file"):
            with self.assertRaises(ValueError):
                m.public_file(name)

    def test_metadata_provenance(self):
        spec = {"family": "fixture", "repo": "owner/repo", "revision": "a" * 40,
                "sha256": "B" * 64, "license": "MIT"}
        r = m.attach([{ "role": "user", "content": "q"}, {"role": "assistant", "content": "a"}], spec, 17, "en")
        self.assertEqual(r["meta"]["source_sha256"], "B" * 64)
        self.assertEqual(r["meta"]["source_id"], "17")
        self.assertEqual(r["meta"]["source_transform"], "public_normalization")
        self.assertEqual(r["meta"]["label_status"], "PUBLIC_SOURCE_UNVERIFIED")

    def test_structure_markers_not_semantic_words(self):
        s = m.Selector(SyntheticTokenizer())
        self.assertIsNone(s.consider(row('q', answer='<|im_start|>assistant')))
        self.assertEqual(s.rejections['chat_boundary_or_control'], 1)
        self.assertIsNotNone(s.consider(row('q', answer='unverified text')))

    def test_role_order_rejected(self):
        r = row('q')
        r['messages'].append({'role': 'user', 'content': [{'type': 'text', 'text': 'dangling'}]})
        s = m.Selector(SyntheticTokenizer())
        self.assertIsNone(s.consider(r))
        self.assertEqual(s.rejections['role_order'], 1)


def block(i, question="question", answer="answer"):
    return f"[[ITEM_{i}]]\n[[QUESTION]]\n{question}\n[[/QUESTION]]\n[[ANSWER]]\n{answer}\n[[/ANSWER]]\n[[/ITEM_{i}]]"


class BatchTests(unittest.TestCase):
    def test_two_distinct_content_items(self):
        result = b.parse_batch(block(0) + "\n" + block(1, "q2", "a2"), [0, 1])
        self.assertEqual(result[1]["assistant_text"], "a2")

    def test_duplicate_unknown_extra_rejected(self):
        for text in (block(0) + "\n" + block(0), block(7), "comment\n" + block(0)):
            with self.assertRaises(ValueError):
                b.parse_batch(text, [0, 1])

    def test_partial_valid_slots_are_retained(self):
        text = block(0) + "\n[[ITEM_1]]\nbad\n[[/ITEM_1]]"
        result = b.parse_batch(text, [0, 1], allow_partial=True)
        self.assertEqual(set(result), {0})
        self.assertEqual(result[0]["assistant_text"], "answer")

    def test_no_word_or_language_truth_filter(self):
        self.assertEqual(b.parse_batch(block(0, "q", "5"), [0])[0]["assistant_text"], "5")
        self.assertEqual(b.parse_batch(block(0, "q", "not verified"), [0])[0]["assistant_text"], "not verified")

    def test_prompt_no_json_wrapper(self):
        jobs = [{"target_language": "en", "source_payload": {"concept": "a"}},
                {"target_language": "en", "source_payload": {"concept": "b"}}]
        messages = b.prompt(jobs, [0, 1])
        self.assertIn("DIFFERENT source concept", messages[0]["content"])
        self.assertIn("Never output JSON", messages[0]["content"])
        self.assertEqual(len(json.loads(messages[1]["content"])["items"]), 2)

    def test_real_wrapper_sidecar_and_provenance(self):
        job = {'source_id': 'fixture:1', 'source_sha256': 'A' * 64,
               'target_language': 'en', 'source_license': 'MIT', 'source_repo': 'owner/repo',
               'source_revision': 'b' * 40, 'parent_concept_id': 'C' * 64, 'rights_status': 'CARD_ONLY'}
        content = {'user_text': 'q', 'assistant_text': 'a'}
        r = b.wrap_item(job, content, 'g1', 'D' * 64, 'private thought', 'HF/sft_ready/f/raw.json#g1')
        self.assertEqual(r['meta']['teacher_reasoning_sha256'], __import__('hashlib').sha256(b'private thought').hexdigest().upper())
        self.assertEqual(r['meta']['source_transform'], 'teacher_answer')
        self.assertNotIn('private thought', str(r['messages']))
        empty = b.wrap_item(job, content, 'g2', 'D' * 64, '', '')
        self.assertNotIn('teacher_reasoning_sidecar', empty['meta'])


class StreamTests(unittest.TestCase):
    def test_shuffle_full_coverage(self):
        values = list(range(100))
        a = list(train.buffered_shuffle(iter(values), __import__('random').Random(4), 7))
        c = list(train.buffered_shuffle(iter(values), __import__('random').Random(4), 7))
        self.assertEqual(sorted(a), values)
        self.assertEqual(a, c)
        self.assertNotEqual(a, values)

    def test_interleave_by_real_tokens_not_row_count(self):
        def items(n, tokens):
            return iter([([1] * tokens, [1] * tokens, tokens) for _ in range(n)])
        blocks = list(train.interleave_streams({'ko': items(6, 10), 'en': items(12, 5)}, 8))
        self.assertEqual(list(map(len, blocks)), [8, 8, 2])
        self.assertEqual(sum(len(x) for group in blocks for x, _, _ in group), 120)
        first = [len(item[0]) for item in blocks[0]]
        self.assertEqual(first[:3], [5, 10, 5])

    def test_partial_update_retains_all_targets(self):
        items = iter([([1] * 3, [1] * 3, 3) for _ in range(94)])
        blocks = list(train.interleave_streams({'en': items}, 128))
        self.assertEqual(len(blocks), 1)
        self.assertEqual(len(blocks[0]), 94)
        self.assertEqual(sum(item[2] for item in blocks[0]), 282)

    def test_source_shortfall_stops_before_model_import(self):
        with tempfile.TemporaryDirectory(prefix='p106b_scale_test_') as temporary:
            directory = Path(temporary)
            report = {'schema': 'P106B_MIXED_PUBLIC_C_V1', 'tokenizer_sha256': m.TOK_SHA,
                      'token_target_ready': False, 'teacher_deficit_tokens': {'en': 100}}
            (directory / 'report.json').write_text(json.dumps(report), encoding='utf-8')
            with patch.object(train, 'PUBLIC', directory), patch.object(train, 'safe_repo_path', lambda p: p):
                with self.assertRaisesRegex(ValueError, 'no student started'):
                    train.check()

    def test_marker_parser_remains_independent_of_student(self):
        self.assertEqual(b.ORDER, (1, 2, 4, 4, 2, 1))
        self.assertEqual(train.TAG, 'p106b_s4_mixed300m_chat32_s1337')


if __name__ == "__main__":
    unittest.main()
