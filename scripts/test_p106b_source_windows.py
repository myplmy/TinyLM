#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import copy
import unittest
from unittest.mock import patch
from tokenizers import Tokenizer
from scripts import p106b_source_windows as f
from scripts import p106b_public_qa_roles as roles
from scripts.test_p106b_public_qa_roles import fixture
from scripts import diag_p106b_original_qa3_course as course
from tinylm.chat.serialize import serialize


class Windows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok = Tokenizer.from_file(str(course.training.data.TOKENIZER))

    def example(self):
        row, _ = roles.wrap(fixture()); row['meta']['semantic_root_id'] = 'fixture_root'
        counter = [0]
        def emit(messages):
            counter[0] += 1
            n = len(self.tok.encode(serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)).ids)
            return 'WRONG' + str(counter[0]), dict(finish_reason='STOP', prompt_tokens=n)
        events = f.original.collect(row, emit)
        return row, [x for x in events if x['history'] == 'ACTUAL_MODEL']

    def test_actual_producer_reference_and_full_prompt_reconstruction(self):
        row, events = self.example(); before = copy.deepcopy((row, events))
        for event in events:
            case = f.make_case(row, event, 'parent', self.tok)
            full = next(x for x in case['variants'] if x['mode'] == 'FULL')
            self.assertEqual(full['messages'], event['messages'])
            self.assertEqual(full['prompt_tokens'], event['generation']['prompt_tokens'])
            self.assertTrue(case['diagnostic_only']); self.assertFalse(case['train_ready'])
        self.assertEqual((row, events), before)

    def test_all_variants_keep_real_wrong_history_and_questions(self):
        row, events = self.example(); event = events[2]
        case = f.make_case(row, event, 'parent', self.tok)
        for variant in case['variants']:
            if variant['eligible']:
                self.assertEqual(variant['messages'][1:], event['messages'][1:])
                self.assertEqual(f.original.text(variant['messages'][1]), 'WRONG1')
                self.assertEqual(f.original.text(variant['messages'][3]), 'WRONG2')

    def test_query_and_random_are_independent_of_current_gold(self):
        source = ('Nora is red. Felix is blue. ' * 50)
        args = (source, ['Who is red?', 'Who is blue?'], 'root', 2)
        a, _ = f.selection(*args, 'Nora', self.tok)
        b, _ = f.selection(*args, 'unavailable_target', self.tok)
        self.assertEqual(a['QUERY'], b['QUERY']); self.assertEqual(a['RANDOM'], b['RANDOM'])
        self.assertTrue(a['GOLD_LITERAL']['eligible']); self.assertFalse(b['GOLD_LITERAL']['eligible'])

    def test_query_uses_only_user_questions_not_actual_or_gold_answers(self):
        row, events = self.example(); captured = []; original = f.query_scores
        def capture(chunks, questions):
            captured.extend(questions); return original(chunks, questions)
        with patch.object(f, 'query_scores', side_effect=capture):
            f.make_case(row, events[2], 'parent', self.tok)
        self.assertEqual(len(captured), 3)
        self.assertFalse(any('WRONG' in q for q in captured))
        self.assertEqual(captured[-1], f.original.text(row['messages'][4]))

    def test_unicode_chunks_are_exact_source_slices(self):
        source = ('서울 Nora는 2013년에 87세였다. 🚀\n' * 30)
        chunks = f.windows(source, self.tok, width=16, stride=8)
        self.assertGreater(len(chunks), 1)
        for w in chunks:
            a, b = w['char_range']; self.assertEqual(w['text'], source[a:b])
            self.assertEqual(w['actual_window_tokens'], len(self.tok.encode(w['text']).ids))

    def test_fixed_random_seed_and_no_endpoint_argument(self):
        source = 'red blue black white ' * 100
        a, _ = f.selection(source, ['white?'], 'r1', 1, 'white', self.tok)
        b, _ = f.selection(source, ['white?'], 'r1', 1, 'other', self.tok)
        self.assertEqual(a['RANDOM'], b['RANDOM'])

    def test_wrong_reference_length_fails_without_guessing(self):
        row, events = self.example(); row['meta']['original_reference_range'][1] += 1
        with self.assertRaisesRegex(ValueError, 'reference length'):
            f.make_case(row, events[0], 'parent', self.tok)

    def test_current_question_and_target_mutations_rejected(self):
        row, events = self.example(); e = copy.deepcopy(events[1])
        e['messages'][-1]['content'][0]['text'] += ' changed'
        with self.assertRaisesRegex(ValueError, 'questions changed'):
            f.make_case(row, e, 'parent', self.tok)
        e = copy.deepcopy(events[1]); e['gold'] = 'untrusted'
        with self.assertRaisesRegex(ValueError, 'target changed'):
            f.make_case(row, e, 'parent', self.tok)

    def test_remove_reference_is_not_remove_actual_history(self):
        row, events = self.example(); case = f.make_case(row, events[2], 'parent', self.tok)
        item = next(v for v in case['variants'] if v['mode'] == 'REMOVE_REFERENCE')
        self.assertEqual(item['selected_char_range'], [0, 0])
        self.assertIn('WRONG1', str(item['messages'])); self.assertIn('Question:', f.original.text(item['messages'][0]))

    def test_missing_gold_window_is_explicit_not_fake_generation(self):
        source = 'one two three'
        result, _ = f.selection(source, ['what?'], 'r', 1, 'not_in_source', self.tok)
        self.assertEqual(result['GOLD_LITERAL'], dict(eligible=False, reason='NO_LITERAL_CONTAINING_WINDOW'))

    def test_cosine_zero_and_deterministic_tie(self):
        values = f.query_scores([dict(text='abc'), dict(text='abc')], ['abc'])
        self.assertEqual(values, [1., 1.])
        self.assertEqual(f.query_scores([dict(text='a')], ['?']), [0.])

    def event(self, root, turn, mode, answer, gold='x'):
        generation = dict(finish_reason='STOP')
        return dict(endpoint='parent', root=root, language='en', turn=turn, mode=mode, status='GENERATED',
            answer=answer, gold=gold, generation=generation, scores=f.score(answer, gold, generation))

    def test_recount_rejects_duplicates_and_changed_scores(self):
        e = self.event('r', 1, 'FULL', 'x')
        self.assertEqual(f.recount([e])['parent/FULL/all']['literal'], 1)
        with self.assertRaisesRegex(ValueError, 'duplicate'): f.recount([e, e])
        bad = copy.deepcopy(e); bad['scores']['literal'] = 0
        with self.assertRaisesRegex(ValueError, 'score mismatch'): f.recount([bad])

    def test_root_pair_is_case_weighted_not_mean_of_root_means(self):
        full = [self.event('a', i, 'FULL', 'wrong') for i in (1, 2, 3)] + [self.event('b', 1, 'FULL', 'x')]
        other = [self.event('a', i, 'QUERY', 'x') for i in (1, 2, 3)] + [self.event('b', 1, 'QUERY', 'wrong')]
        r = f.paired(full, other, draws=20)
        self.assertEqual(r['metrics']['literal']['variant_minus_full'], .5)
        self.assertEqual(r['cases'], 4); self.assertEqual(r['roots'], 2)

    def test_gold_subset_uses_the_same_full_cases(self):
        full = [self.event('a', 1, 'FULL', 'wrong'), self.event('b', 1, 'FULL', 'x')]
        r = f.paired(full, [self.event('a', 1, 'GOLD_LITERAL', 'x')], draws=10)
        self.assertEqual(r['cases'], 1); self.assertEqual(r['full_correct_on_same_cases'], 0)
        self.assertEqual(r['metrics']['literal']['variant_minus_full'], 1.)


if __name__ == '__main__': unittest.main()
