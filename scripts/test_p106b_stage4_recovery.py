#!/usr/bin/env python3
"""CPU regression for source-order skew, paired-slot speed and actual exposure counts."""
from __future__ import annotations
import itertools
import sqlite3
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_balanced_public as source
from scripts import diag_p106b_concept_batch as batch
from scripts import diag_p106b_mixed_repeat4 as train
from tinylm.chat.canonical import normalize


def fixture(i, family="sourceA", tokens=10):
    return normalize({"messages": [{"role": "user", "content": f"question{i}"},
                                   {"role": "assistant", "content": "answer"}],
        "meta": {"parent_concept_id": f"{i:064X}", "language": "en", "source_split": "train",
                 "source_family": family, "processed_x_tokens": tokens, "assistant_targets": tokens // 2}})


def selected(order):
    c = sqlite3.connect(":memory:")
    source.initialize_index(c)
    for i, row in enumerate(order):
        source.index_row(c, row, 0, i)
    result = source.select_index(c, goal=100)
    keys = list(c.execute("SELECT prompt,choice FROM candidates WHERE selected=1 ORDER BY rank,prompt"))
    c.close()
    return keys, result


class RecoveryTests(unittest.TestCase):
    def test_source_and_row_order_do_not_select_early_families(self):
        rows = [fixture(i * 10 + j, f"source{i}") for i in range(5) for j in range(5)]
        a, ar = selected(rows)
        b, br = selected(list(reversed(rows)))
        self.assertEqual(a, b)
        self.assertEqual(ar, br)
        self.assertEqual(ar["nonpadding_tokens"]["train:en"], 100)
        self.assertTrue(all(v <= 25 for v in ar["family_tokens"].values()))

    def test_shortfall_never_relaxes_cap(self):
        keys, report = selected([fixture(i, "single_source") for i in range(100)])
        self.assertEqual(len(keys), 2)
        self.assertEqual(report["teacher_deficit_tokens"]["en"], 80)
        self.assertFalse(report["token_target_ready"])

    def test_duplicate_resolution_independent_of_encounter_order(self):
        a = fixture(1, "a")
        b = fixture(1, "b")
        self.assertEqual(selected([a, b])[0], selected([b, a])[0])
        self.assertEqual(selected([a, b])[1]["unique_prompt_groups"], 1)

    def test_shared_source_variants_cannot_evade_cap(self):
        self.assertEqual(source.family_bucket("oasst1"), source.family_bucket("oasst2"))
        self.assertEqual(source.family_bucket("aya:original-annotations"), source.family_bucket("Aya-Dataset"))
        self.assertEqual(source.family_bucket("Xlel_wd-inst"), source.family_bucket("Xlel_wd-inst (T)"))

    def test_prompt_has_no_literal_placeholder_fields(self):
        jobs = [{"target_language": "ko", "source_payload": {"question": "fixture"}}]
        prompt = batch.prompt(jobs, [2])[0]["content"]
        self.assertNotIn("<question>", prompt)
        self.assertNotIn("<answer>", prompt)
        self.assertNotIn("<id>", prompt)
        self.assertIn("[[ITEM_2]]", prompt)
        self.assertIn("BOTH", prompt)

    def test_xml_observation_preserves_legitimate_literal(self):
        c = {"user_text": "Explain <question> in XML", "assistant_text": "<answer> is a tag"}
        before = dict(c)
        self.assertTrue(all(batch.scaffold_observations(c).values()))
        self.assertEqual(c, before)

    def test_fast_missing_slots_are_not_speed_candidates(self):
        arms = [{"accepted_keys": [str(i) for i in range(8)]} for _ in range(6)]
        ratios = {"2": [1.1, 1.2], "4": [.9, 2]}
        self.assertEqual(batch.speed_candidates(arms, ratios), {"2": True, "4": False})
        arms[2]["accepted_keys"] = [str(i) for i in range(7)]
        self.assertFalse(any(batch.speed_candidates(arms, ratios).values()))

    def test_group_callback_counts_only_consumed_updates(self):
        counted = []
        stream = iter([([1, 2], [1, 2], 2) for _ in range(500)])
        groups = train.interleave_streams({"ko": stream}, 128,
                    on_group=lambda g, lang: counted.append((len(g), len(lang))))
        self.assertEqual(len(list(itertools.islice(groups, 2))), 2)
        self.assertEqual(counted, [(128, 128), (128, 128)])

    def test_wire_validation_has_both_languages_and_stable_order(self):
        rows = [fixture(i) for i in range(40)]
        for i, row in enumerate(rows):
            row["meta"]["language"] = "ko" if i < 20 else "en"
        a = train.validation_rows(iter(rows), 16)
        b = train.validation_rows(iter(reversed(rows)), 16)
        self.assertEqual(a, b)
        self.assertEqual(sum(r["meta"]["language"] == "ko" for r in a), 16)
        self.assertEqual(sum(r["meta"]["language"] == "en" for r in a), 16)

    def test_wire_validation_shortfall_is_explicit(self):
        with self.assertRaises(ValueError):
            train.validation_rows([fixture(1)], 16)

    def test_full_training_requires_matching_wire(self):
        valid = {"status": "WIRE_COMPLETE", "optimizer_updates": 2, "processed_train_row_exposures": 256,
                 "input": {"measurement_contract": "MIXED_COUNTS_VALIDATION_V2", "train_concat_sha256": "a", "val_concat_sha256": "b"}}
        train.require_wire_report(valid, "a", "b")
        for bad in ({**valid, "optimizer_updates": 0}, {**valid, "processed_train_row_exposures": 249217}):
            with self.assertRaises(ValueError):
                train.require_wire_report(bad, "a", "b")
        with self.assertRaises(ValueError):
            train.require_wire_report(valid, "other", "b")


if __name__ == "__main__":
    unittest.main()
