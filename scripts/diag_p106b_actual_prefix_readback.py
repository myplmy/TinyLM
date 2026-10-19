#!/usr/bin/env python3
"""동결된 실제 continuation SHA와 후보별 TF prefix의 CPU 후행 판독.

이름 raw exact 일치와 token hash를 함께 확인한 부분집합만 인증한다.
공개 execute는 회귀/선결/실행이며 모델·새 생성·학습은 하지 않는다.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import argparse
from collections import Counter, defaultdict
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
import subprocess
import time
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_stage_receipt import pipeline

TAG = 'p106b_subject_role_prefix_v1_s1337'
VERSION = 'P106B_ACTUAL_PREFIX_READBACK_V1'
LOCAL = ROOT / 'test_result/evidence/local' / TAG
EVIDENCE = ROOT / 'test_result/evidence' / TAG
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
ENDPOINTS = ('ce', 'role_only', 'all_axes')
OWN_CODE = ('scripts/diag_p106b_actual_prefix_readback.py', 'scripts/test_p106b_actual_prefix_readback.py')
STATES = ('MATCH', 'MISMATCH', 'NOT_REACHED', 'UNAUTHENTICATED')
QUESTIONS, EDGES, MAIN_CASES, BUNDLES = 512, 1536, 1758, 128
MAX_WALL, MAX_NEW, CONTEXT = 300, 128, 1024


class Pending(RuntimeError):
    """부분·미실행을0점으로 채우지 않는다."""


def dependencies():
    # 실물 worker만 import한다. 공개 help/check-only는 원형/모델 모듈0이다.
    from scripts import diag_p106b_subject_role as main
    return main


def sha(value):
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(body.encode('utf-8')).hexdigest().upper()


def safe(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('해결되지 않은 경로')
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError('저장소 안의 독립 연구 경로 필요') from exc
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError('심볼릭 링크 경로 거부')
        if item == ROOT:
            break
    return path


def digest(path):
    path = safe(path)
    if not path.is_file():
        raise Pending('필요한 완료 파일 누락: ' + str(path.relative_to(ROOT)))
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def required(path):
    path = safe(path)
    if not path.is_file():
        raise Pending('선행 파일 미실행/누락: ' + str(path.relative_to(ROOT)))
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('중복 JSON key')
            value[key] = item
        return value
    def constant(_):
        raise ValueError('비유한 JSON 값')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def write(path, value):
    path = safe(path)
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) >= 20_000_000:
        raise ValueError('소형 보고는20MB 미만이어야 함')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def integer_ids(value, *, nonempty=True):
    return (isinstance(value, list) and (bool(value) or not nonempty)
            and all(type(v) is int and v >= 0 for v in value))


def record_contract(record, prompt_ids, eot):
    """완전한 shifted y만 사용한다. standalone 이름 encode는 하지 않는다."""
    x, y, segments = record.x, record.y, record.segments
    if (not integer_ids(prompt_ids) or type(eot) is not int or eot < 0
            or not integer_ids(x) or not isinstance(y, list) or not isinstance(segments, list)
            or len(x) != len(y) or len(x) != len(segments) or not len(prompt_ids) <= len(x) <= CONTEXT
            or len(prompt_ids) + MAX_NEW > CONTEXT
            or any(type(v) is not int or (v < 0 and v != -100) for v in y)
            or any(type(v) is not int for v in segments)):
        raise ValueError('완전한 정수 shifted Record/prefix 필요')
    positions = [i for i, v in enumerate(y) if v != -100]
    targets = [y[i] for i in positions]
    if (positions != list(range(len(prompt_ids) - 1, len(prompt_ids) - 1 + len(targets)))
            or not 2 <= len(targets) <= MAX_NEW
            or targets[-1] != eot or eot in targets[:-1]
            or x[:len(prompt_ids)] != prompt_ids
            or any(segments[i] != (1 if y[i] != -100 else 0) for i in range(len(y)))
            or any(y[i] != x[i + 1] for i in positions if i + 1 < len(x))):
        raise ValueError('실제 prompt/BPE 경계·내용 전체·단일 EOT/마스크 불일치')
    return dict(positions=positions, targets=targets, content_ids=targets[:-1],
                record_sha256=sha(dict(x=x, y=y, segments=segments)))


def build_questions(main, bundles, tok, frozen_specs, cases, *, expected_bundles=BUNDLES):
    from tinylm.chat.serialize import serialize
    if len(bundles) < expected_bundles:
        raise Pending('완전한 TEST bundle cohort 필요')
    if len(bundles) != expected_bundles:
        raise ValueError('TEST bundle 분모 초과')
    source_cases = [c for c in cases if c.get('lane') == 'subject_role' and c.get('view') == 0]
    if len(source_cases) < 4 * expected_bundles:
        raise Pending('관계 view0 원형 부분 집합')
    if len(source_cases) != 4 * expected_bundles or len({c['id'] for c in source_cases}) != len(source_cases):
        raise ValueError('정확한 관계 view0/질문 ID 분모 필요')
    by_id = {c['id']: c for c in source_cases}; output = []
    if set(frozen_specs) != {b['bundle_id'] for b in bundles}:
        raise ValueError('CPU 동결 bundle/spec 집합 변경')
    eot = tok.token_to_id('<|im_end|>')
    if type(eot) is not int or eot < 0:
        raise ValueError('원자적 원래 EOT ID 필요')
    for bundle in bundles:
        positive, crossed = main.data.encode_bundle(bundle, tok)
        if len(positive) != 4 or len(crossed) != 12:
            raise ValueError('완전한 positive4/cross12 필요')
        records = dict(zip(main.data.POSITIVE_LAYOUT + main.data.CROSSED_LAYOUT, positive + crossed))
        frozen = frozen_specs[bundle['bundle_id']]
        if (frozen.get('record_sha256') != sha([main.record_identity(r) for r in positive + crossed])
                or frozen.get('content_lengths') != [r.targets - 1 for r in positive]):
            raise ValueError('CPU 동결 완전 레코드/길이 지문 변경')
        recomputed = [main.first_divergence_spec(records[q, q], records[q, a], q, a)
                      for q, a in main.data.CROSSED_LAYOUT]
        if sha(recomputed) != sha(frozen.get('branches')):
            raise ValueError('CPU 동결 개별 분기 위치/토큰 변경')
        for qi in range(4):
            case = main.data.evaluation_case(bundle, qi, 0)
            if by_id.get(case['id']) != case:
                raise ValueError('실제 view0의 질문/메타데이터가 frozen source와 다름')
            prompt = serialize(dict(messages=case['messages']), 'chatml', add_generation_prompt=True)
            prefix = list(tok.encode(prompt).ids)
            contracts = [record_contract(records[qi, ai], prefix, eot) for ai in range(4)]
            branches = []
            for branch in recomputed:
                if branch['question_index'] != qi:
                    continue
                ai, d = branch['candidate_index'], branch['branch_index']
                p = len(prefix) - 1 + d
                if (type(d) is not int or d < 0 or branch['correct_predictor_position'] != p
                        or d >= len(contracts[qi]['targets']) or d >= len(contracts[ai]['targets'])
                        or branch['correct_token'] != contracts[qi]['targets'][d]
                        or branch['crossed_token'] != contracts[ai]['targets'][d]
                        or branch['correct_token'] == branch['crossed_token']
                        or records[qi, qi].x[:p + 1] != records[qi, ai].x[:p + 1]):
                    raise ValueError('분기의 동일 causal prefix/shifted 위치 불일치')
                branches.append(dict(branch, tf_prefix_ids=records[qi, qi].x[:p + 1],
                                     tf_prefix_sha256=sha(records[qi, qi].x[:p + 1])))
            if len(branches) != 3 or {b['candidate_index'] for b in branches} != set(range(4)) - {qi}:
                raise ValueError('질문별 정확한 세 음성 edge 필요')
            output.append(dict(case_id=case['id'], bundle_id=bundle['bundle_id'],
                group_id=bundle['parent_group_id'], language=bundle['language'], family=bundle['family'],
                question_index=qi, names=copy.deepcopy(bundle['answers']), eot_id=eot,
                prompt_ids=prefix, prompt_ids_sha256=sha(prefix), prompt_sha256=sha(prompt),
                content_ids=[c['content_ids'] for c in contracts],
                record_sha256=[c['record_sha256'] for c in contracts],
                source_spec_sha256=sha(frozen), case_sha256=sha(case), branches=branches))
    if len({q['case_id'] for q in output}) != 4 * expected_bundles:
        raise ValueError('중복 질문 source ID')
    return output


def authenticate(question, event):
    """새 채점이 아니다. raw exact 이름과 원 generated IDs SHA만 역대조한다.

    MAX의 길이/해시 일치는 기록 token열만 인증하며 finish 의미를 증명하지
    않는다. 동결 complete_record는 내용+EOT<=128이므로 정상 MAX128은 짧은
    canonical 이름에 인증되지 않는다. 짧은 MAX fixture는 경계 시험일 뿐이다.
    """
    raw, meta = event.get('answer'), event.get('generation', {})
    matches = [i for i, name in enumerate(question['names']) if type(raw) is str and raw == name]
    result = dict(status='UNRESOLVED', reason=None, raw_name_matches=matches,
        raw_match_kind='UNIQUE' if len(matches) == 1 else 'AMBIGUOUS' if matches else 'NO_EXACT_MATCH',
        candidate_index=matches[0] if len(matches) == 1 else None,
        finish_reason=meta.get('finish_reason'), generated_ids=None, reconstructed_sha256=None,
        recorded_generated_tokens=meta.get('generated_tokens'), recorded_max_new=meta.get('max_new'),
        max_new_length_observation=('RECORDED_MAX128' if meta.get('finish_reason') == 'MAX_NEW' and type(meta.get('generated_tokens')) is int and meta['generated_tokens'] == MAX_NEW
            else 'RECORDED_NON128_MAX' if meta.get('finish_reason') == 'MAX_NEW' else 'NOT_MAX_NEW'),
        finish_reason_semantics_verified=False, raw_normalization_used=False, quality_score=None)
    if len(matches) != 1:
        result['reason'] = 'AMBIGUOUS_RAW_NAME' if matches else 'NO_EXACT_RAW_NAME'
        return result
    ai, eot = matches[0], question['eot_id']; content = question['content_ids'][ai]
    if not integer_ids(content) or eot in content:
        raise ValueError('CPU source의 실제 내용 ID 목록 변경')
    reason = meta.get('finish_reason')
    if reason == 'STOP_SEQUENCE':
        if (meta.get('matched_stop_sequence') != [eot] or meta.get('stop_token_sequences') != [[eot]]
                or any(type(i) is not int for i in meta.get('matched_stop_sequence', []))):
            result['reason'] = 'UNAUTHENTICATED_EOT_RECEIPT'; return result
        generated = content + [eot]
    elif reason == 'MAX_NEW':
        generated = list(content)
    else:
        result['reason'] = 'EOS_UNRESOLVED' if reason == 'EOS' else 'OTHER_FINISH_UNRESOLVED'
        return result
    if type(meta.get('generated_tokens')) is not int or meta['generated_tokens'] != len(generated):
        result['reason'] = 'GENERATED_LENGTH_MISMATCH'; return result
    expected = meta.get('generated_ids_sha256')
    result['reconstructed_sha256'] = sha(generated)
    if not isinstance(expected, str) or re.fullmatch(r'[0-9A-F]{64}', expected) is None:
        result['reason'] = 'UNAUTHENTICATED_HASH_SCHEMA'; return result
    if expected != result['reconstructed_sha256']:
        result['reason'] = 'CANONICAL_GENERATED_IDS_HASH_MISMATCH'; return result
    result.update(status='AUTHENTICATED', reason='EXACT_RAW_AND_TOKEN_SHA', generated_ids=generated)
    return result


def edge_result(question, authentication, branch, original_edge):
    if any(original_edge.get(k) != v for k, v in branch.items() if k not in ('tf_prefix_ids', 'tf_prefix_sha256')):
        raise ValueError('TF 점수를 다른 edge에 결합할 수 없음')
    if (any(type(original_edge.get(k)) not in (int, float) or not math.isfinite(original_edge[k])
            for k in ('correct_logit', 'crossed_logit', 'gap'))
            or original_edge['gap'] != original_edge['correct_logit'] - original_edge['crossed_logit']):
        raise ValueError('원 TF logit/gap 기록 변경')
    generated = authentication['generated_ids']; d = branch['branch_index']; actual_token = None
    actual_prefix, category = None, None
    if authentication['status'] != 'AUTHENTICATED':
        state = 'UNAUTHENTICATED'
    elif d >= len(generated):
        state = 'NOT_REACHED'
    else:
        actual_token = generated[d]; actual_prefix = question['prompt_ids'] + generated[:d]
        state = 'MATCH' if actual_prefix == branch['tf_prefix_ids'] else 'MISMATCH'
        if state == 'MATCH':
            category = 'GOLD' if actual_token == branch['correct_token'] else 'WRONG' if actual_token == branch['crossed_token'] else 'OTHER'
    return dict(question_index=question['question_index'], candidate_index=branch['candidate_index'],
        branch_index=d, predictor_position=branch['correct_predictor_position'], includes_eot=branch['includes_eot'],
        correct_token=branch['correct_token'], wrong_token=branch['crossed_token'],
        branch_type=branch['branch_type'], status=state, source_edge_sha256=sha(original_edge),
        tf_prefix_sha256=branch['tf_prefix_sha256'], actual_prefix_sha256=sha(actual_prefix) if actual_prefix is not None else None,
        actual_token_at_index=actual_token, selected_token_relation=category,
        source_tf_gap=original_edge['gap'], source_tf_gap_sign='POSITIVE' if original_edge['gap'] > 0 else 'NEGATIVE' if original_edge['gap'] < 0 else 'ZERO',
        tf_gap_at_actual_decision=original_edge['gap'] if state == 'MATCH' else None,
        tf_gap_interpretable_for_this_actual_decision=state == 'MATCH',
        full_vocab_argmax_inferred=False, cached_full_numeric_parity_inferred=False, quality_score=None)


def census(questions, events_by_endpoint, ranks_by_endpoint, guard=lambda: None):
    if (len(questions) < QUESTIONS or set(ENDPOINTS) - set(events_by_endpoint)
            or set(ENDPOINTS) - set(ranks_by_endpoint)):
        raise Pending('세 endpoint/512 view0 원형 미완료')
    if (len(questions) != QUESTIONS or len({q['case_id'] for q in questions}) != QUESTIONS
            or Counter(q['language'] for q in questions) != {'ko': 256, 'en': 256}
            or set(events_by_endpoint) != set(ENDPOINTS) or set(ranks_by_endpoint) != set(ENDPOINTS)):
        raise ValueError('세 endpoint·512 view0 고정 분모 필요')
    question_rows, edges = [], []
    for endpoint in ENDPOINTS:
        actual = {}
        for event in events_by_endpoint[endpoint]:
            if event['id'] in actual:
                raise ValueError('중복 실제답 ID')
            actual[event['id']] = event
        ranks = {r['bundle_id']: r for r in ranks_by_endpoint[endpoint]}
        if len(ranks_by_endpoint[endpoint]) < BUNDLES:
            raise Pending('TF128 원형 부분 집합')
        if len(ranks) != BUNDLES or len(ranks) != len(ranks_by_endpoint[endpoint]):
            raise ValueError('128개 고유 TF 원형 필요')
        for question in questions:
            guard(); event = actual.get(question['case_id'])
            if event is None:
                raise Pending('관계 view0 원답 누락')
            meta = event['generation']
            if (sha(event.get('case')) != question['case_sha256']
                    or meta.get('prompt_ids_sha256') != question['prompt_ids_sha256']
                    or meta.get('prompt_sha256') != question['prompt_sha256']
                    or type(meta.get('prompt_tokens')) is not int
                    or meta.get('prompt_tokens') != len(question['prompt_ids'])
                    or meta.get('precision') != 'FP32_MATH' or type(meta.get('temperature')) not in (int, float)
                    or meta['temperature'] != 0 or type(meta.get('top_k')) is not int or meta['top_k'] != 1
                    or meta.get('use_cache') is not True or meta.get('mtp') is not False
                    or meta.get('candidate_answers_supplied') is not False
                    or type(meta.get('max_new')) is not int or meta['max_new'] != MAX_NEW):
                raise ValueError('실제 생성의 완전 prompt 지문 불일치')
            auth = authenticate(question, event)
            question_rows.append(dict(endpoint=endpoint, case_id=question['case_id'], bundle_id=question['bundle_id'],
                group_id=question['group_id'], language=question['language'], family=question['family'],
                question_index=question['question_index'], source_spec_sha256=question['source_spec_sha256'],
                case_sha256=question['case_sha256'], source_event_sha256=sha(event), raw_answer=event['answer'],
                source_generation=copy.deepcopy(meta), authentication=auth))
            rank = ranks.get(question['bundle_id'])
            if rank is None or rank.get('source_spec_sha256') != question['source_spec_sha256']:
                raise ValueError('질문/TF frozen source 불일치')
            source_edges = {(r['question_index'], r['candidate_index']): r for r in rank['first_divergence']}
            if len(rank['first_divergence']) < 12:
                raise Pending('TF12 edge 부분 집합')
            if len(source_edges) != 12:
                raise ValueError('고유12개 원 TF edge 필요')
            for branch in question['branches']:
                original = source_edges.get((question['question_index'], branch['candidate_index']))
                if original is None:
                    raise Pending('원 TF edge 누락')
                row = edge_result(question, auth, branch, original)
                row.update(endpoint=endpoint, case_id=question['case_id'], bundle_id=question['bundle_id'],
                    group_id=question['group_id'], language=question['language'], family=question['family'],
                    source_rank_event_sha256=sha(rank), source_spec_sha256=question['source_spec_sha256'],
                    authentication_status=auth['status'], unresolved_reason=auth['reason'] if auth['status'] != 'AUTHENTICATED' else None)
                row['edge_id'] = sha([TAG, endpoint, question['case_id'], branch['candidate_index']])
                edges.append(row)
    return question_rows, edges, summarize(question_rows, edges)


def summarize(questions, edges):
    if len(questions) < 3 * QUESTIONS or len(edges) < 3 * EDGES:
        raise Pending('부분 독립판독 원형; 미해결과 누락을 구별')
    if (len(questions) != 3 * QUESTIONS or len(edges) != 3 * EDGES
            or len({(q['endpoint'], q['case_id']) for q in questions}) != len(questions)
            or len({e['edge_id'] for e in edges}) != len(edges)):
        raise ValueError('1536질문/4608고유edge 분모 변경')
    question_index = {(q['endpoint'], q['case_id']): q for q in questions}; linked = defaultdict(list)
    for edge in edges:
        key = (edge.get('endpoint'), edge.get('case_id')); question = question_index.get(key)
        if (question is None or edge.get('question_index') != question['question_index']
                or type(edge.get('candidate_index')) is not int or not 0 <= edge['candidate_index'] < 4
                or edge['candidate_index'] == question['question_index']
                or edge.get('edge_id') != sha([TAG, key[0], key[1], edge['candidate_index']])
                or any(edge.get(k) != question[k] for k in ('bundle_id', 'group_id', 'language', 'family', 'source_spec_sha256'))
                or edge.get('authentication_status') != question['authentication']['status']):
            raise ValueError('상세 edge/실제 질문의 연결 변경')
        if ((edge['status'] == 'UNAUTHENTICATED') != (question['authentication']['status'] == 'UNRESOLVED')
                or question['authentication']['status'] not in ('AUTHENTICATED', 'UNRESOLVED')):
            raise ValueError('인증 상태와 배타적 edge 상태 불일치')
        matched = edge['status'] == 'MATCH'
        if (edge.get('tf_gap_interpretable_for_this_actual_decision') is not matched
                or (edge.get('selected_token_relation') not in ('GOLD', 'WRONG', 'OTHER') if matched else edge.get('selected_token_relation') is not None)
                or (edge.get('tf_gap_at_actual_decision') != edge['source_tf_gap'] if matched else edge.get('tf_gap_at_actual_decision') is not None)):
            raise ValueError('미도달/다른 prefix의 TF 점수를 실제 결정으로 해석할 수 없음')
        linked[key].append(edge['candidate_index'])
    for key, question in question_index.items():
        if sorted(linked[key]) != [i for i in range(4) if i != question['question_index']]:
            raise ValueError('각 질문의 세 배타적 음성 edge 필요')
    def counts(qs, es):
        states = Counter(e['status'] for e in es)
        if set(states) - set(STATES):
            raise ValueError('미등록 edge 상태')
        known = sum(q['authentication']['status'] == 'AUTHENTICATED' for q in qs)
        result = dict(questions=len(qs), unique_raw_name_matches=sum(q['authentication']['raw_match_kind'] == 'UNIQUE' for q in qs),
            authenticated_questions=known, unresolved_questions=len(qs) - known,
            unresolved_reasons=dict(sorted(Counter(q['authentication']['reason'] for q in qs if q['authentication']['status'] != 'AUTHENTICATED').items())),
            edges=len(es), edge_states={k: states[k] for k in STATES},
            selected_token_relations_on_match=dict(sorted(Counter(e['selected_token_relation'] for e in es if e['status'] == 'MATCH').items())),
            eot_edge_states={k: sum(e['includes_eot'] and e['status'] == k for e in es) for k in STATES},
            no_quality_score=True, automatic_adoption=False)
        if sum(result['edge_states'].values()) != len(es) or states['UNAUTHENTICATED'] != 3 * result['unresolved_questions']:
            raise ValueError('배타적 edge/미인증 질문 분모 불일치')
        return result
    endpoints = {}
    for endpoint in ENDPOINTS:
        qs = [q for q in questions if q['endpoint'] == endpoint]; es = [e for e in edges if e['endpoint'] == endpoint]
        if len(qs) != QUESTIONS or len(es) != EDGES:
            raise ValueError('모델별512/1536 분모 불일치')
        endpoints[endpoint] = counts(qs, es)
    return dict(overall=counts(questions, edges), by_endpoint=endpoints,
        by_language={l: counts([q for q in questions if q['language'] == l], [e for e in edges if e['language'] == l]) for l in ('ko', 'en')},
        scope='authenticated exact-name subset only; TF gap is linked only on reached MATCH prefix',
        authentication_limit='hash/length agreement authenticates the recorded list, not finish_reason semantics; short MAX is only a possible boundary fixture',
        no_missing_imputation=True, no_full_vocab_argmax=True, no_numeric_cache_parity_claim=True)


def syntax_info():
    return dict(schema=VERSION, tag=TAG, endpoints=list(ENDPOINTS), questions_per_endpoint=QUESTIONS,
        edges_per_endpoint=EDGES, total_questions=3 * QUESTIONS, total_edges=3 * EDGES,
        raw_exact_matching_only=True, original_generated_ids_hash='compact JSON list[int], UTF8, uppercase SHA256',
        max_worker_seconds=MAX_WALL, readback_invocation_max_actual_worker_seconds=2 * MAX_WALL,
        worker_budget_scope='per public readback invocation; not a cumulative ledger across standalone preflight calls',
        wrapper_regression_and_queue_excluded=True, authority_end_utc=END.isoformat(),
        new_model_calls=0, module_created=False, tensor_checkpoint_loads=0, optimizer_updates=0,
        quality_score=None, automatic_adoption=False)


def own_code():
    return {p: digest(ROOT / p) for p in OWN_CODE}


def bind_source_manifests(main, frozen, bind):
    """이미 소비한 frozen ancestry도 후행 byte 불변 검사에 포함한다."""
    def manifests(directory, values, stem_for_name=lambda name: name):
        if not isinstance(values, dict) or not values:
            raise ValueError('비어 있지 않은 동결 source manifest 집합 필요')
        for name, manifest in values.items():
            stem = stem_for_name(name)
            if not isinstance(stem, str) or re.fullmatch(r'[a-z0-9_]+', stem) is None:
                raise ValueError('정확한 source stem 필요')
            path = directory / (stem + '_shards_manifest.json'); bind(path)
            if required(path) != manifest:
                raise ValueError('source manifest 파일/동결 보고 불일치')
            for part in manifest.get('shards', []):
                if not isinstance(part.get('path'), str) or Path(part['path']).name != part['path']:
                    raise ValueError('source 샤드 basename 필요')
                bind(directory / part['path'], part['sha256'])
    binding = frozen['source_binding']
    path = main.A_CORPUS / 'report.json'; bind(path, binding['a_corpus_report_sha256']); original = required(path)
    bind(main.A_EVIDENCE / 'cpu_contract.json', binding['a_cpu_contract_sha256'])
    manifests(main.A_CORPUS, original['manifests']); manifests(main.CORPUS, frozen['manifests'])
    natural_path = safe(ROOT / original['natural_source_report'])
    bind(natural_path, binding['natural_source_sha256']); natural = required(natural_path)
    if sha(natural['manifests']) != binding['natural_manifest_sha256']:
        raise ValueError('원래 natural source manifest 계보 불일치')
    manifests(natural_path.parent, natural['manifests'],
              lambda name: 'replay' if name == 'replay' else 'natural_' + name)


def raw_shard_paths(directory, manifest, stem):
    """전체 이름을 먼저 닫은 뒤에만 링크 검사와 byteSHA 입력을 허용한다."""
    if stem not in ('answers', 'rank') or not isinstance(manifest, dict):
        raise ValueError('정확한 main raw manifest/stem 필요')
    shards = manifest.get('shards')
    if not isinstance(shards, list) or not shards:
        raise ValueError('비어 있지 않은 main raw shard 목록 필요')
    names, seen = [], set()
    for index, shard in enumerate(shards):
        name = shard.get('path') if isinstance(shard, dict) else None
        if (not isinstance(name, str) or Path(name).is_absolute()
                or '/' in name or '\\' in name or '..' in Path(name).parts
                or name != f'{stem}_{index:06d}.jsonl' or name in seen):
            raise ValueError('main raw shard의 중복 없는 정확한 순서/basename 필요')
        names.append(name); seen.add(name)
    # 잘못된 이름은 safe()의 is_symlink/stat에도 전달하지 않는다.
    return [safe(directory / name) for name in names]


def load_source(guard):
    """총괄 actual worker 전용; 기존 readback(write)는 절대 호출하지 않는다."""
    main = dependencies(); gate_path = main.EVIDENCE / 'readback.json'
    gate = required(gate_path)
    if gate.get('status') != 'RAW_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION':
        raise Pending('완료된 main 세팔 Stage4erR가 선결')
    guard(); frozen, source_rows, bundles = main.read_prepared()
    cases = main.evaluation_cases(source_rows, bundles)
    if len(cases) != MAIN_CASES or len({c['id'] for c in cases}) != MAIN_CASES:
        raise ValueError('main1758case 정확분모 변경')
    receipts = {}
    def bind(path, expected=None):
        value = digest(path)
        if expected is not None and value != expected:
            raise ValueError('동결 byteSHA 변경: ' + str(Path(path).relative_to(ROOT)))
        receipts[str(Path(path).relative_to(ROOT))] = value
        return value
    bind(gate_path); bind(main.CORPUS / 'report.json'); bind(main.EVIDENCE / 'cpu_contract.json')
    bind_source_manifests(main, frozen, bind)
    bind(main.natural_data.TOKENIZER, main.natural_data.TOK_SHA)
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(main.natural_data.TOKENIZER))
    if main.evaluation_proof(cases, tok) != frozen['evaluation_proof']:
        raise ValueError('main 실제 생성prefix/마스크 동결 변경')
    specs = main.rank_specifications(bundles['test'], tok)
    if sha(specs) != sha(frozen['ranking_specifications']) or sha(specs) != frozen['ranking_specifications_sha256']:
        raise ValueError('main CPU record/first-divergence spec 변경')
    questions = build_questions(main, bundles['test'], tok, specs, cases)
    reports, actual, ranks, report_shas, identities = {}, {}, {}, {}, {}
    for endpoint in ENDPOINTS:
        guard(); identity = main.endpoint_identity(endpoint)
        bind(ROOT / identity['checkpoint'], identity['checkpoint_sha256'])
        path = main.EVIDENCE / ('evaluate_' + endpoint) / 'report.json'
        report = required(path); report_shas[endpoint] = bind(path)
        main.validate_evaluation(report, identity, cases, frozen)
        directory = main.LOCAL / ('evaluate_' + endpoint)
        for stem, field in (('answers', 'answer'), ('rank', 'rank')):
            path = directory / (stem + '_shards_manifest.json')
            bind(path, report[field + '_manifest_sha256'])
            if required(path) != report[field + '_manifest']:
                raise ValueError('main raw manifest/report 불일치')
            manifest = report[field + '_manifest']
            paths = raw_shard_paths(directory, manifest, stem)
            for shard, raw_path in zip(manifest['shards'], paths):
                bind(raw_path, shard['sha256'])
        events = main.read_shards(directory, report['answer_manifest'], 'answers', MAIN_CASES)
        rank = main.read_shards(directory, report['rank_manifest'], 'rank', BUNDLES)
        if (main.summarize_answers(events, cases, bundles['test'], tok) != report['summary']
                or main.summarize_ranks(rank, bundles['test'], specs, events) != report['rank_summary']):
            raise ValueError('main 저장답/TF 점수 원형 재집계 불일치')
        reports[endpoint], actual[endpoint], ranks[endpoint], identities[endpoint] = report, events, rank, identity
    expected_gate = dict(main.info(), status='RAW_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION',
        cases_sha256=main.natural_data.sha(cases), source_reports_sha256=report_shas,
        summaries={k: v['summary'] for k, v in reports.items()}, learning_seeds=1,
        model_loaded=False, model_training=False, errors=0, semantic_adoption='USER_REVIEW_REQUIRED')
    for left, right in (('ce', 'role_only'), ('ce', 'all_axes'), ('role_only', 'all_axes')):
        expected_gate[right + '_minus_' + left] = main.paired_graphs(actual[left], actual[right], cases)
    if sha(gate) != sha(expected_gate):
        raise ValueError('세 main 보고/R 결과·대응 조건 재구성 불일치')
    proof = dict(syntax_info(), own_code_sha256=own_code(), source_tag=main.TAG,
        source_code_sha256=main.info()['code_sha256'], source_binding=frozen['source_binding'],
        frozen_corpus_sha256=receipts[str((main.CORPUS / 'report.json').relative_to(ROOT))],
        main_readback_sha256=receipts[str(gate_path.relative_to(ROOT))],
        endpoint_report_sha256=report_shas, endpoint_identities=identities,
        immutable_files=receipts, questions_sha256=sha(questions),
        actual_model_byte_hashes_checked=True, checkpoint_tensor_deserializations=0,
        existing_scores_changed=False, existing_readback_write_called=False)
    recheck(proof); guard()
    return dict(proof=proof, questions=questions, actual=actual, ranks=ranks)


def recheck(proof):
    if proof['own_code_sha256'] != own_code():
        raise ValueError('독립 reader 코드 변경')
    for relative, expected in proof['immutable_files'].items():
        if digest(ROOT / relative) != expected:
            raise ValueError('판독 중 원형/CP byte 변경: ' + relative)


def read_output(directory, manifest, stem, expected):
    if type(manifest.get('rows')) is not int or manifest['rows'] != expected:
        raise ValueError('독립 상세 원형의 정확한 행수 필요')
    if required(directory / (stem + '_shards_manifest.json')) != manifest:
        raise ValueError('독립 상세 manifest 변경')
    for index, part in enumerate(manifest.get('shards', [])):
        if (part.get('path') != stem + '_%06d.jsonl' % index or type(part.get('bytes')) is not int
                or not 0 < part['bytes'] <= 19_999_999):
            raise ValueError('순서 고정·20MB 미만 상세 샤드 필요')
        safe(directory / part['path'])
    verify(directory, manifest)
    rows = []
    for part in manifest['shards']:
        with (directory / part['path']).open(encoding='utf-8') as stream:
            rows.extend(json.loads(line) for line in stream)
    if len(rows) != expected:
        raise ValueError('상세 원형 decoded 행수 불일치')
    return rows


def readback(guard):
    target = safe(EVIDENCE / 'report.json'); directory = safe(LOCAL)
    if target.exists() or directory.exists() or safe(EVIDENCE).exists():
        raise FileExistsError('기존 완료/부분 prefix 판독 보존')
    source = load_source(guard)
    question_rows, edge_rows, summary = census(source['questions'], source['actual'], source['ranks'], guard)
    directory.mkdir(parents=True, exist_ok=False); manifests, hashes = {}, {}
    lineage = dict(tag=TAG, own_code_sha256=source['proof']['own_code_sha256'], source_proof_sha256=sha(source['proof']))
    for stem, rows in (('questions', question_rows), ('edges', edge_rows)):
        writer = ShardWriter(directory, stem, limit=19_999_999)
        for row in rows:
            guard(); writer.append(row)
        manifests[stem] = writer.close(lineage=lineage); verify(directory, manifests[stem])
        hashes[stem] = digest(directory / (stem + '_shards_manifest.json'))
    observed_q = read_output(directory, manifests['questions'], 'questions', 3 * QUESTIONS)
    observed_e = read_output(directory, manifests['edges'], 'edges', 3 * EDGES)
    if (sha(observed_q) != sha(question_rows) or sha(observed_e) != sha(edge_rows)
            or summarize(observed_q, observed_e) != summary):
        raise ValueError('새 상세 원형/해시/분모 왕복 불일치')
    recheck(source['proof']); guard()
    result = dict(syntax_info(), status='ACTUAL_PREFIX_SUBSET_READBACK_COMPLETE', errors=0,
        source=source['proof'], summary=summary, manifests=manifests, manifest_sha256=hashes,
        natural_qa_text_copied=False, actual_readback_run=True, model_or_gpu_run=False)
    write(target, result)
    print('[ACTUAL_PREFIX_READBACK] ' + json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


def failure_status(exc):
    if isinstance(exc, KeyboardInterrupt):
        return 'INTERRUPTED', 130
    if isinstance(exc, (Pending, FileNotFoundError)) or type(exc).__name__ in ('PrerequisitePending', 'PrerequisiteHold'):
        return 'HOLD', 8
    return 'TOOL_ERROR', 9


def authority(seconds, now=None):
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError('유한한 명시 시간예산 필요')
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('시간대 있는 현재시각 필요')
    remaining = (END - now).total_seconds()
    if remaining <= seconds:
        raise Pending('20일17시 절대권한 안에 해당 단계 예산이 부족')
    return remaining


def run_worker(mode, max_wall_sec=MAX_WALL):
    if mode not in ('preflight', 'readback') or type(max_wall_sec) is not int or not 60 <= max_wall_sec <= MAX_WALL:
        raise ValueError('등록 worker와60..300초 필요')
    authority(max_wall_sec); began = time.perf_counter()
    def guard():
        elapsed = time.perf_counter() - began
        if elapsed >= max_wall_sec:
            raise TimeoutError('CPU worker 상한 초과; 부분 원형 보존')
        authority(max_wall_sec - elapsed)
    from scripts.p106b_gate_runtime import wall_limit
    with wall_limit(max_wall_sec):
        if mode == 'preflight':
            load_source(guard); guard()
            print('[ACTUAL_PREFIX_PREFLIGHT] main3/R/source/manifest/CP bytes 검산; 읽기 전용·새판독artifact0·품질판정0', flush=True)
            return 0
        result = readback(guard); guard(); return result


def phase_commands(mode, max_wall_sec=MAX_WALL):
    if mode not in ('preflight', 'readback') or type(max_wall_sec) is not int or not 60 <= max_wall_sec <= MAX_WALL:
        raise ValueError('명시 mode와60..300초 상한 필요')
    py = [sys.executable, '-B', '-X', 'utf8']; driver = py + ['scripts/diag_p106b_actual_prefix_readback.py']
    common = ['--max-wall-sec', str(max_wall_sec), '--worker']
    preflight = driver + ['--mode', 'preflight', *common, '--execute' if mode == 'readback' else '--check-only']
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_actual_prefix_readback', '-v']),
            ('PREFLIGHT', preflight), ('EXECUTE', driver + ['--mode', mode, *common, '--execute'])]


def run_pipeline(mode, max_wall_sec=MAX_WALL):
    actual_workers = 2 if mode == 'readback' else 1
    authority(MAX_WALL + actual_workers * max_wall_sec)
    def launch(command):
        print('[PHASE_COMMAND] ' + json.dumps(command), flush=True)
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='')
        for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
            env[name] = '2'
        cap = MAX_WALL if '-m' in command else max_wall_sec
        print('[PHASE_WALL_LIMIT] ' + json.dumps(dict(child_bound_seconds=cap,
            subprocess_cleanup_grace_seconds=5, regression_wrapper_not_actual_readback_activity='-m' in command)), flush=True)
        try:
            authority(cap)
            return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, timeout=cap + 5, env=env).returncode
        except KeyboardInterrupt:
            return 130
        except Pending:
            return 8
        except (OSError, subprocess.TimeoutExpired):
            return 9
    return pipeline(phase_commands(mode, max_wall_sec), launch, lambda line: print(line, flush=True),
                    experiment='P106B_ACTUAL_PREFIX_' + mode)['returncode']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('preflight', 'readback'), required=True)
    parser.add_argument('--max-wall-sec', type=int, default=MAX_WALL)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        phases = phase_commands(args.mode, args.max_wall_sec)
    except ValueError as exc:
        parser.error(str(exc))
    if args.check_only:
        print('[ACTUAL_PREFIX_CHECK_ONLY] ' + json.dumps(dict(syntax_info(), phases=phases,
            requested_worker_seconds=args.max_wall_sec, phase_bounds_seconds=dict(REGRESSION=MAX_WALL,
                PREFLIGHT=args.max_wall_sec, EXECUTE=args.max_wall_sec),
            requested_actual_worker_budget_seconds=args.max_wall_sec * (2 if args.mode == 'readback' else 1),
            source_read=False, tokenizer_loaded=False, model_bytes_read=False, model_loaded=False), ensure_ascii=False))
        return 0
    try:
        return run_worker(args.mode, args.max_wall_sec) if args.worker else run_pipeline(args.mode, args.max_wall_sec)
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        status, code = failure_status(exc)
        print('[ACTUAL_PREFIX_FINAL] %s%d: %s' % (status, code, str(exc)), flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
