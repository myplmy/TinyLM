#!/usr/bin/env python3
"""실물 원천·가중치·토크나이저·모델 없는 합성 CPU 회귀."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ast
from collections import Counter
from contextlib import nullcontext, redirect_stdout
import copy
import hashlib
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from io import StringIO
import json
import subprocess
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from scripts import diag_p106b_actual_prefix_readback as d


NAMES = ['Alpha', 'Alpine', 'Beta', 'AlphaTail']
CONTENTS = [[10, 11], [10, 12, 13], [20], [10, 11, 14]]
POSITIVE = tuple((i, i) for i in range(4))
CROSSED = tuple((i, j) for i in range(4) for j in range(4) if i != j)


@lru_cache(maxsize=1)
def reference_branch():
    # 동결 helper의 순수 함수만 읽어 검사한다. controller import/consumer0.
    path = ROOT / 'scripts/diag_p106b_subject_role.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'first_divergence_spec')
    env = {}; exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), env)
    return env['first_divergence_spec']


def record(prefix, content):
    full = list(prefix) + list(content) + [4]
    x = full[:-1]; y = [-100] * (len(prefix) - 1) + list(content) + [4]
    return NS(x=x, y=y, segments=[int(v != -100) for v in y], targets=len(content) + 1)


def message(body):
    return dict(role='user', content=[dict(type='text', text=body)])


class PrefixTokenizer:
    """완전 generation prompt만 encode 가능; standalone 이름 호출은 실패한다."""
    def token_to_id(self, value):
        return {'<|im_end|>': 4, '<pad>': 0}.get(value)

    def encode(self, text):
        head, tail = '<|im_start|>user\n', '<|im_end|>\n<|im_start|>assistant\n'
        if not text.startswith(head) or not text.endswith(tail):
            raise AssertionError('완전 generation prefix 외 encode 금지')
        body = text[len(head):-len(tail)]
        number = int(body[1:])
        return NS(ids=[3, 100 + number, 77])


class MainFixture:
    TAG = 'p106b_subject_role_v1_s1337'
    EVIDENCE = ROOT / 'test_result/evidence' / TAG
    CORPUS = ROOT / 'test_result/evidence/local' / TAG / 'corpus'
    LOCAL = ROOT / 'test_result/evidence/local' / TAG
    A_CORPUS = ROOT / 'synthetic/a/corpus'
    A_EVIDENCE = ROOT / 'synthetic/a'

    def __init__(self):
        self.tok = PrefixTokenizer()
        self.bundles = [dict(bundle_id='bundle' + str(i), parent_group_id='group' + str(i // 2),
            language='ko' if i % 2 == 0 else 'en', family='synthetic', answers=list(NAMES), number=i) for i in range(128)]
        self.data = NS(POSITIVE_LAYOUT=POSITIVE, CROSSED_LAYOUT=CROSSED,
                       encode_bundle=self.encode_bundle, evaluation_case=self.evaluation_case)
        self.natural_data = NS(sha=d.sha, TOKENIZER=ROOT / 'synthetic/tokenizer.json', TOK_SHA='A' * 64)
        self.cases = [self.evaluation_case(b, q, 0) for b in self.bundles for q in range(4)]
        self.cases += [dict(id='extra' + str(i), lane='fixture', messages=[message('q' + str(1000 + i))]) for i in range(1246)]
        self.specs = self.rank_specifications(self.bundles, self.tok)
        self.frozen = dict(evaluation_proof={'fixture': True}, ranking_specifications=self.specs,
                           ranking_specifications_sha256=d.sha(self.specs), source_binding={'fixture': 'immutable'})
        self.docs, self.files, self.events, self.ranks = {}, {}, {}, {}
        def manifest(directory, stem):
            part = dict(path=stem + '_000000.jsonl', rows=1, bytes=100, sha256=d.sha([str(directory), stem]))
            value = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=1, shards=[part])
            self.docs[str(directory / (stem + '_shards_manifest.json'))] = value
            self.files[str(directory / part['path'])] = part['sha256']
            return value
        natural = ROOT / 'synthetic/natural/report.json'
        natural_report = dict(manifests={s: manifest(natural.parent, 'replay' if s == 'replay' else 'natural_' + s)
                                        for s in ('train', 'dev', 'test', 'replay')})
        self.docs[str(natural)] = natural_report
        original = dict(manifests={s: manifest(self.A_CORPUS, s) for s in ('train', 'dev', 'test')},
                        natural_source_report=str(natural.relative_to(ROOT)))
        self.docs[str(self.A_CORPUS / 'report.json')] = original
        self.docs[str(self.A_EVIDENCE / 'cpu_contract.json')] = {'fixture': 'A_CPU'}
        self.frozen['manifests'] = {s: manifest(self.CORPUS, s) for s in ('train', 'dev', 'test')}
        self.frozen['source_binding'] = dict(a_corpus_report_sha256=d.sha(original),
            a_cpu_contract_sha256=d.sha(self.docs[str(self.A_EVIDENCE / 'cpu_contract.json')]),
            natural_source_sha256=d.sha(natural_report), natural_manifest_sha256=d.sha(natural_report['manifests']))
        self.files[str(self.natural_data.TOKENIZER)] = self.natural_data.TOK_SHA
        self.files[str(self.CORPUS / 'report.json')] = 'B' * 64
        self.files[str(self.EVIDENCE / 'cpu_contract.json')] = 'C' * 64
        for endpoint in d.ENDPOINTS:
            identity = self.endpoint_identity(endpoint)
            self.files[str(ROOT / identity['checkpoint'])] = identity['checkpoint_sha256']
            self.events[endpoint] = [self.event(c) for c in self.cases]
            self.ranks[endpoint] = [dict(bundle_id=b['bundle_id'], source_spec_sha256=d.sha(self.specs[b['bundle_id']]),
                first_divergence=[dict(v, correct_logit=1., crossed_logit=0., gap=1.) for v in self.specs[b['bundle_id']]['branches']]) for b in self.bundles]
            lineage = dict(tag=self.TAG, **identity)
            report = dict(status='ACTUAL_FIRST_ANSWERS_RECORDED', endpoint=endpoint, lineage=lineage,
                summary=self.summarize_answers(self.events[endpoint], self.cases, self.bundles, self.tok),
                rank_summary=self.summarize_ranks(self.ranks[endpoint], self.bundles, self.specs, self.events[endpoint]))
            directory = self.LOCAL / ('evaluate_' + endpoint)
            for stem, field, values in (('answers', 'answer', self.events[endpoint]), ('rank', 'rank', self.ranks[endpoint])):
                part = dict(path=stem + '_000000.jsonl', rows=len(values), bytes=1000, sha256=d.sha(values))
                manifest = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=len(values), shards=[part], lineage=lineage)
                report[field + '_manifest'] = manifest
                self.docs[str(directory / (stem + '_shards_manifest.json'))] = manifest
                self.files[str(directory / part['path'])] = part['sha256']
                report[field + '_manifest_sha256'] = d.sha(manifest)
            self.docs[str(self.EVIDENCE / ('evaluate_' + endpoint) / 'report.json')] = report
        self.docs[str(self.EVIDENCE / 'readback.json')] = self.expected_gate()
        self.readback = Mock(side_effect=AssertionError('기존 readback 쓰기 호출 금지'))
        self.used = Counter()

    def info(self):
        return dict(schema='MAIN_FIXTURE', tag=self.TAG, code_sha256={'frozen_fixture.py': 'D' * 64})

    def evaluation_case(self, bundle, qi, view):
        return dict(id=bundle['bundle_id'] + 'q' + str(qi), lane='subject_role', view=view,
            bundle_id=bundle['bundle_id'], question_index=qi, language=bundle['language'],
            messages=[message('q' + str(4 * bundle['number'] + qi))], gold=bundle['answers'][qi], candidate_answers_supplied=False)

    def encode_bundle(self, bundle, tok):
        from tinylm.chat.serialize import serialize
        records = {}
        for q in range(4):
            c = self.evaluation_case(bundle, q, 0)
            prefix = tok.encode(serialize(dict(messages=c['messages']), 'chatml', add_generation_prompt=True)).ids
            for a in range(4):
                records[q, a] = record(prefix, CONTENTS[a])
        return [records[k] for k in POSITIVE], [records[k] for k in CROSSED]

    def record_identity(self, value):
        return d.sha(dict(x=value.x, y=value.y, segments=value.segments))

    def first_divergence_spec(self, positive, crossed, qi, ai):
        return reference_branch()(positive, crossed, qi, ai)

    def rank_specifications(self, bundles, tok):
        result = {}
        for b in bundles:
            pos, cross = self.encode_bundle(b, tok); rows = dict(zip(POSITIVE + CROSSED, pos + cross))
            result[b['bundle_id']] = dict(content_lengths=[r.targets - 1 for r in pos],
                record_sha256=d.sha([self.record_identity(r) for r in pos + cross]),
                branches=[self.first_divergence_spec(rows[q, q], rows[q, a], q, a) for q, a in CROSSED])
        return result

    def event(self, case, candidate=None, finish='STOP_SEQUENCE'):
        from tinylm.chat.serialize import serialize
        qi = case.get('question_index', 0); ai = qi if candidate is None else candidate
        ids = CONTENTS[ai] + ([4] if finish == 'STOP_SEQUENCE' else [])
        text = serialize(dict(messages=case['messages']), 'chatml', add_generation_prompt=True)
        prefix = self.tok.encode(text).ids
        return dict(id=case['id'], case=copy.deepcopy(case), answer=NAMES[ai], generation=dict(
            precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False, candidate_answers_supplied=False,
            prompt_sha256=d.sha(text), prompt_ids_sha256=d.sha(prefix), prompt_tokens=len(prefix), max_new=128,
            generated_tokens=len(ids), generated_ids_sha256=d.sha(ids), finish_reason=finish,
            stop_token_sequences=[[4]], matched_stop_sequence=[4] if finish == 'STOP_SEQUENCE' else None))

    def read_prepared(self):
        self.used['read_prepared'] += 1
        return self.frozen, ['fixture_only'], dict(test=self.bundles)

    def evaluation_cases(self, rows, bundles):
        return copy.deepcopy(self.cases)

    def evaluation_proof(self, cases, tok):
        return {'fixture': True}

    def endpoint_identity(self, endpoint):
        return dict(endpoint=endpoint, checkpoint='synthetic/' + endpoint + '.pt', checkpoint_sha256=d.sha([endpoint, 'cp']),
                    expected_core_sha256=d.sha([endpoint, 'core']), training_report_sha256=d.sha([endpoint, 'train']))

    def validate_evaluation(self, report, identity, cases, frozen):
        self.used['validate_evaluation'] += 1
        if (report['lineage'] != dict(tag=self.TAG, **identity) or report['endpoint'] != identity['endpoint']
                or report['status'] != 'ACTUAL_FIRST_ANSWERS_RECORDED'):
            raise ValueError('합성 model/report 계보 변경')

    def read_shards(self, directory, manifest, stem, expected):
        endpoint = Path(directory).name.removeprefix('evaluate_')
        values = self.events[endpoint] if stem == 'answers' else self.ranks[endpoint]
        if len(values) < expected:
            raise d.Pending('합성 부분 원형')
        if len(values) != expected:
            raise ValueError('합성 분모 초과')
        self.used['read_shards'] += 1
        return copy.deepcopy(values)

    def summarize_answers(self, events, cases, bundles, tok):
        if len(events) != 1758 or [e['id'] for e in events] != [c['id'] for c in cases]:
            raise ValueError('합성 원답/순서 변경')
        return dict(responses=len(events), events_sha256=d.sha(events))

    def summarize_ranks(self, ranks, bundles, specs, events):
        return dict(graphs=len(ranks), ranks_sha256=d.sha(ranks))

    def paired_graphs(self, left, right, cases):
        return dict(left_sha256=d.sha(left), right_sha256=d.sha(right), fixture_only=True)

    def expected_gate(self):
        reports = {e: self.docs[str(self.EVIDENCE / ('evaluate_' + e) / 'report.json')] for e in d.ENDPOINTS}
        result = dict(self.info(), status='RAW_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION', cases_sha256=d.sha(self.cases),
            source_reports_sha256={e: d.sha(r) for e, r in reports.items()}, summaries={e: r['summary'] for e, r in reports.items()},
            learning_seeds=1, model_loaded=False, model_training=False, errors=0, semantic_adoption='USER_REVIEW_REQUIRED')
        for left, right in (('ce', 'role_only'), ('ce', 'all_axes'), ('role_only', 'all_axes')):
            result[right + '_minus_' + left] = self.paired_graphs(self.events[left], self.events[right], self.cases)
        return result

    def required(self, path):
        if str(path) not in self.docs:
            raise d.Pending('합성 선행 누락')
        return copy.deepcopy(self.docs[str(path)])

    def digest(self, path):
        if str(path) in self.docs:
            return d.sha(self.docs[str(path)])
        if str(path) in self.files:
            return self.files[str(path)]
        if Path(path).name in ('diag_p106b_actual_prefix_readback.py', 'test_p106b_actual_prefix_readback.py'):
            return 'E' * 64
        raise AssertionError('허용되지 않은 실물 지문 읽기: ' + str(path))


@lru_cache(maxsize=1)
def fixture():
    main = MainFixture()
    questions = d.build_questions(main, main.bundles, main.tok, main.specs, main.cases)
    return main, questions


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.main, questions = fixture(); self.question = questions[0]
        self.event = self.main.event(self.main.cases[0])

    def test_stop_includes_exactly_one_real_eot_and_compact_int_list_hash(self):
        auth = d.authenticate(self.question, self.event)
        self.assertEqual(auth['status'], 'AUTHENTICATED'); self.assertEqual(auth['generated_ids'], [10, 11, 4])
        self.assertEqual(auth['reconstructed_sha256'], self.main.natural_data.sha([10, 11, 4]))
        self.assertEqual(auth['reconstructed_sha256'], hashlib.sha256(b'[10,11,4]').hexdigest().upper())
        self.assertNotEqual(auth['reconstructed_sha256'], d.sha([10, 11]))
        self.assertIsNone(auth['quality_score'])

    def test_raw_exact_only_whitespace_nfkc_casefold_and_punctuation_remain_unresolved(self):
        for raw in (' Alpha', 'Alpha ', 'alpha', 'Ａlpha', 'Alpha.', 'Alpha\n'):
            event = dict(self.event, answer=raw)
            auth = d.authenticate(self.question, event)
            self.assertEqual(auth['status'], 'UNRESOLVED'); self.assertEqual(auth['raw_name_matches'], [])
            self.assertFalse(auth['raw_normalization_used']); self.assertIsNone(auth['quality_score'])

    def test_ambiguous_raw_name_and_outside_answer_are_not_model_or_tool_failures(self):
        question = dict(self.question, names=['Alpha', 'Alpha', 'Beta', 'AlphaTail'])
        self.assertEqual(d.authenticate(question, self.event)['reason'], 'AMBIGUOUS_RAW_NAME')
        self.assertEqual(d.authenticate(self.question, dict(self.event, answer='unknown'))['reason'], 'NO_EXACT_RAW_NAME')

    def test_eos_never_guesses_an_eot_even_with_matching_name_and_hash(self):
        event = self.main.event(self.main.cases[0], finish='EOS')
        auth = d.authenticate(self.question, event)
        self.assertEqual(auth['reason'], 'EOS_UNRESOLVED'); self.assertIsNone(auth['generated_ids'])
        self.assertIsNone(auth['reconstructed_sha256'])

    def test_max_new_uses_only_content_vector_exact_count_and_hash(self):
        event = self.main.event(self.main.cases[0], finish='MAX_NEW')
        auth = d.authenticate(self.question, event)
        self.assertEqual(auth['status'], 'AUTHENTICATED'); self.assertEqual(auth['generated_ids'], [10, 11])
        self.assertEqual(auth['max_new_length_observation'], 'RECORDED_NON128_MAX')
        self.assertFalse(auth['finish_reason_semantics_verified'])
        event['generation']['generated_ids_sha256'] = d.sha([10, 11, 4])
        self.assertEqual(d.authenticate(self.question, event)['reason'], 'CANONICAL_GENERATED_IDS_HASH_MISMATCH')

    def test_normal_max128_does_not_authenticate_short_canonical_name(self):
        event = self.main.event(self.main.cases[0], finish='MAX_NEW')
        event['generation'].update(generated_tokens=128, generated_ids_sha256=d.sha([10, 11] + [99] * 126))
        auth = d.authenticate(self.question, event)
        self.assertEqual(auth['status'], 'UNRESOLVED'); self.assertEqual(auth['reason'], 'GENERATED_LENGTH_MISMATCH')
        self.assertEqual(auth['max_new_length_observation'], 'RECORDED_MAX128')
        self.assertIsNone(auth['generated_ids'])

    def test_unknown_finish_missing_or_bad_hash_count_and_noncanonical_segmentation_unresolved(self):
        for update in (dict(finish_reason='EOS_UNAVAILABLE'), dict(generated_tokens=True), dict(generated_tokens=4),
                       dict(generated_ids_sha256='x' * 64), dict(generated_ids_sha256=[10, 11, 4]),
                       dict(generated_ids_sha256=d.sha([110, 111, 4]))):
            event = copy.deepcopy(self.event); event['generation'].update(update)
            auth = d.authenticate(self.question, event)
            self.assertEqual(auth['status'], 'UNRESOLVED'); self.assertIsNone(auth['generated_ids'])
            self.assertIsNone(auth['quality_score'])
        changed = copy.deepcopy(self.event)
        changed['generation']['generated_ids_sha256'] = hashlib.sha256(b'[10, 11, 4]').hexdigest().upper()
        self.assertEqual(d.authenticate(self.question, changed)['reason'], 'CANONICAL_GENERATED_IDS_HASH_MISMATCH')

    def test_stop_mismatch_and_bool_terminal_are_unresolved_not_fabricated_authentication(self):
        for stop in ([5], [True], None, []):
            event = copy.deepcopy(self.event); event['generation']['matched_stop_sequence'] = stop
            self.assertEqual(d.authenticate(self.question, event)['reason'], 'UNAUTHENTICATED_EOT_RECEIPT')
        event = copy.deepcopy(self.event); event['generation']['stop_token_sequences'] = [[5]]
        self.assertEqual(d.authenticate(self.question, event)['reason'], 'UNAUTHENTICATED_EOT_RECEIPT')

    def test_invalid_frozen_content_list_is_source_error(self):
        for ids in ([True, 11], (10, 11), [], [10, 4]):
            question = copy.deepcopy(self.question); question['content_ids'][0] = ids
            with self.assertRaises(ValueError):
                d.authenticate(question, self.event)


class EdgeTests(unittest.TestCase):
    def setUp(self):
        self.main, questions = fixture(); self.question = questions[0]
        self.rank = self.main.ranks['ce'][0]

    def edge(self, candidate, negative):
        event = self.main.event(self.main.cases[0], candidate)
        auth = d.authenticate(self.question, event)
        branch = next(b for b in self.question['branches'] if b['candidate_index'] == negative)
        source = next(b for b in self.rank['first_divergence'] if b['question_index'] == 0 and b['candidate_index'] == negative)
        return d.edge_result(self.question, auth, branch, source)

    def test_different_negative_branch_positions_are_not_shared_one_diag_score(self):
        self.assertEqual([b['branch_index'] for b in self.question['branches']], [1, 0, 2])
        self.assertTrue(all(self.edge(0, a)['status'] == 'MATCH' for a in (1, 2, 3)))

    def test_actual_third_name_has_mismatch_match_and_not_reached_per_edge(self):
        late, selected, too_late = self.edge(2, 1), self.edge(2, 2), self.edge(2, 3)
        self.assertEqual(late['status'], 'MISMATCH'); self.assertIsNone(late['selected_token_relation'])
        self.assertIsNone(late['tf_gap_at_actual_decision']); self.assertFalse(late['tf_gap_interpretable_for_this_actual_decision'])
        self.assertEqual((selected['status'], selected['selected_token_relation']), ('MATCH', 'WRONG'))
        self.assertEqual(too_late['status'], 'NOT_REACHED'); self.assertIsNone(too_late['actual_token_at_index'])

    def test_reached_requires_d_less_than_g_length_even_when_truncated_prefix_matches(self):
        branch = self.question['branches'][-1]
        auth = dict(status='AUTHENTICATED', generated_ids=[10, 11])
        source = next(e for e in self.rank['first_divergence'] if e['question_index'] == 0 and e['candidate_index'] == 3)
        value = d.edge_result(self.question, auth, branch, source)
        self.assertEqual(value['status'], 'NOT_REACHED'); self.assertIsNone(value['tf_gap_at_actual_decision'])

    def test_eot_prefix_branch_both_directions_and_other_token_category(self):
        short = self.edge(0, 3)
        self.assertTrue(short['includes_eot']); self.assertEqual(short['selected_token_relation'], 'GOLD')
        q = fixture()[1][3]; rank = self.main.ranks['ce'][0]
        event = self.main.event(self.main.cases[3], 0); auth = d.authenticate(q, event)
        branch = next(b for b in q['branches'] if b['candidate_index'] == 0)
        source = next(b for b in rank['first_divergence'] if b['question_index'] == 3 and b['candidate_index'] == 0)
        self.assertEqual(d.edge_result(q, auth, branch, source)['selected_token_relation'], 'WRONG')
        self.assertEqual(self.edge(1, 2)['selected_token_relation'], 'GOLD')
        self.assertEqual(self.edge(2, 3)['status'], 'NOT_REACHED')
        q = fixture()[1][2]; event = self.main.event(self.main.cases[2], 1); auth = d.authenticate(q, event)
        branch = next(b for b in q['branches'] if b['candidate_index'] == 0)
        source = next(b for b in rank['first_divergence'] if b['question_index'] == 2 and b['candidate_index'] == 0)
        self.assertEqual(d.edge_result(q, auth, branch, source)['selected_token_relation'], 'WRONG')
        q = copy.deepcopy(self.question); q['content_ids'][3] = [10, 99]
        event = self.main.event(self.main.cases[0], 3)
        event['generation'].update(generated_tokens=3, generated_ids_sha256=d.sha([10, 99, 4]))
        auth = d.authenticate(q, event)
        branch = q['branches'][0]; source = rank['first_divergence'][0]
        self.assertEqual(d.edge_result(q, auth, branch, source)['selected_token_relation'], 'OTHER')

    def test_source_score_sign_is_bound_only_to_exact_edge_and_no_argmax_inferred(self):
        branch = self.question['branches'][0]; source = dict(self.rank['first_divergence'][0], candidate_index=2)
        auth = d.authenticate(self.question, self.main.event(self.main.cases[0]))
        with self.assertRaises(ValueError):
            d.edge_result(self.question, auth, branch, source)
        value = self.edge(0, 1)
        self.assertFalse(value['full_vocab_argmax_inferred']); self.assertFalse(value['cached_full_numeric_parity_inferred'])
        self.assertIsNone(value['quality_score'])


class CorpusAndCensusTests(unittest.TestCase):
    def test_full1536_question4608_edge_closure_and_old_scores_unchanged(self):
        main, questions = fixture(); before = d.sha([main.events, main.ranks, questions])
        qs, edges, summary = d.census(questions, main.events, main.ranks)
        self.assertEqual((len(qs), len(edges)), (1536, 4608))
        self.assertEqual(summary['overall']['edge_states'], dict(MATCH=4608, MISMATCH=0, NOT_REACHED=0, UNAUTHENTICATED=0))
        self.assertEqual(summary['overall']['authenticated_questions'], 1536)
        self.assertEqual(summary['overall']['selected_token_relations_on_match'], {'GOLD': 4608})
        self.assertEqual(d.sha([main.events, main.ranks, questions]), before)

    def test_unresolved_closes_all_three_edges_without_quality_zero(self):
        main, questions = fixture(); events = copy.deepcopy(main.events)
        events['ce'][0]['answer'] += ' '
        qs, edges, summary = d.census(questions, events, main.ranks)
        self.assertEqual(summary['overall']['unresolved_questions'], 1)
        self.assertEqual(summary['overall']['edge_states']['UNAUTHENTICATED'], 3)
        self.assertEqual(summary['overall']['unresolved_reasons'], {'NO_EXACT_RAW_NAME': 1})
        self.assertTrue(all(e['quality_score'] is None for e in edges))
        self.assertEqual(len(qs), 1536)

    def test_partial_duplicate_case_or_rank_and_corrupt_prompt_protocol_fail_closed(self):
        main, questions = fixture()
        events = copy.deepcopy(main.events); events['ce'].pop(0)
        with self.assertRaises(d.Pending):
            d.census(questions, events, main.ranks)
        events = copy.deepcopy(main.events); events['ce'][1] = events['ce'][0]
        with self.assertRaises(ValueError):
            d.census(questions, events, main.ranks)
        for field, value in (('prompt_ids_sha256', 'F' * 64), ('precision', 'BF16'), ('mtp', True)):
            events = copy.deepcopy(main.events); events['ce'][0]['generation'][field] = value
            with self.assertRaises(ValueError):
                d.census(questions, events, main.ranks)
        ranks = copy.deepcopy(main.ranks); ranks['ce'][1] = ranks['ce'][0]
        with self.assertRaises(ValueError):
            d.census(questions, main.events, ranks)
        ranks = copy.deepcopy(main.ranks); ranks['ce'].pop()
        with self.assertRaises(d.Pending):
            d.census(questions, main.events, ranks)
        ranks = copy.deepcopy(main.ranks); ranks['ce'][0]['first_divergence'].pop()
        with self.assertRaises(d.Pending):
            d.census(questions, main.events, ranks)

    def test_detailed_denominator_join_and_unmatched_decision_interpretation_tamper_rejected(self):
        main, questions = fixture(); qs, edges, _ = d.census(questions, main.events, main.ranks)
        for changed in (edges[:-1],):
            with self.assertRaises(d.Pending): d.summarize(qs, changed)
        changed = copy.deepcopy(edges); changed[0]['candidate_index'] = changed[0]['question_index']
        with self.assertRaises(ValueError): d.summarize(qs, changed)
        events = copy.deepcopy(main.events); events['ce'][0] = main.event(main.cases[0], 2)
        qs, edges, _ = d.census(questions, events, main.ranks)
        changed = copy.deepcopy(edges)
        edge = next(e for e in changed if e['status'] == 'MISMATCH'); edge['tf_gap_at_actual_decision'] = edge['source_tf_gap']
        with self.assertRaises(ValueError): d.summarize(qs, changed)

    def test_record_mask_shift_prefix_boolean_token_and_cpu_hash_tamper_rejected(self):
        for changed in (record([3, 6, 7], [10, 11]), record([3, 6, 7], [10, 11])):
            changed.y[1] = 10
            with self.assertRaises(ValueError):
                d.record_contract(changed, [3, 6, 7], 4)
        value = record([3, 6, 7], [10, 11]); value.x[0] = True
        with self.assertRaises(ValueError):
            d.record_contract(value, [3, 6, 7], 4)
        main, _ = fixture(); specs = copy.deepcopy(main.specs); specs['bundle0']['record_sha256'] = 'F' * 64
        with self.assertRaises(ValueError):
            d.build_questions(main, main.bundles, main.tok, specs, main.cases)
        specs = copy.deepcopy(main.specs); specs['bundle0']['branches'][0]['correct_predictor_position'] += 1
        with self.assertRaises(ValueError):
            d.build_questions(main, main.bundles, main.tok, specs, main.cases)

    def test_complete_record_real_encoder_fixture_and_header_bpe_straddle_rejection(self):
        from scripts.p106b_relation_bind_data import complete_record
        from tinylm.chat.canonical import normalize, validate
        from tinylm.chat.serialize import serialize
        class CharTokenizer:
            def __init__(self, straddle=False): self.straddle = straddle
            def token_to_id(self, token): return {'<|im_start|>': 3, '<|im_end|>': 4, '<pad>': 0}.get(token)
            def encode(self, text):
                ids, offsets, i = [], [], 0
                header = '<|im_start|>assistant\n'; body = text.find(header) + len(header) if header in text else len(text)
                while i < len(text):
                    special = next((s for s in ('<|im_start|>', '<|im_end|>') if text.startswith(s, i)), None)
                    if special:
                        ids.append(self.token_to_id(special)); offsets.append((i, i + len(special))); i += len(special)
                    elif self.straddle and i == body - 1 and body < len(text):
                        ids.append(998); offsets.append((i, i + 2)); i += 2
                    else:
                        ids.append(1000 + ord(text[i])); offsets.append((i, i + 1)); i += 1
                return NS(ids=ids, offsets=offsets)
        row = validate(normalize(dict(messages=[message('source fixture'), dict(role='assistant', content='Alpha')])))
        tok = CharTokenizer(); value = complete_record(row, tok)
        prefix = tok.encode(serialize(dict(messages=row['messages'][:1]), 'chatml', add_generation_prompt=True)).ids
        contract = d.record_contract(value, prefix, 4)
        self.assertEqual(contract['targets'], [1000 + ord(c) for c in 'Alpha'] + [4])
        with self.assertRaises(ValueError):
            complete_record(row, CharTokenizer(straddle=True))


class SourceAndOutputTests(unittest.TestCase):
    def source(self, main):
        with patch.object(d, 'dependencies', return_value=main), patch.object(d, 'required', side_effect=main.required), \
             patch.object(d, 'digest', side_effect=main.digest), \
             patch.dict(sys.modules, {'tokenizers': NS(Tokenizer=NS(from_file=Mock(return_value=main.tok)))}):
            return d.load_source(lambda: None)

    def test_complete_r_is_reconstructed_with_only_nonwriting_helpers(self):
        main = MainFixture(); source = self.source(main)
        self.assertEqual(len(source['questions']), 512)
        self.assertEqual(main.used['validate_evaluation'], 3); self.assertEqual(main.used['read_shards'], 6)
        main.readback.assert_not_called()
        self.assertTrue(source['proof']['actual_model_byte_hashes_checked'])
        self.assertEqual(source['proof']['checkpoint_tensor_deserializations'], 0)

    def test_missing_r_blocks_tokenizer_and_endpoint_before_any_assets(self):
        main = MainFixture(); main.docs.pop(str(main.EVIDENCE / 'readback.json'))
        with patch.object(d, 'dependencies', return_value=main), patch.object(d, 'required', side_effect=main.required), \
             patch.object(main, 'endpoint_identity', side_effect=AssertionError('CP 접근 금지')):
            with self.assertRaises(d.Pending): d.load_source(lambda: None)

    def test_corrupt_r_report_manifest_checkpoint_or_frozen_spec_is_tool_error(self):
        for kind in ('r', 'report', 'manifest', 'cp', 'spec', 'ancestor'):
            main = MainFixture()
            if kind == 'r': main.docs[str(main.EVIDENCE / 'readback.json')]['errors'] = 1
            elif kind == 'report': main.docs[str(main.EVIDENCE / 'evaluate_ce/report.json')]['lineage']['checkpoint_sha256'] = 'F' * 64
            elif kind == 'manifest': main.docs[str(main.LOCAL / 'evaluate_ce/answers_shards_manifest.json')]['rows'] = 1
            elif kind == 'cp': main.files[str(ROOT / 'synthetic/ce.pt')] = 'F' * 64
            elif kind == 'ancestor': main.docs[str(main.A_CORPUS / 'report.json')]['natural_source_report'] = 'synthetic/wrong.json'
            else: main.frozen['ranking_specifications_sha256'] = 'F' * 64
            with self.assertRaises(ValueError): self.source(main)

    def test_partial_actual1758_is_hold_not_invented_complete(self):
        main = MainFixture(); main.events['ce'].pop()
        with self.assertRaises(d.Pending): self.source(main)

    def test_readback_fresh_memory_namespace_only_and_no_old_write(self):
        main, questions = fixture(); source = dict(proof=dict(own_code_sha256={'fixture': 'E' * 64}),
            questions=questions, actual=main.events, ranks=main.ranks)
        saved, manifests, written = {}, {}, {}
        class Writer:
            def __init__(self, directory, stem, limit): self.stem, self.rows = stem, []
            def append(self, row): self.rows.append(copy.deepcopy(row))
            def close(self, lineage):
                written[self.stem] = self.rows
                manifests[self.stem] = dict(rows=len(self.rows), lineage=lineage)
                return manifests[self.stem]
        with patch.object(d, 'load_source', return_value=source), patch.object(d, 'recheck'), \
             patch.object(Path, 'exists', return_value=False), patch.object(Path, 'is_symlink', return_value=False), \
             patch.object(Path, 'mkdir'), patch.object(d, 'ShardWriter', Writer), patch.object(d, 'verify'), \
             patch.object(d, 'read_output', side_effect=lambda directory, manifest, stem, expected: copy.deepcopy(written[stem])), \
             patch.object(d, 'digest', return_value='F' * 64), \
             patch.object(d, 'write', side_effect=lambda path, value: saved.update({str(path): copy.deepcopy(value)})), \
             redirect_stdout(StringIO()):
            self.assertEqual(d.readback(lambda: None), 0)
        self.assertEqual(len(written['questions']), 1536); self.assertEqual(len(written['edges']), 4608)
        self.assertEqual(len(saved), 1); report = next(iter(saved.values()))
        self.assertEqual(report['errors'], 0); self.assertFalse(report['natural_qa_text_copied'])
        main.readback.assert_not_called()

    def test_existing_namespace_or_symlink_is_not_overwritten(self):
        with patch.object(Path, 'exists', return_value=True), patch.object(Path, 'is_symlink', return_value=False), \
             patch.object(d, 'load_source', side_effect=AssertionError('재소비 금지')):
            with self.assertRaises(FileExistsError): d.readback(lambda: None)
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaises(ValueError): d.safe(d.LOCAL)

    def test_new_detail_json_wire_roundtrip_bounded_shards_and_corruption(self):
        rows = [dict(edge_id='one', ids=[1, 2], value=None), dict(edge_id='two', ids=[4], value=False)]
        text = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows)
        manifest = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=2,
                        shards=[dict(path='edges_000000.jsonl', bytes=len(text.encode()))])
        with patch.object(d, 'required', return_value=manifest), patch.object(d, 'verify') as verified, \
             patch.object(Path, 'is_symlink', return_value=False), patch.object(Path, 'open', return_value=StringIO(text)):
            decoded = d.read_output(d.LOCAL, manifest, 'edges', 2)
        self.assertEqual(decoded, rows); self.assertEqual(d.sha(decoded), d.sha(rows)); verified.assert_called_once()
        changed = copy.deepcopy(manifest); changed['shards'][0]['bytes'] = 20_000_000
        with patch.object(d, 'required', return_value=changed):
            with self.assertRaises(ValueError): d.read_output(d.LOCAL, changed, 'edges', 2)
        with patch.object(d, 'required', return_value=manifest), patch.object(d, 'verify'), \
             patch.object(Path, 'is_symlink', return_value=False), patch.object(Path, 'open', return_value=StringIO(text.splitlines()[0] + '\n')):
            with self.assertRaises(ValueError): d.read_output(d.LOCAL, manifest, 'edges', 2)

    def test_source_byte_change_after_snapshot_is_rejected(self):
        main = MainFixture(); source = self.source(main)
        main.files[str(ROOT / 'synthetic/ce.pt')] = 'F' * 64
        with patch.object(d, 'digest', side_effect=main.digest):
            with self.assertRaises(ValueError): d.recheck(source['proof'])

    def test_consumer_original_readback_function_is_never_used(self):
        tree = ast.parse((ROOT / 'scripts/diag_p106b_actual_prefix_readback.py').read_text(encoding='utf-8'))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertFalse(any(isinstance(n.func.value, ast.Name) and n.func.value.id == 'main' and n.func.attr == 'readback' for n in calls))


class PipelineTests(unittest.TestCase):
    now = datetime(2026, 10, 19, 0, tzinfo=timezone.utc)

    def test_check_only_all_modes_source_free_and_actual_requested_bounds_displayed(self):
        for mode in ('preflight', 'readback'):
            with patch.object(d, 'dependencies', side_effect=AssertionError('실물 import 금지')), \
                 patch.object(d, 'run_pipeline', side_effect=AssertionError('실행 금지')), redirect_stdout(StringIO()) as out:
                self.assertEqual(d.main(['--mode', mode, '--max-wall-sec', '123', '--check-only']), 0)
            data = json.loads(out.getvalue().split('] ', 1)[1])
            self.assertEqual(data['phase_bounds_seconds'], dict(REGRESSION=300, PREFLIGHT=123, EXECUTE=123))
            self.assertFalse(data['source_read']); self.assertFalse(data['model_bytes_read'])
            self.assertTrue(all('--max-wall-sec' not in c or c[c.index('--max-wall-sec') + 1] == '123' for _, c in data['phases']))

    def test_both_modes_use_shared_three_phase_pipeline_with_actual_worker_adapters(self):
        for mode in ('preflight', 'readback'):
            calls, workers = [], []
            def child(command, **kw):
                calls.append(command); self.assertEqual(kw['stdin'], subprocess.DEVNULL)
                self.assertEqual(kw['env']['CUDA_VISIBLE_DEVICES'], ''); self.assertEqual(kw['env']['OMP_NUM_THREADS'], '2')
                self.assertEqual(kw['timeout'], 305 if '-m' in command else 128)
                if '-m' in command: return NS(returncode=0)
                index = command.index('scripts/diag_p106b_actual_prefix_readback.py')
                return NS(returncode=d.main(command[index + 1:]))
            with patch.object(d, 'authority', return_value=10000), patch.object(d.subprocess, 'run', side_effect=child), \
                 patch.object(d, 'run_worker', side_effect=lambda m, wall: workers.append((m, wall)) or 0), redirect_stdout(StringIO()) as out:
                self.assertEqual(d.run_pipeline(mode, 123), 0)
            self.assertEqual(len(calls), 3)
            self.assertEqual(workers, [('preflight', 123), ('readback', 123)] if mode == 'readback' else [('preflight', 123)])
            receipt = json.loads(next(l.split('] ', 1)[1] for l in out.getvalue().splitlines() if l.startswith('[EXPERIMENT_FINAL] ')))
            self.assertEqual(receipt['status'], 'COMPLETE'); self.assertEqual(len(receipt['phases']), 3)

    def test_pipeline_fail_hold_interrupt_and_timeout_keep_remaining_not_run(self):
        for values, expected in (([0, 8], 8), ([9], 9), ([0, 130], 130), ([8], 9)):
            with patch.object(d, 'authority', return_value=10000), \
                 patch.object(d.subprocess, 'run', side_effect=[NS(returncode=v) for v in values]), redirect_stdout(StringIO()) as out:
                self.assertEqual(d.run_pipeline('readback'), expected)
            receipt = json.loads(next(l.split('] ', 1)[1] for l in out.getvalue().splitlines() if l.startswith('[EXPERIMENT_FINAL] ')))
            self.assertEqual(receipt['phases'][-1]['status'], 'NOT_RUN')
        with patch.object(d, 'authority', return_value=10000), \
             patch.object(d.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['fixture'], 305)), redirect_stdout(StringIO()):
            self.assertEqual(d.run_pipeline('readback'), 9)

    def test_worker_preflight_read_only_readback_separate_and_wall_bound300(self):
        for mode in ('preflight', 'readback'):
            load, read = Mock(), Mock(return_value=0)
            with patch.object(d, 'authority', return_value=10000), patch.object(d, 'load_source', load), \
                 patch.object(d, 'readback', read), patch('scripts.p106b_gate_runtime.wall_limit', side_effect=lambda seconds: nullcontext()) as limit, \
                 redirect_stdout(StringIO()):
                self.assertEqual(d.run_worker(mode, 123), 0)
            limit.assert_called_once_with(123)
            self.assertEqual(load.call_count, int(mode == 'preflight')); self.assertEqual(read.call_count, int(mode == 'readback'))

    def test_absolute_deadline_bounds_parser_mutual_exclusion_and_error_classification(self):
        with self.assertRaises(d.Pending): d.authority(300, d.END - timedelta(seconds=299))
        self.assertGreater(d.authority(600, self.now), 600)
        for argv in (['--mode', 'readback', '--execute', '--check-only'], ['--mode', 'readback'],
                     ['--mode', 'readback', '--max-wall-sec', '301', '--check-only']):
            with self.assertRaises(SystemExit), patch('sys.stderr', StringIO()): d.main(argv)
        for exc, code in ((d.Pending(), 8), (FileNotFoundError(), 8), (ValueError(), 9), (KeyboardInterrupt(), 130), (TimeoutError(), 9)):
            self.assertEqual(d.failure_status(exc)[1], code)

    def test_worker_elapsed_limit_is_enforced_without_sleep_or_global_ledger_claim(self):
        with patch.object(d, 'authority', return_value=10000), patch.object(d.time, 'perf_counter', side_effect=[0., 124.]), \
             patch.object(d, 'load_source', side_effect=lambda guard: guard()), \
             patch('scripts.p106b_gate_runtime.wall_limit', side_effect=lambda seconds: nullcontext()):
            with self.assertRaises(TimeoutError): d.run_worker('preflight', 123)
        self.assertIn('not a cumulative ledger', d.syntax_info()['worker_budget_scope'])

    def test_absolute_help_and_check_only_from_other_cwd(self):
        path = str(ROOT / 'scripts/diag_p106b_actual_prefix_readback.py')
        for argv in (['--help'], ['--mode', 'preflight', '--check-only'], ['--mode', 'readback', '--check-only']):
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', path, *argv], cwd='/tmp', stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            if argv != ['--help']: self.assertIn('"source_read": false', result.stdout)


if __name__ == '__main__':
    unittest.main()
