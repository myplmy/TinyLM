"""GSM8K 저장/생성경계/실행 admission의 CPU 합성 검사. 모델/GPU를 열지 않는다."""
from contextlib import nullcontext
from dataclasses import dataclass
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import p106b_official_gsm8k as data
from scripts import diag_p106b_official_gsm8k as driver


class DataContract(unittest.TestCase):
    def test_row_shape_count_and_duplicates(self):
        row = dict(question='How many?', answer='work #### 2')
        self.assertEqual(data.validate_rows([row, row], 2)['duplicate_rows_preserved'], 1)
        with self.assertRaises(ValueError): data.validate_rows([row], 2)

    def test_blank_or_unknown_fields_rejected(self):
        for row in [dict(question='', answer='2'), dict(question='Q', answer=''), dict(question='Q', answer='2', extra='x')]:
            with self.subTest(row=row), self.assertRaises(ValueError): data.validate_rows([row], 1)

    def test_missing_final_marker_counted_not_rewritten(self):
        row = dict(question='Q', answer='Two')
        self.assertEqual(data.validate_rows([row], 1)['references_without_final_marker'], 1)
        self.assertEqual(row['answer'], 'Two')

    def test_declared_normalization_preserves_meaning(self):
        @dataclass
        class Options:
            sampler: str = 'default'
            split: str = 'train'
        self.assertTrue(data.declared_equal(dict(sampler='default'), Options()))
        self.assertFalse(data.declared_equal(dict(sampler='first_n'), Options()))
        self.assertFalse(data.declared_equal([dict(metric='exact_match')], [dict(metric='accuracy')]))

    def test_generation_options_copy_and_scope(self):
        def normalize(raw, maximum):
            return dict(dict(max_gen_toks=maximum, do_sample=False, temperature=0., until=['Question:']), **raw)
        def stops(until, eos): return list(until) + [eos]
        raw = dict(max_gen_toks=256)
        self.assertEqual(data.options(raw, normalize=normalize, stops=stops), (256, ['Question:', '']))
        self.assertEqual(raw, dict(max_gen_toks=256))
        for invalid in [dict(do_sample=True), dict(max_gen_toks=True), dict(max_gen_toks=257), dict(max_gen_toks=0), dict(top_p=.8)]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError): data.options(invalid, normalize=normalize, stops=stops)


class Tokenizer:
    def encode(self, text, add_special_tokens=False):
        return SimpleNamespace(ids=[5] * 900)
    def token_to_id(self, token): return 2 if token == '<eos>' else None
    def decode(self, ids, skip_special_tokens=True):
        return '' if ids == [2] else 'work #### 5' + chr(10) + 'Question: another'


class Capture:
    def __init__(self, tokenizer): self.tok, self.decoded_ids = tokenizer, None


class Forward:
    def __init__(self, model, precision): self.model, self.precision = model, precision


class Route:
    def __init__(self): self.calls = 0
    def assert_active(self): self.calls += 1


class GenerationContract(unittest.TestCase):
    def setUp(self):
        self.route = Route()
        self.active = dict(tokenizer=Tokenizer(), cfg=SimpleNamespace(vocab_size=32768, max_seq_len=1024),
            route=self.route, torch=SimpleNamespace(no_grad=nullcontext), model=object())
        self.calls = []

    def sampler(self, model, cfg, capture, context, **kwargs):
        prefix = capture.encode(context).ids
        self.calls.append(dict(prefix=prefix, context=context, kwargs=kwargs, precision=model.precision))
        capture.decoded_ids = prefix + [10, 4]
        return '', dict(finish_reason='STOP_SEQUENCE', generated_tokens=2, max_new=256,
            matched_stop_sequence=[4], eos_token_available=True, stop_at_eos_requested=True, stop_at_eos_effective=True)

    def emit(self, sampler=None):
        def postprocess(*, generation, stop, think_end_token):
            self.assertIsNone(think_end_token)
            return generation.split('Question:')[0]
        with patch.object(data, 'options', return_value=(256, ['Question:', '<|im_end|>'])):
            return data.emit_plain(self.active, 'Question: raw prompt Answer:', {},
                tools=(sampler or self.sampler, Capture, Forward), postprocess=postprocess)

    def test_raw_prefix_crop_and_original_sampler_semantics(self):
        output, meta = self.emit()
        self.assertEqual(output, 'work #### 5' + chr(10))
        self.assertEqual(len(self.calls[0]['prefix']), 768)
        self.assertEqual(self.calls[0]['context'], 'Question: raw prompt Answer:')
        self.assertEqual(meta['removed_prompt_tokens'], 132)
        self.assertEqual(meta['generated_ids'], [10, 4])
        self.assertEqual(self.calls[0]['precision'], 'fp32_math')
        self.assertEqual(self.calls[0]['kwargs']['mtp_tokens'], 1)
        self.assertEqual(self.calls[0]['kwargs']['temperature'], 0.)
        self.assertTrue(self.calls[0]['kwargs']['use_cache'])
        self.assertFalse(self.calls[0]['kwargs']['logits_last_only'])
        self.assertEqual(self.route.calls, 2)

    def test_sampler_token_count_lie_rejected(self):
        def malformed(*args, **kwargs):
            answer, meta = self.sampler(*args, **kwargs)
            meta['generated_tokens'] = 3
            return answer, meta
        with self.assertRaises(ValueError): self.emit(malformed)

    def test_wrong_stop_token_receipt_rejected(self):
        def malformed(*args, **kwargs):
            answer, meta = self.sampler(*args, **kwargs)
            meta['matched_stop_sequence'] = [11]
            return answer, meta
        with self.assertRaises(ValueError): self.emit(malformed)

    def test_wrong_context_model_or_ids_rejected(self):
        self.active['cfg'].max_seq_len = 512
        with self.assertRaises(ValueError): self.emit()
        self.active['cfg'].max_seq_len = 1024
        self.active['cfg'].vocab_size = 4
        with self.assertRaises(ValueError): self.emit()


class ResultAndCost(unittest.TestCase):
    def sample_rows(self):
        return [dict(filter=name, doc_id=i, exact_match=i % 2) for name in ['strict-match', 'flexible-extract'] for i in range(8)]

    def test_two_filters_are_one_document_set(self):
        result = driver.sample_audits(self.sample_rows(), 8)
        self.assertEqual(result['strict-match']['rows'], 8)
        self.assertEqual(result['strict-match']['correct'], 4)
        self.assertEqual(result['flexible-extract']['exact_match'], .5)

    def test_partial_duplicate_or_third_filter_rejected(self):
        for rows in [self.sample_rows()[:-1], self.sample_rows() + [dict(filter='other', doc_id=0, exact_match=0)],
                     [dict(row, doc_id=0) for row in self.sample_rows()]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError): driver.sample_audits(rows, 8)

    def test_non_binary_metric_rejected(self):
        rows = self.sample_rows(); rows[0]['exact_match'] = .5
        with self.assertRaises(ValueError): driver.sample_audits(rows, 8)

    def cost(self):
        return dict(status='LIMITED_COST_DIAGNOSTIC', model='native595-q', final_exit=0,
            actual_rows=8, source=dict(sha256='source'), policy=driver.policy(), profile_sha256='profile', generation_seconds=10.)

    def admit(self, value=None, now=None):
        with patch.object(driver, 'identity', return_value=dict(sha256='source')):
            return driver.admit_full(value or self.cost(), 'native595-q', 'profile',
                driver.DEADLINE.timestamp() - 30000 if now is None else now)

    def test_cost_forecast_and_bound(self):
        self.assertAlmostEqual(self.admit()['forecast_seconds'], 10 / 8 * 1319 * 1.5 + 120)
        self.assertEqual(self.admit()['hard_cap_seconds'], 10800)

    def test_bad_scope_or_timing_rejected(self):
        for key, value in [('model', 'new595-broad-q'), ('source', {}), ('actual_rows', 7),
                           ('final_exit', 9), ('generation_seconds', 0), ('generation_seconds', math.nan)]:
            with self.subTest(key=key), self.assertRaises(ValueError): self.admit(dict(self.cost(), **{key:value}))

    def test_deadline_or_high_cost_is_hold(self):
        with self.assertRaises(driver.ResourceHold): self.admit(dict(self.cost(), generation_seconds=1000.))
        with self.assertRaises(driver.ResourceHold): self.admit(now=driver.DEADLINE.timestamp() - 2500)


if __name__ == '__main__':
    unittest.main()
