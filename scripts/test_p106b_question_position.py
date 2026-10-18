#!/usr/bin/env python3
"""질문 위치 진단의 합성 CPU 회귀. 실물 source/tokenizer/모델은 읽지 않는다."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import copy
from contextlib import redirect_stdout, nullcontext
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from io import StringIO
import hashlib
import json
import subprocess
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from scripts import diag_p106b_question_position as d


class TokenizerFixture:
    """Unicode 문자와 원자적 ChatML 특수 token; 실제 tokenizer 파일0."""
    truncation = None
    padding = None
    special = {'<|im_start|>': 3, '<|im_end|>': 4}

    def token_to_id(self, value):
        return self.special.get(value)

    def encode(self, value):
        ids, offsets, index = [], [], 0
        while index < len(value):
            special = next((s for s in self.special if value.startswith(s, index)), None)
            if special is not None:
                ids.append(self.special[special]); offsets.append((index, index + len(special)))
                index += len(special)
            else:
                ids.append(1000 + ord(value[index])); offsets.append((index, index + 1)); index += 1
        return NS(ids=ids, offsets=offsets)


def source(language, number, length=None):
    alias = '정답' if language == 'ko' else 'Gold'
    return dict(language=language, root=d.sha([language, number]),
        article_id=d.sha([language, 'article', number // 8]), source_sha256=d.SOURCE_SHA[language],
        context=alias + ' ' + 'x' * (20 + number if length is None else length),
        question=('답은 무엇인가 ' if language == 'ko' else 'What is the answer ') + str(number) + '?',
        aliases=[alias])


def sources(each=256, tied=False):
    return [source(language, i, 80 if tied else None) for language in d.LANGUAGES for i in range(each)]


def original_rows(each=256):
    return [dict(row, view=view, answer='선정 금지 답', scores={'불러오면_안됨': -1},
                 generation={'불러오면_안됨': '오염'}, messages=[])
            for row in sources(each) for view in (0, 1, 2)]


def canonical_source_messages(row, view):
    from tinylm.chat.canonical import normalize
    body = d.old_user(row['context'], row['question'], row['language'], view)
    return normalize(dict(messages=[dict(role='user', content=body)]))['messages']


@lru_cache(maxsize=1)
def frozen():
    return d.select_cases(sources(), TokenizerFixture())


def generation(case, answer):
    return dict(actual_prompt_sha256=case['encoding']['prompt_sha256'], raw_answer_sha256=d.sha(answer),
        prompt_tokens=case['encoding']['prompt_tokens'], requested_max_new=128, max_new=128,
        stop_token_sequences=[[4]], eos_token_available=True, stop_at_eos_requested=True,
        stop_at_eos_effective=True, generated_tokens=2, finish_reason='STOP_SEQUENCE', matched_stop_sequence=[4])


def fresh_events(endpoint=d.ENDPOINTS[0], wrong=False):
    cases = copy.deepcopy(frozen()[0]); originals, events = [], []
    for case in cases:
        answer = '다른 답' if wrong else case['aliases'][0]
        meta = generation(case, answer)
        original = dict({k: case[k] for k in d.SOURCE_FIELDS}, view=0,
                        messages=case['messages'], answer=answer, generation=copy.deepcopy(meta))
        if case['condition'] == 'CQ':
            originals.append(original)
        events.append(d.event_for_case(case, endpoint, answer, meta, original))
    return cases, originals, events


def prior_activities(*keys, seconds=20.):
    return {key: dict(status='COMPLETE', active_seconds=seconds) for key in keys}


def answer_manifest(events):
    shards, whole = [], b''
    for index, start in enumerate(range(0, len(events), 256)):
        values = events[start:start + 256]
        raw = b''.join((json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8') for v in values)
        shards.append(dict(path='answers_%06d.jsonl' % index, rows=len(values), bytes=len(raw),
                           sha256=hashlib.sha256(raw).hexdigest().upper()))
        whole += raw
    return dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=len(events), bytes=len(whole), limit_bytes=19_999_999,
                concat_sha256=hashlib.sha256(whole).hexdigest().upper(), shards=shards, lineage={'fixture': True})


class SourceProjectionTests(unittest.TestCase):
    def test_full1536_512_projection_preserves_only_source(self):
        rows = original_rows()
        before = copy.deepcopy(rows)
        result = d.project_natural(rows)
        self.assertEqual(len(result), 512)
        self.assertTrue(all(set(r) == set(d.SOURCE_FIELDS) for r in result))
        self.assertEqual(rows, before)

    def test_previous_answers_scores_finish_never_affect_selection(self):
        rows = original_rows(64)
        before = d.project_natural(rows, expected_roots=128)
        for row in rows:
            row['answer'] = object(); row['scores'] = object(); row['generation'] = object()
        after = d.project_natural(rows, expected_roots=128)
        self.assertEqual(before, after)
        a, ap = d.select_cases(before, TokenizerFixture())
        b, bp = d.select_cases(after, TokenizerFixture())
        self.assertEqual(a, b); self.assertEqual(ap, bp)

    def test_selector_rejects_outcome_fields_even_when_ignored_values(self):
        for field in ('answer', 'scores', 'generation'):
            row = source('ko', 1); row[field] = None
            with self.assertRaises(ValueError):
                d.select_cases([row], TokenizerFixture())

    def test_empty_partial_not_zero_and_duplicates_are_corruption(self):
        for rows in ([], original_rows(2)[:-1]):
            with self.assertRaises(d.Pending):
                d.project_natural(rows, expected_roots=4)
        rows = original_rows(2)
        with self.assertRaises(ValueError):
            d.project_natural(rows + [rows[0]], expected_roots=4)

    def test_cross_view_question_alias_source_tamper_rejected(self):
        for field, replacement in (('question', '바뀐 질문'), ('aliases', ['없는 답']),
                                    ('source_sha256', 'F' * 64), ('article_id', 'F' * 64)):
            rows = original_rows(2); rows[1][field] = replacement
            with self.assertRaises(ValueError):
                d.project_natural(rows, expected_roots=4)

    def test_root_language_unknown_view_and_missing_source_rejected(self):
        for field, replacement in (('view', True), ('view', 3), ('root', '짧음'), ('language', 'fr')):
            rows = original_rows(2); rows[0][field] = replacement
            with self.assertRaises(ValueError):
                d.project_natural(rows, expected_roots=4)
        rows = original_rows(2); del rows[0]['question']
        with self.assertRaises(KeyError):
            d.project_natural(rows, expected_roots=4)


class RenderAndSelectionTests(unittest.TestCase):
    def test_all_four_layouts_same_instruction_uncropped_context_and_question(self):
        for language in d.LANGUAGES:
            row = source(language, 7)
            instruction = d.render_layout(row, 'CQ')[0].splitlines()[0]
            for condition in d.CONDITIONS:
                body, spans = d.render_layout(row, condition)
                self.assertEqual(body.splitlines()[0], instruction)
                self.assertEqual([s['kind'] for s in spans], list(condition))
                for span in spans:
                    self.assertEqual(body[span['start']:span['end']], row['context'] if span['kind'] == 'C' else row['question'])
                case = d.encode_case(row, condition, TokenizerFixture())
                self.assertEqual([m['role'] for m in case['messages']], ['user'])
                self.assertEqual(case['encoding']['question_occurrences'], condition.count('Q'))
                self.assertEqual(case['encoding']['full_context_occurrences'], 1)

    def test_cq_byte_identical_to_old_view0_in_both_languages(self):
        for language in d.LANGUAGES:
            row = source(language, 1)
            body, _ = d.render_layout(row, 'CQ')
            self.assertEqual(body, d.old_user(row['context'], row['question'], language, 0))
            self.assertEqual(d.prompt([dict(role='user', content=body)]),
                             d.prompt([dict(role='user', content=d.old_user(row['context'], row['question'], language, 0))]))

    def test_full_prefix_no_assistant_gold_or_candidate_hint(self):
        row = source('en', 1)
        row['context'] += '\nQuestion: a label inside the unmodified context'
        case = d.encode_case(row, 'QCQ', TokenizerFixture())
        serialized = d.prompt(case['messages'])
        self.assertTrue(serialized.endswith('<|im_start|>assistant\n'))
        self.assertNotIn('<|im_start|>assistant\nGold', serialized)
        self.assertEqual(case['encoding']['offsets'][0]['kind'], 'Q')
        self.assertEqual(case['encoding']['question_occurrences'], 2)
        self.assertFalse(case['encoding']['gold_in_generation_prefix'])
        self.assertFalse(d.PROTOCOL['candidate_answers_supplied'])

    def test_question_distances_use_full_prompt_offsets_not_text_search(self):
        row = source('ko', 1)
        row['context'] += row['question']
        cq = d.encode_case(row, 'CQ', TokenizerFixture())
        qc = d.encode_case(row, 'QC', TokenizerFixture())
        qdist = lambda c: [s['tokens_after_end'] for s in c['encoding']['offsets'] if s['kind'] == 'Q']
        self.assertGreater(qdist(qc)[0], qdist(cq)[0])
        repeated = d.encode_case(row, 'QCQ', TokenizerFixture())
        self.assertGreater(qdist(repeated)[0], qdist(repeated)[1])

    def test_case_alias_copy_does_not_mutate_parent_or_other_conditions(self):
        row = source('ko', 3); old = copy.deepcopy(row)
        a = d.encode_case(row, 'CQ', TokenizerFixture())
        b = d.encode_case(row, 'QC', TokenizerFixture())
        a['aliases'].append('임의 답')
        self.assertEqual(row, old); self.assertEqual(b['aliases'], old['aliases'])

    def test_default_exact128roots_512cases_16_each_quartile(self):
        cases, proof = frozen()
        self.assertEqual(len(cases), 512); self.assertEqual(proof['roots'], 128)
        self.assertEqual(proof['source_roots'], 512)
        self.assertEqual(proof['eligible_roots'], {'ko': 256, 'en': 256})
        self.assertEqual(len({c['case_id'] for c in cases}), 512)
        for language in d.LANGUAGES:
            for q in range(4):
                for condition in d.CONDITIONS:
                    self.assertEqual(sum(c['language'] == language and c['length_quartile'] == q
                                         and c['condition'] == condition for c in cases), 16)
        self.assertFalse(proof['selection_uses_previous_answers'])
        self.assertFalse(proof['selection_uses_scores_or_generation'])

    def test_ties_split_rank_quartiles_by_source_hash_deterministically(self):
        original = sources(68, tied=True)
        a, proof = d.select_cases(original, TokenizerFixture())
        b, other = d.select_cases(list(reversed(original)), TokenizerFixture())
        self.assertEqual(a, b)
        self.assertEqual(proof['ordered_selection_sha256'], other['ordered_selection_sha256'])
        self.assertIn('동률', proof['quartile_rule'])
        self.assertTrue(all(len(s['chosen_roots']) == 16 for group in proof['by_language_quartile'].values() for s in group))

    def test_insufficient_quartile_supply_is_hold_with_exact_shortage(self):
        for each in (0, 63):
            with self.assertRaises(d.Pending) as caught:
                d.select_cases(sources(each), TokenizerFixture())
            self.assertIn('missing_per_quartile', str(caught.exception))
            self.assertIn('축소/대체 금지', str(caught.exception))

    def test_any_one_condition_overflow_excludes_whole_root_without_crop(self):
        tok = TokenizerFixture(); row = source('en', 999, 720); row['question'] = 'Q' * 70
        cq = d.encode_case(row, 'CQ', tok); cqq = d.encode_case(row, 'CQQ', tok)
        self.assertLessEqual(cq['encoding']['prompt_tokens'] + 128, 1024)
        self.assertGreater(cqq['encoding']['prompt_tokens'] + 128, 1024)
        before = copy.deepcopy(row)
        cases, proof = d.select_cases(sources(64) + [row], tok)
        self.assertFalse(any(c['root'] == row['root'] for c in cases))
        self.assertEqual(proof['excluded'][0]['root'], row['root'])
        self.assertEqual(row, before)

    def test_truncation_padding_unknown_eot_and_incomplete_offsets_rejected(self):
        row = source('ko', 1)
        for attr in ('truncation', 'padding'):
            tok = TokenizerFixture(); setattr(tok, attr, {})
            with self.assertRaises(ValueError):
                d.encode_case(row, 'CQ', tok)
        tok = TokenizerFixture(); tok.special = {'<|im_start|>': 3}
        with self.assertRaises(ValueError):
            d.encode_case(row, 'CQ', tok)
        tok = TokenizerFixture(); encode = tok.encode
        def cropped(text):
            result = encode(text)
            if len(result.ids) > 3:
                return NS(ids=result.ids[:-1], offsets=result.offsets[:-1])
            return result
        tok.encode = cropped
        with self.assertRaises(ValueError):
            d.encode_case(row, 'CQ', tok)
        tok = TokenizerFixture(); encode = tok.encode; lookup = tok.token_to_id
        tok.token_to_id = lambda text: 0 if text == '<unk>' else lookup(text)
        def unknown(text):
            result = encode(text)
            if len(result.ids) > 3:
                result.ids[2] = 0
            return result
        tok.encode = unknown
        with self.assertRaises(ValueError):
            d.encode_case(row, 'CQ', tok)


class GenerationAndRecountTests(unittest.TestCase):
    def test_actual_collection_path_runs512_pure_receipts_without_model(self):
        cases, originals, expected = fresh_events()
        by_prompt = {d.prompt(c['messages']): c for c in cases}
        calls, appended, guards = [], [], []
        def emit(messages):
            self.assertEqual([m['role'] for m in messages], ['user'])
            calls.append(messages); case = by_prompt[d.prompt(messages)]
            return case['aliases'][0], generation(case, case['aliases'][0])
        values = d.collect_answers(cases, d.ENDPOINTS[0], originals, emit,
            lambda case: d.encode_case({k: case[k] for k in d.SOURCE_FIELDS}, case['condition'], TokenizerFixture()),
            appended.append, lambda: guards.append(True))
        self.assertEqual(values, expected); self.assertEqual(appended, expected)
        self.assertEqual(len(calls), 512); self.assertEqual(len(guards), 512)

    def test_collection_rejects_runtime_prefix_before_any_new_answer(self):
        cases, originals, _ = fresh_events()
        with self.assertRaises(ValueError):
            d.collect_answers(cases, d.ENDPOINTS[0], originals, Mock(side_effect=AssertionError('호출 금지')),
                lambda case: {}, Mock(side_effect=AssertionError('쓰기 금지')), lambda: None)

    def test_free512_count_and_original_cq_receipt_exact_agreement(self):
        cases, originals, events = fresh_events()
        result = d.recount(events, cases, d.ENDPOINTS[0], originals)
        self.assertEqual(result['cases'], 512); self.assertEqual(result['roots'], 128)
        self.assertEqual(result['cq_reproduction'], dict(n=128, answer_exact_equal=128, receipt_exact_equal=128, both_equal=128))
        self.assertFalse(result['cq_reproduction_interpretation_hold'])
        for language in d.LANGUAGES:
            self.assertEqual(result['by_language'][language]['roots'], 64)
            self.assertTrue(all(s['n'] == 64 for s in result['by_language'][language]['by_condition'].values()))

    def test_missing_is_hold_duplicate_and_other_endpoint_are_error(self):
        cases, originals, events = fresh_events()
        for partial in ([], events[:-1]):
            with self.assertRaises(d.Pending):
                d.recount(partial, cases, d.ENDPOINTS[0], originals)
        with self.assertRaises(ValueError):
            d.recount(events + events[:1], cases, d.ENDPOINTS[0], originals)
        events[0]['endpoint'] = d.ENDPOINTS[1]
        with self.assertRaises(ValueError):
            d.recount(events, cases, d.ENDPOINTS[0], originals)

    def test_legitimate_empty_answer_is_not_missing(self):
        cases, originals, events = fresh_events()
        case = next(c for c in cases if c['condition'] == 'QC')
        meta = generation(case, ''); meta['generated_tokens'] = 1
        event = d.event_for_case(case, d.ENDPOINTS[0], '', meta)
        events = [event if e['case_id'] == case['case_id'] else e for e in events]
        result = d.recount(events, cases, d.ENDPOINTS[0], originals)
        self.assertEqual(result['by_language'][case['language']]['by_condition']['QC']['empty'], 1)

    def test_max_new_eot_prompt_answer_and_config_receipts_strict(self):
        case = frozen()[0][0]; answer = case['aliases'][0]; meta = generation(case, answer)
        for key, value in (('actual_prompt_sha256', 'F' * 64), ('raw_answer_sha256', 'F' * 64),
                           ('generated_tokens', 0), ('generated_tokens', True), ('requested_max_new', 127),
                           ('max_new', 128.0), ('stop_at_eos_requested', 1),
                           ('stop_token_sequences', [[4.0]]), ('matched_stop_sequence', [4.0]),
                           ('stop_token_sequences', [[5]]), ('matched_stop_sequence', [5]),
                           ('finish_reason', 'CONTEXT_BUDGET_EXHAUSTED'), ('eos_token_available', False)):
            changed = dict(meta, **{key: value})
            with self.assertRaises(ValueError):
                d.validate_generation(answer, changed, case)
        changed = dict(meta, finish_reason='MAX_NEW', generated_tokens=128, matched_stop_sequence=None)
        d.validate_generation(answer, changed, case)
        with self.assertRaises(ValueError):
            d.validate_generation(answer, dict(changed, generated_tokens=127), case)

    def test_cq_new_answer_and_receipt_mismatch_preserved_and_hold(self):
        cases, originals, events = fresh_events()
        case = cases[0]
        changed_answer = '다른 값'; changed = generation(case, changed_answer)
        events[0] = d.event_for_case(case, d.ENDPOINTS[0], changed_answer, changed, originals[0])
        result = d.recount(events, cases, d.ENDPOINTS[0], originals)
        self.assertTrue(result['cq_reproduction_interpretation_hold'])
        self.assertEqual(events[0]['answer'], changed_answer)
        comparison = events[0]['cq_reference']
        self.assertFalse(comparison['answer_exact_equal'])
        self.assertIn('raw_answer_sha256', comparison['generation_differing_keys'])
        same_answer = case['aliases'][0]; changed = generation(case, same_answer); changed['generated_tokens'] = 3
        comparison = d.cq_comparison(same_answer, changed, originals[0])
        self.assertTrue(comparison['answer_exact_equal']); self.assertFalse(comparison['generation_receipt_exact_equal'])
        changed = dict(originals[0]['generation'], new_null_field=None)
        comparison = d.cq_comparison(same_answer, changed, originals[0])
        self.assertIn('new_null_field', comparison['generation_differing_keys'])

    def test_gold_source_messages_counts_and_scores_tamper_rejected(self):
        cases, originals, clean = fresh_events()
        for field, value in (('aliases', ['없는 답']), ('context', '교체된 지문'),
                              ('messages', []), ('length_quartile', 9),
                              ('scores', dict(em=0., f1=0., raw_exact=0.))):
            events = copy.deepcopy(clean); events[0][field] = value
            with self.assertRaises(ValueError):
                d.recount(events, cases, d.ENDPOINTS[0], originals)

    def test_validated_cohort_requires64_per_language_and16_per_quartile(self):
        cases = copy.deepcopy(frozen()[0])
        for case in cases:
            if case['language'] == 'ko' and case['length_quartile'] == 0:
                case['length_quartile'] = 1
        with self.assertRaises(ValueError):
            d.validate_cases(cases)
        cases = copy.deepcopy(frozen()[0]); cases[0]['encoding']['question_occurrences'] = 2
        with self.assertRaises(ValueError):
            d.validate_cases(cases)

    def test_readback_preserves_complete_raw_but_returns8_on_cq_mismatch(self):
        for hold in (False, True):
            writes = []
            result = {'output': {'counts': {'cq_reproduction_interpretation_hold': hold}, 'manifest': {'fixture': True}}}
            prepared = {'source': {'fixture': True}, 'stdout_example_selection': {'fixture': '사전선정'}}
            with patch.object(d, 'read_prepared', return_value=(prepared, [], {e: [] for e in d.ENDPOINTS})), \
                 patch.object(d, 'read_endpoint', return_value=(result, [])), \
                 patch.object(d, 'paired_articles', return_value={'fixture': True}), \
                 patch.object(d, 'info', return_value={}), patch.object(d, 'digest', return_value='A' * 64), \
                 patch.object(Path, 'exists', return_value=False), \
                 patch.object(d, 'print_answer_examples') as examples, \
                 patch.object(d, 'write', side_effect=lambda p, v: writes.append(v)), redirect_stdout(StringIO()):
                self.assertEqual(d.readback(), 8 if hold else 0)
            self.assertEqual(examples.call_count, 2)
            self.assertEqual([call.args[2] for call in examples.call_args_list], list(d.ENDPOINTS))
            self.assertEqual(len(writes), 1)
            self.assertEqual(writes[0]['errors'], 0)
            self.assertEqual(writes[0]['total_new_responses'], 1024)
            self.assertFalse(writes[0]['automatic_prompt_adoption'])
            self.assertIn('HOLD' if hold else 'COMPLETE', writes[0]['status'])

    def test_readback_missing_endpoint_writes_no_zero_filled_result(self):
        with patch.object(d, 'read_prepared', return_value=({'source': {}}, [], {e: [] for e in d.ENDPOINTS})), \
             patch.object(d, 'read_endpoint', side_effect=d.Pending('두 번째 모델 미실행')), \
             patch.object(d, 'write') as write, patch.object(Path, 'exists', return_value=False):
            with self.assertRaises(d.Pending):
                d.readback()
        write.assert_not_called()

    def test_numeric_alias_local_rule_is_not_silently_corrected(self):
        self.assertEqual(d.score('0.25%', ['.25%'], 'en'), dict(em=0., f1=0., raw_exact=0.))
        self.assertEqual(d.score('1%', ['about 1%'], 'en')['em'], 0.)
        self.assertEqual(d.score('정 답', ['정답'], 'ko')['em'], 1.)

    def test_count_sum_is_stable_after_raw_order_permutation(self):
        cases, originals, events = fresh_events(wrong=True)
        self.assertEqual(d.recount(events, cases, d.ENDPOINTS[0], originals),
                         d.recount(list(reversed(events)), cases, d.ENDPOINTS[0], originals))

    def test_article_paired_is_within_cp_all_roots_and_deterministic(self):
        _, _, events = fresh_events()
        a = d.paired_articles(events, draws=20)
        b = d.paired_articles(list(reversed(events)), draws=20)
        self.assertEqual(a, b)
        for result in a['by_language'].values():
            self.assertEqual(set(result), {'CQ__QC', 'CQ__QCQ', 'CQ__CQQ', 'QCQ__CQQ'})
            self.assertTrue(all(v['n'] == 64 for v in result.values()))
            self.assertTrue(all(v['metrics']['em']['ci95'] == [0., 0.] for v in result.values()))
        self.assertFalse(a['learning_seed_uncertainty_measured'])
        with self.assertRaises(d.Pending):
            d.paired_articles(events[:-1], draws=2)


class StdoutExampleTests(unittest.TestCase):
    def fixture(self, endpoint=d.ENDPOINTS[0]):
        cases, originals, events = fresh_events(endpoint)
        directory = d.LOCAL / 'evaluate' / endpoint
        return cases, originals, events, directory, answer_manifest(events), d.stdout_example_selection(cases)

    def test_eight_roots_hash_first_per_language_quartile_before_outcomes(self):
        cases = frozen()[0]; selection = d.stdout_example_selection(cases)
        self.assertEqual(selection['roots'], 8); self.assertEqual(len(selection['selected']), 8)
        self.assertEqual(len({(s['language'], s['length_quartile']) for s in selection['selected']}), 8)
        for chosen in selection['selected']:
            candidates = [c for c in cases if c['language'] == chosen['language']
                          and c['length_quartile'] == chosen['length_quartile'] and c['condition'] == 'CQ']
            expected = min(candidates, key=lambda c: d.source_key({k: c[k] for k in d.SOURCE_FIELDS}))
            self.assertEqual(chosen['root'], expected['root'])
            self.assertEqual(set(chosen['case_ids']), set(d.CONDITIONS))
            self.assertNotIn('question', chosen); self.assertNotIn('context', chosen)
        self.assertFalse(selection['outcome_based_replacement'])

    def test_full_question_four_answers_finish_and_multishard_raw_locators(self):
        cases, _, events, directory, manifest, selected = self.fixture()
        lines = []
        payload = d.print_answer_examples(cases, events, d.ENDPOINTS[0], directory, manifest, selected, lines.append)
        self.assertEqual(len(lines), 9)
        header = json.loads(lines[0].split('] ', 1)[1])
        self.assertEqual(header['full_response_denominator'], 512)
        self.assertEqual(header['selection_sha256'], selected['selection_sha256'])
        indexed = {e['case_id']: (i, e) for i, e in enumerate(events)}
        for line, row in zip(lines[1:], payload['examples']):
            self.assertEqual(json.loads(line.split('] ', 1)[1]), row)
            self.assertEqual(list(row['answers']), list(d.CONDITIONS))
            for condition, answer in row['answers'].items():
                index, event = indexed[answer['case_id']]
                self.assertEqual(row['question'], event['question'])
                self.assertEqual(answer['answer'], event['answer'])
                self.assertEqual(answer['finish_reason'], event['generation']['finish_reason'])
                self.assertEqual(answer['raw_line_number_1based'], index % 256 + 1)
                self.assertTrue(answer['raw_path'].endswith('answers_%06d.jsonl' % (index // 256)))
                self.assertNotIn(event['context'], line)
            self.assertNotIn('context', row)

    def test_empty_wrong_and_max_new_are_shown_verbatim_without_replacement(self):
        cases, originals, events, directory, _, selected = self.fixture()
        first = selected['selected'][0]
        case_map = {c['case_id']: c for c in cases}
        refs = {(e['language'], e['root']): e for e in originals}
        replacements = {}
        for condition, answer in (('CQ', ''), ('QC', '틀린 반복 답 ' * 30)):
            case = case_map[first['case_ids'][condition]]
            meta = generation(case, answer)
            if condition == 'CQ':
                meta['generated_tokens'] = 1
            else:
                meta.update(finish_reason='MAX_NEW', generated_tokens=128, matched_stop_sequence=None)
            replacements[case['case_id']] = d.event_for_case(case, d.ENDPOINTS[0], answer, meta,
                refs[(case['language'], case['root'])])
        events = [replacements.get(e['case_id'], e) for e in events]
        payload = d.example_comparisons(cases, events, d.ENDPOINTS[0], directory, answer_manifest(events), selected)
        shown = payload['examples'][0]['answers']
        self.assertEqual(shown['CQ']['answer'], '')
        self.assertEqual(shown['QC']['answer'], '틀린 반복 답 ' * 30)
        self.assertEqual(shown['QC']['finish_reason'], 'MAX_NEW')
        self.assertEqual(payload['selection'], selected)
        self.assertFalse(payload['performance_estimate'])

    def test_helper_changes_no_raw_scores_cases_or_corpus_selection_sha(self):
        cases, _, events, directory, manifest, selected = self.fixture()
        proof = copy.deepcopy(frozen()[1])
        before = (d.sha(cases), d.sha(events), d.sha(manifest), d.sha(proof))
        with patch.object(d, 'score', side_effect=AssertionError('재채점 금지')), \
             patch.object(d, 'select_cases', side_effect=AssertionError('답을 본 뒤 재선정 금지')), \
             patch.object(d, 'dependencies', side_effect=AssertionError('모델/원형 로딩 금지')):
            d.print_answer_examples(cases, events, d.ENDPOINTS[0], directory, manifest, selected, lambda _: None)
        self.assertEqual(before, (d.sha(cases), d.sha(events), d.sha(manifest), d.sha(proof)))
        self.assertEqual(proof['cases_sha256'], d.sha(cases))
        self.assertEqual(proof['cases'], 512)

    def test_answers_scores_and_finish_changes_cannot_change_display_root_selection(self):
        cases, _, events, directory, manifest, selected = self.fixture()
        normal = d.example_comparisons(cases, events, d.ENDPOINTS[0], directory, manifest, selected)
        _, _, wrong = fresh_events(wrong=True)
        wrong[1]['generation'].update(finish_reason='MAX_NEW', generated_tokens=128, matched_stop_sequence=None)
        changed = d.example_comparisons(cases, wrong, d.ENDPOINTS[0], directory, answer_manifest(wrong), selected)
        self.assertEqual(normal['selection'], changed['selection'])
        self.assertEqual([v['root'] for v in normal['examples']], [v['root'] for v in changed['examples']])
        self.assertTrue(all(answer['answer'] == '다른 답' for row in changed['examples'] for answer in row['answers'].values()))

    def test_missing_duplicate_manifest_or_precommitted_selection_tamper_rejected(self):
        cases, _, events, directory, manifest, selected = self.fixture()
        with self.assertRaises(d.Pending):
            d.example_comparisons(cases, events[:-1], d.ENDPOINTS[0], directory, manifest, selected)
        duplicate = list(events); duplicate[1] = duplicate[0]
        with self.assertRaises(ValueError):
            d.example_comparisons(cases, duplicate, d.ENDPOINTS[0], directory, manifest, selected)
        changed = dict(manifest, rows=511)
        with self.assertRaises(ValueError):
            d.example_comparisons(cases, events, d.ENDPOINTS[0], directory, changed, selected)
        changed = dict(selected, selection_sha256='F' * 64)
        with self.assertRaises(ValueError):
            d.example_comparisons(cases, events, d.ENDPOINTS[0], directory, manifest, changed)

    def test_actual_readback_prints_eight_questions_for_each_complete_endpoint(self):
        cases, _, events, _, manifest, selected = self.fixture()
        by_endpoint = {endpoint: [dict(e, endpoint=endpoint) for e in events] for endpoint in d.ENDPOINTS}
        prepared = dict(source={'fixture': True}, stdout_example_selection=selected)
        result = {'output': {'counts': {'cq_reproduction_interpretation_hold': False}, 'manifest': manifest}}
        writes = []
        with patch.object(d, 'read_prepared', return_value=(prepared, cases, {e: [] for e in d.ENDPOINTS})), \
             patch.object(d, 'read_endpoint', side_effect=lambda endpoint, *args: (result, by_endpoint[endpoint])), \
             patch.object(d, 'paired_articles', return_value={'fixture': True}), patch.object(d, 'info', return_value={}), \
             patch.object(d, 'digest', return_value='A' * 64), patch.object(Path, 'exists', return_value=False), \
             patch.object(d, 'write', side_effect=lambda path, value: writes.append(value)), redirect_stdout(StringIO()) as output:
            self.assertEqual(d.readback(), 0)
        examples = [json.loads(line.split('] ', 1)[1]) for line in output.getvalue().splitlines()
                    if line.startswith('[QUESTION_POSITION_EXAMPLE] ')]
        self.assertEqual(len(examples), 16)
        for endpoint in d.ENDPOINTS:
            rows = [e for e in examples if e['endpoint'] == endpoint]
            self.assertEqual(len(rows), 8)
            self.assertTrue(all(e['question'] and len(e['answers']) == 4 for e in rows))
        self.assertEqual(writes[0]['total_new_responses'], 1024)
        self.assertFalse(writes[0]['automatic_prompt_adoption'])
        self.assertNotIn('examples', writes[0])


class BudgetAndEntryTests(unittest.TestCase):
    now = datetime(2026, 10, 19, 0, tzinfo=timezone.utc)

    def test_total3600_has_exact_slots_and600_record_reserve(self):
        value = d.admission('prepare', None, 1200, {}, now=self.now)
        self.assertEqual(value['slot_seconds'], 300)
        self.assertEqual(value['total_study_reserved_active_seconds'], 3600)
        self.assertEqual(value['future_worker_reservations_seconds'], 2700)
        self.assertEqual(value['record_reserve_seconds'], 600)

    def test_hours_of_queue_wait_do_not_expire_prepared_study(self):
        old = prior_activities('prepare', seconds=50.)
        old['prepare']['started_utc'] = '2026-10-18T18:00:00+00:00'
        later = datetime(2026, 10, 20, 1, tzinfo=timezone.utc)
        value = d.admission('evaluate', d.ENDPOINTS[0], 1200, old, now=later)
        self.assertEqual(value['total_study_reserved_active_seconds'], 3350)
        self.assertTrue(value['calendar_expiry_is_not_prepare_plus_one_hour'])

    def test_latest_deadline_and_all_remaining_reservations_rechecked(self):
        prior = prior_activities('prepare', seconds=30.)
        for remaining in (599, 3299):
            with self.assertRaises(d.Pending):
                d.admission('evaluate', d.ENDPOINTS[0], 1200, prior,
                            now=d.END - timedelta(seconds=remaining))
        d.admission('evaluate', d.ENDPOINTS[0], 1200, prior,
                    now=d.END - timedelta(seconds=3300))
        with self.assertRaises(ValueError):
            d.admission('prepare', None, 1200, {}, now=datetime(2026, 10, 19))

    def test_active_overrun_incomplete_and_already_started_are_not_bypassed(self):
        with self.assertRaises(d.Pending):
            d.admission('evaluate', d.ENDPOINTS[0], 1200, {}, now=self.now)
        with self.assertRaises(d.Pending):
            d.admission('prepare', None, 1200, prior_activities('prepare'), now=self.now)
        with self.assertRaises(d.Pending):
            d.admission('evaluate', d.ENDPOINTS[0], 1200, prior_activities('prepare', seconds=301.), now=self.now)
        with self.assertRaises(TimeoutError):
            d.admission('prepare', None, 1200, {}, now=self.now, elapsed=300.)
        for invalid in (0, 59, 1201, True):
            with self.assertRaises(ValueError):
                d.admission('prepare', None, invalid, {}, now=self.now)

    def test_corrupt_hold_interrupt_codes_distinct(self):
        self.assertEqual(d.failure_status(ValueError('변조')), ('TOOL_ERROR', 9))
        self.assertEqual(d.failure_status(d.Pending('미실행')), ('HOLD', 8))
        self.assertEqual(d.failure_status(KeyboardInterrupt()), ('INTERRUPTED', 130))

    def test_worker_actual_completion_error_and_interrupt_record_active_time(self):
        from scripts import p106b_gate_runtime as runtime
        real_admission = d.admission
        for failure, rc in ((None, 0), (ValueError('fixture'), 9), (KeyboardInterrupt(), 130)):
            writes = []
            def admit(mode, endpoint, wall, prior, **kwargs):
                return real_admission(mode, endpoint, wall, prior, now=self.now, elapsed=kwargs.get('elapsed', 0.))
            with patch.object(d, 'activities', return_value={}), patch.object(d, 'admission', side_effect=admit), \
                 patch.object(runtime, 'wall_limit', side_effect=lambda _: nullcontext()), \
                 patch.object(d, 'prepare', return_value=0, side_effect=failure), \
                 patch.object(d, 'digest', return_value='A' * 64), \
                 patch.object(d, 'write', side_effect=lambda p, v: writes.append((p, v))), redirect_stdout(StringIO()):
                self.assertEqual(d.run_worker('prepare'), rc)
            self.assertEqual(len(writes), 1)
            receipt = writes[0][1]
            self.assertEqual(receipt['returncode'], rc)
            self.assertGreaterEqual(receipt['active_seconds'], 0.)
            self.assertEqual(receipt['stage'], 'prepare')
            self.assertTrue(receipt['wrapper_regression_preflight_excluded'])
            self.assertEqual(receipt['output_report_sha256'], 'A' * 64 if rc == 0 else None)

    def test_worker_missing_prerequisite_cannot_write_fake_activity(self):
        with patch.object(d, 'activities', return_value={}), patch.object(d, 'write') as write:
            with self.assertRaises(d.Pending):
                d.run_worker('evaluate', d.ENDPOINTS[0])
        write.assert_not_called()

    def test_activity_reader_binds_code_output_status_and_finite_time(self):
        value = dict(schema=d.VERSION, tag=d.TAG, stage='prepare', status='COMPLETE', returncode=0,
            active_seconds=20., own_code_sha256={p: 'A' * 64 for p in d.OWN_CODE}, output_report_sha256='A' * 64)
        with patch.object(Path, 'exists', lambda p: p.name == 'activity_prepare.json'), \
             patch.object(d, 'required', return_value=value), patch.object(d, 'digest', return_value='A' * 64):
            self.assertEqual(set(d.activities()), {'prepare'})
            for field, changed in (('returncode', 9), ('active_seconds', float('nan')),
                                   ('own_code_sha256', {}), ('output_report_sha256', 'F' * 64)):
                before = value[field]; value[field] = changed
                with self.assertRaises(ValueError):
                    d.activities()
                value[field] = before

    def test_all_modes_check_only_never_read_source_tokenizer_model(self):
        for mode in d.MODES:
            arguments = ['--mode', mode, '--check-only']
            if mode == 'evaluate':
                arguments += ['--endpoint', d.ENDPOINTS[0]]
            with patch.object(d, 'dependencies', side_effect=AssertionError('실물 의존')), \
                 patch.object(d, 'read_source', side_effect=AssertionError('실물 원천')), \
                 patch.object(d, 'info', side_effect=AssertionError('실물 info')), \
                 patch.object(d, 'run_pipeline') as run, redirect_stdout(StringIO()) as output:
                self.assertEqual(d.main(arguments), 0)
            run.assert_not_called(); self.assertIn('"source_read": false', output.getvalue())

    def test_cli_selector_and_mutually_exclusive_bounds(self):
        invalids = [[], ['--mode', 'prepare', '--execute', '--check-only'],
                    ['--mode', 'evaluate', '--check-only'],
                    ['--mode', 'prepare', '--endpoint', d.ENDPOINTS[0], '--check-only'],
                    ['--mode', 'evaluate', '--endpoint', 'cpt_unique32k_best', '--check-only'],
                    ['--mode', 'prepare', '--max-wall-sec', '1201', '--check-only']]
        for argv in invalids:
            with self.assertRaises(SystemExit), patch('sys.stderr', StringIO()):
                d.main(argv)

    def test_every_public_execute_routes_pipeline_not_direct_worker(self):
        for mode in d.MODES:
            argv = ['--mode', mode, '--execute']
            if mode == 'evaluate':
                argv += ['--endpoint', d.ENDPOINTS[0]]
            with patch.object(d, 'run_pipeline', return_value=0) as run, patch.object(d, 'run_worker') as worker:
                self.assertEqual(d.main(argv), 0)
            run.assert_called_once(); worker.assert_not_called()

    def test_actual_common_pipeline_drives_all_three_adapters_for_every_mode(self):
        for mode in d.MODES:
            selected = d.ENDPOINTS[0] if mode == 'evaluate' else None
            calls, worker_calls = [], []
            def child(command, **kwargs):
                calls.append(command)
                self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
                self.assertEqual(kwargs['cwd'], d.ROOT)
                self.assertEqual(kwargs['env']['OMP_NUM_THREADS'], '2')
                self.assertLessEqual(kwargs['timeout'], 1230)
                if '-m' in command:
                    self.assertIn('scripts.test_p106b_question_position', command)
                    return NS(returncode=0)
                index = command.index('scripts/diag_p106b_question_position.py')
                return NS(returncode=d.main(command[index + 1:]))
            def worker(worker_mode, endpoint, wall):
                worker_calls.append((worker_mode, endpoint, wall)); return 0
            with patch.object(d.subprocess, 'run', side_effect=child), patch.object(d, 'run_worker', side_effect=worker), redirect_stdout(StringIO()) as output:
                self.assertEqual(d.run_pipeline(mode, selected), 0)
            self.assertEqual(len(calls), 3)
            receipt = json.loads(next(line[len('[EXPERIMENT_FINAL] '):] for line in output.getvalue().splitlines() if line.startswith('[EXPERIMENT_FINAL] ')))
            self.assertEqual([p['phase'] for p in receipt['phases']], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
            self.assertTrue(all(p['status'] == 'PASS' for p in receipt['phases']))
            self.assertEqual(worker_calls[-1][0], mode)
            if mode != 'prepare':
                self.assertEqual(worker_calls[0][0], 'preflight')

    def test_pipeline_hold_failure_interrupt_and_timeout_leave_unrun_explicit(self):
        for results, expected in (([0, 8], 8), ([9], 9), ([0, 130], 130)):
            with patch.object(d.subprocess, 'run', side_effect=[NS(returncode=v) for v in results]), redirect_stdout(StringIO()) as output:
                self.assertEqual(d.run_pipeline('prepare'), expected)
            line = next(s for s in output.getvalue().splitlines() if s.startswith('[EXPERIMENT_FINAL] '))
            receipt = json.loads(line[len('[EXPERIMENT_FINAL] '):])
            self.assertEqual(receipt['phases'][-1]['status'], 'NOT_RUN')
        with patch.object(d.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['fixture'], 300)), redirect_stdout(StringIO()):
            self.assertEqual(d.run_pipeline('prepare'), 9)

    def test_direct_absolute_entry_from_other_cwd_help_and_all_check_modes(self):
        driver = str(d.ROOT / 'scripts/diag_p106b_question_position.py')
        arguments = [['--help']]
        for mode in d.MODES:
            command = ['--mode', mode, '--check-only']
            if mode == 'evaluate':
                command += ['--endpoint', d.ENDPOINTS[0]]
            arguments.append(command)
        for argv in arguments:
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', driver, *argv],
                cwd='/tmp', stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            if argv != ['--help']:
                self.assertIn('"model_loaded": false', result.stdout)
                self.assertIn('"source_read": false', result.stdout)

    def test_pending_prepared_blocks_evaluation_before_gpu_or_model_import(self):
        with patch.object(d, 'read_prepared', side_effect=d.Pending('미실행')), \
             patch.object(d, 'dependencies') as imported:
            with self.assertRaises(d.Pending):
                d.evaluate(d.ENDPOINTS[0], 1200)
        imported.assert_not_called()


class EndpointBindingTests(unittest.TestCase):
    def fixture(self):
        endpoint = d.ENDPOINTS[0]
        identity, core = 'C' * 64, 'D' * 64
        outputs = {lane: {'fixture': lane} for lane in d.LANES}
        report = dict(schema='P106B_CPT_UNIQUE32K_EVAL_V1', endpoint=endpoint,
            tag=d.SOURCE_TAGS[endpoint], selection='final640 primary; separate DEV CE minimum, never TEST-selected',
            status='ACTUAL_EVALUATION_COMPLETE', body_unchanged=True, updates=0, checkpoints_written=0,
            checkpoint='runs/final.pt', checkpoint_sha256=identity, initial_core_sha256=core,
            outputs=outputs, receipt_sha256={lane: 'A' * 64 for lane in d.LANES},
            code_sha256={'scripts/fixture.py': 'B' * 64},
            precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False, max_new_natural=128)
        summary = dict(checkpoint_sha256=identity, initial_core_sha256=core, outputs=outputs)
        return report, summary

    def test_exact_final_cp_core_source_and_protocol_bind(self):
        report, summary = self.fixture()
        result = d.bind_endpoint(report, summary, d.ENDPOINTS[0], 'runs/final.pt')
        self.assertEqual(result['checkpoint_sha256'], 'C' * 64)
        self.assertEqual(result['initial_core_sha256'], 'D' * 64)

    def test_other_arm_best_partial_body_manifest_and_protocol_tamper_refused(self):
        clean, summary = self.fixture()
        for key, value in (('endpoint', 'cpt_unique32k_best'), ('status', 'PARTIAL'),
                            ('checkpoint', 'runs/best.pt'), ('body_unchanged', False),
                            ('checkpoint_sha256', 'F' * 64), ('initial_core_sha256', 'F' * 64),
                            ('outputs', {}), ('precision', 'BF16'), ('use_cache', False),
                            ('mtp', True), ('max_new_natural', 64), ('receipt_sha256', {})):
            report = copy.deepcopy(clean); report[key] = value
            with self.assertRaises(ValueError):
                d.bind_endpoint(report, summary, d.ENDPOINTS[0], 'runs/final.pt')

    def test_strict_path_symlink_rejection_and_write_once_open(self):
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaises(ValueError):
                d.safe(d.ROOT / 'test_result/evidence/new.json')
        with self.assertRaises(ValueError):
            d.safe('/tmp/not_in_repository.json')
        stream = Mock(); stream.__enter__ = Mock(return_value=stream); stream.__exit__ = Mock(return_value=False)
        with patch.object(Path, 'is_symlink', return_value=False), patch.object(Path, 'mkdir'), patch.object(Path, 'open', return_value=stream) as opened:
            d.write(d.ROOT / 'test_result/evidence/fixture.json', {'fixture': True})
        self.assertEqual(opened.call_args.args, ('xb',))

    def test_missing_manifest_never_becomes_zero_success(self):
        with self.assertRaises(d.Pending):
            d.read_shards(d.ROOT / 'synthetic', {'rows': 0}, 'answers')
        manifest = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=1,
            shards=[dict(path='../answers_000000.jsonl', bytes=100)])
        with self.assertRaises(ValueError):
            d.read_shards(d.ROOT / 'synthetic', manifest, 'answers')


class CpuLifecycleTests(unittest.TestCase):
    def lifecycle(self, mutate=None):
        """전체 prepare -> read를 메모리 저장소로만 실행한다."""
        documents, directories, stored = {}, set(), {}
        source_rows = sorted(sources(), key=lambda r: (r['language'], r['root']))
        source_proof = {'fixture': '원형 두 endpoint의 검산된 소스'}
        old_rows = {endpoint: [] for endpoint in d.ENDPOINTS}
        meta = dict(d.syntax_info(), code_sha256={'scripts/owned_fixture.py': 'A' * 64})
        loaded = Mock(return_value=TokenizerFixture())
        def exists(path):
            return str(path) in documents or str(path) in directories
        def mkdir(path, **kwargs):
            if not kwargs.get('exist_ok', False) and exists(path):
                raise FileExistsError('합성 namespace 중복')
            directories.add(str(path))
        def write(path, value):
            if str(path) in documents:
                raise FileExistsError('합성 write-once')
            documents[str(path)] = copy.deepcopy(value)
        def digest(path):
            if Path(path) == d.TOKENIZER:
                return d.TOK_SHA
            return d.sha(documents[str(path)])
        def store(stem, rows, lineage):
            stored[stem] = copy.deepcopy(rows)
            manifest = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=len(rows), bytes=100,
                concat_sha256=d.sha(rows), lineage=lineage,
                shards=[dict(path=stem + '_000000.jsonl', bytes=100, rows=len(rows), sha256=d.sha(rows))])
            path = d.CORPUS / (stem + '_shards_manifest.json')
            write(path, manifest)
            return manifest, digest(path)
        with patch.dict(sys.modules, {'tokenizers': NS(Tokenizer=NS(from_file=loaded))}), \
             patch.object(d, 'read_source', return_value=(source_proof, source_rows, old_rows)), \
             patch.object(d, 'info', return_value=meta), \
             patch.object(d, 'write', side_effect=write), patch.object(d, 'digest', side_effect=digest), \
             patch.object(d, 'required', side_effect=lambda path: copy.deepcopy(documents[str(path)])), \
             patch.object(d, 'store_rows', side_effect=store), \
             patch.object(d, 'read_shards', side_effect=lambda directory, manifest, stem: copy.deepcopy(stored[stem])), \
             patch.object(Path, 'exists', exists), patch.object(Path, 'mkdir', mkdir), \
             patch.object(Path, 'is_symlink', return_value=False), redirect_stdout(StringIO()):
            self.assertEqual(d.prepare(), 0)
            loaded.assert_called_once_with(str(d.TOKENIZER))
            report, cases, original = d.read_prepared()
            self.assertEqual(len(cases), 512); self.assertEqual(original, old_rows)
            self.assertFalse(report['model_loaded']); self.assertFalse(report['cuda_initialized'])
            self.assertTrue(report['source_read']); self.assertTrue(report['tokenizer_loaded'])
            self.assertEqual(len(documents), 3)
            self.assertNotIn('context', documents[str(d.EVIDENCE / 'cpu_contract.json')])
            with self.assertRaises(FileExistsError):
                d.prepare()
            if mutate is not None:
                mutate(documents, stored)
                with self.assertRaises((ValueError, d.Pending)):
                    d.read_prepared()
        return report

    def test_real_prepare_read_prepared_functions_share_wire_contract_without_files(self):
        self.lifecycle()

    def test_case_manifest_and_public_summary_tamper_are_detected(self):
        def case(documents, stored):
            stored['cases'][0]['aliases'] = ['없는 답']
        def manifest(documents, stored):
            documents[str(d.CORPUS / 'cases_shards_manifest.json')]['rows'] = 511
        def public(documents, stored):
            documents[str(d.EVIDENCE / 'cpu_contract.json')]['selection']['roots'] = 127
        for mutate in (case, manifest, public):
            self.lifecycle(mutate)


class FullSourceBindingTests(unittest.TestCase):
    """실물 경로를 열지 않고 두 provider의 source/receipt 연결을 통과시킨다."""
    def fixture(self):
        documents, hashes, raw_by_directory = {}, {}, {}
        rows = original_rows()
        for event in rows:
            event['messages'] = canonical_source_messages(event, event['view'])
            event['answer'] = event['aliases'][0]
            event['scores'] = d.score(event['answer'], event['aliases'], event['language'])
            event['generation'] = dict(finish_reason='STOP_SEQUENCE', generated_tokens=2,
                actual_prompt_sha256=d.sha(d.prompt(event['messages'])), raw_answer_sha256=d.sha(event['answer']))
        from scripts.diag_p106b_night_eval_recovery import generation_proof as original_generation_proof
        from scripts.p106b_night_evaluation import summarize_natural as original_summarize_natural
        original_counts = original_summarize_natural(rows)
        providers, summaries = [], {}
        for endpoint in d.ENDPOINTS:
            evidence = d.ROOT / ('test_result/evidence/p106b_cpt_unique32k_v1_s1337/evaluate' if endpoint == d.ENDPOINTS[0] else 'synthetic/base/evaluate')
            local = d.ROOT / 'synthetic' / endpoint / 'local'
            frozen_path = d.ROOT / 'synthetic' / endpoint / 'frozen'
            checkpoint = d.ROOT / 'synthetic' / endpoint / 'final.pt'
            cp_sha, core = d.sha([endpoint, 'cp']), d.sha([endpoint, 'core'])
            manifest = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=1536, concat_sha256=d.sha([endpoint, 'raw']),
                shards=[dict(path='natural_000000.jsonl', sha256=d.sha([endpoint, 'raw']), bytes=100)])
            counts = original_counts
            outputs = {lane: dict(manifest=manifest, counts=counts) if lane == 'natural' else {'fixture': lane} for lane in d.LANES}
            input_sha = d.sha([endpoint, 'input']); hashes[str(frozen_path / 'report.json')] = input_sha
            code_sha = d.sha(['fixture_code']); hashes[str(d.ROOT / 'scripts/fixture.py')] = code_sha
            schema = d.SOURCE_SCHEMAS[endpoint]
            receipt_paths = {lane: evidence / endpoint / (lane + '_receipt.json') for lane in d.LANES}
            receipt_hashes = {lane: d.sha([endpoint, lane]) for lane in d.LANES}
            for lane, path in receipt_paths.items():
                documents[str(path)] = dict(status='LANE_COMPLETE', endpoint=endpoint, lane=lane, output=outputs[lane],
                    checkpoint_sha256=cp_sha, initial_core_sha256=core,
                    body_proof=dict(initial_core_sha256=core, final_core_sha256=core))
                hashes[str(path)] = receipt_hashes[lane]
            report = dict(schema=schema, endpoint=endpoint, status='ACTUAL_EVALUATION_COMPLETE',
                tag=d.SOURCE_TAGS[endpoint], selection='final640 primary; separate DEV CE minimum, never TEST-selected',
                checkpoint=str(checkpoint.relative_to(d.ROOT)), checkpoint_sha256=cp_sha,
                initial_core_sha256=core, body_unchanged=True, updates=0, checkpoints_written=0,
                outputs=outputs, receipt_sha256=receipt_hashes, code_sha256={'scripts/fixture.py': code_sha},
                input_report_sha256=input_sha, directory=str((local / endpoint).relative_to(d.ROOT)),
                precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False, max_new_natural=128)
            report_path = evidence / (endpoint + '_report.json')
            report_sha = d.SOURCE_REPORT_SHA if endpoint == d.ENDPOINTS[0] else d.sha([endpoint, 'report'])
            documents[str(report_path)] = report; hashes[str(report_path)] = report_sha
            documents[str(local / endpoint / 'natural_shards_manifest.json')] = manifest
            hashes[str(local / endpoint / 'natural_shards_manifest.json')] = d.sha([endpoint, 'manifest'])
            hashes[str(local / endpoint / 'natural_000000.jsonl')] = manifest['concat_sha256']
            hashes[str(checkpoint)] = cp_sha
            raw_by_directory[str(local / endpoint)] = copy.deepcopy(rows)
            provider = NS(EVIDENCE=evidence, LOCAL=local, FROZEN=frozen_path,
                training=NS(checkpoint=lambda best, cp=checkpoint: cp),
                info=lambda schema=schema: {'schema': schema},
                receipt_path=lambda e, lane, paths=receipt_paths: paths[lane])
            providers.append(provider)
            summaries[endpoint] = dict(report_sha256=report_sha, checkpoint_sha256=cp_sha,
                initial_core_sha256=core, outputs=outputs)
        providers[0].evaluation = NS(generation_proof=Mock(wraps=original_generation_proof),
            method=NS(summarize_natural=original_summarize_natural))
        documents[str(d.ROOT / d.SOURCE_READBACK)] = dict(status='RAW_RECOUNTED', errors=0,
            tag='p106b_cpt_unique32k_v1_s1337', endpoints=summaries)
        hashes[str(d.ROOT / d.SOURCE_READBACK)] = d.SOURCE_READBACK_SHA
        return providers, documents, hashes, raw_by_directory

    def read(self, fixture):
        providers, documents, hashes, rows = fixture
        with patch.object(d, 'dependencies', return_value=tuple(providers)), \
             patch.object(d, 'required', side_effect=lambda path: documents[str(path)]), \
             patch.object(d, 'digest', side_effect=lambda path: hashes[str(path)]), \
             patch.object(d, 'read_shards', side_effect=lambda directory, manifest, stem: rows[str(directory)]):
            return d.read_source()

    def test_both_reports_all16_lane_receipts_two_cps_and1536_source_equal(self):
        fixture = self.fixture()
        proof, sources_, rows = self.read(fixture)
        self.assertEqual(len(sources_), 512)
        self.assertTrue(all(len(v) == 1536 for v in rows.values()))
        self.assertEqual(set(proof['endpoints']), set(d.ENDPOINTS))
        self.assertEqual(proof['paired_readback_sha256'], d.SOURCE_READBACK_SHA)
        self.assertEqual(fixture[0][0].evaluation.generation_proof.call_count, 3072)

    def test_canonical_text_block_source_full_roundtrip_is_lossless(self):
        fixture = self.fixture()
        before = copy.deepcopy(fixture[3])
        proof, sources_, rows = self.read(fixture)
        self.assertEqual(fixture[3], before)
        self.assertTrue(all(isinstance(e['messages'][0]['content'], list)
                            and e['messages'][0]['content'][0]['type'] == 'text'
                            for values in rows.values() for e in values))
        self.assertEqual(d.project_natural(rows[d.ENDPOINTS[0]]), sources_)
        self.assertEqual(proof['source_projection_sha256'], d.sha(sources_))
        self.assertEqual(len(sources_), 512)

    def test_canonical_and_old_string_prompts_and_new_cq_are_byte_identical(self):
        for language in d.LANGUAGES:
            row = source(language, 3)
            for view in (0, 1, 2):
                canonical = canonical_source_messages(row, view)
                old_string = [dict(role='user', content=d.old_user(row['context'], row['question'], language, view))]
                self.assertIsInstance(canonical[0]['content'], list)
                self.assertIsInstance(old_string[0]['content'], str)
                self.assertNotEqual(canonical, old_string)
                self.assertEqual(d.prompt(canonical).encode('utf-8'), d.prompt(old_string).encode('utf-8'))
                if view == 0:
                    case = d.encode_case(row, 'CQ', TokenizerFixture())
                    self.assertEqual(d.prompt(canonical).encode('utf-8'), d.prompt(case['messages']).encode('utf-8'))
                    self.assertEqual(case['encoding']['prompt_sha256'], d.sha(d.prompt(canonical)))

    def test_source_message_block_tamper_and_same_prompt_shape_changes_rejected(self):
        for change in ('text', 'string', 'extra_empty_block'):
            fixture = self.fixture()
            event = fixture[3][str(fixture[0][0].LOCAL / d.ENDPOINTS[0])][0]
            original_prompt = d.prompt(event['messages']).encode('utf-8')
            blocks = event['messages'][0]['content']
            if change == 'text':
                blocks[0]['text'] += '\n변조된 지시'
            elif change == 'string':
                event['messages'][0]['content'] = blocks[0]['text']
            else:
                blocks.append(dict(type='text', text=''))
            if change != 'text':
                self.assertEqual(d.prompt(event['messages']).encode('utf-8'), original_prompt)
            event['generation']['actual_prompt_sha256'] = d.sha(d.prompt(event['messages']))
            with self.assertRaises(ValueError):
                self.read(fixture)

    def test_source_alias_or_question_difference_across_models_is_rejected(self):
        fixture = self.fixture()
        base_rows = fixture[3][str(fixture[0][1].LOCAL / d.ENDPOINTS[1])]
        root = base_rows[0]['root']
        for row in base_rows:
            if row['root'] == root:
                row['question'] = '다른 원형 질문'
                row['messages'] = canonical_source_messages(row, row['view'])
                row['generation']['actual_prompt_sha256'] = d.sha(d.prompt(row['messages']))
        with self.assertRaises(ValueError):
            self.read(fixture)

    def test_fixed_readback_digest_and_loaded_checkpoint_bytes_are_bound(self):
        for which in ('readback', 'cp'):
            fixture = self.fixture()
            path = str(d.ROOT / d.SOURCE_READBACK) if which == 'readback' else str(fixture[0][0].training.checkpoint(False))
            fixture[2][path] = 'F' * 64
            with self.assertRaises(ValueError):
                self.read(fixture)

    def test_changed_lane_body_or_manifest_stops_before_selection(self):
        for which in ('body', 'manifest'):
            fixture = self.fixture(); provider = fixture[0][0]
            if which == 'body':
                path = provider.receipt_path(d.ENDPOINTS[0], 'natural')
                fixture[1][str(path)]['body_proof']['final_core_sha256'] = 'F' * 64
            else:
                path = provider.LOCAL / d.ENDPOINTS[0] / 'natural_shards_manifest.json'
                fixture[1][str(path)] = {'changed': True}
            with self.assertRaises(ValueError):
                self.read(fixture)


if __name__ == '__main__':
    unittest.main()
