#!/usr/bin/env python3
"""완료 native/SFT 가중치의 무학습 추론 경로 교차 진단.

원 훈련 route로 CPU strict load한 context를 완전히 종료한 뒤, 다른 추론
route를 명시적으로 연다. 원 학습기/pin/제품 loader를 변경하지 않는다.
대각선은 검산한 기존 원형만 재사용하며 새 네 off-diagonal과 분리한다.
실물 prepare/모델/CP/GPU는 총괄의 명시 실행 worker만 담당한다.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diag_p106b_native_weight_route as n
from scripts.p106b_shards import ShardWriter
from scripts.p106b_stage_receipt import pipeline

TAG = 'p106b_route_cross_v1_s1337'
SCHEMA = 'P106B_ROUTE_CROSS_V1'
MODES = ('source', 'prepare', 'preflight', 'evaluate', 'readback')
ROUTES = ('ternary', 'float')
ENDPOINTS = ('native', 'sft')
ANSWERS, MAX_NEW, USER_CASES, DISPLAY_COUNT = 1694, 64, 6, 12
CACHE = ROOT / 'data_cache' / TAG
RAW = ROOT / 'runs/eval' / TAG
EVIDENCE = ROOT / 'test_result/evidence' / TAG
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
RECORD_RESERVE, MAX_WORKER = 600, 7200
OWN_CODE = ('scripts/diag_p106b_route_cross_readout.py', 'scripts/test_p106b_route_cross_readout.py')
CODE = tuple(sorted(set((*n.CODE, *OWN_CODE))))
Pending = n.Pending
sha = n.sha


def safe(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(ROOT):
        raise ValueError('저장소 안의 정확한 절대 경로가 필요하다')
    if any(part in ('.claude', '.aws') for part in path.relative_to(ROOT).parts):
        raise ValueError('이 단계의 원천 범위 밖이다')
    if path.is_relative_to(ROOT / 'datasets/TinyDataset'):
        raise ValueError('보호 데이터 경로는 접근하지 않는다')
    for current in (path, *path.parents):
        if current.is_symlink(): raise ValueError('심볼릭 링크는 허용하지 않는다')
        if current == ROOT: break
    return path


def exists(path): return safe(path).exists()


def digest(path):
    path = safe(path)
    if not path.is_file(): raise Pending('정확한 선결 파일이 아직 없다: ' + str(path.relative_to(ROOT)))
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest().upper()


def raw_bytes(path):
    path = safe(path)
    if not path.is_file(): raise Pending('선결 원형이 아직 없다')
    if path.stat().st_size >= 20_000_000: raise ValueError('원형은 파일당20MB 미만이어야 한다')
    return path.read_bytes()


def required(path): return json.loads(raw_bytes(path).decode('utf-8'))


def write(path, value):
    path = safe(path)
    if not any(path.is_relative_to(base) for base in (CACHE, RAW, EVIDENCE)):
        raise ValueError('새 교차 진단 namespace에만 쓸 수 있다')
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(data) >= 20_000_000: raise ValueError('단일 JSON은20MB 미만이어야 한다')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(data)


def info():
    pins = {p: digest(ROOT / p) if safe(ROOT / p).is_file() else 'NOT_CREATED' for p in CODE}
    return dict(schema=SCHEMA, tag=TAG, source_tag=n.TAG, code_sha256=pins,
        code_complete=all(v != 'NOT_CREATED' for v in pins.values()),
        endpoints=list(ENDPOINTS), trained_modes=list(ROUTES), inference_modes=list(ROUTES),
        cases_per_cell=ANSWERS, new_off_diagonal_cells=4, new_answers=4 * ANSWERS,
        reused_diagonal_cells=4, reused_answers=4 * ANSWERS, max_new=MAX_NEW,
        precision='FP32_MATH', greedy=True, kv_on=True, mtp=False,
        authority_end_utc=END.isoformat(), record_reserve_seconds=RECORD_RESERVE,
        optimizer_updates=0, checkpoint_writes=0, teacher_calls=0,
        intervention='CPU_STRICT_TRAINED_ROUTE_CLOSED_THEN_OTHER_INFERENCE_ROUTE',
        general_assistant_improvement='NOT_ESTABLISHED')


def authority(now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None: raise ValueError('시간대가 있는 시각이 필요하다')
    remaining = (END - now).total_seconds() - RECORD_RESERVE
    if remaining <= 0: raise Pending('20일17시 전 최종 기록600초 예비에 도달했다')
    return remaining


def phase_key(mode, trained_mode=None, inference_mode=None, endpoint=None):
    if mode not in MODES: raise ValueError('등록된 단계가 필요하다')
    if mode == 'evaluate':
        if (trained_mode not in ROUTES or inference_mode not in ROUTES
                or trained_mode == inference_mode or endpoint not in ENDPOINTS):
            raise ValueError('native/SFT의 서로 다른 훈련→추론 경로를 명시해야 한다')
        return '_'.join((mode, endpoint, trained_mode, 'to', inference_mode))
    if any(v is not None for v in (trained_mode, inference_mode, endpoint)):
        raise ValueError('이 단계는 경로/종점을 사용하지 않으므로 추가 선택자를 거부한다')
    return mode


def slot(endpoint, trained_mode):
    if endpoint not in ENDPOINTS or trained_mode not in ROUTES: raise ValueError('정확한 원 종점이 필요하다')
    return endpoint + '_' + trained_mode


def result_path(key): return EVIDENCE / key / 'report.json'


def tokenizer():
    if digest(n.TOKENIZER) != n.TOKENIZER_SHA: raise ValueError('동결 tokenizer 바이트가 다르다')
    from tokenizers import Tokenizer
    return Tokenizer.from_file(str(n.TOKENIZER))


def read_answers(directory, manifest, count=ANSWERS):
    """선언된 answers shard만 읽고 바이트/행/해시/닫힌 manifest를 검산한다."""
    if (type(count) is not int or count <= 0 or not isinstance(manifest, dict)
            or manifest.get('schema') != 'P106B_WRITE_ONCE_SHARDS_V1'
            or manifest.get('rows') != count or manifest.get('limit_bytes') != 19_999_999
            or not manifest.get('shards')
            or any(p.get('path') != f'answers_{i:06d}.jsonl' for i, p in enumerate(manifest['shards']))):
        raise ValueError('읽기 전 정확한 전체 answers manifest가 필요하다')
    if required(directory / 'answers_shards_manifest.json') != manifest:
        raise ValueError('닫힌 on-disk manifest가 다르다')
    all_hash = hashlib.sha256(); rows = []; total = 0
    for spec in manifest['shards']:
        data = raw_bytes(directory / spec['path'])
        if (not data.endswith(b'\n') or len(data) >= 20_000_000 or len(data) > manifest['limit_bytes']
                or len(data) != spec.get('bytes') or data.count(b'\n') != spec.get('rows')
                or hashlib.sha256(data).hexdigest().upper() != spec.get('sha256')):
            raise ValueError('원형 shard의 바이트/행/해시가 다르다')
        rows.extend(json.loads(line) for line in data.decode('utf-8').splitlines())
        total += len(data); all_hash.update(data)
    if (len(rows) != count or total != manifest.get('bytes')
            or all_hash.hexdigest().upper() != manifest.get('concat_sha256')):
        raise ValueError('원형 전체 집계 또는 concat SHA가 다르다')
    return rows


def prefix_case(case, tok):
    """추론 전 동결 prefix만 검산하며 case의 골드/위치 필드는 참조하지 않는다."""
    from tinylm.chat.serialize import serialize
    prompt = serialize(dict(messages=case['messages']), 'chatml', add_generation_prompt=True)
    ids = tok.encode(prompt).ids
    proof = dict(prompt_sha256=sha(prompt), prompt_ids_sha256=sha(ids), prompt_tokens=len(ids))
    if len(ids) + MAX_NEW > 1024 or any(case.get('encoding', {}).get(k) != v for k, v in proof.items()):
        raise ValueError('같은 동결 prefix와64토큰 생성 예산이 필요하다')
    return dict(inference=dict(prompt=prompt), encoding=dict(ids=ids))


def validate_event(event, case, tok, trained_mode, inference_mode, endpoint, cp_sha, *, diagonal=False):
    _, source, route = n.modules()
    if (event.get('id') != case['id'] or event.get('case_sha256') != sha(case)
            or event.get('endpoint') != endpoint or event.get('checkpoint_sha256') != cp_sha
            or sha(event.get('metrics')) != sha(source.classify_case(case, event.get('answer', '')))):
        raise ValueError('같은 문항/CP/원답의 score 계보가 다르다')
    if diagonal:
        if (trained_mode != inference_mode or event.get('arm') != trained_mode
                or event.get('quantization_route') != route.route_metadata(trained_mode)):
            raise ValueError('대각선 원답은 원래 자기 route의 원형이어야 한다')
    elif (event.get('trained_mode') != trained_mode or event.get('inference_mode') != inference_mode
            or event.get('training_quantization_route') != route.route_metadata(trained_mode)
            or event.get('inference_quantization_route') != route.route_metadata(inference_mode)):
        raise ValueError('교차 원답의 훈련/추론 route를 명시해야 한다')
    from scripts.diag_p106b_span_readout import validate_vocabulary
    validate_vocabulary(dict(answer=event['answer'], generation=event['generation']),
        prefix_case(case, tok), tok)
    if event['generation'].get('max_new') != MAX_NEW: raise ValueError('greedy64 계약이 다르다')


def diagonal(trained_mode, endpoint, training, cases, tok):
    key = n.phase_key('evaluate', trained_mode, endpoint)
    n.completed_activity('evaluate', trained_mode, endpoint)
    report = n.required(n.result_path(key)); _, source, route = n.modules()
    expected = dict(tag=n.TAG, arm=trained_mode, endpoint=endpoint,
        checkpoint_sha256=training['checkpoint_sha256'], core_sha256=training['final_core_sha256'],
        cases_sha256=sha(cases), quantization_route=route.route_metadata(trained_mode))
    if (report.get('status') != 'ACTUAL_ANSWERS_COLLECTED' or report.get('arm') != trained_mode
            or report.get('endpoint') != endpoint or report.get('actual_cases') != ANSWERS
            or report.get('checkpoint_sha256') != training['checkpoint_sha256']
            or report.get('core_before') != training['final_core_sha256']
            or report.get('core_before') != report.get('core_after')
            or report.get('cases_sha256') != sha(cases)
            or report.get('lineage') != expected or report.get('raw_manifest', {}).get('lineage') != expected
            or any(report.get(k) != v for k, v in n.info().items())):
        raise ValueError('원 대각선의 완전한 보고서/원형 계보가 필요하다')
    route.validate_route_metadata(report.get('quantization_route'), trained_mode)
    n.validate_route_receipt(report.get('route', {}), trained_mode)
    n.validate_native32(report.get('native32_fp32'))
    events = read_answers(n.RAW / key, report['raw_manifest'], ANSWERS)
    if [e.get('id') for e in events] != [c['id'] for c in cases]:
        raise ValueError('원 대각선도 같은 ordered1694 전체를 재사용해야 한다')
    for event, case in zip(events, cases):
        validate_event(event, case, tok, trained_mode, trained_mode, endpoint, training['checkpoint_sha256'], diagonal=True)
    summary = source.recount(events, cases, tok)
    return report, events, summary


def source_state():
    """순수 원형 검산만 재사용; n.TAG/CACHE/pin 또는 보고서를 바꾸지 않는다."""
    if not info()['code_complete']: raise ValueError('새 두 코드와 회귀가 완전해야 한다')
    reference, _, cases, _ = n.prepared()
    if len(cases) != ANSWERS or len({c['id'] for c in cases}) != ANSWERS:
        raise ValueError('같은 고유 ordered1694 평가 문항이 필요하다')
    if sha(cases) != reference['binding']['source_cases_sha256']:
        raise ValueError('원 native 연구의 동결 평가 문항 SHA가 다르다')
    tok = tokenizer(); reports = {}; diagonals = {}; links = {}
    for case in cases: prefix_case(case, tok)
    for endpoint in ENDPOINTS:
        for trained in ROUTES:
            training_mode = 'train' if endpoint == 'native' else 'sft'
            training = n.train_report(training_mode, trained)
            report, events, summary = diagonal(trained, endpoint, training, cases, tok)
            key = slot(endpoint, trained); reports[key] = training; diagonals[key] = events
            diagonal_key = n.phase_key('evaluate', trained, endpoint)
            links[key] = dict(checkpoint=str(n.checkpoint(trained, endpoint).relative_to(ROOT)),
                checkpoint_sha256=training['checkpoint_sha256'], core_sha256=training['final_core_sha256'],
                scratch_core_sha256=training['scratch_core_sha256'],
                training_report_sha256=digest(n.result_path(n.phase_key(training_mode, trained))),
                training_activity_sha256=digest(n.EVIDENCE / ('activity_' + n.phase_key(training_mode, trained) + '.json')),
                diagonal_report_sha256=digest(n.result_path(diagonal_key)),
                diagonal_activity_sha256=digest(n.EVIDENCE / ('activity_' + diagonal_key + '.json')),
                diagonal_manifest_sha256=digest(n.RAW / diagonal_key / 'answers_shards_manifest.json'),
                diagonal_raw_manifest=report['raw_manifest'], summary=summary, native32_fp32=report['native32_fp32'])
    if len({r['scratch_core_sha256'] for r in reports.values()}) != 1:
        raise ValueError('모든 종점은 같은 원 native 무작위 초기화에서 와야 한다')
    users = [c['id'] for c in cases if c['lane'] == 'user_seen']
    if len(users) != USER_CASES: raise ValueError('기존 사용자6질문을 빠짐없이 유지해야 한다')
    binding = dict(source_reference_sha256=digest(n.CACHE / 'frozen_reference.json'),
        source_cpu_contract_sha256=digest(n.EVIDENCE / 'cpu_contract.json'),
        source_code_sha256=n.info()['code_sha256'], cases_sha256=sha(cases), endpoints=links)
    return cases, reports, binding, diagonals, tok


def prepare():
    authority()
    if any(exists(base) for base in (CACHE, RAW, EVIDENCE)):
        raise FileExistsError('이전 완료/부분 교차 namespace를 보존한다')
    cases, _, binding, _, _ = source_state()
    display = sorted((c['id'] for c in cases), key=lambda k: sha([TAG, 'DISPLAY', k]))[:DISPLAY_COUNT]
    result = dict(info(), status='CROSS_REFERENCE_PREPARED', binding=binding,
        display_ids=display, user_ids=[c['id'] for c in cases if c['lane'] == 'user_seen'],
        selection='same ordered source1694; display SHA fixed before cross answers',
        models_loaded=0, checkpoint_tensor_loads=0)
    write(CACHE / 'frozen_reference.json', result)
    write(EVIDENCE / 'cpu_contract.json', dict(result, reference_sha256=digest(CACHE / 'frozen_reference.json')))
    write(result_path('prepare'), dict(status='CROSS_REFERENCE_COMPLETE',
        reference_sha256=digest(CACHE / 'frozen_reference.json')))
    return 0


def prepared():
    cases, reports, binding, diagonals, tok = source_state()
    reference = required(CACHE / 'frozen_reference.json')
    if (reference.get('status') != 'CROSS_REFERENCE_PREPARED' or reference.get('binding') != binding
            or any(reference.get(k) != v for k, v in info().items())
            or reference.get('display_ids') != sorted((c['id'] for c in cases), key=lambda k: sha([TAG, 'DISPLAY', k]))[:DISPLAY_COUNT]
            or reference.get('user_ids') != [c['id'] for c in cases if c['lane'] == 'user_seen']
            or required(EVIDENCE / 'cpu_contract.json') != dict(reference, reference_sha256=digest(CACHE / 'frozen_reference.json'))):
        raise ValueError('같은 원형/코드/사전표본의 동결 참조가 필요하다')
    completed_activity('prepare')
    return reference, cases, reports, diagonals, tok


@contextmanager
def cross_runtime(trained_mode, inference_mode, endpoint, training):
    """반사실 전용 이중 context. 일반 float loader guard는 완화하지 않는다."""
    phase_key('evaluate', trained_mode, inference_mode, endpoint)
    runtime, _, route_method = n.modules()
    torch, model, cfg, tok, scratch = runtime.load_runtime('scratch_ntp')
    if (cfg.n_layers != 14 or cfg.dim != 768 or cfg.tie_mlp or cfg.vocab_size != 32768
            or cfg.max_seq_len != 1024 or cfg.grad_checkpoint is not True or cfg.mtp_aux
            or scratch == n.PARENT_CORE or scratch != training['scratch_core_sha256']):
        raise ValueError('원 연구와 같은 CPU scratch cfg/초기화가 필요하다')
    checkpoint = n.checkpoint(trained_mode, endpoint)
    if digest(checkpoint) != training['checkpoint_sha256']: raise ValueError('로드 전 CP 바이트가 다르다')
    saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
    n.validate_payload(saved, cfg, trained_mode, endpoint, n.cp_experiment(training))
    n.validate_cpu_state(model, saved, torch)
    cfg_sha = sha(asdict(cfg)); requires_grad = tuple((k, p.requires_grad) for k, p in model.named_parameters())
    with route_method.weight_route(model, trained_mode) as load_route:
        route_method.load_routed_state(model, saved, trained_mode)
        loaded_core = runtime.state_fingerprint(model)
        if loaded_core != training['final_core_sha256']: raise ValueError('CPU strict load 본체 SHA가 다르다')
        training_metadata = load_route.metadata
    del saved
    if getattr(model, '_p106b_weight_route', None) is not None or sha(asdict(cfg)) != cfg_sha:
        raise ValueError('원 훈련 context는 CUDA 이동 전에 완전히 종료되어야 한다')
    load_receipt = dict(training_mode=trained_mode, inference_mode=inference_mode,
        training_quantization_route=training_metadata, cpu_strict_keys_dtypes_aliases=True,
        loaded_core_sha256=loaded_core, cfg_sha256=cfg_sha,
        training_context_closed_before_cuda=True, inference_context_opened_after_load=True)
    model = model.cuda()
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    try:
        with route_method.weight_route(model, inference_mode) as inference_route:
            try:
                yield torch, model, cfg, tok, inference_route, load_receipt
            finally:
                model.clear_quant()
                if (sha(asdict(cfg)) != cfg_sha
                        or tuple((k, p.requires_grad) for k, p in model.named_parameters()) != requires_grad):
                    raise ValueError('교차 추론이 cfg 또는 requires_grad를 바꾸었다')
    finally:
        del model; gc.collect(); torch.cuda.empty_cache()


def cross_lineage(training, trained, inference, endpoint, cases):
    _, _, route = n.modules()
    return dict(tag=TAG, source_tag=n.TAG, trained_mode=trained, inference_mode=inference,
        endpoint=endpoint, checkpoint_sha256=training['checkpoint_sha256'],
        core_sha256=training['final_core_sha256'], cases_sha256=sha(cases),
        training_quantization_route=route.route_metadata(trained), inference_quantization_route=route.route_metadata(inference))


def evaluate(trained_mode, inference_mode, endpoint):
    authority(); key = phase_key('evaluate', trained_mode, inference_mode, endpoint)
    reference, cases, reports, _, _ = prepared(); training = reports[slot(endpoint, trained_mode)]
    directory = safe(RAW / key)
    if exists(directory) or exists(result_path(key)): raise FileExistsError('기존 부분/완료 원형을 보존한다')
    from scripts.p106b_gate_runtime import idle_before_gpu
    idle_before_gpu(); authority()
    runtime, source, _ = n.modules(); events = []; writer = None; began = time.perf_counter()
    with cross_runtime(trained_mode, inference_mode, endpoint, training) as (torch, model, cfg, tok, route, load_receipt):
        model.eval(); model.set_anneal(1.); model.freeze_quant()
        before = runtime.state_fingerprint(model); cfg_before = sha(asdict(cfg))
        if before != training['final_core_sha256']: raise ValueError('추론 route 전환이 본체를 바꾸었다')
        writer = ShardWriter(directory, 'answers', limit=19_999_999)
        try:
            with torch.no_grad():
                for index, case in enumerate(cases):
                    authority(); route.assert_active()
                    prefix_case(case, tok)
                    answer, generation = source.emit64(model, cfg, tok, case['messages'])
                    event = dict(id=case['id'], case_sha256=sha(case), answer=answer, generation=generation,
                        metrics=source.classify_case(case, answer), trained_mode=trained_mode,
                        inference_mode=inference_mode, endpoint=endpoint, checkpoint_sha256=training['checkpoint_sha256'],
                        training_quantization_route=load_receipt['training_quantization_route'], inference_quantization_route=route.metadata)
                    validate_event(event, case, tok, trained_mode, inference_mode, endpoint, training['checkpoint_sha256'])
                    writer.append(event); events.append(event)
                    if (index + 1) % 128 == 0:
                        print('[ROUTE_CROSS_PROGRESS] ' + json.dumps(dict(key=key, actual=index + 1, expected=ANSWERS)), flush=True)
                    if case['id'] in reference['display_ids'] or case['id'] in reference['user_ids']:
                        print('[ROUTE_CROSS_SAMPLE] ' + json.dumps(dict(key=key, id=case['id'], lane=case['lane'],
                            language=case['language'], family=case['family'], messages=case['messages'], answer=answer,
                            finish_reason=generation['finish_reason'], generated_tokens=generation['generated_tokens']), ensure_ascii=False), flush=True)
            if len(events) != ANSWERS: raise ValueError('새 off-diagonal1694개 전체가 필요하다')
            model.clear_quant(); native32 = n.native_probe(torch, model); after = runtime.state_fingerprint(model)
            if (before != after or sha(asdict(cfg)) != cfg_before
                    or digest(n.checkpoint(trained_mode, endpoint)) != training['checkpoint_sha256']):
                raise ValueError('교차 평가가 본체/cfg/CP를 바꾸었다')
            lineage = cross_lineage(training, trained_mode, inference_mode, endpoint, cases)
            manifest = writer.close(lineage=lineage)
            result = dict(info(), status='OFF_DIAGONAL_ANSWERS_COLLECTED', trained_mode=trained_mode,
                inference_mode=inference_mode, endpoint=endpoint, actual_cases=len(events), cases_sha256=sha(cases),
                reference_sha256=digest(CACHE / 'frozen_reference.json'), checkpoint_sha256=training['checkpoint_sha256'],
                core_before=before, core_after=after, cfg_before_sha256=cfg_before, cfg_after_sha256=sha(asdict(cfg)),
                load_receipt=load_receipt, route=n.route_receipt(model, route), native32_fp32=native32,
                raw_manifest=manifest, lineage=lineage, summary=source.recount(events, cases, tok),
                requires_grad_unchanged=True, models_loaded=1, new_training=0, whole_seconds=time.perf_counter() - began)
            write(result_path(key), result)
        finally:
            # 실패 원형은 flush/close만 하고 완료 manifest를 만들지 않는다.
            stream = getattr(writer, '_file', None)
            if stream is not None and not stream.closed:
                stream.flush(); stream.close(); writer._file = None
    return 0


def validate_cross_report(report, trained, inference, endpoint, training, cases, tok):
    key = phase_key('evaluate', trained, inference, endpoint)
    lineage = cross_lineage(training, trained, inference, endpoint, cases)
    if (report.get('status') != 'OFF_DIAGONAL_ANSWERS_COLLECTED'
            or any(report.get(k) != v for k, v in info().items())
            or report.get('trained_mode') != trained or report.get('inference_mode') != inference
            or report.get('endpoint') != endpoint or report.get('actual_cases') != ANSWERS
            or report.get('cases_sha256') != sha(cases)
            or report.get('reference_sha256') != digest(CACHE / 'frozen_reference.json')
            or report.get('checkpoint_sha256') != training['checkpoint_sha256']
            or report.get('core_before') != training['final_core_sha256'] or report.get('core_after') != report.get('core_before')
            or not n.fingerprint(report.get('cfg_before_sha256'))
            or report.get('cfg_before_sha256') != report.get('cfg_after_sha256')
            or report.get('requires_grad_unchanged') is not True
            or type(report.get('models_loaded')) is not int or report.get('models_loaded') != 1
            or report.get('new_training') != 0 or report.get('lineage') != lineage
            or report.get('raw_manifest', {}).get('lineage') != lineage):
        raise ValueError('같은 CP/코드/cfg의 완전한 교차 평가가 필요하다')
    receipt = report.get('load_receipt', {})
    expected = dict(training_mode=trained, inference_mode=inference,
        training_quantization_route=lineage['training_quantization_route'], cpu_strict_keys_dtypes_aliases=True,
        loaded_core_sha256=training['final_core_sha256'], cfg_sha256=report['cfg_before_sha256'],
        training_context_closed_before_cuda=True, inference_context_opened_after_load=True)
    if receipt != expected: raise ValueError('원훈련 CPU load→context종료→다른 추론 route의 영수증이 필요하다')
    n.validate_route_receipt(report.get('route', {}), inference); n.validate_native32(report.get('native32_fp32'))
    events = read_answers(RAW / key, report['raw_manifest'], ANSWERS)
    if [e.get('id') for e in events] != [c['id'] for c in cases]: raise ValueError('교차 원형의 ordered1694가 다르다')
    for event, case in zip(events, cases):
        validate_event(event, case, tok, trained, inference, endpoint, training['checkpoint_sha256'])
    _, source, _ = n.modules(); summary = source.recount(events, cases, tok)
    if summary != report.get('summary'): raise ValueError('교차 원답의 전체 재집계가 다르다')
    return events, summary


def paired(left, right, cases):
    if [e['id'] for e in left] != [c['id'] for c in cases] or [e['id'] for e in right] != [c['id'] for c in cases]:
        raise ValueError('같은 ordered 문항에서만 대응 비교한다')
    cells = defaultdict(Counter)
    for a, b, case in zip(left, right, cases):
        key = (case['lane'], case.get('split', 'monitor'), case['family'], case['language'],
               str(case.get('wording', 'monitor')), case.get('position', 'monitor'))
        target = cells[key]; target['n'] += 1; target['same_text'] += a['answer'] == b['answer']
        aa, bb = a['metrics']['correct'], b['metrics']['correct']
        if type(aa) is bool and type(bb) is bool:
            target['scored'] += 1; target['right_only'] += bb and not aa; target['left_only'] += aa and not bb
    return [dict(stratum=list(key), **dict(value)) for key, value in sorted(cells.items())]


def readback():
    authority(); reference, cases, reports, diagonals, tok = prepared()
    matrix = {}; summaries = []
    for endpoint in ENDPOINTS:
        for trained in ROUTES:
            link = reference['binding']['endpoints'][slot(endpoint, trained)]
            matrix[endpoint, trained, trained] = diagonals[slot(endpoint, trained)]
            summaries.append(dict(endpoint=endpoint, trained_mode=trained, inference_mode=trained,
                origin='REUSED_DIAGONAL', actual_answers=ANSWERS, source_report_sha256=link['diagonal_report_sha256'],
                summary=link['summary'], native32_fp32=link['native32_fp32']))
            inference = ROUTES[1 - ROUTES.index(trained)]
            completed_activity('evaluate', trained, inference, endpoint)
            events, summary = validate_cross_report(required(result_path(phase_key('evaluate', trained, inference, endpoint))),
                trained, inference, endpoint, reports[slot(endpoint, trained)], cases, tok)
            matrix[endpoint, trained, inference] = events
            summaries.append(dict(endpoint=endpoint, trained_mode=trained, inference_mode=inference,
                origin='NEW_OFF_DIAGONAL', actual_answers=ANSWERS, summary=summary,
                native32_fp32=required(result_path(phase_key('evaluate', trained, inference, endpoint)))['native32_fp32']))
    contrasts = []
    for endpoint in ENDPOINTS:
        for trained in ROUTES:
            contrasts.append(dict(endpoint=endpoint, axis='INFERENCE_FIXED_TRAINED_WEIGHTS', trained_mode=trained,
                left='ternary', right='float', cells=paired(matrix[endpoint, trained, 'ternary'], matrix[endpoint, trained, 'float'], cases)))
        for inference in ROUTES:
            contrasts.append(dict(endpoint=endpoint, axis='TRAINING_FIXED_INFERENCE_ROUTE', inference_mode=inference,
                left='ternary', right='float', cells=paired(matrix[endpoint, 'ternary', inference], matrix[endpoint, 'float', inference], cases)))
    write(result_path('readback'), dict(info(), status='CROSS_MATRIX_RAW_RECOUNT_COMPLETE', summaries=summaries,
        paired_contrasts=contrasts, models_loaded=0, checkpoint_tensor_loads=0,
        fresh_off_diagonal_answers=4 * ANSWERS, reused_diagonal_answers=4 * ANSWERS,
        limitation='native/SFT별 탐색적 같은seed 대응 관측; 범용지능·언어보존·Falcon·75M 성공이 아니다'))
    return 0


def validate_activity(value, key, complete=False):
    if (not isinstance(value, dict) or value.get('schema') != SCHEMA or value.get('tag') != TAG
            or value.get('key') != key or value.get('code_sha256') != info()['code_sha256']
            or not n.finite(value.get('seconds')) or type(value.get('max_wall_sec')) is not int
            or not 60 <= value['max_wall_sec'] <= MAX_WORKER or value['seconds'] > value['max_wall_sec'] + 30
            or type(value.get('returncode')) is not int or type(value.get('complete')) is not bool
            or value['complete'] != (value['returncode'] == 0)
            or type(value.get('worker_pid')) is not int or value['worker_pid'] <= 0
            or value.get('worker_pgid') != value['worker_pid']):
        raise ValueError('같은 코드·자기 PGID의 유한한 실제 activity가 필요하다')
    if phase_key(value['mode'], value.get('trained_mode'), value.get('inference_mode'), value.get('endpoint')) != key:
        raise ValueError('activity 단계가 다르다')
    start, end = (datetime.fromisoformat(value[k]) for k in ('started_at', 'ended_at'))
    if start.tzinfo is None or end.tzinfo is None or end < start or start >= END - timedelta(seconds=RECORD_RESERVE) or end > END:
        raise ValueError('activity의 절대 권한/기록 예비 경계가 다르다')
    if complete and (not value['complete'] or value.get('error_type') is not None): raise Pending('완료 activity가 아직 없다')
    return value


def completed_activity(mode, trained_mode=None, inference_mode=None, endpoint=None):
    key = phase_key(mode, trained_mode, inference_mode, endpoint)
    value = validate_activity(required(EVIDENCE / ('activity_' + key + '.json')), key, True)
    if (value.get('result_sha256') != digest(result_path(key))
            or value.get('reference_sha256') != digest(CACHE / 'frozen_reference.json')):
        raise ValueError('activity/결과/참조 SHA가 다르다')
    return value


def worker(mode, trained_mode, inference_mode, endpoint, max_wall_sec):
    key = phase_key(mode, trained_mode, inference_mode, endpoint)
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= MAX_WORKER: raise ValueError('60~7200초 상한이 필요하다')
    if max_wall_sec > authority(): raise Pending('worker 상한이600초 예비를 뺀 남은 권한보다 크다')
    pid = os.getpid(); pgid = os.getpgid(pid)
    if pgid != pid: raise ValueError('worker는 전용 launcher가 만든 자기 PGID에서만 실행한다')
    if mode in ('source', 'preflight'):
        from scripts.p106b_gate_runtime import wall_limit
        with n.termination_guard(), wall_limit(max_wall_sec):
            source_state() if mode == 'source' else prepared()
            authority()
        print('[ROUTE_CROSS_PREFLIGHT] 동일 원천/네 CP/대각선 원형 검산, 모델0', flush=True); return 0
    activity = EVIDENCE / ('activity_' + key + '.json')
    if exists(activity): raise FileExistsError('기존 activity와 부분 결과를 보존한다')
    metadata = info(); began = time.perf_counter(); started = datetime.now(timezone.utc).isoformat(); code = 9; error = None
    try:
        from scripts.p106b_gate_runtime import wall_limit
        with n.termination_guard(), wall_limit(max_wall_sec):
            if mode == 'prepare': code = prepare()
            elif mode == 'evaluate': code = evaluate(trained_mode, inference_mode, endpoint)
            elif mode == 'readback': code = readback()
            else: raise ValueError('등록된 worker 단계가 필요하다')
        if code == 0 and (not exists(result_path(key)) or metadata['code_sha256'] != info()['code_sha256']):
            raise ValueError('종료0에는 같은 코드의 완전한 결과가 필요하다')
        return code
    except BaseException as exc:
        error = type(exc).__name__
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (Pending, FileNotFoundError, FileExistsError)) else 9
        raise
    finally:
        write(activity, dict(schema=SCHEMA, tag=TAG, key=key, mode=mode, trained_mode=trained_mode,
            inference_mode=inference_mode, endpoint=endpoint, started_at=started, ended_at=datetime.now(timezone.utc).isoformat(),
            seconds=time.perf_counter() - began, max_wall_sec=max_wall_sec, worker_pid=pid, worker_pgid=pgid,
            returncode=code, complete=code == 0, error_type=error, code_sha256=metadata['code_sha256'],
            result_sha256=digest(result_path(key)) if exists(result_path(key)) else None,
            reference_sha256=digest(CACHE / 'frozen_reference.json') if exists(CACHE / 'frozen_reference.json') else None))


def phase_commands(mode, trained_mode, inference_mode, endpoint, max_wall_sec):
    phase_key(mode, trained_mode, inference_mode, endpoint)
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= MAX_WORKER: raise ValueError('60~7200초 상한이 필요하다')
    py = [sys.executable, '-B', '-X', 'utf8']; base = py + ['scripts/diag_p106b_route_cross_readout.py']
    actual = base + ['--mode', mode, '--worker', '--execute', '--max-wall-sec', str(max_wall_sec)]
    if mode == 'evaluate': actual += ['--trained-mode', trained_mode, '--inference-mode', inference_mode, '--endpoint', endpoint]
    prior = 'source' if mode in ('source', 'prepare') else 'preflight'
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_route_cross_readout', '-v']),
        ('PREFLIGHT', base + ['--mode', prior, '--worker', '--execute', '--max-wall-sec', '600']), ('EXECUTE', actual)]


def launch_phase(command, fallback_limit):
    try:
        remaining = authority()
    except Pending:
        return 8
    limit = int(command[command.index('--max-wall-sec') + 1]) if '--max-wall-sec' in command else fallback_limit
    return n.launch(command, min(limit + 120, remaining))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, required=True)
    parser.add_argument('--trained-mode', choices=ROUTES); parser.add_argument('--inference-mode', choices=ROUTES)
    parser.add_argument('--endpoint', choices=ENDPOINTS); parser.add_argument('--max-wall-sec', type=int, default=600)
    parser.add_argument('--worker', action='store_true')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        phases = phase_commands(args.mode, args.trained_mode, args.inference_mode, args.endpoint, args.max_wall_sec)
        if args.check_only:
            print('[ROUTE_CROSS_CHECK_ONLY] ' + json.dumps(info(), ensure_ascii=False), flush=True); return 0
        if args.worker: return worker(args.mode, args.trained_mode, args.inference_mode, args.endpoint, args.max_wall_sec)
        result = pipeline(phases, lambda cmd: launch_phase(cmd, args.max_wall_sec),
            lambda line: print(line, flush=True), experiment='P106B_ROUTE_CROSS_' + phase_key(args.mode, args.trained_mode, args.inference_mode, args.endpoint))
        return result['returncode']
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (Pending, FileNotFoundError, FileExistsError)) else 9
        if code == 9: traceback.print_exc(file=sys.stderr)
        print('[ROUTE_CROSS_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True); return code


if __name__ == '__main__': raise SystemExit(main())
