#!/usr/bin/env python3
"""보존 확장 TRAIN에 기존 VAL 규칙과 native32 창을 독립 재적용하는 CPU 감사.

원 코드/날짜/globals/cache를 바꾸지 않는다. 직접 pinned VAL ID를 사용하므로
tokenizer/model/CP를 load하지 않는다. 실제 bin은 명시 execute worker만 읽는다.
0-hit는 선언한 두 기계 검사만 뜻하며 학습 허가나 의미 중복 제거가 아니다.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import mmap
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
TAG, SCHEMA = 'p106b_expansion_val_audit_v1_s1337', 'P106B_EXPANSION_VAL_AUDIT_V1'
SCRIPT, TEST = 'scripts/diag_p106b_expansion_val_audit.py', 'scripts/test_p106b_expansion_val_audit.py'
F4 = 'handoff/audit/WIP_20261020_EXPANSION_VAL_AUDIT_F4.json'
ORIGINAL = 'p106b_native_expansion_v1_s1337'
BASE = 'test_result/evidence/' + ORIGINAL + '/'
META = 'data_cache/' + ORIGINAL + '/meta.json'
PINS = {
    'scripts/diag_p106b_native_expansion.py': '882738C52731B6E667E3F0984C8F74D2B978D28067A24831192888B2F0E763D1',
    'scripts/test_p106b_native_expansion.py': '5377A796AC36B4CA5BC107103922558C33F9D40DDB122BDE68C3D79D45646235',
    META: '059617A670A6333B2E8F68A34CF7865DE70C5576537C42C74B45857935602089',
    BASE + 'build/report.json': '103C9DFBDF45171E13F70ADFB8D3E4443ABFBDF4E982FD0A839720E02F44B5FD',
    BASE + 'readback/report.json': '9B897BDD0C9216625EC79F49F6AE62CA4DA71130B749B4C1CE98F691AF6357C1',
    BASE + 'activity_build.json': '5301922DAB60F5D268B165C0E829C5F7B67E8D34683BC9FE3482F93E44D06CCA',
    BASE + 'activity_readback.json': 'EF82F45AA1E420E3F0638E388B4C225627DB8E335541CB94351D231145A51028',
}
PIPELINE = 'scripts/p106b_stage_receipt.py'
PIPELINE_SHA = '334FBD2B9031DA7E58E43762BCFD4CD9902BD972165D953E3D7D385C3B8709B9'
BINS = [dict(path='data_cache/' + ORIGINAL + '/train.bin', ids=1191116192,
    sha256='6DB291329CB1562E127A2D753F879C8ED8D3AB46789A3EF2B4BC3C4258846138'),
    dict(path='data_cache/ko-en_601000000_chat32/val.bin', ids=3005000,
    sha256='AD7EFB0DBD0D830A216B4D21A91C8ACB3FC41DAE2B23A3A55999AE8727AA374C')]
TOKENIZER = dict(path='data_cache/tok-ko-en-32768-chat32.json',
    sha256='9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E')
INDEX = dict(total_ids=3005000, complete_eos_segments=3758, unique_complete_id_hashes=3758,
    prefix_partial_ids=412, suffix_partial_ids=43,
    prefix_partial_sha256='4DE752FB91A0D9BA376511E6A38CD592152850CC75A3360AC6E6B8865D5E6B0D',
    suffix_partial_sha256='E074DD81AE56E05FCCCCDA69710C8F0AE0B66E7E8C4516BA14230492FA719F8E')
END = datetime(2026, 10, 21, 8, tzinfo=timezone.utc)
CAP, RESERVE, LIMIT = 600, 600, 20_000_000
CHUNK_IDS, MAX_SEGMENT_IDS = 4_194_304, 16_777_217
EVIDENCE = 'test_result/evidence/' + TAG + '/'
REPORT, ACTIVITY, FAILURE = EVIDENCE + 'report.json', EVIDENCE + 'activity.json', EVIDENCE + 'failure.json'
ALLOWED = frozenset((*PINS, SCRIPT, TEST, F4, PIPELINE, TOKENIZER['path'],
    *(value['path'] for value in BINS), REPORT, ACTIVITY, FAILURE))


class Pending(RuntimeError): pass


class ScanError(ValueError):
    def __init__(self, message, **counts):
        super().__init__(message); self.counts = counts


def finite(value): return type(value) in (int, float) and math.isfinite(value) and value >= 0


def path(relative, *, root=None, allowed=None):
    root, allowed = ROOT if root is None else Path(root), ALLOWED if allowed is None else allowed
    if (not isinstance(relative, str) or relative not in allowed or '\\' in relative or ':' in relative
            or relative.startswith('/') or relative != Path(relative).as_posix()
            or any(p in ('', '.', '..', '.aws', '.claude', 'TinyDataset') for p in relative.split('/'))):
        raise ValueError('허가된 고정 상대경로만 읽거나 쓸 수 있다')
    result = root / relative
    for ancestor in (result, *result.parents):
        if ancestor.is_symlink(): raise ValueError('입력/출력 symlink 조상은 열기 전에 거부한다')
        if ancestor == root: break
    return result


def digest(filename):
    result = hashlib.sha256()
    with filename.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): result.update(block)
    return result.hexdigest().upper()


def small_json(filename):
    if filename.stat().st_size >= LIMIT: raise ValueError('작은 JSON은20MB 미만이어야 한다')
    return json.loads(filename.read_text(encoding='utf-8'))


def write(relative, value, *, root=None):
    if relative not in (REPORT, ACTIVITY, FAILURE): raise ValueError('자기 감사 산출물만 쓸 수 있다')
    filename = path(relative, root=root)
    body = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(body) >= LIMIT: raise ValueError('보고서는20MB 미만이어야 한다')
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open('xb') as stream: stream.write(body)


def code_info():
    contract = small_json(path(F4))
    if (contract.get('schema') != 'P106B_EXPANSION_VAL_AUDIT_F4_V1' or contract.get('tag') != TAG
            or contract.get('agent_write_allowlist') != [SCRIPT, TEST] or contract.get('read_only_inputs') != PINS
            or contract.get('binary_inputs_execute_only') != BINS or contract.get('tokenizer') != TOKENIZER
            or contract.get('resource', {}).get('max_worker_seconds') != CAP
            or contract['resource'].get('record_reserve_seconds') != RESERVE
            or contract['resource'].get('end_utc') != '2026-10-21T08:00:00Z'):
        raise ValueError('정확한 원 F4/고정 입력/기한/두 파일 경계가 필요하다')
    code = {name: digest(path(name)) for name in (SCRIPT, TEST, PIPELINE, *list(PINS)[:2])}
    if code[PIPELINE] != PIPELINE_SHA or any(code[name] != PINS[name] for name in list(PINS)[:2]):
        raise ValueError('import 전 동결 코드 SHA가 다르다')
    return dict(schema=SCHEMA, tag=TAG, code_sha256=code, code_complete=True, f4_sha256=digest(path(F4)),
        binary_inputs=BINS, tokenizer=TOKENIZER, source_metadata_pins=PINS, expected_index=INDEX, max_worker_seconds=CAP,
        authority_end_utc=END.isoformat(), record_reserve_seconds=RESERVE,
        chunk_ids=CHUNK_IDS, maximum_segment_ids=MAX_SEGMENT_IDS, vocab=32768,
        probe_count=32, probe_stride_ids=1024, probe_window_ids=1025,
        scan_scope='same full-EOS hash and both aligned edge partials; separate32 exact full-window search',
        semantic_decontamination='NOT_ESTABLISHED', arbitrary_full_val_substring_scan=False,
        training_admission=False, model_loading=False, checkpoint_tensor_loading=False, gpu=False,
        termination='own SIGTERM ->130 with finally; SIGKILL cannot guarantee activity')


def validate_metadata(values):
    meta, built, read = values[META], values[BASE + 'build/report.json'], values[BASE + 'readback/report.json']
    if (meta.get('tag') != ORIGINAL or meta.get('schema') != 'P106B_NATIVE_EXPANSION_CPU_V1'
            or meta.get('train') != BINS[0]['ids'] or meta.get('train_sha256') != BINS[0]['sha256']
            or meta.get('val') != 0 or meta.get('token_dtype') != 'uint16' or meta.get('byte_order') != 'little'
            or meta.get('tokenizer_sha256') != TOKENIZER['sha256'] or meta.get('tokenizer_lineage') != 'chat32'
            or meta.get('current_val_sha256') != BINS[1]['sha256']
            or meta.get('source_ids') != 1194000000 or meta.get('original_data_mutated') is not False
            or meta.get('legacy_val_access') is not False
            or built.get('status') != 'FULL_CONVERSION_COMPLETE_NOT_TRAINING'
            or built.get('output_path') != BINS[0]['path'] or built.get('output_sha256') != BINS[0]['sha256']
            or built.get('output_bytes') != 2 * BINS[0]['ids'] or built.get('meta_sha256') != PINS[META]
            or read.get('status') != 'FULL_CACHE_READBACK_COMPLETE'
            or read.get('build_report_sha256') != PINS[BASE + 'build/report.json']
            or read.get('actual_output_ids') != BINS[0]['ids'] or read.get('actual_output_sha256') != BINS[0]['sha256']
            or read.get('actual_eos_segments') != 1441175 or read.get('last_id') != 2):
        raise ValueError('원 변환 TRAIN/meta/build/readback 계보가 다르다')
    if (meta.get('source_train_sha256') != built.get('source_train_sha256')
            or not isinstance(meta.get('source_train_sha256'), str) or len(meta['source_train_sha256']) != 64
            or meta.get('source_train_sha256') != read.get('source_train_sha256_verified_by_completed_build_stream')
            or built.get('metrics', {}).get('new_kept_ids') != BINS[0]['ids']
            or built['metrics'].get('new_canonical_ids', 0) - built['metrics'].get('new_excluded_ids', 0) != BINS[0]['ids']
            or any(read.get('full_input_consumer', {}).get(k) != built['metrics'].get(k) for k in
                ('old_input_ids', 'old_incomplete_tail_ids', 'new_kept_ids', 'kept_segments', 'excluded_segments'))):
        raise ValueError('완성 출력과 원 입력/제외/tail 계수의 보존이 다르다')
    val = built.get('current_val', {})
    if val.get('ids') != BINS[1]['ids'] or val.get('source_sha256') != BINS[1]['sha256'] or any(val.get('index', {}).get(k) != v for k, v in INDEX.items()):
        raise ValueError('제외에 사용한 정확한 외부VAL/index가 필요하다')
    for mode in ('build', 'readback'):
        record = values[BASE + 'activity_' + mode + '.json']
        recipe = values[BASE + mode + '/report.json'].get('recipe', {})
        if (record.get('tag') != ORIGINAL or record.get('schema') != 'P106B_NATIVE_EXPANSION_CPU_V1'
                or record.get('mode') != mode or record.get('complete') is not True or record.get('returncode') != 0
                or record.get('report_path') != BASE + mode + '/report.json'
                or record.get('report_sha256') != PINS[BASE + mode + '/report.json']
                or record.get('code_sha256') != recipe.get('code_sha256') or recipe.get('tag') != ORIGINAL
                or recipe.get('authority_end_utc') != '2026-10-20T08:00:00+00:00'
                or recipe.get('full_build_readback_stop_utc') != '2026-10-20T05:00:00+00:00'
                or not finite(record.get('seconds'))):
            raise ValueError('원 완료 activity/report/code를 retag할 수 없다')


def preflight():
    info = code_info(); values = {}
    for relative, expected in PINS.items():
        if path(relative).stat().st_size >= LIMIT: raise ValueError('원 코드/메타도20MB 미만이어야 한다')
        if digest(path(relative)) != expected: raise ValueError('고정 source/meta/report SHA가 다르다: ' + relative)
        if relative.endswith('.json'): values[relative] = small_json(path(relative))
    if digest(path(TOKENIZER['path'])) != TOKENIZER['sha256']: raise ValueError('tokenizer 파일 SHA가 다르다')
    validate_metadata(values)
    if path(REPORT).parent.exists(): raise FileExistsError('기존 성공/음성/부분 감사 namespace를 보존한다')
    return info


def aligned_search(buffer, needle, start=0, end=None, *, first=False):
    if not needle or len(needle) % 2 or start % 2: raise ValueError('비어 있지 않은 uint16 패턴과 짝수 시작이 필요하다')
    end = len(buffer) if end is None else end
    cursor, even, odd = start, 0, 0
    while True:
        found = buffer.find(needle, cursor, end)
        if found < 0: return even, odd
        if found % 2: odd += 1
        else:
            even += 1
            if first: return even, odd
        cursor = found + 1


def index_val(buffer, np, *, probe_count=32, stride=1024, vocab=32768, max_segment=MAX_SEGMENT_IDS):
    if len(buffer) % 2: raise ScanError('VAL uint16 바이트 정렬이 다르다')
    values = np.frombuffer(buffer, dtype='<u2')
    try:
        if not len(values) or bool(np.any(values >= vocab)): raise ScanError('VAL ID 범위/전량 입력이 잘못됐다')
        if probe_count <= 0 or stride <= 0 or len(values) < (probe_count - 1) * stride + stride + 1:
            raise ScanError('선언한 native probe 창의 전체 VAL이 필요하다')
        boundaries = np.flatnonzero(values == 2); full = set(); cursor = 0
        for ordinal, boundary in enumerate(boundaries):
            stop = int(boundary) + 1
            if stop - cursor > max_segment: raise ScanError('VAL segment 메모리 상한을 넘었다')
            if ordinal: full.add((stop - cursor, hashlib.sha256(buffer[cursor * 2:stop * 2]).hexdigest().upper()))
            cursor = stop
        first = int(boundaries[0]) if len(boundaries) else len(values)
        if len(values) - cursor > max_segment: raise ScanError('VAL 끝 조각 상한을 넘었다')
        prefix = bytes(buffer[:first * 2]); suffix = bytes(buffer[cursor * 2:])
        summary = dict(total_ids=len(values), complete_eos_segments=max(0, len(boundaries) - 1),
            unique_complete_id_hashes=len(full), prefix_partial_ids=len(prefix) // 2, suffix_partial_ids=len(suffix) // 2,
            prefix_partial_sha256=hashlib.sha256(prefix).hexdigest().upper(), suffix_partial_sha256=hashlib.sha256(suffix).hexdigest().upper())
        probes = [bytes(buffer[i * stride * 2:(i * stride + stride + 1) * 2]) for i in range(probe_count)]
        return dict(full=full, prefix=prefix, suffix=suffix, summary=summary, probes=probes, stride=stride)
    finally: del values


def scan_train(buffer, index, np, *, chunk_ids=CHUNK_IDS, max_segment=MAX_SEGMENT_IDS, vocab=32768, note=lambda _: None):
    if not len(buffer) or len(buffer) % 2 or type(chunk_ids) is not int or chunk_ids <= 0:
        raise ScanError('완전한 bounded uint16 TRAIN이 필요하다')
    h = hashlib.sha256(); count = len(buffer) // 2; cursor = 0; segments = largest = 0; stamped = time.monotonic()
    hits = dict(full_eos_segments=0, prefix_segments=0, suffix_segments=0, any_rule_segments=0, odd_candidates_ignored=0)
    for begin in range(0, count, chunk_ids):
        stop = min(count, begin + chunk_ids)
        block = np.frombuffer(buffer, dtype='<u2', count=stop - begin, offset=begin * 2)
        try:
            if bool(np.any(block >= vocab)): raise ScanError('TRAIN ID 범위가 잘못됐다', checked_prefix_ids=begin)
            boundaries = np.flatnonzero(block == 2)
        finally: del block
        h.update(memoryview(buffer)[begin * 2:stop * 2])
        for boundary in boundaries:
            end = begin + int(boundary) + 1; size = end - cursor
            if size > max_segment: raise ScanError('TRAIN segment 메모리 상한을 넘었다', complete_segments=segments)
            raw_hash = hashlib.sha256(memoryview(buffer)[cursor * 2:end * 2]).hexdigest().upper()
            full = (size, raw_hash) in index['full']; matched = full
            hits['full_eos_segments'] += int(full)
            for label in ('prefix', 'suffix'):
                if index[label]:
                    found, odd = aligned_search(buffer, index[label], cursor * 2, end * 2, first=True)
                    hits[label + '_segments'] += int(found > 0); hits['odd_candidates_ignored'] += odd; matched |= found > 0
            hits['any_rule_segments'] += int(matched); segments += 1; largest = max(largest, size); cursor = end
        if stop - cursor > max_segment: raise ScanError('chunk 경계를 넘는 TRAIN segment가 상한을 넘었다')
        if begin == 0 or stop == count or time.monotonic() - stamped >= 20:
            note(dict(stage='TRAIN_CHUNK', ids_consumed=stop, eos_segments=segments)); stamped = time.monotonic()
    if cursor != count: raise ScanError('TRAIN 마지막 ID가 EOS가 아니며 미완 꼬리를 허용하지 않는다', complete_segments=segments)
    return dict(ids=count, sha256=h.hexdigest().upper(), range_checked_ids=count, eos_segments=segments,
        last_id_matches_eos=True, maximum_segment_ids_observed=largest, same_rule=hits)


def probe_search(buffer, index, *, chunk_bytes=64 << 20, note=lambda _: None):
    if type(chunk_bytes) is not int or chunk_bytes < 2 or chunk_bytes % 2: raise ValueError('짝수 bounded 검색 chunk가 필요하다')
    rows = []
    for ordinal, needle in enumerate(index['probes']):
        aligned = odd = 0
        for begin in range(0, len(buffer), chunk_bytes):
            primary_end = min(len(buffer), begin + chunk_bytes); end = min(len(buffer), primary_end + len(needle) - 1)
            cursor = begin
            while True:
                found = buffer.find(needle, cursor, end)
                if found < 0 or found >= primary_end: break
                if found % 2: odd += 1
                else: aligned += 1
                cursor = found + 1
        rows.append(dict(probe=ordinal, start_id_offset=ordinal * index['stride'], window_ids=len(needle) // 2,
            ids_sha256=hashlib.sha256(needle).hexdigest().upper(), aligned_occurrences=aligned, odd_byte_occurrences_ignored=odd))
        if (ordinal + 1) % 4 == 0: note(dict(stage='PROBE_SEARCH', windows_consumed=ordinal + 1, windows=len(index['probes'])))
    return dict(windows=len(rows), matched_windows=sum(r['aligned_occurrences'] > 0 for r in rows),
        total_aligned_occurrences=sum(r['aligned_occurrences'] for r in rows), rows=rows,
        count_scope='sum per probe; duplicate probes may count the same output position more than once')


def scan_files(train_path, val_path, contracts, *, expected_index=None, expected_eos=None, chunk_ids=CHUNK_IDS,
               max_segment=MAX_SEGMENT_IDS, probe_count=32, stride=1024, note=lambda _: None):
    # NumPy는 명시한 worker 또는 작은 fixture scanner 호출 안에서만 import한다.
    import numpy as np
    for filename, expected in zip((train_path, val_path), contracts):
        if (not filename.is_absolute() or '..' in filename.parts
                or any(p in ('TinyDataset', '.aws', '.claude') for p in filename.parts)
                or any(p.is_symlink() for p in (filename, *filename.parents)) or not filename.is_file()):
            raise ScanError('고정 regular input과 symlink 없는 조상이 필요하다')
        if filename.stat().st_size != 2 * expected['ids']: raise ScanError('입력 전체 ID/byte 수가 다르다')
    before = [(f.stat().st_size, f.stat().st_mtime_ns, f.stat().st_ino, f.stat().st_dev) for f in (train_path, val_path)]
    with val_path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as val:
        val_sha = hashlib.sha256(val).hexdigest().upper()
        if val_sha != contracts[1]['sha256']: raise ScanError('외부VAL 전체 SHA가 다르다', actual_sha256=val_sha)
        index = index_val(val, np, probe_count=probe_count, stride=stride, max_segment=max_segment)
    if expected_index is not None and index['summary'] != expected_index: raise ScanError('기존3758/양끝412·43 VAL index 정책과 다르다')
    with train_path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as train:
        training = scan_train(train, index, np, chunk_ids=chunk_ids, max_segment=max_segment, note=note)
        if training['sha256'] != contracts[0]['sha256']: raise ScanError('완성TRAIN 전체 SHA가 다르다', actual_sha256=training['sha256'])
        if expected_eos is not None and training['eos_segments'] != expected_eos: raise ScanError('보존 전체 EOS 구간 수가 다르다')
        probes = probe_search(train, index, note=note)
    after = [(f.stat().st_size, f.stat().st_mtime_ns, f.stat().st_ino, f.stat().st_dev) for f in (train_path, val_path)]
    if before != after: raise ScanError('검사 중 readonly 입력의 stat identity가 바뀌었다')
    return dict(train=training, val=dict(ids=contracts[1]['ids'], sha256=val_sha, index=index['summary']), probe32=probes,
        same_rule_zero_hits=training['same_rule']['any_rule_segments'] == 0,
        probe32_zero_hits=probes['matched_windows'] == 0, training_admission=False)


def remaining(now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None: raise ValueError('aware UTC가 필요하다')
    value = (END - now).total_seconds() - RESERVE
    if value <= 0: raise Pending('21일08Z/기록600초 경계에 도달했다')
    return value


@contextmanager
def bounded(seconds):
    previous_term, previous_alarm = signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGALRM)
    stopped = False
    def terminate(*_):
        nonlocal stopped
        if not stopped: stopped = True; raise KeyboardInterrupt('자기 CPU worker TERM 요청')
    def expired(*_):
        nonlocal stopped
        stopped = True; raise TimeoutError('독립 CPU 감사 worker 시간 상한')
    signal.signal(signal.SIGTERM, terminate); signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, previous_alarm); signal.signal(signal.SIGTERM, previous_term)


def worker(cap=CAP, *, root=None, info=None, prerequisite=None, scanner=None):
    if type(cap) is not int or not 60 <= cap <= CAP: raise ValueError('60..600초 상한만 허용한다')
    if os.getpid() != os.getpgid(0): raise ValueError('자기 PGID worker가 필요하다')
    if cap > remaining(): raise Pending('선언한 cap과 기록 예비가 절대UTC 안에 들어가야 한다')
    info = code_info() if info is None else info; root = ROOT if root is None else Path(root)
    directory = path(REPORT, root=root).parent; directory.mkdir(parents=True, exist_ok=False)
    code, error, report = 9, None, None; started = datetime.now(timezone.utc); began = time.perf_counter()
    with bounded(cap):
        try:
            if prerequisite is None: preflight_after_claim()
            else: prerequisite()
            result = (scanner if scanner is not None else lambda: scan_files(path(BINS[0]['path']), path(BINS[1]['path']), BINS,
                expected_index=INDEX, expected_eos=1441175, note=lambda v: print('[VAL_AUDIT_PROGRESS] ' + json.dumps(v), flush=True)))()
            remaining()
            if scanner is None and code_info() != info: raise ValueError('감사 중 코드/F4가 바뀌었다')
            report = dict(info=info, status='SCAN_COMPLETE', measurements=result, actual_scan_seconds=time.perf_counter() - began,
                mechanical_status='ZERO_HITS_AT_DECLARED_SCOPE' if result['same_rule_zero_hits'] and result['probe32_zero_hits'] else 'NEGATIVE_OBSERVED_HITS',
                models_loaded=0, checkpoint_tensor_loads=0, gpu_calls=0, original_inputs_changed=False)
            write(REPORT, report, root=root); code = 0
        except BaseException as exc:
            error = type(exc).__name__; code = 130 if isinstance(exc, KeyboardInterrupt) else 124 if isinstance(exc, TimeoutError) else 8 if isinstance(exc, Pending) else 9
            write(FAILURE, dict(info=info, error_type=error, error=str(exc)[:1500], returncode=code,
                partial_counts=getattr(exc, 'counts', {}), traceback=traceback.format_exc(limit=15),
                scan_complete=False, original_inputs_changed=False), root=root)
        finally:
            ended = datetime.now(timezone.utc)
            write(ACTIVITY, dict(schema=SCHEMA, tag=TAG, complete=code == 0, returncode=code, error_type=error,
                started_at=started.isoformat(), ended_at=ended.isoformat(), seconds=time.perf_counter() - began,
                max_wall_sec=cap, worker_pid=os.getpid(), worker_pgid=os.getpgid(0), info_sha256=json_sha(info),
                report_sha256=digest(path(REPORT, root=root)) if report is not None else None,
                failure_sha256=digest(path(FAILURE, root=root)) if error else None), root=root)
    return code


def preflight_after_claim():
    # 자기 namespace 생성 후에도 원천만 재검산하며 이전 activity는 쓰거나 고치지 않는다.
    for relative, expected in PINS.items():
        if path(relative).stat().st_size >= LIMIT: raise ValueError('원 코드/메타가 상한을 넘었다')
        if digest(path(relative)) != expected: raise ValueError('worker 진입 원천 SHA가 다르다')
    validate_metadata({name: small_json(path(name)) for name in PINS if name.endswith('.json')})
    if digest(path(TOKENIZER['path'])) != TOKENIZER['sha256']: raise ValueError('worker tokenizer pin이 다르다')


def json_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def closed_result(info, *, root=None):
    report, activity = small_json(path(REPORT, root=root)), small_json(path(ACTIVITY, root=root))
    begin, end = (datetime.fromisoformat(activity[k]) for k in ('started_at', 'ended_at'))
    if (report.get('info') != info or report.get('status') != 'SCAN_COMPLETE' or activity.get('schema') != SCHEMA
            or activity.get('tag') != TAG or activity.get('complete') is not True
            or type(activity.get('returncode')) is not int or activity['returncode'] != 0
            or activity.get('error_type') is not None or activity.get('info_sha256') != json_sha(info)
            or activity.get('report_sha256') != digest(path(REPORT, root=root)) or activity.get('failure_sha256') is not None
            or not finite(activity.get('seconds')) or type(activity.get('max_wall_sec')) is not int
            or not 60 <= activity['max_wall_sec'] <= CAP or activity['seconds'] > activity['max_wall_sec'] + 30
            or begin.tzinfo is None or end.tzinfo is None or begin > end
            or begin >= END - timedelta(seconds=RESERVE) or end > END - timedelta(seconds=RESERVE) + timedelta(seconds=30)
            or type(activity.get('worker_pid')) is not int or activity['worker_pid'] <= 0
            or activity.get('worker_pgid') != activity['worker_pid']): raise ValueError('닫힌 실제 감사 activity/report가 필요하다')
    result = report['measurements']; training, val, probes = result['train'], result['val'], result['probe32']
    if (training.get('ids') != BINS[0]['ids'] or training.get('range_checked_ids') != BINS[0]['ids']
            or training.get('sha256') != BINS[0]['sha256'] or training.get('eos_segments') != 1441175
            or training.get('last_id_matches_eos') is not True or val != dict(ids=BINS[1]['ids'], sha256=BINS[1]['sha256'], index=INDEX)
            or not isinstance(training.get('maximum_segment_ids_observed'), int)
            or not 0 < training['maximum_segment_ids_observed'] <= MAX_SEGMENT_IDS
            or probes.get('windows') != 32 or len(probes.get('rows', [])) != 32
            or not finite(report.get('actual_scan_seconds'))
            or report.get('models_loaded') != 0 or report.get('checkpoint_tensor_loads') != 0 or report.get('gpu_calls') != 0
            or report.get('original_inputs_changed') is not False): raise ValueError('전량 SHA/count/EOS/VAL/32창 분모가 다르다')
    hits = training['same_rule']; rows = probes['rows']
    if any(type(v) is not int or v < 0 for v in hits.values()): raise ValueError('음이 아닌 실제 hit 계수가 필요하다')
    if (set(hits) != {'full_eos_segments', 'prefix_segments', 'suffix_segments', 'any_rule_segments', 'odd_candidates_ignored'}
            or not max(hits[k] for k in ('full_eos_segments', 'prefix_segments', 'suffix_segments')) <= hits['any_rule_segments'] <=
                sum(hits[k] for k in ('full_eos_segments', 'prefix_segments', 'suffix_segments'))
            or hits['any_rule_segments'] > training['eos_segments']): raise ValueError('같은규칙 hit 합계/구간 분모가 모순된다')
    for i, row in enumerate(rows):
        if (row.get('probe') != i or row.get('start_id_offset') != i * 1024 or row.get('window_ids') != 1025
                or any(type(row.get(k)) is not int or row[k] < 0 for k in ('aligned_occurrences', 'odd_byte_occurrences_ignored'))
                or not isinstance(row.get('ids_sha256'), str) or len(row['ids_sha256']) != 64
                or any(ch not in '0123456789ABCDEF' for ch in row['ids_sha256'])): raise ValueError('각 probe의 counts/hash 계약이 다르다')
    same, probe = hits['any_rule_segments'] == 0, all(r['aligned_occurrences'] == 0 for r in rows)
    if (result.get('same_rule_zero_hits') is not same or result.get('probe32_zero_hits') is not probe
            or result.get('training_admission') is not False or probes['matched_windows'] != sum(r['aligned_occurrences'] > 0 for r in rows)
            or probes['total_aligned_occurrences'] != sum(r['aligned_occurrences'] for r in rows)
            or report.get('mechanical_status') != ('ZERO_HITS_AT_DECLARED_SCOPE' if same and probe else 'NEGATIVE_OBSERVED_HITS')):
        raise ValueError('별개 두 hit 판정/부적격과 전량 합계가 다르다')
    return 0 if same and probe else 8


def commands(cap):
    if type(cap) is not int or not 60 <= cap <= CAP: raise ValueError('60..600초 상한이 필요하다')
    py = [sys.executable, '-B', '-X', 'utf8']; base = py + [SCRIPT, '--execute', '--max-wall-sec', str(cap)]
    return [('REGRESSION', py + ['-m', 'unittest', TEST[:-3].replace('/', '.'), '-v']),
        ('PREFLIGHT', base + ['--preflight']), ('EXECUTE', base + ['--worker'])]


def launch(command, timeout):
    child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, start_new_session=True)
    try: return child.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        interrupted = sys.exc_info()[0] is KeyboardInterrupt
        if child.poll() is None and os.getpgid(child.pid) == child.pid:
            os.killpg(child.pid, signal.SIGTERM)
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired: os.killpg(child.pid, signal.SIGKILL); child.wait(timeout=5)
        return 130 if interrupted else 124


def main(argv=None):
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--max-wall-sec', type=int, default=CAP)
        internal = parser.add_mutually_exclusive_group(); internal.add_argument('--worker', action='store_true'); internal.add_argument('--preflight', action='store_true')
        action = parser.add_mutually_exclusive_group(required=True); action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
        args = parser.parse_args(argv); phases = commands(args.max_wall_sec); info = code_info()
        if args.check_only:
            if args.worker or args.preflight: raise ValueError('check-only는 실제 내부단계와 결합하지 않는다')
            print('[VAL_AUDIT_CHECK_ONLY] ' + json.dumps(info, ensure_ascii=False), flush=True); return 0
        if args.preflight:
            if args.max_wall_sec > remaining(): raise Pending('메타선결의 기한 여유가 부족하다')
            with bounded(args.max_wall_sec): preflight()
            print('[VAL_AUDIT_PREFLIGHT] metadata only; bin/model/GPU0', flush=True); return 0
        if args.worker: return worker(args.max_wall_sec)
        from scripts.p106b_stage_receipt import pipeline
        def stage(command):
            rc = launch(command, min(args.max_wall_sec + 30, remaining()))
            if rc or '--worker' not in command: return rc
            try:
                preflight_after_claim(); result = closed_result(code_info())
            except KeyboardInterrupt: return 130
            except Exception as exc:
                traceback.print_exc(file=sys.stderr)
                print('[VAL_AUDIT_FINAL] ' + json.dumps(dict(worker_returncode=0, status='EXECUTED_STRICT_VERIFY_FAILED',
                    error_type=type(exc).__name__, returncode=9, training_admission=False)), flush=True)
                return 9
            print('[VAL_AUDIT_FINAL] ' + json.dumps(dict(scan_completed=True, returncode=result,
                status='ZERO_HITS_AT_DECLARED_SCOPE' if result == 0 else 'NEGATIVE_OBSERVED_HITS', training_admission=False)), flush=True)
            return result
        return pipeline(phases, stage, lambda line: print(line, flush=True), experiment='P106B_EXPANSION_VAL_AUDIT')['returncode']
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        code = 130 if isinstance(exc, KeyboardInterrupt) else 124 if isinstance(exc, TimeoutError) else 8 if isinstance(exc, (Pending, FileExistsError)) else 9
        if code == 9: traceback.print_exc(file=sys.stderr)
        print('[VAL_AUDIT_ERROR] ' + type(exc).__name__ + ': ' + str(exc), flush=True); return code


if __name__ == '__main__': raise SystemExit(main())
