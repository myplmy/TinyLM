#!/usr/bin/env python3
"""Isolated Stage4fp controller. Check-only/readonly never construct a model.

Only the sealed training-initializer descriptor is accepted. Historical family
Runtime/prepared/authority and manual inference manifests are never called.
All real prepare/model/GPU actions require explicit --execute. Raw files are
write-once, <20MB shards; incomplete stages never become successful evidence.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from contextlib import contextmanager, nullcontext
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))


def import_environment(root=ROOT):
    root = Path(root)
    if root.is_symlink() or not root.is_dir(): raise ValueError('existing nonsymlink import ROOT required')
    for name, expected in (('TINYLM_DIR', str(root)), ('TINYLM_HF', str(root / 'HF'))):
        if name in os.environ and os.environ[name] != expected: raise ValueError('explicit fixed import environment required: ' + name)
    for rel in ('HF', 'HF/hub', 'data_cache', 'runs', 'runs/ckpt', 'runs/logs'):
        mode = (root / rel).lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode): raise ValueError('existing nonsymlink import directories required')


import_environment()  # Even the pure project data helper is imported after this boundary.
from scripts import p106b_verified_trace_data as data

TAG, SCHEMA = 'p106b_verified_trace_recovery_v2_s1337', 'P106B_VERIFIED_TRACE_DRIVER_RECOVERY_V2'
SCRIPT, TEST = 'scripts/diag_p106b_verified_trace_recovery.py', 'scripts/test_p106b_verified_trace_recovery.py'
F4 = 'handoff/audit/WIP_20261021_VERIFIED_TRACE_RECOVERY_F4.json'
PARENT_REF = 'handoff/audit/WIP_20261021_VERIFIED_TRACE_PARENT.json'
PARENT_REF_SHA = '4F97C1B724F95E11D1E45660AA4777E2FBDC14D300F428DE277D9D0F56D336EB'
PARENT_PATH = 'runs/ckpt/m100s10_ko-en_broad4_p106b_native595_broad_v1_s1337_float.pt'
PARENT_SHA = '2630B4C2862A41CB677AC9CAA89B0F2DD03234C4FD540FCCA6205AA847CF1C71'
PARENT_CORE = '00262611800E81BB117DB68F8053ED0A15A8454FBD9D34AFEFE44DB9A0D21B0D'
TOKENIZER = 'data_cache/tok-ko-en-32768-chat32.json'
TOKENIZER_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
NATIVE = 'data_cache/ko-en_601000000_chat32/train.bin'
NATIVE_SHA = 'DBD12235B4A1478177246B4BD5214C8B8BBF10D077CBA80304690AD12A8E59A2'
REPLAY_REF = 'data_cache/p106b_native595_broad_v1_s1337/frozen_reference.json'
CACHE, RAW, EVIDENCE = (ROOT / p / TAG for p in ('data_cache', 'runs/eval', 'test_result/evidence'))
ARMS, ENDPOINTS = ('direct', 'trace'), ('parent', 'direct', 'trace')
MODES = ('prepare', 'cost', 'budget', 'train', 'evaluate', 'readback')
COST_GROUPS = tuple(range(0, 32, 4))
CAPS = dict(prepare=600, cost=900, budget=600, train=1800, evaluate=1200, readback=600)
SFT_WIDTH = 128
LIMITS = dict(implementation_stop='2026-10-21T03:00:00+00:00', training_stop='2026-10-21T05:00:00+00:00',
    authority_end='2026-10-21T08:00:00+00:00', family_actual_worker_seconds=10800,
    train_worker_cap_seconds=1800, cost_worker_cap_seconds=900, evaluation_reserve_seconds=3600,
    record_reserve_seconds=600, evaluation_worker_cap_seconds=1200)
EXTRA_CODE = ('scripts/p106b_verified_trace_data.py', SCRIPT, TEST,
    'scripts/diag_p106b_verified_trace.py', 'scripts/test_p106b_verified_trace.py', 'tinylm/__init__.py', 'tinylm/paths.py',
    'tinylm/chat/__init__.py', 'tinylm/chat/tokens.py', 'tinylm/infer/__init__.py',
    'tinylm/data/prepare.py', 'tinylm/data/loader.py', 'tinylm/train/__init__.py',
    'tinylm/train/trainer.py', 'tinylm/train/lr_finder.py', 'tinylm/train/init_utils.py',
    'tinylm/train/init_mapping.py', 'tinylm/training_defaults.py', 'tinylm/eval/__init__.py',
    'tinylm/eval/evaluate.py', 'tinylm/eval/compare.py', 'tinylm/audit_io.py')
IMPLEMENTATION_READY = True


class Pending(RuntimeError): pass


def safe(relative, root=ROOT):
    relative = Path(relative); root = Path(root)
    if relative.is_absolute() or '..' in relative.parts or relative.parts[:1] in (('HF',), ('datasets',)):
        raise ValueError('explicit nonprotected repository-relative path required')
    path = root
    if path.is_symlink(): raise ValueError('linked ROOT refused')
    for part in relative.parts:
        path = path / part
        if path.is_symlink(): raise ValueError('linked path/ancestor refused')
    return path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest().upper()


def required(relative, root=ROOT):
    path = safe(relative, root)
    with path.open('rb') as stream: raw = stream.read(20_000_000)
    if len(raw) >= 20_000_000: raise ValueError('small JSON limit exceeded')
    value = json.loads(raw.decode('utf-8'))
    if not isinstance(value, dict): raise ValueError('JSON object required')
    return value


def write(path, value):
    path = Path(path)
    if not any(path.is_relative_to(p) for p in (CACHE, RAW, EVIDENCE)):
        raise ValueError('only new pilot namespace may be written')
    safe(str(path.relative_to(ROOT)), ROOT)
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(raw) >= 20_000_000: raise ValueError('small report must be below20MB')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(raw)


def file_binding(value, *, assets=False, expected=None, root=ROOT):
    if (not isinstance(value, dict) or set(value) != {'path', 'bytes', 'sha256'}
            or type(value.get('bytes')) is not int or value['bytes'] <= 0
            or not isinstance(value.get('sha256'), str) or len(value['sha256']) != 64
            or expected is not None and value.get('path') != expected):
        raise ValueError('exact file path/bytes/SHA descriptor required')
    path = safe(value['path'], root)
    if assets or not value['path'].startswith('runs/ckpt/'):
        if path.stat().st_size != value['bytes'] or digest(path) != value['sha256']:
            raise ValueError('bound file changed: ' + value['path'])
    return path


def parent_reference(*, assets=False, root=ROOT):
    if digest(safe(PARENT_REF, root)) != PARENT_REF_SHA:
        raise ValueError('immutable root parent descriptor bytes changed')
    parent = required(PARENT_REF, root)
    if (parent.get('schema') != 'TINYLM_VERIFIED_TRACE_TRAINING_PARENT_V1'
            or parent.get('training_initializer_only') is not True or parent.get('inference_only_manifest_reused') is not False
            or parent.get('core_sha256') != PARENT_CORE or parent.get('checkpoint', {}).get('sha256') != PARENT_SHA
            or parent.get('actual_export', {}).get('checkpoint_changed') is not False
            or parent.get('actual_export', {}).get('hf_raw_access') != 0
            or len(parent.get('source_sha256', {})) != 88):
        raise ValueError('root sealed exact training-initializer descriptor required')
    header = parent.get('header', {})
    if (set(header) != {'cfg', 'step', 'tokenizer_sha256', 'tokenizer_lineage', 'quantization_route', 'experiment'}
            or parent.get('header_sha256') != data.sha(header) or parent.get('cfg_sha256') != data.sha(header['cfg'])
            or parent.get('route_sha256') != data.sha(header['quantization_route'])
            or header.get('step') != 704 or header.get('tokenizer_sha256') != TOKENIZER_SHA
            or header.get('tokenizer_lineage') != 'chat32' or header['quantization_route'].get('mode') != 'float'):
        raise ValueError('sealed cfg/header/route mismatch')
    file_binding(parent['checkpoint'], assets=assets, expected=PARENT_PATH, root=root)
    for key in ('report', 'activity', 'evaluation_report', 'evaluation_activity', 'historical_root_recount'):
        file_binding(parent[key], root=root)
    report = required(parent['report']['path'], root); activity = required(parent['activity']['path'], root)
    if (report.get('status') != 'TRAIN_COMPLETE' or report.get('checkpoint_sha256') != PARENT_SHA
            or report.get('final_core_sha256') != PARENT_CORE or report.get('updates') != 704
            or report.get('arm') != 'float' or report.get('cost') is not False
            or parent['source_sha256'] != report.get('code_sha256')
            or activity.get('complete') is not True or activity.get('returncode') != 0
            or activity.get('result_sha256') != parent['report']['sha256']):
        raise ValueError('closed parent report/activity binding mismatch')
    for name, sha in parent['source_sha256'].items():
        if not name.startswith(('scripts/', 'tinylm/')) or not name.endswith('.py') or digest(safe(name, root)) != sha:
            raise ValueError('parent source pin changed: ' + name)
    return parent


def info():
    f4 = required(F4); parent = parent_reference()
    if (f4.get('schema') != 'TINYLM_VERIFIED_SHORT_TRACE_F4_V1' or f4.get('tag') != TAG
            or f4.get('allowed_new_implementation_files') != ['scripts/p106b_verified_trace_data.py', SCRIPT, TEST]
            or PARENT_REF not in f4.get('root_owned_metadata', [])
            or f4.get('parent_descriptor_sha256') != PARENT_REF_SHA
            or PARENT_SHA not in f4.get('training_contract', {}).get('parent', '')
            or any(f4.get('execution_gates', {}).get(k) != v for k, v in LIMITS.items())):
        raise ValueError('exact root F4/limits required')
    pins = dict(parent['source_sha256'])
    pins.update({p: digest(safe(p)) for p in EXTRA_CODE})
    return dict(schema=SCHEMA, tag=TAG, code_sha256=pins, f4_sha256=digest(safe(F4)),
        parent_descriptor_sha256=PARENT_REF_SHA, parent_checkpoint_sha256=PARENT_SHA,
        parent_core_sha256=PARENT_CORE, tokenizer_sha256=TOKENIZER_SHA,
        arms=list(ARMS), endpoints=list(ENDPOINTS), seed=1337, rows=4096, passes=4, updates=128,
        micro_bs=8, accum=16, seq=1024, grad_checkpoint=True, adam_lr=5e-5, muon_lr=2e-4,
        sft_execution_width=SFT_WIDTH, padded_sft_slots_per_arm=4096 * 4 * SFT_WIDTH,
        maximum_1024_slot_ceiling=16777216, native_execution_width=1024,
        weight_decay=0., clip=1., objective='L0_ASSISTANT_MEAN_PLUS_NATIVE8192_MEAN',
        route='float', native_targets_per_update=8192, native_targets_per_arm=1048576,
        cost_group_updates=list(COST_GROUPS), test_roots=128, test_views=4, test_answers=1024,
        train_observations=32, user_answers=6, endpoint_free_answers=1062, all_free_answers=3186,
        limits=LIMITS, mtp=False, teacher_calls=0, new_head_parameters=0, automatic_adoption=False)


def authority(mode, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None: raise ValueError('aware actual UTC required')
    key = 'implementation_stop' if mode == 'prepare' else 'training_stop' if mode in ('cost', 'train', 'budget') else 'authority_end'
    remaining = (datetime.fromisoformat(LIMITS[key]) - now).total_seconds()
    if key == 'authority_end': remaining -= LIMITS['record_reserve_seconds']
    if remaining <= 0: raise Pending('own preparation/training/authority boundary reached')
    return remaining


def boundary(mode):
    key = 'implementation_stop' if mode == 'prepare' else 'training_stop' if mode in ('cost', 'train', 'budget') else 'authority_end'
    end = datetime.fromisoformat(LIMITS[key])
    return end - timedelta(seconds=600) if key == 'authority_end' else end


def validate_activity(activity, key, identity, invocation):
    mode = invocation['mode']; begin, end = (datetime.fromisoformat(activity[k]) for k in ('started_at', 'ended_at'))
    if (phase_key(mode, invocation.get('arm'), invocation.get('endpoint')) != key
            or activity.get('info') != identity or activity.get('key') != key or activity.get('mode') != mode
            or activity.get('arm') != invocation.get('arm') or activity.get('endpoint') != invocation.get('endpoint')
            or activity.get('complete') is not True or type(activity.get('returncode')) is not int or activity['returncode'] != 0
            or activity.get('error_type') is not None or begin.tzinfo is None or end.tzinfo is None or begin > end
            or begin >= boundary(mode) or end > boundary(mode) + timedelta(seconds=30)
            or type(activity.get('worker_pid')) is not int or activity['worker_pid'] <= 0
            or type(activity.get('worker_pgid')) is not int or activity['worker_pgid'] != activity['worker_pid']
            or type(activity.get('max_wall_sec')) is not int or activity['max_wall_sec'] != invocation['max_wall_sec']
            or not 60 <= activity['max_wall_sec'] <= CAPS[mode]
            or any(type(activity.get(k)) not in (int, float) or not math.isfinite(activity[k]) or activity[k] < 0
                   for k in ('seconds', 'utc_seconds'))
            or activity['seconds'] > activity['max_wall_sec'] + 30
            or not math.isclose(activity['utc_seconds'], (end - begin).total_seconds(), abs_tol=1e-5)):
        raise ValueError('strict original invocation/UTC boundary/cap/PGID/elapsed activity required')
    admission = activity.get('admission')
    if (not isinstance(admission, dict) or admission.get('requested_cap') != activity['max_wall_sec']
            or any(type(admission.get(k)) not in (int, float) or not math.isfinite(admission[k])
                   or admission[k] < activity['max_wall_sec'] for k in ('utc_remaining', 'family_remaining'))):
        raise ValueError('original actual worker cap/remaining admission required')


def phase_key(mode, arm=None, endpoint=None):
    if mode not in MODES: raise ValueError('known mode required')
    if mode in ('cost', 'train'):
        if arm not in ARMS or endpoint is not None: raise ValueError('training policy only')
        return mode + '_' + arm
    if mode == 'evaluate':
        if endpoint not in ENDPOINTS or arm is not None: raise ValueError('one evaluation endpoint required')
        return mode + '_' + endpoint
    if arm is not None or endpoint is not None: raise ValueError('unused selector refused')
    return mode


def report_path(key): return EVIDENCE / key / 'report.json'
def activity_path(key): return EVIDENCE / ('activity_' + key + '.json')
def checkpoint(arm):
    if arm not in ARMS: raise ValueError('known child policy required')
    return safe('runs/ckpt/' + 'm100s10_ko-en_' + TAG + '_' + arm + '.pt', ROOT)


def closed(key):
    activity = required(str(activity_path(key).relative_to(ROOT)))
    value = required(str(report_path(key).relative_to(ROOT)))
    validate_activity(activity, key, info(), value['invocation'])
    if (activity.get('result_sha256') != digest(report_path(key))
            or activity.get('info') != info() or value.get('info') != info()):
        raise ValueError('same-source closed worker/report required: ' + key)
    return value


def replay_reference(*, assets=False):
    ref = required(REPLAY_REF); binding = ref['binding']; offsets = binding['native_train_offsets']
    parent = parent_reference()
    if (binding.get('native_train_file') != NATIVE or binding.get('native_train_sha256') != NATIVE_SHA
            or len(offsets) != 5632 or data.sha(offsets) != binding['native_selection']['offsets_sha256']
            or data.sha(offsets) != parent['header']['experiment']['native_offsets_sha256']
            or digest(safe(REPLAY_REF)) != parent['header']['experiment']['reference_sha256']):
        raise ValueError('exact old native5632 selection required')
    chosen = offsets[:1024]; ordered = sorted(chosen)
    if (any(type(i) is not int or i < 0 or i + 1025 > 597995000 for i in chosen)
            or any(b - a < 1025 for a, b in zip(ordered, ordered[1:]))):
        raise ValueError('1024 in-bounds disjoint1025-ID replay windows required')
    if assets:
        path = safe(NATIVE)
        if path.stat().st_size != 2 * 597995000 or digest(path) != NATIVE_SHA: raise ValueError('native source bytes changed')
    return dict(native_access='INDEXED_TRAIN_ONLY', native_train_file=NATIVE,
        native_train_sha256=NATIVE_SHA, native_train_offsets=chosen, offsets_sha256=data.sha(chosen),
        source_reference_sha256=digest(safe(REPLAY_REF)), source_selection_sha256=data.sha(offsets))


def put_rows(directory, stem, rows):
    import_environment(); safe(str(Path(directory).relative_to(ROOT)), ROOT)
    from scripts.p106b_shards import ShardWriter, verify
    safe(str(Path(directory).relative_to(ROOT)), ROOT)
    writer = ShardWriter(directory, stem, limit=19_999_999)
    for row in rows: writer.append(row)
    manifest = writer.close(lineage=dict(tag=TAG, stem=stem)); verify(directory, manifest)
    return manifest


def get_rows(directory, stem, manifest):
    import_environment(); safe(str(Path(directory).relative_to(ROOT)), ROOT)
    from scripts.p106b_shards import verify
    if required(str((directory / (stem + '_shards_manifest.json')).relative_to(ROOT))) != manifest:
        raise ValueError('exact raw manifest required')
    verify(directory, manifest); rows = []
    for part in manifest['shards']:
        with (directory / part['path']).open(encoding='utf-8') as stream:
            rows.extend(json.loads(line) for line in stream)
    if len(rows) != manifest['rows']: raise ValueError('raw row count differs')
    return rows


def train_observations(rows):
    selected = []
    for family, count in (('addition', 16), ('lookup', 8), ('update', 8)):
        for language in ('ko', 'en'):
            lane = [r for r in rows if r['meta']['family'] == family and r['meta']['language'] == language]
            lane.sort(key=lambda r: data.sha(['TRAIN_OBSERVE', r['meta']['root']]))
            if len(lane) < count // 2: raise ValueError('full fixed TRAIN observation supply required')
            selected.extend(lane[:count // 2])
    return selected


def record_counts(record):
    x, y, owners = record.x, record.y, record.segments
    if (not 0 < len(x) <= SFT_WIDTH or len(x) != len(y) or len(x) != len(owners)
            or any(type(v) is not int or not 0 <= v < 32768 for v in x)
            or any(type(v) is not int or v != -100 and not 0 <= v < 32768 for v in y)
            or any(type(v) is not int or v not in (0, 1) for v in owners)
            or any((target == -100 and owner != 0) or (target != -100 and owner != 1) for target, owner in zip(y, owners))):
        raise ValueError('exact single-assistant shifted owner/mask/shape required')
    total = sum(v != -100 for v in y); eot = sum(v == 4 for v in y)
    if total <= 0 or total > 128 or eot != 1: raise ValueError('positive assistant targets/EOT1/generation128 fit required')
    return dict(x_tokens=len(x), assistant_targets=total, content_targets=total - eot, eot_targets=eot)


def group_totals(wires, groups):
    indices = [i for micro in groups for i in micro]
    if (len(indices) != 128 or len(set(indices)) != 128 or any(type(i) is not int or not 0 <= i < len(wires) for i in indices)
            or any(len(m) != 8 for m in groups) or len(groups) != 16):
        raise ValueError('same128/16x8 whole-update consumer required')
    selected = [wires[i] for i in indices]
    result = {k: sum(row['counts'][k] for row in selected) for k in ('x_tokens', 'assistant_targets', 'content_targets', 'eot_targets')}
    return dict(result, positive_rows=128, native_targets=8192)


def prepare():
    authority('prepare'); began = time.perf_counter()
    safe(str(CACHE.relative_to(ROOT)), ROOT)
    if CACHE.exists(): raise FileExistsError('preserve complete/partial pilot corpus')
    parent = parent_reference(assets=True); replay = replay_reference(assets=True); import_environment()
    from tinylm.train.mtp_sft import encode_record
    from tinylm.chat.serialize import serialize
    tok = tokenizer()
    course = data.build_course(); schedule = data.training_schedule()
    observation = train_observations(course['train']['direct'])
    safe(str(CACHE.relative_to(ROOT)), ROOT)
    CACHE.mkdir(parents=True, exist_ok=False); manifests = {}; counts = {}; updates = {}
    for split in ('train', 'dev', 'test'):
        for arm in ARMS:
            rows = course[split][arm]; wires = []
            for row in rows:
                authority('prepare'); record = encode_record(row, tok, context=1024)
                wire = dict(row=row, record=dict(x=record.x, y=record.y, segments=record.segments), counts=record_counts(record))
                prompt = serialize(dict(messages=row['messages'][:-1]), 'chatml', add_generation_prompt=True)
                prefix = tok.encode(prompt).ids
                first = next(i for i, target in enumerate(record.y) if target != -100)
                if first != len(prefix) - 1 or record.x[:len(prefix)] != prefix or len(prefix) + 128 > 1024:
                    raise ValueError('exact actual generation prefix/shift/mask/budget required')
                wire.update(prompt_sha256=data.sha(prompt), prompt_ids_sha256=data.sha(prefix), prompt_tokens=len(prefix))
                wire['record_sha256'] = data.sha(wire['record']); wires.append(wire)
            stem = split + '_' + arm; manifests[stem] = put_rows(CACHE, stem, wires)
            counts[stem] = {k: sum(w['counts'][k] for w in wires) for k in wires[0]['counts']}
            if split == 'train': updates[arm] = [group_totals(wires, group['micros']) for group in schedule]
    user_encodings = []
    for question in data.USER6:
        prompt = serialize(dict(messages=[dict(role='user', content=question)]), 'chatml', add_generation_prompt=True)
        prefix = tok.encode(prompt).ids
        if len(prefix) + 128 > 1024: raise ValueError('complete user6 context plus128 required')
        user_encodings.append(dict(prompt_sha256=data.sha(prompt), prompt_ids_sha256=data.sha(prefix), prompt_tokens=len(prefix)))
    from scripts.p106b_native_windows import reader
    windows = reader(ROOT, replay)
    window_sha256 = [data.sha(windows[i].astype('int64').tolist()) for i in range(1024)]
    authority('prepare')
    frozen = dict(info=info(), status='CPU_PREPARED', manifests=manifests, counts=counts, updates=updates,
        schedule=schedule, schedule_sha256=data.sha(schedule), course_report=course['report'], replay=replay,
        train_observation_roots=[r['meta']['root'] for r in observation],
        train_observation_rows_sha256=data.sha(observation), train_observation_count=32,
        evaluation_counts=dict(test=1024, train_observation=32, user=6, total=1062),
        parent_header_sha256=parent['header_sha256'], model_constructions=0, checkpoint_tensor_loads=0,
        user_encodings=user_encodings,
        native_window_ids_sha256=window_sha256,
        tokenizer_loaded=True, meaningful_training='NOT_RUN', cpu_seconds=time.perf_counter() - began)
    write(CACHE / 'frozen.json', frozen)
    return dict(info=info(), status='CPU_PREPARED', frozen_sha256=digest(CACHE / 'frozen.json'),
        evaluation_counts=frozen['evaluation_counts'], cpu_seconds=frozen['cpu_seconds'], models_loaded=0, checkpoint_tensor_loads=0)


def prepared(*, assets=False):
    prepare_report = closed('prepare')
    frozen_path = safe(str((CACHE / 'frozen.json').relative_to(ROOT)), ROOT)
    if digest(frozen_path) != prepare_report.get('frozen_sha256'):
        raise ValueError('actual frozen bytes must match original closed prepare report')
    value = required(str((CACHE / 'frozen.json').relative_to(ROOT)))
    if (value.get('status') != 'CPU_PREPARED' or value.get('info') != info()
            or value.get('schedule') != data.training_schedule() or value.get('schedule_sha256') != data.sha(value['schedule'])
            or value.get('evaluation_counts') != dict(test=1024, train_observation=32, user=6, total=1062)
            or value.get('replay') != replay_reference(assets=assets)):
        raise ValueError('same full CPU source/data/replay/schedule contract required')
    parent_reference(assets=assets)
    if digest(safe(TOKENIZER)) != TOKENIZER_SHA: raise ValueError('prepared tokenizer bytes changed')
    validate_frozen_corpora(value)
    return value


def corpus(value, split, arm):
    stem = split + '_' + arm
    wires = get_rows(CACHE, stem, value['manifests'][stem])
    if len(wires) != (4096 if split == 'train' else 1024): raise ValueError('full fixed corpus required')
    for wire in wires:
        record = wire['record']
        class RecordView:
            x, y, segments = record['x'], record['y'], record['segments']
        if wire['record_sha256'] != data.sha(record) or record_counts(RecordView) != wire['counts']:
            raise ValueError('frozen encoded record/mask/counts changed')
    actual = {k: sum(w['counts'][k] for w in wires) for k in wires[0]['counts']}
    if actual != value['counts'][stem]: raise ValueError('actual encoded corpus totals differ from frozen preparation')
    if split == 'train' and [group_totals(wires, g['micros']) for g in value['schedule']] != value['updates'][arm]:
        raise ValueError('actual all128 encoded group denominators differ from preparation')
    return wires


def validate_frozen_corpora(value):
    stems = {split + '_' + arm for split in data.COUNTS for arm in ARMS}
    if set(value['manifests']) != stems or set(value['counts']) != stems:
        raise ValueError('all six original encoded manifests and denominators required')
    all_roots = set()
    for split, family_counts in data.COUNTS.items():
        root_ids = value['course_report']['root_ids'][split]
        if len(root_ids) != sum(family_counts.values()) or len(set(root_ids)) != len(root_ids) or all_roots.intersection(root_ids):
            raise ValueError('original distinct full split roots required')
        all_roots.update(root_ids); policies = {}
        for arm in ARMS:
            wires = corpus(value, split, arm); policies[arm] = wires; keys = set(); families = Counter(); roots = Counter()
            for wire in wires:
                row = wire['row']; meta = row['meta']; task = meta['task']; messages = row['messages']; prefix = wire['prompt_tokens']
                key = (meta['root'], meta['language'], meta['view'])
                gold = data.score_response(task, messages[1]['content'], meta['language'], arm)
                if (key in keys or meta['root'] not in root_ids or meta['root'] != data.canonical_root(task)
                        or data.split_for_root(meta['root']) != split or data.is_reserved(task)
                        or meta['policy'] != arm or meta['split'] != split or meta['family'] != task['family']
                        or meta['language'] not in ('ko', 'en') or type(meta['view']) is not int or not 0 <= meta['view'] < 4
                        or len(messages) != 2 or messages[0]['role'] != 'user' or messages[1]['role'] != 'assistant'
                        or meta['question_sha256'] != data.sha(messages[0]['content']) or meta['gold_trace_in_prompt'] is not False
                        or type(meta['gold_value']) is not int or meta['gold_value'] != data.truth(task)
                        or not gold['policy_compliant'] or not gold['final_correct']
                        or type(prefix) is not int or not 1 < prefix <= len(wire['record']['x'])
                        or data.sha(wire['record']['x'][:prefix]) != wire['prompt_ids_sha256']
                        or next(i for i, target in enumerate(wire['record']['y']) if target != -100) != prefix - 1):
                    raise ValueError('actual encoded row/root/question/mask/gold/policy/prefix contract differs')
                keys.add(key); roots[meta['root']] += 1; families[(meta['family'], meta['language'])] += 1
            multiplier = 1 if split == 'train' else 8
            if (set(roots) != set(root_ids) or any(n != multiplier for n in roots.values())
                    or any(families[(family, lang)] != count * multiplier // 2 for family, count in family_counts.items() for lang in ('ko', 'en'))):
                raise ValueError('full exact original family/language/root denominators required')
            if split != 'train' and keys != {(root, lang, view) for root in root_ids for lang in ('ko', 'en') for view in range(4)}:
                raise ValueError('original full language x four-view heldout roots required')
        for direct, trace in zip(policies['direct'], policies['trace']):
            if (direct['row']['messages'][0] != trace['row']['messages'][0]
                    or any(direct[k] != trace[k] for k in ('prompt_tokens', 'prompt_sha256', 'prompt_ids_sha256'))):
                raise ValueError('direct/trace questions and actual prefixes must match exactly')


def tokenizer():
    import_environment()
    raw = safe(TOKENIZER).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != TOKENIZER_SHA: raise ValueError('pinned tokenizer bytes changed')
    from tokenizers import Tokenizer
    tok = Tokenizer.from_str(raw.decode('utf-8'))
    if (tok.get_vocab_size() != 32768 or tok.token_to_id('<|im_start|>') != 3
            or tok.token_to_id('<|im_end|>') != 4 or tok.token_to_id('<eos>') != 2):
        raise ValueError('same decoded chat32 vocabulary/terminal map required')
    return tok


def gpu_idle():
    reply = subprocess.run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader,nounits'],
                           text=True, capture_output=True, timeout=10, check=False)
    if reply.returncode or reply.stderr.strip(): raise Pending('NVML process query failed; no GPU admission')
    for line in reply.stdout.splitlines():
        if not line.strip(): continue
        if not line.strip().isdigit() or int(line.strip()) != os.getpid(): raise Pending('other/unknown compute PID; GPU serial only')
    memory = subprocess.run(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
                            text=True, capture_output=True, timeout=10, check=False)
    rows = memory.stdout.splitlines()
    if memory.returncode or memory.stderr.strip() or len(rows) != 1 or not rows[0].strip().isdigit() or int(rows[0]) < 14000:
        raise Pending('single GPU free-memory point gate failed; not continuous/OOM guarantee')


@contextmanager
def loaded(endpoint='parent', *, training=False):
    parent = parent_reference(assets=True); import_environment()
    tok = tokenizer()
    import torch
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from scripts import p106b_weight_route as method
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    path = safe(PARENT_PATH) if endpoint == 'parent' else checkpoint(endpoint)
    expected = PARENT_SHA if endpoint == 'parent' else read_training(endpoint, cost=False)['checkpoint_sha256']
    if digest(path) != expected: raise ValueError('exact initializer/child checkpoint bytes required')
    runtime_counts = dict(checkpoint_tensor_loads=0, model_constructions=0, cuda_transfers=0)
    payload = torch.load(path, map_location='cpu', weights_only=True); runtime_counts['checkpoint_tensor_loads'] += 1
    header = {k: v for k, v in payload.items() if k != 'model'}
    expected_core = PARENT_CORE
    if endpoint == 'parent':
        if data.sha(header) != parent['header_sha256']: raise ValueError('actual parent full header differs')
    else:
        trained = read_training(endpoint, cost=False); expected_core = trained['final_core_sha256']
        if (set(payload) != {'model', 'cfg', 'step', 'tokenizer_sha256', 'tokenizer_lineage', 'quantization_route', 'verified_trace'}
                or payload.get('step') != 128 or payload.get('tokenizer_sha256') != TOKENIZER_SHA
                or payload.get('tokenizer_lineage') != 'chat32'
                or payload.get('verified_trace') != checkpoint_header(trained)): raise ValueError('child training header differs')
    cfg = TMTConfig(**payload['cfg'])
    if data.sha(asdict(cfg)) != parent['cfg_sha256'] or not cfg.grad_checkpoint or cfg.mtp_aux:
        raise ValueError('unchanged parent cfg/ckptON/MTPoff required')
    torch.manual_seed(1337)
    with torch.device('cpu'): model = TiedMLPTransformer(cfg)
    runtime_counts['model_constructions'] += 1
    def fingerprint(base): return state_fingerprint(base)
    fingerprint.runtime_counts = runtime_counts
    gpu = False; route = None
    try:
        with method.weight_route(model, 'float') as cpu:
            method.load_routed_state(model, payload, 'float')
            if state_fingerprint(model) != expected_core: raise ValueError('strict CPU core mismatch')
        del payload; cpu = None
        authority('train' if training else 'evaluate'); gpu_idle()
        torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
        gpu = True; model = model.cuda(); runtime_counts['cuda_transfers'] += 1
        with method.weight_route(model, 'float') as route:
            route.assert_active(); model.clear_quant(); model.set_anneal(1.)
            if training: model.train()
            else:
                model.eval()
                with torch.no_grad(): model.freeze_quant()
            try: yield torch, model, cfg, tok, route, fingerprint
            finally: model.clear_quant()
    finally:
        model.clear_quant(); model = route = None; gc.collect()
        if gpu: torch.cuda.empty_cache()


def optimizer_groups(model):
    import_environment()
    from scripts.diag_p106b_relation_bind import make_optimizers
    adam, muon, groups = make_optimizers(model)
    actual = [dict(optimizer=name, group=index, lr=group['lr'], weight_decay=group['weight_decay'],
                   tensors=len(group['params']), parameters=sum(p.numel() for p in group['params']))
              for name, opt in (('adamw', adam), ('muon', muon)) for index, group in enumerate(opt.param_groups)]
    ids = [id(p) for opt in (adam, muon) for g in opt.param_groups for p in g['params']]
    if (len(ids) != len(set(ids)) or set(ids) != {id(p) for p in model.parameters() if p.requires_grad}
            or type(adam).__name__ != 'AdamW' or type(muon).__name__ != 'Muon' or adam.state or muon.state
            or groups != actual or getattr(muon, 'scale_mode', None) != 'rms'
            or any(g.get('scale_mode') != 'rms' for g in muon.param_groups)
            or any(g.get('betas') != (.9, .95) or g.get('eps') != 1e-8 for g in adam.param_groups)):
        raise ValueError('fresh original lowercase3tuple/groups/coverage required')
    validate_optimizer_receipts(groups)
    return adam, muon, groups


def validate_optimizer_receipts(groups):
    if not isinstance(groups, list) or not groups: raise ValueError('actual nonempty optimizer groups required')
    for name in ('adamw', 'muon'):
        selected = [g for g in groups if g.get('optimizer') == name]
        if not selected or [g.get('group') for g in selected] != list(range(len(selected))):
            raise ValueError('actual lowercase consecutive optimizer group indices required')
    for group in groups:
        if (set(group) != {'optimizer', 'group', 'lr', 'weight_decay', 'tensors', 'parameters'}
                or group['optimizer'] not in ('adamw', 'muon') or type(group['group']) is not int
                or any(type(group[k]) is not int or group[k] <= 0 for k in ('tensors', 'parameters'))
                or type(group['lr']) not in (int, float) or type(group['weight_decay']) not in (int, float)
                or group['weight_decay'] != 0 or group['lr'] != (5e-5 if group['optimizer'] == 'adamw' else 2e-4)):
            raise ValueError('actual unchanged LR5e-5/Muon2e-4/WD0 optimizer receipt required')


def step_identity(value, index, cost=False):
    actual = COST_GROUPS[index] if cost else index
    group = value['schedule'][actual]
    return actual, group


def checkpoint_header(report):
    return {k: report[k] for k in ('tag', 'arm', 'actual_updates', 'parent_checkpoint_sha256',
        'initial_core_sha256', 'final_core_sha256', 'frozen_sha256')}


def _precision_types():
    source = safe('scripts/diag_p101a_mtp_parity.py')
    tree = ast.parse(source.read_text(encoding='utf-8'))
    selected = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name in ('CaptureTokens', 'PrecisionForward')]
    if [n.name for n in selected] != ['CaptureTokens', 'PrecisionForward']: raise ValueError('pinned precision class contract differs')
    namespace = dict(nullcontext=nullcontext)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), 'exec'), namespace)
    return namespace['CaptureTokens'], namespace['PrecisionForward']


def dev_ce(torch, model, route, wires):
    import_environment()
    from tinylm.train import mtp_sft as core
    _, precision = _precision_types(); total = targets = 0
    model.clear_quant(); model.eval()
    with torch.no_grad(): model.freeze_quant()
    try:
        with torch.no_grad():
            for start in range(0, len(wires), 8):
                batch = [core.Record(**w['record']) for w in wires[start:start + 8]]
                x, y, owners = core.pad_records(batch, 0, 'cuda', fixed_width=SFT_WIDTH, batch_size=8)
                values, counts = core.components(model, precision(model, 'fp32_math')(x, return_hidden=True), y, owners, horizons=())
                total += float(values[1]); targets += counts[1]
        if targets != sum(w['counts']['assistant_targets'] for w in wires): raise ValueError('full DEV targets differ')
        return dict(ce=total / targets, targets=targets, rows=len(wires), scope='POLICY_SPECIFIC_TF_NOT_FINAL_ANSWER_ACCURACY')
    finally:
        model.clear_quant(); model.train(); model.set_anneal(1.); route.assert_active()


def native32(model):
    import_environment()
    import torch
    from scripts.diag_p106b_relation_bind import native_probe
    with torch.no_grad(): return native_probe(model)


def train(arm, cost=False):
    value = prepared(assets=True); mode = 'cost' if cost else 'train'; authority(mode)
    import_environment()
    key = phase_key(mode, arm); directory = safe(str((RAW / key).relative_to(ROOT)), ROOT)
    if directory.exists() or not cost and checkpoint(arm).exists(): raise FileExistsError('previous complete/partial raw/CP preserved')
    reservation = None if cost else budget()
    if not cost and not reservation['fits']: raise Pending('fresh all-pending reservation does not fit')
    wires = corpus(value, 'train', arm); dev = [] if cost else corpus(value, 'dev', arm)
    from scripts.p106b_native_windows import reader
    from scripts.p106b_shards import ShardWriter
    from tinylm.train import mtp_sft as core
    from scripts import p106b_content_objective as objective
    windows = reader(ROOT, value['replay'])
    safe(str(directory.relative_to(ROOT)), ROOT)
    directory.mkdir(parents=True, exist_ok=False); writer = None; events = []; history = []
    began = time.perf_counter()
    with loaded(training=True) as (torch, model, cfg, tok, route, fingerprint):
        initial = fingerprint(model)
        if initial != PARENT_CORE: raise ValueError('fresh common parent required')
        adam, muon, groups = optimizer_groups(model); identities = (id(model), id(adam), id(muon))
        if not cost and groups != read_training(arm, cost=True)['actual_optimizer_groups']:
            raise ValueError('actual cost/train optimizer groups differ')
        compile_directory = safe(str((CACHE / ('compile_' + key)).relative_to(ROOT)), ROOT)
        os.environ['TORCHINDUCTOR_CACHE_DIR'] = str(compile_directory)
        forward = torch.compile(model, mode='default'); torch.cuda.reset_peak_memory_stats()
        safe(str(directory.relative_to(ROOT)), ROOT)
        writer = ShardWriter(directory, 'updates', limit=19_999_999)
        try:
            before = None if cost else dict(dev=dev_ce(torch, model, route, dev), native=native32(model))
            for index in range(8 if cost else 128):
                authority(mode); route.assert_active(); model.clear_quant(); model.train(); model.set_anneal(1.)
                if identities != (id(model), id(adam), id(muon)): raise ValueError('model/optimizer replacement forbidden')
                actual, group = step_identity(value, index, cost); tick = time.perf_counter()
                records = [core.Record(**wires[i]['record']) for micro in group['micros'] for i in micro]
                plan = objective.make_weights(records, policy='token'); expected = value['updates'][arm][actual]
                if (plan.targets != expected['assistant_targets'] or plan.content_targets != expected['content_targets']
                        or plan.eot_targets != expected['eot_targets']): raise ValueError('whole-update assistant denominators differ')
                adam.zero_grad(set_to_none=True); muon.zero_grad(set_to_none=True); sums = Counter(); observed = Counter()
                for offset in range(0, 128, 8):
                    batch = records[offset:offset + 8]
                    x, y, owners = core.pad_records(batch, 0, 'cuda', fixed_width=SFT_WIDTH, batch_size=8)
                    weights = objective.make_tensor(plan, range(offset, offset + 8), width=SFT_WIDTH, device='cuda')
                    with torch.autocast('cuda', dtype=torch.bfloat16):
                        parts, counts = objective.components(model, forward(x, return_hidden=True), y, owners, weights)
                    if not bool(torch.isfinite(parts['weighted'])): raise ValueError('nonfinite assistant loss')
                    if x.numel() != 8 * SFT_WIDTH: raise ValueError('same common128 micro execution shape required')
                    parts['weighted'].backward()
                    observed.update(assistant_targets=counts['targets'], content_targets=counts['content'],
                                    eot_targets=counts['eot'], positive_rows=len(batch), x_tokens=sum(len(r.x) for r in batch))
                    for name in ('raw', 'content', 'eot'): sums[name] += float(parts[name].detach())
                if observed['assistant_targets'] != plan.targets: raise ValueError('all16 actual micro targets must equal whole update')
                native = [core.Record(windows[i][:-1].astype('int64').tolist(), windows[i][1:].astype('int64').tolist(), [1] * 1024)
                          for i in range(actual * 8, (actual + 1) * 8)]
                actual_window_sha256 = [data.sha(row.x + [row.y[-1]]) for row in native]
                expected_window_sha256 = value['native_window_ids_sha256'][actual * 8:(actual + 1) * 8]
                if actual_window_sha256 != expected_window_sha256: raise ValueError('actual native ID windows differ from CPU freeze')
                nx, ny, ns = core.pad_records(native, 0, 'cuda', fixed_width=1024, batch_size=8)
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    parts, counts = core.components(model, forward(nx, return_hidden=True), ny, ns, horizons=())
                    loss = parts[1] / 8192
                if counts[1] != 8192 or not bool(torch.isfinite(loss)): raise ValueError('native8192 mean required')
                observed['native_targets'] = counts[1]
                if dict(observed) != expected: raise ValueError('actual rows/x/targets/content/EOT/native must equal original CPU frozen counts')
                loss.backward(); norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                if not bool(torch.isfinite(norm)): raise ValueError('nonfinite gradient')
                adam.step(); muon.step(); torch.cuda.synchronize()
                event = dict(update=index + 1, source_update=actual, epoch=group['epoch'], **dict(observed),
                    native_indices=list(range(actual * 8, (actual + 1) * 8)),
                    native_window_ids_sha256=data.sha(actual_window_sha256),
                    assistant_ce=sums['raw'] / plan.targets, content_ce=sums['content'] / plan.content_targets,
                    eot_ce=sums['eot'] / plan.eot_targets, native_ce=float(loss.detach()),
                    gradient_norm=float(norm), clipped=bool(norm > 1.), step_seconds=time.perf_counter() - tick)
                writer.append(event); events.append(event)
                if index < 8 or (index + 1) % 32 == 0: print('[TRACE_UPDATE] ' + json.dumps(event), flush=True)
                if not cost and (index + 1) % 32 == 0:
                    history.append(dict(update=index + 1, dev=dev_ce(torch, model, route, dev), native=native32(model)))
            raw = writer.close(lineage=dict(tag=TAG, arm=arm, cost=cost)); writer = None
            model.clear_quant(); model.eval(); model.set_anneal(1.)
            with torch.no_grad(): model.freeze_quant()
            final = fingerprint(model)
            result = dict(info=info(), tag=TAG, arm=arm, status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE',
                cost=cost, actual_updates=len(events), initial_core_sha256=initial, final_core_sha256=final,
                parent_checkpoint_sha256=PARENT_SHA, frozen_sha256=digest(CACHE / 'frozen.json'),
                actual_optimizer_groups=groups, optimizer_identities=list(identities), optimizer_saved=False,
                fresh_optimizer=True, raw_manifest=raw, history=history, before=before, reservation=reservation,
                optimizer_contract=dict(adam_betas=list(adam.param_groups[0]['betas']), adam_eps=adam.param_groups[0]['eps'],
                    muon_scale_mode=muon.scale_mode, muon_group_scale_modes=[g['scale_mode'] for g in muon.param_groups]),
                step_seconds=[e['step_seconds'] for e in events], grad_max=max(e['gradient_norm'] for e in events),
                clip_events=sum(e['clipped'] for e in events), optimizer_factory_calls=1,
                optimizer_reset_between_updates=False, sft_padded_slots=(8 if cost else 128) * 128 * SFT_WIDTH,
                totals={k: sum(e[k] for e in events) for k in ('positive_rows', 'x_tokens', 'assistant_targets', 'content_targets', 'eot_targets', 'native_targets')},
                peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                whole_seconds=time.perf_counter() - began, checkpoint_writes=0 if cost else 1,
                quantization_route=route.metadata, runtime_counts=dict(fingerprint.runtime_counts), quality='NOT_EVALUATED')
            if not cost:
                authority('train')
                path = checkpoint(arm)
                with path.open('xb') as stream:
                    torch.save(dict(model=model.state_dict(), cfg=asdict(cfg), step=128,
                        tokenizer_sha256=TOKENIZER_SHA, tokenizer_lineage='chat32', quantization_route=route.metadata,
                        verified_trace=checkpoint_header(result)), stream)
                result.update(checkpoint=str(path.relative_to(ROOT)), checkpoint_sha256=digest(path))
            return result
        finally:
            if writer is not None and events:
                writer.close(lineage=dict(tag=TAG, arm=arm, cost=cost, partial=True))
            del forward


def read_training(arm, cost=False):
    mode = 'cost' if cost else 'train'; report = closed(phase_key(mode, arm)); value = prepared()
    if (report.get('status') != ('COST8_COMPLETE' if cost else 'TRAIN_COMPLETE') or report.get('cost') is not cost
            or report.get('arm') != arm or report.get('actual_updates') != (8 if cost else 128)
            or report.get('parent_checkpoint_sha256') != PARENT_SHA or report.get('initial_core_sha256') != PARENT_CORE
            or report.get('frozen_sha256') != digest(CACHE / 'frozen.json')):
        raise ValueError('full same-parent/source training receipt required')
    validate_optimizer_receipts(report['actual_optimizer_groups'])
    if (report.get('fresh_optimizer') is not True or report.get('optimizer_saved') is not False
            or report.get('optimizer_contract') != dict(adam_betas=[.9, .95], adam_eps=1e-8,
                muon_scale_mode='rms', muon_group_scale_modes=['rms'] * sum(g['optimizer'] == 'muon' for g in report['actual_optimizer_groups']))
            or report.get('sft_padded_slots') != (8 if cost else 128) * 128 * SFT_WIDTH
            or report.get('runtime_counts') != dict(checkpoint_tensor_loads=1, model_constructions=1, cuda_transfers=1)
            or type(report.get('final_core_sha256')) is not str or len(report['final_core_sha256']) != 64
            or cost and report.get('checkpoint_writes') != 0):
        raise ValueError('actual fresh optimizer/RMS/common128 shape/CP-write contract required')
    events = get_rows(RAW / phase_key(mode, arm), 'updates', report['raw_manifest'])
    if len(events) != (8 if cost else 128): raise ValueError('exact closed update count required')
    for index, event in enumerate(events):
        actual, group = step_identity(value, index, cost); expected = value['updates'][arm][actual]
        if (event.get('update') != index + 1 or event.get('source_update') != actual or event.get('epoch') != group['epoch']
                or any(event.get(k) != v for k, v in expected.items())
                or event.get('native_indices') != list(range(actual * 8, (actual + 1) * 8))
                or event.get('native_window_ids_sha256') != data.sha(value['native_window_ids_sha256'][actual * 8:(actual + 1) * 8])
                or any(type(event.get(k)) not in (int, float) or not math.isfinite(event[k]) for k in
                       ('assistant_ce', 'content_ce', 'eot_ce', 'native_ce', 'gradient_norm', 'step_seconds'))
                or event['step_seconds'] <= 0 or event.get('clipped') is not (event['gradient_norm'] > 1.)):
            raise ValueError('actual all-group/mask/native/gradient/timing receipt differs')
    if (report['step_seconds'] != [e['step_seconds'] for e in events]
            or report['grad_max'] != max(e['gradient_norm'] for e in events)
            or report['clip_events'] != sum(e['clipped'] for e in events)
            or report.get('optimizer_factory_calls') != 1 or report.get('optimizer_reset_between_updates') is not False
            or set(report['totals']) != {'positive_rows', 'x_tokens', 'assistant_targets', 'content_targets', 'eot_targets', 'native_targets'}):
        raise ValueError('step times/gradient/optimizer continuity/raw totals mismatch')
    if (any(type(report.get(k)) not in (int, float) or not math.isfinite(report[k]) or report[k] < 0
            for k in ('whole_seconds', 'peak_allocated_mib', 'peak_reserved_mib'))
            or report['whole_seconds'] < sum(report['step_seconds'])
            or report['peak_reserved_mib'] < report['peak_allocated_mib']):
        raise ValueError('finite actual worker-overhead/allocator measurements required')
    for key, total in report['totals'].items():
        if total != sum(e[key] for e in events): raise ValueError('full raw sum mismatch')
    if not cost and (report.get('checkpoint_writes') != 1 or digest(checkpoint(arm)) != report.get('checkpoint_sha256')):
        raise ValueError('strict child CP lineage mismatch')
    return report


def forecast(costs, pending, evaluation_pending, spent, remaining_train, remaining_end):
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in (spent, remaining_train, remaining_end)):
        raise ValueError('finite nonnegative actual time/remaining budgets required')
    if set(costs) != set(ARMS) or len(set(pending)) != len(pending) or not set(pending) <= set(ARMS):
        raise ValueError('both exact costs/all pending policies required')
    if len(set(evaluation_pending)) != len(evaluation_pending) or not set(evaluation_pending) <= set(ENDPOINTS):
        raise ValueError('all pending evaluation endpoints required')
    forecasts = {}
    for arm in ARMS:
        times = costs[arm]
        if len(times) != 8 or any(type(t) not in (int, float) or not math.isfinite(t) or t <= 0 for t in times):
            raise ValueError('eight actual finite positive cost steps required')
        forecasts[arm] = times[0] + max(times[1:]) * 127 * 1.35 + 300 if arm in pending else 0.
    training = sum(forecasts.values()); evaluation = len(evaluation_pending) * 1200; reserve = training + evaluation + 600
    fits = (training < remaining_train and reserve < remaining_end
            and spent + reserve <= 10800 and all(v <= 1800 for v in forecasts.values()))
    return dict(status='BUDGET_READY' if fits else 'HOLD_BUDGET', fits=fits,
        pending_training=list(pending), pending_evaluation=list(evaluation_pending), estimated_training_seconds=forecasts,
        evaluation_reserved_seconds=evaluation, record_reserved_seconds=600, actual_worker_seconds=spent,
        remaining_train_seconds=remaining_train, remaining_end_seconds=remaining_end,
        total_reserved_seconds=reserve, scope='COST_SAMPLE_FORECAST_NOT_UTC_COMPLETION_GUARANTEE')


def budget():
    authority('budget'); prepared(); costs = {}; pending = []
    for arm in ARMS:
        cost = read_training(arm, cost=True); costs[arm] = cost['step_seconds']
        if report_path('train_' + arm).exists(): read_training(arm)
        else: pending.append(arm)
    evaluation_pending = []
    for endpoint in ENDPOINTS:
        if report_path('evaluate_' + endpoint).exists(): read_evaluation(endpoint)
        else: evaluation_pending.append(endpoint)
    spent = actual_spent(info())
    return dict(info=info(), cost_report_sha256={arm: digest(report_path('cost_' + arm)) for arm in ARMS},
        **forecast(costs, pending, evaluation_pending, spent, authority('train'), authority('readback') + 600))


def read_budget():
    report = closed('budget'); costs = {}
    for arm in ARMS:
        cost = read_training(arm, cost=True); costs[arm] = cost['step_seconds']
        if report.get('cost_report_sha256', {}).get(arm) != digest(report_path('cost_' + arm)):
            raise ValueError('original both-policy actual cost reports changed')
    actual = forecast(costs, report['pending_training'], report['pending_evaluation'], report['actual_worker_seconds'],
                      report['remaining_train_seconds'], report['remaining_end_seconds'])
    if any(report.get(k) != v for k, v in actual.items()) or report.get('fits') is not True:
        raise ValueError('independent original cost/raw pending-budget calculation differs')
    return report


def evaluation_cases(value):
    test_wires = corpus(value, 'test', 'direct'); train_wires = corpus(value, 'train', 'direct')
    train_rows = [w['row'] for w in train_wires]
    observed = train_observations(train_rows)
    if [r['meta']['root'] for r in observed] != value['train_observation_roots'] or data.sha(observed) != value['train_observation_rows_sha256']:
        raise ValueError('same actual TRAIN one-row observations required')
    selected_train = [w for r in observed for w in train_wires if w['row']['meta']['root'] == r['meta']['root']]
    cases = [dict(lane=lane, row=w['row'], **{k: w[k] for k in ('prompt_sha256', 'prompt_ids_sha256', 'prompt_tokens')})
             for lane, wires in (('test', test_wires), ('train_observation', selected_train)) for w in wires]
    cases += [dict(lane='user', question=q, id='user_' + str(i), **value['user_encodings'][i]) for i, q in enumerate(data.USER6)]
    if len(cases) != 1062: raise ValueError('full1024TEST+32TRAIN+6USER free answers required')
    return cases


def emit(torch, model, cfg, tok, question):
    import_environment()
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample
    capture_type, precision = _precision_types()
    prompt = serialize(dict(messages=[dict(role='user', content=question)]), 'chatml', add_generation_prompt=True)
    prefix = tok.encode(prompt).ids
    if len(prefix) + 128 > cfg.max_seq_len: raise Pending('complete prompt plus128 exceeds context; never truncate')
    captured = capture_type(tok)
    _, meta = sample(precision(model, 'fp32_math'), cfg, captured, prompt, max_new=128, temperature=0., top_k=1,
        device='cuda', use_cache=True, logits_last_only=True, return_metadata=True, mtp_tokens=1, stop_token_sequences=[[4]])
    ids = captured.decoded_ids
    if (not isinstance(ids, list) or ids[:len(prefix)] != prefix or type(meta.get('generated_tokens')) is not int
            or len(ids) - len(prefix) != meta['generated_tokens'] or not 1 <= meta['generated_tokens'] <= 128):
        raise ValueError('actual prefix/generated ID count differs')
    generated = ids[len(prefix):]; reason = meta['finish_reason']
    terminal = [4] if reason == 'STOP_SEQUENCE' else [2] if reason == 'EOS' else []
    if (reason not in ('STOP_SEQUENCE', 'EOS', 'MAX_NEW') or terminal and generated[-1:] != terminal
            or reason == 'STOP_SEQUENCE' and meta.get('matched_stop_sequence') != [4]
            or reason != 'STOP_SEQUENCE' and meta.get('matched_stop_sequence') is not None
            or not terminal and len(generated) != 128): raise ValueError('actual terminal receipt differs')
    content = generated[:-1] if terminal else generated
    if any(t in (2, 4) for t in content): raise ValueError('terminal inside actual body')
    return tok.decode(content, skip_special_tokens=False), dict(meta, generated_ids=generated, terminal_ids=terminal,
        prompt_tokens=len(prefix), prompt_sha256=data.sha(prompt), prompt_ids_sha256=data.sha(prefix),
        precision='FP32_MATH', tf32=False, mtp=False, gold_trace_in_prompt=False, gold_history_used=False)


def evaluation_summary(events, cases):
    """Independent text rescoring and raw lane/root/counterfactual aggregation."""
    if len(events) != len(cases): raise ValueError('same full raw/case denominator required')
    lanes = {}; families = {}; presentations = {}; roots = {}; views = {}
    def add(bucket, event, score):
        bucket['rows'] = bucket.get('rows', 0) + 1
        reason = event['generation']['finish_reason']; finishes = bucket.setdefault('finish_reasons', {})
        finishes[reason] = finishes.get(reason, 0) + 1
        bucket['generated_tokens'] = bucket.get('generated_tokens', 0) + event['generation']['generated_tokens']
        if score is None:
            for key in ('final_contract', 'final_correct', 'trace_present', 'trace_valid', 'trace_final_agree'):
                bucket[key] = None
        else:
            for key in ('final_contract', 'final_correct', 'trace_present', 'trace_valid', 'trace_final_agree'):
                bucket[key] = bucket.get(key, 0) + int(score[key] is True)
            bucket['valid_trace_wrong_final'] = bucket.get('valid_trace_wrong_final', 0) + int(score['trace_valid'] is True and not score['final_correct'])
            bucket['right_final_invalid_trace'] = bucket.get('right_final_invalid_trace', 0) + int(score['final_correct'] and score['trace_valid'] is False)
    for index, (event, case) in enumerate(zip(events, cases)):
        if event.get('index') != index or event.get('lane') != case['lane'] or event.get('case_sha256') != data.sha(case):
            raise ValueError('independent raw summary requires exact original case order')
        score = None if case['lane'] == 'user' else data.score_response(case['row']['meta']['task'], event['answer'], case['row']['meta']['language'])
        if event.get('score') != score: raise ValueError('raw score differs from independent text regrade')
        add(lanes.setdefault(case['lane'], {}), event, score)
        if score is None: continue
        meta = case['row']['meta']; group = case['lane'] + ':' + meta['family'] + ':' + meta['language']
        add(families.setdefault(group, {}), event, score)
        for field, value in meta['presentation'].items():
            add(presentations.setdefault(group + ':' + field + '=' + str(value), {}), event, score)
        root_key = case['lane'] + ':' + meta['root']
        root = roots.setdefault(root_key, dict(family=meta['family'], languages={}, total={}))
        add(root['total'], event, score); add(root['languages'].setdefault(meta['language'], {}), event, score)
        if case['lane'] == 'test':
            group_key = (meta['family'], meta['root'], meta['language'])
            entry = views.setdefault(group_key, {})
            if meta['view'] in entry: raise ValueError('duplicate evaluation view in original root/language group')
            entry[meta['view']] = score
    counterfactual = {}
    for (family, _root, _language), group in views.items():
        if set(group) != {0, 1, 2, 3}: raise ValueError('all four original Cartesian views required')
        counts = counterfactual.setdefault(family, Counter())
        counts['root_language_groups'] += 1
        counts['all_four_final_correct'] += int(all(s['final_correct'] for s in group.values()))
        if family == 'addition':
            pairs = (('operand_order', 0, 1), ('operand_order', 2, 3), ('wording', 0, 2), ('wording', 1, 3))
        else:
            pairs = (('asked_target', 0, 1), ('asked_target', 2, 3), ('fact_order', 0, 2), ('fact_order', 1, 3))
        for kind, a, b in pairs:
            counts[kind + '_pairs'] += 1
            counts[kind + '_both_final_correct'] += int(group[a]['final_correct'] and group[b]['final_correct'])
            valid = group[a]['final_contract'] and group[b]['final_contract']
            expected_equal = kind != 'asked_target'
            counts[kind + '_valid_expected_relation'] += int(valid and (group[a]['final_value'] == group[b]['final_value']) == expected_equal)
    for root in roots.values():
        root['all_final_correct'] = root['total']['final_correct'] == root['total']['rows']
    return dict(lanes=lanes, families=families, presentations=presentations, roots=roots,
        counterfactual={key: dict(value) for key, value in counterfactual.items()},
        scope='INDEPENDENT_RAW_TEXT_RESCORING_AND_FULL_ROOT_COUNTERFACTUAL_RECOUNT')


def validate_generation(event, case, tok):
    generation = event['generation']; ids = generation.get('generated_ids'); reason = generation.get('finish_reason')
    terminal = [4] if reason == 'STOP_SEQUENCE' else [2] if reason == 'EOS' else []
    if (not isinstance(ids, list) or any(type(i) is not int or not 0 <= i < 32768 for i in ids)
            or type(generation.get('generated_tokens')) is not int or len(ids) != generation['generated_tokens'] or not 1 <= len(ids) <= 128
            or any(generation.get(k) != case[k] for k in ('prompt_sha256', 'prompt_ids_sha256', 'prompt_tokens'))
            or reason not in ('STOP_SEQUENCE', 'EOS', 'MAX_NEW') or generation.get('terminal_ids') != terminal
            or terminal and ids[-1:] != terminal or not terminal and len(ids) != 128
            or generation.get('matched_stop_sequence') != ([4] if reason == 'STOP_SEQUENCE' else None)
            or generation.get('stop_token_sequences') != [[4]] or generation.get('max_new') != 128
            or generation.get('eos_token_available') is not True or generation.get('stop_at_eos_requested') is not True
            or generation.get('stop_at_eos_effective') is not True or generation.get('precision') != 'FP32_MATH'
            or generation.get('tf32') is not False or generation.get('mtp') is not False
            or generation.get('gold_trace_in_prompt') is not False or generation.get('gold_history_used') is not False):
        raise ValueError('full actual prefix/terminal/ID/precision receipt differs')
    content = ids[:-1] if terminal else ids
    if any(i in (2, 4) for i in content) or tok.decode(content, skip_special_tokens=False) != event.get('answer'):
        raise ValueError('raw answer must equal pinned-tokenizer decoding of actual generated body IDs')


def evaluate(endpoint):
    value = prepared(assets=True); authority('evaluate'); cases = evaluation_cases(value)
    import_environment()
    key = 'evaluate_' + endpoint; directory = safe(str((RAW / key).relative_to(ROOT)), ROOT)
    if directory.exists(): raise FileExistsError('preserve old complete/partial actual answers')
    from scripts.p106b_shards import ShardWriter
    safe(str(directory.relative_to(ROOT)), ROOT)
    directory.mkdir(parents=True, exist_ok=False)
    safe(str(directory.relative_to(ROOT)), ROOT)
    writer = ShardWriter(directory, 'answers', limit=19_999_999)
    events = []
    with loaded(endpoint) as (torch, model, cfg, tok, route, fingerprint):
        before = fingerprint(model)
        try:
            with torch.no_grad():
                for index, case in enumerate(cases):
                    authority('evaluate'); route.assert_active()
                    question = case['question'] if case['lane'] == 'user' else case['row']['messages'][0]['content']
                    answer, generation = emit(torch, model, cfg, tok, question)
                    if any(generation[k] != case[k] for k in ('prompt_sha256', 'prompt_ids_sha256', 'prompt_tokens')):
                        raise ValueError('same actual question/prefix generation required')
                    score = None if case['lane'] == 'user' else data.score_response(case['row']['meta']['task'], answer, case['row']['meta']['language'])
                    event = dict(index=index, lane=case['lane'], case_sha256=data.sha(case), question=question,
                                 answer=answer, generation=generation, score=score)
                    writer.append(event); events.append(event)
                    if case['lane'] == 'user' or index < 4:
                        print('[ACTUAL_ANSWER] ' + json.dumps(dict(endpoint=endpoint, **event), ensure_ascii=False), flush=True)
                native = native32(model)
            after = fingerprint(model)
            if after != before: raise ValueError('evaluation mutated actual core')
            manifest = writer.close(lineage=dict(tag=TAG, endpoint=endpoint)); writer = None
            return dict(info=info(), status='EVALUATION_COMPLETE', endpoint=endpoint, cases_sha256=data.sha(cases),
                raw_manifest=manifest, core_before=before, core_after=after, weights_changed=False, checkpoint_writes=0,
                counts=dict(test=1024, train_observation=32, user=6, total=1062), native32=native,
                runtime_counts=dict(fingerprint.runtime_counts),
                summary=evaluation_summary(events, cases), user_semantic_truth='HUMAN_REVIEW_REQUIRED')
        finally:
            if writer is not None and events: writer.close(lineage=dict(tag=TAG, endpoint=endpoint, partial=True))


def read_evaluation(endpoint):
    report = closed('evaluate_' + endpoint); value = prepared(); cases = evaluation_cases(value)
    events = get_rows(RAW / ('evaluate_' + endpoint), 'answers', report['raw_manifest'])
    expected_core = PARENT_CORE if endpoint == 'parent' else read_training(endpoint)['final_core_sha256']
    if (len(events) != 1062 or report.get('cases_sha256') != data.sha(cases)
            or report.get('status') != 'EVALUATION_COMPLETE' or report.get('endpoint') != endpoint
            or report.get('counts') != dict(test=1024, train_observation=32, user=6, total=1062)
            or report.get('core_before') != expected_core or report.get('core_after') != expected_core
            or report.get('weights_changed') is not False or report.get('checkpoint_writes') != 0
            or report.get('runtime_counts') != dict(checkpoint_tensor_loads=1, model_constructions=1, cuda_transfers=1)
            or report.get('user_semantic_truth') != 'HUMAN_REVIEW_REQUIRED'):
        raise ValueError('full unchanged-body actual free-answer receipt required')
    tok = tokenizer()
    for index, (event, case) in enumerate(zip(events, cases)):
        if event.get('index') != index or event.get('case_sha256') != data.sha(case) or event.get('lane') != case['lane']:
            raise ValueError('same full case order required')
        score = None if case['lane'] == 'user' else data.score_response(case['row']['meta']['task'], event['answer'], case['row']['meta']['language'])
        if event['score'] != score or event['generation'].get('gold_trace_in_prompt') is not False:
            raise ValueError('actual answer/trace recount differs')
        question = case['question'] if case['lane'] == 'user' else case['row']['messages'][0]['content']
        if event.get('question') != question: raise ValueError('actual question text differs from original case')
        validate_generation(event, case, tok)
    if report.get('summary') != evaluation_summary(events, cases):
        raise ValueError('report summary differs from independent full raw/root/counterfactual recount')
    native = report.get('native32', {})
    if (native.get('targets') != 32768 or native.get('windows') != 32 or native.get('precision') != 'FP32_MATH'
            or native.get('val_sha256') != 'AD7EFB0DBD0D830A216B4D21A91C8ACB3FC41DAE2B23A3A55999AE8727AA374C'
            or type(native.get('ce')) not in (int, float) or not math.isfinite(native['ce']) or native['ce'] < 0):
        raise ValueError('full fixed native32 scalar contract required')
    return report


def readback():
    prepared(); trains = {arm: read_training(arm) for arm in ARMS}
    evaluations = {ep: read_evaluation(ep) for ep in ENDPOINTS}
    return dict(info=info(), status='RAW_RECOUNTED_NOT_QUALITY_ADOPTION',
        updates={arm: r['actual_updates'] for arm, r in trains.items()},
        summaries={ep: r['summary'] for ep, r in evaluations.items()}, models_loaded=0, checkpoint_tensor_loads=0)


@contextmanager
def termination_guard():
    previous = signal.getsignal(signal.SIGTERM)
    def stop(_number, _frame): raise KeyboardInterrupt('own worker SIGTERM')
    signal.signal(signal.SIGTERM, stop)
    try: yield
    finally: signal.signal(signal.SIGTERM, previous)


@contextmanager
def wall_limit(seconds):
    previous = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    def expired(_number, _frame): raise Pending('own actual wall cap reached; partial is not PASS')
    signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer); signal.signal(signal.SIGALRM, previous)


def admission(mode, key, cap, identity):
    remaining = authority(mode); spent = actual_spent(identity)
    family_remaining = 10800 - spent
    if cap > remaining or cap > family_remaining:
        raise Pending('declared whole cap does not fit actual UTC/family remainder; do not shrink it silently')
    # Before measurements, reserve full caps for all pending expensive stages.
    # Training additionally uses the measured all-pending forecast in train().
    pending = [('cost_' + a, 900, True) for a in ARMS] + [('train_' + a, 1800, True) for a in ARMS]
    pending += [('evaluate_' + ep, 1200, False) for ep in ENDPOINTS]
    future = [(k, c, t) for k, c, t in pending if k != key and not activity_path(k).exists()]
    if mode in ('prepare', 'cost', 'budget', 'evaluate', 'readback'):
        train_reserve = (cap if mode == 'cost' else 0) + sum(c for _, c, t in future if t)
        total_reserve = cap + sum(c for _, c, _ in future) + (0 if mode == 'readback' else 600)
        if (train_reserve and train_reserve > authority('train')
                or total_reserve > authority('readback') + 600 or total_reserve > family_remaining):
            raise Pending('all pending cost/train/evaluation caps and record reserve do not fit')
    return dict(requested_cap=cap, utc_remaining=remaining, family_remaining=family_remaining,
                actual_prior_worker_seconds=spent, scope='COOPERATIVE_UTC_AND_WALL_CAP_NOT_HARD_CUDA_KILL_GUARANTEE')


def actual_spent(identity):
    safe(str(EVIDENCE.relative_to(ROOT)), ROOT)
    spent = 0.
    for path in EVIDENCE.glob('activity_*.json') if EVIDENCE.exists() else ():
        item = required(str(path.relative_to(ROOT)))
        if item.get('info') != identity or type(item.get('seconds')) not in (int, float) or not math.isfinite(item['seconds']) or item['seconds'] < 0:
            raise ValueError('owned finite actual activity ledger required before every worker')
        key = path.name[len('activity_'):-len('.json')]
        if item.get('complete') is not True or item.get('returncode') != 0:
            raise Pending('prior incomplete/failed own stage is preserved; no new actual stage admission')
        closed(key)
        spent += item['seconds']
    return spent


def worker(args):
    key = phase_key(args.mode, args.arm, args.endpoint); identity = info()
    safe(str(EVIDENCE.relative_to(ROOT)), ROOT); safe(str((RAW / key).relative_to(ROOT)), ROOT)
    if activity_path(key).exists() or report_path(key).exists(): raise FileExistsError('completed/failed own stage preserved')
    began = datetime.now(timezone.utc); tick = time.perf_counter(); code = 9; error = None; admitted = None
    try:
        with termination_guard():
            if os.getpgrp() != os.getpid(): raise Pending('internal worker must own its new process group')
            admitted = admission(args.mode, key, args.max_wall_sec, identity)
            with wall_limit(args.max_wall_sec):
                result = (prepare() if args.mode == 'prepare' else train(args.arm, cost=args.mode == 'cost') if args.mode in ('cost', 'train') else
                          budget() if args.mode == 'budget' else evaluate(args.endpoint) if args.mode == 'evaluate' else readback())
                authority(args.mode)
                result['invocation'] = dict(mode=args.mode, arm=args.arm, endpoint=args.endpoint, max_wall_sec=args.max_wall_sec)
                write(report_path(key), result)
                if args.mode == 'budget' and not result['fits']: raise Pending('HOLD_BUDGET')
                authority(args.mode); code = 0
    except KeyboardInterrupt:
        code = 130; error = 'KeyboardInterrupt'
    except Pending as exc:
        code = 8; error = type(exc).__name__; print('[HOLD] ' + str(exc), flush=True)
    except Exception as exc:
        code = 9; error = type(exc).__name__; print('[ERROR] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
    finally:
        ended = datetime.now(timezone.utc)
        write(activity_path(key), dict(info=identity, key=key, mode=args.mode, arm=args.arm, endpoint=args.endpoint,
            complete=code == 0, returncode=code, error_type=error, started_at=began.isoformat(), ended_at=ended.isoformat(),
            seconds=time.perf_counter() - tick, utc_seconds=(ended - began).total_seconds(),
            worker_pid=os.getpid(), worker_pgid=os.getpgrp(), max_wall_sec=args.max_wall_sec,
            admission=admitted,
            result_sha256=digest(report_path(key)) if report_path(key).is_file() else None))
    return code


def readonly_remaining(now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None: raise ValueError('aware actual UTC required')
    remaining = (datetime.fromisoformat(LIMITS['authority_end']) - now).total_seconds()
    if remaining <= 0: raise Pending('17:00 KST readonly/reporting authority reached')
    return remaining


def verify_readonly(args):
    cap = min(600., args.max_wall_sec, readonly_remaining())
    with termination_guard(), wall_limit(cap):
        result = _verify_readonly(args)
        readonly_remaining()
        print('[READONLY_VERIFIED] ' + json.dumps(dict(mode=args.mode, status=result['status'], max_wall_sec=cap,
            model_loads=0, checkpoint_tensor_loads=0)), flush=True)
    return 0


def _verify_readonly(args):
    key = phase_key(args.mode, args.arm, args.endpoint)
    if args.mode in ('cost', 'train'): result = read_training(args.arm, cost=args.mode == 'cost')
    elif args.mode == 'evaluate': result = read_evaluation(args.endpoint)
    elif args.mode == 'prepare': prepared(); result = closed(key)
    elif args.mode == 'budget': result = read_budget()
    else:
        result = closed(key); actual = readback()
        if {k: v for k, v in result.items() if k != 'invocation'} != actual:
            raise ValueError('final readback differs from independent original full raw recount')
    return result


def launch(command, cap):
    proc = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, start_new_session=True)
    try: return proc.wait(timeout=cap + 30)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        os.killpg(proc.pid, signal.SIGTERM)
        try: proc.wait(timeout=30)
        except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL); proc.wait()
        return 130


def execute(args):
    import_environment()
    from scripts.p106b_stage_receipt import pipeline
    common = [sys.executable, '-B', '-X', 'utf8', SCRIPT, '--mode', args.mode, '--max-wall-sec', str(args.max_wall_sec)]
    if args.arm: common += ['--arm', args.arm]
    if args.endpoint: common += ['--endpoint', args.endpoint]
    execute_command = common + ['--execute', '--worker']
    phases = [('REGRESSION', [sys.executable, '-B', '-X', 'utf8', '-m', 'unittest', 'scripts.test_p106b_verified_trace_recovery']),
              ('PREFLIGHT', common + ['--check-only']), ('EXECUTE', execute_command)]
    def dispatch(command):
        code = launch(command, args.max_wall_sec)
        if code == 0 and command == execute_command:
            try: verify_cap = min(600., readonly_remaining())
            except Pending as exc:
                print('[HOLD] ' + str(exc), flush=True); return 8
            print('[READONLY_VERIFY_BEGIN] actual worker is closed; final phase remains pending; max_wall_sec=' + str(verify_cap), flush=True)
            code = launch(common + ['--verify-readonly'], verify_cap)
        return code
    receipt = pipeline(phases, dispatch, lambda s: print(s, flush=True), experiment=phase_key(args.mode, args.arm, args.endpoint))
    return receipt['returncode']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, required=True); parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--endpoint', choices=ENDPOINTS); parser.add_argument('--max-wall-sec', type=int)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check-only', action='store_true'); action.add_argument('--execute', action='store_true')
    action.add_argument('--verify-readonly', action='store_true'); parser.add_argument('--worker', action='store_true')
    args = parser.parse_args(argv); args.max_wall_sec = CAPS[args.mode] if args.max_wall_sec is None else args.max_wall_sec
    try:
        phase_key(args.mode, args.arm, args.endpoint)
        if args.worker and not args.execute: raise ValueError('internal worker only belongs to execute mode')
        if not 60 <= args.max_wall_sec <= CAPS[args.mode]: raise ValueError('declared worker cap required')
        if not IMPLEMENTATION_READY: raise Pending('implementation/CPU fixture review not complete; no actual stage admission')
        if args.check_only:
            contract = info()
            print('[STATIC_ONLY] ' + json.dumps(dict(mode=args.mode, source_files=len(contract['code_sha256']),
                model_loads=0, torch_imports=0, checkpoint_tensor_loads=0, hf_raw_access=0)), flush=True)
            return 0
        if args.verify_readonly: return verify_readonly(args)
        return worker(args) if args.worker else execute(args)
    except Pending as exc:
        print('[HOLD] ' + str(exc), flush=True); return 8
    except KeyboardInterrupt:
        print('[INTERRUPTED] own process received interruption; no PASS', flush=True); return 130
    except Exception as exc:
        print('[ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True); return 9


if __name__ == '__main__': raise SystemExit(main())
