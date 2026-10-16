"""원천이나 모델 없이 작은 합성 QA만 사용하는 묶음 진단 회귀."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_question_bundles as b


def case(root, question, gold, *, context='빨강 파랑', language='ko', article='article', context_id='context',
         source='synthetic.json', aliases=None, starts=None):
    aliases = [gold] if aliases is None else aliases
    starts = [context.index(alias) for alias in aliases] if starts is None else starts
    return dict(root=root, language=language, article_id=article, context_id=context_id,
        context=context, question=question, answers=[dict(text=a, answer_start=s) for a, s in zip(aliases, starts)],
        aliases=list(aliases), source_path=source, source_sha256=b._sha(source))


def distinct(language='ko', suffix=''):
    return [case('a' + suffix, '첫 질문?', '빨강', language=language, context_id='context' + suffix),
            case('b' + suffix, '둘째 질문?', '파랑', language=language, context_id='context' + suffix)]


def events(cases, answers=None, lang_key='language'):
    answers = {} if answers is None else answers
    result = []
    for c in cases:
        for view in (0, 1, 2):
            answer = answers.get((c['root'], view), c['aliases'][0])
            result.append(dict(root=c['root'], **{lang_key: c['language']}, view=view,
                question=c['question'], context=c['context'], aliases=copy.deepcopy(c['aliases']), answer=answer,
                scores=b.qa_scores(answer, c['aliases'], c['language'])))
    return result


class QuestionBundleTests(unittest.TestCase):
    def test_distinct_source_only_bundle_identity_and_no_mutation(self):
        cases = distinct(); before = copy.deepcopy(cases); report = b.census(cases)
        self.assertEqual(report['counts']['cases'], 2); self.assertEqual(report['counts']['exact_two_groups'], 1)
        bundle = report['bundles'][0]
        self.assertEqual(bundle['roots'], ['a', 'b']); self.assertEqual(bundle['category'], 'character_distinct_candidate')
        self.assertTrue(bundle['character_distinct_candidate']); self.assertFalse(bundle['semantic_negative'])
        self.assertFalse(bundle['training_example']); self.assertFalse(report['model_answers_used_for_selection'])
        self.assertEqual(cases, before); json.dumps(report, ensure_ascii=False, allow_nan=False)

    def test_source_only_ids_stable_under_order_but_ordered_digest_changes(self):
        cases = distinct(); left = b.census(cases); right = b.census(list(reversed(cases)))
        self.assertEqual(left['bundles'], right['bundles'])
        self.assertEqual(left['source_set_sha256'], right['source_set_sha256'])
        self.assertNotEqual(left['source_ordered_sha256'], right['source_ordered_sha256'])

    def test_exactly_two_only_no_pair_selection_from_three(self):
        cases = distinct(); cases.append(case('c', '셋째?', '빨강'))
        report = b.census(cases)
        self.assertEqual(report['counts']['group_size_histogram'], {'3': 1})
        self.assertEqual(report['counts']['exact_two_groups'], 0); self.assertFalse(report['bundles'])
        report = b.census(cases[:1]); self.assertEqual(report['counts']['unbundled_cases'], 1)

    def test_group_language_article_context_and_source_must_all_match(self):
        for field, value in (('language', 'en'), ('article_id', 'other'), ('context_id', 'other'),
                ('source_path', 'other.json')):
            cases = distinct(); cases[1][field] = value
            if field == 'source_path': cases[1]['source_sha256'] = b._sha(value)
            report = b.census(cases)
            self.assertEqual(report['counts']['exact_two_groups'], 0)

    def test_same_alias_is_normal_and_not_a_negative(self):
        cases = distinct(); cases[1] = case('b', '다른 질문?', '빨강')
        report = b.census(cases); bundle = report['bundles'][0]
        self.assertEqual(bundle['category'], 'same_alias'); self.assertTrue(bundle['relation_flags']['span_overlap'])
        result = b.summarize(events(cases), cases)['overall']['by_view']['0']
        self.assertEqual(result['both_correct'], 1); self.assertEqual(result['same_output'], 1)
        self.assertEqual(result['same_wrong'], 0)

    def test_normalized_context_identity_accepts_but_does_not_pair_raw_variants(self):
        cases = [case('a', '첫 질문?', 'red', context='red blue', language='en'),
                 case('b', '둘째 질문?', 'blue', context='ｒｅｄ\tblue', language='en')]
        report = b.census(cases)
        self.assertEqual(report['counts']['source_groups'], 2)
        self.assertEqual(report['counts']['exact_two_groups'], 0)
        self.assertEqual(report['counts']['unbundled_cases'], 2)
        cases.append(case('c', '셋째 질문?', 'blue', context='red blue', language='en'))
        report = b.census(cases)
        self.assertEqual(report['counts']['exact_two_groups'], 1)
        self.assertEqual(report['bundles'][0]['roots'], ['a', 'c'])
        self.assertEqual(report['bundles'][0]['source']['context_exact_sha256'], b._sha('red blue'))

    def test_normalized_context_collision_still_rejected(self):
        cases = distinct()
        cases[1] = case('b', '둘째 질문?', '파랑', context='빨강 파랑 더하기')
        with self.assertRaisesRegex(ValueError, '정규화 본문'):
            b.census(cases)

    def test_alias_set_intersection_uses_all_aliases_not_only_first(self):
        context = 'red blue crimson'
        cases = [case('a', 'First?', 'red', context=context, language='en', aliases=['red', 'crimson']),
                 case('b', 'Second?', 'blue', context=context, language='en', aliases=['blue', 'crimson'])]
        bundle = b.census(cases)['bundles'][0]
        self.assertEqual(bundle['category'], 'same_alias')

    def test_alias_containment_and_span_overlap_are_separate_flags(self):
        context = '서울시 서울'
        cases = [case('a', '첫째?', '서울시', context=context), case('b', '둘째?', '서울', context=context, starts=[4])]
        bundle = b.census(cases)['bundles'][0]
        self.assertEqual(bundle['category'], 'alias_containment'); self.assertFalse(bundle['relation_flags']['span_overlap'])
        context = 'abcd'
        cases = [case('a', '첫째?', 'abc', context=context), case('b', '둘째?', 'bcd', context=context)]
        bundle = b.census(cases)['bundles'][0]
        self.assertEqual(bundle['category'], 'span_overlap'); self.assertFalse(bundle['relation_flags']['alias_containment'])

    def test_adjacent_spans_not_overlapping_and_same_question_not_candidate(self):
        context = '가나'
        cases = [case('a', '같은 질문', '가', context=context), case('b', '같은\t질문', '나', context=context)]
        bundle = b.census(cases)['bundles'][0]
        self.assertFalse(bundle['relation_flags']['span_overlap']); self.assertEqual(bundle['category'], 'same_question')
        self.assertFalse(bundle['character_distinct_candidate'])

    def test_nfkc_whitespace_casefold_only_preserves_sign_decimal_negation_and_punctuation(self):
        self.assertEqual(b.normalized(' Ａ\tB\n  -３．５ '), 'a b -3.5')
        for left, right in (('-3.5', '3.5'), ('+3.5', '3.5'), ('3.5', '35'), ('not red', 'red'), ('아니다', '이다'), ('a-b', 'ab')):
            self.assertNotEqual(b.normalized(left), b.normalized(right))

    def test_unicode_character_offsets_not_utf8_byte_offsets(self):
        context = '🙂 가 e\u0301 나'
        cases = [case('a', '첫째?', 'e\u0301', context=context), case('b', '둘째?', '나', context=context)]
        self.assertEqual(b.census(cases)['counts']['exact_two_groups'], 1)
        bad = copy.deepcopy(cases); bad[0]['answers'][0]['answer_start'] = len(context[:context.index('e')].encode())
        with self.assertRaises(ValueError): b.census(bad)

    def test_root_duplicate_context_collision_bad_span_alias_and_source_conflict_rejected(self):
        base = distinct(); variants = [base + [base[0]], []]
        for field, value in (('context', '빨강 파랑 추가'), ('source_sha256', 'B' * 64), ('aliases', ['다른 답'])):
            bad = copy.deepcopy(base); bad[1][field] = value; variants.append(bad)
        bad = copy.deepcopy(base); bad[0]['answers'][0]['answer_start'] = True; variants.append(bad)
        bad = copy.deepcopy(base); bad[0]['answers'][0]['answer_start'] = -1; variants.append(bad)
        bad = copy.deepcopy(base); bad[0]['answers'][0]['text'] = '실제 없는 답'; variants.append(bad)
        bad = copy.deepcopy(base); del bad[0]['question']; variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError): b.census(bad)

    def test_source_census_never_accepts_model_output_selection_fields(self):
        for field in b.FORBIDDEN_SOURCE:
            cases = distinct(); cases[0][field] = '사용 금지'
            with self.assertRaises(ValueError): b.census(cases)

    def test_complete_bilingual_all_views_and_both_correct_changed_output(self):
        cases = distinct() + distinct('en', '_en'); raw = events(cases)
        before = copy.deepcopy((cases, raw)); report = b.summarize(raw, cases)
        self.assertEqual(report['cases'], 4); self.assertEqual(report['events'], 12)
        for language in ('ko', 'en'):
            for view in ('0', '1', '2'):
                metric = report['by_language'][language]['by_view'][view]
                self.assertEqual(metric['both_correct'], 1); self.assertEqual(metric['changed_output'], 1)
                self.assertEqual(metric['same_output'], 0); self.assertEqual(metric['em'], 1.)
        self.assertEqual(report['source_census'], b.census(cases)); self.assertEqual((cases, raw), before)
        self.assertEqual(b.summarize(list(reversed(raw)), cases), report)
        json.dumps(report, ensure_ascii=False, allow_nan=False)

    def test_same_wrong_one_correct_and_both_wrong_are_not_promoted(self):
        cases = distinct(); changed = {('a', 0): '오답', ('b', 0): ' 오답 ', ('b', 1): '오답',
            ('a', 2): '첫 오답', ('b', 2): '둘째 오답'}
        result = b.summarize(events(cases, changed), cases)['overall']['by_view']
        self.assertEqual(result['0']['both_wrong'], 1); self.assertEqual(result['0']['same_wrong'], 1)
        self.assertEqual(result['0']['same_output'], 1); self.assertEqual(result['0']['both_correct'], 0)
        self.assertEqual(result['1']['one_correct'], 1); self.assertEqual(result['1']['changed_output'], 1)
        self.assertEqual(result['2']['both_wrong'], 1); self.assertEqual(result['2']['same_wrong'], 0)

    def test_empty_and_signed_outputs_remain_separate(self):
        cases = distinct(); raw = events(cases, {('a', 0): '', ('b', 0): '  ', ('a', 1): '-3.5', ('b', 1): '3.5'})
        report = b.summarize(raw, cases)['overall']['by_view']
        self.assertEqual(report['0']['both_empty'], 1); self.assertEqual(report['0']['same_wrong'], 0)
        self.assertEqual(report['0']['same_wrong_including_empty'], 1)
        self.assertEqual(report['1']['changed_output'], 1); self.assertEqual(report['1']['same_output'], 0)

    def test_events_missing_duplicate_unknown_root_or_view_rejected(self):
        cases = distinct(); raw = events(cases); variants = [raw[:-1], raw + [raw[0]], [raw[0]] + raw[:-1]]
        for field, value in (('root', 'unknown'), ('view', 3), ('view', True), ('view', '0')):
            bad = copy.deepcopy(raw); bad[0][field] = value; variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError): b.summarize(bad, cases)

    def test_event_language_question_context_alias_or_source_change_rejected(self):
        cases = distinct(); raw = events(cases)
        for field, value in (('language', 'en'), ('lang', 'en'), ('question', '다른 질문'), ('context', '다른 문맥'),
                ('aliases', ['다른 답']), ('article_id', 'other'), ('source_sha256', 'B' * 64)):
            bad = copy.deepcopy(raw); bad[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): b.summarize(bad, cases)
        self.assertEqual(b.summarize(events(cases, lang_key='lang'), cases)['events'], 6)

    def test_stored_scores_recomputed_and_wrong_answer_not_same_as_gold(self):
        cases = distinct(); raw = events(cases)
        for change in ('answer', 'em', 'nan', 'missing', 'extra', 'bool'):
            bad = copy.deepcopy(raw)
            if change == 'answer': bad[0]['answer'] = '오답'
            elif change == 'em': bad[0]['scores']['em'] = 0.
            elif change == 'nan': bad[0]['scores']['f1'] = float('nan')
            elif change == 'missing': del bad[0]['scores']['raw_exact']
            elif change == 'extra': bad[0]['scores']['extra'] = 1.
            else: bad[0]['scores']['em'] = True
            with self.assertRaises(ValueError): b.summarize(bad, cases)

    def test_unbundled_cases_still_require_every_original_event(self):
        cases = distinct() + [case('c', '세 번째?', '빨강')]
        self.assertEqual(b.summarize(events(cases), cases)['overall']['bundles'], 0)
        with self.assertRaises(ValueError): b.summarize(events(cases[:2]), cases)
        report = b.summarize(events(cases), cases)
        self.assertIsNone(report['overall']['by_view']['0']['em'])
        json.dumps(report, allow_nan=False)

    def test_actual_answers_cannot_reselect_source_bundles(self):
        cases = distinct(); first = b.summarize(events(cases), cases)
        second = b.summarize(events(cases, {(c['root'], v): '같은 오답' for c in cases for v in (0, 1, 2)}), cases)
        self.assertEqual(first['source_census_sha256'], second['source_census_sha256'])
        self.assertEqual(first['source_census']['bundles'], second['source_census']['bundles'])
        self.assertFalse(second['source_bundles_reselected']); self.assertFalse(second['same_output_promoted_to_correct'])


if __name__ == '__main__': unittest.main()
