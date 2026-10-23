"""P106B Stage7b byte 계약의 합성 회귀. 작성만 했으며 실행은 총괄 소유다."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_alm_bytes as m


def display_bytes(raw):
    """실제 tokenizer 없이 합성 ByteLevel piece를 만드는 독립 표면 fixture."""
    visible = set(range(33, 127)) | set(range(161, 173)) | set(range(174, 256))
    escaped = {value: chr(256 + index)
               for index, value in enumerate(value for value in range(256)
                                             if value not in visible)}
    return "".join(chr(value) if value in visible else escaped[value] for value in raw)


def student(text, parts, *, keep=None, turns=None, specials=(), ids=None):
    n = len(parts)
    native_ids = list(range(100, 100 + n)) if ids is None else ids
    pieces = [display_bytes(part) if isinstance(part, bytes) else part for part in parts]
    return m.build_student_stream(
        text, native_ids, pieces,
        supervised=[index > 0 for index in range(n)] if keep is None else keep,
        turn_ids=[int(index > 0) for index in range(n)] if turns is None else turns,
        specials=specials,
    )


def teacher(text, parts, *, keep=None, turns=None, specials=(), ids=None):
    n = len(parts)
    native_ids = list(range(200, 200 + n)) if ids is None else ids
    # 서버의 정수 배열 transport만 흉내 낸다. 모델/토크나이저는 없다.
    pieces = [list(part) if isinstance(part, bytes) else part for part in parts]
    return m.build_teacher_stream(
        text, native_ids, pieces,
        supervised=[index > 0 for index in range(n)] if keep is None else keep,
        turn_ids=[int(index > 0) for index in range(n)] if turns is None else turns,
        specials=specials,
    )


class PieceContract(unittest.TestCase):
    def test_known_bytelevel_inverse_not_utf8_display_encoding(self):
        self.assertEqual(m.student_piece_bytes("ĠĊĉčĀĢŃ"),
                         bytes([32, 10, 9, 13, 0, 128, 173]))
        self.assertEqual(m.student_piece_bytes("ê°Ģ"), "가".encode("utf-8"))
        self.assertNotEqual(m.student_piece_bytes("Ġ"), "Ġ".encode("utf-8"))

    def test_all_256_byte_values_round_trip_without_unicode_repair(self):
        raw = bytes(range(256))
        self.assertEqual(m.student_piece_bytes(display_bytes(raw)), raw)

    def test_korean_fragment_may_be_invalid_unicode_alone(self):
        first = m.student_piece_bytes("ê")
        rest = m.student_piece_bytes("°Ģ")
        with self.assertRaises(UnicodeDecodeError):
            first.decode("utf-8")
        self.assertEqual(first + rest, "가".encode("utf-8"))

    def test_teacher_string_and_fragment_array_are_distinct_transports(self):
        self.assertEqual(m.teacher_piece_bytes("가"), bytes([234, 176, 128]))
        self.assertEqual(m.teacher_piece_bytes([234]), bytes([234]))
        self.assertEqual(m.teacher_piece_bytes((176, 128)), bytes([176, 128]))

    def test_invalid_teacher_byte_array_rejected(self):
        for invalid in ([True], [1.0], [-1], [256], ["1"], None, b"x", {"piece": "x"}):
            with self.subTest(invalid=invalid):
                with self.assertRaises(m.ByteAlignmentError):
                    m.teacher_piece_bytes(invalid)

    def test_non_bytelevel_student_character_rejected(self):
        for invalid in ("가", "😀", ["a"], None):
            with self.subTest(invalid=invalid):
                with self.assertRaises(m.ByteAlignmentError):
                    m.student_piece_bytes(invalid)

    def test_surrogate_input_is_not_silently_repaired(self):
        with self.assertRaises(m.ByteAlignmentError):
            m.teacher_piece_bytes(chr(0xD800))
        with self.assertRaises(m.ByteAlignmentError):
            student(chr(0xD800), [b"x"], keep=[False], turns=[0])


class StreamContract(unittest.TestCase):
    def test_entire_input_exact_reconstruction_with_whitespace(self):
        text = "P \t가\r\n나  "
        pieces = [bytes([value]) for value in text.encode("utf-8")]
        stream = student(text, pieces)
        self.assertEqual(b"".join(span.data for span in stream.tokens), text.encode("utf-8"))
        self.assertEqual(stream.tokens[-1].byte_end, len(text.encode("utf-8")))
        self.assertEqual(tuple(span.raw_index for span in stream.tokens),
                         tuple(range(len(pieces))))

    def test_same_length_different_bytes_rejected(self):
        with self.assertRaises(m.ByteAlignmentError):
            student("Pa", [b"P", b"b"])
        with self.assertRaises(m.ByteAlignmentError):
            teacher("Pa", ["P", "b"])

    def test_incomplete_or_extra_input_rejected(self):
        for text, parts in (("Pa", [b"P"]), ("P", [b"P", b"a"])):
            with self.subTest(text=text, parts=parts):
                with self.assertRaises(m.ByteAlignmentError):
                    student(text, parts)

    def test_truncated_utf8_fragment_cannot_reconstruct_full_korean_input(self):
        incomplete = "가".encode("utf-8")[:-1]
        with self.assertRaises(m.ByteAlignmentError):
            student("P가", [b"P", incomplete])
        with self.assertRaises(m.ByteAlignmentError):
            teacher("P가", ["P", incomplete])

    def test_missing_or_empty_ordinary_piece_rejected(self):
        for missing in (None, ""):
            with self.subTest(missing=missing):
                with self.assertRaises(m.ByteAlignmentError):
                    teacher("P", ["P", missing], keep=[False, False], turns=[0, 0])
        with self.assertRaises(m.ByteAlignmentError):
            teacher("P", ["P", []], keep=[False, False], turns=[0, 0])

    def test_automatic_bos_requires_explicit_index_and_id(self):
        special = m.SpecialToken(0, 200, "BOS", b"")
        stream = teacher("Pa", [None, "P", "a"],
                         keep=[False, False, True], turns=[0, 0, 1],
                         specials=[special])
        self.assertEqual((stream.tokens[0].byte_start, stream.tokens[0].byte_end), (0, 0))
        self.assertEqual(stream.tokens[0].special_kind, "BOS")
        with self.assertRaises(m.ByteAlignmentError):
            teacher("Pa", [None, "P", "a"],
                    keep=[False, False, True], turns=[0, 0, 1])
        with self.assertRaises(m.ByteAlignmentError):
            teacher("Pa", [None, "P", "a"],
                    keep=[False, False, True], turns=[0, 0, 1],
                    specials=[replace(special, token_id=999)])

    def test_literal_special_consumes_real_input_offset(self):
        special = m.SpecialToken(0, 100, "ROLE_START", b"<S>")
        stream = student("<S>Pa", ["<S>", b"P", b"a"],
                         keep=[False, False, True], turns=[0, 0, 1],
                         specials=[special])
        self.assertEqual((stream.tokens[0].byte_start, stream.tokens[0].byte_end), (0, 3))
        self.assertEqual(stream.tokens[1].byte_start, 3)
        with self.assertRaises(m.ByteAlignmentError):
            student("<S>Pa", ["<S>", b"P", b"a"],
                    keep=[False, False, True], turns=[0, 0, 1],
                    specials=[replace(special, source_bytes=b"")])

    def test_literal_special_cannot_replace_wrong_or_missing_piece(self):
        special = m.SpecialToken(0, 200, "ROLE_START", b"<S>")
        for wrong in ("<X>", None, []):
            with self.subTest(wrong=wrong):
                with self.assertRaises(m.ByteAlignmentError):
                    teacher("<S>", [wrong], keep=[False], turns=[0], specials=[special])

    def test_zero_byte_special_display_is_not_consumed(self):
        special = m.SpecialToken(0, 200, "BOS", b"")
        stream = teacher("P", ["<bos>", "P"],
                         keep=[False, False], turns=[0, 0], specials=[special])
        self.assertEqual(stream.tokens[0].data, b"")
        self.assertEqual(stream.tokens[1].byte_start, 0)

    def test_duplicate_outside_and_untyped_special_declarations_rejected(self):
        special = m.SpecialToken(0, 200, "BOS", b"")
        for declarations in ([special, special],
                             [replace(special, raw_index=3)],
                             [replace(special, raw_index=True)],
                             [replace(special, source_bytes="")],
                             [replace(special, kind=" ")],
                             [dict(raw_index=0, token_id=200)]):
            with self.subTest(declarations=declarations):
                with self.assertRaises(m.ByteAlignmentError):
                    teacher("P", [None, "P"], keep=[False, False], turns=[0, 0],
                            specials=declarations)

    def test_lengths_mask_ids_and_turns_are_explicit(self):
        invalid_kwargs = (
            dict(supervised=[], turn_ids=[1]),
            dict(supervised=[1], turn_ids=[1]),
            dict(supervised=[True], turn_ids=[0]),
            dict(supervised=[True], turn_ids=[True]),
            dict(supervised=[False], turn_ids=[-1]),
        )
        for kwargs in invalid_kwargs:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(m.ByteAlignmentError):
                    m.build_teacher_stream("a", [7], ["a"], **kwargs)
        for invalid_id in (True, -1, 1.0):
            with self.subTest(invalid_id=invalid_id):
                with self.assertRaises(m.ByteAlignmentError):
                    m.build_teacher_stream("a", [invalid_id], ["a"],
                                           supervised=[False], turn_ids=[0])

    def test_inputs_are_not_mutated(self):
        ids = [200, 201]
        pieces = [[80], [97]]
        keep = [False, True]
        turns = [0, 1]
        m.build_teacher_stream("Pa", ids, pieces, supervised=keep, turn_ids=turns)
        self.assertEqual((ids, pieces, keep, turns),
                         ([200, 201], [[80], [97]], [False, True], [0, 1]))

    def test_same_native_id_cannot_describe_different_ordinary_bytes(self):
        with self.assertRaises(m.ByteAlignmentError):
            student("Pa", [b"P", b"a"], ids=[7, 7])
        with self.assertRaises(m.ByteAlignmentError):
            teacher("Pa", ["P", "a"], ids=[7, 7])

    def test_each_occurrence_of_known_special_id_needs_index_declaration(self):
        with self.assertRaises(m.ByteAlignmentError):
            teacher("P", [None, "P"], ids=[7, 7],
                    keep=[False, False], turns=[0, 0],
                    specials=[m.SpecialToken(0, 7, "BOS", b"")])

    def test_forged_overlap_and_duplicate_raw_index_rejected(self):
        stream = student("Pa", [b"P", b"a"])
        overlap = replace(stream.tokens[1], byte_start=0)
        duplicate = replace(stream.tokens[1], raw_index=0)
        for bad_token in (overlap, duplicate):
            with self.subTest(bad_token=bad_token):
                broken = replace(stream, tokens=(stream.tokens[0], bad_token))
                with self.assertRaises(m.ByteAlignmentError):
                    m.validate_stream(broken)


class AlignmentContract(unittest.TestCase):
    def test_shortest_korean_space_and_newline_chunks_keep_native_indices(self):
        ga, na = "가".encode("utf-8"), "나".encode("utf-8")
        left = student("P가 나\n", [b"P", ga[:1], ga[1:], b" ", na, b"\n"])
        right = teacher("P가 나\n", ["P", "가", " ", na[:1], na[1:], "\n"])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual([chunk.data for chunk in result.chunks], [ga, b" ", na, b"\n"])
        self.assertEqual(result.covered_byte_count, len("가 나\n".encode("utf-8")))
        first = result.chunks[0]
        self.assertEqual(first.student_raw_indices, (1, 2))
        self.assertEqual(first.teacher_raw_indices, (1,))
        self.assertEqual(first.student_shifted_indices, (0, 1))
        self.assertEqual(first.teacher_shifted_indices, (0,))
        self.assertEqual(tuple(span.token_id for span in left.tokens),
                         (100, 101, 102, 103, 104, 105))

    def test_shared_boundary_can_be_inside_a_unicode_character(self):
        ga = "가".encode("utf-8")
        left = student("P가", [b"P", ga[:1], ga[1:]])
        right = teacher("P가", ["P", ga[:1], ga[1:]])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual([chunk.data for chunk in result.chunks], [ga[:1], ga[1:]])
        self.assertEqual(b"".join(chunk.data for chunk in result.chunks), ga)

    def test_many_to_many_chunk_is_not_split_by_equal_token_count(self):
        left = student("Pabcd", [b"P", b"ab", b"cd"])
        right = teacher("Pabcd", ["P", "a", "bcd"])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual(len(result.chunks), 1)
        self.assertEqual(result.chunks[0].student_raw_indices, (1, 2))
        self.assertEqual(result.chunks[0].teacher_raw_indices, (1, 2))
        self.assertEqual(result.chunks[0].data, b"abcd")

    def test_repeated_token_id_does_not_collapse_original_positions(self):
        left = student("Pa a", [b"P", b"a", b" ", b"a"], ids=[9, 7, 8, 7])
        right = teacher("Pa a", ["P", "a", " ", "a"], ids=[19, 17, 18, 17])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual([chunk.student_raw_indices for chunk in result.chunks],
                         [(1,), (2,), (3,)])
        self.assertEqual([span.token_id for span in left.tokens], [9, 7, 8, 7])

    def test_partial_assistant_mask_rejects_whole_chunk_on_either_side(self):
        left = student("Pab", [b"P", b"ab"])
        right = teacher("Pab", ["P", "a", "b"],
                        keep=[False, True, False], turns=[0, 1, 0])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual(result.chunks, ())
        candidate = next(chunk for chunk in result.rejected if chunk.byte_start == 1)
        self.assertIn("unsupervised_token", candidate.reasons)
        self.assertEqual(candidate.student_raw_indices, (1,))
        self.assertEqual(candidate.teacher_raw_indices, (1, 2))
        left2 = student("Pab", [b"P", b"a", b"b"],
                        keep=[False, True, False], turns=[0, 1, 0])
        right2 = teacher("Pab", ["P", "ab"])
        self.assertEqual(m.align_assistant_chunks(left2, right2).chunks, ())

    def test_turn_crossing_and_cross_model_turn_mismatch_rejected(self):
        left = student("Pab", [b"P", b"ab"], keep=[False, True], turns=[0, 1])
        crossing = teacher("Pab", ["P", "a", "b"],
                           keep=[False, True, True], turns=[0, 1, 2])
        mismatch = teacher("Pab", ["P", "ab"], keep=[False, True], turns=[0, 2])
        crossing_result = m.align_assistant_chunks(left, crossing)
        mismatch_result = m.align_assistant_chunks(left, mismatch)
        self.assertEqual(crossing_result.chunks, ())
        self.assertEqual(mismatch_result.chunks, ())
        self.assertIn("turn_boundary", crossing_result.rejected[-1].reasons)
        self.assertIn("turn_mismatch", mismatch_result.rejected[-1].reasons)

    def test_two_turns_at_common_boundary_remain_separate(self):
        left = student("Pab", [b"P", b"a", b"b"],
                       keep=[False, True, True], turns=[0, 1, 2])
        right = teacher("Pab", ["P", "a", "b"],
                        keep=[False, True, True], turns=[0, 1, 2])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual([chunk.turn_id for chunk in result.chunks], [1, 2])

    def test_literal_eot_remains_in_offsets_but_never_in_kd(self):
        left = student("Pa<E>\n", [b"P", b"a", "<E>", b"\n"],
                       keep=[False, True, True, False], turns=[0, 1, 1, 0],
                       specials=[m.SpecialToken(2, 102, "EOT", b"<E>")])
        right = teacher("Pa<E>\n", ["P", "a", "<E>", "\n"],
                        keep=[False, True, True, False], turns=[0, 1, 1, 0],
                        specials=[m.SpecialToken(2, 202, "EOT", b"<E>")])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual([chunk.data for chunk in result.chunks], [b"a"])
        self.assertEqual(result.student_special_indices, (2,))
        self.assertEqual(left.tokens[-1].byte_start, len("Pa<E>".encode("utf-8")))
        eot = next(chunk for chunk in result.rejected if chunk.byte_start == 2)
        self.assertIn("special_token", eot.reasons)

    def test_auto_bos_and_eot_metadata_preserve_all_original_indices(self):
        left = student("Pa", [None, b"P", b"a", "<eot>"],
                       keep=[False, False, True, True], turns=[0, 0, 1, 1],
                       specials=[m.SpecialToken(0, 100, "BOS", b""),
                                 m.SpecialToken(3, 103, "EOT", b"")])
        right = teacher("Pa", [None, "P", "a", None],
                        keep=[False, False, True, True], turns=[0, 0, 1, 1],
                        specials=[m.SpecialToken(0, 200, "BOS", b""),
                                  m.SpecialToken(3, 203, "EOT", b"")])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual(result.chunks[0].student_raw_indices, (2,))
        self.assertEqual(result.chunks[0].student_shifted_indices, (1,))
        self.assertEqual(result.student_special_indices, (0, 3))
        self.assertEqual(result.teacher_special_indices, (0, 3))

    def test_zero_byte_interior_special_rejects_enclosing_chunk(self):
        left = student("Pab", [b"P", b"a", None, b"b"],
                       keep=[False, True, False, True], turns=[0, 1, 0, 1],
                       specials=[m.SpecialToken(2, 102, "INTERIOR_CONTROL", b"")])
        right = teacher("Pab", ["P", "ab"])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual(result.chunks, ())
        self.assertIn("special_token", result.rejected[-1].reasons)
        self.assertEqual(result.rejected[-1].student_raw_indices, (1, 2, 3))

    def test_first_raw_token_is_not_a_predictable_target_without_prefix(self):
        left = student("a", [b"a"], keep=[True], turns=[1])
        right = teacher("a", ["a"], keep=[True], turns=[1])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual(result.chunks, ())
        self.assertIn("unpredictable_first_token", result.rejected[0].reasons)

    def test_same_length_different_full_sources_and_templates_rejected(self):
        left = student("Pa", [b"P", b"a"])
        for other_text, parts in (("Pb", ["P", "b"]), ("Xa", ["X", "a"])):
            with self.subTest(other_text=other_text):
                with self.assertRaises(m.ByteAlignmentError):
                    m.align_assistant_chunks(left, teacher(other_text, parts))

    def test_normalized_equivalent_text_is_not_byte_equivalent(self):
        left = student("Pé", [b"P", "é".encode("utf-8")])
        right = teacher("Pe\u0301", ["P", "e\u0301"])
        with self.assertRaises(m.ByteAlignmentError):
            m.align_assistant_chunks(left, right)

    def test_literal_marker_without_special_declaration_is_ordinary_content(self):
        text = "P<S>"
        left = student(text, [b"P", b"<", b"S", b">"])
        right = teacher(text, ["P", "<S>"])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual(result.chunks[0].data, b"<S>")
        self.assertEqual(result.student_special_indices, ())

    def test_empty_input_or_all_specials_give_no_chunk_not_fake_success(self):
        empty_left = student("", [])
        empty_right = teacher("", [])
        self.assertEqual(m.align_assistant_chunks(empty_left, empty_right).chunks, ())
        left = student("", [None], keep=[False], turns=[0],
                       specials=[m.SpecialToken(0, 100, "BOS", b"")])
        right = teacher("", [None], keep=[False], turns=[0],
                        specials=[m.SpecialToken(0, 200, "BOS", b"")])
        result = m.align_assistant_chunks(left, right)
        self.assertEqual((result.covered_byte_count, result.input_byte_count), (0, 0))
        self.assertEqual(result.student_special_indices, (0,))

    def test_swapped_stream_roles_rejected(self):
        left = student("Pa", [b"P", b"a"])
        right = teacher("Pa", ["P", "a"])
        with self.assertRaises(m.ByteAlignmentError):
            m.align_assistant_chunks(right, left)


class ShiftContract(unittest.TestCase):
    def test_raw_target_to_shifted_row_exactly_once(self):
        self.assertEqual(m.raw_to_shifted([1, 2, 5]), (0, 1, 4))
        self.assertEqual(m.raw_to_shifted([]), ())
        with self.assertRaises(m.ByteAlignmentError):
            m.raw_to_shifted([1, 2], already_shifted=True)

    def test_tagged_second_shift_rejected_even_when_all_rows_are_positive(self):
        shifted = m.raw_to_shifted([2, 3])
        self.assertEqual(shifted, (1, 2))
        self.assertIsInstance(shifted, m.ShiftedTargetIndices)
        with self.assertRaises(m.ByteAlignmentError):
            m.raw_to_shifted(shifted)

    def test_zero_duplicate_unsorted_or_nonnative_indices_rejected(self):
        for indices in ([0], [1, 1], [2, 1], [-1], [True], [1.0]):
            with self.subTest(indices=indices):
                with self.assertRaises(m.ByteAlignmentError):
                    m.raw_to_shifted(indices)


if __name__ == "__main__":
    unittest.main()
