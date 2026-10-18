#!/usr/bin/env python3
"""CPU-only relation labels/splits/encoder tests; no learned model/weights."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import copy
from types import SimpleNamespace
import unittest
from scripts import p106b_relation_bind_data as d


class CharTokenizer:
    """Small deterministic tokenizer fixture, not an actual LM/tokenizer asset."""
    def __init__(self, straddle=False): self.straddle = straddle
    def token_to_id(self, name): return {'<|im_start|>': 3, '<|im_end|>': 4, '<pad>': 0}.get(name)
    def encode(self, text):
        ids = []; offsets = []; i = 0
        boundary = text.find('<|im_start|>assistant\n') + len('<|im_start|>assistant')
        while i < len(text):
            found = next((s for s in ('<|im_start|>', '<|im_end|>') if text.startswith(s, i)), None)
            if found:
                ids.append(self.token_to_id(found)); offsets.append((i, i + len(found))); i += len(found)
            elif self.straddle and i == boundary and i + 1 < len(text):
                ids.append(999); offsets.append((i, i + 2)); i += 2
            else:
                ids.append(1000 + ord(text[i])); offsets.append((i, i + 1)); i += 1
        return SimpleNamespace(ids=ids, offsets=offsets)


class RelationDataTests(unittest.TestCase):
    def setUp(self):
        self.rows = d.generate(dict(train=32, dev=16, test=16))
        self.b = self.rows['train'][0]

    def test_deterministic_balanced_distinct_graphs(self):
        self.assertEqual(self.rows, d.generate(dict(train=32, dev=16, test=16)))
        self.assertTrue(d.validate_splits(self.rows))
        for split, bundles in self.rows.items():
            self.assertEqual(len(bundles), dict(train=32, dev=16, test=16)[split])
            self.assertEqual(len({b['bundle_id'] for b in bundles}), len(bundles))

    def test_translations_share_graph_and_partition(self):
        owners = {}
        for split, bundles in self.rows.items():
            for b in bundles:
                self.assertEqual(b['split'], split)
                owners.setdefault(b['group_id'], []).append((split, b['language']))
        self.assertTrue(all(len(v) == 2 and {x[1] for x in v} == {'ko', 'en'}
                            and len({x[0] for x in v}) == 1 for v in owners.values()))

    def test_code_answers_and_both_cross_negatives(self):
        for bundles in self.rows.values():
            for b in bundles:
                table = {(s, r): a for s, r, a in b['facts']}
                names = d.NAMES[b['language']]
                for qi, relation in enumerate(b['query_order']):
                    self.assertEqual(b['answers'][qi], names[table[b['subject'], relation]])
                    self.assertNotEqual(b['answers'][1 - qi], names[table[b['subject'], relation]])

    def test_recomputed_digest_cannot_certify_arbitrary_wrong_answer(self):
        b = copy.deepcopy(self.b)
        b['answers'][0] = 'invented wrong answer'
        b['bundle_sha256'] = d.sha({k: v for k, v in b.items() if k != 'bundle_sha256'})
        with self.assertRaises(ValueError): d.validate_bundle(b)

    def test_forged_natural_negative_flag_rejected(self):
        b = copy.deepcopy(self.b); b['label_status'] = 'GPT_VERIFIED_NATURAL'
        with self.assertRaises(ValueError): d.validate_bundle(b)

    def test_duplicate_entity_slots_refused(self):
        with self.assertRaises(ValueError): d.build_bundle('kinship', [0, 1, 2, 2, 4, 5], 'ko')

    def test_eval_view_not_train(self):
        with self.assertRaises(ValueError): d.render(self.b, 0, view=1)
        with self.assertRaises(ValueError): d.render(self.b, 1, view=2)

    def test_eval_fact_reversal_and_question_paraphrase_keep_gold(self):
        b = self.rows['test'][0]
        from scripts.p106b_night_qa_data import text
        for qi in (0, 1):
            original = d.render(b, qi)
            for view in (1, 2):
                row = d.render(b, qi, view=view)
                self.assertEqual(text(original['messages'][1]), text(row['messages'][1]))
                self.assertNotEqual(text(original['messages'][0]), text(row['messages'][0]))

    def test_no_oracle_meta_in_prompt(self):
        from tinylm.chat.serialize import serialize
        row = d.render(self.b, 0)
        before = serialize(row, 'chatml')
        row['meta']['candidate_index'] = 999
        row['meta']['negative_reason'] = 'SECRET_ORACLE_SENTINEL'
        self.assertEqual(serialize(row, 'chatml'), before)
        self.assertNotIn('SECRET_ORACLE_SENTINEL', before)

    def test_only_cross_candidate_not_positive(self):
        for qi in (0, 1):
            self.assertTrue(d.render(self.b, qi)['meta']['positive_example'])
            self.assertFalse(d.render(self.b, qi, 1 - qi)['meta']['positive_example'])

    def test_conservative_metric_does_not_erase_meaning(self):
        self.assertNotEqual(d.exact_answer('A'), d.exact_answer('a'))
        self.assertNotEqual(d.exact_answer('-5'), d.exact_answer('5'))
        self.assertNotEqual(d.exact_answer('1.5'), d.exact_answer('15'))
        self.assertEqual(d.exact_answer(' 민수\n'), '민수')

    def test_simple_shortcuts_only_half_questions(self):
        counts = d.shortcut_counts(self.rows['train'])['counts']
        self.assertEqual(counts['questions'], 64)
        for name in ('first_of_two_role_candidates', 'alphabetically_first_candidate', 'repeat_answer0'):
            self.assertEqual(counts[name], 32)

    def test_invalid_size_does_not_repeat_to_fill(self):
        with self.assertRaises(ValueError): d.generate(dict(train=7, dev=8, test=8))

    def test_eligibility_filters_before_quota_and_keeps_both_translations(self):
        rows = d.generate(dict(train=8, dev=8, test=8), eligible=lambda b: b['slots'][2] % 2 == 0)
        self.assertTrue(d.validate_splits(rows))
        self.assertTrue(all(b['slots'][2] % 2 == 0 for values in rows.values() for b in values))
        self.assertEqual({s: len(v) for s, v in rows.items()}, dict(train=8, dev=8, test=8))

    def test_rendered_meaning_has_independent_fixed_role_answers(self):
        # This literal fixture does not ask the factory for the expected answer.
        fixed = {'kinship': ('아버지', '스승', 'father', 'mentor'),
                 'work': ('상사', '보조 담당자', 'manager', 'assistant'),
                 'project': ('설계 담당자', '검토 담당자', 'designer', 'reviewer'),
                 'event': ('안내 담당자', '진행 담당자', 'guide', 'coordinator')}
        from scripts.p106b_night_qa_data import text
        for family, roles in fixed.items():
            for language, subject, expected in (('ko', '민수', ('지훈', '수진')),
                                                 ('en', 'Alice', ('Clara', 'David'))):
                b = d.build_bundle(family, [0, 1, 2, 3, 4, 5], language)
                for qi, relation in enumerate(b['query_order']):
                    row = d.render(b, qi)
                    prompt = text(row['messages'][0]); question = prompt.split('질문: ' if language == 'ko' else 'Question: ')[1]
                    role = roles[relation if language == 'ko' else 2 + relation]
                    self.assertIn(subject, question); self.assertIn(role, question)
                    self.assertEqual(text(row['messages'][1]), expected[relation])
                    self.assertNotEqual(text(d.render(b, qi, 1 - qi)['messages'][1]), expected[relation])

    def test_complete_content_and_answer_free_prefix(self):
        pos, crossed = d.encode_bundle(self.b, CharTokenizer())
        for p, c in zip(pos, crossed):
            first = next(i for i, y in enumerate(p.y) if y != -100)
            self.assertEqual(p.x[:first + 1], c.x[:first + 1])
            self.assertEqual([v for v in p.y if v != -100][-1], 4)

    def test_header_answer_token_straddle_is_rejected(self):
        with self.assertRaises(ValueError): d.encode_bundle(self.b, CharTokenizer(straddle=True))


if __name__ == '__main__': unittest.main(verbosity=2)
