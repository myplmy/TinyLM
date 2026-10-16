"""CPU, in-memory records only: completeness, recount and intervention checks."""
from pathlib import Path
import copy
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_evaluation as evaluation
from scripts.p106b_night_learning import qa_scores


def natural_events():
    rows = []
    for language in ('ko', 'en'):
        for index in range(4):
            gold = ('정답' if language == 'ko' else 'answer') + str(index)
            for view in (0, 1, 2):
                rows.append(dict(root=language + '_root_' + str(index),
                    article_id=language + '_article_' + str(index // 2),
                    language=language, view=view, answer=gold, aliases=[gold],
                    generation=dict(finish_reason='STOP_SEQUENCE'),
                    scores=qa_scores(gold, [gold], language), source_sha256='source_' + language,
                    question='question_' + str(index), context='context_' + str(index)))
    return rows


def answer(event, value):
    event['answer'] = value
    if 'aliases' in event:
        event['scores'] = qa_scores(value, event['aliases'], event['language'])


def cube_events():
    return [dict(row, answer=row['gold'], generation=dict(finish_reason='STOP_SEQUENCE'))
            for row in evaluation.cube_rows()]


class NaturalTests(unittest.TestCase):
    def test_complete_scored_roots_and_heldout_are_separate(self):
        result = evaluation.summarize_natural(natural_events())
        self.assertEqual((result['cases'], result['roots']), (24, 8))
        for language in ('ko', 'en'):
            lane = result['by_language'][language]
            self.assertEqual(lane['train_pair']['both_correct'], 4)
            self.assertEqual(lane['heldout_view2']['em'], 1.)
            self.assertEqual(lane['by_view']['0']['stop'], 4)
            self.assertEqual(lane['by_view']['0']['articles'], 2)

    def test_duplicate_and_missing_views_rejected(self):
        rows = natural_events()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            evaluation.summarize_natural(rows + [copy.deepcopy(rows[0])])
        with self.assertRaisesRegex(ValueError, 'views0/1/2'):
            evaluation.summarize_natural(rows[:-1])

    def test_stored_scores_are_recounted_from_raw_answer(self):
        rows = natural_events()
        rows[0]['scores']['em'] = 0.
        with self.assertRaisesRegex(ValueError, 'recount'):
            evaluation.summarize_natural(rows)
        rows = natural_events()
        rows[0]['scores']['f1'] = float('nan')
        with self.assertRaises(ValueError):
            evaluation.summarize_natural(rows)

    def test_same_wrong_and_blank_collapse_do_not_become_bothcorrect(self):
        rows = natural_events()
        for event in rows:
            if event['view'] < 2:
                answer(event, 'wrong')
        result = evaluation.summarize_natural(rows)
        for language in ('ko', 'en'):
            lane = result['by_language'][language]
            self.assertEqual(lane['train_pair']['same_wrong'], 4)
            self.assertEqual(lane['train_pair']['both_correct'], 0)
            self.assertEqual(lane['heldout_view2']['em'], 1.)
        for event in rows:
            if event['view'] < 2:
                answer(event, '  ')
        result = evaluation.summarize_natural(rows)
        self.assertEqual(result['by_language']['ko']['train_pair']['same_wrong'], 0)
        self.assertEqual(result['by_language']['ko']['train_pair']['both_empty'], 4)

    def test_source_and_gold_may_not_change_with_wrapper(self):
        for field, value in (('article_id', 'different'), ('aliases', ['different']),
                             ('source_sha256', 'different'), ('question', 'different'),
                             ('context', 'different')):
            rows = natural_events()
            rows[1][field] = value
            if field == 'aliases':
                rows[1]['scores'] = qa_scores(rows[1]['answer'], value, rows[1]['language'])
            with self.assertRaises(ValueError):
                evaluation.summarize_natural(rows)

    def test_finish_reason_required_and_truncation_preserved(self):
        rows = natural_events()
        rows[0]['generation'] = {}
        with self.assertRaises(ValueError):
            evaluation.summarize_natural(rows)
        rows = natural_events()
        rows[0]['generation']['finish_reason'] = 'MAX_NEW'
        result = evaluation.summarize_natural(rows)['by_language']['ko']['by_view']['0']
        self.assertEqual((result['max_new'], result['stop']), (1, 3))

    def test_article_bootstrap_identical_endpoints_and_reproducibility(self):
        rows = natural_events()
        first = evaluation.paired_natural(rows, copy.deepcopy(rows), draws=39, seed=44)
        second = evaluation.paired_natural(rows, copy.deepcopy(rows), draws=39, seed=44)
        self.assertEqual(first, second)
        for language in ('ko', 'en'):
            lane = first['by_language'][language]
            self.assertEqual(lane['articles'], 2)
            self.assertEqual(lane['roots'], 4)
            self.assertEqual(lane['train_pair_both_correct']['ci95'], [0., 0.])
            for view in ('0', '1', '2'):
                self.assertEqual(lane['by_view'][view]['em']['right_minus_left'], 0.)
        self.assertFalse(first['training_seed_generalization'])
        self.assertFalse(first['multiple_comparison_adjusted'])

    def test_bootstrap_negative_direction_and_source_case_guard(self):
        left, right = natural_events(), natural_events()
        for event in right:
            answer(event, 'wrong')
        result = evaluation.paired_natural(left, right, draws=31, seed=12)
        for language in ('ko', 'en'):
            self.assertEqual(result['by_language'][language]['by_view']['0']['em']['ci95'], [-1., -1.])
            self.assertEqual(result['by_language'][language]['train_pair_both_correct']['right_minus_left'], -1.)
        for field in ('article_id', 'source_sha256', 'question', 'context'):
            right = natural_events()
            for event in right[:3]:
                event[field] = 'different'
            with self.assertRaises(ValueError):
                evaluation.paired_natural(left, right, draws=2)
        with self.assertRaises(ValueError):
            evaluation.paired_natural(left, right[3:], draws=2)

    def test_numeric_sign_and_decimal_are_preserved_by_scorer(self):
        self.assertEqual(qa_scores('-5', ['5'], 'en')['em'], 0.)
        self.assertEqual(qa_scores('1.5', ['15'], 'ko')['em'], 0.)


class CubeTests(unittest.TestCase):
    def test_exact_factorial64_and_question_has_no_gold_number(self):
        rows = evaluation.cube_rows()
        self.assertEqual(len(rows), 64)
        self.assertEqual(len({r['root'] for r in rows}), 8)
        self.assertEqual(len({r['case_id'] for r in rows}), 64)
        for row in rows:
            self.assertEqual(row['language'], row['lang'])
            self.assertFalse(re.search(r'\d', row['question']))
            expected = (row['new_age'] if row['field'] == 'age' and row['updated'] else
                        row['initial_age'] if row['field'] == 'age' else row['class_value'])
            self.assertEqual(row['gold'], str(expected))
        self.assertEqual(rows, evaluation.cube_rows())

    def test_all_correct_transitions_and_slices(self):
        result = evaluation.summarize_cube(cube_events())
        self.assertEqual(result['summary']['literal'], 64)
        self.assertEqual(result['transitions']['age_change']['both_correct'], 16)
        self.assertEqual(result['transitions']['age_change']['output_changed'], 16)
        self.assertEqual(result['transitions']['class_invariance']['both_correct'], 16)
        self.assertEqual(result['transitions']['class_invariance']['output_unchanged'], 16)
        self.assertEqual(result['slices']['by_language']['ko']['n'], 32)
        self.assertEqual(result['slices']['by_updated']['true']['n'], 32)

    def test_old_age_repetition_fails_change_but_keeps_class(self):
        rows = cube_events()
        for event in rows:
            if event['field'] == 'age':
                event['answer'] = str(event['initial_age'])
        result = evaluation.summarize_cube(rows)
        self.assertEqual(result['transitions']['age_change']['both_correct'], 0)
        self.assertEqual(result['transitions']['age_change']['output_changed'], 0)
        self.assertEqual(result['transitions']['class_invariance']['both_correct'], 16)

    def test_incorrect_class_update_is_separate_from_age_change(self):
        rows = cube_events()
        for event in rows:
            if event['field'] == 'class' and event['updated']:
                event['answer'] = str(event['class_value'] + 1)
        result = evaluation.summarize_cube(rows)
        self.assertEqual(result['transitions']['class_invariance']['both_correct'], 0)
        self.assertEqual(result['transitions']['age_change']['both_correct'], 16)

    def test_missing_duplicate_and_altered_producer_rows_rejected(self):
        rows = cube_events()
        for changed in (rows[:-1], rows + [copy.deepcopy(rows[0])]):
            with self.assertRaises(ValueError):
                evaluation.summarize_cube(changed)
        for field, value in (('gold', '999'), ('lang', 'en'), ('updated', 1),
                             ('reference', 'changed'), ('messages', [])):
            changed = copy.deepcopy(rows)
            changed[0][field] = value
            with self.assertRaises(ValueError):
                evaluation.summarize_cube(changed)

    def test_literal_keeps_sign_decimal_and_original_answer(self):
        for transform in (lambda value: '-' + value, lambda value: value + '.0'):
            rows = cube_events()
            rows[0]['answer'] = transform(rows[0]['gold'])
            self.assertEqual(evaluation.summarize_cube(rows)['summary']['literal'], 63)
        rows = cube_events()
        rows[0]['answer'] = ' ' + rows[0]['gold'] + '\n'
        result = evaluation.summarize_cube(rows)
        self.assertEqual((result['summary']['literal'], result['summary']['raw_exact']), (64, 63))


if __name__ == '__main__':
    unittest.main()
