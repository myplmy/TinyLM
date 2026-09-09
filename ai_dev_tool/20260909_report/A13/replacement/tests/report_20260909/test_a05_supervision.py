import unittest
import torch
import torch.nn.functional as F
from tinylm.chat.serialize import serialize, loss_spans
from tinylm.chat.supervision import encode_sample, collate_samples, masked_ce_sum
from tinylm.eval.sft_grading import grade_response
from support_report import CharacterTokenizer


def conversation(body="답"):
    return {"messages": [{"role": "user", "content": "질문"},
                         {"role": "assistant", "content": body}],
            "meta": {"id": "toy", "split": "train"}}


class SupervisionTests(unittest.TestCase):
    def test_prompt_mask_answer_and_end_marker(self):
        raw, tok = conversation(), CharacterTokenizer()
        s = encode_sample(raw, tok, kind="plain", max_length=100)
        start = s.text.index("답")
        self.assertTrue(all(y == -100 for y in s.labels[:start]))
        self.assertTrue(all(y != -100 for y in s.labels[start:]))
        x, y = collate_samples([s])
        self.assertEqual(x.shape, y.shape)
        self.assertEqual(int((y != -100).sum()), s.loss_tokens)

    def test_empty_and_overflow_fail(self):
        with self.assertRaises(ValueError):
            encode_sample(conversation(""), CharacterTokenizer())
        with self.assertRaises(ValueError):
            encode_sample(conversation("긴 답"), CharacterTokenizer(), max_length=3)

    def test_multi_turn_thinking_mask_and_serialization(self):
        raw = conversation()
        raw["messages"][-1]["content"] = [{"type": "thinking", "text": "생각"},
                                         {"type": "text", "text": "결론"}]
        raw["messages"].extend([{"role": "user", "content": "후속 질문"},
                                {"role": "assistant", "content": "두 번째 답"}])
        for kind in ("chatml", "gemma", "plain", "minimal"):
            text = serialize(raw, kind)
            spans = loss_spans(raw, kind, train_thinking=False)
            visible = "".join(text[a:b] for a, b in spans)
            self.assertIn("결론", visible)
            self.assertNotIn("생각", visible)
            self.assertIn("두 번째 답", visible)
            self.assertNotIn("후속 질문", visible)
            self.assertEqual(text, encode_sample(raw, CharacterTokenizer(), kind=kind,
                                                 train_thinking=False).text)


    def test_token_crossing_assistant_boundary_is_masked(self):
        class BoundaryTokenizer(CharacterTokenizer):
            def encode(self, text, add_special_tokens=False):
                encoded = super().encode(text, add_special_tokens=add_special_tokens)
                first_answer = text.index("답")
                # 역할 접두사의 마지막 문자와 답의 첫 문자를 단일 BPE token처럼 묶는다.
                encoded.ids[first_answer - 1:first_answer + 1] = [7]
                encoded.offsets[first_answer - 1:first_answer + 1] = [(first_answer - 1, first_answer + 1)]
                return encoded
        sample = encode_sample(conversation(), BoundaryTokenizer(), kind="plain", max_length=100)
        boundary_index = sample.text.index("답") - 1
        self.assertEqual(sample.boundary_tokens_masked, 1)
        self.assertEqual(sample.labels[boundary_index], -100)
        self.assertGreater(sample.loss_tokens, 0)  # 종료 marker 손실은 남는다.

    def test_padding_not_loss(self):
        samples = [encode_sample(conversation(body), CharacterTokenizer(), kind="plain")
                   for body in ("답", "긴 답변")]
        _, y = collate_samples(samples)
        self.assertEqual(int((y != -100).sum()), sum(s.loss_tokens for s in samples))
        self.assertTrue(bool((y[0, len(samples[0].input_ids)-1:] == -100).all()))

    def test_variable_loss_count_microbatch_gradient(self):
        torch.manual_seed(1)
        logits = torch.randn(2, 3, 5, requires_grad=True)
        labels = torch.tensor([[1, 2, 3], [4, -100, -100]])
        reference = F.cross_entropy(logits.reshape(-1, 5), labels.reshape(-1), ignore_index=-100)
        reference.backward()
        expected = logits.grad.detach().clone()
        variant = logits.detach().clone().requires_grad_()
        denominator = int((labels != -100).sum())
        for i in range(2):
            loss, _ = masked_ce_sum(variant[i:i+1], labels[i:i+1], chunk=2)
            (loss / denominator).backward()
        self.assertTrue(torch.allclose(expected, variant.grad, atol=1e-7, rtol=1e-6))

    def test_exact_contract_does_not_silently_strip_korean_suffix(self):
        raw = {"meta": {"grading": {"scoring_mode": "normalized_exact",
               "accepted_answers": ["미리내통"], "ranking_eligible": True}}}
        self.assertEqual(grade_response(raw, "미리내통")["correct"], 1)
        self.assertEqual(grade_response(raw, "미리내통이다.")["correct"], 0)

    def test_diagnostic_and_unimplemented_constraints(self):
        raw = {"meta": {"grading": {"scoring_mode": "diagnostic_required_elements",
               "required_elements": ["답"], "ranking_eligible": True}}}
        self.assertFalse(grade_response(raw, "답")["ranking_eligible"])
        raw["meta"]["grading"].update(scoring_mode="required_elements_and_format",
                                      format_constraints={"unknown": 1})
        self.assertEqual(grade_response(raw, "답")["status"], "unscored")
