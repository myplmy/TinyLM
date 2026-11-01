"""공식 평가 의미를 바꾸지 않는 MMLU 자료/누락/비용 경계 시험. CPU·합성만 사용한다."""
import copy
from dataclasses import dataclass
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import p106b_official_mmlu as data
from scripts import diag_p106b_official_mmlu as driver


def example(subject='alpha', answer=0, question='Which?'):
    return dict(subject=subject, question=question, choices=['one', 'two', 'three', 'four'], answer=answer)


def sample(index, answer=0, scores=(-1., -2., -3., -4.)):
    return dict(doc_id=index, doc=example(answer=answer), filtered_resps=[(s, False) for s in scores],
                acc=int(max(range(4), key=lambda i:scores[i]) == answer))


class DataContract(unittest.TestCase):
    def test_subject_filter_keeps_source_order_and_duplicates(self):
        a, b = example(question='first'), example('beta')
        rows = [a, b, a, example(question='last')]
        grouped = data.validate_rows(rows, ['alpha', 'beta'], 'test', total=4)
        self.assertEqual(grouped['alpha'], [a, a, rows[3]])
        self.assertEqual(len(grouped['beta']), 1)

    def test_row_digest_changes_with_order(self):
        a, b = example(question='first'), example(question='second')
        self.assertNotEqual(data.row_digest([a, b]), data.row_digest([b, a]))

    def test_exact_test_denominator(self):
        with self.assertRaises(ValueError):
            data.validate_rows([example()], ['alpha'], 'test', total=2)

    def test_dev_requires_five_for_each_subject(self):
        self.assertEqual(len(data.validate_rows([example()] * 5, ['alpha'], 'dev')['alpha']), 5)
        for count in [0, 4, 6]:
            with self.subTest(count=count), self.assertRaises(ValueError):
                data.validate_rows([example()] * count, ['alpha'], 'dev')

    def test_missing_unknown_or_duplicate_subjects(self):
        for subjects in [['beta'], ['alpha', 'beta'], ['alpha', 'alpha']]:
            with self.subTest(subjects=subjects), self.assertRaises(ValueError):
                data.validate_rows([example()], subjects, 'test')

    def test_only_test_dev_splits(self):
        with self.assertRaises(ValueError):
            data.validate_rows([example()], ['alpha'], 'auxiliary_train')

    def test_bool_or_out_of_range_labels(self):
        for label in [True, False, -1, 4, '0', None]:
            with self.subTest(label=label), self.assertRaises(ValueError):
                data.validate_rows([example(answer=label)], ['alpha'], 'test')

    def test_missing_or_blank_question_choices(self):
        for field, value in [('question', ''), ('choices', ['one'] * 3), ('choices', ['one', '', 'three', 'four'])]:
            row = example()
            row[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                data.validate_rows([row], ['alpha'], 'test')

    def test_unknown_columns_rejected(self):
        row = dict(example(), hidden_answer='do not use')
        with self.assertRaises(ValueError):
            data.validate_rows([row], ['alpha'], 'test')

    def test_official_fewshot_object_keeps_declared_fields(self):
        @dataclass
        class Fewshot:
            sampler: str = 'first_n'
            split: str = 'dev'
        before = dict(doc_to_target='answer', fewshot_config=dict(sampler='first_n'))
        self.assertTrue(data.preserved_fields_match(before, SimpleNamespace(doc_to_target='answer', fewshot_config=Fewshot())))
        self.assertFalse(data.preserved_fields_match(before, SimpleNamespace(doc_to_target='answer', fewshot_config=Fewshot('random'))))

    def test_config_normalization_cannot_hide_prompt_or_target_changes(self):
        before = dict(doc_to_text='Question', doc_to_target='answer', fewshot_config=dict(sampler='first_n'))
        actual = SimpleNamespace(doc_to_text='Different', doc_to_target='answer', fewshot_config=dict(sampler='first_n', split='dev'))
        self.assertFalse(data.preserved_fields_match(before, actual))
        actual.doc_to_text = 'Question'
        actual.doc_to_target = 'wrong'
        self.assertFalse(data.preserved_fields_match(before, actual))


class Scores(unittest.TestCase):
    def test_full_labels_independent_count(self):
        value = data.independent_scores([sample(0), sample(1, answer=2), sample(2, answer=1, scores=(-4., -1., -2., -3.))], 3)
        self.assertEqual(value['correct'], 2)
        self.assertAlmostEqual(value['accuracy'], 2 / 3)
        self.assertEqual(value['uniform_expected_correct'], .75)

    def test_ties_preserve_first_argmax(self):
        self.assertEqual(data.independent_scores([sample(0, scores=(-1.,) * 4)], 1)['correct'], 1)

    def test_missing_rows_or_order(self):
        for rows in [[sample(0)], [sample(1), sample(0)], [sample(0), sample(0)]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                data.independent_scores(rows, 2)

    def test_partial_or_nonfinite_candidates(self):
        for scores in [(-1., -2., -3.), (-1., -2., math.nan, -4.), (-1., 0.1, -2., -3.)]:
            row = sample(0)
            row['filtered_resps'] = [(v, False) for v in scores]
            with self.subTest(scores=scores), self.assertRaises(ValueError):
                data.independent_scores([row], 1)

    def test_official_per_item_mismatch(self):
        row = sample(0)
        row['acc'] = 0
        with self.assertRaises(ValueError):
            data.independent_scores([row], 1)


class CostAdmission(unittest.TestCase):
    def setUp(self):
        self.source = dict(files={}, sha256='source')
        self.cost = dict(status='LIMITED_COST_DIAGNOSTIC', final_exit=0, model='native595-q', shots=0,
            profile_sha256='profile', source=self.source, policy=driver.policy(0), actual_rows=114,
            audits={str(i):{} for i in range(57)}, scorer_seconds=10., scored_input_positions=100.)
        self.now = driver.DEADLINE.timestamp() - 20_000

    def admit(self, cost=None, now=None):
        with patch.object(driver, 'identity', return_value=self.source):
            return driver.admit_full(cost or self.cost, 'profile', 'native595-q', 0, 1000, self.now if now is None else now)

    def test_matching_cost_uses_measured_positions(self):
        value = self.admit()
        self.assertAlmostEqual(value['forecast_seconds'], 480.)
        self.assertEqual(value['hard_cap_seconds'], 5400)

    def test_stale_source_model_shot_profile_or_scope(self):
        for key, value in [('source', {}), ('model', 'new595-broad-q'), ('shots', 5),
                           ('profile_sha256', 'wrong'), ('actual_rows', 113), ('audits', {}), ('final_exit', 9)]:
            cost = dict(self.cost, **{key:value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.admit(cost)

    def test_nonpositive_or_nonfinite_timings(self):
        for key in ['scorer_seconds', 'scored_input_positions']:
            for value in [0, -1, True, math.inf, math.nan]:
                cost = dict(self.cost, **{key:value})
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.admit(cost)

    def test_over_budget_or_deadline_is_hold(self):
        with self.assertRaises(driver.ResourceHold):
            self.admit(dict(self.cost, scorer_seconds=1000.))
        with self.assertRaises(driver.ResourceHold):
            self.admit(now=driver.DEADLINE.timestamp() - 500)

    def test_policy_never_enables_train_or_cache(self):
        for shots in [0, 5]:
            value = driver.policy(shots)
            self.assertEqual(value['training'], 0)
            self.assertEqual(value['checkpoint_writes'], 0)
            self.assertFalse(value['chat_template'])
            self.assertFalse(value['use_cache'])
        with self.assertRaises(ValueError):
            driver.policy(3)

    def test_existing_arm_selector_covers_exact_model_shot_cross(self):
        self.assertEqual(set(driver.ARMS.values()), {(model, shot) for model in data.MODELS for shot in (0, 5)})
        self.assertEqual(driver.ARMS['native0'], ('native595-q', 0))
        self.assertEqual(driver.ARMS['broad5'], ('new595-broad-q', 5))


if __name__ == '__main__':
    unittest.main()
