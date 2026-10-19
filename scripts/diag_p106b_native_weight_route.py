#!/usr/bin/env python3
"""같은 무작위 초기화의 native 두 경로와 자기 경로 SFT를 비교한다.

제품 학습기와 예전 자료·체크포인트는 변경하지 않는다. 실제 모델과 CUDA는
총괄이 명시적으로 실행한 worker에서만 사용하며 CPU 검증과 구분한다.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
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
import runpy
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_stage_receipt import pipeline

TAG = 'p106b_native_weight_route_v1_s1337'
SCHEMA = 'P106B_NATIVE_WEIGHT_ROUTE_V1'
ARMS = ('ternary', 'float')
ENDPOINTS = ('native', 'sft')
MODES = ('source', 'prepare', 'preflight', 'cost', 'budget', 'train', 'sft_cost', 'sft', 'evaluate', 'readback')
CACHE = ROOT / 'data_cache' / TAG
RAW = ROOT / 'runs/eval' / TAG
EVIDENCE = ROOT / 'test_result/evidence' / TAG
NATIVE = ROOT / 'data_cache/ko-en_601000000_chat32'
TRAIN = NATIVE / 'train.bin'
VAL = NATIVE / 'val.bin'
TRAIN_SHA = 'DBD12235B4A1478177246B4BD5214C8B8BBF10D077CBA80304690AD12A8E59A2'
VAL_SHA = 'AD7EFB0DBD0D830A216B4D21A91C8ACB3FC41DAE2B23A3A55999AE8727AA374C'
PARENT = ROOT / 'runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt'
PARENT_SHA = '12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950'
PARENT_CORE = 'E854AB4EC2E505DDC581CE08C94F9C8B4A8081E456AFBA193DF28A877E34A193'
TOKENIZER = ROOT / 'data_cache/tok-ko-en-32768-chat32.json'
TOKENIZER_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
TRAIN_TOKENS, VAL_TOKENS = 597995000, 3005000
SEQ, MICRO, ACCUM, SEED, UPDATES, SFT_UPDATES = 1024, 8, 16, 1337, 2281, 384
TARGETS = SEQ * MICRO * ACCUM
DRAW_TOKENS, CROPS = UPDATES * TARGETS, UPDATES * MICRO * ACCUM
SOURCE_ARM, ANSWERS, MAX_NEW = 'varied_balanced', 1694, 64
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
TRAIN_STOP = END - timedelta(hours=3)
ACTIVE_LIMIT, NATIVE_WORKER_LIMIT, FINISH_RESERVE, SFT_UNMEASURED_RESERVE = 43200, 14400, 10800, 3600
RECORD_RESERVE = 600
FORECAST_FACTOR = 1.35
OWN_CODE = ('scripts/p106b_weight_route.py', 'scripts/test_p106b_weight_route.py',
    'scripts/diag_p106b_native_weight_route.py', 'scripts/test_p106b_native_weight_route.py')
CODE = (*OWN_CODE, 'scripts/diag_p101a_sft_mtp.py', 'scripts/p101a_sft_mtp_data.py',
    'scripts/diag_p106b_question_transfer.py', 'scripts/p106b_question_transfer_data.py',
    'scripts/diag_p106b_relation_bind.py', 'scripts/p106b_native_windows.py',
    'scripts/diag_p101a_mtp_parity.py', 'scripts/diag_p106b_span_readout.py',
    'scripts/p106b_shards.py', 'scripts/p106b_stage_receipt.py', 'scripts/p106b_gate_runtime.py',
    'scripts/train_sft_p090.py', 'tinylm/paths.py', 'tinylm/data/__init__.py',
    'tinylm/model/__init__.py', 'tinylm/config.py', 'tinylm/model/transformer.py',
    'tinylm/model/modules.py', 'tinylm/model/ternary.py',
    'tinylm/train/mtp_sft.py', 'tinylm/train/anneal_schedule.py',
    'tinylm/train/muon.py', 'tinylm/train/optimizer_audit.py',
    'tinylm/chat/serialize.py', 'tinylm/chat/canonical.py', 'tinylm/data/sft.py',
    'tinylm/infer/generate.py')


class Pending(RuntimeError):
    """명시한 자원·권한·정확한 계보의 선결 조건이 아직 충족되지 않았다."""


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest().upper()


def safe(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(ROOT):
        raise ValueError('저장소 안의 정확한 절대 경로가 필요하다')
    for p in (path, *path.parents):
        if p.is_symlink(): raise ValueError('심볼릭 링크 경로는 허용하지 않는다')
        if p == ROOT: break
    return path


def digest(path):
    path = safe(path)
    if not path.is_file(): raise Pending('정확한 입력 파일이 없다: ' + str(path.relative_to(ROOT)))
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest().upper()


def required(path):
    path = safe(path)
    if not path.is_file(): raise Pending('이 단계의 선결 파일이 없다: ' + str(path.relative_to(ROOT)))
    if path.stat().st_size >= 20_000_000: raise ValueError('20MB 미만의 JSON이 필요하다')
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path = safe(path)
    if not any(path.is_relative_to(base) for base in (CACHE, RAW, EVIDENCE)):
        raise ValueError('이 새 단계의 허가된 산출물 경로에만 쓸 수 있다')
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(payload) >= 20_000_000: raise ValueError('단일 JSON은 20MB 미만이어야 한다')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(payload)


def modules():
    from scripts import diag_p101a_sft_mtp as runtime
    from scripts import diag_p106b_question_transfer as source
    from scripts import p106b_weight_route as route
    return runtime, source, route


def schedule(step, updates=UPDATES):
    if type(step) is not int or not 0 <= step < updates: raise ValueError('0부터 시작하는 실제 update 번호가 필요하다')
    functions = runpy.run_path(str(ROOT / 'tinylm/train/anneal_schedule.py'))
    start = functions['resolve_quant_start'](100, updates)
    return dict(lr_factor=functions['lr_factor'](step, 100, updates, 'wsd', decay_frac=.2),
        anneal=functions['quant_anneal_factor'](step, updates, 'wsd', 'linear', start, .8),
        quant_start=start)


def make_offsets(*, pool_tokens=TRAIN_TOKENS, updates=UPDATES, micro=MICRO,
                 accum=ACCUM, seq=SEQ, seed=SEED):
    import numpy as np
    values = (pool_tokens, updates, micro, accum, seq, seed)
    if any(type(v) is not int for v in values) or min(values[:-1]) <= 0 or seed < 0:
        raise ValueError('native 조건은 양의 정수여야 한다')
    draw = updates * micro * accum * seq
    if pool_tokens < 2 * draw or pool_tokens <= seq:
        raise ValueError('실제 TRAIN 풀은 지정 draw의 두 배 이상이어야 한다')
    offsets = np.random.default_rng(seed).integers(0, pool_tokens - seq,
        size=updates * micro * accum, dtype=np.int64)
    return offsets, dict(crops=len(offsets), draw_tokens=draw, pool_tokens=pool_tokens,
        twice_draw=2 * draw, pool_slack=pool_tokens - 2 * draw,
        min_offset=int(offsets.min()), max_offset=int(offsets.max()),
        unique_offsets=len(np.unique(offsets)), window_tokens=seq + 1,
        rng='numpy.default_rng(seed).integers(0,TRAIN-seq,size=crops,dtype=int64)', seed=seed,
        replacement=True, overlap='복원 추출 crop은 서로 겹칠 수 있으며 고유 지식량을 뜻하지 않는다',
        offsets_bytes_sha256=hashlib.sha256(offsets.tobytes()).hexdigest().upper())


def info():
    pins = {p: digest(ROOT / p) if safe(ROOT / p).is_file() else 'NOT_CREATED' for p in sorted(set(CODE))}
    return dict(schema=SCHEMA, tag=TAG, code_sha256=pins,
        code_complete=all(v != 'NOT_CREATED' for v in pins.values()), arms=list(ARMS),
        parent_cfg_only=str(PARENT.relative_to(ROOT)), parent_sha256=PARENT_SHA,
        parent_training_weights_copied=False, initializer='load_runtime(scratch_ntp)',
        tokenizer_sha256=TOKENIZER_SHA, train_tokens=TRAIN_TOKENS, val_tokens=VAL_TOKENS,
        train_sha256=TRAIN_SHA, val_sha256=VAL_SHA, micro_bs=MICRO, accum=ACCUM,
        seq=SEQ, checkpoint_on=True, amp='bf16', compile='default', tf32=False,
        native_updates=UPDATES, native_draw_tokens=DRAW_TOKENS, native_crops=CROPS,
        native_peak_adam_lr=.001, native_peak_muon_lr=.004, native_warmup=100,
        native_lr_schedule='wsd', native_decay_frac=.2, native_quant_anneal='linear',
        native_anneal_end=.8, muon_scale='rms', clip=1., native_language_ratio='NOT_MEASURED',
        sft_source='p106b_question_transfer_v2_s1337', sft_arm=SOURCE_ARM,
        sft_updates=SFT_UPDATES, sft_passes=4, sft_policy='TOKEN_L0',
        sft_adam_lr=5e-5, sft_muon_lr=2e-4, sft_all_weight_decay=0., sft_native_targets=8192,
        max_new=MAX_NEW, expected_answers=ANSWERS, teacher_calls=0,
        authority_end_utc=END.isoformat(), training_stop_utc=TRAIN_STOP.isoformat(),
        stage_active_limit_seconds=ACTIVE_LIMIT, finish_reserve_seconds=FINISH_RESERVE,
        native_worker_limit_seconds=NATIVE_WORKER_LIMIT,
        final_record_reserve_seconds=RECORD_RESERVE,
        unmeasured_sft_reserve_seconds=SFT_UNMEASURED_RESERVE, forecast_factor=FORECAST_FACTOR,
        comparison='초기 가중치·draw·optimizer·스케줄은 같고 TLinear 가중치 경로만 다르다',
        original2289_reproduction=False, broad_intelligence='NOT_ESTABLISHED')


def authority(training=False, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None: raise ValueError('시간대가 있는 시각이 필요하다')
    remaining = ((TRAIN_STOP if training else END) - now).total_seconds()
    if remaining <= 0: raise Pending('명시한 실행 권한 또는 학습 예비시간을 소진했다')
    return remaining


def execution_remaining(training=False, now=None):
    remaining = authority(training, now) - (0 if training else RECORD_RESERVE)
    if remaining <= 0: raise Pending('최종 기록 예비 600초 또는 학습 종료 경계에 도달했다')
    return remaining


def source_state():
    _, source, _ = modules()
    if not info()['code_complete']: raise ValueError('새 소스와 회귀 파일이 모두 있어야 한다')
    if (source.base.NATIVE_TRAIN_SHA != TRAIN_SHA or source.base.NATIVE_VAL_SHA != VAL_SHA
            or source.base.PARENT_SHA != PARENT_SHA): raise ValueError('정본 native 또는 부모 SHA와 다르다')
    for path, expected, size in ((TRAIN, TRAIN_SHA, 2 * TRAIN_TOKENS), (VAL, VAL_SHA, 2 * VAL_TOKENS)):
        if safe(path).stat().st_size != size or digest(path) != expected:
            raise ValueError('원본 native 캐시의 크기 또는 SHA가 다르다')
    if digest(PARENT) != PARENT_SHA or digest(TOKENIZER) != TOKENIZER_SHA:
        raise ValueError('부모 cfg 또는 tokenizer 원본 바이트가 바뀌었다')
    frozen, _, _ = source.read_prepared()
    if (frozen.get('native_access') != 'INDEXED_TRAIN_ONLY'
            or frozen.get('native_train_file') != str(TRAIN.relative_to(ROOT))
            or len(frozen.get('native_train_offsets', [])) != SFT_UPDATES * MICRO):
        raise ValueError('SFT replay도 정확한 TRAIN 전용 offset3072개만 읽어야 한다')
    consumer = source.validate_training_inputs(frozen, SOURCE_ARM)
    cases = source.read_rows(source.CORPUS, frozen['manifests']['cases'], 'cases', ANSWERS)
    binding = dict(native_train=str(TRAIN.relative_to(ROOT)), native_val=str(VAL.relative_to(ROOT)),
        native_train_sha256=TRAIN_SHA, native_val_sha256=VAL_SHA,
        native_train_bytes=2 * TRAIN_TOKENS, native_val_bytes=2 * VAL_TOKENS,
        val_training_token_access=False, val_identity_hashed_only_during_prepare=True,
        source_report_sha256=digest(source.CORPUS / 'report.json'),
        source_manifests_sha256=sha(frozen['manifests']), source_consumer=consumer,
        source_exposure=frozen['exposure'][SOURCE_ARM], source_cases_sha256=sha(cases),
        sft_native_offsets_sha256=sha(frozen['native_train_offsets']), language_ratio='NOT_MEASURED')
    return frozen, cases, binding


def prepare():
    authority(training=True)
    for path in (CACHE, RAW, EVIDENCE):
        if safe(path).exists(): raise FileExistsError('이전 완료 또는 부분 namespace를 보존한다')
    _, cases, binding = source_state()
    offsets, description = make_offsets()
    for path in (CACHE, RAW, EVIDENCE): path.mkdir(parents=True, exist_ok=False)
    import numpy as np
    with (CACHE / 'native_offsets.npy').open('xb') as stream: np.save(stream, offsets, allow_pickle=False)
    result = dict(info(), status='NATIVE_ROUTE_CPU_PREPARED', binding=binding,
        offsets=description, offsets_file_sha256=digest(CACHE / 'native_offsets.npy'),
        native_schedule=[dict(step=s, **schedule(s)) for s in (0, 7, 99, 100, UPDATES - 1)],
        display_ids=sorted((c['id'] for c in cases), key=lambda k: sha([TAG, 'DISPLAY', k]))[:24],
        actual_model_initialization='NOT_RUN', models_loaded=0, optimizer_updates=0, checkpoint_writes=0)
    write(CACHE / 'frozen_reference.json', result)
    write(EVIDENCE / 'cpu_contract.json', dict(result, frozen_reference_sha256=digest(CACHE / 'frozen_reference.json')))
    print('[NATIVE_ROUTE_CPU] 같은 복원 crop291968개와 전체 SFT pass 검산, 모델0', flush=True)
    return 0


def prepared():
    frozen, cases, binding = source_state()
    reference = required(CACHE / 'frozen_reference.json')
    if (reference.get('status') != 'NATIVE_ROUTE_CPU_PREPARED' or reference.get('binding') != binding
            or any(reference.get(k) != v for k, v in info().items())
            or required(EVIDENCE / 'cpu_contract.json') != dict(reference, frozen_reference_sha256=digest(CACHE / 'frozen_reference.json'))):
        raise ValueError('동일하고 완전한 원천·코드·조건 참조가 필요하다')
    completed_activity('prepare')
    import numpy as np
    if digest(CACHE / 'native_offsets.npy') != reference['offsets_file_sha256']:
        raise ValueError('동결 crop 바이트가 다르다')
    offsets = np.load(CACHE / 'native_offsets.npy', allow_pickle=False)
    expected, description = make_offsets()
    if offsets.dtype != np.int64 or not np.array_equal(offsets, expected) or description != reference['offsets']:
        raise ValueError('같은 RNG1337의 전체 복원 추출 crop 벡터가 필요하다')
    return reference, frozen, cases, offsets


def phase_key(mode, arm=None, endpoint=None):
    if mode not in MODES: raise ValueError('등록된 단계가 필요하다')
    needs_arm = mode in ('cost', 'train', 'sft_cost', 'sft', 'evaluate')
    if needs_arm != (arm in ARMS) or (not needs_arm and arm is not None):
        raise ValueError('실제로 사용할 arm을 명시해야 하며 미사용 arm은 거부한다')
    needs_endpoint = mode in ('budget', 'evaluate')
    if needs_endpoint != (endpoint in ENDPOINTS) or (not needs_endpoint and endpoint is not None):
        raise ValueError('실제로 사용할 native 또는 sft 종점을 명시해야 한다')
    return '_'.join(v for v in (mode, arm, endpoint) if v)


def finite(value, positive=False):
    return (type(value) in (int, float) and math.isfinite(value)
            and (value > 0 if positive else value >= 0))


def fingerprint(value):
    return (type(value) is str and len(value) == 64
            and all(ch in '0123456789ABCDEF' for ch in value))


def checkpoint(arm, endpoint):
    if arm not in ARMS or endpoint not in ENDPOINTS: raise ValueError('등록된 체크포인트가 필요하다')
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_' + TAG + '_' + arm + '_' + endpoint + '.pt')


def result_path(key): return EVIDENCE / key / 'report.json'


def validate_activity(value, key, complete=False):
    if (not isinstance(value, dict) or value.get('schema') != SCHEMA or value.get('tag') != TAG or value.get('key') != key
            or type(value.get('seconds')) not in (int, float) or not math.isfinite(value['seconds'])
            or value['seconds'] < 0 or type(value.get('max_wall_sec')) is not int
            or not 60 <= value['max_wall_sec'] <= 21600 or value['seconds'] > value['max_wall_sec'] + 30
            or type(value.get('returncode')) is not int or type(value.get('complete')) is not bool
            or value['complete'] != (value['returncode'] == 0) or value.get('code_sha256') != info()['code_sha256']):
        raise ValueError('같은 코드에 묶인 유한한 실제 activity가 필요하다')
    if phase_key(value['mode'], value.get('arm'), value.get('endpoint')) != key: raise ValueError('activity의 단계 식별자가 다르다')
    begin, end = (datetime.fromisoformat(value[k]) for k in ('started_at', 'ended_at'))
    if begin.tzinfo is None or end.tzinfo is None or end < begin: raise ValueError('activity 시각은 시간대가 있고 순서가 맞아야 한다')
    stop = TRAIN_STOP if value['mode'] in ('prepare', 'cost', 'train', 'sft_cost', 'sft') else END
    if begin >= stop or end > stop + timedelta(seconds=30):
        raise ValueError('activity가 절대 권한 종료 경계를 넘었다')
    if complete and (not value['complete'] or value.get('error_type') is not None): raise Pending('성공 종료한 완전한 activity가 필요하다')
    return value


def completed_activity(mode, arm=None, endpoint=None):
    key = phase_key(mode, arm, endpoint)
    value = validate_activity(required(EVIDENCE / ('activity_' + key + '.json')), key, True)
    if (value.get('result_sha256') != digest(result_path(key))
            or value.get('reference_sha256') != digest(CACHE / 'frozen_reference.json')):
        raise ValueError('activity·보고서·참조의 결합이 다르다')
    return value


def spent_seconds():
    total = 0.
    if EVIDENCE.exists():
        for path in EVIDENCE.glob('activity_*.json'):
            value = required(path)
            if path.name != 'activity_' + str(value.get('key')) + '.json':
                raise ValueError('activity 파일명과 단계 식별자가 다르다')
            total += validate_activity(value, value.get('key'))['seconds']
    return total


def read_events(directory, manifest, count):
    if (manifest.get('rows') != count or manifest.get('limit_bytes') != 19_999_999 or not manifest.get('shards')
            or any(p.get('path') != f'updates_{i:06d}.jsonl' for i, p in enumerate(manifest['shards']))):
        raise ValueError('읽기 전에 이 단계의 정확한 update shard가 필요하다')
    if required(directory / 'updates_shards_manifest.json') != manifest: raise ValueError('닫힌 event manifest와 다르다')
    verify(directory, manifest); values = []
    for part in manifest['shards']:
        with safe(directory / part['path']).open(encoding='utf-8') as stream:
            values.extend(json.loads(line) for line in stream)
    if len(values) != count: raise ValueError('실제 optimizer event 수가 다르다')
    return values


def update_contract(endpoint, step, frozen=None):
    """정답이나 모델 없이 원천 메타데이터로 실제 update 분모를 재구성한다."""
    if endpoint == 'native':
        if not 0 <= step < UPDATES: raise ValueError('등록된 native update 번호가 필요하다')
        return dict(targets=TARGETS, x_tokens=TARGETS, native_replay_targets=0,
            crop_start=step * MICRO * ACCUM, schedule=schedule(step))
    if endpoint != 'sft' or not 0 <= step < SFT_UPDATES or frozen is None:
        raise ValueError('등록된 SFT update 번호와 동결 원천이 필요하다')
    epoch, slot = divmod(step, 96)
    return dict(targets=frozen['exposure'][SOURCE_ARM][epoch]['update_target_denominators'][slot],
        native_replay_targets=8192, crop_start=None, schedule=dict(lr_factor=1., anneal=1.))


def validate_native32(value):
    if (not isinstance(value, dict) or not finite(value.get('ce'))
            or value.get('targets') != 32768 or value.get('windows') != 32
            or value.get('val_sha256') != VAL_SHA or value.get('precision') != 'FP32_MATH'):
        raise ValueError('같은 32개 native FP32 VAL의 완전한 영수증이 필요하다')
    return value


def validate_route_receipt(value, arm):
    _, _, method = modules()
    method.validate_route_metadata(value.get('metadata'), arm)
    if (value.get('mode') != arm or type(value.get('tlinear_instances')) is not int
            or value['tlinear_instances'] <= 0 or value.get('owned_tlinear_instances') != value['tlinear_instances']
            or type(value.get('refreshed_tlinear_instances')) is not int
            or value['refreshed_tlinear_instances'] != value['tlinear_instances']
            or value.get('forward_methods') != ['_guarded_forward']
            or value.get('refresh_methods') != ['_float_refresh' if arm == 'float' else '_ternary_refresh']):
        raise ValueError('실제 전체 TLinear 소유권과 갱신된 경로 증거가 필요하다')
    return value


def actual_lrs(groups, factor=1.):
    optimizers = {}
    for group in groups:
        values = optimizers.setdefault(group['optimizer'], [])
        if group['group'] != len(values): raise ValueError('순서가 일치하는 전체 optimizer group이 필요하다')
        values.append(group['lr'] * factor)
    if len(optimizers) != 2: raise ValueError('정확한 AdamW와 Muon 쌍이 필요하다')
    return list(optimizers.values())


def validate_optimizer_groups(groups, endpoint):
    if not isinstance(groups, list) or not groups: raise ValueError('실제 optimizer group 영수증이 필요하다')
    factor = 10. if endpoint == 'native' else .5
    for group in groups:
        if (not finite(group.get('lr'), True) or not finite(group.get('runtime_lr'), True)
                or group['lr'] != group['runtime_lr'] * factor or group.get('lr_multiplier') != factor
                or not finite(group.get('weight_decay')) or not finite(group.get('runtime_weight_decay'))
                or type(group.get('parameters')) is not int or group['parameters'] <= 0
                or not fingerprint(group.get('names_sha256'))
                or group['weight_decay'] != (group['runtime_weight_decay'] if endpoint == 'native' else 0.)):
            raise ValueError('원형 group의 LR 비율·WD와 전체 Parameter 영수증이 필요하다')
        if group['optimizer'] == 'AdamW':
            if group['scale_mode'] is not None: raise ValueError('AdamW scale mode가 다르다')
        elif group.get('scale_mode') != 'rms' or group['weight_decay'] != 0.:
            raise ValueError('RMS Muon과 행렬 WD0이 필요하다')
    rates = actual_lrs(groups)
    adam = [g['lr'] for g in groups if g['optimizer'] == 'AdamW']
    muon = [g['lr'] for g in groups if g['optimizer'] != 'AdamW']
    if (not adam or not muon or max(adam) != (.001 if endpoint == 'native' else 5e-5)
            or any(v != (.004 if endpoint == 'native' else 2e-4) for v in muon)):
        raise ValueError('native Adam1e-3/Muon4e-3 또는 지정한 기존 SFT 최대 LR이 필요하다')
    return rates


def train_report(mode, arm):
    key = phase_key(mode, arm); completed_activity(mode, arm)
    r = required(result_path(key)); endpoint = 'sft' if mode in ('sft', 'sft_cost') else 'native'
    cost = mode in ('cost', 'sft_cost'); n = 8 if cost else UPDATES if endpoint == 'native' else SFT_UPDATES
    if (r.get('status') != ('COST_COMPLETE' if cost else 'TRAIN_COMPLETE') or r.get('cost') is not cost
            or r.get('arm') != arm or r.get('endpoint') != endpoint or r.get('updates') != n
            or any(r.get(k) != v for k, v in info().items())
            or r.get('reference_sha256') != digest(CACHE / 'frozen_reference.json')
            or r.get('checkpoint_writes') != (0 if cost else 1) or r.get('optimizer_saved') is not False
            or not all(fingerprint(r.get(k)) for k in ('scratch_core_sha256', 'initial_core_sha256', 'final_core_sha256'))
            or r.get('scratch_core_sha256') == PARENT_CORE):
        raise ValueError('같은 코드·경로·단계·조건의 완전한 학습 보고서가 필요하다')
    _, source, method = modules()
    method.validate_route_metadata(r.get('quantization_route'), arm)
    validate_route_receipt(r.get('route', {}), arm)
    validate_optimizer_groups(r.get('actual_optimizer_groups'), endpoint)
    lineage = dict(tag=TAG, arm=arm, endpoint=endpoint, cost=cost, reference_sha256=r['reference_sha256'])
    if r['event_manifest'].get('lineage') != lineage: raise ValueError('원시 update 계보가 다르다')
    events = read_events(RAW / key, r['event_manifest'], n)
    if [e['update'] for e in events] != list(range(1, n + 1)) or r['step_seconds'] != [e['step_seconds'] for e in events]:
        raise ValueError('모든 실제 update와 시간 event가 필요하다')
    if any(not finite(e['step_seconds'], True) or not finite(e.get('ce')) or not finite(e.get('gradient_norm'))
           or type(e.get('clipped')) is not bool or e['clipped'] != (e['gradient_norm'] > 1.) for e in events):
        raise ValueError('유한한 손실·gradient와 양수인 실제 시간이 필요하다')
    frozen = None
    if endpoint == 'native':
        if (r['initial_core_sha256'] != r['scratch_core_sha256'] or r.get('parent_core_sha256') is not None
                or r.get('parent_checkpoint_sha256') is not None): raise ValueError('native 무작위 초기화에 부모 학습 가중치를 복사하면 안 된다')
    else:
        frozen, _, _ = source.read_prepared()
        parent = train_report('train', arm)
        if (r['scratch_core_sha256'] != parent['scratch_core_sha256']
                or r['initial_core_sha256'] != parent['final_core_sha256']
                or r.get('parent_core_sha256') != parent['final_core_sha256']
                or r.get('parent_checkpoint_sha256') != parent['checkpoint_sha256']):
            raise ValueError('SFT에는 같은 경로의 정확한 자기 native 부모가 필요하다')
    for step, e in enumerate(events):
        if any(e.get(k) != v for k, v in update_contract(endpoint, step, frozen).items()):
            raise ValueError('실제 16micro·전체 update 분모·crop·스케줄이 같아야 한다')
        if e.get('actual_lrs') != actual_lrs(r['actual_optimizer_groups'], e['schedule']['lr_factor']):
            raise ValueError('실제 group별 update LR이 원형 스케줄과 다르다')
        if (endpoint == 'native' and e.get('native_replay_ce') is not None
                or endpoint == 'sft' and not finite(e.get('native_replay_ce'))):
            raise ValueError('native replay 성분 또는 종점이 다르다')
    totals = {k: sum(e[k] for e in events) for k in ('targets', 'x_tokens', 'native_replay_targets')}
    if r.get('totals') != totals: raise ValueError('원시 update 합계가 다르다')
    if (not finite(r.get('max_preclip_gradient')) or type(r.get('clip_events')) is not int
            or r.get('max_preclip_gradient') != max(e['gradient_norm'] for e in events)
            or r.get('clip_events') != sum(e['clipped'] for e in events)):
        raise ValueError('원시 gradient 최대 또는 clip 합계가 보고서와 다르다')
    if endpoint == 'sft':
        if not cost and (totals['targets'] != sum(p['counts']['assistant_targets'] for p in frozen['exposure'][SOURCE_ARM])
                or totals['x_tokens'] != sum(p['counts']['x_tokens'] for p in frozen['exposure'][SOURCE_ARM])):
            raise ValueError('같은 원천의 전체 네 pass 합계가 필요하다')
        if cost:
            rr = source.records_for(frozen, SOURCE_ARM, 0)
            expected_x = sum(rr[i].x_tokens for group in source.schedule(0)[:8] for micro in group for i in micro)
            if totals['x_tokens'] != expected_x: raise ValueError('같은 첫 8회 SFT 실행 형태가 필요하다')
    if cost and endpoint == 'native':
        late = r.get('late_probe', {})
        if (late.get('optimizer_updates') != 0 or late.get('micro_batches') != 1 or late.get('targets') != 8192
                or late.get('anneal') != 1. or late.get('core_before') != late.get('core_after')
                or late.get('finite') is not True or not finite(late.get('gradient_norm'))
                or not finite(late.get('seconds'), True) or not finite(late.get('peak_allocated_mib'), True)
                or not finite(late.get('peak_reserved_mib'), True)
                or late.get('core_after') != r['final_core_sha256']):
            raise ValueError('update 없는 별도 late 자원 probe의 성공 증거가 필요하다')
    elif r.get('late_probe') is not None: raise ValueError('late probe는 native 비용 단계에만 허용한다')
    if cost:
        audit = r.get('cache_audit', {})
        if (audit.get('quality_forwards') != 0 or audit.get('optimizer_updates') != 0
                or audit.get('finite') is not True or audit.get('core_before') != r['final_core_sha256']
                or audit.get('core_after') != r['final_core_sha256'] or audit.get('route') != r['route']
                or audit.get('cache_tensors') != r['route']['tlinear_instances']
                or not finite(audit.get('cache_nominal_bytes'), True)
                or not finite(audit.get('extra_cache_storage_bytes'))
                or not finite(audit.get('seconds'), True)
                or not finite(audit.get('peak_allocated_mib'), True) or not finite(audit.get('peak_reserved_mib'), True)):
            raise ValueError('품질 forward·update 없는 별도 전체 TLinear 동결 캐시 검산이 필요하다')
    if not cost:
        validate_native32(r.get('native32_fp32'))
        if r.get('checkpoint') != str(checkpoint(arm, endpoint).relative_to(ROOT)) or digest(checkpoint(arm, endpoint)) != r['checkpoint_sha256']:
            raise ValueError('완료한 정확한 자기 체크포인트가 필요하다')
    elif any(r.get(k) is not None for k in ('checkpoint', 'checkpoint_sha256', 'native32_fp32')):
        raise ValueError('비용 단계는 체크포인트를 쓰거나 품질 평가를 하지 않는다')
    return r


def budget(endpoint, record=False):
    if endpoint not in ENDPOINTS: raise ValueError('native 또는 sft 예산 단계가 필요하다')
    prepared(); spent = spent_seconds(); costs = {a: train_report('cost', a) for a in ARMS}
    if costs['ternary']['scratch_core_sha256'] != costs['float']['scratch_core_sha256']:
        raise ValueError('두 새 초기 본체 fingerprint가 다르다')
    estimates = {}; completed = []
    for arm in ARMS:
        r = costs[arm]; steady = r['step_seconds'][1:]
        if len(steady) != 7: raise ValueError('첫 회를 뺀 native 7회 시간 표본이 필요하다')
        estimates[arm + '_native'] = r['step_seconds'][0] + max(steady) * (UPDATES - 1) * FORECAST_FACTOR + r['late_probe']['seconds'] + 300
        key = phase_key('train', arm)
        if result_path(key).exists(): train_report('train', arm); completed.append(arm + '_native')
    if endpoint == 'sft':
        if len(completed) != 2: raise Pending('실제 SFT 비용 측정 전 양 native 부모가 모두 완료되어야 한다')
        for arm in ARMS:
            r = train_report('sft_cost', arm); steady = r['step_seconds'][1:]
            estimates[arm + '_sft'] = r['step_seconds'][0] + max(steady) * (SFT_UPDATES - 1) * FORECAST_FACTOR + 300
            if result_path(phase_key('sft', arm)).exists(): train_report('sft', arm); completed.append(arm + '_sft')
        sft_reserve = 0.
    else:
        sft_reserve = float(SFT_UNMEASURED_RESERVE)
    pending = sum(value for key, value in estimates.items() if key not in completed)
    needed = pending + sft_reserve + FINISH_RESERVE
    value = dict(info(), status='RESOURCE_FORECAST', endpoint=endpoint, spent_seconds=spent,
        estimates_seconds=estimates, completed=completed, remaining_training_seconds=authority(True),
        remaining_total_seconds=authority(), needed_seconds=needed,
        unmeasured_sft_reserve_seconds=sft_reserve, evaluation_and_record_reserve_seconds=FINISH_RESERVE,
        fits=(spent + needed <= ACTIVE_LIMIT and pending + sft_reserve <= authority(True) and needed <= authority()
            and all(value <= NATIVE_WORKER_LIMIT for name, value in estimates.items() if name.endswith('_native'))),
        late_probe_scope='메모리와 유한한 역전파만 검증한다. 일회 컴파일 시간은 말기 정상 update 시간 추정치가 아니다',
        uncertainty='초기 정상 시간 표본에 사전 지정한 1.35 여유를 곱한 예측이며 말기 속도나 수렴을 보장하지 않는다')
    if record: write(result_path(phase_key('budget', endpoint=endpoint)), value)
    return value


def validate_payload(payload, cfg, arm, endpoint, expected):
    _, _, route = modules()
    if not isinstance(payload, Mapping): raise ValueError('엄격한 체크포인트 mapping이 필요하다')
    route.validate_route_metadata(payload.get('quantization_route'), arm)
    meta = payload.get('experiment', {})
    n = UPDATES if endpoint == 'native' else SFT_UPDATES
    if (set(payload) != {'model', 'cfg', 'step', 'tokenizer_sha256', 'tokenizer_lineage', 'quantization_route', 'experiment'}
            or payload['step'] != n or payload['tokenizer_sha256'] != TOKENIZER_SHA or payload['tokenizer_lineage'] != 'chat32'
            or sha(payload['cfg']) != sha(asdict(cfg)) or meta != expected):
        raise ValueError('자기 경로·tag·단계·cfg·tokenizer·초기화가 모두 같은 엄격한 CP가 필요하다')


def validate_cpu_state(model, payload, torch):
    """CUDA 이동 전에 키·모양·dtype·공유 Parameter 충돌만 검사한다. 복사하지 않는다."""
    current, supplied = model.state_dict(), payload.get('model')
    if not isinstance(supplied, Mapping) or set(supplied) != set(current):
        raise ValueError('CPU 검산에서 정확한 원형 state_dict 키가 필요하다')
    for key, value in current.items():
        other = supplied[key]
        if (not isinstance(other, torch.Tensor) or other.shape != value.shape
                or other.dtype != value.dtype or other.layout != value.layout or other.device.type != 'cpu'):
            raise ValueError('CPU 검산에서 CP 모양·dtype·layout이 다르다: ' + key)
    aliases = {}
    for name, parameter in model.named_parameters(remove_duplicate=False):
        if name in current: aliases.setdefault(id(parameter), []).append(name)
    for names in aliases.values():
        if any(not torch.equal(supplied[names[0]], supplied[name]) for name in names[1:]):
            raise ValueError('CPU 검산에서 공유 Parameter의 CP 값이 충돌한다')


def cp_experiment(r):
    return dict(tag=TAG, arm=r['arm'], endpoint=r['endpoint'], updates=r['updates'],
        reference_sha256=r['reference_sha256'], scratch_core_sha256=r['scratch_core_sha256'],
        parent_checkpoint_sha256=r['parent_checkpoint_sha256'], parent_core_sha256=r['parent_core_sha256'],
        core_sha256=r['final_core_sha256'])


@contextmanager
def routed_runtime(arm, endpoint=None):
    runtime, _, route_method = modules()
    torch, model, cfg, tokenizer, scratch = runtime.load_runtime('scratch_ntp')
    if (scratch == PARENT_CORE or cfg.n_layers != 14 or cfg.dim != 768 or cfg.tie_mlp
            or cfg.vocab_size != 32768 or cfg.max_seq_len != SEQ or cfg.grad_checkpoint is not True or cfg.mtp_aux):
        raise ValueError('새 untied dense14/chat32/seq1024/ckptON 무작위 초기화가 필요하다')
    saved = None; r = None
    if endpoint is not None:
        r = train_report('train' if endpoint == 'native' else 'sft', arm)
        saved = torch.load(checkpoint(arm, endpoint), map_location='cpu', weights_only=True)
        validate_payload(saved, cfg, arm, endpoint, cp_experiment(r)); validate_cpu_state(model, saved, torch)
        if scratch != r['scratch_core_sha256']: raise ValueError('무작위 초기화가 저장한 조건과 달라졌다')
    # 설치 전 CUDA 이동이라는 helper 계약을 유지하되 지원 cfg는 CPU에서 먼저 검산한다.
    with route_method.weight_route(model, arm) as cpu_route: cpu_route.assert_active()
    model = model.cuda(); torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    with route_method.weight_route(model, arm) as route:
        if saved is not None:
            route_method.load_routed_state(model, saved, arm); del saved
            if runtime.state_fingerprint(model) != r['final_core_sha256']: raise ValueError('불러온 자기 경로 본체 SHA가 다르다')
        try:
            yield torch, model, cfg, tokenizer, scratch, route
        finally:
            model.clear_quant()
    del model; gc.collect(); torch.cuda.empty_cache()


def route_receipt(model, route):
    route.assert_active()
    return dict(mode=route.mode, metadata=route.metadata, tlinear_instances=len(route.linears),
        owned_tlinear_instances=sum(getattr(m, '_p106b_weight_route', None) is route for m in route.linears),
        refreshed_tlinear_instances=len(route._versions),
        refresh_methods=sorted({m.refresh_quant.__func__.__name__ for m in route.linears}),
        forward_methods=sorted({m.forward.__func__.__name__ for m in route.linears}),
        forward_call_count='NOT_INSTRUMENTED: 인스턴스와 갱신 수만 기록한다')


def optimizer_receipt(model, optimizers):
    names = {id(p): name for name, p in model.named_parameters()}
    return [dict(optimizer=type(opt).__name__, group=index, lr=float(g['lr']), weight_decay=float(g.get('weight_decay', 0)),
        parameters=sum(p.numel() for p in g['params']), names_sha256=sha([names[id(p)] for p in g['params']]),
        scale_mode=g.get('scale_mode', getattr(opt, 'scale_mode', None)))
        for opt in optimizers for index, g in enumerate(opt.param_groups)]


def make_optimizers(model, endpoint):
    runtime, _, _ = modules(); adam, muon = runtime.optimizers(model)
    before = optimizer_receipt(model, (adam, muon))
    factor = 10. if endpoint == 'native' else .5
    for opt in (adam, muon):
        for g in opt.param_groups:
            g['lr'] *= factor
            if endpoint == 'sft': g['weight_decay'] = 0.
    if getattr(muon, 'scale_mode', None) != 'rms' or any(g.get('weight_decay', 0) != 0 for g in muon.param_groups):
        raise ValueError('RMS4 Muon과 행렬 WD0이 필요하다')
    ids = [id(p) for opt in (adam, muon) for g in opt.param_groups for p in g['params']]
    if len(ids) != len(set(ids)) or set(ids) != {id(p) for p in model.parameters() if p.requires_grad}:
        raise ValueError('모든 학습 Parameter는 정확히 하나의 optimizer group에 속해야 한다')
    receipt = [dict(current, runtime_lr=original['lr'], runtime_weight_decay=original['weight_decay'], lr_multiplier=factor)
        for current, original in zip(optimizer_receipt(model, (adam, muon)), before)]
    validate_optimizer_groups(receipt, endpoint)
    return (adam, muon), receipt


def native_records(tokens, offsets):
    from tinylm.train.mtp_sft import Record
    records = []
    for offset in offsets:
        if not 0 <= int(offset) < len(tokens) - SEQ: raise ValueError('선언한 native 풀 안의 완전한 target window가 필요하다')
        values = tokens[int(offset):int(offset) + SEQ + 1]
        records.append(Record(values[:-1].astype('int64').tolist(), values[1:].astype('int64').tolist(), [1] * SEQ))
    return records


def backward_micro(model, forward, records, denominator, torch):
    from tinylm.train import mtp_sft as core
    if len(records) != MICRO or denominator <= 0: raise ValueError('micro8과 양수인 전체 update 분모가 필요하다')
    x, y, segments = core.pad_records(records, 0, 'cuda', fixed_width=SEQ, batch_size=MICRO)
    with torch.autocast('cuda', dtype=torch.bfloat16):
        sums, counts = core.components(model, forward(x, return_hidden=True), y, segments, horizons=())
        loss = sums[1] / denominator
    if counts[1] != sum(r.targets for r in records) or not bool(torch.isfinite(loss)):
        raise ValueError('유한한 micro CE와 정확한 target 수가 필요하다')
    loss.backward()
    return float(sums[1].detach()), counts[1], sum(r.x_tokens for r in records)


def native_probe(torch, model):
    import numpy as np
    from tinylm.train import mtp_sft as core
    from torch.nn.attention import sdpa_kernel, SDPBackend
    was_training = model.training; total = 0.; targets = 0
    tokens = np.memmap(VAL, dtype=np.uint16, mode='r')
    model.clear_quant(); model.eval(); model.set_anneal(1.); model.freeze_quant()
    try:
        with torch.no_grad(), torch.autocast('cuda', enabled=False), sdpa_kernel(SDPBackend.MATH):
            for start in range(0, 32, MICRO):
                records = native_records(tokens, [i * SEQ for i in range(start, start + MICRO)])
                x, y, s = core.pad_records(records, 0, 'cuda', fixed_width=SEQ, batch_size=MICRO)
                sums, counts = core.components(model, model(x, return_hidden=True), y, s, horizons=(), checkpoint_heads=False)
                if not bool(torch.isfinite(sums[1])): raise ValueError('유한한 native32 FP32 평가가 필요하다')
                total += float(sums[1]); targets += counts[1]
    finally:
        model.clear_quant(); model.train(was_training)
    if targets != 32768: raise ValueError('같은 32개 완전한 native VAL crop이 필요하다')
    return dict(ce=total / targets, targets=targets, windows=32, val_sha256=VAL_SHA,
        precision='FP32_MATH', scope='고정 1024 길이의 첫 32개 crop이며 전체 VAL 또는 두 언어 능력 평가가 아니다')


def late_probe(torch, model, forward, optimizers, tokens, offsets):
    runtime, _, _ = modules(); before = runtime.state_fingerprint(model); saved = float(model.cfg.quant_anneal)
    for opt in optimizers: opt.zero_grad(set_to_none=True)
    model.clear_quant(); model.set_anneal(1.); torch.cuda.reset_peak_memory_stats(); began = time.perf_counter()
    try:
        numerator, targets, _ = backward_micro(model, forward, native_records(tokens, offsets[:MICRO]), 8192, torch)
        grad = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
        if not bool(torch.isfinite(grad)): raise ValueError('late QAT 역전파에서 유한하지 않은 gradient가 발생했다')
        torch.cuda.synchronize(); seconds = time.perf_counter() - began
        allocated, reserved = torch.cuda.max_memory_allocated() / 2**20, torch.cuda.max_memory_reserved() / 2**20
    finally:
        for opt in optimizers: opt.zero_grad(set_to_none=True)
        model.clear_quant(); model.set_anneal(saved)
    after = runtime.state_fingerprint(model)
    if before != after: raise ValueError('역전파만 하는 late probe가 모델 상태를 바꾸었다')
    return dict(optimizer_updates=0, micro_batches=1, targets=targets, anneal=1., finite=math.isfinite(numerator), gradient_norm=float(grad),
        seconds=seconds, peak_allocated_mib=allocated, peak_reserved_mib=reserved,
        core_before=before, core_after=after, source_offsets_sha256=sha([int(v) for v in offsets[:MICRO]]),
        scope='추가 자원 probe이며 예정 optimizer 토큰이나 말기 정상 속도에 합산하지 않는다')


def cache_audit(torch, model, route):
    """품질 forward 없이 모든 TLinear의 최종 평가 캐시만 별도로 검산한다."""
    runtime, _, _ = modules(); before = runtime.state_fingerprint(model)
    training, anneal = model.training, float(model.cfg.quant_anneal)
    model.clear_quant(); model.eval(); model.set_anneal(1.)
    torch.cuda.reset_peak_memory_stats(); began = time.perf_counter()
    try:
        with torch.no_grad(), torch.autocast('cuda', enabled=False):
            model.freeze_quant(); nominal = 0; extra = {}; master = {p.data_ptr() for p in model.parameters()}
            for module in route.linears:
                cached = module._wq
                if (cached is None or cached.dtype != module.weight.dtype or cached.shape != module.weight.shape
                        or not bool(torch.isfinite(cached).all())
                        or route._versions.get(id(module)) != module.weight._version):
                    raise ValueError('모든 TLinear 캐시의 모양·유한성·실제 버전이 일치해야 한다')
                nominal += cached.numel() * cached.element_size()
                if cached.data_ptr() not in master: extra[cached.data_ptr()] = cached.untyped_storage().nbytes()
            receipt = route_receipt(model, route); validate_route_receipt(receipt, route.mode)
            if receipt['refreshed_tlinear_instances'] != len(route.linears):
                raise ValueError('전체 TLinear 평가 캐시가 실제로 갱신되어야 한다')
        torch.cuda.synchronize(); seconds = time.perf_counter() - began
        allocated, reserved = torch.cuda.max_memory_allocated() / 2**20, torch.cuda.max_memory_reserved() / 2**20
    finally:
        model.clear_quant(); model.set_anneal(anneal); model.train(training)
    after = runtime.state_fingerprint(model)
    if before != after: raise ValueError('캐시 검산이 학습 가중치를 변경했다')
    return dict(quality_forwards=0, optimizer_updates=0, finite=True, route=receipt,
        cache_tensors=len(route.linears), cache_nominal_bytes=nominal, extra_cache_storage_bytes=sum(extra.values()),
        seconds=seconds, peak_allocated_mib=allocated, peak_reserved_mib=reserved, core_before=before, core_after=after,
        scope='학습·late probe와 분리한 allocator 최고값이며 전체 장치 메모리나 품질 평가가 아니다')


def train(arm, endpoint='native', cost=False, max_wall_sec=NATIVE_WORKER_LIMIT):
    reference, frozen, _, offsets = prepared(); authority(training=True)
    runtime, source, _ = modules()
    mode = ('cost' if cost else 'train') if endpoint == 'native' else ('sft_cost' if cost else 'sft')
    key = phase_key(mode, arm); directory = safe(RAW / key)
    if directory.exists() or result_path(key).exists() or (not cost and checkpoint(arm, endpoint).exists()):
        raise FileExistsError('이전 완료 또는 부분 arm 산출물을 보존한다')
    parent = None
    if endpoint == 'sft':
        for a in ARMS: train_report('train', a)
        parent = train_report('train', arm)
    reservation = None
    if not cost:
        completed_activity('budget', endpoint=endpoint)
        reservation = budget(endpoint)
        if not reservation['fits']: raise Pending('보수적 전체 단계 자원 예측이 허용 범위에 들어오지 않는다')
        if reservation['estimates_seconds'][arm + '_' + endpoint] > max_wall_sec:
            raise Pending('보수적 arm 예측이 이 worker의 정확한 시간 상한을 넘는다')
    from scripts.p106b_gate_runtime import idle_before_gpu
    idle_before_gpu(); authority(training=True)
    import numpy as np
    tokens = np.memmap(TRAIN, dtype=np.uint16, mode='r')
    if len(tokens) != TRAIN_TOKENS: raise ValueError('정확한 TRAIN 토큰 크기가 필요하다')
    with routed_runtime(arm, 'native' if endpoint == 'sft' else None) as (torch, model, cfg, tok, scratch, route):
        actual_initial = runtime.state_fingerprint(model)
        if actual_initial != (parent['final_core_sha256'] if parent else scratch):
            raise ValueError('첫 update 전 실제 초기화 또는 자기 부모 본체 fingerprint가 다르다')
        if not cost:
            actual_cost = train_report('cost' if endpoint == 'native' else 'sft_cost', arm)
            if scratch != actual_cost['scratch_core_sha256']: raise ValueError('비용 측정과 학습의 무작위 초기 fingerprint가 같아야 한다')
        if endpoint == 'native':
            for other in ARMS:
                if other != arm and result_path(phase_key('cost', other)).exists():
                    if train_report('cost', other)['scratch_core_sha256'] != scratch: raise ValueError('짝지은 두 무작위 초기화가 다르다')
        model.train(); model.set_anneal(0. if endpoint == 'native' else 1.)
        torch.cuda.reset_peak_memory_stats()
        os.environ['TORCHINDUCTOR_CACHE_DIR'] = str(CACHE / ('compile_' + key))
        forward = torch.compile(model, mode='default')
        try:
            optimizers, groups = make_optimizers(model, endpoint)
            if not cost and groups != actual_cost['actual_optimizer_groups']: raise ValueError('비용 측정과 학습의 실제 optimizer group이 같아야 한다')
            bases = [[g['lr'] for g in opt.param_groups] for opt in optimizers]
            writer = ShardWriter(directory, 'updates', limit=19_999_999)
            n = 8 if cost else UPDATES if endpoint == 'native' else SFT_UPDATES
            windows = None
            if endpoint == 'sft':
                from scripts.p106b_native_windows import reader
                windows = reader(ROOT, frozen)
                if len(windows) != SFT_UPDATES * MICRO: raise ValueError('같은 절대 update의 SFT native window 벡터가 필요하다')
            steps = 0; times = []; totals = Counter(); gmax = 0.; clips = 0; cache_epoch = None; records = None
            began = time.perf_counter()
            for step in range(n):
                authority(training=True); route.assert_active(); tick = time.perf_counter()
                for opt in optimizers: opt.zero_grad(set_to_none=True)
                policy = schedule(step) if endpoint == 'native' else dict(lr_factor=1., anneal=1.)
                for opt, rates in zip(optimizers, bases):
                    for g, base in zip(opt.param_groups, rates): g['lr'] = base * policy['lr_factor']
                model.set_anneal(policy['anneal']); observed = 0; numerator = 0.; x_tokens = 0
                if endpoint == 'native':
                    chosen = offsets[step * MICRO * ACCUM:(step + 1) * MICRO * ACCUM]
                    denominator = TARGETS
                    micros = [native_records(tokens, chosen[i:i + MICRO]) for i in range(0, MICRO * ACCUM, MICRO)]
                else:
                    epoch, slot = divmod(step, 96)
                    if cache_epoch != epoch: records = source.records_for(frozen, SOURCE_ARM, epoch); cache_epoch = epoch
                    groups_of_indices = source.schedule(epoch)[slot]
                    micros = [[records[i] for i in micro] for micro in groups_of_indices]
                    denominator = sum(r.targets for micro in micros for r in micro)
                    if denominator != frozen['exposure'][SOURCE_ARM][epoch]['update_target_denominators'][slot]:
                        raise ValueError('같은 전체 update의 SFT 분모가 필요하다')
                if len(micros) != ACCUM: raise ValueError('정확히 16개 물리 microbatch가 필요하다')
                for batch in micros:
                    total, count, used = backward_micro(model, forward, batch, denominator, torch)
                    numerator += total; observed += count; x_tokens += used
                if observed != denominator: raise ValueError('실제 전체 update의 target 합계가 다르다')
                native_ce = None
                if endpoint == 'sft':
                    from tinylm.train.mtp_sft import Record
                    rr = [Record(a[:-1].astype('int64').tolist(), a[1:].astype('int64').tolist(), [1] * SEQ)
                          for a in windows[step * MICRO:(step + 1) * MICRO]]
                    total, count, _ = backward_micro(model, forward, rr, 8192, torch)
                    if count != 8192: raise ValueError('같은 절대 update의 native replay8192가 필요하다')
                    native_ce = total / count
                grad = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                if not bool(torch.isfinite(grad)): raise ValueError('유한하지 않은 gradient이므로 optimizer update를 하지 않는다')
                gmax = max(gmax, float(grad)); clips += int(grad > 1.)
                for opt in optimizers: opt.step()
                steps += 1; torch.cuda.synchronize(); seconds = time.perf_counter() - tick; times.append(seconds)
                event = dict(update=steps, targets=observed, x_tokens=x_tokens, ce=numerator / denominator,
                    native_replay_ce=native_ce, native_replay_targets=8192 if endpoint == 'sft' else 0,
                    crop_start=step * MICRO * ACCUM if endpoint == 'native' else None,
                    schedule=policy, actual_lrs=[[float(g['lr']) for g in opt.param_groups] for opt in optimizers],
                    gradient_norm=float(grad), clipped=bool(grad > 1.), step_seconds=seconds)
                writer.append(event); totals.update(targets=observed, x_tokens=x_tokens, native_replay_targets=event['native_replay_targets'])
                if cost or steps % 100 == 0 or steps == n:
                    print('[NATIVE_ROUTE_UPDATE] ' + json.dumps(dict(arm=arm, endpoint=endpoint, **event)), flush=True)
            primary_peak = dict(allocated_mib=torch.cuda.max_memory_allocated() / 2**20, reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
            late = late_probe(torch, model, forward, optimizers, tokens, offsets) if cost and endpoint == 'native' else None
            if not cost and endpoint == 'native' and totals['targets'] != DRAW_TOKENS: raise ValueError('native target 298975232개 전체가 필요하다')
            if not cost and endpoint == 'sft':
                if (totals['targets'] != sum(r['counts']['assistant_targets'] for r in frozen['exposure'][SOURCE_ARM])
                        or totals['native_replay_targets'] != SFT_UPDATES * 8192): raise ValueError('원천 네 pass와 native replay target 전체가 필요하다')
            model.clear_quant(); model.set_anneal(1.)
            final_core = runtime.state_fingerprint(model); native32 = None if cost else native_probe(torch, model)
            cache = cache_audit(torch, model, route) if cost else None
            lineage = dict(tag=TAG, arm=arm, endpoint=endpoint, cost=cost, reference_sha256=digest(CACHE / 'frozen_reference.json'))
            manifest = writer.close(lineage=lineage); verify(directory, manifest)
            result = dict(info(), status='COST_COMPLETE' if cost else 'TRAIN_COMPLETE', arm=arm, endpoint=endpoint,
                cost=cost, updates=steps, reference_sha256=lineage['reference_sha256'],
                scratch_core_sha256=scratch, initial_core_sha256=actual_initial,
                final_core_sha256=final_core, parent_checkpoint_sha256=parent['checkpoint_sha256'] if parent else None,
                parent_core_sha256=parent['final_core_sha256'] if parent else None,
                actual_optimizer_groups=groups, route=cache['route'] if cache else route_receipt(model, route),
                quantization_route=route.metadata, cache_audit=cache,
                step_seconds=times, totals=dict(totals), event_manifest=manifest, late_probe=late,
                primary_peak=primary_peak, max_preclip_gradient=gmax, clip_events=clips,
                native32_fp32=native32, reservation=reservation, whole_seconds=time.perf_counter() - began,
                optimizer_saved=False, checkpoint_writes=0 if cost else 1, actual_quality='NOT_EVALUATED')
            if not cost:
                out = safe(checkpoint(arm, endpoint))
                with out.open('xb') as stream:
                    torch.save(dict(model=model.state_dict(), cfg=asdict(cfg), step=steps,
                        tokenizer_sha256=TOKENIZER_SHA, tokenizer_lineage='chat32', quantization_route=route.metadata,
                        experiment=cp_experiment(result)), stream)
                result.update(checkpoint=str(out.relative_to(ROOT)), checkpoint_sha256=digest(out))
            write(result_path(key), result)
        finally:
            del forward
    print('[NATIVE_ROUTE_FINAL] ' + json.dumps(dict(arm=arm, endpoint=endpoint, cost=cost, updates=steps)), flush=True)
    return 0


def evaluate(arm, endpoint):
    execution_remaining()
    reference, _, cases, _ = prepared(); r = train_report('train' if endpoint == 'native' else 'sft', arm)
    key = phase_key('evaluate', arm, endpoint); directory = safe(RAW / key)
    if directory.exists() or result_path(key).exists(): raise FileExistsError('이전 평가 산출물을 보존한다')
    from scripts.p106b_gate_runtime import idle_before_gpu
    idle_before_gpu(); execution_remaining()
    runtime, source, _ = modules()
    from scripts import diag_p106b_span_readout as receipts
    with routed_runtime(arm, endpoint) as (torch, model, cfg, tok, scratch, route):
        model.eval(); model.set_anneal(1.); model.freeze_quant()
        before = runtime.state_fingerprint(model); writer = ShardWriter(directory, 'answers', limit=19_999_999)
        summaries = Counter(); count = 0
        with torch.no_grad():
            for case in cases:
                execution_remaining(); route.assert_active()
                answer, generation = source.emit64(model, cfg, tok, case['messages'])
                from tinylm.chat.serialize import serialize
                prompt = serialize(dict(messages=case['messages']), 'chatml', add_generation_prompt=True)
                adapted = dict(inference=dict(prompt=prompt), encoding=dict(ids=tok.encode(prompt).ids))
                receipts.validate_vocabulary(dict(answer=answer, generation=generation), adapted, tok)
                if generation.get('max_new') != MAX_NEW: raise ValueError('실제 greedy64 생성 영수증이 필요하다')
                metric = source.classify_case(case, answer)
                event = dict(id=case['id'], case_sha256=sha(case), answer=answer, generation=generation, metrics=metric,
                    arm=arm, endpoint=endpoint, checkpoint_sha256=r['checkpoint_sha256'], quantization_route=route.metadata)
                writer.append(event); count += 1
                summaries[case['lane'] + ':' + case['language']] += 1
                if count % 100 == 0: print('[NATIVE_ROUTE_ANSWERS] ' + json.dumps(dict(arm=arm, endpoint=endpoint, actual=count)), flush=True)
                if case['id'] in reference['display_ids']:
                    print('[NATIVE_ROUTE_SAMPLE] ' + json.dumps(dict(arm=arm, endpoint=endpoint, id=case['id'],
                        language=case['language'], family=case['family'], messages=case['messages'], answer=answer,
                        finish_reason=generation['finish_reason'], generated_tokens=generation['generated_tokens']), ensure_ascii=False), flush=True)
        model.clear_quant(); native32 = native_probe(torch, model); after = runtime.state_fingerprint(model)
        if before != after or digest(checkpoint(arm, endpoint)) != r['checkpoint_sha256']: raise ValueError('평가가 자기 경로 모델 또는 체크포인트를 바꾸었다')
        lineage = dict(tag=TAG, arm=arm, endpoint=endpoint, checkpoint_sha256=r['checkpoint_sha256'],
            core_sha256=before, cases_sha256=sha(cases), quantization_route=route.metadata)
        manifest = writer.close(lineage=lineage); verify(directory, manifest)
        if count != ANSWERS: raise ValueError('실제 첫 답 1694개 전체가 필요하다')
        result = dict(info(), status='ACTUAL_ANSWERS_COLLECTED', arm=arm, endpoint=endpoint,
            actual_cases=count, case_counts=dict(summaries), cases_sha256=sha(cases), raw_manifest=manifest,
            lineage=lineage, core_before=before, core_after=after, native32_fp32=native32,
            checkpoint_sha256=r['checkpoint_sha256'], quantization_route=route.metadata,
            route=route_receipt(model, route), scope='ChatML 학습 전 native와 학습 후 SFT는 별개 종점이며 합산하지 않는다')
        write(result_path(key), result)
    return 0


def readback():
    execution_remaining()
    _, _, cases, _ = prepared(); runtime, source, route = modules()
    from scripts import diag_p106b_span_readout as receipts
    from tokenizers import Tokenizer
    from tinylm.chat.serialize import serialize
    tokenizer = Tokenizer.from_file(str(TOKENIZER)); lookup = {c['id']: c for c in cases}; summaries = []
    for arm in ARMS:
        for endpoint in ENDPOINTS:
            execution_remaining()
            key = phase_key('evaluate', arm, endpoint); completed_activity('evaluate', arm, endpoint)
            report = required(result_path(key)); cp = train_report('train' if endpoint == 'native' else 'sft', arm)
            if (report.get('status') != 'ACTUAL_ANSWERS_COLLECTED' or report.get('checkpoint_sha256') != cp['checkpoint_sha256']
                    or report.get('core_before') != report.get('core_after') or report.get('core_before') != cp['final_core_sha256']
                    or report.get('cases_sha256') != sha(cases) or any(report.get(k) != v for k, v in info().items())):
                raise ValueError('같은 경로·단계·CP의 완전한 평가가 필요하다')
            route.validate_route_metadata(report['quantization_route'], arm)
            validate_route_receipt(report.get('route', {}), arm)
            validate_native32(report.get('native32_fp32'))
            expected_lineage = dict(tag=TAG, arm=arm, endpoint=endpoint, checkpoint_sha256=cp['checkpoint_sha256'],
                core_sha256=cp['final_core_sha256'], cases_sha256=sha(cases), quantization_route=route.route_metadata(arm))
            directory = RAW / key; manifest = report['raw_manifest']
            if (manifest.get('rows') != ANSWERS or not manifest.get('shards')
                    or manifest.get('lineage') != expected_lineage or report.get('lineage') != expected_lineage
                    or manifest.get('limit_bytes') != 19_999_999 or report.get('actual_cases') != ANSWERS
                    or any(p.get('path') != f'answers_{i:06d}.jsonl' for i, p in enumerate(manifest['shards']))
                    or required(directory / 'answers_shards_manifest.json') != manifest):
                raise ValueError('읽기 전에 이 단계의 완전한 답변 manifest가 필요하다')
            verify(directory, manifest); events = []
            for part in manifest['shards']:
                with safe(directory / part['path']).open(encoding='utf-8') as stream: events.extend(json.loads(line) for line in stream)
            if len(events) != ANSWERS or {e['id'] for e in events} != set(lookup): raise ValueError('같은 문항의 고유한 실제 답변 1694개 전체가 필요하다')
            for e in events:
                case = lookup[e['id']]; prompt = serialize(dict(messages=case['messages']), 'chatml', add_generation_prompt=True)
                if (e['case_sha256'] != sha(case) or e['arm'] != arm or e['endpoint'] != endpoint
                        or e['checkpoint_sha256'] != cp['checkpoint_sha256'] or e['quantization_route'] != route.route_metadata(arm)
                        or e['metrics'] != source.classify_case(case, e['answer'])): raise ValueError('같은 원시 문항의 경로 또는 의미 계약 재집계가 다르다')
                receipts.validate_vocabulary(dict(answer=e['answer'], generation=e['generation']),
                    dict(inference=dict(prompt=prompt), encoding=dict(ids=tokenizer.encode(prompt).ids)), tokenizer)
                if e['generation'].get('max_new') != MAX_NEW: raise ValueError('실제 최대 생성 64 계약이 같아야 한다')
            summaries.append(dict(arm=arm, endpoint=endpoint, summary=source.recount(events, cases, tokenizer),
                native32_fp32=report['native32_fp32'], checkpoint_sha256=cp['checkpoint_sha256']))
    write(result_path('readback'), dict(info(), status='ALL_ROUTE_ENDPOINTS_RECOUNTED', summaries=summaries,
        models_loaded=0, checkpoint_tensor_loads=0, source_language_ratio='NOT_MEASURED',
        limitation='기존 교육법의 네 종점을 분리 비교하며 범용 assistant·Falcon·75M 완료를 주장하지 않는다'))
    print('[NATIVE_ROUTE_RECOUNT] 네 종점과 실제 답변 ID 검산 완료', flush=True)
    return 0


@contextmanager
def termination_guard():
    """자기 worker의 SIGTERM도 실패 activity를 쓰는 finally 경로로 보낸다."""
    previous = signal.getsignal(signal.SIGTERM)
    def terminate(*_args): raise KeyboardInterrupt('자기 worker 종료 요청으로 실패 기록을 남긴다')
    signal.signal(signal.SIGTERM, terminate)
    try: yield
    finally: signal.signal(signal.SIGTERM, previous)


def worker(mode, arm, endpoint, max_wall_sec):
    key = phase_key(mode, arm, endpoint)
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 21600:
        raise ValueError('60~21600초의 시간 상한을 명시해야 한다')
    if mode in ('cost', 'train') and max_wall_sec > NATIVE_WORKER_LIMIT:
        raise ValueError('native worker는 명시한 4시간 상한을 넘으면 안 된다')
    if mode in ('source', 'preflight'):
        execution_remaining(); source_state() if mode == 'source' else prepared()
        print('[NATIVE_ROUTE_PREFLIGHT] 정확한 원천·조건·CPU reader 검산, 모델0', flush=True); return 0
    activity = EVIDENCE / ('activity_' + key + '.json')
    if safe(activity).exists(): raise FileExistsError('이전 activity를 보존하며 묵시적으로 재시도하지 않는다')
    metadata = info(); began = time.perf_counter(); start = datetime.now(timezone.utc).isoformat(); code = 9; error = None
    try:
        is_training = mode in ('cost', 'train', 'sft_cost', 'sft', 'prepare')
        if max_wall_sec > min(execution_remaining(is_training), ACTIVE_LIMIT - spent_seconds()): raise Pending('worker 상한이 남은 권한 또는 활동 총상한을 넘는다')
        from scripts.p106b_gate_runtime import wall_limit
        with termination_guard(), wall_limit(max_wall_sec):
            if mode == 'prepare':
                code = prepare()
                write(result_path(key), dict(status='CPU_REFERENCE_COMPLETE', reference_sha256=digest(CACHE / 'frozen_reference.json')))
            elif mode == 'budget':
                forecast = budget(endpoint, record=True); code = 0 if forecast['fits'] else 8
            elif mode in ('cost', 'train', 'sft_cost', 'sft'):
                code = train(arm, 'sft' if mode in ('sft_cost', 'sft') else 'native', mode in ('cost', 'sft_cost'), max_wall_sec)
            elif mode == 'evaluate': code = evaluate(arm, endpoint)
            elif mode == 'readback': code = readback()
            else: raise ValueError('등록된 worker 단계가 필요하다')
        if code == 0 and (not result_path(key).is_file() or metadata['code_sha256'] != info()['code_sha256']):
            raise ValueError('종료 0에는 같은 코드의 완전한 자기 결과가 필요하다')
        return code
    except BaseException as exc:
        error = type(exc).__name__; code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (Pending, FileNotFoundError, FileExistsError)) else 9
        raise
    finally:
        result = result_path(key); reference = CACHE / 'frozen_reference.json'
        write(activity, dict(schema=SCHEMA, tag=TAG, key=key, mode=mode, arm=arm, endpoint=endpoint,
            seconds=time.perf_counter() - began, started_at=start, ended_at=datetime.now(timezone.utc).isoformat(),
            returncode=code, complete=code == 0, error_type=error, max_wall_sec=max_wall_sec,
            code_sha256=metadata['code_sha256'], result_sha256=digest(result) if result.is_file() else None,
            reference_sha256=digest(reference) if reference.is_file() else None))


def phase_commands(mode, arm, endpoint, max_wall_sec):
    phase_key(mode, arm, endpoint)
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 21600: raise ValueError('60~21600초의 시간 상한을 명시해야 한다')
    if mode in ('cost', 'train') and max_wall_sec > NATIVE_WORKER_LIMIT:
        raise ValueError('native worker는 명시한 4시간 상한을 넘으면 안 된다')
    py = [sys.executable, '-B', '-X', 'utf8']; base = py + ['scripts/diag_p106b_native_weight_route.py']
    actual = base + ['--mode', mode, '--worker', '--execute', '--max-wall-sec', str(max_wall_sec)]
    if arm: actual += ['--arm', arm]
    if endpoint: actual += ['--endpoint', endpoint]
    prior = 'source' if mode in ('source', 'prepare') else 'preflight'
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_weight_route', 'scripts.test_p106b_native_weight_route', '-v']),
        ('PREFLIGHT', base + ['--mode', prior, '--worker', '--execute', '--max-wall-sec', '600']), ('EXECUTE', actual)]


def launch(command, timeout):
    process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, start_new_session=True)
    try: return process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        interrupted = sys.exc_info()[0] is KeyboardInterrupt
        if process.poll() is None and os.getpgid(process.pid) == process.pid:
            os.killpg(process.pid, signal.SIGTERM)
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if process.poll() is None: os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        return 130 if interrupted else 124


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, required=True); parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--endpoint', choices=ENDPOINTS); parser.add_argument('--max-wall-sec', type=int, default=600)
    parser.add_argument('--worker', action='store_true'); action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        phases = phase_commands(args.mode, args.arm, args.endpoint, args.max_wall_sec)
        if args.check_only:
            print('[NATIVE_ROUTE_CHECK_ONLY] ' + json.dumps(info(), ensure_ascii=False), flush=True); return 0
        if args.worker: return worker(args.mode, args.arm, args.endpoint, args.max_wall_sec)
        return pipeline(phases, lambda cmd: launch(cmd, min(args.max_wall_sec + 120, execution_remaining(args.mode in ('prepare', 'cost', 'train', 'sft_cost', 'sft')))),
            lambda line: print(line, flush=True), experiment='P106B_NATIVE_ROUTE_' + phase_key(args.mode, args.arm, args.endpoint))['returncode']
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (Pending, FileNotFoundError, FileExistsError)) else 9
        if code == 9: traceback.print_exc(file=sys.stderr)
        print('[NATIVE_ROUTE_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True); return code


if __name__ == '__main__': raise SystemExit(main())
