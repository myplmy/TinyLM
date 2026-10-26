"""Small CPU contract tests for the actual-window adapter, not model quality."""
import importlib.util
from pathlib import Path
import unittest
import time
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("actual_exposure", Path(__file__).with_name("audit_actual_exposure.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExposureTests(unittest.TestCase):
    def test_targets_shift_one_and_keep_exact_width(self):
        values = list(range(12))
        self.assertEqual(values[slice(*module.target_span(2, 12, 4))], [3, 4, 5, 6])
        self.assertEqual(values[slice(*module.target_span(7, 12, 4))], [8, 9, 10, 11])

    def test_invalid_offsets_and_bool_are_not_silently_clipped(self):
        for args in [(-1, 12, 4), (8, 12, 4), (True, 12, 4), (0, 12, 0), (0, 12.0, 4)]:
            with self.assertRaises(ValueError):
                module.target_span(*args)

    def test_partial_boundary_headings_do_not_count(self):
        info, headings, count = module.window_signals("각주" + chr(10) + "실제 내용" + chr(10) + "외부 링크")
        self.assertEqual(headings, {})
        self.assertEqual(count, 1)

    def test_complete_heading_uses_existing_signal(self):
        text = chr(10).join(["boundary", "각주", "내용입니다", "boundary"])
        info, headings, _ = module.window_signals(text)
        self.assertEqual(info["standalone_heading_lines"], 1)
        self.assertEqual(headings, {"각주": 1})

    def test_prose_mentions_are_not_standalone_headings(self):
        text = chr(10).join(["boundary", "각주를 읽으세요", "외부 링크가 있습니다", "boundary"])
        self.assertNotIn("standalone_heading_lines", module.window_signals(text)[0])

    def test_complete_code_fence_is_preserved_and_excluded(self):
        text = chr(10).join(["boundary", "```text", "각주", "```", "boundary"])
        self.assertEqual(module.window_signals(text)[1], {})
        self.assertIn("각주", text)

    def test_requested_repeated_lines_are_observations_not_removed(self):
        text = chr(10).join(["boundary", "반복을 요청한 문장", "반복을 요청한 문장", "boundary"])
        info, _, _ = module.window_signals(text)
        self.assertEqual(info["within_segment_repeated_line_extras"], 1)
        self.assertEqual(text.count("반복을 요청한 문장"), 2)

    def test_different_values_are_not_identical_repeated_lines(self):
        text = chr(10).join(["boundary", "대상 A는 사과입니다", "대상 A는 당근입니다", "boundary"])
        self.assertNotIn("within_segment_repeated_line_extras", module.window_signals(text)[0])

    def test_shared_signal_implementation_is_reused(self):
        from scripts.p106b_native_text_audit import signals
        self.assertIs(module.signals, signals)

    def test_eos_splits_complete_and_partial_document_boundaries(self):
        self.assertEqual(module.segment_ranges(6, [2, 4]), [(0, 2, False, True), (3, 4, True, True), (5, 6, True, False)])
        self.assertEqual(module.segment_ranges(5, [0, 4]), [(1, 4, True, True)])

    def test_bad_eos_positions_are_rejected(self):
        for length, ends in [(5, [5]), (5, [2, 1]), (5, [2, 2]), (5, [True])]:
            with self.assertRaises(ValueError):
                module.segment_ranges(length, ends)

    def test_eos_bounded_single_heading_is_complete(self):
        self.assertEqual(module.window_signals("각주", left_complete=True, right_complete=True)[1], {"각주": 1})

    def test_distinct_documents_do_not_create_within_document_repetition(self):
        first = module.window_signals("같은 문장을 요청했습니다", left_complete=True, right_complete=True)[0]
        second = module.window_signals("같은 문장을 요청했습니다", left_complete=True, right_complete=True)[0]
        self.assertNotIn("within_segment_repeated_line_extras", first)
        self.assertNotIn("within_segment_repeated_line_extras", second)

    def test_full_target_adapter_keeps_real_html_and_excludes_eos_metadata(self):
        import numpy as np
        from tokenizers import Tokenizer, models
        tokenizer = Tokenizer(models.WordLevel({"[UNK]": 0, "<eos>": 2, "<br>": 3, "x": 4}, unk_token="[UNK]"))
        ids = np.array([0, 2, 3, 2] + [4] * 1021, dtype="<u2")
        with patch.object(module, "DEADLINE", float("inf")):
            result, samples = module.scan(ids, tokenizer, np.array([0]), 1, time.monotonic() + 10)
        self.assertEqual(result["target_tokens"], 1024)
        self.assertEqual(result["totals"]["eos_target_tokens"], 2)
        self.assertEqual(result["totals"]["html_tag_occurrences"], 1)
        self.assertIn("<eos>", samples[0]["text"])
        self.assertIn("<br>", samples[0]["text"])

    def test_code_fence_at_both_crop_edges_does_not_expose_heading(self):
        text = chr(10).join(["```text", "각주", "```"])
        self.assertEqual(module.window_signals(text)[1], {})
        self.assertIn("각주", text)

    def test_code_mask_preserves_following_real_heading(self):
        text = chr(10).join(["```text", "각주", "```", "외부 링크", ""])
        self.assertEqual(module.window_signals(text)[1], {"외부 링크": 1})

    def test_actual_training_fingerprints_are_all_required(self):
        profile = {"tokenizer": {"sha256": "C" * 64}}
        worker = {"profile_sha256": "A" * 64, "pair_complete_sha256": "B" * 64,
            "geometry_and_token_metadata": {"tokenizer_sha256": "C" * 64}, "offsets": {"pool_tokens": 2048}}
        module.validate_training_link(worker, profile, "A" * 64, "B" * 64, 2048)
        for key in worker:
            bad = {name: value for name, value in worker.items() if name != key}
            with self.assertRaises(ValueError):
                module.validate_training_link(bad, profile, "A" * 64, "B" * 64, 2048)

    def test_postscan_budget_rejects_publication_at_reserve(self):
        with patch.object(module.time, "time", return_value=module.DEADLINE - 10):
            with self.assertRaises(ValueError):
                module.publication_budget()


if __name__ == "__main__":
    unittest.main(verbosity=2)
