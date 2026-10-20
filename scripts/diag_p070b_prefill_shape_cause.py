#!/usr/bin/env python3
"""입력 길이·cache 플래그·미래 내용을 분리하는 CPU 관측 도구.

진단 완료는 모든 고정 대조가 기록되었다는 뜻뿐이다. 원 게이트 종료9와
수치 문턱은 유지하며, cache 무결성·언어품질·route 학습을 승인하지 않는다.
실물 자산과 모델은 별도 권한으로 실행하는 bounded worker만 읽는다.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p070b_full_checkpoint_cpu as old

TAG, SCHEMA = 'p070b_prefill_shape_cause_v1_s1337', 'P070B_PREFILL_SHAPE_CAUSE_CPU_V1'
SCRIPT, TEST = 'scripts/diag_p070b_prefill_shape_cause.py', 'scripts/test_p070b_prefill_shape_cause.py'
CACHE, RAW, EVIDENCE = (ROOT / p / TAG for p in ('data_cache', 'runs/eval', 'test_result/evidence'))
F4 = ROOT / 'handoff/audit/WIP_20261019b_P070B_PREFILL_SHAPE_CAUSE_F4.json'
PARENT, PARENT_SHA, PARENT_CORE = old.PARENT, old.PARENT_SHA, old.PARENT_CORE
TOKENIZER, TOKENIZER_SHA = old.TOKENIZER, old.TOKENIZER_SHA
OLD_FAILURE = ROOT / 'test_result/evidence/p070b_full_model_cache_v1_s1337/failure.json'
OLD_RAW = ROOT / 'runs/eval/p070b_full_model_cache_v1_s1337/failure_r2_reverse_ko.npz'
OLD_FAILURE_SHA = 'CF707AAA4927746636C797F66D5724AE9D35413F17135A354E54F80623ACAD32'
OLD_RAW_SHA = '31D4590CEDB8E8DB130CEA4FD7607BB9BFC5ED8EEE030B1CB9CCDAD29C8DECC8'
END, RECORD_RESERVE, MAX_WALL, LIMIT = old.END, 600, 600, 20_000_000
ATOL, RTOL, PREFILL, INPUTS, ORDINARY_START = 1e-5, 1e-4, 3, 9, 35
PROBES = ('A', 'Aon', 'B', 'C', 'D', 'E')
CONTRASTS = ('A_vs_old_full', 'D_vs_old_cached', 'A_vs_D', 'A_vs_Aon',
             'A_prefix_vs_B', 'B_vs_C', 'A_prefix_vs_E_prefix')
LIMITATIONS = dict(old_gate_status='ERROR9_PRESERVED', old_gate_pass=False,
    threshold_changed=False, route_training_admitted=False, parent_is_r2_trained=False,
    language_quality='NOT_RUN', generation='NOT_RUN', optimizer_updates=0,
    checkpoint_writes=0, gpu_calls=0, cause='UNDETERMINED',
    completion_meaning='고정한 모든 대조의 실제 기록만 뜻하며 원 게이트 PASS가 아니다')
Pending, sha, canonical, seal = old.Pending, old.sha, old.canonical, old.seal


def safe(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(ROOT):
        raise ValueError('저장소 안의 정확한 절대 경로가 필요하다')
    for p in (path, *path.parents):
        if p.is_symlink(): raise ValueError('심볼릭 링크는 허용하지 않는다')
        if p == ROOT: break
    return path


def digest(path):
    path = safe(path)
    if not path.is_file(): raise Pending('필수 파일이 없다: ' + str(path.relative_to(ROOT)))
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): value.update(block)
    return value.hexdigest().upper()


def read_json(path):
    path = safe(path)
    if not path.is_file(): raise Pending('필수 JSON이 없다')
    if path.stat().st_size >= LIMIT: raise ValueError('JSON은20MB 미만이어야 한다')
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path = safe(path)
    if not any(path.is_relative_to(p) for p in (CACHE, RAW, EVIDENCE)):
        raise ValueError('새 namespace 밖 쓰기는 금지한다')
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(payload) >= LIMIT: raise ValueError('공개 JSON은20MB 미만이어야 한다')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(payload)


def info():
    legacy = old.info(); pins = dict(legacy['code_sha256'])
    for path in (SCRIPT, TEST): pins[path] = digest(ROOT / path) if safe(ROOT / path).is_file() else 'NOT_CREATED'
    return canonical(dict(schema=SCHEMA, tag=TAG, code_sha256=pins,
        code_complete=all(v != 'NOT_CREATED' for v in pins.values()), f4_sha256=digest(F4),
        legacy_recipe_sha256=sha(legacy), parent=str(PARENT.relative_to(ROOT)), parent_sha256=PARENT_SHA,
        parent_core_sha256=PARENT_CORE, tokenizer_sha256=TOKENIZER_SHA, shape=legacy['shape'],
        old_failure=str(OLD_FAILURE.relative_to(ROOT)), old_failure_sha256=OLD_FAILURE_SHA,
        old_raw=str(OLD_RAW.relative_to(ROOT)), old_raw_sha256=OLD_RAW_SHA,
        inputs=INPUTS, prefill=PREFILL, ordinary_id_start=ORDINARY_START,
        future_control='first3 unchanged; last6 -> 35+((id-35+1)%(vocab-35)); no special IDs',
        route='fixed reverse R2, same permuted body in both cycles',
        probes=list(PROBES), contrasts=list(CONTRASTS), atol=ATOL, rtol=RTOL,
        device='cpu', dtype='float32', attention='SDPA_MATH', torch_threads=1,
        authority_end_utc=END.isoformat(), record_reserve_seconds=RECORD_RESERVE,
        worker_max_seconds=MAX_WALL, limitations=LIMITATIONS))


def authority(seconds=MAX_WALL, now=None):
    old.cap(seconds); now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None: raise ValueError('시간대가 명시된 시각이 필요하다')
    remaining = (END - now).total_seconds() - RECORD_RESERVE
    if remaining < seconds: raise Pending('기한 전600초 기록 예비를 침범한다')
    return remaining


def parent_preflight(seconds):
    return old.preflight(seconds, require_fresh=False)


def validate_old_failure(value):
    unsigned = {k: v for k, v in value.items() if k != 'integrity_sha256'}
    if (value.get('integrity_sha256') != sha(unsigned) or value.get('status') != 'CPU_TOLERANCE_FAILED'
            or value.get('complete') is not False or value.get('route') != 'r2_reverse'
            or value.get('language') != 'ko' or value.get('comparison_kind') != 'FULL_VS_CACHED'
            or value.get('parent_sha256') != PARENT_SHA or value.get('parent_core_sha256') != PARENT_CORE
            or sha(value.get('recipe')) != info()['legacy_recipe_sha256']
            or value.get('input_ids') != INPUTS or value.get('raw', {}).get('sha256') != OLD_RAW_SHA
            or value['raw']['comparison'].get('close') is not False
            or value['raw']['comparison'].get('atol') != ATOL or value['raw']['comparison'].get('rtol') != RTOL):
        raise ValueError('원래의 reverseR2/KO 수치 음성과 원 문턱이 정확히 일치해야 한다')


def preflight(seconds=MAX_WALL, *, fresh=True):
    authority(seconds); recipe = info()
    if not recipe['code_complete']: raise Pending('새 두 파일과 전체 CODE pin이 필요하다')
    if fresh and any(safe(p).exists() for p in (CACHE, RAW, EVIDENCE)):
        raise FileExistsError('기존 완료/부분 namespace를 보존하며 재시도하지 않는다')
    parent = parent_preflight(seconds)
    if digest(OLD_FAILURE) != OLD_FAILURE_SHA or digest(OLD_RAW) != OLD_RAW_SHA:
        raise ValueError('원래 failure/raw SHA가 다르다')
    original = read_json(OLD_FAILURE); validate_old_failure(original)
    with zipfile.ZipFile(OLD_RAW) as archive:
        members = archive.infolist()
        if (len(members) != 3 or {m.filename for m in members} != {'ids.npy', 'full.npy', 'cached.npy'}
                or sum(m.file_size for m in members) >= LIMIT
                or any(m.compress_type != zipfile.ZIP_STORED for m in members)):
            raise ValueError('원래의 bounded raw 배열 계약이 다르다')
    return dict(recipe_sha256=sha(recipe), parent_metadata=parent,
        old_failure_sha256=OLD_FAILURE_SHA, old_raw_sha256=OLD_RAW_SHA,
        models_created=0, checkpoint_tensors_loaded=0, tokenizer_loaded=False, raw_arrays_loaded=False)


def load_old_arrays():
    import numpy as np
    if digest(OLD_RAW) != OLD_RAW_SHA or digest(OLD_FAILURE) != OLD_FAILURE_SHA:
        raise ValueError('원래 raw 또는 failure JSON이 바뀌었다')
    with np.load(OLD_RAW, allow_pickle=False) as arrays:
        if set(arrays.files) != {'ids', 'full', 'cached'}: raise ValueError('원래 raw 필드가 다르다')
        ids, full, cached = (arrays[k].copy() for k in ('ids', 'full', 'cached'))
    vocab = info()['shape']['vocab_size']
    if (ids.dtype != np.int64 or ids.shape != (1, INPUTS) or full.shape != (1, INPUTS, vocab)
            or cached.shape != full.shape or ids.min() < 0 or ids.max() >= vocab):
        raise ValueError('원래9IDs/어휘/배열 shape가 다르다')
    result = measured(full, cached)
    original = read_json(OLD_FAILURE)
    validate_old_failure(original)
    if (old.array_sha(ids) != original['raw']['ids_sha256']
            or result['full_sha256'] != original['raw']['comparison']['full_sha256']
            or result['cached_sha256'] != original['raw']['comparison']['cached_sha256']
            or result['close'] is not False):
        raise ValueError('원래 수치 음성을 조용히 교체할 수 없다')
    return ids, full, cached


def future_ids(ids, vocab):
    import numpy as np
    if (ids.dtype != np.int64 or ids.shape != (1, INPUTS) or vocab <= ORDINARY_START
            or np.any(ids[:, PREFILL:] < ORDINARY_START) or np.any(ids >= vocab)):
        raise ValueError('후행6개가 기존 ordinary ID인 정확한9IDs만 허용한다')
    changed = ids.copy()
    changed[:, PREFILL:] = ORDINARY_START + (ids[:, PREFILL:] - ORDINARY_START + 1) % (vocab - ORDINARY_START)
    if (not np.array_equal(changed[:, :PREFILL], ids[:, :PREFILL])
            or np.count_nonzero(changed != ids) != INPUTS - PREFILL):
        raise ValueError('첫3개를 보존하고 마지막6개만 바꿔야 한다')
    return changed


def measured(left, right):
    """허용치 음성도 관측값으로 보존하되 shape/NaN은 계속 거부한다."""
    import numpy as np
    try: result = old.comparison(left, right)
    except old.ToleranceFailure as exc: result = exc.metrics
    mismatch = ~np.isclose(left, right, atol=ATOL, rtol=RTOL)
    coordinates = np.argwhere(mismatch)
    ta = np.argsort(-left, axis=-1, kind='stable')[..., :2]
    tb = np.argsort(-right, axis=-1, kind='stable')[..., :2]
    per_position = []
    for position in range(left.shape[1]):
        a, b = ta[0, position], tb[0, position]
        per_position.append(dict(position=position, mismatch_elements=int(mismatch[0, position].sum()),
            top2_left_ids=a.tolist(), top2_right_ids=b.tolist(),
            top2_left_logits=left[0, position, a].astype(float).tolist(),
            top2_right_logits=right[0, position, b].astype(float).tolist()))
    return dict(result, exact_equal=left.tobytes() == right.tobytes(), mismatch_elements=int(mismatch.sum()),
        mismatch_coordinates_sha256=old.array_sha(coordinates), first_mismatch_coordinates=coordinates[:16].tolist(),
        argmax_changes=int(np.count_nonzero(ta[..., 0] != tb[..., 0])),
        ordered_top2_changes=int(np.count_nonzero(np.any(ta != tb, axis=-1))), per_position=per_position)


def contrasts(probes, saved_full, saved_cached):
    a, aon, b, c, d, e = (probes[k] for k in PROBES)
    pairs = ((a, saved_full), (d, saved_cached), (a, d), (a, aon),
             (a[:, :PREFILL], b), (b, c), (a[:, :PREFILL], e[:, :PREFILL]))
    return {name: measured(left, right) for name, (left, right) in zip(CONTRASTS, pairs)}


def save_probe(name, ids, logits):
    import numpy as np
    if name not in PROBES: raise ValueError('사전 고정한 여섯 probe만 허용한다')
    measured(logits, logits)
    if ids.nbytes + logits.nbytes + 2048 >= LIMIT: raise ValueError('raw 한 파일은20MB 미만이어야 한다')
    path = safe(RAW / (name + '.npz'))
    with path.open('xb') as stream: np.savez(stream, ids=ids, logits=logits)
    if path.stat().st_size >= LIMIT: raise ValueError('raw 한 파일이20MB에 도달했다')
    return dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size, sha256=digest(path),
        ids_sha256=old.array_sha(ids), logits_sha256=old.array_sha(logits), shape=list(logits.shape), dtype='float32')


def read_probe(name, entry):
    import numpy as np
    path = safe(RAW / (name + '.npz'))
    if (entry['path'] != str(path.relative_to(ROOT)) or not 0 < entry['bytes'] < LIMIT
            or path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']):
        raise ValueError('정확한 raw 파일·크기·SHA가 필요하다')
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if (len(members) != 2 or {m.filename for m in members} != {'ids.npy', 'logits.npy'}
                or sum(m.file_size for m in members) >= LIMIT
                or any(m.compress_type != zipfile.ZIP_STORED for m in members)):
            raise ValueError('bounded uncompressed raw만 허용한다')
    with np.load(path, allow_pickle=False) as arrays:
        ids, logits = arrays['ids'].copy(), arrays['logits'].copy()
    length = PREFILL if name in ('B', 'C') else INPUTS
    if (ids.dtype != np.int64 or ids.shape != (1, length)
            or logits.shape != (1, length, info()['shape']['vocab_size'])
            or entry['shape'] != list(logits.shape) or entry['dtype'] != 'float32'
            or old.array_sha(ids) != entry['ids_sha256'] or old.array_sha(logits) != entry['logits_sha256']):
        raise ValueError('실제 raw 배열·입력·분모가 다르다')
    measured(logits, logits)
    return ids, logits


def load_bundle():
    """정확한 부모만 읽으며 임의 CP 경로나 weight-route 우회 API는 없다."""
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.data.prepare import verify_chat_tokenizer
    if digest(PARENT) != PARENT_SHA or digest(TOKENIZER) != TOKENIZER_SHA:
        raise ValueError('정확한 부모·tokenizer SHA가 필요하다')
    tokenizer = Tokenizer.from_file(str(TOKENIZER)); verify_chat_tokenizer(tokenizer, 32768)
    payload = torch.load(PARENT, map_location='cpu', weights_only=True)
    cfg = TMTConfig(**payload['cfg']); old.validate_cfg(cfg)
    old.validate_payload(payload, cfg, old.read_json(old.NATIVE_REPORT))
    return torch, payload, cfg, tokenizer


def run_observation(binding):
    torch, payload, cfg, tokenizer = load_bundle()
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from scripts.p070b_cla_routes import FixedRouteTransformer
    if torch.cuda.is_initialized(): raise ValueError('GPU 초기화는 금지한다')
    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1: torch.set_num_interop_threads(1)
    original_ids, saved_full, saved_cached = load_old_arrays()
    changed = future_ids(original_ids, cfg.vocab_size)
    before = dict(parent=digest(PARENT), tokenizer=digest(TOKENIZER), failure=digest(OLD_FAILURE), raw=digest(OLD_RAW))
    torch.manual_seed(1337)
    model = FixedRouteTransformer(replace(cfg, train_repeat=2., infer_repeat=1.), 'reverse', 2, 0)
    old.strict_load(model, payload, PARENT_CORE); del payload
    if model.route_sha256 != read_json(OLD_FAILURE)['route_sha256']: raise ValueError('원래의 reverseR2 route SHA가 다르다')
    model.eval(); model.clear_quant(); core_before = old.fingerprint(model)
    probes, caches = {}, {}
    values = torch.tensor(original_ids, dtype=torch.long)
    try:
        with torch.no_grad(), torch.autocast('cpu', enabled=False), sdpa_kernel(SDPBackend.MATH):
            model.freeze_quant()
            probes['A'] = model(values).numpy().copy()
            aon, bank = model(values, use_cache=True)
            caches['Aon'] = old.cache_receipt(model, bank, INPUTS, fixed=True); probes['Aon'] = aon.numpy().copy()
            probes['B'] = model(values[:, :PREFILL]).numpy().copy()
            c, bank = model(values[:, :PREFILL], use_cache=True)
            caches['C'] = old.cache_receipt(model, bank, PREFILL, fixed=True); probes['C'] = c.numpy().copy()
            pieces = [c]
            for position in range(PREFILL, INPUTS):
                out, bank = model(values[:, position:position + 1], past_kv=bank, use_cache=True)
                old.cache_receipt(model, bank, position + 1, fixed=True); pieces.append(out)
            caches['D'] = old.cache_receipt(model, bank, INPUTS, fixed=True)
            probes['D'] = torch.cat(pieces, dim=1).numpy().copy()
            probes['E'] = model(torch.tensor(changed, dtype=torch.long)).numpy().copy()
        if any(cache['kv_entries'] != 12 for cache in caches.values()): raise ValueError('reverseR2의12 KV 엔트리가 필요하다')
        core_after = old.fingerprint(model)
        if core_before != core_after or core_after != PARENT_CORE: raise ValueError('모델 가중치가 바뀌었다')
        manifest = {name: save_probe(name, changed if name == 'E' else original_ids[:, :PREFILL] if name in ('B', 'C') else original_ids,
            probes[name]) for name in PROBES}
        after = dict(parent=digest(PARENT), tokenizer=digest(TOKENIZER), failure=digest(OLD_FAILURE), raw=digest(OLD_RAW))
        if before != after or torch.cuda.is_initialized(): raise ValueError('입력 원형 변경 또는 GPU 초기화가 발생했다')
        return dict(status='DIAGNOSTIC_OBSERVATIONS_COMPLETE', binding=binding, probes=manifest,
            comparisons=contrasts(probes, saved_full, saved_cached), cache_receipts=caches,
            core_before=core_before, core_after=core_after, source_before=before, source_after=after,
            route_sha256=model.route_sha256, runtime_cfg=canonical(asdict(model.cfg)),
            cuda_initialized=False, model_instances=1, limitations=LIMITATIONS)
    finally:
        model.clear_quant(); del model, tokenizer; gc.collect()


def validate_report(report):
    import numpy as np
    if (report.get('integrity_sha256') != sha({k: v for k, v in report.items() if k != 'integrity_sha256'})
            or report.get('recipe') != info() or report.get('status') != 'DIAGNOSTIC_OBSERVATIONS_COMPLETE'
            or report.get('limitations') != LIMITATIONS or report.get('model_instances') != 1
            or report.get('cuda_initialized') is not False
            or report.get('core_before') != PARENT_CORE or report.get('core_after') != PARENT_CORE
            or report.get('source_before') != report.get('source_after')
            or report.get('source_after') != dict(parent=PARENT_SHA, tokenizer=TOKENIZER_SHA, failure=OLD_FAILURE_SHA, raw=OLD_RAW_SHA)
            or set(report.get('probes', {})) != set(PROBES) or set(report.get('comparisons', {})) != set(CONTRASTS)):
        raise ValueError('전체 고정 대조와 원 게이트 음성 보존 계약이 필요하다')
    contract = read_json(CACHE / 'contract.json')
    if (contract.get('recipe') != info() or contract.get('binding') != report.get('binding')
            or report['binding'].get('recipe_sha256') != sha(info())
            or report.get('contract_sha256') != digest(CACHE / 'contract.json')):
        raise ValueError('recipe·contract·report 결합이 다르다')
    ids, saved_full, saved_cached = load_old_arrays(); probes = {}
    changed = future_ids(ids, info()['shape']['vocab_size'])
    for name in PROBES:
        actual_ids, probes[name] = read_probe(name, report['probes'][name])
        expected = changed if name == 'E' else ids[:, :PREFILL] if name in ('B', 'C') else ids
        if not np.array_equal(actual_ids, expected): raise ValueError('probe의 실제 입력과 통제축이 다르다')
    if report['comparisons'] != contrasts(probes, saved_full, saved_cached): raise ValueError('raw 재계산과 공개 대조 수치가 다르다')
    if report.get('route_sha256') != read_json(OLD_FAILURE)['route_sha256']:
        raise ValueError('원래 실패한 route와 같아야 한다')
    runtime_config_doc = report.get('runtime_cfg', {})
    if (any(runtime_config_doc.get(key) != value for key, value in info()['shape'].items())
            or runtime_config_doc.get('train_repeat') != 2. or runtime_config_doc.get('infer_repeat') != 1.
            or runtime_config_doc.get('repeat_mode') != 'uniform' or runtime_config_doc.get('mtp_aux') is not False):
        raise ValueError('동일한 부모 형상과 fixed reverseR2 실행 cfg가 필요하다')
    for key, length in (('Aon', INPUTS), ('C', PREFILL), ('D', INPUTS)):
        cache = report.get('cache_receipts', {}).get(key, {})
        if (cache.get('route_sha256') != report['route_sha256'] or cache.get('kv_entries') != 12
                or cache.get('tokens') != length or cache.get('dtype') != 'float32'):
            raise ValueError('실제 cache 경로·엔트리·길이의 기록이 필요하다')
    return report


def worker(seconds=MAX_WALL):
    old.cap(seconds)
    if any(safe(p).exists() for p in (CACHE, RAW, EVIDENCE)): raise FileExistsError('이전 namespace를 보존한다')
    recipe = info(); began = time.perf_counter(); started = datetime.now(timezone.utc).isoformat()
    code, error, owned = 9, None, False
    with old.termination_guard():
        try:
            EVIDENCE.mkdir(parents=True, exist_ok=False); owned = True
            with old.bounded_worker(seconds):
                binding = preflight(seconds, fresh=False)
                for path in (CACHE, RAW): path.mkdir(parents=True, exist_ok=False)
                write_json(CACHE / 'contract.json', dict(recipe=recipe, binding=binding))
                report = seal(dict(recipe=recipe, contract_sha256=digest(CACHE / 'contract.json'), **run_observation(binding)))
                validate_report(report)
                if recipe != info(): raise ValueError('실행 중 코드 또는 recipe가 바뀌었다')
                write_json(EVIDENCE / 'report.json', report); code = 0
            return 0
        except BaseException as exc:
            error = type(exc).__name__
            code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (Pending, FileNotFoundError, FileExistsError)) else 9
            raise
        finally:
            if owned:
                result = EVIDENCE / 'report.json'
                write_json(EVIDENCE / 'activity.json', dict(schema=SCHEMA, tag=TAG, returncode=code, complete=code == 0,
                    error_type=error, seconds=time.perf_counter() - began, started_at=started,
                    ended_at=datetime.now(timezone.utc).isoformat(), max_wall_sec=seconds,
                    recipe_sha256=sha(recipe), code_sha256=recipe['code_sha256'],
                    report_sha256=digest(result) if result.is_file() else None,
                    old_gate_status='ERROR9_PRESERVED', signal_limit='TERM은finally로정리; SIGKILL/전원/쓰기오류는보장불가'))


def readback():
    report = validate_report(read_json(EVIDENCE / 'report.json')); activity = read_json(EVIDENCE / 'activity.json')
    if (activity.get('schema') != SCHEMA or activity.get('tag') != TAG or activity.get('returncode') != 0
            or type(activity.get('returncode')) is not int or activity.get('complete') is not True
            or activity.get('error_type') is not None or activity.get('recipe_sha256') != sha(info())
            or activity.get('code_sha256') != info()['code_sha256']
            or activity.get('report_sha256') != digest(EVIDENCE / 'report.json')
            or type(activity.get('seconds')) not in (int, float) or not math.isfinite(activity['seconds'])
            or not 0 <= activity['seconds'] <= old.cap(activity['max_wall_sec'])):
        raise ValueError('완결된 bounded activity/report 결합이 필요하다')
    begin, end = (datetime.fromisoformat(activity[k]) for k in ('started_at', 'ended_at'))
    if (begin.tzinfo is None or end.tzinfo is None or end < begin or end > END
            or (END - begin).total_seconds() < activity['max_wall_sec'] + RECORD_RESERVE):
        raise ValueError('실제 activity가 권한/기록 예비를 침범했다')
    return dict(status='DIAGNOSTIC_RAW_READBACK_COMPLETE', report_sha256=digest(EVIDENCE / 'report.json'),
        activity_sha256=digest(EVIDENCE / 'activity.json'), contrasts=len(report['comparisons']), limitations=LIMITATIONS)


def phase_commands(seconds=MAX_WALL):
    old.cap(seconds); py = [sys.executable, '-B', '-X', 'utf8']; base = py + [SCRIPT]
    flags = ['--max-wall-sec', str(seconds)]
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p070b_prefill_shape_cause', '-v']),
        ('PREFLIGHT', base + ['--preflight'] + flags), ('EXECUTE', base + ['--execute', '--worker'] + flags)]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); action = p.add_mutually_exclusive_group(required=True)
    action.add_argument('--check-only', action='store_true'); action.add_argument('--execute', action='store_true')
    action.add_argument('--preflight', action='store_true'); p.add_argument('--worker', action='store_true')
    p.add_argument('--max-wall-sec', type=int, default=MAX_WALL); args = p.parse_args(argv)
    try:
        old.cap(args.max_wall_sec)
        if args.worker and not args.execute: raise ValueError('--worker는--execute에서만허용한다')
        if args.check_only:
            print('[P070B_SHAPE_CHECK_ONLY] ' + json.dumps(dict(recipe=info(), phases=phase_commands(args.max_wall_sec),
                models_created=0, real_assets_opened=False, writes=0)), flush=True); return 0
        if args.preflight:
            print('[P070B_SHAPE_PREFLIGHT] ' + json.dumps(preflight(args.max_wall_sec)), flush=True); return 0
        if args.worker: return worker(args.max_wall_sec)
        authority(args.max_wall_sec)
        if any(safe(path).exists() for path in (CACHE, RAW, EVIDENCE)): raise FileExistsError('이전namespace에final을추가하지않는다')
        from scripts.p106b_stage_receipt import pipeline
        phases = phase_commands(args.max_wall_sec); began = time.monotonic(); actual = None
        def launch(command):
            nonlocal actual
            remaining = min(args.max_wall_sec - (time.monotonic() - began), authority(1))
            result = old.launch(command, min(remaining, 60) if command != phases[-1][1] else remaining)
            if command == phases[-1][1] and result == 0: actual = readback()
            return result
        receipt = pipeline(phases, launch, lambda s: print(s, flush=True), experiment=SCHEMA)
        if receipt['returncode'] == 0 and actual is None: raise ValueError('실제관측없는완료는허용하지않는다')
        final = seal(dict(recipe=info(), phases=receipt, readback=actual, limitations=LIMITATIONS))
        if EVIDENCE.is_dir(): write_json(EVIDENCE / 'final.json', final)
        print('[P070B_SHAPE_DIAGNOSTIC_FINAL] ' + json.dumps(final), flush=True); return receipt['returncode']
    except (Pending, FileNotFoundError, FileExistsError) as exc:
        print('[P070B_SHAPE_DIAGNOSTIC_FINAL] HOLD8: ' + str(exc), flush=True); return 8
    except KeyboardInterrupt:
        print('[P070B_SHAPE_DIAGNOSTIC_FINAL] INTERRUPTED130; 부분원형보존', flush=True); return 130
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        traceback.print_exc(); print('[P070B_SHAPE_DIAGNOSTIC_FINAL] ERROR9: ' + str(exc), flush=True); return 9


if __name__ == '__main__': raise SystemExit(main())
