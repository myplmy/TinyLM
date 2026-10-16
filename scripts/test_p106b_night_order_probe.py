"""합성 원형과 원답만 사용하는 순서 진단 회귀."""
from __future__ import annotations

from collections import Counter
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_order_probe as p
from scripts import p106b_night_order_data as old


def pair(language='ko', index=0):
    if language == 'ko':
        context, question, answer = '별이는 파란색 공을 골랐습니다.\n끝\n', '별이는 무슨 색 공을 골랐나요?\n', '파란색'
    else:
        context, question, answer = 'Ari selected a blue ball.\nEnd\n', 'What color did Ari select?\n', 'blue'
    value = dict(root=p.original.sha([language, index]), language=language, split='test',
        article_id=p.original.sha(['article', language, index]), article_title='제목 ' + str(index),
        context_id=p.original.sha(['context', language, index]), qa_id='qa' + str(index),
        source_path='synthetic/' + language + '.json', source_sha256=p.original.sha(['source', language]),
        context=context, question=question, answers=[dict(text=answer, answer_start=context.index(answer))], aliases=[answer])
    value['views'] = {str(view): p.original.render_view(value, view) for view in (0, 1, 2)}
    return value


def panel():
    return [pair(language, i) for i in range(32) for language in ('ko', 'en')]


def generation(value, view, answer, reason='EOS', count=4, prompt_tokens=40):
    prompt = p.serialize(dict(messages=p.messages(value, view)), 'chatml', add_generation_prompt=True)
    return dict(finish_reason=reason, generated_tokens=count, prompt_tokens=prompt_tokens,
        requested_max_new=128, max_new=128, actual_prompt_sha256=p.original.sha(prompt),
        raw_answer_sha256=p.original.sha(answer))


def events_for(rows):
    return [p.make_event(value, i, view, value['aliases'][0], generation(value, view, value['aliases'][0]))
        for i, value in enumerate(rows) for view in (1, 3)]


class OrderProbeTests(unittest.TestCase):
    def test_korean_same_instruction_all_characters_and_source_unchanged(self):
        value = pair(); before = copy.deepcopy(value)
        left, right = p.messages(value, 1), p.messages(value, 3)
        a, b = p.original.text(left[0]), p.original.text(right[0])
        self.assertEqual(left, value['views']['1']['messages'][:1])
        self.assertEqual(Counter(a), Counter(b)); self.assertNotEqual(a, b)
        self.assertEqual(b, '다음 지문에 근거해 질문에 대한 답만 쓰세요.\n질문:\n' + value['question'] + '\n지문:\n' + value['context'])
        self.assertEqual(value, before); self.assertEqual(value['split'], 'test')
        right[0]['content'][0]['text'] = '반환값 변경'
        self.assertEqual(value, before)

    def test_english_same_passage_instruction_not_old_view2(self):
        value = pair('en'); message = p.original.text(p.messages(value, 3)[0])
        self.assertEqual(message, 'Answer the question using only the passage below.\nQuestion:\n' + value['question'] + '\nPassage:\n' + value['context'])
        self.assertNotEqual(message, p.original._user(value['context'], value['question'], 'en', 2))
        self.assertEqual(Counter(message), Counter(p.original.text(p.messages(value, 1)[0])))

    def test_unicode_repeated_question_and_label_in_context_are_not_parsed_by_find(self):
        for language in ('ko', 'en'):
            value = pair(language)
            value['context'] = value['question'] + '\nQuestion:\nPassage:\n질문:\n지문:\n🙂 e\u0301\n' + value['context']
            value['answers'][0]['answer_start'] = value['context'].index(value['aliases'][0])
            value['views'] = {str(v): p.original.render_view(value, v) for v in (0, 1, 2)}
            after = p.original.text(p.messages(value, 3)[0])
            self.assertTrue(after.endswith(value['context']))
            self.assertEqual(Counter(after), Counter(p.original.text(p.messages(value, 1)[0])))

    def test_sentinel_collision_keeps_original_characters(self):
        value = pair(); value['question'] += '\x00P106B_PROBE_CONTEXT\x00\x00P106B_PROBE_QUESTION\x00'
        value['views'] = {str(v): p.original.render_view(value, v) for v in (0, 1, 2)}
        after = p.original.text(p.messages(value, 3)[0])
        self.assertIn(value['question'], after)
        self.assertEqual(Counter(after), Counter(p.original.text(p.messages(value, 1)[0])))

    def test_original_training_transform_stays_forbidden_for_test(self):
        value = pair(); before = copy.deepcopy(value)
        with self.assertRaises(ValueError): old.render(value)
        p.messages(value, 3)
        self.assertEqual(value, before)
        training = copy.deepcopy(value); training['split'] = 'train'
        with self.assertRaises(ValueError): p.messages(training, 3)

    def test_only_views1_and3_no_bool_or_heldout_view(self):
        for view in (0, 2, 4, '1', '3', True, None):
            with self.subTest(view=view), self.assertRaises(ValueError): p.messages(pair(), view)

    def test_changed_instruction_question_gold_or_metadata_rejected(self):
        value = pair()
        variants = []
        for field, replacement in (('question', '의역된 질문'), ('context', '다른 문맥'), ('aliases', ['다른 답']), ('source_sha256', 'BAD')):
            broken = copy.deepcopy(value); broken[field] = replacement; variants.append(broken)
        broken = copy.deepcopy(value); broken['views']['1']['messages'][0]['content'][0]['text'] += ' 새 지시'; variants.append(broken)
        broken = copy.deepcopy(value); broken['views']['1']['messages'][1]['content'][0]['text'] = '다른 정답'; variants.append(broken)
        broken = copy.deepcopy(value); broken['views']['1']['meta']['split'] = 'train'; variants.append(broken)
        broken = copy.deepcopy(value); broken['answers'][0]['answer_start'] += 1; variants.append(broken)
        for broken in variants:
            with self.assertRaises(ValueError): p.messages(broken, 3)

    def test_source_proof_exact64_balance_order_full_pair_dict(self):
        rows = panel(); before = copy.deepcopy(rows); proof = p.source_proof(rows)
        self.assertEqual(proof['roots'], 64); self.assertEqual(proof['views'], [1, 3])
        self.assertEqual(proof['source_panel_sha256'], p.original.sha(rows))
        self.assertEqual([case['row_index'] for case in proof['cases']], list(range(64)))
        self.assertEqual([case['root'] for case in proof['cases']], [row['root'] for row in rows])
        self.assertEqual(proof['cases'][0]['case_source_sha256'], p.original.sha(rows[0]))
        self.assertFalse(proof['source_selection_performed']); self.assertFalse(proof['legacy_order640_gate_credited'])
        self.assertEqual(rows, before)

    def test_incomplete_unbalanced_duplicate_or_output_contaminated_source_rejected(self):
        rows = panel(); bad = [rows[:-1], rows + [rows[0]], [pair('ko', i) for i in range(64)]]
        dup = copy.deepcopy(rows); dup[1] = copy.deepcopy(dup[0]); bad.append(dup)
        for key in p.FORBIDDEN_SOURCE_FIELDS:
            value = copy.deepcopy(rows); value[0][key] = '금지된 모형 출력'; bad.append(value)
        for value in bad:
            with self.assertRaises(ValueError): p.source_proof(value)

    def test_make_event_binds_actual_hashes_and_does_not_mutate_inputs(self):
        value = pair(); answer = '  파란색\n'; meta = generation(value, 3, answer)
        before = copy.deepcopy((value, meta)); event = p.make_event(value, 0, 3, answer, meta)
        self.assertEqual((value, meta), before)
        self.assertEqual(event['case_source_sha256'], p.original.sha(value))
        self.assertEqual(event['scores'], dict(em=1., f1=1., raw_exact=0.))
        self.assertEqual(event['messages'], p.messages(value, 3)); self.assertEqual(event['answer'], answer)
        self.assertEqual(event['generation']['raw_answer_sha256'], p.original.sha(answer))

    def test_alias_metric_keeps_numeric_sign_and_decimal_without_new_truth_rule(self):
        value = pair('en'); value['context'] = 'The recorded value is -3.5.'
        value['question'] = 'What value is recorded?'
        value['answers'] = [dict(text='-3.5', answer_start=value['context'].index('-3.5'))]
        value['aliases'] = ['-3.5']
        value['views'] = {str(view): p.original.render_view(value, view) for view in (0, 1, 2)}
        event = p.make_event(value, 0, 1, '3.5', generation(value, 1, '3.5'))
        self.assertEqual(event['scores']['em'], 0.); self.assertEqual(event['scores']['raw_exact'], 0.)
        self.assertEqual(event['scores'], p.qa_scores('3.5', ['-3.5'], 'en'))

    def test_complete_summary_bilingual_views_scoped_metrics(self):
        rows = panel(); events = events_for(rows); before = copy.deepcopy((events, rows))
        report = p.summarize(events, rows)
        self.assertEqual(report['roots'], 64); self.assertEqual(report['cases'], 128)
        self.assertEqual(report['views'], [1, 3]); self.assertEqual(report['overall']['paired']['both_correct'], 64)
        for language in ('ko', 'en'):
            group = report['by_language'][language]; self.assertEqual(group['roots'], 32)
            for view in ('1', '3'):
                self.assertEqual(group['by_view'][view]['n'], 32); self.assertEqual(group['by_view'][view]['em'], 1.)
                self.assertEqual(group['by_view'][view]['f1'], 1.); self.assertEqual(group['by_view'][view]['stop'], 32)
        self.assertFalse(report['world_truth_certified']); self.assertFalse(report['model_probabilities_computed'])
        self.assertFalse(report['legacy_order640_gate_credited']); self.assertFalse(report['training_performed'])
        self.assertEqual((events, rows), before)
        self.assertEqual(p.summarize(list(reversed(events)), rows), report)

    def test_transition_same_wrong_and_empty_separated(self):
        rows = panel(); events = events_for(rows)
        replacements = {(0, 3): '잘못된 답', (1, 1): 'wrong', (2, 1): '오답', (2, 3): ' 오답 ',
            (3, 1): '', (3, 3): ''}
        for (index, view), answer in replacements.items():
            position = index * 2 + (view == 3)
            events[position] = p.make_event(rows[index], index, view, answer, generation(rows[index], view, answer))
        result = p.summarize(events, rows)['overall']['paired']
        self.assertEqual(result['correct_to_wrong'], 1); self.assertEqual(result['wrong_to_correct'], 1)
        self.assertEqual(result['both_wrong'], 2); self.assertEqual(result['both_correct'], 60)
        self.assertEqual(result['same_wrong'], 1); self.assertEqual(result['same_wrong_including_empty'], 2)
        self.assertEqual(result['both_empty'], 1); self.assertEqual(result['raw_same_wrong'], 0)
        self.assertEqual(result['em_delta_view3_minus_view1'], 0.)

    def test_stop_at_cap_max_new_and_context_exhaustion_separate(self):
        rows = panel(); events = events_for(rows)
        for position, reason, count, tokens, answer in ((0, 'EOS', 128, 40, '파란색'),
                (1, 'MAX_NEW', 128, 40, '오답'), (2, 'CONTEXT_BUDGET_EXHAUSTED', 0, 897, '')):
            index, view = position // 2, (1, 3)[position % 2]
            meta = generation(rows[index], view, answer, reason, count, tokens)
            events[position] = p.make_event(rows[index], index, view, answer, meta)
        report = p.summarize(events, rows)['overall']['by_view']
        self.assertEqual(report['1']['at_output_cap'], 1); self.assertEqual(report['1']['max_new'], 0)
        self.assertEqual(report['1']['context_exhausted'], 1); self.assertEqual(report['1']['empty'], 1)
        self.assertEqual(report['3']['at_output_cap'], 1); self.assertEqual(report['3']['max_new'], 1)

    def test_duplicate_missing_unknown_view_and_index_rejected(self):
        rows = panel(); events = events_for(rows)
        bad = [events[:-1], events + [events[0]], [events[0]] + events[:-1]]
        for field, value in (('view', 0), ('view', 2), ('view', '3'), ('frozen_row_index', 64), ('frozen_row_index', True)):
            broken = copy.deepcopy(events); broken[0][field] = value; bad.append(broken)
        for broken in bad:
            with self.assertRaises(ValueError): p.summarize(broken, rows)

    def test_source_id_language_alias_context_and_prompt_mutations_rejected(self):
        rows = panel(); events = events_for(rows)
        for field, value in (('root', 'OTHER'), ('language', 'en'), ('case_id', 'OTHER'),
                ('case_source_sha256', 'OTHER'), ('source_sha256', 'OTHER'), ('source_path', 'other.json'),
                ('aliases', ['다른 답']), ('context', rows[0]['context'] + '추가'), ('question', '다른 질문'),
                ('frozen_row_index', 2), ('article_id', 'OTHER'), ('split', 'train')):
            broken = copy.deepcopy(events); broken[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): p.summarize(broken, rows)
        broken = copy.deepcopy(events); broken[0]['messages'] = p.messages(rows[0], 3)
        with self.assertRaises(ValueError): p.summarize(broken, rows)

    def test_raw_answer_or_score_change_cannot_hide_behind_stored_hashes(self):
        rows = panel(); events = events_for(rows)
        for change in ('answer', 'score', 'nan', 'extra_score'):
            broken = copy.deepcopy(events)
            if change == 'answer': broken[0]['answer'] += '추가'
            elif change == 'score': broken[0]['scores']['em'] = 0.
            elif change == 'nan': broken[0]['scores']['f1'] = float('nan')
            else: broken[0]['scores']['other'] = 1.
            with self.assertRaises(ValueError): p.summarize(broken, rows)

    def test_generation_sha_output_limit_and_false_max_completion_rejected(self):
        value = pair(); answer = '파란색'; good = generation(value, 1, answer)
        for change in (dict(actual_prompt_sha256='BAD'), dict(raw_answer_sha256='BAD'),
                dict(requested_max_new=64), dict(max_new=64), dict(prompt_tokens=897),
                dict(generated_tokens=129), dict(generated_tokens=True), dict(finish_reason='OTHER'),
                dict(finish_reason=[]),
                dict(finish_reason='MAX_NEW', generated_tokens=127), dict(finish_reason='EOS', generated_tokens=0),
                dict(finish_reason='CONTEXT_BUDGET_EXHAUSTED', generated_tokens=0, prompt_tokens=897)):
            with self.assertRaises(ValueError): p.make_event(value, 0, 1, answer, dict(good, **change))
        for index in (-1, 64, True, '0'):
            with self.assertRaises(ValueError): p.make_event(value, index, 1, answer, good)

    def test_whole_source_order_or_unrelated_original_view_mutation_rejected(self):
        rows = panel(); events = events_for(rows)
        with self.assertRaises(ValueError): p.summarize(events, list(reversed(rows)))
        changed = copy.deepcopy(rows)
        changed[0]['views']['0']['meta']['추가'] = '다른 원형'
        with self.assertRaises(ValueError): p.summarize(events, changed)


if __name__ == '__main__': unittest.main()
