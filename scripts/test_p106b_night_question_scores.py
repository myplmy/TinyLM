"""메모리 tokenizer와 함수형 head만 사용하는 순수 합성 CPU 회귀."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from scripts import p106b_night_question_scores as q


class Tokenizer:
    specials = {'<|im_start|>': 3, '<|im_end|>': 4, '<pad>': 0}
    def __init__(self, straddle=None, variable=False): self.straddle, self.variable = straddle, variable
    def token_to_id(self, text): return self.specials.get(text)
    def encode(self, text):
        ids, offsets, i = [], [], 0
        while i < len(text):
            special = next((s for s in self.specials if text.startswith(s, i)), None)
            if special: size, value = len(special), self.specials[special]
            elif self.straddle and text.startswith(self.straddle, i): size, value = len(self.straddle), 250
            else: size, value = 1, ord(text[i]) + 16
            if self.variable and 'Which second?' in text and text[max(0, i - len('assistant\n')):i] == 'assistant\n': value += 100
            ids.append(value); offsets.append((i, i + size)); i += size
        return NS(ids=ids, offsets=offsets)


def cases(language='en'):
    context = 'red blue' if language == 'en' else '빨강🙂 파랑'
    words = ('red', 'blue') if language == 'en' else ('빨강', '파랑')
    return [dict(root='root' + str(i), language=language, split='test', article_id='article', article_title='title',
        context_id='context', qa_id='qa' + str(i), context=context, question=('Which first?' if i == 0 else 'Which second?'),
        answers=[dict(text=word, answer_start=context.index(word))], aliases=[word], source_path='fixture.json',
        source_sha256='A' * 64) for i, word in enumerate(words)]


def uniform_events(bundle):
    return [q._event(cell, [-2.] * (cell['content_token_count'] + 1)) for cell in bundle['cells']]


class QuestionScoreTests(unittest.TestCase):
    def setUp(self): self.tok = Tokenizer()

    def test_four_cells_preserve_source_question_meta_and_separate_candidate(self):
        original = cases(); before = copy.deepcopy(original); bundle = q.build_records(original, self.tok)
        self.assertEqual(original, before); self.assertEqual(len(bundle['cells']), 4)
        for cell in bundle['cells']:
            qi, ai = cell['question_index'], cell['candidate_index']
            expected = q.data.render_view(original[qi], 0)
            self.assertEqual(cell['row']['meta'], expected['meta'])
            self.assertEqual(cell['row']['messages'][0], expected['messages'][0])
            self.assertEqual(q.data.text(cell['row']['messages'][1]), original[ai]['aliases'][0])
            self.assertEqual(cell['scoring_candidate']['root'], original[ai]['root'])
            self.assertFalse(cell['proof']['training_example'])
        json.dumps(bundle, allow_nan=False)

    def test_exact_shift_content_only_and_separate_eot(self):
        bundle = q.build_records(cases(), self.tok)
        for cell in bundle['cells']:
            ids, labels, text = q.data.encode_view(cell['row'], self.tok)
            self.assertEqual(cell['x'], ids[:-1]); self.assertEqual(cell['y'], labels[1:])
            positions, targets = q._cell(cell)
            self.assertEqual(targets[-1], 4); self.assertNotIn(4, targets[:-1])
            self.assertEqual([ids[i + 1] for i in positions], targets)
            self.assertEqual([i for i, v in enumerate(cell['y']) if v != -100], positions)
            self.assertEqual(cell['content_token_count'], len(cell['scoring_candidate']['text']))

    def test_unicode_and_repeated_question_inside_context(self):
        values = cases('ko')
        for value in values:
            value['context'] = 'Which first? e\u0301 ' + value['context']
            value['answers'][0]['answer_start'] = value['context'].index(value['aliases'][0])
        bundle = q.build_records(values, self.tok)
        self.assertEqual(bundle['language'], 'ko')
        self.assertEqual(bundle['cells'][0]['content_token_count'], 2)

    def test_same_answer_target_ids_match_for_both_questions_not_answer_lengths(self):
        bundle = q.build_records(cases(), self.tok)
        self.assertEqual(bundle['cells'][0]['content_target_ids'], bundle['cells'][2]['content_target_ids'])
        self.assertEqual(bundle['cells'][1]['content_target_ids'], bundle['cells'][3]['content_target_ids'])
        self.assertNotEqual(bundle['cells'][0]['content_token_count'], bundle['cells'][1]['content_token_count'])

    def test_context_dependent_target_ids_or_boundary_straddle_rejected(self):
        for tok in (Tokenizer(straddle='\nred'), Tokenizer(straddle='red<|im_end|>'), Tokenizer(variable=True)):
            with self.subTest(straddle=tok.straddle, variable=tok.variable), self.assertRaises(ValueError):
                q.build_records(cases(), tok)

    def test_overlength_empty_answer_different_context_or_duplicate_root_rejected(self):
        for kind in ('long', 'empty', 'context', 'root'):
            values = cases()
            if kind == 'long':
                for value in values: value['context'] += 'x' * 1100
            elif kind == 'empty': values[0]['aliases'] = []
            elif kind == 'context': values[1]['context'] += ' different'
            else: values[1]['root'] = values[0]['root']
            with self.assertRaises(ValueError): q.build_records(values, self.tok)

    def test_logits_fp32_logsoftmax_content_first_and_eot_reference(self):
        cell = q.build_records(cases(), self.tok)['cells'][0]
        generator = torch.Generator().manual_seed(1337)
        logits = torch.randn(len(cell['x']), 256, generator=generator)
        event = q.score_logits(cell, logits); pos, target = q._cell(cell)
        reference = torch.log_softmax(logits[pos].float(), -1)[torch.arange(len(pos)), target].tolist()
        self.assertEqual(event['token_logprobs'], reference)
        self.assertEqual(event['metrics']['content_sum'], sum(reference[:-1]))
        self.assertEqual(event['metrics']['content_mean'], sum(reference[:-1]) / (len(reference) - 1))
        self.assertEqual(event['metrics']['first_content'], reference[0])
        self.assertEqual(event['metrics']['eot'], reference[-1])
        self.assertEqual(event['metrics']['eot_included_sum'], sum(reference[:-1]) + reference[-1])

    def test_hidden_chunk_head_matches_dense_logits_without_model(self):
        cell = q.build_records(cases(), self.tok)['cells'][1]
        generator = torch.Generator().manual_seed(55)
        hidden = torch.randn(len(cell['x']), 5, generator=generator); weight = torch.randn(5, 256, generator=generator)
        seen = []
        def head(value): seen.append(value.shape[1]); return value @ weight
        actual = q.score_hidden(cell, hidden, head, chunk=2)
        expected = q.score_logits(cell, hidden @ weight)
        self.assertEqual(actual, expected); self.assertLessEqual(max(seen), 2)

    def test_nonfinite_shape_vocab_padding_and_invalid_chunk_refused(self):
        cell = q.build_records(cases(), self.tok)['cells'][0]; n = len(cell['x'])
        for logits in (torch.zeros(n + 1, 256), torch.zeros(n, 2), torch.zeros(n, 256, dtype=torch.long),
                torch.full((n, 256), float('nan')), torch.full((n, 256), float('inf'))):
            with self.assertRaises(ValueError): q.score_logits(cell, logits)
        for hidden, head, chunk in ((torch.zeros(n + 1, 5), lambda x: x, 2),
                (torch.full((n, 5), float('nan')), lambda x: x, 2),
                (torch.zeros(n, 5), lambda x: torch.zeros(x.shape[1], 256), 2),
                (torch.zeros(n, 5), lambda x: torch.zeros(1, x.shape[1], 256), True)):
            with self.assertRaises(ValueError): q.score_hidden(cell, hidden, head, chunk)

    def test_record_target_position_or_length_tampering_refused(self):
        base = q.build_records(cases(), self.tok)['cells'][0]
        for field, value in (('content_positions', [0]), ('content_target_ids', [100]), ('content_token_count', 99),
                ('eot_position', 0), ('y', [-100] * len(base['y'])), ('x', base['x'][:-1])):
            cell = copy.deepcopy(base); cell[field] = value
            with self.assertRaises(ValueError): q.score_logits(cell, torch.zeros(len(base['x']), 256))

    def test_two_direction_gaps_fixed_answer_positive_negative_zero(self):
        bundle = q.build_records(cases(), self.tok); raw = uniform_events(bundle)
        for i, event in enumerate(raw):
            lp = (-1. if i == 0 else -3. if i == 2 else -2.)
            raw[i] = q._event(bundle['cells'][i], [lp] * (bundle['cells'][i]['content_token_count'] + 1))
        report = q.summarize(raw, [bundle])
        self.assertEqual(report['outcomes'][0]['gaps']['content_mean'], [2., 0.])
        self.assertEqual(report['overall']['gaps']['content_mean']['positive'], 1)
        self.assertEqual(report['overall']['gaps']['content_mean']['zero'], 1)
        self.assertFalse(report['quality_pass_declared']); self.assertFalse(report['scoring_candidate_is_semantic_negative'])
        opposite = [q._event(cell, [-4. if cell['question_index'] == cell['candidate_index'] else -1.] *
            (cell['content_token_count'] + 1)) for cell in bundle['cells']]
        self.assertEqual(q.summarize(opposite, [bundle])['overall']['gaps']['content_mean']['negative'], 2)
        json.dumps(report, allow_nan=False)

    def test_missing_duplicate_unknown_score_cell_and_nonfinite_rejected(self):
        bundle = q.build_records(cases(), self.tok); raw = uniform_events(bundle)
        variants = [raw[:-1], raw + [raw[0]], [raw[0]] + raw[:-1]]
        for field, value in (('record_sha256', 'BAD'), ('question_index', True), ('content_token_count', 99), ('bundle_id', 'BAD')):
            bad = copy.deepcopy(raw); bad[0][field] = value; variants.append(bad)
        bad = copy.deepcopy(raw); bad[0]['token_logprobs'][0] = float('nan'); variants.append(bad)
        bad = copy.deepcopy(raw); bad[0]['metrics']['content_sum'] += 1; variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError): q.summarize(bad, [bundle])

    def test_fixed_bundle_duplicate_or_changed_candidate_meta_refused(self):
        bundle = q.build_records(cases(), self.tok); raw = uniform_events(bundle)
        with self.assertRaises(ValueError): q.summarize(raw * 2, [bundle, bundle])
        bad = copy.deepcopy(bundle); bad['cells'][0]['row']['meta']['question_original'] = 'changed'
        with self.assertRaises(ValueError): q.summarize(raw, [bad])

    def test_score_precision_metadata_and_overflow_cannot_be_hidden(self):
        bundle = q.build_records(cases(), self.tok); raw = uniform_events(bundle)
        for change in (dict(softmax_precision='FP16'), dict(training_performed=True)):
            bad = copy.deepcopy(raw); bad[0].update(change)
            with self.assertRaises(ValueError): q.summarize(bad, [bundle])
        with self.assertRaises(ValueError): q._gap_stats([1e308, 1e308])

    def test_empty_or_eot_only_and_bool_logprob_are_refused(self):
        cell = q.build_records(cases(), self.tok)['cells'][0]
        for values in ([], [-1.], [False] * (cell['content_token_count'] + 1),
                [1.] * (cell['content_token_count'] + 1)):
            with self.assertRaises(ValueError): q._event(cell, values)

    def test_free_view0_both_correct_link_not_selection_and_bad_free_refused(self):
        values = cases(); bundle = q.build_records(values, self.tok); raw = uniform_events(bundle)
        free = [dict(root=c['root'], language=c['language'], view=0, question=c['question'], context=c['context'],
            aliases=c['aliases'], answer=c['aliases'][0], scores=q.qa_scores(c['aliases'][0], c['aliases'], c['language'])) for c in values]
        result = q.summarize(raw, [bundle], free)
        self.assertTrue(result['outcomes'][0]['free_view0_both_correct'])
        self.assertEqual(result['overall']['by_free_view0']['both_correct']['content_mean']['n'], 2)
        for field, value in (('view', 1), ('question', 'changed'), ('aliases', ['wrong'])):
            bad = copy.deepcopy(free); bad[0][field] = value
            with self.assertRaises(ValueError): q.summarize(raw, [bundle], bad)
        with self.assertRaises(ValueError): q.summarize(raw, [bundle], free[:-1])


if __name__ == '__main__': unittest.main()
