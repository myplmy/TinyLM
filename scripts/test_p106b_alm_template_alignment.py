"""다른 template의 같은 답 본문에 대한 순수 합성 CPU 회귀."""
from dataclasses import FrozenInstanceError, asdict, replace
from importlib import reload
from itertools import product
import builtins
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import p106b_alm_bytes as old
from scripts import p106b_alm_template_alignment as m
from scripts.test_p106b_alm_bytes import student, teacher


def pair(body, student_parts, teacher_parts):
    """본문만 supervised인 서로 다른 합성 prefix/suffix. 실제 template가 아니다."""
    content = body.encode("utf-8")
    left = student("P" + body + "!", [b"P", *student_parts, b"!"],
                   keep=[False, *([True] * len(student_parts)), False],
                   turns=[0, *([1] * len(student_parts)), 0])
    right = teacher("QQ" + body + "?", [b"Q", b"Q", *teacher_parts, b"?"],
                    keep=[False, False, *([True] * len(teacher_parts)), False],
                    turns=[0, 0, *([1] * len(teacher_parts)), 0])
    return left, right, (1, 1 + len(content)), (2, 2 + len(content))


def align(values):
    return m.align_answer_contents(*values)


def partitions(raw):
    for cuts in product((False, True), repeat=len(raw) - 1):
        points = [0] + [index + 1 for index, yes in enumerate(cuts) if yes] + [len(raw)]
        yield [raw[left:right] for left, right in zip(points, points[1:])]


class ScopeAndContentTests(unittest.TestCase):
    def test_different_full_templates_align_only_explicit_equal_answer(self):
        values = pair("abc", [b"a", b"bc"], [b"ab", b"c"])
        result = align(values)
        self.assertNotEqual(values[0].text_utf8, values[1].text_utf8)
        self.assertEqual([c.data for c in result.chunks], [b"abc"])
        self.assertEqual(result.alignment_scope, "ANSWER_CONTENT_BYTES_ONLY")
        self.assertEqual(result.student_span, (1, 4))
        self.assertEqual(result.teacher_span, (2, 5))
        self.assertEqual((result.student_input_byte_count, result.teacher_input_byte_count), (5, 6))
        self.assertEqual((result.answer_byte_count, result.covered_byte_count,
                          result.uncovered_byte_count), (3, 3, 0))
        with self.assertRaises(old.ByteAlignmentError):
            old.align_assistant_chunks(values[0], values[1])

    def test_each_full_stream_still_must_reconstruct_its_original_bytes(self):
        values = pair("ab", [b"a", b"b"], [b"ab"])
        for side in (0, 1):
            forged = list(values)
            forged[side] = replace(values[side], text_utf8=values[side].text_utf8 + b"X")
            with self.subTest(side=side), self.assertRaises(old.ByteAlignmentError):
                align(tuple(forged))

    def test_forged_outside_answer_token_is_not_ignored(self):
        values = pair("ab", [b"ab"], [b"ab"])
        broken = replace(values[0].tokens[0], data=b"X")
        left = replace(values[0], tokens=(broken, *values[0].tokens[1:]))
        with self.assertRaises(old.ByteAlignmentError):
            align((left, *values[1:]))

    def test_same_length_different_answer_bytes_fail(self):
        values = pair("ab", [b"ab"], [b"ab"])
        right = teacher("QQac?", [b"Q", b"Q", b"ac", b"?"],
                        keep=[False, False, True, False], turns=[0, 0, 1, 0])
        with self.assertRaisesRegex(old.ByteAlignmentError, "content bytes differ"):
            align((values[0], right, values[2], values[3]))

    def test_answer_whitespace_is_never_stripped(self):
        values = pair(" a\n ", [b" ", b"a", b"\n "], [b" a", b"\n", b" "])
        self.assertEqual(b"".join(c.data for c in align(values).chunks), b" a\n ")
        with self.assertRaisesRegex(old.ByteAlignmentError, "content bytes differ"):
            align((values[0], values[1], (2, 5), (2, 5)))

    def test_unicode_normalization_is_not_an_equivalence(self):
        left = student("Pé", [b"P", "é".encode("utf-8")])
        right = teacher("QQe\u0301", [b"QQ", "e\u0301"])
        with self.assertRaises(old.ByteAlignmentError):
            align((left, right, (1, 3), (2, 5)))

    def test_swapped_stream_roles_fail(self):
        left, right, ls, rs = pair("ab", [b"ab"], [b"ab"])
        with self.assertRaisesRegex(old.ByteAlignmentError, "roles were swapped"):
            align((right, left, rs, ls))

    def test_bad_span_types_ranges_and_empty_answers_fail(self):
        left, right, ls, rs = pair("ab", [b"ab"], [b"ab"])
        for invalid in (None, "1:3", (1,), (1, 2, 3), (True, 3),
                        (1., 3), (-1, 3), (1, 99), (2, 1), (1, 1)):
            for side in (0, 1):
                with self.subTest(invalid=invalid, side=side), self.assertRaises(old.ByteAlignmentError):
                    align((left, right, invalid if side == 0 else ls,
                           invalid if side == 1 else rs))

    def test_mutable_span_argument_is_snapshotted_not_retained(self):
        left, right, ls, rs = pair("ab", [b"ab"], [b"ab"])
        mutable = list(ls)
        result = align((left, right, mutable, rs))
        mutable[0] = 0
        self.assertEqual(result.student_span, ls)

    def test_alignment_and_json_metadata_wrapper_reuses_original_contract(self):
        result = align(pair("ab", [b"a", b"b"], [b"ab"]))
        self.assertIsInstance(result.alignment, old.AlignmentResult)
        self.assertEqual(result.alignment.chunks, result.chunks)
        self.assertEqual(result.alignment.input_byte_count, result.answer_byte_count)
        metadata = json.loads(json.dumps(result.metadata, allow_nan=False))
        self.assertFalse(metadata["full_template_equality_claim"])
        self.assertEqual(metadata["student_span"], [1, 3])
        self.assertEqual(metadata["teacher_span"], [2, 4])
        self.assertEqual(metadata["accepted_ranges"][0]["student_span"], [1, 3])
        self.assertEqual(metadata["accepted_ranges"][0]["teacher_span"], [2, 4])
        mutable = result.metadata
        mutable["student_span"][0] = 0
        self.assertEqual(result.metadata["student_span"], [1, 3])

    def test_rejection_metadata_contains_boundary_reason_and_absolute_ranges(self):
        left = student("Pa", [b"Pa"], keep=[True], turns=[1])
        right = teacher("QQa", [b"QQ", b"a"])
        result = align((left, right, (1, 2), (2, 3)))
        metadata = json.loads(json.dumps(result.metadata, allow_nan=False))
        self.assertEqual(metadata["uncovered_byte_count"], 1)
        self.assertEqual(metadata["student_boundary_crossing_indices"], [0])
        self.assertEqual(metadata["rejected_ranges"][0]["student_span"], [1, 2])
        self.assertEqual(metadata["rejected_ranges"][0]["teacher_span"], [2, 3])
        self.assertIn("student_boundary_crossing", metadata["rejected_ranges"][0]["reasons"])

    def test_import_has_no_heavy_library_or_external_action(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "tokenizers", "transformers", "numpy", "requests"}:
                raise AssertionError("순수 helper가 무거운 패키지를 가져옴: " + name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded), \
                patch("subprocess.run", side_effect=AssertionError("외부 명령 실행")), \
                patch("pathlib.Path.open", side_effect=AssertionError("자산 열람")):
            reload(m)


class NativeBoundaryTests(unittest.TestCase):
    def test_shortest_intersection_not_token_count_or_unicode_character_count(self):
        values = pair("abcd", [b"a", b"b", b"cd"], [b"ab", b"c", b"d"])
        result = align(values)
        self.assertEqual([c.data for c in result.chunks], [b"ab", b"cd"])
        self.assertEqual(result.common_answer_boundaries, (0, 2, 4))
        self.assertEqual(result.chunks[0].student_raw_indices, (1, 2))
        self.assertEqual(result.chunks[0].teacher_raw_indices, (2,))

    def test_korean_fragment_tokens_preserve_all_bytes(self):
        ga, na = "가".encode("utf-8"), "나".encode("utf-8")
        result = align(pair("가 나\n", [ga[:1], ga[1:], b" ", na, b"\n"],
                            [ga, b" ", na[:1], na[1:], b"\n"]))
        self.assertEqual([c.data for c in result.chunks], [ga, b" ", na, b"\n"])
        self.assertEqual(result.covered_byte_count, 8)

    def test_common_native_boundary_inside_korean_character_is_legal(self):
        ga = "가".encode("utf-8")
        result = align(pair("가", [ga[:1], ga[1:]], [ga[:1], ga[1:]]))
        self.assertEqual([c.data for c in result.chunks], [ga[:1], ga[1:]])
        with self.assertRaises(UnicodeDecodeError):
            result.chunks[0].data.decode("utf-8")

    def test_different_absolute_offsets_and_shift_maps_are_preserved(self):
        result = align(pair("ab", [b"a", b"b"], [b"a", b"b"]))
        first = result.chunks[0]
        self.assertIsInstance(first, old.AlignedChunk)
        self.assertEqual((first.byte_start, first.byte_end), (0, 1))
        self.assertEqual((first.student_byte_start, first.student_byte_end), (1, 2))
        self.assertEqual((first.teacher_byte_start, first.teacher_byte_end), (2, 3))
        self.assertEqual(first.student_raw_indices, (1,))
        self.assertEqual(first.teacher_raw_indices, (2,))
        self.assertEqual(first.student_shifted_indices, (0,))
        self.assertEqual(first.teacher_shifted_indices, (1,))
        self.assertIsInstance(first.student_shifted_indices, old.ShiftedTargetIndices)
        with self.assertRaises(old.ByteAlignmentError):
            old.raw_to_shifted(first.student_shifted_indices)

    def test_student_left_boundary_crossing_is_not_partially_scored(self):
        left = student("Pabc!", [b"Pa", b"b", b"c", b"!"])
        right = teacher("QQabc?", [b"QQ", b"a", b"b", b"c", b"?"])
        result = align((left, right, (1, 4), (2, 5)))
        self.assertEqual([c.data for c in result.chunks], [b"b", b"c"])
        self.assertEqual(result.student_boundary_crossing_indices, (0,))
        self.assertEqual(result.teacher_boundary_crossing_indices, ())
        self.assertEqual(result.student_uncovered_ranges, ((1, 2),))
        self.assertEqual(result.teacher_uncovered_ranges, ((2, 3),))
        self.assertEqual((result.covered_byte_count, result.uncovered_byte_count,
                          result.boundary_uncovered_byte_count), (2, 1, 1))
        self.assertIn("student_boundary_crossing", result.rejected[0].reasons)
        self.assertEqual(result.rejected[0].student_raw_indices, (0,))

    def test_teacher_right_boundary_crossing_is_not_partially_scored(self):
        left = student("Pabc!", [b"P", b"a", b"b", b"c", b"!"])
        right = teacher("QQabc?", [b"QQ", b"a", b"b", b"c?"])
        result = align((left, right, (1, 4), (2, 5)))
        self.assertEqual([c.data for c in result.chunks], [b"a", b"b"])
        self.assertEqual(result.teacher_boundary_crossing_indices, (3,))
        self.assertEqual(result.student_uncovered_ranges, ((3, 4),))
        self.assertEqual(result.teacher_uncovered_ranges, ((4, 5),))
        self.assertIn("teacher_boundary_crossing", result.rejected[-1].reasons)

    def test_both_boundaries_crossed_no_fake_alignment_or_error_replacement(self):
        left = student("Pabc!", [b"Pabc!"], keep=[True], turns=[1])
        right = teacher("QQabc?", [b"QQabc?"], keep=[True], turns=[1])
        result = align((left, right, (1, 4), (2, 5)))
        self.assertEqual(result.chunks, ())
        self.assertEqual(result.common_answer_boundaries, ())
        self.assertEqual(result.uncovered_byte_count, 3)
        self.assertIn("student_boundary_crossing", result.rejected[0].reasons)
        self.assertIn("teacher_boundary_crossing", result.rejected[0].reasons)

    def test_boundary_crossing_inside_korean_character_reports_missing_byte(self):
        ga = "가".encode("utf-8")
        left = student("P가", [b"P" + ga[:1], ga[1:]],
                       keep=[False, True], turns=[0, 1])
        right = teacher("QQ가", [b"QQ", ga[:1], ga[1:]])
        result = align((left, right, (1, 4), (2, 5)))
        self.assertEqual([c.data for c in result.chunks], [ga[1:]])
        self.assertEqual((result.covered_byte_count, result.uncovered_byte_count), (2, 1))
        self.assertEqual(result.student_uncovered_ranges, ((1, 2),))

    def test_all_small_native_segmentations_use_exact_common_boundaries(self):
        # 341개 분절 쌍. prefix/suffix를 제외한 원 native pieces만 비교한다.
        for length in range(1, 6):
            raw = b"abcde"[:length]
            for sp in partitions(raw):
                for tp in partitions(raw):
                    with self.subTest(length=length, sp=sp, tp=tp):
                        result = align(pair(raw.decode("ascii"), sp, tp))
                        sb = {0}
                        tb = {0}
                        for parts, points in ((sp, sb), (tp, tb)):
                            cursor = 0
                            for part in parts:
                                cursor += len(part)
                                points.add(cursor)
                        bounds = sorted(sb & tb)
                        self.assertEqual([(c.byte_start, c.byte_end) for c in result.chunks],
                                         list(zip(bounds, bounds[1:])))
                        self.assertEqual(b"".join(c.data for c in result.chunks), raw)
                        self.assertEqual(result.uncovered_byte_count, 0)


class MaskTurnAndSpecialTests(unittest.TestCase):
    def test_eot_outside_content_keeps_native_metadata_but_not_kd(self):
        left = student("Pa<E>", [b"P", b"a", "<E>"],
                       keep=[False, True, True], turns=[0, 1, 1],
                       specials=[old.SpecialToken(2, 102, "EOT", b"<E>")])
        right = teacher("QQa<END>", [b"QQ", b"a", "<END>"],
                        keep=[False, True, True], turns=[0, 1, 1],
                        specials=[old.SpecialToken(2, 202, "EOT", b"<END>")])
        result = align((left, right, (1, 2), (2, 3)))
        self.assertEqual([c.data for c in result.chunks], [b"a"])
        self.assertEqual(result.student_special_indices, (2,))
        self.assertEqual(result.teacher_special_indices, (2,))
        self.assertNotIn(2, result.chunks[0].student_raw_indices)

    def test_literal_special_inside_selected_content_is_rejected(self):
        left = student("Pa<E>", [b"P", b"a", "<E>"],
                       specials=[old.SpecialToken(2, 102, "EOT", b"<E>")])
        right = teacher("QQa<E>", [b"QQ", b"a", "<E>"],
                        specials=[old.SpecialToken(2, 202, "EOT", b"<E>")])
        result = align((left, right, (1, 5), (2, 6)))
        self.assertEqual([c.data for c in result.chunks], [b"a"])
        self.assertEqual(result.uncovered_byte_count, 3)
        self.assertIn("special_token", result.rejected[-1].reasons)
        self.assertIsInstance(result.rejected[-1], old.RejectedChunk)

    def test_zero_bos_and_eot_preserve_full_raw_indices(self):
        left = student("Pa", [None, b"P", b"a", None],
                       keep=[False, False, True, True], turns=[0, 0, 1, 1],
                       specials=[old.SpecialToken(0, 100, "BOS", b""),
                                 old.SpecialToken(3, 103, "EOT", b"")])
        right = teacher("QQa", [None, b"QQ", b"a", None],
                        keep=[False, False, True, True], turns=[0, 0, 1, 1],
                        specials=[old.SpecialToken(0, 200, "BOS", b""),
                                  old.SpecialToken(3, 203, "EOT", b"")])
        result = align((left, right, (1, 2), (2, 3)))
        self.assertEqual(result.chunks[0].student_raw_indices, (2,))
        self.assertEqual(result.chunks[0].student_shifted_indices, (1,))
        self.assertEqual(result.student_special_indices, (0, 3))
        self.assertEqual(result.uncovered_byte_count, 0)
        self.assertEqual(result.rejected[-1].byte_start, result.rejected[-1].byte_end)
        self.assertIn("zero_byte_special_at_boundary", result.rejected[-1].reasons)

    def test_zero_special_at_common_boundary_does_not_poison_neighbors(self):
        left = student("Pab", [b"P", b"a", None, b"b"],
                       keep=[False, True, False, True], turns=[0, 1, 0, 1],
                       specials=[old.SpecialToken(2, 102, "CONTROL", b"")])
        right = teacher("QQab", [b"QQ", b"a", b"b"])
        result = align((left, right, (1, 3), (2, 4)))
        self.assertEqual([c.data for c in result.chunks], [b"a", b"b"])
        self.assertEqual([c.student_raw_indices for c in result.chunks], [(1,), (3,)])
        self.assertEqual(result.rejected[0].student_raw_indices, (2,))
        self.assertEqual(result.rejected[0].teacher_raw_indices, ())
        self.assertEqual((result.rejected[0].student_byte_start,
                          result.rejected[0].teacher_byte_start), (2, 3))
        self.assertEqual(result.uncovered_byte_count, 0)

    def test_interior_zero_special_rejects_entire_many_to_one_candidate(self):
        left = student("Pab", [b"P", b"a", None, b"b"],
                       keep=[False, True, False, True], turns=[0, 1, 0, 1],
                       specials=[old.SpecialToken(2, 102, "CONTROL", b"")])
        right = teacher("QQab", [b"QQ", b"ab"])
        result = align((left, right, (1, 3), (2, 4)))
        self.assertEqual(result.chunks, ())
        self.assertEqual(result.uncovered_byte_count, 2)
        self.assertEqual(result.rejected[0].student_raw_indices, (1, 2, 3))
        self.assertIn("special_token", result.rejected[0].reasons)

    def test_unsupervised_token_on_either_side_rejects_whole_candidate(self):
        left, right, ls, rs = pair("ab", [b"ab"], [b"ab"])
        for side in (0, 1):
            values = [left, right, ls, rs]
            stream = values[side]
            index = 1 if side == 0 else 2
            changed = list(stream.tokens)
            changed[index] = replace(changed[index], supervised=False, turn_id=0)
            values[side] = replace(stream, tokens=tuple(changed))
            with self.subTest(side=side):
                result = align(tuple(values))
                self.assertEqual(result.chunks, ())
                self.assertIn("unsupervised_token", result.rejected[0].reasons)

    def test_turn_mismatch_and_inside_chunk_turn_boundary_are_recorded(self):
        left = student("Pab", [b"P", b"ab"], keep=[False, True], turns=[0, 1])
        crossing = teacher("QQab", [b"QQ", b"a", b"b"],
                           keep=[False, True, True], turns=[0, 1, 2])
        mismatch = teacher("QQab", [b"QQ", b"ab"],
                           keep=[False, True], turns=[0, 2])
        for right, reason in ((crossing, "turn_boundary"), (mismatch, "turn_mismatch")):
            with self.subTest(reason=reason):
                result = align((left, right, (1, 3), (2, 4)))
                self.assertEqual(result.chunks, ())
                self.assertIn(reason, result.rejected[0].reasons)

    def test_common_boundary_between_two_turns_keeps_them_distinct(self):
        left = student("Pab", [b"P", b"a", b"b"],
                       keep=[False, True, True], turns=[0, 1, 2])
        right = teacher("QQab", [b"QQ", b"a", b"b"],
                        keep=[False, True, True], turns=[0, 1, 2])
        self.assertEqual([c.turn_id for c in align((left, right, (1, 3), (2, 4))).chunks], [1, 2])

    def test_raw_zero_is_unpredictable_even_when_answer_is_supervised(self):
        left = student("a", [b"a"], keep=[True], turns=[1])
        right = teacher("QQa", [b"QQ", b"a"])
        result = align((left, right, (0, 1), (2, 3)))
        self.assertEqual(result.chunks, ())
        self.assertIn("unpredictable_first_token", result.rejected[0].reasons)

    def test_inputs_and_result_are_immutable(self):
        values = pair("ab", [b"a", b"b"], [b"ab"])
        before = (asdict(values[0]), asdict(values[1]), values[2:])
        result = align(values)
        self.assertEqual((asdict(values[0]), asdict(values[1]), values[2:]), before)
        with self.assertRaises(FrozenInstanceError):
            result.covered_byte_count = 0
        with self.assertRaises(FrozenInstanceError):
            result.chunks[0].student_byte_start = 0
        self.assertEqual(sum(right - left for left, right in result.student_uncovered_ranges),
                         result.uncovered_byte_count)
        self.assertEqual(sum(right - left for left, right in result.teacher_uncovered_ranges),
                         result.uncovered_byte_count)


if __name__ == "__main__":
    unittest.main()
