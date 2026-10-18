#!/usr/bin/env python3
"""Stage5 합성 CPU 회귀; 실제 source/tokenizer/모델은 읽지 않는다."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import copy
from contextlib import redirect_stdout, nullcontext
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from io import StringIO
import json
import subprocess
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from scripts import diag_p106d_history_scope as d


class TokenizerFixture:
    truncation = None
    padding = None
    specials = {'<|im_start|>': 3, '<|im_end|>': 4, '<eos>': 5}

    def __init__(self, inflate_actual=False, drop_specials=False):
        self.inflate_actual = inflate_actual
        self.drop_specials = drop_specials

    def token_to_id(self, value):
        return self.specials.get(value)

    def encode(self, value, add_special_tokens=True):
        ids, index = [], 0
        while index < len(value):
            special = next((s for s in self.specials if value.startswith(s, index)), None)
            if special is not None:
                ids.append(self.specials[special]); index += len(special)
            else:
                ids.append(1000 + ord(value[index])); index += 1
        if self.inflate_actual and value.startswith('<|im_start|>user') and '\nSTUDENT_OVERFLOW' in value:
            ids = ids * 20
        return NS(ids=ids)

    def decode(self, ids, skip_special_tokens=True):
        reverse = {value: key for key, value in self.specials.items()}
        return ''.join(('' if skip_special_tokens and self.drop_specials else reverse[i]) if i in reverse else chr(i - 1000) for i in ids)


def prior_row(row):
    from tinylm.chat.canonical import normalize, validate
    meta = row['meta']
    return validate(normalize(dict(messages=copy.deepcopy(row['messages']), meta=dict(
        source='p106d_prior_diagnostic', source_family='p106d_prior_closed64',
        root_concept_id=meta['root_concept_id'], language=meta['language'], split='val',
        source_license='repository-code-generated', diagnostic_reuse='known failures, not new blind generalization'))))


@lru_cache(maxsize=1)
def source_fixture():
    _, small, expanded, _ = d.producers()
    result = []
    for cohort in d.COHORTS:
        for family in d.FAMILIES:
            start = 200 if cohort == 'old' else 1000 if family == 'boolean' else 2000
            found, seen = 0, set()
            for index in range(start, start + 300):
                data = small.recipe(family, index) if cohort == 'old' else expanded.expanded_recipe(family, index)
                root = small.hash_object(small.root_definition(data))
                if root in seen or int(root[:8], 16) % 5:
                    continue
                seen.add(root)
                for language in d.LANGUAGES:
                    spec = small.spec_for(data, language, 'val') if cohort == 'old' else expanded.make_spec(data, language, 'val')
                    payload = copy.deepcopy(spec['payload'])
                    if family == 'arithmetic':
                        payload['a'] += 21 if cohort == 'old' else 1 if payload['a'] < 65 else -1
                        payload['b'] += 21 if cohort == 'old' else 0
                    elif family == 'boolean':
                        payload['values']['A'] = not payload['values']['A']
                    elif family == 'lookup':
                        payload['target'] = payload['entries'][1 - data['target']][0]
                        if cohort == 'fresh':
                            payload['entries'].reverse()
                    key = 'reply' if cohort == 'old' else d.KEYS[found % 4]
                    row = small.format_probe(spec, key) if family == 'format' else small.closed_row(spec, payload, probe=True)
                    if cohort == 'old':
                        row = prior_row(row)
                    result.append(d.recover_probe(row, cohort))
                found += 1
                if found == 8:
                    break
            if found != 8:
                raise AssertionError('합성 VAL 공급 부족')
    d.validate_probes(result)
    return result


@lru_cache(maxsize=1)
def frozen():
    probes = source_fixture()
    return probes, d.encode_static_cases(d.make_cases(probes), TokenizerFixture())


def identity(endpoint='parent'):
    return dict(checkpoint='synthetic/' + endpoint + '.pt', checkpoint_sha256=d.sha([endpoint, 'cp']),
                initial_core_sha256=d.sha([endpoint, 'core']))


def response(messages, wanted, tok, finish='STOP_SEQUENCE'):
    ids = tok.encode(wanted + ('<eos>' if finish == 'EOS' else '<|im_end|>'), add_special_tokens=False).ids[:128]
    first_stop = next((i for i, value in enumerate(ids) if value in (4, 5)), None)
    if first_stop is not None:
        ids = ids[:first_stop + 1]
    reason = 'MAX_NEW' if first_stop is None else 'EOS' if ids[-1] == 5 else 'STOP_SEQUENCE'
    prefix_ids = tok.encode(d.common.prompt(messages)).ids
    full, prefix = tok.decode(prefix_ids + ids), tok.decode(prefix_ids)
    helper_answer = full[len(prefix):].split('<|im_end|>', 1)[0]
    proof = d.encoding(messages, None, tok)
    meta = dict(actual_prompt_sha256=proof['prompt_sha256'], raw_answer_sha256=d.sha(helper_answer),
        prompt_tokens=proof['prompt_tokens'], requested_max_new=128, max_new=128,
        stop_token_sequences=[[4]], eos_token_available=True, stop_at_eos_requested=True,
        stop_at_eos_effective=True, generated_tokens=len(ids),
        finish_reason=reason, matched_stop_sequence=[4] if reason == 'STOP_SEQUENCE' else None)
    calls = [dict(ids=prefix_ids + ids, args=[], kwargs={}, output=full),
             dict(ids=prefix_ids, args=[], kwargs={}, output=prefix)]
    body, observation = d.observed_emission(messages, helper_answer, meta, calls, tok)
    return body, meta, observation


def collected(endpoint='parent', overrides=None, tokenizer=None, initial_finish=None, family_answers=None):
    probes, original_cases = frozen(); cases = copy.deepcopy(original_cases)
    tok = tokenizer or TokenizerFixture(); overrides = overrides or {}
    if tokenizer is not None:
        cases = d.encode_static_cases(d.make_cases(probes), tok)
    by_probe = {p['probe_id']: p for p in probes}; initial = {}; answers = {}
    who = identity(endpoint); input_sha = 'A' * 64
    for case in cases:
        probe = by_probe.get(case['probe_id'])
        previous = initial.get(case['probe_id'])
        actual = d.materialize(case, probe, tok, previous, who, endpoint, input_sha)
        if actual['record_status'] != d.GENERATED:
            continue
        wanted = overrides.get(case['probe_id'], case['target']) if case['condition'] == 'INITIAL_DIRECT' else actual['target']
        if probe is not None and probe['family'] in (family_answers or {}):
            wanted = family_answers[probe['family']]
        finish = (initial_finish.get(case['probe_id']) if isinstance(initial_finish, dict) else initial_finish)
        output = response(actual['messages'], wanted, tok,
                          finish if finish and case['condition'] == 'INITIAL_DIRECT' else 'STOP_SEQUENCE')
        key = d.common.prompt(actual['messages'])
        # A pure oracle fixture; no learned model is created or called.
        if key in answers and answers[key] != output:
            raise AssertionError('합성 oracle의 같은 prompt에 충돌 답')
        answers[key] = output
        if case['condition'] == 'INITIAL_DIRECT':
            initial[case['probe_id']] = d.finish_event(actual, probe, endpoint, who, input_sha,
                                                    output[0], output[1], None, output[2], tok)
    calls, appended = [], []
    def emit(messages):
        calls.append(copy.deepcopy(messages))
        return answers[d.common.prompt(messages)]
    events = d.collect(cases, probes, tok, endpoint, who, input_sha, emit, appended.append, lambda: None)
    return probes, cases, tok, who, events, calls


def legacy_records(probes, label):
    tok = TokenizerFixture(); result = []
    for probe in probes:
        prompt = d.common.prompt(probe['source_row']['messages'][:3]); answer = probe['follow_gold']
        result.append(dict(label=label, root=probe['neutral_root_id'], language=probe['language'],
            prompt=prompt, raw_decoded=tok.decode(tok.encode(prompt).ids) + answer,
            answer=answer, gold=answer, closed_code_contract_pass=True,
            generation=dict(finish_reason='STOP_SEQUENCE', generated_tokens=2, max_new=64)))
    return result


def source_documents():
    """실물 경로를 열지 않고 기존 보고/manifest/raw 연결 전체를 만든다."""
    legacy, _, expanded, _ = d.producers(); probes = source_fixture()
    documents, shard_rows = {}, {}
    code = {path: d.sha(['FIXTURE_CODE', path]) for path in legacy.CODE}
    def put(path, value):
        documents[str(path)] = copy.deepcopy(value)
        return d.sha(value)
    def shard(directory, stem, rows):
        part = dict(path=stem + '_000000.jsonl', rows=len(rows), bytes=1234, sha256=d.sha(rows))
        result = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=len(rows), bytes=1234,
                      concat_sha256=d.sha(rows), shards=[part], lineage={'fixture': True})
        put(directory / part['path'], rows); put(directory / (stem + '_shards_manifest.json'), result)
        shard_rows[str(directory), stem] = copy.deepcopy(rows)
        return result
    shards = {stem: shard(d.SOURCE_CORPUS, stem, [p['source_row'] for p in probes if p['cohort'] == cohort])
              for cohort, stem in (('old', 'prior_probes'), ('fresh', 'val_probes'))}
    prepared = dict(schema=expanded.VERSION, status='CORPUS_READY', ready=True, train_rows=4096,
        val_rows=64, seed=1337, tokenizer_sha256=d.TOK_SHA, input=dict(code_sha256=code), shards=shards,
        roots=dict(train=[d.sha(['unrelated TRAIN', i]) for i in range(2048)],
                   val=sorted({p['neutral_root_id'] for p in probes if p['cohort'] == 'fresh'})),
        four_epoch_processed_tokens=123456, epoch_assistant_targets=2345)
    corpus_sha = put(d.SOURCE_CORPUS / 'report.json', prepared)
    reports = dict(prepare=prepared)
    for endpoint in ('fixed', 'views'):
        directory = d.SOURCE_EVIDENCE / endpoint
        reports[endpoint] = dict(status='STUDENT_GATE_COMPLETE', schema=legacy.SCHEMA, arm=endpoint,
            updates=128, data_report_sha256=corpus_sha,
            checkpoint='runs/ckpt/m100s10_ko-en_300M_dense_chat32_' + d.SOURCE_TAG + '_' + endpoint + '.pt',
            checkpoint_sha256=d.sha(['FIXTURE_CHECKPOINT', endpoint]), processed_tokens=123456,
            assistant_targets=4 * 2345, input=dict(code_sha256=code, parent_sha256=d.PARENT_SHA,
                                                 tokenizer_sha256=d.TOK_SHA))
        for label in ('parent', 'child'):
            manifest = shard(directory, 'answers_' + label, legacy_records(probes, label))
            reports[endpoint][label + '_answers'] = dict(questions=128, first_answer_pass=128, shards=manifest)
    reports['readback'] = dict(status='PAIR_READBACK_COMPLETE', arms=[reports['fixed'], reports['views']])
    report_shas = {name: put(d.SOURCE_EVIDENCE / name / 'report.json', value) for name, value in reports.items()}
    audit = {'근거': dict(report_sha256=report_shas)}
    audit_sha = put(d.AUDIT, audit)
    code_paths = {str(d.ROOT / path): identity for path, identity in code.items()}
    def digest(path):
        key = str(path)
        if key in code_paths:
            return code_paths[key]
        if key not in documents:
            raise d.Pending('합성 원형 파일 누락: ' + key)
        return d.sha(documents[key])
    def required(path):
        if str(path) not in documents:
            raise d.Pending('합성 보고 누락')
        return copy.deepcopy(documents[str(path)])
    def read_shards(directory, manifest, stem):
        if required(directory / (stem + '_shards_manifest.json')) != manifest:
            raise ValueError('합성 manifest 바인딩 불일치')
        return copy.deepcopy(shard_rows[str(directory), stem])
    return NS(documents=documents, shards=shard_rows, reports=reports, report_shas=report_shas,
              audit_sha=audit_sha, digest=digest, required=required, read_shards=read_shards)


class ProducerRecoveryTests(unittest.TestCase):
    def test_all128_old_and_fresh_exact_grammar_metadata_and_root_recovered(self):
        probes = source_fixture()
        self.assertEqual(len(probes), 128)
        self.assertEqual(len({p['neutral_root_id'] for p in probes}), 64)
        self.assertEqual({p['recovery_path'] for p in probes}, {'OLD_PRIOR_EXACT_GRAMMAR', 'FRESH_PRODUCER_METADATA_AND_GRAMMAR'})
        self.assertTrue(all(p['original_source_sha256'] is None for p in probes if p['cohort'] == 'old'))
        self.assertTrue(all('output_contract' not in p['source_row']['meta'] for p in probes if p['family'] == 'format'))

    def test_boolean_ast_full_grammar_roundtrip_and_no_eval(self):
        _, _, _, rules = d.producers()
        expression = '(NOT ((A AND B)) OR (C IMPLIES NOT (D)))'
        ast = d.parse_boolean(expression)
        self.assertEqual(rules._boolean(ast, dict(A=True, B=False, C=True, D=False))[1], expression)
        for bad in ('A OR B', 'A; print(1)', '__import__("os")', '(A AND E)', '(A AND B) tail'):
            with self.assertRaises((ValueError, d.Pending)):
                d.parse_boolean(bad)

    def test_initial_follow_gold_meta_and_state_tamper_rejected(self):
        probes = source_fixture()
        for p in (probes[0], next(p for p in probes if p['cohort'] == 'fresh' and p['family'] == 'format')):
            for index in (0, 1, 2, 3):
                row = copy.deepcopy(p['source_row']); row['messages'][index]['content'][0]['text'] += ' 변조'
                with self.assertRaises((ValueError, d.Pending)):
                    d.recover_probe(row, p['cohort'])
            row = copy.deepcopy(p['source_row']); row['meta']['root_concept_id'] = 'F' * 64
            with self.assertRaises(ValueError):
                d.recover_probe(row, p['cohort'])

    def test_old_state_rule_not_recovered_from_gold_or_keywords(self):
        p = next(p for p in source_fixture() if p['cohort'] == 'old' and p['family'] == 'arithmetic')
        row = copy.deepcopy(p['source_row']); state = dict(p['current_payload'], a=p['current_payload']['a'] + 1)
        _, small, _, rules = d.producers(); spec = small.spec_for(p['neutral_definition'], p['language'], 'val')
        row['messages'][2]['content'][0]['text'] = rules.condition_question(spec, state)
        row['messages'][3]['content'][0]['text'] = rules._render(spec, state)[1]
        with self.assertRaises(ValueError):
            d.recover_probe(row, 'old')

    def test_noncanonical_source_blocks_and_split_change_are_not_accepted(self):
        p = source_fixture()[0]
        row = copy.deepcopy(p['source_row']); row['messages'][0]['content'] = d.text(row['messages'][0])
        with self.assertRaises(ValueError):
            d.recover_probe(row, p['cohort'])
        row = copy.deepcopy(p['source_row']); row['meta']['split'] = 'train'
        with self.assertRaises(ValueError):
            d.recover_probe(row, p['cohort'])


class CaseContractTests(unittest.TestCase):
    def test_exact546_with418_static128_templates_and_language_denominators(self):
        probes, cases = frozen()
        self.assertEqual(len(cases), 546)
        self.assertEqual(sum(c['encoding'] is None for c in cases), 128)
        self.assertEqual(sum(c['encoding'] is not None for c in cases), 418)
        self.assertEqual(sum(c['language'] == 'ko' for c in cases), 274)
        self.assertEqual(sum(c['language'] == 'en' for c in cases), 272)
        self.assertTrue(all(c['messages'] is None for c in cases if c['condition'] == 'ACTUAL_HISTORY'))

    def test_compact_uses_initial_not_updated_operands(self):
        probes, cases = frozen(); lookup = {p['probe_id']: p for p in probes}
        for case in cases:
            if case['condition'] == 'MATH_COMPACT_INITIAL':
                p = lookup[case['probe_id']]; v = p['initial_payload']
                self.assertEqual(d.text(case['messages'][0]), f"{v['a']}{v['op']}{v['b']}=?")
                self.assertEqual(case['target'], p['initial_gold'])
                self.assertFalse(case['new_independent_root'])

    def test_c3_current_is_literal_data_not_completed_gold_json(self):
        probes, cases = frozen(); lookup = {p['probe_id']: p for p in probes}
        for case in cases:
            if case['family'] == 'format' and case['condition'] == 'CURRENT_DIRECT':
                p = lookup[case['probe_id']]; body = d.text(case['messages'][0])
                self.assertEqual(case['truth_scope'], 'FORMAT_LITERAL_INPUT')
                self.assertIn(json.dumps(p['current_payload']['literal'], ensure_ascii=False), body)
                self.assertNotIn(p['follow_gold'], body)
                self.assertEqual([m['role'] for m in case['messages']], ['user'])

    def test_minimal_questions_are_separate_development_prompts(self):
        _, cases = frozen(); minimal = [c for c in cases if c['condition'] == 'MINIMAL_KO']
        self.assertEqual([d.text(c['messages'][0]) for c in minimal], [v[0] for v in d.MINIMAL_QUESTIONS])
        self.assertEqual([c['target'] for c in minimal], ['2', '4'])
        self.assertTrue(all(c['probe_id'] is None and not c['new_independent_root'] for c in minimal))


class ActualHistoryTests(unittest.TestCase):
    def test_all546_safe_cases_generated_once_initial_and_complete_recount(self):
        probes, cases, tok, who, events, calls = collected()
        self.assertEqual(len(events), 546); self.assertEqual(len(calls), 546)
        self.assertEqual(sum(e['condition'] == 'INITIAL_DIRECT' for e in events), 128)
        report = d.recount(events, cases, probes, tok, 'parent', who, 'A' * 64)
        self.assertEqual(report['expected_cases'], 546)
        self.assertEqual(report['actual_generations'], 546)
        self.assertEqual(report['explicit_not_run'], 0)
        self.assertEqual(report['real_chain']['chain_both_sum'], 128)

    def test_c3_wrong_empty_whitespace_json_first_answers_preserved_without_strip(self):
        p = next(p for p in source_fixture() if p['family'] == 'format')
        for raw in ('오답', '', ' \n ', ' \n A \n ', '{"x":"틀림"}'):
            probes, cases, tok, who, events, _ = collected(overrides={p['probe_id']: raw})
            actual = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'ACTUAL_HISTORY')
            self.assertEqual(d.text(actual['messages'][1]), raw)
            self.assertEqual(json.loads(actual['target']), {p['format_key']: raw})
            self.assertTrue(actual['metrics']['strict_c3_format_preserved'])
            self.assertFalse(next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'INITIAL_DIRECT')['metrics']['first_fact_correct'])
            report = d.recount(events, cases, probes, tok, 'parent', who, 'A' * 64)
            self.assertEqual(report['real_chain']['chain_both_sum'], 127)
            self.assertEqual(report['real_chain']['first_wrong_but_c3_format_preserved'], 1)
            initial_stats = report['by_condition']['INITIAL_DIRECT']
            self.assertEqual(initial_stats['empty_exact'], int(raw == ''))
            self.assertEqual(initial_stats['whitespace_only'], int(bool(raw) and not raw.strip()))

    def test_eos_terminated_first_reuses_visible_body_not_original_helper_eos_marker(self):
        p = next(p for p in source_fixture() if p['family'] == 'format')
        raw = ' \nwrong\n '
        probes, cases, tok, who, events, calls = collected(overrides={p['probe_id']: raw}, initial_finish={p['probe_id']: 'EOS'})
        first = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'INITIAL_DIRECT')
        actual = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'ACTUAL_HISTORY')
        self.assertEqual(first['answer'], raw); self.assertEqual(first['original_helper_answer'], raw + '<eos>')
        self.assertEqual(first['generation']['finish_reason'], 'EOS')
        self.assertEqual(first['decode_observation']['terminal_ids'], [5])
        self.assertEqual(d.text(actual['messages'][1]), raw); self.assertEqual(json.loads(actual['target']), {p['format_key']: raw})
        self.assertTrue(actual['metrics']['strict_c3_format_preserved']); self.assertEqual(len(calls), 546)
        self.assertEqual(d.recount(events, cases, probes, tok, 'parent', who, 'A' * 64)['actual_generations'], 546)

    def test_c3_uses_actual_previous_string_not_gold_when_scoring(self):
        p = next(p for p in source_fixture() if p['family'] == 'format')
        _, _, _, _, events, _ = collected(overrides={p['probe_id']: 'wrong'})
        event = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'ACTUAL_HISTORY')
        self.assertNotEqual(event['target'], p['follow_gold'])
        self.assertFalse(d.strict_format(p['follow_gold'], p['format_key'], 'wrong'))
        self.assertTrue(d.strict_format(event['answer'], p['format_key'], 'wrong'))

    def test_c1_wrong_initial_is_kept_in_history_but_follow_target_uses_actual_code_state(self):
        probes, cases = frozen()
        prompts = [d.common.prompt(c['messages']) for c in cases if c['messages'] is not None]
        p = next(p for p in probes if p['family'] == 'arithmetic' and prompts.count(d.common.prompt(p['source_row']['messages'][:1])) == 1)
        probes, cases, tok, who, events, _ = collected(overrides={p['probe_id']: 'WRONG_INITIAL'})
        first = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'INITIAL_DIRECT')
        actual = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'ACTUAL_HISTORY')
        self.assertEqual(d.text(actual['messages'][1]), 'WRONG_INITIAL')
        self.assertNotEqual(d.text(actual['messages'][1]), p['initial_gold'])
        self.assertEqual(actual['target'], p['follow_gold']); self.assertTrue(actual['metrics']['condition_pass'])
        self.assertFalse(first['metrics']['first_fact_correct'])
        self.assertEqual(d.recount(events, cases, probes, tok, 'parent', who, 'A' * 64)['real_chain']['chain_both_sum'], 127)

    def test_strict_c3_rejects_duplicate_extra_key_and_non_string_values(self):
        for bad in ('{"reply":"x","reply":"x"}', '{"reply":"x","extra":0}', '{"reply":1}', '{"reply":true}', 'not json'):
            self.assertFalse(d.strict_format(bad, 'reply', 'x'))
        self.assertTrue(d.strict_format(' {"reply":"x"} \n', 'reply', 'x'))
        legacy, _, _, _ = d.producers()
        self.assertTrue(legacy.classify('{"reply":"x","reply":"x"}', '{"reply":"x"}'))

    def test_canonical_reference_over128_keeps_generation_and_all_c3_denominators(self):
        p = next(p for p in source_fixture() if p['family'] == 'format')
        probes, cases, tok, who, events, calls = collected(overrides={p['probe_id']: '\\' * 80})
        actual = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'ACTUAL_HISTORY')
        self.assertGreater(actual['encoding']['canonical_target_tokens_with_eot'], 128)
        self.assertFalse(actual['encoding']['canonical_target_fits_budget'])
        self.assertEqual(actual['record_status'], d.GENERATED)
        self.assertEqual(actual['generation']['finish_reason'], 'MAX_NEW')
        self.assertEqual(len(calls), 546)
        report = d.recount(events, cases, probes, tok, 'parent', who, 'A' * 64)
        group = report['c3_actual_canonical_reference_budget']
        self.assertEqual(group['all_c3']['n_expected'], 32)
        self.assertEqual(group['groups']['CANONICAL_REFERENCE_EXCEEDS']['n_generated'], 1)
        self.assertFalse(group['universal_impossibility_proven'])

    def test_chatml_control_skips_only_actual_case_and_never_fakes_empty_answer(self):
        p = next(p for p in source_fixture() if p['family'] == 'format')
        probes, cases, tok, who, events, calls = collected(overrides={p['probe_id']: '<|im_start|>'})
        actual = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'ACTUAL_HISTORY')
        self.assertEqual(actual['record_status'], d.UNSAFE)
        self.assertNotIn('answer', actual); self.assertNotIn('generation', actual); self.assertNotIn('metrics', actual)
        self.assertEqual(d.text(actual['messages'][1]), '<|im_start|>')
        self.assertEqual(len(events), 546); self.assertEqual(len(calls), 545)
        report = d.recount(events, cases, probes, tok, 'parent', who, 'A' * 64)
        self.assertEqual(report['explicit_not_run'], 1)
        self.assertEqual(report['actual_generations'], 545)
        self.assertIsNone(report['overall']['pass_rate_full_when_complete'])

    def test_all_eight_canonical_chatml_markers_preserve_first_and_only_skip_actual(self):
        p = next(p for p in source_fixture() if p['family'] == 'format')
        markers = d.chatml_control_markers()
        self.assertEqual(set(markers), {'<|im_start|>', '<|im_end|>', '<|think|>', '<|/think|>',
                                       '<|tool_call|>', '<|/tool_call|>', '<|tool_result|>', '<|/tool_result|>'})
        probes, cases, tok, who, events, _ = collected()
        first_source = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'INITIAL_DIRECT')
        actual_case = next(c for c in cases if c['probe_id'] == p['probe_id'] and c['condition'] == 'ACTUAL_HISTORY')
        for marker in markers:
            raw = ' \n' + marker + '\n실제 첫답 '
            # Materializer payload만 격리한다. INITIAL 관찰검산은 다른 회귀가
            # 맡으며 이 mock을 실제 생성/영수증 성공으로 주장하지 않는다.
            first = copy.deepcopy(first_source); first['answer'] = first['original_helper_answer'] = raw
            first['generation']['raw_answer_sha256'] = d.sha(raw)
            with patch.object(d, 'initial_reference', return_value={'isolated_payload_fixture': True}):
                actual = d.materialize(actual_case, p, tok, first, who, 'parent', 'A' * 64)
            self.assertEqual(first['answer'], raw); self.assertEqual(d.text(actual['messages'][1]), raw)
            self.assertEqual(actual['record_status'], d.UNSAFE)
            self.assertEqual(actual['input_rejection_reasons'], ['CHATML_CONTROL_STRING'])
            self.assertNotIn('answer', actual); self.assertNotIn('generation', actual)

    def test_seven_non_eot_chatml_payload_markers_end_to_end_preserve546_accounting(self):
        p = next(p for p in source_fixture() if p['family'] == 'format')
        for marker in set(d.chatml_control_markers()) - {'<|im_end|>'}:
            raw = ' \n' + marker + '\n실제 첫답 '
            probes, cases, tok, who, events, calls = collected(overrides={p['probe_id']: raw})
            first = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'INITIAL_DIRECT')
            actual = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'ACTUAL_HISTORY')
            self.assertEqual(first['answer'], raw); self.assertEqual(actual['record_status'], d.UNSAFE)
            self.assertEqual(len(calls), 545); self.assertEqual(len(events), 546)
            self.assertEqual(d.recount(events, cases, probes, tok, 'parent', who, 'A' * 64)['explicit_not_run'], 1)

    def test_unsafe_and_input_overflow_reasons_both_preserved_for_one_not_run(self):
        p = next(p for p in source_fixture() if p['family'] == 'format')
        probes, cases, tok, who, events, calls = collected(overrides={p['probe_id']: 'STUDENT_OVERFLOW<|think|>'},
                                                        tokenizer=TokenizerFixture(inflate_actual=True))
        actual = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'ACTUAL_HISTORY')
        self.assertEqual(actual['record_status'], d.UNSAFE)
        self.assertEqual(actual['input_rejection_reasons'], ['CHATML_CONTROL_STRING', 'FULL_PROMPT_PLUS128_EXCEEDS1024'])
        self.assertEqual(len(calls), 545)
        self.assertEqual(d.recount(events, cases, probes, tok, 'parent', who, 'A' * 64)['explicit_not_run'], 1)

    def test_actual_input_overflow_not_run_but_other545_generations_continue(self):
        p = next(p for p in source_fixture() if p['family'] == 'format')
        probes, cases, tok, who, events, calls = collected(overrides={p['probe_id']: 'STUDENT_OVERFLOW'}, tokenizer=TokenizerFixture(inflate_actual=True))
        actual = next(e for e in events if e['probe_id'] == p['probe_id'] and e['condition'] == 'ACTUAL_HISTORY')
        self.assertEqual(actual['record_status'], d.OVERFLOW)
        self.assertGreater(actual['encoding']['prompt_tokens'] + 128, 1024)
        self.assertEqual(len(calls), 545)
        self.assertEqual(d.recount(events, cases, probes, tok, 'parent', who, 'A' * 64)['explicit_not_run'], 1)

    def test_other_endpoint_initial_ref_hash_or_raw_tamper_is_technical_error(self):
        probes, cases, tok, who, events, _ = collected()
        for field, value in (('endpoint', 'fixed'), ('checkpoint_sha256', 'F' * 64), ('answer', '바꾼 앞답')):
            changed = copy.deepcopy(events); changed[0][field] = value
            with self.assertRaises(ValueError):
                d.recount(changed, cases, probes, tok, 'parent', who, 'A' * 64)
        changed = copy.deepcopy(events)
        event = next(e for e in changed if e['condition'] == 'ACTUAL_HISTORY')
        event['initial_event_reference']['initial_event_sha256'] = 'F' * 64
        with self.assertRaises(ValueError):
            d.recount(changed, cases, probes, tok, 'parent', who, 'A' * 64)

    def test_partial_duplicate_and_safe_case_forged_not_run_rejected(self):
        probes, cases, tok, who, events, _ = collected()
        with self.assertRaises(d.Pending):
            d.recount(events[:-1], cases, probes, tok, 'parent', who, 'A' * 64)
        duplicate = copy.deepcopy(events); duplicate[1] = duplicate[0]
        with self.assertRaises(ValueError):
            d.recount(duplicate, cases, probes, tok, 'parent', who, 'A' * 64)
        changed = copy.deepcopy(events); changed[3]['record_status'] = d.UNSAFE
        for key in ('answer', 'generation', 'metrics'):
            changed[3].pop(key, None)
        with self.assertRaises(ValueError):
            d.recount(changed, cases, probes, tok, 'parent', who, 'A' * 64)

    def test_boolean_code_label_distribution_and_constant_baselines_are_condition_specific(self):
        probes, cases, tok, who, events, _ = collected()
        report = d.recount(events, cases, probes, tok, 'parent', who, 'A' * 64)
        for condition in d.CONDITIONS:
            values = [e for e in events if e['condition'] == condition and e['family'] == 'boolean']
            expected = {label: sum(e['target'] == label for e in values) for label in ('true', 'false')}
            result = report['boolean_label_diagnostics'][condition]
            self.assertEqual(result['n_expected'], 32); self.assertEqual(result['n_generated'], 32)
            self.assertEqual(result['constant_true_correct_sum'], expected['true'])
            self.assertEqual(result['constant_false_correct_sum'], expected['false'])
            self.assertEqual(result['condition_correct_sum'], 32)
            self.assertEqual(sum(result['actual_label_counts'].values()), 32)

    def test_constant_false_first_answers_not_promoted_to_general_boolean_learning(self):
        probes, cases, tok, who, events, _ = collected(family_answers={'boolean': 'false'})
        result = d.recount(events, cases, probes, tok, 'parent', who, 'A' * 64)['boolean_label_diagnostics']['INITIAL_DIRECT']
        self.assertEqual(result['actual_label_counts'], {'false': 32})
        self.assertEqual(result['condition_correct_sum'], result['constant_false_correct_sum'])
        self.assertIn('not proof of Boolean generalization', result['scope'])


class DecodeObservationTests(unittest.TestCase):
    def emission(self, body=' \n{"x":"내용"}\n ', reason='STOP_SEQUENCE', drop_specials=False, content_ids=None):
        tok = TokenizerFixture(drop_specials=drop_specials)
        messages = d.canonical([dict(role='user', content='주어진 문자열을 그대로 쓰세요.')])
        prefix_ids = tok.encode(d.common.prompt(messages)).ids
        content_ids = tok.encode(body, add_special_tokens=False).ids if content_ids is None else content_ids
        terminal = [4] if reason == 'STOP_SEQUENCE' else [5] if reason == 'EOS' else []
        generated = content_ids + terminal
        full, prefix = tok.decode(prefix_ids + generated), tok.decode(prefix_ids)
        helper_answer = full[len(prefix):].split('<|im_end|>', 1)[0]
        proof = d.encoding(messages, None, tok)
        meta = dict(actual_prompt_sha256=proof['prompt_sha256'], raw_answer_sha256=d.sha(helper_answer),
            prompt_tokens=len(prefix_ids), requested_max_new=128, max_new=128,
            stop_token_sequences=[[4]], eos_token_available=True, stop_at_eos_requested=True,
            stop_at_eos_effective=True, generated_tokens=len(generated), finish_reason=reason,
            matched_stop_sequence=[4] if reason == 'STOP_SEQUENCE' else None)
        calls = [dict(ids=prefix_ids + generated, args=[], kwargs={}, output=full),
                 dict(ids=prefix_ids, args=[], kwargs={}, output=prefix)]
        return NS(tok=tok, messages=messages, body=body, helper_answer=helper_answer, meta=meta, calls=calls,
                  case=dict(messages=messages, encoding=proof))

    def observe(self, fixture):
        return d.observed_emission(fixture.messages, fixture.helper_answer, fixture.meta, fixture.calls, fixture.tok)

    def test_eot_only_boundary_removed_empty_whitespace_and_json_preserved(self):
        for content in ('', ' \n ', '  {"reply":"wrong"}\n '):
            fixture = self.emission(content); before = d.sha([fixture.meta, fixture.calls])
            body, receipt = self.observe(fixture)
            self.assertEqual(body, content); self.assertEqual(receipt['terminal_ids'], [4])
            self.assertEqual(receipt['helper_to_visible_relation'], 'HELPER_ALREADY_BODY')
            self.assertEqual(receipt['original_helper_answer'], fixture.helper_answer)
            self.assertEqual(d.sha([fixture.meta, fixture.calls]), before)
            d.validate_observation(fixture.case, body, fixture.meta, receipt, fixture.tok)

    def test_eos_retained_or_hidden_by_original_decoder_both_keep_original_helper(self):
        for dropped in (False, True):
            fixture = self.emission(' \n5\n ', 'EOS', dropped)
            body, receipt = self.observe(fixture)
            self.assertEqual(body, ' \n5\n '); self.assertEqual(receipt['terminal_ids'], [5])
            self.assertEqual(receipt['original_helper_answer'], fixture.helper_answer)
            self.assertEqual(fixture.helper_answer, body if dropped else body + '<eos>')
            self.assertEqual(receipt['helper_to_visible_relation'], 'HELPER_ALREADY_BODY' if dropped else 'HELPER_RETAINS_AUTHENTICATED_TERMINAL')
            d.validate_observation(fixture.case, body, fixture.meta, receipt, fixture.tok)

    def test_max_new_preserves_all128_content_tokens_and_literal_eos_text(self):
        content = '<eos>' + 'x' * 123
        # 이 경우 '<eos>'는 단일 종료ID가 아니라5개의 관측된 일반문자ID다.
        ids = [1000 + ord(c) for c in content]
        fixture = self.emission(content, 'MAX_NEW', content_ids=ids)
        body, receipt = self.observe(fixture)
        self.assertEqual(body, content); self.assertEqual(receipt['terminal_ids'], [])
        self.assertEqual(receipt['content_tokens'], 128); self.assertFalse(receipt['terminal_removed_from_continuation_ids'])

    def test_middle_nonterminal_special_marker_is_not_removed(self):
        fixture = self.emission(' 앞 <|think|> 중간 <|/think|> 뒤 ')
        body, receipt = self.observe(fixture)
        self.assertEqual(body, fixture.body); self.assertIn('<|think|>', body)
        self.assertEqual(receipt['content_tokens'], len(fixture.tok.encode(fixture.body).ids))

    def test_nonterminal_textual_eot_helper_split_difference_is_error_not_content_repair(self):
        body = 'a<|im_end|>b'
        fixture = self.emission(body, content_ids=[1000 + ord(c) for c in body])
        self.assertEqual(fixture.helper_answer, 'a')
        before = d.sha([fixture.calls, fixture.meta])
        with self.assertRaisesRegex(ValueError, '인증된 마지막 종료경계'):
            self.observe(fixture)
        self.assertEqual(d.sha([fixture.calls, fixture.meta]), before)

    def test_wrong_terminal_prefix_generated_count_and_sha_tamper_rejected(self):
        fixture = self.emission()
        for update in (dict(finish_reason='EOS', matched_stop_sequence=None), dict(generated_tokens=1),
                       dict(actual_prompt_sha256='F' * 64), dict(raw_answer_sha256='F' * 64)):
            changed = copy.deepcopy(fixture); changed.meta.update(update)
            with self.assertRaises(ValueError):
                self.observe(changed)
        changed = copy.deepcopy(fixture); changed.calls[1]['ids'][0] += 1
        with self.assertRaises(ValueError):
            self.observe(changed)
        body, receipt = self.observe(fixture)
        for field in ('prefix_ids_sha256', 'generated_ids_sha256', 'full_ids_sha256', 'message_content_sha256'):
            changed = dict(receipt, **{field: 'F' * 64})
            with self.assertRaises(ValueError):
                d.validate_observation(fixture.case, body, fixture.meta, changed, fixture.tok)

    def test_observer_delegate_returns_unchanged_and_original_helper_metadata_object_preserved(self):
        fixture = self.emission(); observer = d.DecodeObserver(fixture.tok)
        returned = (fixture.helper_answer, fixture.meta); before = d.sha(returned)
        def helper(messages):
            for call in fixture.calls:
                output = observer.decode(call['ids'])
                self.assertEqual(output, call['output'])
            return returned
        body, original_meta, observation = d.observe_helper(helper, observer, fixture.messages)
        self.assertEqual(body, fixture.body); self.assertIs(original_meta, fixture.meta)
        self.assertEqual(d.sha(returned), before); self.assertEqual(len(observer.calls), 2)
        self.assertEqual(observation['generated_ids_sha256'], d.sha(observation['generated_ids']))

    def test_missing_helper_return_or_decode_calls_preserves_error_evidence(self):
        fixture = self.emission(); observer = d.DecodeObserver(fixture.tok)
        def missing(messages):
            for call in fixture.calls:
                observer.decode(call['ids'])
            return None
        with self.assertRaises(d.DecodeObservationError) as error:
            d.observe_helper(missing, observer, fixture.messages)
        self.assertEqual(len(error.exception.evidence['decode_calls']), 2)
        self.assertIsNone(error.exception.evidence['original_helper_answer'])
        with self.assertRaises(d.DecodeObservationError):
            d.observe_helper(lambda messages: (fixture.helper_answer, fixture.meta), observer, fixture.messages)

    def test_adapter_error_appends_unmodified_raw_evidence_then_aborts_without_model_metric(self):
        probes, cases = frozen(); tok = TokenizerFixture(); saved = []
        first = cases[0]; result = response(first['messages'], first['target'], tok)
        observation = result[2]
        evidence = dict(decode_calls=observation['decode_calls'], original_helper_answer=observation['original_helper_answer'],
                        original_helper_generation=result[1], helper_return_type='tuple')
        before = d.sha(evidence)
        with self.assertRaises(d.DecodeObservationError):
            d.collect(cases, probes, tok, 'parent', identity(), 'A' * 64,
                      Mock(side_effect=d.DecodeObservationError('경계 불명', evidence)), saved.append, lambda: None)
        self.assertEqual(len(saved), 1); error = saved[0]
        self.assertEqual(error['record_status'], 'TOOL_ERROR_DECODE_OBSERVATION')
        self.assertFalse(error['model_quality_failure']); self.assertNotIn('metrics', error)
        self.assertNotIn('answer', error); self.assertEqual(d.sha(error['protocol_error']), before)
        self.assertEqual(error['case_id'], first['case_id'])


class SourceBindingTests(unittest.TestCase):
    def run_source(self, fixture):
        with patch.object(d, 'SOURCE_REPORT_SHAS', fixture.report_shas), patch.object(d, 'AUDIT_SHA', fixture.audit_sha), \
             patch.object(d, 'digest', side_effect=fixture.digest), patch.object(d, 'required', side_effect=fixture.required), \
             patch.object(d.common, 'read_shards', side_effect=fixture.read_shards):
            return d.read_source()

    def test_complete_source_reports_manifests_and_four_old128_raws_roundtrip(self):
        fixture = source_documents(); before = d.sha(fixture.documents)
        source, probes, raw = self.run_source(fixture)
        self.assertEqual(d.sha(fixture.documents), before)
        self.assertEqual(d.sha(probes), d.sha(source_fixture()))
        self.assertEqual(source['probe_rows'], 128); self.assertEqual(source['neutral_roots'], 64)
        self.assertEqual(len(raw), 4); self.assertTrue(all(len(rows) == 128 for rows in raw.values()))
        self.assertEqual(source['report_sha256'], fixture.report_shas)
        self.assertTrue(all(v['legacy_gold_history_pass'] == 128 for v in source['historical_gold_history'].values()))
        self.assertFalse(source['source_teacher_packet_accessed'])

    def test_missing_report_and_byte_hash_corruption_rejected_without_model(self):
        fixture = source_documents(); fixture.documents.pop(str(d.SOURCE_EVIDENCE / 'fixed/report.json'))
        with self.assertRaises(d.Pending):
            self.run_source(fixture)
        fixture = source_documents()
        fixture.documents[str(d.SOURCE_EVIDENCE / 'prepare/report.json')]['seed'] = 42
        with self.assertRaises(ValueError):
            self.run_source(fixture)

    def test_source_raw_label_gold_root_duplicate_and_manifest_tamper_rejected(self):
        for field, value in (('label', 'parent'), ('gold', '999999'), ('root', 'F' * 64)):
            fixture = source_documents()
            fixture.shards[str(d.SOURCE_EVIDENCE / 'fixed'), 'answers_child'][0][field] = value
            with self.assertRaises(ValueError):
                self.run_source(fixture)
        fixture = source_documents()
        rows = fixture.shards[str(d.SOURCE_EVIDENCE / 'views'), 'answers_parent']; rows[1] = copy.deepcopy(rows[0])
        with self.assertRaises(ValueError):
            self.run_source(fixture)
        fixture = source_documents()
        fixture.documents[str(d.SOURCE_CORPUS / 'val_probes_shards_manifest.json')]['rows'] = 63
        with self.assertRaises(ValueError):
            self.run_source(fixture)

    def test_partial_old_records_and_probe_rows_do_not_become_wrong_zero(self):
        for directory, stem in ((d.SOURCE_EVIDENCE / 'fixed', 'answers_child'), (d.SOURCE_CORPUS, 'prior_probes')):
            fixture = source_documents(); fixture.shards[str(directory), stem].pop()
            with self.assertRaises(d.Pending):
                self.run_source(fixture)


class CpuAndFingerprintTests(unittest.TestCase):
    def test_state_fingerprint_reuses_exact_helper_without_nn_module(self):
        import torch
        from scripts.diag_p101a_sft_mtp import state_fingerprint
        state = {'w': torch.tensor([1., 2.]), 'mtp_up2': torch.tensor([9.])}
        self.assertEqual(d.state_fingerprint(state), state_fingerprint(NS(state_dict=lambda: state)))
        changed = dict(state, mtp_up2=torch.tensor([10.]))
        self.assertEqual(d.state_fingerprint(state), d.state_fingerprint(changed))
        changed = dict(state, w=torch.tensor([1., 3.]))
        self.assertNotEqual(d.state_fingerprint(state), d.state_fingerprint(changed))

    def test_cpu_checkpoint_inspection_is_three_mock_loads_no_module_optimizer_or_write(self):
        import torch
        from tinylm.config import TMTConfig
        cfg = asdict(TMTConfig(n_prelude=2, n_middle=10, n_coda=2, mlp_group=1,
                              tie_mlp=False, vocab_size=32768, max_seq_len=1024))
        source = dict(endpoints={e: identity(e) for e in d.ENDPOINTS}, corpus_report_sha256='B' * 64)
        payloads = {}
        for endpoint in d.ENDPOINTS:
            payloads[str(d.ROOT / source['endpoints'][endpoint]['checkpoint'])] = dict(cfg=cfg,
                model={'_orig_mod.w': torch.tensor([1., 2.])}, step=2289 if endpoint == 'parent' else 128,
                epoch=4, source_parent_sha256=d.PARENT_SHA, data_report_sha256='B' * 64, tokenizer_sha256=d.TOK_SHA)
        files = {str(d.ROOT / v['checkpoint']): v['checkpoint_sha256'] for v in source['endpoints'].values()}
        writes, guard = [], Mock()
        with patch.object(torch, 'load', side_effect=lambda path, **kw: copy.deepcopy(payloads[str(path)])) as loaded, \
             patch.object(d, 'digest', side_effect=lambda path: files[str(path)]), patch.object(d, 'safe', side_effect=Path), \
             patch.object(Path, 'stat', return_value=NS(st_size=1024)), \
             patch.object(d, 'write', side_effect=lambda path, value: writes.append(value)), redirect_stdout(StringIO()):
            receipts = d.inspect_checkpoints(source, guard)
        self.assertEqual(loaded.call_count, 3); self.assertEqual(len(writes), 3)
        self.assertTrue(all(call.kwargs == dict(map_location='cpu', weights_only=True) for call in loaded.call_args_list))
        self.assertTrue(all(v['nn_modules_constructed'] == 0 and v['optimizers_created'] == 0 and not v['cuda_initialized'] for v in receipts.values()))
        self.assertTrue(all(v['state_tensor_bytes'] == 8 for v in receipts.values()))

    def lifecycle(self, mutate=None):
        probes, _ = frozen(); who = {e: identity(e) for e in d.ENDPOINTS}
        source = dict(endpoints=who, corpus_report_sha256='B' * 64, fixture=True)
        documents, directories, shards = {}, set(), {}
        meta = dict(d.syntax_info(), code_sha256={'owned_fixture': 'C' * 64})
        cp_by_path = {str(d.ROOT / value['checkpoint']): value['checkpoint_sha256'] for value in who.values()}
        def write(path, value):
            if str(path) in documents:
                raise FileExistsError('합성 write-once 충돌')
            documents[str(path)] = copy.deepcopy(value)
        def digest(path):
            if Path(path) == d.TOKENIZER:
                return d.TOK_SHA
            if str(path) in cp_by_path:
                return cp_by_path[str(path)]
            return d.sha(documents[str(path)])
        def inspection(source, guard):
            result = {e: dict(who[e], effective_cfg_sha256='D' * 64, effective_cfg={'fixture': True}) for e in d.ENDPOINTS}
            for endpoint, value in result.items():
                write(d.CORPUS / ('checkpoint_' + endpoint + '.json'), value)
            return result
        class Writer:
            def __init__(self, directory, stem, limit):
                self.stem, self.rows = stem, []
            def append(self, value):
                self.rows.append(copy.deepcopy(value))
            def close(self, lineage):
                shards[self.stem] = self.rows
                manifest = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=len(self.rows),
                    shards=[dict(path=self.stem + '_000000.jsonl', rows=len(self.rows), bytes=100, sha256=d.sha(self.rows))],
                    bytes=100, concat_sha256=d.sha(self.rows), lineage=lineage)
                write(d.CORPUS / (self.stem + '_shards_manifest.json'), manifest)
                return manifest
        def exists(path):
            return str(path) in documents or str(path) in directories
        def mkdir(path, **kwargs):
            if exists(path) and not kwargs.get('exist_ok', False):
                raise FileExistsError('합성 디렉터리 중복')
            directories.add(str(path))
        loader = Mock(return_value=TokenizerFixture())
        with patch.dict(sys.modules, {'tokenizers': NS(Tokenizer=NS(from_file=loader))}), \
             patch.object(d, 'read_source', return_value=(source, probes, {'mock_parent': legacy_records(probes, 'parent')})), \
             patch.object(d, 'info', return_value=meta), patch.object(d, 'inspect_checkpoints', side_effect=inspection), \
             patch.object(d, 'write', side_effect=write), patch.object(d, 'digest', side_effect=digest), \
             patch.object(d, 'required', side_effect=lambda path: copy.deepcopy(documents[str(path)])), \
             patch.object(d, 'ShardWriter', Writer), \
             patch.object(d.common, 'read_shards', side_effect=lambda directory, manifest, stem: copy.deepcopy(shards[stem])), \
             patch.object(Path, 'exists', exists), patch.object(Path, 'mkdir', mkdir), patch.object(Path, 'is_symlink', return_value=False), \
             redirect_stdout(StringIO()):
            self.assertEqual(d.prepare(lambda: None), 0)
            report, actual_probes, actual_cases = d.read_prepared()
            self.assertEqual(len(actual_probes), 128); self.assertEqual(len(actual_cases), 546)
            self.assertEqual(report['cpu_checkpoint_tensor_load_calls'], 3)
            self.assertFalse(report['model_inference_run'])
            loader.assert_called_once_with(str(d.TOKENIZER))
            with self.assertRaises(FileExistsError):
                d.prepare(lambda: None)
            if mutate is not None:
                mutate(documents, shards)
                with self.assertRaises((ValueError, d.Pending)):
                    d.read_prepared()

    def test_full_prepare_read_roundtrip_is_memory_only_with_canonical_source(self):
        self.lifecycle()

    def test_cpu_manifest_case_actual_template_or_checkpoint_metadata_tamper_rejected(self):
        def case(documents, shards):
            shards['cases'][0]['target'] = '오염'
        def template(documents, shards):
            next(c for c in shards['cases'] if c['requires_initial_event'])['messages'] = []
        def manifest(documents, shards):
            documents[str(d.CORPUS / 'cases_shards_manifest.json')]['rows'] = 545
        def cp(documents, shards):
            documents[str(d.CORPUS / 'checkpoint_parent.json')]['initial_core_sha256'] = 'F' * 64
        for mutate in (case, template, manifest, cp):
            self.lifecycle(mutate)


class ReadbackAndPresentationTests(unittest.TestCase):
    def endpoint_fixture(self, endpoint='parent', overrides=None):
        probes, cases, tok, who, events, _ = collected(endpoint, overrides)
        who = dict(who, effective_cfg_sha256='D' * 64)
        metadata = dict(d.syntax_info(), code_sha256={'fixture': 'E' * 64})
        report = dict(source={'fixture': 'immutable'}, checkpoints={endpoint: who}, stdout_selection=d.stdout_selection(probes))
        counts = d.recount(events, cases, probes, tok, endpoint, who, 'A' * 64)
        lineage = dict(metadata, endpoint=endpoint, input_report_sha256='A' * 64,
            checkpoint_sha256=who['checkpoint_sha256'], initial_core_sha256=who['initial_core_sha256'])
        manifest = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=546, lineage=lineage, shards=[{'fixture': True}])
        result = dict(metadata, status='ACTUAL_HISTORY_EVALUATION_ACCOUNTED', endpoint=endpoint,
            checkpoint=who['checkpoint'], checkpoint_sha256=who['checkpoint_sha256'],
            initial_core_sha256=who['initial_core_sha256'], final_core_sha256=who['initial_core_sha256'],
            effective_cfg_sha256=who['effective_cfg_sha256'], core_unchanged=True,
            input_report_sha256='A' * 64, source=report['source'],
            directory=str((d.LOCAL / 'evaluate' / endpoint).relative_to(d.ROOT)),
            all_generation_calls_eval_mode=True, torch_no_grad_during_generation=True,
            model_training_before_cleanup=False, model_training_after_cleanup=False,
            actual_generation_calls=counts['actual_generations'], output=dict(manifest=manifest, counts=counts),
            manifest_sha256=d.sha(manifest))
        return NS(probes=probes, cases=cases, tok=tok, identity=who, events=events, metadata=metadata,
                  report=report, manifest=manifest, result=result)

    def read_endpoint(self, fixture, reader=None):
        reader = d.read_endpoint if reader is None else reader
        endpoint = fixture.result['endpoint']
        def required(path):
            if Path(path).name == endpoint + '_report.json':
                return copy.deepcopy(fixture.result)
            if Path(path).name == 'answers_shards_manifest.json':
                return copy.deepcopy(fixture.manifest)
            raise AssertionError('미예상 실물 경로 읽기')
        def digest(path):
            if Path(path) == d.CORPUS / 'report.json':
                return 'A' * 64
            if Path(path).name == 'answers_shards_manifest.json':
                return d.sha(fixture.manifest)
            if Path(path) == d.ROOT / fixture.identity['checkpoint']:
                return fixture.identity['checkpoint_sha256']
            raise AssertionError('미예상 실물 지문 읽기')
        with patch.object(d, 'info', return_value=fixture.metadata), patch.object(d, 'required', side_effect=required), \
             patch.object(d, 'digest', side_effect=digest), \
             patch.object(d.common, 'read_shards', return_value=copy.deepcopy(fixture.events)):
            return reader(endpoint, fixture.report, fixture.probes, fixture.cases, fixture.tok)

    def test_endpoint_raw546_recount_and_receipt_exact_match_without_model(self):
        fixture = self.endpoint_fixture()
        result, events = self.read_endpoint(fixture)
        self.assertEqual(len(events), 546)
        self.assertEqual(result['output']['counts']['actual_generations'], 546)
        self.assertEqual(d.sha(result), d.sha(fixture.result))

    def test_endpoint_partial_or_corrupt_core_mode_count_and_initial_reference_rejected(self):
        fixture = self.endpoint_fixture()
        for field, value in (('final_core_sha256', 'F' * 64), ('model_training_after_cleanup', True),
                             ('actual_generation_calls', 547)):
            changed = copy.deepcopy(fixture); changed.result[field] = value
            with self.assertRaises(ValueError):
                self.read_endpoint(changed)
        changed = copy.deepcopy(fixture); changed.events.pop()
        with self.assertRaises(d.Pending):
            self.read_endpoint(changed)
        changed = copy.deepcopy(fixture)
        next(e for e in changed.events if e['condition'] == 'ACTUAL_HISTORY')['initial_event_reference']['initial_event_sha256'] = 'F' * 64
        with self.assertRaises(ValueError):
            self.read_endpoint(changed)

    def test_three_endpoint_readback_preserves1638_expected_and_one_explicit_not_run(self):
        p = next(p for p in source_fixture() if p['family'] == 'format')
        fixtures = {e: self.endpoint_fixture(e, {p['probe_id']: '<|im_start|>'} if e == 'views' else None) for e in d.ENDPOINTS}
        first = fixtures['parent']; saved = []; seen = []
        reader = d.read_endpoint
        report = dict(first.report, checkpoints={e: f.identity for e, f in fixtures.items()})
        def endpoint(name, received, probes, cases, tok):
            seen.append(name)
            self.assertIs(received, report)
            return self.read_endpoint(fixtures[name], reader)
        with patch.object(d, 'read_prepared', return_value=(report, first.probes, first.cases)), \
             patch.object(d, 'read_endpoint', side_effect=endpoint), patch.object(d, 'info', return_value=first.metadata), \
             patch.object(d, 'digest', side_effect=lambda path: 'A' * 64 if Path(path) == d.CORPUS / 'report.json' else d.sha(str(path))), \
             patch.object(d, 'write', side_effect=lambda path, value: saved.append(copy.deepcopy(value))), \
             patch.object(Path, 'exists', return_value=False), patch.object(Path, 'is_symlink', return_value=False), \
             patch.dict(sys.modules, {'tokenizers': NS(Tokenizer=NS(from_file=Mock(return_value=first.tok)))}), \
             redirect_stdout(StringIO()):
            self.assertEqual(d.readback(lambda: None), 0)
        self.assertEqual(seen, list(d.ENDPOINTS)); self.assertEqual(len(saved), 1)
        result = saved[0]
        self.assertEqual(result['expected_case_records'], 1638)
        self.assertEqual(result['actual_generation_calls'], 1637); self.assertEqual(result['explicit_not_run'], 1)
        self.assertEqual(result['status'], 'RAW_HISTORY_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION')
        self.assertEqual(result['errors'], 0); self.assertFalse(result['automatic_adoption'])

    def test_stdout_source_fixed16_plus_minimal2_prints_actual_questions_and_answers_without_mutation(self):
        fixture = self.endpoint_fixture(); selection = d.stdout_selection(fixture.probes)
        before = d.sha([fixture.events, fixture.probes, selection])
        with redirect_stdout(StringIO()) as output:
            d.print_examples(fixture.events, fixture.probes, selection, 'parent')
        lines = output.getvalue().splitlines()
        rows = [json.loads(line.split('] ', 1)[1]) for line in lines if line.startswith('[HISTORY_ACTUAL_QUESTION_ANSWERS] ')]
        self.assertEqual(len(rows), 16); self.assertEqual(len(lines), 18)
        self.assertTrue(all(set(row['answers']) == set(d.CONDITIONS) for row in rows))
        self.assertTrue(all(row['first_question'] and row['current_question'] and row['follow_question'] for row in rows))
        self.assertEqual(d.sha([fixture.events, fixture.probes, selection]), before)
        changed = copy.deepcopy(fixture.probes)
        # Source-based selection cannot inspect or depend on answer/score fields.
        for probe in changed:
            probe['answer'] = '틀림'; probe['score'] = 0
        self.assertEqual(d.stdout_selection(changed), selection)
        altered = dict(selection, probe_ids=selection['probe_ids'][1:])
        with self.assertRaises(ValueError):
            d.print_examples(fixture.events, fixture.probes, altered, 'parent')


class EvaluationBoundaryTests(unittest.TestCase):
    def exercise(self, corrupt_mode=False):
        """실제 CUDA/Module 없이 orchestration만 관측하는 합성 mock 경로."""
        import torch
        from scripts import diag_p106b_cpt_unique32k_eval as inference
        from tinylm.config import TMTConfig
        import importlib
        generation = importlib.import_module('tinylm.infer.generate')
        probes, cases, tok, who, events, _ = collected()
        cfg = TMTConfig(); who = dict(who, effective_cfg_sha256=d.sha(asdict(cfg)))
        report = dict(source={'fixture': True}, code_sha256={'fixture': 'B' * 64},
                      checkpoints={'parent': who}, stdout_selection=d.stdout_selection(probes))
        oracle = {d.common.prompt(e['messages']): e for e in events}
        saved, appended, modes = [], [], []
        class ModelFixture:
            training = True
            def eval(self):
                self.training = False
                modes.append('eval')
                return self
            def clear_quant(self):
                self.training = True
                modes.append('clear_quant_switched_to_train')
        model = ModelFixture()
        class Writer:
            def __init__(self, directory, stem, limit):
                self._file = NS(flush=Mock(), fileno=lambda: 99)
            def append(self, value):
                appended.append(copy.deepcopy(value))
            def close(self, lineage):
                return dict(lineage=lineage, rows=len(appended), fixture=True)
        def factory(base, config, observed_tok, max_new):
            def emit(messages):
                self.assertFalse(torch.is_grad_enabled()); self.assertFalse(model.training)
                value = oracle[d.common.prompt(messages)]
                for call in value['decode_observation']['decode_calls']:
                    observed_tok.decode(call['ids'], *call['args'], **call['kwargs'])
                if corrupt_mode:
                    model.training = True
                return value['original_helper_answer'], value['generation']
            return emit
        def digest(path):
            if Path(path) == d.ROOT / who['checkpoint']:
                return who['checkpoint_sha256']
            return 'A' * 64
        with patch.object(d, 'read_prepared', return_value=(report, probes, cases)), \
             patch.object(d, 'read_source', return_value=(report['source'], probes, {})), \
             patch.object(d, 'info', return_value={'code_sha256': report['code_sha256']}), \
             patch.object(d, 'digest', side_effect=digest), patch.object(d, 'state_fingerprint', return_value=who['initial_core_sha256']), \
             patch.object(d, 'write', side_effect=lambda path, value: saved.append(copy.deepcopy(value))), \
             patch.object(d, 'ShardWriter', Writer), patch.object(d.os, 'fsync') as sync, \
             patch.object(Path, 'exists', return_value=False), patch.object(Path, 'is_symlink', return_value=False), \
             patch.object(Path, 'mkdir'), patch('scripts.p106b_gate_runtime.idle_before_gpu'), \
             patch.object(generation, 'load_model', return_value=(model, cfg, 'cuda')) as loader, \
             patch.object(inference, 'emit_function', side_effect=factory), \
             patch.dict(sys.modules, {'tokenizers': NS(Tokenizer=NS(from_file=Mock(return_value=tok)))}), \
             patch.object(torch.cuda, 'reset_peak_memory_stats'), patch.object(torch.cuda, 'max_memory_reserved', return_value=0), \
             patch.object(torch.cuda, 'empty_cache'), redirect_stdout(StringIO()):
            if corrupt_mode:
                with self.assertRaises(ValueError):
                    d.evaluate('parent', lambda: None)
            else:
                self.assertEqual(d.evaluate('parent', lambda: None), 0)
        loader.assert_called_once_with(arch='dense', ckpt_path=str(d.ROOT / who['checkpoint']), device='cuda')
        self.assertFalse(model.training)
        if corrupt_mode:
            self.assertEqual(saved, [])
        else:
            self.assertEqual(len(saved), 1); result = saved[0]
            self.assertEqual(result['actual_generation_calls'], 546); self.assertEqual(len(appended), 546)
            self.assertEqual(sync.call_count, 128)
            self.assertFalse(result['model_training_before_cleanup']); self.assertFalse(result['model_training_after_cleanup'])
            self.assertIn('clear_quant_switched_to_train', modes)
            self.assertTrue(result['torch_no_grad_during_generation']); self.assertTrue(result['core_unchanged'])

    def test_mock_orchestration_every_call_no_grad_eval_and_cleanup_restores_eval(self):
        self.exercise()

    def test_mock_emit_training_mode_change_aborts_before_success_report(self):
        self.exercise(corrupt_mode=True)


class BudgetAndPipelineTests(unittest.TestCase):
    now = datetime(2026, 10, 19, 0, tzinfo=timezone.utc)

    def test_initial_reservation_exact5400_and_cpu600(self):
        proof = d.admission('prepare', None, 1200, {}, now=self.now)
        self.assertEqual(proof['slot_seconds'], 600)
        self.assertEqual(proof['total_study_reserved_active_seconds'], 5400)
        self.assertEqual(proof['future_reserved_seconds'], 4200)
        self.assertEqual(proof['record_reserve_seconds'], 600)

    def test_queue_wait_not_charged_and_latest_absolute_deadline_rechecked(self):
        prior = dict(prepare=dict(status='COMPLETE', active_seconds=20., started_utc='2026-10-18T00:00:00Z'))
        proof = d.admission('evaluate', 'parent', 1200, prior, now=self.now + timedelta(days=1))
        self.assertTrue(proof['prepare_time_is_not_calendar_expiry'])
        with self.assertRaises(d.Pending):
            d.admission('evaluate', 'parent', 1200, prior, now=d.END - timedelta(seconds=4799))

    def test_missing_failed_over_budget_or_duplicate_worker_are_not_executed(self):
        for prior in ({}, {'prepare': dict(status='TOOL_ERROR', active_seconds=1.)},
                      {'prepare': dict(status='COMPLETE', active_seconds=601.)}):
            with self.assertRaises(d.Pending):
                d.admission('evaluate', 'parent', 1200, prior, now=self.now)
        with self.assertRaises(d.Pending):
            d.admission('prepare', None, 1200, {'prepare': dict(status='COMPLETE', active_seconds=1.)}, now=self.now)
        with self.assertRaises(TimeoutError):
            d.admission('prepare', None, 1200, {}, elapsed=600., now=self.now)

    def test_all_modes_check_only_are_source_tokenizer_tensor_model_free(self):
        for mode in d.MODES:
            argv = ['--mode', mode, '--check-only'] + (['--endpoint', 'parent'] if mode == 'evaluate' else [])
            with patch.object(d, 'read_source', side_effect=AssertionError('source 금지')), \
                 patch.object(d, 'info', side_effect=AssertionError('실물 info 금지')), \
                 patch.object(d, 'run_pipeline') as run, redirect_stdout(StringIO()) as out:
                self.assertEqual(d.main(argv), 0)
            run.assert_not_called(); self.assertIn('"checkpoint_tensors_loaded": false', out.getvalue())

    def test_public_execute_calls_pipeline_not_direct_worker(self):
        for mode in d.MODES:
            argv = ['--mode', mode, '--execute'] + (['--endpoint', 'parent'] if mode == 'evaluate' else [])
            with patch.object(d, 'run_pipeline', return_value=0) as pipe, patch.object(d, 'run_worker') as worker:
                self.assertEqual(d.main(argv), 0)
            pipe.assert_called_once(); worker.assert_not_called()

    def test_every_mode_actually_drives_shared_three_phase_adapters(self):
        for mode in d.MODES:
            calls, workers = [], []
            def child(command, **kwargs):
                calls.append(command)
                self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
                self.assertEqual(kwargs['env']['OMP_NUM_THREADS'], '2')
                if '-m' in command:
                    return NS(returncode=0)
                pos = command.index('scripts/diag_p106d_history_scope.py')
                return NS(returncode=d.main(command[pos + 1:]))
            def worker(mode, endpoint, wall):
                workers.append(mode); return 0
            with patch.object(d.subprocess, 'run', side_effect=child), patch.object(d, 'run_worker', side_effect=worker), redirect_stdout(StringIO()) as out:
                self.assertEqual(d.run_pipeline(mode, 'parent' if mode == 'evaluate' else None), 0)
            self.assertEqual(len(calls), 3); self.assertEqual(workers[-1], mode)
            receipt = json.loads(next(line.split('] ', 1)[1] for line in out.getvalue().splitlines() if line.startswith('[EXPERIMENT_FINAL] ')))
            self.assertEqual([p['phase'] for p in receipt['phases']], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
            self.assertTrue(all(p['status'] == 'PASS' for p in receipt['phases']))

    def test_pipeline_hold_error_interrupt_timeout_leave_unrun_receipt(self):
        for codes, expected in (([0, 8], 8), ([9], 9), ([0, 130], 130)):
            with patch.object(d.subprocess, 'run', side_effect=[NS(returncode=c) for c in codes]), redirect_stdout(StringIO()) as out:
                self.assertEqual(d.run_pipeline('prepare'), expected)
            receipt = json.loads(next(line.split('] ', 1)[1] for line in out.getvalue().splitlines() if line.startswith('[EXPERIMENT_FINAL] ')))
            self.assertEqual(receipt['phases'][-1]['status'], 'NOT_RUN')
        with patch.object(d.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['fixture'], 600)), redirect_stdout(StringIO()):
            self.assertEqual(d.run_pipeline('prepare'), 9)

    def test_direct_absolute_help_and_every_check_only_from_other_cwd(self):
        driver = str(d.ROOT / 'scripts/diag_p106d_history_scope.py')
        commands = [['--help']] + [['--mode', mode, '--check-only'] + (['--endpoint', 'parent'] if mode == 'evaluate' else []) for mode in d.MODES]
        for argv in commands:
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', driver, *argv], cwd='/tmp',
                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            if argv != ['--help']:
                self.assertIn('"source_read": false', result.stdout)

    def test_cli_exact_endpoint_and_bounded_wall_mutual_exclusion(self):
        for args in (['--mode', 'prepare', '--execute', '--check-only'], ['--mode', 'evaluate', '--check-only'],
                     ['--mode', 'evaluate', '--endpoint', 'views_best', '--check-only'],
                     ['--mode', 'prepare', '--endpoint', 'parent', '--check-only'],
                     ['--mode', 'prepare', '--max-wall-sec', '1201', '--check-only']):
            with self.assertRaises(SystemExit), patch('sys.stderr', StringIO()):
                d.main(args)

    def test_missing_prepared_blocks_gpu_admission_before_model_import(self):
        with patch.object(d, 'read_prepared', side_effect=d.Pending('준비 미실행')):
            with self.assertRaises(d.Pending):
                d.evaluate('parent', lambda: None)

    def test_active_receipts_bind_returncode_output_and_nonfinite_or_bool_time_rejected(self):
        record = dict(schema=d.VERSION, tag=d.TAG, stage='prepare', status='COMPLETE', returncode=0,
            active_seconds=1., own_code_sha256={p: 'A' * 64 for p in d.OWN_CODE}, output_report_sha256='A' * 64)
        selected = d.EVIDENCE / 'activity_prepare.json'
        def read(value):
            with patch.object(d, 'required', return_value=value), patch.object(d, 'digest', return_value='A' * 64), \
                 patch.object(Path, 'exists', lambda path: Path(path) == selected), patch.object(Path, 'is_symlink', return_value=False):
                return d.activities()
        self.assertEqual(read(record)['prepare']['active_seconds'], 1.)
        for update in (dict(returncode=8), dict(active_seconds=True), dict(active_seconds=float('nan')),
                       dict(output_report_sha256='F' * 64), dict(own_code_sha256={})):
            with self.assertRaises(ValueError):
                read(dict(record, **update))
        for elapsed in (True, float('nan'), float('inf'), -1.):
            with self.assertRaises(ValueError):
                d.admission('prepare', None, 1200, {}, elapsed=elapsed, now=self.now)
        with self.assertRaises(ValueError):
            d.admission('evaluate', 'parent', 1200, {'prepare': dict(status='COMPLETE', active_seconds=float('inf'))}, now=self.now)

    def test_worker_complete_hold_corruption_interrupt_and_timeout_write_distinct_receipts(self):
        admission = d.admission
        for raised, status, expected in ((None, 'COMPLETE', 0), (d.Pending('불충분'), 'HOLD', 8),
                                        (ValueError('오염'), 'TOOL_ERROR', 9), (KeyboardInterrupt(), 'INTERRUPTED', 130),
                                        (TimeoutError('예산초과'), 'TOOL_ERROR', 9)):
            saved = []
            with patch.object(d, 'activities', return_value={}), \
                 patch.object(d, 'admission', side_effect=lambda *a, **kw: admission(*a, **kw, now=self.now)), \
                 patch('scripts.p106b_gate_runtime.wall_limit', side_effect=lambda seconds: nullcontext()), \
                 patch.object(d, 'prepare', side_effect=raised, return_value=0), \
                 patch.object(d, 'digest', return_value='A' * 64), \
                 patch.object(d, 'write', side_effect=lambda path, value: saved.append((path, copy.deepcopy(value)))), \
                 redirect_stdout(StringIO()):
                self.assertEqual(d.run_worker('prepare'), expected)
            self.assertEqual(len(saved), 1); receipt = saved[0][1]
            self.assertEqual(receipt['status'], status); self.assertEqual(receipt['returncode'], expected)
            if expected == 0:
                self.assertIsNotNone(receipt['output_report_sha256'])
            else:
                self.assertIsNone(receipt['output_report_sha256'])
            self.assertGreaterEqual(receipt['active_seconds'], 0)
            self.assertTrue(receipt['wrapper_regression_preflight_excluded'])

    def test_preflight_is_no_write_no_tensor_and_deadline_checked_before_prepared_read(self):
        prepared = Mock(); fake_time = NS(now=lambda tz: self.now)
        with patch.object(d, 'datetime', fake_time), patch.object(d, 'read_prepared', prepared), \
             patch.object(d, 'write', side_effect=AssertionError('쓰기 금지')), \
             patch.object(d, 'inspect_checkpoints', side_effect=AssertionError('tensor금지')), redirect_stdout(StringIO()):
            self.assertEqual(d.run_worker('preflight'), 0)
        prepared.assert_called_once()
        fake_time = NS(now=lambda tz: d.END - timedelta(seconds=599))
        with patch.object(d, 'datetime', fake_time), patch.object(d, 'read_prepared') as read:
            with self.assertRaises(d.Pending):
                d.run_worker('preflight')
        read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
