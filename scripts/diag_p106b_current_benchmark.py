#!/usr/bin/env python3
"""현재 여섯 가중치의 고정 공개팩 평가 전용 드라이버.

실물 준비·모델·GPU 실행은 명시된 worker만 한다. 기존 팩/scorer/제품
loader는 수정하지 않으며 Falcon은 검산한 과거 MC 원형만 재사용한다.
선택형 우도는 자유답·실제 대화 능력 또는 구조 단독 인과가 아니다.
"""
from __future__ import annotations

import argparse
from collections import Counter
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
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diag_p106b_native_weight_route as n
from scripts import diag_p106b_broad_recovery as recovery
from scripts import diag_p106b_authorized_benchmark as public
from scripts import diag_p106b_night_falcon as falcon
from scripts import p106b_night_falcon_readback as audit
from scripts import eval_bench_suite as suite
from scripts.p106b_shards import ShardWriter
from scripts.p106b_stage_receipt import pipeline

TAG, SCHEMA = 'p106b_current_benchmark_v1_s1337', 'P106B_CURRENT_BENCHMARK_V1'
CACHE = ROOT / 'data_cache' / TAG
RAW = ROOT / 'runs/eval' / TAG
EVIDENCE = ROOT / 'test_result/evidence' / TAG
MODELS = ('native_ternary', 'native_float', 'sft_ternary', 'sft_float', 'broad_mixed', 'broad_staged')
STUDENTS = MODELS[2:]
ENGLISH = ('piqa', 'hellaswag', 'arc_easy')
GENERATIVE = ('korquad_free', 'gsm8k_free')
TASKS = (*public.TASKS, *GENERATIVE)
MODES = ('source', 'prepare', 'preflight', 'evaluate', 'readback')
CONTEXT, MAX_NEW, ACTIVE_LIMIT, RECORD_RESERVE = 1024, 128, 3600, 600
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
OWN_CODE = ('scripts/diag_p106b_current_benchmark.py', 'scripts/test_p106b_current_benchmark.py')
CODE = tuple(sorted(set((*n.CODE, *recovery.legacy.CODE, *recovery.OWN_CODE, *falcon.CODE,
    *OWN_CODE, 'scripts/p106b_night_falcon_readback.py', 'scripts/p106b_shards.py',
    'scripts/p106b_stage_receipt.py'))))
FIXED = {
    public.FROZEN / 'report.json': 'A2D57C8E2A8F767EBA4D679A1660AB2A85A0B756A713FB0196D013DFB2E3A926',
    falcon.FROZEN / 'report.json': '441E07F5CAB51568DFD70E6CD4A307BC875E0186A89819AAA93C133E51C5DB4F',
    falcon.EVIDENCE / 'english896/report.json': 'B7483D07D4CDDC51F4B76723830C0AE86C7BB440476501DDE8C2E8BB41B4DB2F',
    falcon.evaluation.FROZEN / 'report.json': 'EF7FB9DDD1AC87637A309E6722D9622687412D41ABDC4A8281E3B36F11802096',
}
Pending, sha = n.Pending, n.sha


def safe(path):
    path = Path(path)
    if (not path.is_absolute() or '..' in path.parts or not path.is_relative_to(ROOT)
            or path.is_relative_to(ROOT / 'datasets/TinyDataset')
            or any(p in ('.claude', '.aws') for p in path.relative_to(ROOT).parts)):
        raise ValueError('정확한 승인 저장소 경로만 사용한다')
    for parent in (path, *path.parents):
        if parent.is_symlink(): raise ValueError('심볼릭 링크는 허용하지 않는다')
        if parent == ROOT: break
    return path


def exists(path): return safe(path).exists()


def digest(path):
    path = safe(path)
    if not path.is_file(): raise Pending('선결 파일이 아직 없다: ' + str(path.relative_to(ROOT)))
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest().upper()


def raw_bytes(path):
    path = safe(path)
    if not path.is_file(): raise Pending('선결 원형이 아직 없다')
    if path.stat().st_size >= 20_000_000: raise ValueError('단일 원형은20MB 미만이어야 한다')
    return path.read_bytes()


def required(path): return json.loads(raw_bytes(path).decode('utf-8'))


def write(path, value):
    path = safe(path)
    if not any(path.is_relative_to(base) for base in (CACHE, RAW, EVIDENCE)):
        raise ValueError('새 benchmark namespace 밖에는 쓰지 않는다')
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(payload) >= 20_000_000: raise ValueError('단일 JSON은20MB 미만이어야 한다')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(payload)


def read_shards(directory, manifest, stem, count):
    """선언된 닫힌 shard만 읽으며 과거20MB 상한과 새 엄격상한을 모두 검산한다."""
    if (manifest.get('schema') != 'P106B_WRITE_ONCE_SHARDS_V1' or manifest.get('rows') != count
            or manifest.get('limit_bytes') not in (19_999_999, 20_000_000) or not manifest.get('shards')
            or any(p.get('path') != f'{stem}_{i:06d}.jsonl' for i, p in enumerate(manifest['shards']))):
        raise ValueError('정확한 전체 shard manifest가 필요하다')
    if required(directory / (stem + '_shards_manifest.json')) != manifest:
        raise ValueError('닫힌 manifest가 다르다')
    rows, total, h = [], 0, hashlib.sha256()
    for part in manifest['shards']:
        payload = raw_bytes(directory / part['path'])
        if (not payload.endswith(b'\n') or len(payload) > manifest['limit_bytes']
                or len(payload) != part.get('bytes') or payload.count(b'\n') != part.get('rows')
                or hashlib.sha256(payload).hexdigest().upper() != part.get('sha256')):
            raise ValueError('shard 바이트/행/해시가 다르다')
        rows.extend(json.loads(line) for line in payload.decode('utf-8').splitlines())
        total += len(payload); h.update(payload)
    if len(rows) != count or total != manifest.get('bytes') or h.hexdigest().upper() != manifest.get('concat_sha256'):
        raise ValueError('전체 shard 집계 또는 concat SHA가 다르다')
    return rows


def info():
    pins = {p: digest(ROOT / p) if exists(ROOT / p) else 'NOT_CREATED' for p in CODE}
    return dict(schema=SCHEMA, tag=TAG, code_sha256=pins, code_complete='NOT_CREATED' not in pins.values(),
        models=list(MODELS), requested_rows=9216, expected_scored_rows=9212,
        common_english_mc_rows=768, students_full_public_rows=1920, context=CONTEXT, max_new=MAX_NEW,
        precision='FP32_MATH', no_pmi=True, pmi_computed=False, mc_primary='ARGMIN_SUM_NLL',
        mc_secondary='ARGMIN_SUM_NLL_PER_CHARACTER', separate_prefix_continuation_encode=True,
        greedy=True, kv_on=True, mtp=False, training=False, optimizer_updates=0, checkpoint_writes=0,
        new_falcon_calls=0, cached_falcon_origin='REUSED_OLD_ENGLISH896_MC768_NOT_NEW_EXECUTION',
        actual_history_dialogues_in_denominator=0, active_limit_seconds=ACTIVE_LIMIT,
        authority_end_utc=END.isoformat(), record_reserve_seconds=RECORD_RESERVE,
        contamination='NOT_AUDITED_ALL_PRETRAINING', official_harness_equivalence=False,
        cross_model_ce_comparable=False, architecture_only_causality=False,
        general_assistant_quality='NOT_ESTABLISHED')


def phase_key(mode, model_id=None):
    if mode not in MODES: raise ValueError('등록된 단계가 필요하다')
    if mode == 'evaluate':
        if model_id not in MODELS: raise ValueError('정확한 여섯 model-id 중 하나가 필요하다')
        return mode + '_' + model_id
    if model_id is not None: raise ValueError('이 단계에는 model-id를 넣지 않는다')
    return mode


def result_path(key): return EVIDENCE / key / 'report.json'


def authority(now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None: raise ValueError('시간대 있는 시각이 필요하다')
    remaining = (END - now).total_seconds() - RECORD_RESERVE
    if remaining <= 0: raise Pending('20일17시 전 기록600초 예비에 도달했다')
    return remaining


def tokenizer():
    if digest(public.TOKENIZER) != public.TOKENIZER_SHA: raise ValueError('동결 chat32 tokenizer가 다르다')
    from tokenizers import Tokenizer
    return Tokenizer.from_file(str(public.TOKENIZER))


def row_id(row): return row['task'] + '#' + str(row['index'])


def cohort(rows, model_id):
    phase_key('evaluate', model_id)
    return list(rows) if model_id in STUDENTS else [row for row in rows if row['task'] in ENGLISH]


def eligibility(row, tok):
    if row['kind'] == 'mc':
        from scripts.diag_p106b_night_eval import mc_skip_reason
        return mc_skip_reason(row['item'], tok)
    size = len(tok.encode(row['prompt']).ids)
    if size != row['prompt_tokens']: raise ValueError('원 공개 생성 prefix 토큰 수가 다르다')
    return 'full_prompt_plus128_exceeds1024' if size + MAX_NEW > CONTEXT else None


def read_public(tok):
    for path, expected in FIXED.items():
        if digest(path) != expected: raise ValueError('고정 공개/Falcon 원 보고서 SHA가 다르다')
    report = required(public.FROZEN / 'report.json')
    if (report.get('status') != 'FROZEN_CPU_STRICT_LOAD_PASSED'
            or report.get('driver_sha256') != digest(ROOT / 'scripts/diag_p106b_authorized_benchmark.py')
            or report.get('tokenizer_sha256') != public.TOKENIZER_SHA or report.get('context') != CONTEXT
            or report.get('max_new') != MAX_NEW):
        raise ValueError('원 공개팩 코드/tokenizer/길이 계약이 다르다')
    rows = read_shards(public.FROZEN, report['manifest'], 'cases', 1920)
    expected = dict.fromkeys(public.TASKS, 256); expected.update(dict.fromkeys(GENERATIVE, 64))
    if (dict(Counter(r['task'] for r in rows)) != expected or len({row_id(r) for r in rows}) != 1920
            or any(r['kind'] != ('gen' if r['task'] in GENERATIVE else 'mc') for r in rows)):
        raise ValueError('원래 고유1920 문항과 과제별 분모가 필요하다')
    exclusions = {row_id(r): eligibility(r, tok) for r in rows}
    excluded = [key for key, reason in exclusions.items() if reason is not None]
    if len(excluded) != 1 or not excluded[0].startswith('korquad_free#'):
        raise ValueError('원래 KorQuAD 한 행 길이 제외만 허용한다')
    return report, rows, exclusions


def validate_cached_mc(rows, events, public_rows, tok):
    """동일768 item/ID와 저장 점수 재선택을 검산한다. 새 로짓 계산은 없다."""
    original = [r for r in rows if r['task'] in ENGLISH]
    actual = [e for e in events if e.get('task') in ENGLISH]
    expected = [r for r in public_rows if r['task'] in ENGLISH]
    if (len(original) != 768 or len(actual) != 768 or len(expected) != 768
            or len({r['case_id'] for r in original}) != 768
            or [row_id(r) for r in original] != [row_id(r) for r in expected]
            or [e.get('case_id') for e in actual] != [r['case_id'] for r in original]):
        raise ValueError('Falcon과 동일한 ordered 영어MC768 전체가 필요하다')
    outcomes = []
    for old, event, current in zip(original, actual, expected):
        check = dict(old); check.pop('case_id')
        source = dict(check); source.pop('expected_skip', None)
        if (sha([old['task'], old['index'], check]) != old['case_id'] or source != current
                or old.get('expected_skip') is not None or event.get('skipped') is not False):
            raise ValueError('Falcon 원형/source item 또는 적격성 계약이 다르다')
        outcomes.append(audit._mc(event, old, tok))
    counts = {task: sum(o['correct'] for o in outcomes if o['task'] == task) for task in ENGLISH}
    if counts != dict(piqa=170, hellaswag=89, arc_easy=139): raise ValueError('원 Falcon398/768 재집계가 다르다')
    return outcomes


def cached_falcon(public_rows):
    proof = required(falcon.FROZEN / 'report.json')
    report = required(falcon.EVIDENCE / 'english896/report.json')
    if (proof.get('status') != 'FALCON_CPU_STRICT_FROZEN'
            or required(falcon.EVIDENCE / 'cpu_contract.json') != proof
            or report.get('status') != 'FALCON_REFERENCE_COMPLETE' or report.get('cost') is not False
            or report.get('input_sha256') != FIXED[falcon.FROZEN / 'report.json']
            or report.get('body_unchanged') is not True or report.get('runtime') != proof.get('runtime')
            or report.get('asset_sha256') != proof.get('asset_sha256')
            or report.get('initial_core_sha256') != proof.get('initial_core_sha256')
            or report.get('code_sha256') != proof.get('code_sha256')
            or report.get('directory') != str((falcon.LOCAL / 'english896').relative_to(ROOT))
            or proof.get('source_report_sha256') != FIXED[falcon.evaluation.FROZEN / 'report.json']):
        raise ValueError('완료한 같은 Falcon 원 보고서/원형 계보가 필요하다')
    for relative, pin in report['code_sha256'].items():
        if digest(ROOT / relative) != pin: raise ValueError('과거 Falcon scorer/producer 코드가 달라졌다')
    rows = read_shards(falcon.FROZEN, proof['manifest'], 'cases', 896)
    events = read_shards(falcon.LOCAL / 'english896', report['manifest'], 'answers', 896)
    for name in ('config.json', 'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json'):
        if digest(falcon.ASSET / name) != proof['asset_sha256'][name]:
            raise ValueError('과거 Falcon tokenizer 설정/바이트가 달라졌다')
    # 가중치/모델이 아니라 원래 local tokenizer와 no-BOS adapter만 재사용한다.
    from transformers import AutoTokenizer
    tok = falcon.Tokens(AutoTokenizer.from_pretrained(str(falcon.ASSET), local_files_only=True, trust_remote_code=False))
    outcomes = validate_cached_mc(rows, events, public_rows, tok)
    for task in ENGLISH:
        values = [o for o in outcomes if o['task'] == task]; saved = report['summary'][task]
        if (saved['n'] != len(values) or saved['skipped'] != 0
                or saved['correct'] != sum(o['correct'] for o in values)
                or saved['char_norm_correct'] != sum(o['char_norm_correct'] for o in values)):
            raise ValueError('Falcon 저장 집계와 실제 MC 원답이 다르다')
    receipt = dict(origin='REUSED_OLD_ENGLISH896_MC768_NOT_NEW_EXECUTION', new_model_calls=0,
        report_sha256=FIXED[falcon.EVIDENCE / 'english896/report.json'],
        frozen_sha256=FIXED[falcon.FROZEN / 'report.json'], raw_manifest_sha256=sha(report['manifest']),
        common_ids_sha256=sha([r['id'] for r in outcomes]), summary={task: report['summary'][task] for task in ENGLISH},
        reused_rows=768, excluded_other_formats=128, independent_gsm_problems_not128=True)
    return receipt, outcomes


def model_reference(model_id):
    """모델을 만들지 않고 원 완료보고·원 훈련 update 검산기를 재사용한다."""
    phase_key('evaluate', model_id)
    if not model_id.startswith('broad_'):
        endpoint, arm = model_id.split('_')
        report = n.train_report('train' if endpoint == 'native' else 'sft', arm)
        checkpoint = n.checkpoint(arm, endpoint)
        metadata = dict(family='native_weight_route', endpoint=endpoint, arm=arm,
            route=report['quantization_route'], trained_tag=n.TAG,
            training_report=str(n.result_path(n.phase_key('train' if endpoint == 'native' else 'sft', arm)).relative_to(ROOT)))
    else:
        arm = model_id.removeprefix('broad_'); b = recovery.legacy
        with recovery.runtime_scope():
            recovery.validate_equivalence()
            frozen, course = b.required(b.CACHE / 'frozen.json'), b.required(b.CACHE / 'course.json')
            if (any(frozen.get(k) != v for k, v in b.info().items()) or b.UPDATES != 352
                    or course.get('updates') != 352 or course.get('groups_per_pass') != 176
                    or b.digest(b.CACHE / 'course.json') != frozen['course_report_sha256']):
                raise ValueError('동결 broad v2/352update/2pass course가 필요하다')
            # 원 검산기는 group 통계와 순서만 사용한다. train consumer 재열거는 하지 않는다.
            bundle = dict(course=SimpleNamespace(schedules=course['schedules'], report=course))
            b.completed_activity('train', arm); report = b.read_training(arm, cost=False, bundle=bundle)
            checkpoint = b.checkpoint(arm)
            if digest(b.monitor.base.PARENT) != b.monitor.base.PARENT_SHA:
                raise ValueError('원 broad 부모 체크포인트 바이트가 다르다')
            metadata = dict(family='broad_v2', endpoint='sft', arm=arm, route='PRODUCT_TERNARY',
                trained_tag=recovery.TAG, parent_checkpoint_sha256=b.monitor.base.PARENT_SHA,
                parent_core_sha256=b.monitor.base.PARENT_CORE,
                training_report=str((b.EVIDENCE / ('train_' + arm) / 'report.json').relative_to(ROOT)))
    if digest(checkpoint) != report['checkpoint_sha256']: raise ValueError('원 완료 CP 바이트가 다르다')
    return dict(metadata, model_id=model_id, checkpoint=str(checkpoint.relative_to(ROOT)),
        checkpoint_sha256=report['checkpoint_sha256'], core_sha256=report['final_core_sha256'],
        training_report_sha256=digest(ROOT / metadata['training_report']), tokenizer_sha256=public.TOKENIZER_SHA)


def display_ids(rows):
    return [row_id(row) for task in TASKS for row in
        sorted((r for r in rows if r['task'] == task), key=lambda r: sha([TAG, row_id(r), sha(r)]))[:2]]


def source_state():
    if not info()['code_complete']: raise ValueError('신설 두 코드와 회귀가 완전해야 한다')
    tok = tokenizer(); report, rows, exclusions = read_public(tok)
    reference, outcomes = cached_falcon(rows)
    models = {model_id: model_reference(model_id) for model_id in MODELS}
    binding = dict(public_report_sha256=FIXED[public.FROZEN / 'report.json'], cases_sha256=sha(rows),
        ordered_ids_sha256=sha([row_id(r) for r in rows]), exclusions=exclusions,
        public_manifest_sha256=sha(report['manifest']), models=models, cached_falcon=reference)
    return binding, rows, tok, outcomes


def prepare():
    if exists(CACHE) or exists(result_path('prepare')): raise FileExistsError('기존 또는 부분 준비를 보존한다')
    binding, rows, _, _ = source_state()
    reference = dict(info(), status='CURRENT_BENCHMARK_CPU_FROZEN', binding=binding,
        display_ids=display_ids(rows), models_loaded=0, checkpoint_tensor_loads=0, new_model_calls=0)
    write(CACHE / 'frozen_reference.json', reference); write(result_path('prepare'), reference)
    print('[CURRENT_BENCHMARK_PREPARE] 모델0, 요청9216·예상채점9212 동결', flush=True)
    return 0


def prepared():
    reference = required(CACHE / 'frozen_reference.json')
    if (reference.get('status') != 'CURRENT_BENCHMARK_CPU_FROZEN'
            or any(reference.get(k) != v for k, v in info().items())
            or required(result_path('prepare')) != reference):
        raise ValueError('같은 코드의 완전한 준비 영수증이 필요하다')
    completed_activity('prepare')
    binding, rows, tok, outcomes = source_state()
    if sha(binding) != sha(reference['binding']) or reference['display_ids'] != display_ids(rows):
        raise ValueError('동결 원형/CP/캐시/표본 선택이 다르다')
    return reference, rows, tok, outcomes


def validate_broad_payload(saved, model, cfg, arm, torch):
    """원 evaluate의 strict 계약에 CPU dtype/공유관계 사전 거부를 추가한다."""
    from tinylm.infer.generate import _strip
    if (saved.get('broad_curriculum') != dict(tag=recovery.TAG, arm=arm, passes=2, objective='token')
            or saved.get('cfg') != asdict(cfg) or saved.get('step') != 352
            or saved.get('tokenizer_sha256') != public.TOKENIZER_SHA or 'quantization_route' in saved):
        raise ValueError('정확한 broad v2 child cfg/recipe/tokenizer만 불러온다')
    state = _strip(saved['model'])
    if len(state) != len(saved['model']): raise ValueError('compile 접두사 제거 뒤 state 키 충돌을 허용하지 않는다')
    n.validate_cpu_state(model, dict(model=state), torch)
    model.load_state_dict(state, strict=True)


@contextmanager
def model_runtime(model_id, reference):
    """native는 정식 trained route, broad는 원 v2 evaluate loader로 분리한다."""
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    if reference['model_id'] != model_id: raise ValueError('동결 model-id가 다르다')
    if reference['family'] == 'native_weight_route':
        with n.routed_runtime(reference['arm'], reference['endpoint']) as values:
            torch, model, cfg, tok, _, route = values
            model.eval(); model.set_anneal(1.); model.freeze_quant(); route.assert_active()
            if state_fingerprint(model) != reference['core_sha256']: raise ValueError('정식 native route 본체가 다르다')
            yield torch, model, cfg, tok, route
    elif reference['family'] == 'broad_v2':
        b = recovery.legacy
        with recovery.runtime_scope():
            recovery.validate_equivalence()
            torch, model, cfg, tok, initial = b.monitor.base.load_parent()
            try:
                if initial != b.monitor.base.PARENT_CORE: raise ValueError('정확한 원 broad 부모가 필요하다')
                saved = torch.load(safe(ROOT / reference['checkpoint']), map_location='cpu', weights_only=True)
                validate_broad_payload(saved, model, cfg, reference['arm'], torch); del saved
                if state_fingerprint(model) != reference['core_sha256']: raise ValueError('strict broad 본체가 다르다')
                model = model.cuda(); model.eval(); model.freeze_quant()
                torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
                yield torch, model, cfg, tok, None
            finally:
                model.clear_quant(); del model; gc.collect(); torch.cuda.empty_cache()
    else: raise ValueError('generic loader를 허용하지 않는다')


def mc_encoding(row, tok):
    pairs = audit._pairs(row['item'])
    boundaries = [(tok.encode(p).ids if p else tok.encode('\n').ids[:1], tok.encode(c).ids) for p, c in pairs]
    return dict(prompt_sha256=sha(pairs), separate_boundaries_sha256=sha(boundaries),
        prefix_tokens=[len(p) for p, _ in boundaries], continuation_tokens=[len(c) for _, c in boundaries])


class FP32Forward:
    """기존 MATH wrapper를 유지하고 실제 입력 장치의 바깥 autocast도 닫는다."""
    def __init__(self, model):
        from scripts.diag_p101a_mtp_parity import PrecisionForward
        self.wrapped = PrecisionForward(model, 'fp32_math')

    def __getattr__(self, name): return getattr(self.wrapped, name)

    def __call__(self, x, *args, **kwargs):
        import torch
        with torch.autocast(x.device.type, enabled=False):
            value = self.wrapped(x, *args, **kwargs)
        logits = value[0] if isinstance(value, tuple) else value
        if logits.dtype != torch.float32: raise ValueError('실제 forward 로짓은 FP32여야 한다')
        return value


def emit_public(model, cfg, tok, prompt):
    """원 public greedy128과 답 추출을 유지하며 실제 ID/원 body를 따로 보존한다."""
    from scripts.diag_p101a_mtp_parity import CaptureTokens
    from tinylm.infer.generate import sample
    ids = tok.encode(prompt).ids
    if len(ids) + MAX_NEW > CONTEXT: raise ValueError('원 prefix를 자르지 않는다')
    eot = tok.encode('<|im_end|>').ids
    if eot != [tok.token_to_id('<|im_end|>')]: raise ValueError('동결 단일 EOT가 필요하다')
    capture = CaptureTokens(tok)
    decoded, generation = sample(FP32Forward(model), cfg, capture, prompt,
        max_new=MAX_NEW, temperature=0., top_k=1, device='cuda', return_metadata=True,
        logits_last_only=True, use_cache=True, mtp_tokens=1, stop_token_sequences=[eot])
    full = capture.decoded_ids
    if not isinstance(full, list) or full[:len(ids)] != ids: raise ValueError('실제 sampler의 전체 토큰이 필요하다')
    new = full[len(ids):]; prefix = tok.decode(ids)
    if not decoded.startswith(prefix): raise ValueError('원 public prefix decode가 보존되어야 한다')
    answer = decoded[len(prefix):].split('<|im_end|>', 1)[0].strip()
    terminal = eot if generation['finish_reason'] == 'STOP_SEQUENCE' else [tok.token_to_id('<eos>')] if generation['finish_reason'] == 'EOS' else []
    content = new[:-len(terminal)] if terminal else new
    generation.update(precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False,
        requested_max_new=MAX_NEW, effective_max_new=MAX_NEW, prompt_sha256=sha(prompt),
        prompt_ids=ids, prompt_ids_sha256=sha(ids), requested_prompt_tokens=len(ids), effective_prompt_tokens=len(ids),
        truncated=False, generated_ids=new, generated_ids_sha256=sha(new), terminal_ids=terminal,
        body=tok.decode(content, skip_special_tokens=False), raw_new_text=tok.decode(new, skip_special_tokens=False),
        decoded_total=decoded, historical_answer_extraction=True)
    return answer, generation


def validate_generation(answer, g, row, tok):
    ids = tok.encode(row['prompt']).ids
    expected = dict(precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False,
        max_new=MAX_NEW, requested_max_new=MAX_NEW, effective_max_new=MAX_NEW,
        prompt_sha256=sha(row['prompt']), prompt_ids=ids, prompt_ids_sha256=sha(ids),
        requested_prompt_tokens=len(ids), effective_prompt_tokens=len(ids), truncated=False,
        eos_token_available=True, stop_at_eos_requested=True, stop_at_eos_effective=True,
        stop_token_sequences=[[tok.token_to_id('<|im_end|>')]], historical_answer_extraction=True)
    if any(g.get(k) != v for k, v in expected.items()): raise ValueError('원 public greedy128 영수증이 다르다')
    new, terminal = g.get('generated_ids'), g.get('terminal_ids')
    if (not isinstance(new, list) or not 1 <= len(new) <= MAX_NEW
            or any(type(i) is not int or not 0 <= i < 32768 for i in new)
            or type(g.get('generated_tokens')) is not int or g['generated_tokens'] != len(new)
            or not isinstance(terminal, list) or g.get('generated_ids_sha256') != sha(new)):
        raise ValueError('실제 생성 ID/개수/해시가 다르다')
    reason = g.get('finish_reason'); eot, eos = tok.token_to_id('<|im_end|>'), tok.token_to_id('<eos>')
    if reason == 'STOP_SEQUENCE':
        if terminal != [eot] or g.get('matched_stop_sequence') != [eot]: raise ValueError('끝 EOT가 다르다')
    elif reason == 'EOS':
        if terminal != [eos] or g.get('matched_stop_sequence') is not None: raise ValueError('끝 EOS가 다르다')
    elif reason != 'MAX_NEW' or terminal or len(new) != MAX_NEW or g.get('matched_stop_sequence') is not None:
        raise ValueError('원 종료 사유/128토큰 상한이 다르다')
    if terminal and new[-len(terminal):] != terminal: raise ValueError('실제 마지막 control ID가 다르다')
    content = new[:-len(terminal)] if terminal else new
    if any(i in (eot, eos) for i in content): raise ValueError('생성 중간 종료 ID를 허용하지 않는다')
    decoded = tok.decode(ids + new); prefix = tok.decode(ids)
    if (not decoded.startswith(prefix) or g.get('decoded_total') != decoded
            or g.get('body') != tok.decode(content, skip_special_tokens=False)
            or g.get('raw_new_text') != tok.decode(new, skip_special_tokens=False)
            or answer != decoded[len(prefix):].split('<|im_end|>', 1)[0].strip()):
        raise ValueError('실제 ID/body/기존 답 추출의 재decode가 다르다')


def score_free(row, answer):
    scores = public.answer_scores(answer, row['golds'])
    if row['task'] == 'gsm8k_free':
        value = public.numerical(answer)
        scores['numeric_exact'] = int(value is not None and value == public.numerical(row['golds'][0]))
    return scores


def event_base(row, lineage):
    return dict(id=row_id(row), case_sha256=sha(row), task=row['task'], kind=row['kind'], index=row['index'], lineage=lineage)


def validate_event(event, row, tok, lineage, exclusion):
    if any(event.get(k) != v for k, v in event_base(row, lineage).items()): raise ValueError('원답 문항/모델 계보가 다르다')
    if exclusion is not None:
        if event.get('skipped') is not True or event.get('reason') != exclusion: raise ValueError('길이 제외 사유가 다르다')
        return
    if event.get('skipped') is not False: raise ValueError('적격 문항을 임의 제외하지 않는다')
    if row['kind'] == 'mc':
        if event.get('encoding') != mc_encoding(row, tok): raise ValueError('prefix/후속 분리 토큰화 경계가 다르다')
        audit._mc(dict(kind='mc', source_item=row['item'], scores=event['scores']), dict(row, case_id=row_id(row)), tok)
    else:
        validate_generation(event['answer'], event['generation'], row, tok)
        if event.get('scores') != score_free(row, event['answer']): raise ValueError('자유답 점수 재계산이 다르다')


def recount(events, rows):
    if [e.get('id') for e in events] != [row_id(r) for r in rows]: raise ValueError('ordered 전체 원형이 필요하다')
    result = {}
    for task in dict.fromkeys(r['task'] for r in rows):
        group = [e for e in events if e['task'] == task]; eligible = [e for e in group if not e['skipped']]
        if not eligible: raise ValueError('전체 제외 과제는 완전한 평가가 아니다')
        cell = dict(asked=len(group), n=len(eligible), skipped=len(group) - len(eligible),
            skip_reasons=dict(Counter(e['reason'] for e in group if e['skipped'])))
        if task in public.TASKS:
            golds = Counter(e['scores']['gold'] for e in eligible); predictions = Counter(e['scores']['pred_harness'] for e in eligible)
            correct = sum(e['scores']['pred_harness'] == e['scores']['gold'] for e in eligible)
            cell.update(correct=correct, accuracy=suite.wilson(correct, len(eligible)),
                char_norm_correct=sum(e['scores']['pred_harness_norm'] == e['scores']['gold'] for e in eligible),
                chance=sum(1 / len(r['item']['choices']) for r in rows if r['task'] == task) / len(group),
                gold_distribution=dict(golds), prediction_distribution=dict(predictions),
                sample_majority_baseline=max(golds.values()) / len(eligible))
        else:
            cell.update(exact=sum(e['scores']['whitespace_nfkc_exact'] for e in eligible),
                mean_char_f1=sum(e['scores']['char_overlap_f1'] for e in eligible) / len(eligible),
                empty=sum(not e['answer'].strip() for e in eligible),
                finish_reasons=dict(Counter(e['generation']['finish_reason'] for e in eligible)))
            if task == 'gsm8k_free': cell['numeric_exact'] = sum(e['scores']['numeric_exact'] for e in eligible)
        result[task] = cell
    return result


def show(row, event, model_id):
    value = dict(model_id=model_id, id=row_id(row), task=row['task'], skipped=event['skipped'])
    if row['kind'] == 'mc':
        value.update(question=row['item'].get('ctx'), choices=row['item']['choices'], pairs=row['item'].get('pairs'),
            gold=row['item']['gold'], selected=event.get('scores', {}).get('pred_harness'),
            char_selected=event.get('scores', {}).get('pred_harness_norm'))
    else:
        value.update(question=row['question'], golds=row['golds'], answer=event.get('answer'),
            finish_reason=event.get('generation', {}).get('finish_reason'))
    value['rejection_reason'] = event.get('reason')
    print('[CURRENT_BENCHMARK_SAMPLE] ' + json.dumps(value, ensure_ascii=False), flush=True)


def evaluate(model_id):
    reference, all_rows, _, _ = prepared(); rows = cohort(all_rows, model_id)
    key = phase_key('evaluate', model_id); directory = safe(RAW / key)
    if exists(directory) or exists(result_path(key)): raise FileExistsError('이전/부분 모델 평가를 보존한다')
    from scripts.p106b_gate_runtime import idle_before_gpu
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    idle_before_gpu(); authority(); spec = reference['binding']['models'][model_id]
    lineage = dict(tag=TAG, model_id=model_id, checkpoint_sha256=spec['checkpoint_sha256'],
        core_sha256=spec['core_sha256'], route=spec['route'], reference_sha256=digest(CACHE / 'frozen_reference.json'))
    began = time.perf_counter()
    with model_runtime(model_id, spec) as (torch, model, cfg, tok, route):
        if model.training or cfg.max_seq_len != CONTEXT or cfg.mtp_aux: raise ValueError('동일 eval/문맥/MTPoff가 필요하다')
        before = state_fingerprint(model); flags = [p.requires_grad for p in model.parameters()]
        lineage['cfg_sha256'] = sha(asdict(cfg))
        wrapped = FP32Forward(model); writer = ShardWriter(directory, 'answers', limit=19_999_999)
        events = []; torch.cuda.reset_peak_memory_stats()
        import torch.nn.functional as F
        with torch.no_grad():
            for row in rows:
                authority()
                if route is not None: route.assert_active()
                event = event_base(row, lineage); exclusion = reference['binding']['exclusions'][row_id(row)]
                if eligibility(row, tok) != exclusion: raise ValueError('원 frozen 적격성이 달라졌다')
                if exclusion is not None: event.update(skipped=True, reason=exclusion)
                elif row['kind'] == 'mc':
                    result = suite.run_mc(row['task'], [row['item']], wrapped, tok, 'cuda', CONTEXT, torch, F, True)
                    if len(result['rows']) != 1 or result['skip_rows']: raise ValueError('원 scorer 적격성이 다르다')
                    event.update(skipped=False, scores=result['rows'][0], encoding=mc_encoding(row, tok))
                else:
                    answer, generation = emit_public(model, cfg, tok, row['prompt'])
                    event.update(skipped=False, answer=answer, generation=generation, scores=score_free(row, answer))
                validate_event(event, row, tok, lineage, exclusion); writer.append(event); events.append(event)
                if row_id(row) in reference['display_ids'] or exclusion is not None: show(row, event, model_id)
                if len(events) % 128 == 0:
                    print('[CURRENT_BENCHMARK_PROGRESS] ' + json.dumps(dict(model_id=model_id, rows=len(events), requested=len(rows))), flush=True)
        route_receipt = n.route_receipt(model, route) if route is not None else dict(mode='PRODUCT_TERNARY', loader='BROAD_V2_ORIGINAL_STRICT')
        if route is not None: n.validate_route_receipt(route_receipt, spec['arm'])
        model.clear_quant(); after = state_fingerprint(model)
        if (before != spec['core_sha256'] or before != after or flags != [p.requires_grad for p in model.parameters()]
                or digest(ROOT / spec['checkpoint']) != spec['checkpoint_sha256']):
            raise ValueError('평가가 본체/Parameter 플래그/CP를 바꾸었다')
        manifest = writer.close(lineage=lineage)
        report = dict(info(), status='CURRENT_PUBLIC_MODEL_COMPLETE', model_id=model_id, lineage=lineage,
            checkpoint_sha256=spec['checkpoint_sha256'], cfg=asdict(cfg), cfg_sha256=sha(asdict(cfg)),
            tokenizer_sha256=public.TOKENIZER_SHA, route=route_receipt, core_before=before, core_after=after,
            requires_grad_unchanged=True, raw_manifest=manifest, summary=recount(events, rows),
            requested=len(rows), scored=sum(not e['skipped'] for e in events), length_excluded=sum(e['skipped'] for e in events),
            model_exceptions=0, whole_seconds=time.perf_counter() - began,
            peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
        write(result_path(key), report)
    print('[CURRENT_BENCHMARK_MODEL_FINAL] ' + json.dumps(dict(model_id=model_id, requested=report['requested'], scored=report['scored'])), flush=True)
    return 0


def read_model(model_id, reference, all_rows, tok):
    completed_activity('evaluate', model_id)
    report = required(result_path(phase_key('evaluate', model_id))); rows = cohort(all_rows, model_id)
    spec = reference['binding']['models'][model_id]
    lineage = dict(tag=TAG, model_id=model_id, checkpoint_sha256=spec['checkpoint_sha256'], core_sha256=spec['core_sha256'],
        route=spec['route'], cfg_sha256=sha(report.get('cfg')), reference_sha256=digest(CACHE / 'frozen_reference.json'))
    if (report.get('status') != 'CURRENT_PUBLIC_MODEL_COMPLETE' or report.get('model_id') != model_id
            or any(report.get(k) != v for k, v in info().items()) or report.get('lineage') != lineage
            or report.get('core_before') != spec['core_sha256'] or report.get('core_after') != spec['core_sha256']
            or report.get('requires_grad_unchanged') is not True or report.get('model_exceptions') != 0
            or report.get('cfg_sha256') != sha(report.get('cfg')) or report.get('cfg', {}).get('max_seq_len') != CONTEXT
            or report.get('tokenizer_sha256') != public.TOKENIZER_SHA or report.get('checkpoint_sha256') != spec['checkpoint_sha256']
            or report.get('raw_manifest', {}).get('lineage') != lineage):
        raise ValueError('같은 모델/정식 route/본체의 완전한 benchmark 보고서가 필요하다')
    if spec['family'] == 'native_weight_route': n.validate_route_receipt(report['route'], spec['arm'])
    elif report.get('route') != dict(mode='PRODUCT_TERNARY', loader='BROAD_V2_ORIGINAL_STRICT'):
        raise ValueError('원 broad loader 영수증이 다르다')
    events = read_shards(RAW / phase_key('evaluate', model_id), report['raw_manifest'], 'answers', len(rows))
    for event, row in zip(events, rows): validate_event(event, row, tok, lineage, reference['binding']['exclusions'][row_id(row)])
    summary = recount(events, rows)
    if (sha(report.get('summary')) != sha(summary) or report.get('requested') != len(rows)
            or report.get('scored') != sum(not e['skipped'] for e in events)
            or report.get('length_excluded') != sum(e['skipped'] for e in events)):
        raise ValueError('원답 재집계/요청/실채점/길이 제외가 다르다')
    return report, events


def readback():
    reference, rows, tok, cached = prepared(); summaries = {}; comparisons = {}; total, scored = 0, 0
    lookup = {r['id']: r for r in cached}
    for model_id in MODELS:
        authority(); report, events = read_model(model_id, reference, rows, tok)
        summaries[model_id] = report['summary']; total += report['requested']; scored += report['scored']
        cells = {}
        for task in ENGLISH:
            actual = [e for e in events if e['task'] == task and not e['skipped']]
            if len(actual) != 256 or {e['scores']['id'] for e in actual} != {r['id'] for r in cached if r['task'] == task}:
                raise ValueError('Falcon과 정확한 공통256 ID가 필요하다')
            right = sum(e['scores']['pred_harness'] == e['scores']['gold'] for e in actual)
            left = sum(lookup[e['scores']['id']]['correct'] for e in actual)
            if any(lookup[e['scores']['id']]['gold'] != e['scores']['gold'] for e in actual): raise ValueError('공통 정답이 다르다')
            cells[task] = dict(n_common=256, common_ids_sha256=sha(sorted(e['scores']['id'] for e in actual)),
                cached_falcon_correct=left, current_model_correct=right, model_minus_cached_falcon=(right - left) / 256)
        comparisons[model_id] = cells
    if (total, scored) != (9216, 9212): raise ValueError('전체 요청9216/실채점9212 분모가 다르다')
    write(result_path('readback'), dict(info(), status='CURRENT_BENCHMARK_RAW_RECOUNT_COMPLETE',
        summaries=summaries, same_id_cached_falcon=comparisons, cached_falcon=reference['binding']['cached_falcon'],
        actual_requested_rows=total, actual_scored_rows=scored, actual_length_excluded=total - scored,
        models_loaded=0, checkpoint_tensor_loads=0,
        limitation='관찰 공개팩·단일seed·오염미감사; 선택형 우도는 자유답·대화·Falcon 동등성 또는 구조 단독 인과가 아니다'))
    return 0


def validate_activity(value, key, complete=False):
    if (not isinstance(value, dict) or value.get('schema') != SCHEMA or value.get('tag') != TAG or value.get('key') != key
            or value.get('code_sha256') != info()['code_sha256'] or not n.finite(value.get('seconds'))
            or type(value.get('max_wall_sec')) is not int or not 60 <= value['max_wall_sec'] <= ACTIVE_LIMIT
            or value['seconds'] > value['max_wall_sec'] + 30 or type(value.get('returncode')) is not int
            or type(value.get('complete')) is not bool or value['complete'] != (value['returncode'] == 0)
            or type(value.get('worker_pid')) is not int or value['worker_pid'] <= 0 or value.get('worker_pgid') != value['worker_pid']
            or phase_key(value['mode'], value.get('model_id')) != key):
        raise ValueError('같은 코드/자기 PGID/상한의 실제 activity가 필요하다')
    start, end = (datetime.fromisoformat(value[k]) for k in ('started_at', 'ended_at'))
    if start.tzinfo is None or end.tzinfo is None or end < start or start >= END - timedelta(seconds=RECORD_RESERVE) or end > END:
        raise ValueError('activity의 절대 권한/기록 예비 시각이 다르다')
    if complete and (not value['complete'] or value.get('error_type') is not None): raise Pending('완료 activity가 아직 없다')
    return value


def completed_activity(mode, model_id=None):
    key = phase_key(mode, model_id)
    value = validate_activity(required(EVIDENCE / ('activity_' + key + '.json')), key, True)
    if (value.get('result_sha256') != digest(result_path(key))
            or value.get('reference_sha256') != digest(CACHE / 'frozen_reference.json')):
        raise ValueError('activity/결과/준비 SHA가 다르다')
    return value


def spent_seconds():
    total, workers, linked = 0., {}, set()
    if exists(EVIDENCE):
        for path in safe(EVIDENCE).glob('activity_*.json'):
            value = required(path)
            if path.name != 'activity_' + str(value.get('key')) + '.json': raise ValueError('activity 파일명 식별자가 다르다')
            workers[value['key']] = (validate_activity(value, value['key'])['seconds'], digest(path))
        for path in safe(EVIDENCE).glob('aux_*.json'):
            value = required(path)
            if (value.get('tag') != TAG or value.get('code_sha256') != info()['code_sha256']
                    or not n.finite(value.get('seconds')) or type(value.get('returncode')) is not int
                    or not n.fingerprint(value.get('command_sha256'))):
                raise ValueError('회귀/사전검사의 실제 활동 영수증이 다르다')
            total += value['seconds']
            key = value.get('new_worker_key')
            if key is not None:
                if key in linked or key not in workers or value.get('new_worker_sha256') != workers[key][1]:
                    raise ValueError('전체 child 경과시간과 새 worker 영수증의 결합이 다르다')
                linked.add(key)
            elif value.get('new_worker_sha256') is not None:
                raise ValueError('worker 없는 launcher 영수증에 worker SHA를 넣지 않는다')
    # launcher 전체 경과시간을 우선한다. 직접 실행한 worker만 별도로 합한다.
    return total + sum(value[0] for key, value in workers.items() if key not in linked)


def remaining_activity():
    remaining = min(authority(), ACTIVE_LIMIT - spent_seconds())
    if remaining <= 0: raise Pending('이 benchmark의 총 활동1시간 상한에 도달했다')
    return remaining


def worker(mode, model_id, max_wall_sec):
    key = phase_key(mode, model_id)
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= ACTIVE_LIMIT: raise ValueError('60~3600초 상한이 필요하다')
    if max_wall_sec > remaining_activity(): raise Pending('총1시간/기록 예비를 뺀 남은 활동보다 worker 상한이 크다')
    pid, pgid = os.getpid(), os.getpgid(os.getpid())
    if pid != pgid: raise ValueError('전용 launcher가 만든 자기 PGID가 필요하다')
    activity = EVIDENCE / ('activity_' + key + '.json')
    if mode in ('source', 'preflight'):
        from scripts.p106b_gate_runtime import wall_limit
        with n.termination_guard(), wall_limit(max_wall_sec):
            source_state() if mode == 'source' else prepared()
            remaining_activity()
        print('[CURRENT_BENCHMARK_PREFLIGHT] 원형/여섯CP/캐시 검산, 모델0', flush=True); return 0
    if exists(activity): raise FileExistsError('이전 activity와 부분 결과를 보존한다')
    metadata = info(); began = time.perf_counter(); start = datetime.now(timezone.utc).isoformat(); code, error = 9, None
    try:
        from scripts.p106b_gate_runtime import wall_limit
        with n.termination_guard(), wall_limit(max_wall_sec):
            code = prepare() if mode == 'prepare' else evaluate(model_id) if mode == 'evaluate' else readback()
        if code == 0 and (not exists(result_path(key)) or info()['code_sha256'] != metadata['code_sha256']):
            raise ValueError('종료0에는 같은 코드의 닫힌 결과가 필요하다')
        return code
    except BaseException as exc:
        error = type(exc).__name__; code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (Pending, FileNotFoundError, FileExistsError)) else 9
        raise
    finally:
        write(activity, dict(schema=SCHEMA, tag=TAG, key=key, mode=mode, model_id=model_id,
            started_at=start, ended_at=datetime.now(timezone.utc).isoformat(), seconds=time.perf_counter() - began,
            max_wall_sec=max_wall_sec, worker_pid=pid, worker_pgid=pgid, returncode=code, complete=code == 0,
            error_type=error, code_sha256=metadata['code_sha256'],
            result_sha256=digest(result_path(key)) if exists(result_path(key)) else None,
            reference_sha256=digest(CACHE / 'frozen_reference.json') if exists(CACHE / 'frozen_reference.json') else None))


def phase_commands(mode, model_id, max_wall_sec):
    phase_key(mode, model_id)
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= ACTIVE_LIMIT: raise ValueError('60~3600초 상한이 필요하다')
    py = [sys.executable, '-B', '-X', 'utf8']; base = py + [OWN_CODE[0]]
    command = base + ['--mode', mode, '--worker', '--execute', '--max-wall-sec', str(max_wall_sec)]
    if model_id is not None: command += ['--model-id', model_id]
    preflight = 'source' if mode in ('source', 'prepare') else 'preflight'
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_current_benchmark', '-v']),
        ('PREFLIGHT', base + ['--mode', preflight, '--worker', '--execute', '--max-wall-sec', '600']), ('EXECUTE', command)]


def launch_phase(command, fallback):
    try: remaining = remaining_activity()
    except Pending: return 8
    limit = int(command[command.index('--max-wall-sec') + 1]) if '--max-wall-sec' in command else fallback
    # 실물 worker는 자체 activity를 남긴다. 회귀/사전검사도 총 활동 예산에 포함한다.
    began = time.perf_counter(); start = datetime.now(timezone.utc).isoformat(); result = 9
    key = None; activity = None
    if '--mode' in command:
        mode = command[command.index('--mode') + 1]
        if mode in ('prepare', 'evaluate', 'readback'):
            model_id = command[command.index('--model-id') + 1] if '--model-id' in command else None
            key = phase_key(mode, model_id); activity = EVIDENCE / ('activity_' + key + '.json')
    existed = activity is not None and exists(activity)
    try:
        result = n.launch(command, min(limit + 30, remaining))
        return result
    finally:
        created = activity is not None and not existed and exists(activity)
        launch_id = sha([command, os.getpid(), start])[:24]
        write(EVIDENCE / ('aux_' + launch_id + '.json'), dict(tag=TAG, code_sha256=info()['code_sha256'],
            command_sha256=sha(command), seconds=time.perf_counter() - began, returncode=result,
            new_worker_key=key if created else None, new_worker_sha256=digest(activity) if created else None))


def stage_note(line):
    line = line.replace('child success is not the final experiment verdict', '자식 단계 성공은 최종 품질 판정이 아니다')
    if line.startswith('[EXPERIMENT_FINAL] '):
        value = json.loads(line.split('] ', 1)[1]); value['evidence_scope'] = '단계 실행 영수증이며 모델 품질·과학적 채택 판정이 아니다'
        line = '[EXPERIMENT_FINAL] ' + json.dumps(value, ensure_ascii=False, sort_keys=True)
    print(line, flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, required=True); parser.add_argument('--model-id', choices=MODELS)
    parser.add_argument('--max-wall-sec', type=int, default=600); parser.add_argument('--worker', action='store_true')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        phases = phase_commands(args.mode, args.model_id, args.max_wall_sec)
        if args.check_only:
            print('[CURRENT_BENCHMARK_CHECK_ONLY] ' + json.dumps(info(), ensure_ascii=False), flush=True); return 0
        if args.worker: return worker(args.mode, args.model_id, args.max_wall_sec)
        return pipeline(phases, lambda cmd: launch_phase(cmd, args.max_wall_sec), stage_note,
            experiment='P106B_CURRENT_BENCHMARK_' + phase_key(args.mode, args.model_id))['returncode']
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (Pending, FileNotFoundError, FileExistsError)) else 9
        if code == 9: traceback.print_exc(file=sys.stderr)
        print('[CURRENT_BENCHMARK_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__': raise SystemExit(main())
