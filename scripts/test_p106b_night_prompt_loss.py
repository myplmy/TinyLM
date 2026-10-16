"""In-memory tokenizer/head fixtures only; no real tokenizer/model/data read."""
from pathlib import Path
import copy
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
import torch.nn.functional as F
from scripts import p106b_night_prompt_loss as method


class FixtureTokenizer:
    specials = {'<|im_start|>': 1, '<|im_end|>': 2, '<pad>': 3}

    def __init__(self, straddle=None):
        self.straddle = straddle

    def token_to_id(self, text):
        return self.specials.get(text)

    def encode(self, text):
        ids, offsets, index = [], [], 0
        while index < len(text):
            special = next((s for s in self.specials if text.startswith(s, index)), None)
            if special:
                length, value = len(special), self.specials[special]
            elif self.straddle and text.startswith(self.straddle, index):
                length, value = len(self.straddle), 99999
            else:
                length, value = 1, ord(text[index]) + 10
            ids.append(value)
            offsets.append((index, index + length))
            index += length
        return SimpleNamespace(ids=ids, offsets=offsets)


def pair(language='en', context=None, question=None, answer=None):
    if context is None:
        context = '가온은 12세입니다. 질문: 나이는?' if language == 'ko' else 'Mira is twelve. Age? appears here too.'
    if question is None:
        question = '나이는?' if language == 'ko' else 'Age?'
    if answer is None:
        answer = '12' if language == 'ko' else 'twelve'
    return dict(root='fixture-root', language=language, split='train', article_id='fixture-article',
        article_title='fixture-title', context_id='fixture-context', qa_id='fixture-question',
        question=question, context=context, answers=[dict(text=answer, answer_start=0)],
        aliases=[answer], source_path='fixture-in-memory', source_sha256='A' * 64)


class ToyHead(torch.nn.Module):
    def __init__(self, width=5, vocab=11, wrong_shape=False):
        super().__init__()
        generator = torch.Generator().manual_seed(55)
        self.weight = torch.nn.Parameter(torch.randn(width, vocab, generator=generator))
        self.max_tokens = 0
        self.wrong_shape = wrong_shape

    def _head_logits(self, features):
        self.max_tokens = max(self.max_tokens, features.shape[1])
        logits = features @ self.weight
        return logits.squeeze(0) if self.wrong_shape else logits


class PromptLabelsTests(unittest.TestCase):
    def test_languages_unicode_exact_shift_and_assistant_disjoint(self):
        tok = FixtureTokenizer()
        for language in ('ko', 'en'):
            source = pair(language, context='가온🙂 café e\u0301 12; Age? 나이는?', question='Age? 나이는?')
            before = copy.deepcopy(source)
            for view in (0, 1):
                row = method.data.render_view(source, view)
                ids, labels, text = method.data.encode_view(row, tok)
                record = SimpleNamespace(x=ids[:-1], y=labels[1:])
                result = method.prompt_labels(source, view, tok, record)
                self.assertEqual(result['x'], ids[:-1])
                self.assertEqual(result['assistant_y'], labels[1:])
                self.assertEqual(len(result['prompt_y']), len(record.x))
                ranges = result['proof']['ranges']
                offsets = tok.encode(text).offsets
                expected = [ids[i] if any(a <= offsets[i][0] < offsets[i][1] <= b for a, b in ranges.values())
                            else -100 for i in range(1, len(ids))]
                self.assertEqual(result['prompt_y'], expected)
                self.assertTrue(all(p == -100 or a == -100 for p, a in zip(result['prompt_y'], result['assistant_y'])))
                self.assertNotIn(tok.token_to_id('<|im_end|>'), result['prompt_y'])
                self.assertEqual(result['proof']['token_count'], len(source['context']) + len(source['question']))
                self.assertTrue(result['proof']['record_checked'])
            self.assertEqual(source, before)

    def test_question_repeated_inside_context_has_its_own_structural_range(self):
        source = pair(context='Age? First occurrence. Age? Again.', question='Age?')
        result = method.prompt_labels(source, 0, FixtureTokenizer())
        ranges = result['proof']['ranges']
        self.assertGreater(ranges['question'][0], ranges['context'][1])
        self.assertEqual(result['proof']['token_count_by_field']['question'], 4)
        self.assertEqual(result['proof']['token_count_by_field']['context'], len(source['context']))

    def test_sentinel_collision_is_resolved_without_real_text_search(self):
        source = pair(context='\ue000TLM_PROMPT_CONTEXT_0\ue001 is ordinary quoted text. Age?', question='Age?')
        result = method.prompt_labels(source, 1, FixtureTokenizer())
        self.assertGreaterEqual(result['proof']['sentinel_collision_retries'], 1)

    def test_straddling_wrapper_body_boundary_is_dropped_and_counted(self):
        source = pair(context='Mira is twelve.', question='Age?')
        result = method.prompt_labels(source, 0, FixtureTokenizer(straddle='\nM'))
        self.assertEqual(result['proof']['boundary_dropped'], 1)
        self.assertEqual(result['proof']['boundary_dropped_by_field']['context'], 1)
        self.assertNotIn(99999, result['prompt_y'])
        self.assertEqual(result['proof']['token_count'], len(source['context']) + len(source['question']) - 1)

    def test_control_tokens_inside_body_are_not_prompt_targets(self):
        source = pair(context='Mira <|im_end|> <pad> is twelve.', question='Age?')
        result = method.prompt_labels(source, 0, FixtureTokenizer())
        self.assertEqual(result['proof']['special_dropped'], 2)
        for value in FixtureTokenizer.specials.values():
            self.assertNotIn(value, result['prompt_y'])

    def test_evaluation_replay_wrong_assistant_and_record_tampering_refused(self):
        source = pair()
        with self.assertRaises(ValueError):
            method.prompt_labels(source, 2, FixtureTokenizer())
        heldout = copy.deepcopy(source)
        heldout['split'] = 'test'
        with self.assertRaises(ValueError):
            method.prompt_labels(heldout, 0, FixtureTokenizer())
        replay = dict(messages=[], meta=dict(kind='fictional_relation_fields'))
        with self.assertRaises(ValueError):
            method.prompt_labels(replay, 0, FixtureTokenizer())
        row = method.data.render_view(source, 0)
        ids, labels, _ = method.data.encode_view(row, FixtureTokenizer())
        for record in (SimpleNamespace(x=ids[1:], y=labels[1:]),
                       SimpleNamespace(x=ids[:-1], y=[-100] * (len(ids) - 1)),
                       SimpleNamespace(x=[True] + ids[1:-1], y=labels[1:])):
            with self.assertRaises(ValueError):
                method.prompt_labels(source, 0, FixtureTokenizer(), record)
        forged = copy.deepcopy(source)
        forged['views'] = {'0': copy.deepcopy(row)}
        forged['views']['0']['messages'][1]['content'][0]['text'] = 'old wrong answer'
        with self.assertRaises(ValueError):
            method.prompt_labels(forged, 0, FixtureTokenizer())

    def test_bad_offsets_and_context_overflow_refused(self):
        class BadOffsets(FixtureTokenizer):
            def encode(self, text):
                encoded = super().encode(text)
                encoded.offsets[0] = (-1, 0)
                return encoded
        with self.assertRaises(ValueError):
            method.prompt_labels(pair(), 0, BadOffsets())
        with self.assertRaises(ValueError):
            method.prompt_labels(pair(context='x' * 1100), 0, FixtureTokenizer())


class PromptSumsTests(unittest.TestCase):
    def hidden(self):
        return torch.randn(2, 1024, 5, generator=torch.Generator().manual_seed(44), requires_grad=True)

    def labels(self):
        return [[-100, 2, -100, 3, 4], [5, -100, 6, -100, -100, 7]]

    def test_chunk_ce_and_gradients_match_dense_reference(self):
        labels = self.labels()
        for checkpoint in (False, True):
            head, dense_head = ToyHead(), ToyHead()
            hidden = self.hidden()
            dense_hidden = hidden.detach().clone().requires_grad_()
            actual, count = method.prompt_sums(head, hidden, labels, checkpoint_heads=checkpoint, chunk=2)
            targets = torch.full((2, 1024), -100, dtype=torch.long)
            for i, values in enumerate(labels):
                targets[i, :len(values)] = torch.tensor(values)
            logits = dense_head._head_logits(dense_hidden).float()
            expected = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), targets.reshape(-1), reduction='sum')
            self.assertEqual(count, 6)
            self.assertEqual(actual.dtype, torch.float32)
            torch.testing.assert_close(actual, expected, rtol=1e-6, atol=1e-6)
            actual.backward()
            expected.backward()
            torch.testing.assert_close(hidden.grad, dense_hidden.grad, rtol=1e-6, atol=1e-6)
            torch.testing.assert_close(head.weight.grad, dense_head.weight.grad, rtol=1e-6, atol=1e-6)
            self.assertLessEqual(head.max_tokens, 2)
            self.assertEqual(float(hidden.grad[:, 6:].abs().sum()), 0.)

    def test_zero_beta_preserves_existing_gradient_exactly(self):
        head = ToyHead()
        hidden = self.hidden()
        answer_loss = hidden.square().sum() + head.weight.square().sum()
        baseline = torch.autograd.grad(answer_loss, (hidden, head.weight), retain_graph=True)
        total, n = method.prompt_sums(head, hidden, self.labels(), chunk=2)
        mixed = torch.autograd.grad(answer_loss + method.prompt_update_loss(total, n, 0.), (hidden, head.weight))
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(baseline, mixed)))

    def test_whole_update_denominator_and_replay_zero_mass(self):
        first = torch.tensor(12., requires_grad=True)
        second = torch.tensor(6., requires_grad=True)
        whole = method.prompt_update_loss(first, 9, .1) + method.prompt_update_loss(second, 9, .1)
        torch.testing.assert_close(whole, .1 * (first + second) / 9)
        hidden, head = self.hidden(), ToyHead()
        total, n = method.prompt_sums(head, hidden, [[-100] * 5, [-100] * 7], chunk=2)
        self.assertEqual((float(total.detach()), n, head.max_tokens), (0., 0, 0))
        self.assertEqual(float(method.prompt_update_loss(total, 0, .1).detach()), 0.)
        total.backward()
        self.assertEqual(float(hidden.grad.abs().sum()), 0.)

    def test_empty_bfloat16_auxiliary_sum_remains_fp32(self):
        hidden = self.hidden().detach().to(torch.bfloat16).requires_grad_()
        total, count = method.prompt_sums(ToyHead(), hidden, [[-100], [-100]])
        self.assertEqual((total.dtype, count), (torch.float32, 0))
        total.backward()
        self.assertEqual(float(hidden.grad.abs().sum()), 0.)

    def test_shape_real_length_target_and_head_shape_pollution_refused(self):
        hidden, labels = self.hidden(), self.labels()
        for bad_hidden in (hidden[:, :20], hidden[0], hidden.long()):
            with self.assertRaises(ValueError):
                method.prompt_sums(ToyHead(), bad_hidden, labels)
        for bad_labels in (labels[:1], [[], labels[1]], [[0] * 1025, labels[1]],
                           [[-1], labels[1]], [[1.], labels[1]], [[True], labels[1]],
                           [[11], labels[1]]):
            with self.assertRaises(ValueError):
                method.prompt_sums(ToyHead(), hidden, bad_labels)
        with self.assertRaises(ValueError):
            method.prompt_sums(ToyHead(wrong_shape=True), hidden, labels)
        for chunk in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                method.prompt_sums(ToyHead(), hidden, labels, chunk=chunk)

    def test_scalar_whole_update_count_and_registered_beta_refused_when_invalid(self):
        for value, n, beta in ((torch.tensor(1.), 0, 0.), (torch.tensor(1.), -1, .1),
                (torch.tensor(1.), True, .1), (torch.tensor(1.), 1., .1),
                (torch.tensor([1.]), 1, .1), (torch.tensor(-1.), 1, .1),
                (torch.tensor(float('nan')), 1, .1), (torch.tensor(1.), 1, .05),
                (torch.tensor(1.), 1, True)):
            with self.assertRaises(ValueError):
                method.prompt_update_loss(value, n, beta)


if __name__ == '__main__':
    unittest.main()
