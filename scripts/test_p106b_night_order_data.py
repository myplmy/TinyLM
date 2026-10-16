"""합성 producer 회귀만 수행하며 실제 원형·모델·GPU를 열지 않는다."""
from pathlib import Path
import sys
import unittest
import copy
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_order_data as d


def pair(language='ko'):
    context, question, answer = ('A는 빨강입니다.', 'A는 무엇입니까?', '빨강') if language == 'ko' else ('A is red.', 'What is A?', 'red')
    return dict(split='train', language=language, root='root', context=context, question=question,
        answers=[dict(text=answer, answer_start=context.index(answer))],
        views={'1':dict(messages=[dict(role='user', content=d.original._user(context, question, language, 1)),
            dict(role='assistant', content=answer)], meta=dict(kind='test', semantic_root_id='root'))})


class OrderTests(unittest.TestCase):
    def test_korean_only_field_order_changes_and_input_not_mutated(self):
        p = pair(); before = copy.deepcopy(p); row = d.render(p)
        self.assertEqual(p, before)
        a, b = d.original.text(p['views']['1']['messages'][0]), d.original.text(row['messages'][0])
        self.assertEqual(Counter(a), Counter(b)); self.assertNotEqual(a, b)
        self.assertLess(b.index(p['question']), b.index(p['context']))
        self.assertEqual(d.original.text(row['messages'][1]), '빨강'); self.assertEqual(row['meta']['wrapper_view'], 3)

    def test_english_uses_same_instruction_and_not_old_held_template(self):
        p = pair('en'); row = d.render(p); text = d.original.text(row['messages'][0])
        self.assertTrue(text.startswith('Answer the question using only the passage below.\nQuestion:'))
        self.assertNotEqual(text, d.original._user(p['context'], p['question'], 'en', 2))
        self.assertFalse(row['meta']['held_wrapper2_training'])

    def test_old_wrapper2_training_remains_forbidden(self):
        with self.assertRaises(ValueError): d.original.render_view(pair(), 2)

    def test_dev_test_unknown_language_never_transformed(self):
        for change in (dict(split='dev'), dict(split='test'), dict(language='other')):
            with self.assertRaises(ValueError): d.render(dict(pair(), **change))

    def test_mismatched_original_or_answer_cannot_be_packed(self):
        p = pair(); p['views']['1']['messages'][0]['content'] = 'different'
        with self.assertRaises(ValueError): d.render(p)

    def test_actual_canonical_text_blocks_not_only_string_fixtures(self):
        from tinylm.chat.canonical import normalize, validate
        p = pair(); p['views']['1'] = validate(normalize(p['views']['1']))
        self.assertIsInstance(p['views']['1']['messages'][0]['content'], list)
        result = d.render(p)
        self.assertIn('질문:\nA는 무엇입니까?\n지문:\nA는 빨강입니다.', d.original.text(result['messages'][0]))
        p = pair(); p['views']['1']['messages'][1]['content'] = 'blue'
        with self.assertRaises(ValueError): d.render(p)

    def test_real_encoder_shift_pairing_schedule_and_replay_are_preserved(self):
        from scripts.test_p106b_night_prompt_loss import FixtureTokenizer
        from tinylm.chat.canonical import normalize, validate
        from tinylm.train.mtp_sft import encode_record
        tok = FixtureTokenizer(); quarters = []; old_courses = []
        for q in range(4):
            values = []; natural = []
            for i in range(4):
                p = pair('ko' if i < 2 else 'en'); p['root'] = str((q, i))
                p['views']['0'] = copy.deepcopy(p['views']['1'])
                p['views']['0']['messages'][0]['content'] = d.original._user(p['context'], p['question'], p['language'], 0)
                for view in ('0', '1'):
                    p['views'][view] = validate(normalize(p['views'][view]))
                values.append(p); natural.append([encode_record(p['views'][str(v)], tok) for v in (0, 1)])
            replay = [copy.deepcopy(natural[0][0]) for _ in range(120)]
            quarters.append(values); old_courses.append((natural, replay))
        new, proofs, total, schedules = d.transform(quarters, old_courses, tok)
        self.assertEqual(len(proofs), 16); self.assertEqual(total['rows'], 512)
        self.assertEqual([s['updates'] for s in schedules], [1] * 4)
        for q in range(4):
            self.assertIs(new[q][1], old_courses[q][1])
            for i in range(4):
                self.assertIs(new[q][0][i][0], old_courses[q][0][i][0])
                self.assertEqual([y for y in new[q][0][i][1].y if y != -100],
                                 [y for y in old_courses[q][0][i][1].y if y != -100])


if __name__ == '__main__': unittest.main()
