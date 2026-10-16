"""합성 원형·원답·메모리 토크나이저만 쓰는 독립 검산 회귀."""
from pathlib import Path
import copy
import statistics
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_falcon_readback as readback


class FixtureTokenizer:
    def __init__(self):
        self.char_to_id = {}
        self.id_to_char = {}

    def encode(self, text):
        result = []
        for char in text:
            if char not in self.char_to_id:
                index = 100 + len(self.char_to_id)
                self.char_to_id[char] = index
                self.id_to_char[index] = char
            result.append(self.char_to_id[char])
        return SimpleNamespace(ids=result)

    def decode(self, ids):
        return ''.join('<EOS>' if value == 11 else self.id_to_char[value] for value in ids)


def freeze(row):
    result = copy.deepcopy(row)
    result['case_id'] = readback._sha([row['task'], row['index'], row])
    return result


def mc_case(index=0, skip=None, pairs=False):
    item = dict(ctx='문맥', choices=[' 가', ' 나나다'], gold=0, _iid='문항' + str(index))
    if pairs:
        item['pairs'] = [['문맥 가', ' 가'], ['문맥 나', ' 나나다']]
    return freeze(dict(task='piqa', kind='mc', index=index, item=item, expected_skip=skip))


def mc_event(row, tok):
    pairs = row['item'].get('pairs') or [(row['item']['ctx'], choice) for choice in row['item']['choices']]
    sums = [4., 6.]
    ntokens = [len(tok.encode(cont).ids) for prompt, cont in pairs]
    nchars = [max(1, len(cont)) for prompt, cont in pairs]
    means = [value / count for value, count in zip(sums, ntokens)]
    gold = row['item']['gold']
    wrong = [value for index, value in enumerate(means) if index != gold]
    scores = dict(id=row['item']['_iid'], gold=gold,
        pred_internal=min(range(2), key=lambda i: means[i]),
        pred_internal_norm=min(range(2), key=lambda i: sums[i] / ntokens[i]),
        pred_harness=0, pred_harness_norm=min(range(2), key=lambda i: sums[i] / nchars[i]),
        sum_nll=sums, mean_nll=means, score=list(means), n_tokens=ntokens, n_chars=nchars,
        margin_mean=statistics.fmean(wrong) - means[gold], margin_decision=min(wrong) - means[gold])
    return dict(kind='mc', task=row['task'], case_id=row['case_id'], index=row['index'],
                source_item=copy.deepcopy(row['item']), scores=scores, skipped=False, seconds=.01)


def gen_case(tok, index=0, task='gsm8k_plain', gold='-5'):
    prompt = '질문: 값은?\n답:'
    return freeze(dict(kind='gen', task=task, index=index, id='산수' + str(index),
        question='값은?', prompt=prompt, prompt_tokens=len(tok.encode(prompt).ids),
        golds=[gold], expected_skip=None))


def gen_event(row, tok, answer='  -5  ', eos=True):
    new = tok.encode(answer).ids + ([11] if eos else [])
    final = tok.decode(new[:-1] if eos else new).strip()
    numeric = readback.public.numerical(final)
    return dict(kind='gen', task=row['task'], case_id=row['case_id'], index=row['index'],
        id=row['id'], prompt=row['prompt'], question=row['question'], golds=list(row['golds']),
        input_ids=tok.encode(row['prompt']).ids, new_ids=new, raw_answer=tok.decode(new), answer=final,
        numeric_exact=int(numeric is not None and numeric == readback.public.numerical(row['golds'][0])),
        skipped=False, seconds=.1, finish_reason='eos' if eos else 'max_new_tokens',
        generation=dict(temperature=0., max_new=128, do_sample=False, use_cache=True, bos_added=False))


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.tok = FixtureTokenizer()

    def test_mixed_rows_counts_outcomes_and_input_immutability(self):
        mc, gen = mc_case(), gen_case(self.tok)
        originals = [mc, gen]
        events = [mc_event(mc, self.tok), gen_event(gen, self.tok)]
        before = copy.deepcopy((events, originals))
        result = readback.recount_reference(events, originals, self.tok)
        self.assertEqual(result['summary']['piqa'], dict(n=1, correct=1, char_norm_correct=0, skip=0, skipped=0))
        self.assertEqual(result['summary']['gsm8k_plain']['correct'], 1)
        self.assertEqual(result['mc_outcomes'][0]['pred'], 0)
        self.assertEqual(result['mc_outcomes'][0]['char_norm_pred'], 1)
        self.assertEqual((events, originals), before)
        self.assertEqual(readback.recount_reference(list(reversed(events)), originals, self.tok), result)

    def test_original_and_event_missing_duplicate_unknown_and_caseid_tamper(self):
        row = mc_case()
        event = mc_event(row, self.tok)
        for events, rows in (([], [row]), ([event, event], [row]), ([event], [row, row]),
                             ([dict(event, case_id='F' * 64)], [row]),
                             ([dict(event, case_id=[])], [row])):
            with self.assertRaises(ValueError):
                readback.recount_reference(events, rows, self.tok)
        changed = copy.deepcopy(row)
        changed['index'] += 1
        with self.assertRaises(ValueError):
            readback.recount_reference([event], [changed], self.tok)

    def test_frozen_skip_reason_exact_and_eligible_may_not_be_skipped(self):
        row = mc_case(skip='seq_max_exceeded')
        event = dict(task=row['task'], case_id=row['case_id'], index=row['index'], skipped=True, reason=row['expected_skip'])
        self.assertEqual(readback.recount_reference([event], [row], self.tok)['summary']['piqa']['skip'], 1)
        for key, value in (('reason', 'gold_missing'), ('skipped', False), ('task', 'hellaswag'), ('index', 9)):
            with self.assertRaises(ValueError):
                readback.recount_reference([dict(event, **{key: value})], [row], self.tok)
        eligible = mc_case()
        forged = dict(task=eligible['task'], case_id=eligible['case_id'], index=eligible['index'], skipped=True, reason='seq_max_exceeded')
        with self.assertRaises(ValueError):
            readback.recount_reference([forged], [eligible], self.tok)

    def test_mc_source_gold_choice_count_and_actual_lengths(self):
        row = mc_case(pairs=True)
        event = mc_event(row, self.tok)
        readback.recount_reference([event], [row], self.tok)
        for change in ('source', 'gold', 'count', 'tokens', 'chars'):
            changed = copy.deepcopy(event)
            if change == 'source':
                changed['source_item']['pairs'][0][1] = '다른 선택지'
            elif change == 'gold':
                changed['scores']['gold'] = 1
            elif change == 'count':
                changed['scores']['sum_nll'].pop()
            elif change == 'tokens':
                changed['scores']['n_tokens'][0] += 1
            else:
                changed['scores']['n_chars'][0] += 1
            with self.assertRaises(ValueError, msg=change):
                readback.recount_reference([changed], [row], self.tok)

    def test_mc_nonfinite_mean_sum_consistency_and_predictions(self):
        row = mc_case()
        event = mc_event(row, self.tok)
        for name in ('sum_nll', 'mean_nll', 'score'):
            for value in (float('nan'), float('inf'), -1.):
                changed = copy.deepcopy(event)
                changed['scores'][name][0] = value
                with self.assertRaises(ValueError):
                    readback.recount_reference([changed], [row], self.tok)
        changed = copy.deepcopy(event)
        changed['scores']['mean_nll'][0] += .1
        changed['scores']['score'][0] += .1
        with self.assertRaises(ValueError):
            readback.recount_reference([changed], [row], self.tok)
        for name in ('pred_harness', 'pred_harness_norm', 'pred_internal', 'pred_internal_norm'):
            changed = copy.deepcopy(event)
            changed['scores'][name] = 1 - changed['scores'][name]
            with self.assertRaises(ValueError):
                readback.recount_reference([changed], [row], self.tok)

    def test_mc_mean_sum_rounding_tolerance_is_the_declared_bound(self):
        row = mc_case()
        event = mc_event(row, self.tok)
        inside = copy.deepcopy(event)
        delta = .0005 / inside['scores']['n_tokens'][0]
        inside['scores']['mean_nll'][0] += delta
        inside['scores']['score'][0] += delta
        readback.recount_reference([inside], [row], self.tok)
        outside = copy.deepcopy(event)
        delta = .005 / outside['scores']['n_tokens'][0]
        outside['scores']['mean_nll'][0] += delta
        outside['scores']['score'][0] += delta
        with self.assertRaises(ValueError):
            readback.recount_reference([outside], [row], self.tok)

    def test_mc_equal_scores_use_the_first_argmin(self):
        row = mc_case()
        event = mc_event(row, self.tok)
        event['scores'].update(sum_nll=[4., 4.], mean_nll=[2., 1.], score=[2., 1.],
            pred_harness=0, pred_harness_norm=1, pred_internal=1, pred_internal_norm=1,
            margin_mean=-1., margin_decision=-1.)
        result = readback.recount_reference([event], [row], self.tok)
        self.assertEqual(result['mc_outcomes'][0]['pred'], 0)
        event['scores']['pred_harness'] = 1
        with self.assertRaises(ValueError):
            readback.recount_reference([event], [row], self.tok)

    def test_gen_original_prompt_question_gold_input_and_generation_contract(self):
        row = gen_case(self.tok)
        event = gen_event(row, self.tok)
        for field, value in (('prompt', '바뀐 프롬프트'), ('question', '다른 질문'),
                             ('golds', ['5']), ('input_ids', [99] + event['input_ids'])):
            changed = copy.deepcopy(event)
            changed[field] = value
            with self.assertRaises(ValueError):
                readback.recount_reference([changed], [row], self.tok)
        changed = copy.deepcopy(event)
        changed['generation']['bos_added'] = True
        with self.assertRaises(ValueError):
            readback.recount_reference([changed], [row], self.tok)

    def test_gen_eos_must_be_first_and_final_and_new_count_bounded(self):
        row = gen_case(self.tok)
        event = gen_event(row, self.tok)
        for values in ([11, *event['new_ids']], [*event['new_ids'], 123], [120] * 129):
            changed = copy.deepcopy(event)
            changed['new_ids'] = values
            with self.assertRaises(ValueError):
                readback.recount_reference([changed], [row], self.tok)

    def test_gen_decode_strip_finish_and_numeric_recount(self):
        row = gen_case(self.tok)
        event = gen_event(row, self.tok)
        for field, value in (('raw_answer', event['answer']), ('answer', ' -5 '),
                             ('finish_reason', 'max_new_tokens'), ('numeric_exact', 0)):
            changed = copy.deepcopy(event)
            changed[field] = value
            with self.assertRaises(ValueError):
                readback.recount_reference([changed], [row], self.tok)
        short_no_eos = gen_event(row, self.tok, eos=False)
        with self.assertRaisesRegex(ValueError, '정확히 128'):
            readback.recount_reference([short_no_eos], [row], self.tok)
        wrong_sign = gen_event(row, self.tok, answer='5')
        self.assertEqual(readback.recount_reference([wrong_sign], [row], self.tok)['summary']['gsm8k_plain']['correct'], 0)

    def test_zero_content_eos_and_decimal_final_number_are_preserved(self):
        row = gen_case(self.tok, gold='-1.5')
        empty = gen_event(row, self.tok, answer='')
        self.assertEqual(readback.recount_reference([empty], [row], self.tok)['summary']['gsm8k_plain']['correct'], 0)
        numeric = gen_event(row, self.tok, answer='풀이\n#### -1.50')
        self.assertEqual(readback.recount_reference([numeric], [row], self.tok)['summary']['gsm8k_plain']['correct'], 1)

    def test_no_eos_requires_full128_and_empty_or_short_is_not_completion(self):
        row = gen_case(self.tok)
        full = gen_event(row, self.tok, answer='-5' + ' ' * 126, eos=False)
        self.assertEqual(len(full['new_ids']), 128)
        self.assertEqual(readback.recount_reference([full], [row], self.tok)['summary']['gsm8k_plain']['correct'], 1)
        for text in ('', '-5', ' ' * 127):
            short = gen_event(row, self.tok, answer=text, eos=False)
            with self.assertRaisesRegex(ValueError, '정확히 128'):
                readback.recount_reference([short], [row], self.tok)

    def test_input_output_token_ids_must_stay_within32768_vocabulary(self):
        row = gen_case(self.tok)
        event = gen_event(row, self.tok)
        for field in ('input_ids', 'new_ids'):
            for value in (-1, 32768, True):
                changed = copy.deepcopy(event)
                changed[field][0] = value
                with self.assertRaises(ValueError):
                    readback.recount_reference([changed], [row], self.tok)

    def test_backend_no_bos_and_special_decode_reconciled(self):
        fixture = self.tok
        class Backend:
            def encode(self, text, *, add_special_tokens):
                if add_special_tokens is not False:
                    raise ValueError('합성 backend의 no-BOS 계약 위반')
                return fixture.encode(text).ids
            def decode(self, ids, *, skip_special_tokens, clean_up_tokenization_spaces):
                if skip_special_tokens is not False or clean_up_tokenization_spaces is not False:
                    raise ValueError('합성 backend의 decode 계약 위반')
                return fixture.decode(ids)
        class Adapter:
            tokenizer = Backend()
            def encode(self, text):
                return fixture.encode(text)
            def decode(self, ids):
                return fixture.decode(ids)
        adapter = Adapter()
        row = gen_case(adapter)
        event = gen_event(row, adapter)
        readback.recount_reference([event], [row], adapter)
        class BadAdapter(Adapter):
            def encode(self, text):
                return SimpleNamespace(ids=[99] + super().encode(text).ids)
        with self.assertRaises(ValueError):
            readback.recount_reference([event], [row], BadAdapter())


if __name__ == '__main__':
    unittest.main()
