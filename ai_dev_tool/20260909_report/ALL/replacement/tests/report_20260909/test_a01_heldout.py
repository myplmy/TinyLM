import json
import tempfile
import unittest
from pathlib import Path
from tinylm.eval.heldout import adapt_heldout, normalize_version, source_path, export_cache, load_cache


class HeldoutContractTests(unittest.TestCase):
    def test_two_schemas(self):
        legacy = {"prompt": "질문", "candidates": ["가", "나", "다", "라"], "correct_index": 2}
        modern = {"ctx": "질문", "choices": ["가", "나", "다", "라"], "gold": 2}
        self.assertEqual(adapt_heldout(legacy)["choices"], adapt_heldout(modern)["choices"])

    def test_invalid_gold_and_duplicate(self):
        for gold, choices in [(True, ["가", "나", "다", "라"]),
                              (-1, ["가", "나", "다", "라"]),
                              (0, ["가", " 가 ", "다", "라"])]:
            with self.assertRaises(ValueError):
                adapt_heldout({"ctx": "질문", "choices": choices, "gold": gold})

    def test_explicit_version(self):
        self.assertEqual(normalize_version("v2.8"), "2.8")
        with self.assertRaises(ValueError):
            normalize_version("latest")

    def test_v28_full_count_cache_and_tampering(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = source_path(root, "2.8")
            source.parent.mkdir(parents=True)
            rows = [{"id": str(i), "ctx": f"질문 {i}", "choices": ["가", "나", "다", "라"], "gold": 0}
                    for i in range(4500)]
            source.write_text(json.dumps({"records": rows}), encoding="utf-8")
            dest, n, meta = export_cache(root, "2.8")
            self.assertEqual(n, 4500)
            self.assertEqual(len(load_cache(root, "2.8")[0]), 4500)
            self.assertIn("warnings", meta["semantic_status"])
            with dest.open("a", encoding="utf-8") as f:
                f.write("{}\n")
            with self.assertRaises(ValueError):
                load_cache(root, "2.8")

    def test_missing_cache_metadata_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(FileNotFoundError):
                load_cache(name, "2.7")
