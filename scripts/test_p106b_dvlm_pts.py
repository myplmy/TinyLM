"""Input, visibility, logical-position and exactly-once target-shift contracts."""
import unittest
from scripts import p106b_dvlm_pts as pts


def fixture():
    return pts.build_layout([10, 11, 12], [20, 21, 22],
        [b'ab', b'cd', b'ef'], [b'abcd', b'e', b'f'], [[30, 31], [32], [33, 34]])


class PTSContracts(unittest.TestCase):
    def test_lossless_nonmatching_token_boundaries_form_complete_groups(self):
        layout = fixture()
        self.assertEqual([(g.student, g.teacher, g.byte_start, g.byte_end) for g in layout.groups],
                         [((0, 1), (0,), 0, 4), ((2,), (1, 2), 4, 6)])

    def test_teacher_byte_fragments_preserve_the_complete_raw_alignment(self):
        raw = '가'.encode('utf-8')
        groups = pts.align_piece_groups([raw], [bytes([value]) for value in raw])
        self.assertEqual(groups, (pts.AlignmentGroup((0,), (0, 1, 2), 0, 3),))

    def test_tokenizer_admission_rejects_individual_student_decode_rewrite(self):
        def student_decode(ids):
            return 'ab' if len(ids) == 2 else ('a' if ids[0] == 1 else 'X')
        teacher_decode = lambda ids: {(3,): 'ab', (4,): 'a', (5,): 'b'}[tuple(ids)]
        with self.assertRaisesRegex(pts.AdmissionHold, 'STANDALONE_STUDENT'):
            pts.prepare_layout([1, 2], [3], [b'a', b'b'], [b'ab'],
                decode_student=student_decode, encode_teacher=lambda text: [4 if text == 'a' else 5], decode_teacher=teacher_decode)

    def test_native_teacher_cannot_see_any_private_or_future_native_token(self):
        layout = fixture()
        for query in range(3):
            self.assertEqual([k for k in range(8) if layout.visible(query, k)], list(range(query + 1)))

    def test_same_alignment_group_previous_student_expansion_is_visible(self):
        layout = fixture()
        self.assertEqual([k for k in range(8) if layout.visible(5, k)], [3, 4, 5])

    def test_other_alignment_group_private_tokens_are_invisible(self):
        layout = fixture()
        self.assertEqual([k for k in range(8) if layout.visible(6, k)], [0, 6])
        self.assertEqual([k for k in range(8) if layout.visible(7, k)], [0, 6, 7])

    def test_logical_positions_restart_at_native_prefix_and_keep_same_group_offsets(self):
        self.assertEqual(fixture().position_ids, (0, 1, 2, 0, 1, 2, 1, 2))

    def test_group_serial_branches_have_the_same_logical_sequence(self):
        layout = fixture()
        self.assertEqual(layout.branch_indices(0), (3, 4, 5))
        self.assertEqual(layout.branch_indices(1), (0, 6, 7))
        for group in range(2):
            branch = layout.branch_indices(group)
            self.assertEqual([layout.position_ids[i] for i in branch], list(range(len(branch))))

    def test_head_selection_and_next_student_shift_preserve_supervision_mask(self):
        layout = fixture()
        self.assertEqual(layout.head_indices, (4, 5, 7))
        self.assertEqual(layout.head_targets([False, True, True]), (11, 12, -100))
        self.assertEqual(layout.head_targets([True, False, True]), (-100, 12, -100))

    def test_full_text_mismatch_is_not_hidden_by_a_residual_group(self):
        with self.assertRaisesRegex(pts.AdmissionHold, 'MISMATCH'):
            pts.align_piece_groups([b'ab', b'c'], [b'ab', b'x'])

    def test_nonappend_decoder_is_rejected(self):
        with self.assertRaisesRegex(pts.AdmissionHold, 'NON_APPEND'):
            pts.canonical_pieces([1, 2], lambda ids: 'a' if len(ids) == 1 else 'b')

    def test_incomplete_utf8_student_token_is_rejected_before_teacher_encode(self):
        def forbidden(_text):
            raise AssertionError('teacher must not see broken UTF8')
        with self.assertRaisesRegex(pts.AdmissionHold, 'INDEPENDENT_UTF8'):
            pts.expand_piece(bytes([0xe3]), forbidden, forbidden)

    def test_retokenization_must_preserve_exact_text_and_spaces(self):
        self.assertEqual(pts.expand_piece(b' a', lambda text: [5, 6], lambda ids: ' a'), (5, 6))
        with self.assertRaisesRegex(pts.AdmissionHold, 'CHANGED_TEXT'):
            pts.expand_piece(b' a', lambda text: [5], lambda ids: 'a')

    def test_empty_pieces_and_incomplete_expansion_coverage_are_refused(self):
        with self.assertRaises(pts.AdmissionHold):
            pts.align_piece_groups([b'a', b''], [b'a'])
        with self.assertRaisesRegex(pts.AdmissionHold, 'EVERY_STUDENT'):
            pts.build_layout([1, 2], [3], [b'a', b'b'], [b'ab'], [[4]])

    def test_complete_pts_length_cap_never_silently_truncates(self):
        with self.assertRaisesRegex(pts.AdmissionHold, 'OVER_LENGTH'):
            pts.build_layout([1], [2], [b'a'], [b'a'], [[3, 4]], max_length=2)

    def test_invalid_boolean_ids_or_implicit_supervision_are_refused(self):
        with self.assertRaises(pts.AdmissionHold):
            pts.build_layout([True], [2], [b'a'], [b'a'], [[3]])
        with self.assertRaises(pts.AdmissionHold):
            fixture().head_targets([1, 1, 1])

    def test_visibility_matches_independent_group_causal_branches_exhaustively(self):
        layout = fixture()
        expected = {(q, k) for q in range(3) for k in range(q + 1)}
        for group in range(len(layout.groups)):
            branch = layout.branch_indices(group)
            for qpos, query in enumerate(branch):
                if query >= layout.teacher_count:
                    expected.update((query, k) for k in branch[:qpos + 1])
        observed = {(q, k) for q in range(8) for k in range(8) if layout.visible(q, k)}
        self.assertEqual(observed, expected)


if __name__ == '__main__':
    unittest.main()
