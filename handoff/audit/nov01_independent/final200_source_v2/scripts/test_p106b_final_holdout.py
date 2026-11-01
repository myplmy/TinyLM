"""응답 품질과 분리한 동결·판독 경계·부분 결과 보존의 CPU 시험."""
import copy
import json
import unittest
from unittest.mock import patch
from scripts import p106b_final_holdout as data
from scripts import diag_p106b_final_holdout as driver


class Writer:
    def __init__(self):
        self.rows = []

    def append(self, row):
        self.rows.append(copy.deepcopy(row))


class Budget:
    def __init__(self, fail_at=100):
        self.calls, self.fail_at = 0, fail_at

    def check(self):
        self.calls += 1
        if self.calls == self.fail_at:
            raise TimeoutError('test budget')


class TestHoldout(unittest.TestCase):
    def test_korean_particles_keep_consonants_and_vowels(self):
        self.assertEqual(data.particle('유진', '이', '가'), '유진이')
        self.assertEqual(data.particle('미나', '이', '가'), '미나가')
        self.assertEqual(data.particle('도윤', '은', '는'), '도윤은')
        self.assertEqual(data.particle('미나', '은', '는'), '미나는')

    def test_rendered_name_particles_do_not_use_fixed_wrong_suffixes(self):
        for row in data.build() + data.build('dev'):
            if row['language'] == 'ko':
                for name in ('소담', '가온', '보람', '다온', '하린', '도윤', '서진', '유진'):
                    self.assertNotIn(name + '가 ', row['prompt'])
                    self.assertNotIn(name + '는 ', row['prompt'])

    def test_exact_counts_and_determinism(self):
        self.assertEqual(data.build(), data.build())
        report = data.validate(data.build(), data.build('dev'))
        self.assertEqual((report['final_rows'], report['dev_rows']), (200, 20))
        self.assertEqual(report['counts']['ko'], {category: 20 for category in data.CATEGORIES})

    def test_final_dev_prompts_disjoint(self):
        self.assertFalse({row['prompt'] for row in data.build()} & {row['prompt'] for row in data.build('dev')})

    def test_wrong_split_and_duplicate_are_rejected(self):
        for change in ('split', 'duplicate'):
            final = data.build()
            if change == 'split':
                final[0]['split'] = 'dev'
            else:
                final[1]['prompt'] = final[0]['prompt']
            with self.subTest(change=change), self.assertRaises(ValueError):
                data.validate(final, data.build('dev'))

    def test_missing_type_balance_is_rejected(self):
        dev = data.build('dev')
        dev[0]['category'] = 'everyday'
        with self.assertRaises(ValueError):
            data.validate(data.build(), dev)

    def test_exact_answer_does_not_accept_explanation(self):
        case = dict(match_rule='exact', reference='11')
        self.assertTrue(data.reference_match(' 11 ', case))
        self.assertFalse(data.reference_match('The answer is 11.', case))

    def test_json_requires_content_and_types(self):
        case = dict(match_rule='json', reference=dict(count=1, name='Mina'))
        self.assertTrue(data.reference_match('{"name":"Mina", "count":1}', case))
        for answer in ['{"name":"Mina","count":true}', '{"name":"Mina","count":1.0}',
                       '{"name":"Mina","count":1,"extra":0}', '```json {"name":"Mina","count":1}```']:
            self.assertFalse(data.reference_match(answer, case))

    def test_duplicate_json_key_rejected(self):
        case = dict(match_rule='json', reference=dict(answer='red'))
        self.assertFalse(data.reference_match('{"answer":"wrong","answer":"red"}', case))

    def test_open_answer_is_not_string_graded(self):
        case = dict(match_rule='manual', reference=None)
        self.assertIsNone(data.reference_match('Good morning!', case))

    def test_requested_repeat_is_not_automatically_failed(self):
        case = next(row for row in data.build() if row['required_repetition'])
        self.assertTrue(data.reference_match(case['reference'], case))
        flags = data.review_signals(case['reference'], dict(finish_reason='EOS'), case)
        self.assertTrue(flags['required_repetition'])
        self.assertFalse(flags['automatic_failure_or_quality_verdict'])

    def test_rule_outputs_have_160_closed_40_open(self):
        closed = [r for r in data.build() if r['match_rule'] != 'manual']
        self.assertEqual(len(closed), 160)
        for row in closed:
            answer = json.dumps(row['reference'], ensure_ascii=False) if row['match_rule'] == 'json' else row['reference']
            self.assertTrue(data.reference_match(answer, row), row['id'])

    def emitter(self, active, prompt, max_new):
        self.assertEqual(max_new, 96)
        return 'not correct', dict(generated_tokens=3, finish_reason='EOS')

    def test_collection_is_raw_first_answer_and_not_quality_pass(self):
        writer, report = Writer(), dict(model='test', completed_rows=0)
        cases = data.build()[:3]
        original = copy.deepcopy(cases)
        driver.collect({}, cases, writer, Budget(), report, emit=self.emitter)
        self.assertEqual((report['completed_rows'], len(writer.rows)), (3, 3))
        self.assertEqual(cases, original)
        for row in writer.rows:
            self.assertEqual(row['answer'], 'not correct')
            self.assertIsNone(row['stable'])
            self.assertIsNone(row['responsive'])
            self.assertIsNone(row['correct'])

    def test_completed_case_survives_post_case_timeout(self):
        writer, report = Writer(), dict(model='test', completed_rows=0)
        with self.assertRaises(TimeoutError):
            driver.collect({}, data.build()[:3], writer, Budget(fail_at=2), report, emit=self.emitter)
        self.assertEqual((report['completed_rows'], len(writer.rows)), (1, 1))

    def test_prior_answer_survives_later_emit_failure(self):
        writer, report = Writer(), dict(model='test', completed_rows=0)
        called = []
        def emit(*args, **kwargs):
            called.append(1)
            if len(called) == 2:
                raise RuntimeError('injected failure')
            return self.emitter(*args, **kwargs)
        with self.assertRaises(RuntimeError):
            driver.collect({}, data.build()[:3], writer, Budget(), report, emit=emit)
        self.assertEqual((report['completed_rows'], len(writer.rows)), (1, 1))

    def test_invalid_token_receipt_not_counted(self):
        writer, report = Writer(), dict(model='test', completed_rows=0)
        with self.assertRaises(ValueError):
            driver.collect({}, data.build()[:1], writer, Budget(), report,
                           emit=lambda *_a, **_k: ('answer', dict(generated_tokens=True)))
        self.assertEqual((report['completed_rows'], len(writer.rows)), (0, 0))

    def test_read_inputs_refuses_unknown_source_before_reading_data(self):
        fake = dict(schema=data.SCHEMA, status='FINAL200_CPU_FROZEN', source={'changed': True},
                    authority_directive=104, deadline=driver.DEADLINE.isoformat())
        with patch.object(driver.resource, 'read_ref', return_value=fake), self.assertRaises(ValueError):
            driver.read_inputs('unused', 'unused')


if __name__ == '__main__':
    unittest.main()
