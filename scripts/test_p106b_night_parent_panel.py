"""합성 원형·원답과 메모리 토크나이저만 사용하는 부모 진단 회귀."""
from pathlib import Path
import copy
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_parent_panel as panel


def natural_rows(count=40):
    return [dict(root=panel._sha([language, index]), language=language,
                 question='질문' + str(index), context='원문' + str(index),
                 answers=[dict(text='원래 정답' + str(index))],
                 views={'0': {'meta': {'원형': index}}, '1': {'meta': {'원형': index}}, '2': {'meta': {'원형': index}}})
            for index in range(count) for language in ('ko', 'en')]


class FixtureTokenizer:
    def encode(self, text):
        return SimpleNamespace(ids=[ord(char) for char in text])


def mc_row(index=0, skip=None):
    return dict(task='piqa', kind='mc', index=index, expected_skip=skip,
        item=dict(ctx='문맥', choices=[' 가', ' 나나다'], gold=0, _iid='문항' + str(index)))


def mc_event(row):
    item = row['item']
    return dict(task=row['task'], id=item['_iid'], kind='mc', skipped=False,
        source_item=copy.deepcopy(item), gold=item['gold'], sum_nll=[4., 6.],
        mean_nll=[2., 1.5], n_tokens=[2, 4], n_chars=[2, 4],
        score=[-3., 8.], pred_internal=0, pred_internal_norm=1,
        margin_mean=11., margin_decision=11., pred_harness=0, pred_harness_norm=1)


class PanelSelectionTests(unittest.TestCase):
    def test_default64_unique_balanced_original_order_full_rows_and_proof(self):
        original = natural_rows()
        before = copy.deepcopy(original)
        rows, proof = panel.select_pairs(original)
        self.assertEqual(len(rows), 64)
        self.assertEqual(len({p['root'] for p in rows}), 64)
        self.assertEqual([original[i] for i in proof['source_indices']], rows)
        self.assertEqual(proof['source_indices'], sorted(proof['source_indices']))
        self.assertEqual(sum(p['language'] == 'ko' for p in rows), 32)
        self.assertEqual(sum(p['language'] == 'en' for p in rows), 32)
        self.assertEqual(proof['source_sha256'], panel._sha(original))
        self.assertEqual(proof['source_roots_sha256'], panel._sha(sorted(p['root'] for p in original)))
        self.assertFalse(proof['model_outputs_used'])
        self.assertEqual(original, before)
        rows[0]['views']['0']['meta']['원형'] = '반환값 변경'
        self.assertEqual(original, before)

    def test_hash_rule_seed_reproducibility_and_source_reorder(self):
        original = natural_rows()
        rows, proof = panel.select_pairs(original)
        again, same_proof = panel.select_pairs(original)
        self.assertEqual((rows, proof), (again, same_proof))
        reversed_rows, reversed_proof = panel.select_pairs(list(reversed(original)))
        self.assertEqual({p['root'] for p in rows}, {p['root'] for p in reversed_rows})
        changed, _ = panel.select_pairs(original, seed=20261018)
        self.assertNotEqual({p['root'] for p in rows}, {p['root'] for p in changed})
        for language in ('ko', 'en'):
            ranked = sorted([p for p in original if p['language'] == language],
                            key=lambda p: panel._sha([20261017, language, p['root']]))[:32]
            self.assertEqual(proof['ranked_roots_by_language'][language], [p['root'] for p in ranked])

    def test_original_gold_or_text_does_not_control_selection(self):
        original = natural_rows()
        selected, proof = panel.select_pairs(original)
        altered = copy.deepcopy(original)
        for row in altered:
            row['context'] = '다른 원문'
            row['answers'] = [dict(text='다른 원래 정답')]
        newer, newer_proof = panel.select_pairs(altered)
        self.assertEqual([p['root'] for p in selected], [p['root'] for p in newer])
        self.assertNotEqual(proof['source_sha256'], newer_proof['source_sha256'])

    def test_missing_language_duplicate_root_insufficient_and_model_output_rejected(self):
        original = natural_rows()
        for changed in ([r for r in original if r['language'] == 'ko'], original + [original[0]], natural_rows(31)):
            with self.assertRaises(ValueError):
                panel.select_pairs(changed)
        for field in ('answer', 'model_answer', 'scores', 'correct', 'generation'):
            changed = copy.deepcopy(original)
            changed[0][field] = '사용 금지'
            with self.assertRaises(ValueError):
                panel.select_pairs(changed)


class PublicMCRecountTests(unittest.TestCase):
    def setUp(self):
        self.tok = FixtureTokenizer()

    def test_flat_scores_source_and_two_separate_predictions(self):
        row = mc_row()
        event = mc_event(row)
        before = copy.deepcopy((event, row))
        result = panel.public_mc_recount([event], [row], self.tok)
        self.assertEqual(result['summary']['piqa'], dict(n=1, correct=1, char_norm_correct=0,
            skip=0, skipped=0, prediction_counts={'0': 1}, char_norm_prediction_counts={'1': 1}))
        self.assertEqual(result['outcomes'][0]['pred'], 0)
        self.assertEqual(result['outcomes'][0]['char_norm_pred'], 1)
        self.assertEqual((event, row), before)

    def test_pmi_values_and_internal_choice_are_not_primary_ranking(self):
        row = mc_row()
        event = mc_event(row)
        first = panel.public_mc_recount([event], [row], self.tok)
        changed = copy.deepcopy(event)
        changed.update(score=[900., -900.], pred_internal=1, pred_internal_norm=0,
                       margin_mean=-1800., margin_decision=-1800.)
        other = panel.public_mc_recount([changed], [row], self.tok)
        self.assertEqual(first, other)
        self.assertFalse(first['internal_pmi_used_for_ranking'])

    def test_duplicate_missing_unknown_and_source_gold_changes_rejected(self):
        row = mc_row()
        event = mc_event(row)
        for events, originals in (([], [row]), ([event, event], [row]), ([event], [row, row]),
                                  ([dict(event, id='없는 문항')], [row])):
            with self.assertRaises(ValueError):
                panel.public_mc_recount(events, originals, self.tok)
        for field, value in (('source_item', dict(row['item'], ctx='다른 원문')), ('gold', 1), ('kind', 'gen')):
            with self.assertRaises(ValueError):
                panel.public_mc_recount([dict(event, **{field: value})], [row], self.tok)

    def test_nll_lengths_mean_sum_and_both_predictions_rechecked(self):
        row = mc_row()
        event = mc_event(row)
        for field, values in (('sum_nll', [4.]), ('sum_nll', [float('nan'), 6.]),
                ('mean_nll', [2.1, 1.5]), ('score', [float('inf'), 0.]),
                ('n_tokens', [3, 4]), ('n_chars', [2, 5])):
            changed = copy.deepcopy(event)
            changed[field] = values
            with self.assertRaises(ValueError):
                panel.public_mc_recount([changed], [row], self.tok)
        for field in ('pred_harness', 'pred_harness_norm'):
            changed = copy.deepcopy(event)
            changed[field] = 1 - changed[field]
            with self.assertRaises(ValueError):
                panel.public_mc_recount([changed], [row], self.tok)

    def test_skip_counts_are_not_invented_zero_scores_and_reason_is_fixed(self):
        row = mc_row(skip='seq_max_exceeded')
        event = dict(task=row['task'], id=row['item']['_iid'], kind='mc', skipped=True,
                     reason=row['expected_skip'], source_item=copy.deepcopy(row['item']))
        result = panel.public_mc_recount([event], [row], self.tok)
        self.assertEqual((result['summary']['piqa']['n'], result['summary']['piqa']['skip']), (0, 1))
        self.assertIsNone(result['outcomes'][0]['correct'])
        with self.assertRaises(ValueError):
            panel.public_mc_recount([dict(event, reason='gold_missing')], [row], self.tok)
        eligible = mc_row()
        with self.assertRaises(ValueError):
            panel.public_mc_recount([dict(event, source_item=eligible['item'])], [eligible], self.tok)

    def test_sum_ties_choose_first_and_optional_index_requires_integer(self):
        row = mc_row(index=1)
        event = mc_event(row)
        event.update(sum_nll=[4., 4.], mean_nll=[2., 1.], pred_harness=0, pred_harness_norm=1)
        result = panel.public_mc_recount([event], [row], self.tok)
        self.assertEqual(result['outcomes'][0]['pred'], 0)
        with self.assertRaises(ValueError):
            panel.public_mc_recount([dict(event, pred_harness=1)], [row], self.tok)
        with self.assertRaises(ValueError):
            panel.public_mc_recount([dict(event, index=True)], [row], self.tok)


if __name__ == '__main__':
    unittest.main()
