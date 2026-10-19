#!/usr/bin/env python3
"""Write-once broad-course group-order comparison; no changes to old sources.

Prepare alone admits sources and freezes encoded consumers. Cost never saves a
checkpoint. Main training accepts only the pinned original P090B initializer.
Evaluate without an arm is its new public-VAL dialogue baseline; both trained
arms reuse the same bounded generation protocols. A receipt is not quality.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import nullcontext
from dataclasses import asdict
from datetime import datetime, timezone
import copy
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_broad_course as builder
from scripts import p106b_content_objective as objective
from scripts import p106b_night_course as grounded
from scripts import diag_p106b_question_transfer as monitor
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_stage_receipt import pipeline
from tinylm.train import mtp_sft as core
from tinylm.chat.canonical import normalize, validate
from tinylm.chat.serialize import serialize

TAG, SCHEMA = 'p106b_broad_curriculum_v1_s1337', 'P106B_BROAD_CURRICULUM_V1'
ARMS = builder.ARMS
MODES = ('source', 'prepare', 'preflight', 'cost', 'budget', 'train', 'evaluate', 'readback')
CACHE = ROOT / 'data_cache' / TAG
RAW = ROOT / 'runs/eval' / TAG
EVIDENCE = ROOT / 'test_result/evidence' / TAG
PUBLIC = ROOT / 'HF/sft_ready'
PUBLIC_MANIFEST = PUBLIC / 'p090_public_v3_manifest.json'
PUBLIC_TRAIN = PUBLIC / 'p090_public_v3_train.canonical.jsonl'
PUBLIC_VAL = PUBLIC / 'p090_public_v3_val.canonical.jsonl'
PUBLIC_MANIFEST_SHA = '2111D17E87BA1F0B50406B904D76D3CF7BA988AB8CFB01DCD94BFF158C434A04'
GROUNDED_SHA = 'E340BCE35E0B5FA6CC0EE2F08694E584A711231BC6443C5D599D55F95D5D122B'
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
TRAIN_STOP = datetime(2026, 10, 20, 5, tzinfo=timezone.utc)
UPDATES, ROWS, GROUPS, CONTEXT = 352, 22528, 176, 1024
ACTIVE_LIMIT, EVAL_RESERVE, RECORD_RESERVE = 10800, 1200, 600
OWN_CODE = ('scripts/p106b_broad_course.py', 'scripts/test_p106b_broad_course.py',
            'scripts/diag_p106b_broad_curriculum.py', 'scripts/test_p106b_broad_curriculum.py',
            'scripts/p106b_content_objective.py', 'scripts/test_p106b_content_objective.py')
CODE = tuple(sorted(set((*monitor.CODE, *grounded.CODE, *OWN_CODE))))
safe, digest, sha, Pending = monitor.safe, monitor.digest, builder.sha, monitor.Pending


def info():
    pins = {p: digest(safe(ROOT / p)) if (ROOT / p).is_file() else 'NOT_CREATED' for p in CODE}
    return dict(schema=SCHEMA, tag=TAG, code_sha256=pins, code_complete='NOT_CREATED' not in pins.values(),
        parent=str(monitor.base.PARENT.relative_to(ROOT)), parent_sha256=monitor.base.PARENT_SHA,
        expected_parent_core=monitor.base.PARENT_CORE, tokenizer_sha256=monitor.natural.TOK_SHA,
        arms=list(ARMS), epochs=2, updates=UPDATES, rows_per_pass=ROWS, groups_per_pass=GROUPS,
        micro_bs=8, accum=16, seq=CONTEXT, grad_checkpoint=True, compile='default',
        adam_lr=5e-5, muon_lr=2e-4, all_group_weight_decay=0., grad_clip=1.,
        objective='L0_TOKEN_MEAN_OVER_WHOLE_UPDATE', scheduler='constant', seed=1337,
        native_targets_per_update=8192, native_windows=2816, native_binding='ABSOLUTE_UPDATE',
        teacher_calls=0, mtp=False, automatic_adoption=False, formal_train_ready=False,
        general_intelligence='NOT_ESTABLISHED', total75m_complete=False,
        authority_end_utc=END.isoformat(), training_stop_utc=TRAIN_STOP.isoformat(),
        active_limit_seconds=ACTIVE_LIMIT, evaluation_reserve_seconds=EVAL_RESERVE,
        record_reserve_seconds=RECORD_RESERVE, monitor_max_new=64, dialogue_max_new=128,
        dialogue_history='ACTUAL_MODEL_ANSWERS_NOT_SOURCE_GOLD', source_admission='CPU_PREPARE_ONLY')


def authority(training=False, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None:
        raise ValueError('timezone-aware clock required')
    remaining = ((TRAIN_STOP if training else END) - now).total_seconds()
    if not math.isfinite(remaining) or remaining <= 0:
        raise Pending('explicit authority or reserved training deadline ended')
    return remaining


def write(path, value):
    path = safe(path)
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(payload) >= 20_000_000:
        raise ValueError('single report must be below20MB; use row shards')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(payload)


def required(path):
    path = safe(path)
    if not path.is_file():
        raise Pending('required owned artifact absent: ' + str(path.relative_to(ROOT)))
    return json.loads(path.read_text(encoding='utf-8'))


def checkpoint(arm):
    if arm not in ARMS:
        raise ValueError('registered broad-course training arm required')
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_broad_' + TAG + '_' + arm + '.pt')


def source_pins():
    """Code/file identity only; no selection, model, output or source regeneration."""
    if not info()['code_complete']:
        raise ValueError('all new implementation/test files required')
    fixed = ((PUBLIC_MANIFEST, PUBLIC_MANIFEST_SHA), (grounded.CORPUS / 'report.json', GROUNDED_SHA),
             (monitor.natural.TOKENIZER, monitor.natural.TOK_SHA),
             (monitor.base.PARENT, monitor.base.PARENT_SHA))
    for path, expected in fixed:
        if digest(safe(path)) != expected:
            raise ValueError('pinned source/tokenizer/original parent bytes changed: ' + str(path.relative_to(ROOT)))
    public = required(PUBLIC_MANIFEST)
    if public.get('schema') != 'TINYLM_PUBLIC_SFT_V1':
        raise ValueError('exact original public manifest required')
    pins = {str(path.relative_to(ROOT)): expected for path, expected in fixed}
    for split, path in (('train', PUBLIC_TRAIN), ('val', PUBLIC_VAL)):
        expected = public['output_sha256'][split]
        if digest(path) != expected:
            raise ValueError('exact public split bytes changed')
        pins[str(path.relative_to(ROOT))] = expected
    return pins


def _lines(path):
    return [json.loads(line) for line in safe(path).read_text(encoding='utf-8').splitlines()]


def dialogue_turns(row):
    """Original user/system additions and source gold, never a gold history."""
    row = validate(normalize(copy.deepcopy(row)))
    pending, turns = [], []
    for message in row['messages']:
        builder._text(message)
        if message['role'] == 'assistant':
            if not pending or pending[-1]['role'] != 'user':
                raise ValueError('complete original user/assistant sequence required')
            turns.append(dict(additions=pending, source_gold=builder._text(message)))
            pending = []
        else:
            pending.append(copy.deepcopy(message))
    if not turns or pending:
        raise ValueError('complete original conversation required')
    return turns[:3]


def select_dialogues(public_val, tok):
    selected, excluded = [], []
    for language in ('ko', 'en'):
        candidates = []
        for index, row in enumerate(public_val):
            if row.get('meta', {}).get('language') != language:
                continue
            try:
                turns = dialogue_turns(row)
                prompt = serialize(dict(messages=turns[0]['additions']), 'chatml', add_generation_prompt=True)
                if len(tok.encode(prompt).ids) + 128 > CONTEXT:
                    raise ValueError('initial complete prompt plus128 exceeds1024')
                first_user = next(iter(builder._identity(builder._canonical(row))['first_user']))
                identity = sha([TAG, 'NEW_PUBLIC_VAL_DIALOGUE', first_user, row['meta']])
                candidates.append(dict(id=identity, language=language, source_index=index,
                    first_user_sha256=first_user,
                    source_row_sha256=sha(row), source_meta=copy.deepcopy(row['meta']),
                    source_messages=copy.deepcopy(row['messages']), turns=turns,
                    source_split='PUBLIC_VAL', maximum_assistant_turns=3,
                    expected_source_turns=len(turns), quality='NOT_AUTOGRADED', max_new=128))
            except ValueError as exc:
                excluded.append(dict(source_index=index, language=language, technical_reason=str(exc)))
        candidates.sort(key=lambda value: value['id'])
        if len(candidates) < 8:
            raise builder.SourceUnavailable(dict(status='SOURCE_UNAVAILABLE', reason='public_val_dialogue_supply',
                language=language, available=len(candidates), required=8, exclusions=excluded))
        selected.extend(candidates[:8])
    return selected, dict(selected_ids_sha256=sha([v['id'] for v in selected]),
        source_indices=[v['source_index'] for v in selected], technical_exclusions=excluded,
        selection='first-question/source hash fixed before model answers',
        quality='human source/answer review required; lexical equality is not a quality PASS')


def monitor_display_ids(cases):
    ordinary = sorted((c for c in cases if c['lane'] != 'user_seen'),
                      key=lambda c: sha([TAG, 'DISPLAY8_BEFORE_MODEL', c['id']]))[:8]
    users = [c for c in cases if c['lane'] == 'user_seen']
    return [c['id'] for c in (*ordinary, *users)]


def show_monitor(case, event, endpoint, origin, note=print):
    value = dict(endpoint=endpoint, origin=origin, id=case['id'], language=case['language'],
        family=case['family'], question=case['messages'], answer=event['answer'],
        finish_reason=event['generation']['finish_reason'], metrics=event['metrics'])
    note('[BROAD_MONITOR_SAMPLE] ' + json.dumps(value, ensure_ascii=False))


def show_dialogue(event, case, endpoint, note=print):
    for index, turn in enumerate(event['turns']):
        actual_history = turn['actual_prompt_messages']
        value = dict(endpoint=endpoint, episode=case['id'], language=case['language'], turn=index + 1,
            source_user_additions=case['turns'][index]['additions'],
            prior_actual_assistant_answers=[builder._text(m) for m in actual_history if m['role'] == 'assistant'],
            answer=turn.get('answer'), status=turn['status'],
            finish_reason=turn.get('generation', {}).get('finish_reason', turn['status']),
            actual_history=True, semantic_correct=None)
        note('[BROAD_DIALOGUE] ' + json.dumps(value, ensure_ascii=False))


def overlap_audit(course, cases):
    index = builder._Index()
    for row in course.rows:
        # Source context grams are audited from original references in prepare.
        index.add(dict(messages={row['messages_sha256']}, first_user={row['first_user_sha256']},
            source_id=set(), concept=set(row['root_aliases']), split_root=set(row['root_aliases']), word24=set()),
            'train:' + row['id'])
    rows, counts = [], defaultdict(Counter)
    for case in cases:
        reference = next(builder._references([case]))
        collision = index.collisions(builder._identity(reference))
        value = dict(id=case['id'], language=case['language'], family=case['family'],
                     collision=collision, exact_or_root_overlap=bool(collision),
                     evaluation_scope='EXISTING_MONITOR_NOT_BLIND_GENERALIZATION')
        rows.append(value)
        counts[(case['language'], case['family'])].update(total=1, flagged=int(bool(collision)), clean=int(not collision))
    return dict(cases=rows, strata=[dict(language=k[0], family=k[1], **dict(v)) for k, v in sorted(counts.items())],
                scope='source/root/exact messages/first-user here; original word24 appended by prepare',
                all1694_unseen_claim=False)


def _wire(record, metadata):
    return dict(x=record.x, y=record.y, segments=record.segments, meta=metadata)


def _unwire(value):
    if not isinstance(value, dict) or set(value) != {'x', 'y', 'segments', 'meta'}:
        raise ValueError('exact encoded broad-course wire required')
    record = core.Record(value['x'], value['y'], value['segments'])
    counts = builder._record_counts(record)
    if (builder._record_sha(record) != value['meta']['record_sha256']
            or any(value['meta'].get(k) != v for k, v in counts.items())):
        raise ValueError('actual encoded target/owner/count/hash differs')
    return record, value['meta']


def _put(stem, values):
    writer = ShardWriter(CACHE / 'wire', stem, limit=19_999_999)
    for value in values:
        writer.append(value)
    return writer.close(lineage=dict(tag=TAG, stem=stem))


def _read(stem, manifest):
    if manifest.get('lineage') != dict(tag=TAG, stem=stem):
        raise ValueError('exact new source shard lineage required')
    return monitor.read_rows(CACHE / 'wire', manifest, stem, manifest['rows'])


def cost_group_ids(course):
    """Eight common cost groups cover all lanes and warmed long general heads."""
    ranked = {}
    for lane in ('grounded', 'replay', 'general'):
        groups = [i for i, group in enumerate(course.groups) if course.rows[group[0]]['lane'] == lane]
        ranked[lane] = sorted(groups, key=lambda i: (
            -max(course.rows[j]['assistant_targets'] for j in course.groups[i]),
            -sum(course.rows[j]['assistant_targets'] for j in course.groups[i]), i))
        if len(groups) < 3:
            raise ValueError('three full groups in each lane required for cost admission')
    return [ranked['grounded'][0], ranked['replay'][0], ranked['general'][0], ranked['general'][1],
            ranked['grounded'][1], ranked['replay'][1], ranked['general'][2], ranked['grounded'][2]]


def prepare():
    authority(training=True)
    for directory in (CACHE, RAW, EVIDENCE):
        if safe(directory).exists():
            raise FileExistsError('preserve previous complete/partial broad namespace')
    pins = source_pins()
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(monitor.natural.TOKENIZER))
    # Actual existing API: hashes/checks the closed source, never loads a model.
    old, rows = grounded.read_night_course()
    original, _, _ = monitor.read_prepared()
    cases = monitor.read_rows(monitor.CORPUS, original['manifests']['cases'], 'cases', 1694)
    public_train, public_val = _lines(PUBLIC_TRAIN), _lines(PUBLIC_VAL)
    if len(public_train) != 2996 or len(public_val) != 158:
        raise ValueError('complete original public TRAIN2996/VAL158 required')
    heldout = [*rows['dev'], *rows['test']]
    upstream = ROOT / old['upstream_course']['path']
    upstream_report_path = upstream / 'report.json'
    if digest(safe(upstream_report_path)) != old['upstream_course']['sha256']:
        raise ValueError('replay own held-out source report changed')
    upstream_report = required(upstream_report_path)
    replay_dev = []
    for key in ('dev_code', 'dev_fiction', 'dev_role', 'dev_evidence',
                'retention_fiction', 'test_role_style0', 'test_role_style2', 'test_evidence'):
        values = monitor.read_rows(upstream, upstream_report['manifests'][key], key,
                                   upstream_report['manifests'][key]['rows'])
        heldout.extend(values)
        if key.startswith('dev_'):
            replay_dev.extend(values)
    try:
        admission = builder.inspect_general(public_train, tok, public_val=public_val,
            heldout_rows=heldout, training_rows=[*rows['train'], *rows['replay']], monitor_rows=())
        if admission['status'] != 'ADMISSIBLE':
            raise builder.SourceUnavailable(admission)
        dialogues, dialogue_selection = select_dialogues(public_val, tok)
        course = builder.build_course(rows['train'], rows['replay'], public_train, tok,
            public_val=public_val, heldout_rows=heldout, monitor_rows=())
    except builder.SourceUnavailable as exc:
        write(EVIDENCE / 'source_admission.json', dict(info(), status='SOURCE_UNAVAILABLE',
            admission=exc.report, optimizer_updates=0, model_loaded=False, source_changed=False))
        raise
    dialogue_indices = {value['source_index'] for value in dialogues}
    dev = []
    for pair in rows['dev']:
        for view in (0, 1):
            row = pair['views'][str(view)]; rec = core.encode_record(row, tok)
            dev.append(_wire(rec, builder._metadata(row, rec, 'dev_natural', len(dev), variant=view)))
    for row in replay_dev:
        rec, _ = builder.fields.encode(row, tok)
        dev.append(_wire(rec, builder._metadata(row, rec, 'dev_replay', len(dev))))
    for index, row in enumerate(public_val):
        if index not in dialogue_indices:
            rec = core.encode_record(row, tok)
            dev.append(_wire(rec, builder._metadata(row, rec, 'dev_general', index)))
    # Soft annotation for old, repeatedly observed monitors; own splits stay hard.
    audit = overlap_audit(course, cases)
    train_index = builder._Index()
    for row in builder._references([*rows['train'], *rows['replay'],
                                   *[public_train[i] for i in admission['selected_source_indices']]]):
        identity = builder._identity(row)
        train_index.add(identity, 'original_train:' + next(iter(identity['messages'])))
    for result, case in zip(audit['cases'], cases):
        collision = train_index.collisions(builder._identity(next(builder._references([case]))))
        result['collision'] = collision; result['exact_or_root_overlap'] = bool(collision)
    counts = defaultdict(Counter)
    for value in audit['cases']:
        counts[(value['language'], value['family'])].update(total=1,
            flagged=int(value['exact_or_root_overlap']), clean=int(not value['exact_or_root_overlap']))
    audit['strata'] = [dict(language=k[0], family=k[1], **dict(v)) for k, v in sorted(counts.items())]
    audit['scope'] = 'source/root/exact messages/first-user/original word24; synthetic template grams excluded'
    offsets = original['native_train_offsets']
    if len(offsets) != 3072:
        raise ValueError('original frozen3072 native offsets required')
    CACHE.mkdir(parents=True, exist_ok=False); RAW.mkdir(parents=True, exist_ok=False)
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    manifests = dict(train=_put('train', (_wire(r, m) for r, m in zip(course.records, course.rows))),
        dev=_put('dev', dev), monitor=_put('monitor', cases), dialogues=_put('dialogues', dialogues))
    write(CACHE / 'course.json', course.report)
    result = dict(info(), status='BROAD_CPU_FROZEN', source_pins=pins, source_manifest_sha256=sha(old['manifests']),
        grounded_report_sha256=GROUNDED_SHA, monitor_report_sha256=digest(monitor.CORPUS / 'report.json'),
        replay_heldout_report_sha256=digest(upstream_report_path),
        manifests=manifests, course_report_sha256=digest(CACHE / 'course.json'),
        cost_group_ids=cost_group_ids(course), dialogue_selection=dialogue_selection,
        monitor_cases_sha256=sha(cases), dialogue_cases_sha256=sha(dialogues),
        monitor_display_ids=monitor_display_ids(cases),
        monitor_display_selection_sha256=sha(monitor_display_ids(cases)),
        monitor_overlap=audit, dev_rows=len(dev), dev_targets=sum(v['meta']['assistant_targets'] for v in dev),
        dev_public_val_rows=sum(v['meta']['lane'] == 'dev_general' for v in dev),
        dialogue_source_turns=sum(v['expected_source_turns'] for v in dialogues),
        heldout_dialogues_excluded_from_dev_tf=True, public_val_rows=158,
        native_access='INDEXED_TRAIN_ONLY', native_train_file=str((monitor.base.NATIVE / 'train.bin').relative_to(ROOT)),
        native_train_offsets=offsets[:2816], native_train_sha256=monitor.base.NATIVE_TRAIN_SHA,
        native_val_sha256=monitor.base.NATIVE_VAL_SHA, native_reuse='first2816 of old3072; this study compares order only',
        source_admission=admission, model_loaded=False, optimizer_updates=0, checkpoints_written=0)
    write(CACHE / 'frozen.json', result)
    write(EVIDENCE / 'cpu_contract.json', public_contract(result))
    prepared(completed=False)
    print('[BROAD_PREPARED] full sources/352 updates/DEV verified; model/GPU NOT_RUN', flush=True)
    return 0


def public_contract(frozen):
    return dict(info(), status='BROAD_CPU_FROZEN', frozen_sha256=digest(CACHE / 'frozen.json'),
        course_report_sha256=frozen['course_report_sha256'], source_admission=frozen['source_admission'],
        monitor_overlap=frozen['monitor_overlap'], dialogue_selection=frozen['dialogue_selection'],
        monitor_display_ids=frozen['monitor_display_ids'],
        monitor_display_selection_sha256=frozen['monitor_display_selection_sha256'],
        dev_rows=frozen['dev_rows'], dev_targets=frozen['dev_targets'], model_loaded=False)


def validate_public_contract(frozen, public):
    if sha(public) != sha(public_contract(frozen)):
        raise ValueError('exact public metadata/code/frozen source receipt differs')


def prepared(*, completed=True):
    frozen = required(CACHE / 'frozen.json')
    if frozen.get('status') != 'BROAD_CPU_FROZEN' or any(frozen.get(k) != v for k, v in info().items()):
        raise ValueError('same exact prepared code/recipe required')
    for path, expected in frozen['source_pins'].items():
        if digest(safe(ROOT / path)) != expected:
            raise ValueError('original source changed after prepare')
    if digest(CACHE / 'course.json') != frozen['course_report_sha256']:
        raise ValueError('course metadata changed')
    public = required(EVIDENCE / 'cpu_contract.json')
    validate_public_contract(frozen, public)
    train = _read('train', frozen['manifests']['train'])
    values = [_unwire(value) for value in train]
    report = required(CACHE / 'course.json')
    rows, records = [v[1] for v in values], [v[0] for v in values]
    if len(records) != ROWS or sha(rows) != report['rows_metadata_sha256']:
        raise ValueError('complete22528 actual rows required')
    groups = [list(range(i, i + 128)) for i in range(0, ROWS, 128)]
    course = builder.BroadCourse(records, rows, groups, report['schedules'], report)
    if report['geometry'] != dict(builder._Geometry().__dict__) or cost_group_ids(course) != frozen['cost_group_ids']:
        raise ValueError('fixed geometry/cost long-head consumers differ')
    for group_id, indices in enumerate(groups):
        observed = builder._aggregate([rows[i] for i in indices])
        if any(course.report['groups'][group_id].get(k) != v for k, v in observed.items()):
            raise ValueError('actual group counts/language/turn/source receipts differ')
    for arm in ARMS:
        totals = Counter()
        for epoch in range(2):
            if sorted(course.schedules[arm][epoch]) != list(range(GROUPS)):
                raise ValueError('same complete group permutation required')
            for slot in range(GROUPS):
                micros = builder.materialize_group(course, arm, epoch, slot)
                if len(micros) != 16 or any(len(m) != 8 for m in micros):
                    raise ValueError('actual sixteen micro8 groups required')
                for micro in micros:
                    for record in micro:
                        totals.update(x_tokens=record.x_tokens, assistant_targets=record.targets)
        if any(totals[k] != report['two_pass_totals'][k] for k in totals):
            raise ValueError('late pass exposure differs')
    dev_values = _read('dev', frozen['manifests']['dev'])
    dev = [_unwire(v)[0] for v in dev_values]
    if len(dev) != frozen['dev_rows'] or sum(r.targets for r in dev) != frozen['dev_targets']:
        raise ValueError('complete actual DEV consumer required')
    cases, dialogues = _read('monitor', frozen['manifests']['monitor']), _read('dialogues', frozen['manifests']['dialogues'])
    if (len(cases) != 1694 or sha(cases) != frozen['monitor_cases_sha256']
            or len(dialogues) != 16 or sha(dialogues) != frozen['dialogue_cases_sha256']):
        raise ValueError('complete fixed monitor/dialogue inputs required')
    if (monitor_display_ids(cases) != frozen['monitor_display_ids']
            or sha(frozen['monitor_display_ids']) != frozen['monitor_display_selection_sha256']):
        raise ValueError('pre-model monitor question/answer display selection changed')
    if completed:
        completed_activity('prepare')
    return dict(contract=frozen, course=course, dev=dev, monitor=cases, dialogues=dialogues)


def activity_key(mode, arm):
    return mode + ('_' + arm if arm else '_parent' if mode == 'evaluate' else '')


def completion_report_path(mode, arm):
    if mode == 'prepare' and arm is None:
        return CACHE / 'frozen.json'
    if mode in ('cost', 'train') and arm in ARMS:
        return EVIDENCE / (mode + '_' + arm) / 'report.json'
    if mode == 'evaluate' and (arm is None or arm in ARMS):
        return EVIDENCE / ('evaluate_' + (arm or 'parent')) / 'report.json'
    if mode == 'readback' and arm is None:
        return EVIDENCE / 'readback.json'
    raise ValueError('exact complete-report mode/selector required')


def completion_binding(mode, arm, *, required_report):
    path = safe(completion_report_path(mode, arm))
    if not path.is_file():
        if required_report:
            raise ValueError('successful worker must close its exact owned report')
        return dict(report_path=None, report_sha256=None)
    return dict(report_path=str(path.relative_to(ROOT)), report_sha256=digest(path))


def completed_activity(mode, arm=None):
    key = activity_key(mode, arm); value = required(EVIDENCE / ('activity_' + key + '.json'))
    if (value.get('schema') != SCHEMA or value.get('tag') != TAG or value.get('key') != key
            or value.get('mode') != mode or value.get('arm') != arm or value.get('complete') is not True
            or type(value.get('returncode')) is not int or value['returncode'] != 0
            or value.get('code_sha256') != info()['code_sha256']
            or type(value.get('seconds')) not in (int, float) or not math.isfinite(value['seconds']) or value['seconds'] < 0
            or type(value.get('max_wall_sec')) is not int or not 60 <= value['max_wall_sec'] <= 7200
            or value.get('scope') != 'actual worker wall including full input verification; regression/wrapper excluded'):
        raise Pending('complete successful same-code owned activity required')
    stamp = datetime.fromisoformat(value['recorded_at'])
    if stamp.tzinfo is None or any(value.get(k) != v for k, v in completion_binding(mode, arm, required_report=True).items()):
        raise ValueError('closed worker/current report SHA and aware completion time required')
    return value


def spent_seconds():
    total = 0.
    if EVIDENCE.exists():
        for path in EVIDENCE.glob('activity_*.json'):
            value = required(path)
            if (value.get('tag') != TAG or type(value.get('seconds')) not in (int, float)
                    or not math.isfinite(value['seconds']) or value['seconds'] < 0):
                raise ValueError('valid owned actual activity time required')
            total += value['seconds']
    return total


def expected_group(bundle, arm, update, cost=False):
    if arm not in ARMS or type(update) is not int or not 0 <= update < (8 if cost else UPDATES):
        raise ValueError('declared update required')
    course = bundle['course']
    epoch, slot = (0, None) if cost else divmod(update, GROUPS)
    group = bundle['contract']['cost_group_ids'][update] if cost else course.schedules[arm][epoch][slot]
    if cost:
        slot = course.schedules[arm][0].index(group)
    return epoch, slot, group, course.report['groups'][group]['totals']


def read_training(arm, *, cost, bundle=None):
    if arm not in ARMS or type(cost) is not bool:
        raise ValueError('registered arm/cost identity required')
    bundle = prepared() if bundle is None else bundle
    directory = EVIDENCE / (('cost_' if cost else 'train_') + arm)
    report = required(directory / 'report.json'); count = 8 if cost else UPDATES
    if (report.get('status') != ('COST8_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING')
            or any(report.get(k) != v for k, v in info().items()) or report.get('arm') != arm
            or report.get('actual_updates') != count or report.get('initial_core_sha256') != monitor.base.PARENT_CORE
            or report.get('frozen_sha256') != digest(CACHE / 'frozen.json')
            or report.get('checkpoint_written') is not (not cost)):
        raise ValueError('complete exact same-source/initializer training report required')
    manifest = report['event_manifest']
    if manifest.get('lineage') != dict(tag=TAG, arm=arm, cost=cost):
        raise ValueError('raw training lineage differs')
    events = monitor.read_rows(directory, manifest, 'updates', count)
    if (not isinstance(report.get('final_core_sha256'), str)
            or len(report['final_core_sha256']) != 64
            or any(c not in '0123456789ABCDEF' for c in report['final_core_sha256'])):
        raise ValueError('actual final body fingerprint required')
    for index, event in enumerate(events):
        epoch, slot, group, expected = expected_group(bundle, arm, index, cost)
        if (event.get('update') != index + 1 or event.get('epoch') != epoch + 1
                or event.get('group') != group or event.get('native_indices') != list(builder.native_indices(index))
                or event.get('native_targets') != 8192 or event.get('positive_rows') != 128
                or any(event.get(k) != expected[k] for k in
                       ('x_tokens', 'assistant_targets', 'content_targets', 'eot_targets'))
                or any(type(event.get(k)) not in (float, int) or not math.isfinite(event[k]) for k in
                       ('assistant_ce', 'content_ce', 'eot_ce', 'native_ce', 'gradient_norm', 'step_seconds'))
                or event['step_seconds'] <= 0 or event.get('clipped') is not (event['gradient_norm'] > 1)):
            raise ValueError('actual group/absolute-native/whole-update losses/counts differ')
    if (report['step_seconds'] != [e['step_seconds'] for e in events]
            or report['grad_max'] != max(e['gradient_norm'] for e in events)
            or report['clip_events'] != sum(e['gradient_norm'] > 1 for e in events)
            or any(report['totals'].get(k) != sum(e[k] for e in events) for k in
                   ('positive_rows', 'x_tokens', 'assistant_targets', 'content_targets', 'eot_targets', 'native_targets'))):
        raise ValueError('complete raw sums/timing/gradient exposure differ')
    monitor.original.validate_groups(report['actual_optimizer_groups'])
    if not cost and (report.get('checkpoint') != str(checkpoint(arm).relative_to(ROOT))
                     or digest(checkpoint(arm)) != report.get('checkpoint_sha256')):
        raise ValueError('actual new checkpoint lineage differs')
    return report


def budget():
    bundle = prepared(); estimates = {}
    for arm in ARMS:
        completed_activity('cost', arm); report = read_training(arm, cost=True, bundle=bundle)
        times = report['step_seconds']
        prediction = times[0] + max(times[1:]) * (UPDATES - 1) * 1.35 + 300
        if (EVIDENCE / ('train_' + arm) / 'report.json').exists():
            completed_activity('train', arm); read_training(arm, cost=False, bundle=bundle); prediction = 0.
        estimates[arm] = prediction
    whole = spent_seconds() + sum(estimates.values()) + EVAL_RESERVE + RECORD_RESERVE
    if whole > ACTIVE_LIMIT or sum(estimates.values()) > authority(training=True):
        raise Pending('measured cost plus evaluation/record reserves does not fit3h/current authority')
    return dict(admission=True, estimated_training_seconds=estimates, total_reserved_seconds=whole,
                active_limit_seconds=ACTIVE_LIMIT, prediction_not_actual_training=True,
                scope='includes worst warmed long-general cost; no speed or quality adoption')


def dev_probe(model, records, device='cuda'):
    import torch
    totals = Counter(); targets = 0
    model.eval(); model.freeze_quant()
    try:
        with torch.no_grad():
            for start in range(0, len(records), 8):
                batch = records[start:start + 8]
                x, y, owners = core.pad_records(batch, 0, device, fixed_width=CONTEXT, batch_size=8)
                plan = objective.make_weights(batch, policy='token')
                weights = objective.make_tensor(plan, range(len(batch)), width=CONTEXT, device=device)
                if len(batch) < 8:
                    weights = torch.cat((weights, torch.zeros(8 - len(batch), CONTEXT, device=device)), dim=0)
                with torch.autocast('cuda', dtype=torch.bfloat16) if device == 'cuda' else nullcontext():
                    values, counts = objective.components(model, model(x, return_hidden=True), y, owners, weights)
                for key in ('raw', 'content', 'eot'):
                    totals[key] += float(values[key])
                totals.update(content_targets=counts['content'], eot_targets=counts['eot'])
                targets += counts['targets']
    finally:
        model.clear_quant(); model.train()
    if targets != sum(r.targets for r in records) or not all(math.isfinite(v) for v in totals.values()):
        raise ValueError('complete finite unweighted DEV consumer required')
    return dict(ce=totals['raw'] / targets, targets=targets, rows=len(records),
        content_ce=totals['content'] / totals['content_targets'] if totals['content_targets'] else 0.,
        eot_ce=totals['eot'] / totals['eot_targets'] if totals['eot_targets'] else 0.,
        content_targets=totals['content_targets'], eot_targets=totals['eot_targets'],
        scope='unweighted heldout TF; excludes16 dialogue evaluation source conversations')


def train_updates(model, cfg, tok, frozen, arm, output, *, cost=False, forward=None,
                  native_windows, optimizers=None, device='cuda', probe=None):
    """Reusable given-model update core; no initializer loading or checkpoint save.

    The main route verifies the original E854 parent before calling this core.
    A future explicitly authorized initializer route must supply its own receipt;
    no arbitrary checkpoint loader is exposed here. CPU fixtures use mock heads.
    """
    import torch
    if arm not in ARMS or cfg.grad_checkpoint is not True or cfg.mtp_aux or cfg.max_seq_len != CONTEXT:
        raise ValueError('same micro/geometry/ckptON/MTPoff update core required')
    if len(native_windows) != 2816:
        raise ValueError('same2816 absolute native windows required')
    forward = model if forward is None else forward
    adam, muon, groups = monitor.base.make_optimizers(model) if optimizers is None else optimizers
    monitor.original.validate_groups(groups)
    count = 8 if cost else UPDATES
    writer = ShardWriter(output, 'updates', limit=19_999_999)
    totals, times, history = Counter(), [], []
    gmax = 0.; clips = 0; began = time.perf_counter()
    for update in range(count):
        authority(training=True); tick = time.perf_counter()
        epoch, slot, group, expected = expected_group(frozen, arm, update, cost)
        micros = builder.materialize_group(frozen['course'], arm, epoch, slot)
        records = [record for micro in micros for record in micro]
        if len(records) != 128 or any(len(micro) != 8 for micro in micros):
            raise ValueError('whole128/16micro consumer required')
        plan = objective.make_weights(records, policy='token')
        if (plan.targets != expected['assistant_targets']
                or plan.content_targets != expected['content_targets'] or plan.eot_targets != expected['eot_targets']
                or sum(r.x_tokens for r in records) != expected['x_tokens']):
            raise ValueError('whole-update token denominator changed')
        adam.zero_grad(set_to_none=True); muon.zero_grad(set_to_none=True)
        sums = Counter(); observed = 0
        for offset, batch in enumerate(micros):
            x, y, owners = core.pad_records(batch, 0, device, fixed_width=CONTEXT, batch_size=8)
            weights = objective.make_tensor(plan, range(offset * 8, (offset + 1) * 8), width=CONTEXT, device=device)
            with torch.autocast('cuda', dtype=torch.bfloat16) if device == 'cuda' else nullcontext():
                values, counts = objective.components(model, forward(x, return_hidden=True), y, owners, weights)
            if not bool(torch.isfinite(values['weighted'])):
                raise ValueError('nonfinite whole-update assistant objective')
            values['weighted'].backward(); observed += counts['targets']
            for key in ('raw', 'content', 'eot'):
                sums[key] += float(values[key].detach())
        if observed != plan.targets:
            raise ValueError('actual micro/whole-update target mismatch')
        windows = [native_windows[i] for i in builder.native_indices(update)]
        native = [core.Record(v[:-1].astype('int64').tolist(), v[1:].astype('int64').tolist(), [1] * CONTEXT) for v in windows]
        nx, ny, ns = core.pad_records(native, 0, device, fixed_width=CONTEXT, batch_size=8)
        with torch.autocast('cuda', dtype=torch.bfloat16) if device == 'cuda' else nullcontext():
            values, counts = core.components(model, forward(nx, return_hidden=True), ny, ns, horizons=())
            native_loss = values[1] / 8192
        if counts[1] != 8192 or not bool(torch.isfinite(native_loss)):
            raise ValueError('unchanged separate native8192 denominator required')
        native_loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
        if not bool(torch.isfinite(norm)):
            raise ValueError('nonfinite gradient')
        adam.step(); muon.step()
        if device == 'cuda':
            torch.cuda.synchronize()
        times.append(time.perf_counter() - tick); gmax = max(gmax, float(norm)); clips += int(norm > 1.)
        event = dict(update=update + 1, epoch=epoch + 1, group=group, lane=frozen['course'].rows[frozen['course'].groups[group][0]]['lane'],
            positive_rows=128, x_tokens=sum(r.x_tokens for r in records), assistant_targets=plan.targets,
            content_targets=plan.content_targets, eot_targets=plan.eot_targets, native_targets=8192,
            native_indices=list(builder.native_indices(update)), assistant_ce=sums['raw'] / plan.targets,
            content_ce=sums['content'] / plan.content_targets if plan.content_targets else 0.,
            eot_ce=sums['eot'] / plan.eot_targets if plan.eot_targets else 0., native_ce=float(native_loss.detach()),
            gradient_norm=float(norm), clipped=bool(norm > 1.), step_seconds=times[-1])
        writer.append(event)
        totals.update({k: event[k] for k in ('positive_rows', 'x_tokens', 'assistant_targets', 'content_targets', 'eot_targets', 'native_targets')})
        if update < 8 or (update + 1) % 32 == 0:
            print('[BROAD_UPDATE] ' + json.dumps(dict(arm=arm, **event)), flush=True)
        if not cost and (update + 1) % GROUPS == 0 and probe is not None:
            history.append(dict(epoch=epoch + 1, updates=update + 1, **probe()))
    manifest = writer.close(lineage=dict(tag=TAG, arm=arm, cost=cost))
    return dict(actual_updates=count, totals=dict(totals), step_seconds=times, grad_max=gmax,
                clip_events=clips, history=history, actual_optimizer_groups=groups,
                event_manifest=manifest, update_core_seconds=time.perf_counter() - began)


def train(arm, *, cost):
    import torch
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    from scripts.p106b_native_windows import reader
    from scripts.p106b_gate_runtime import idle_before_gpu
    bundle = prepared(); authority(training=True)
    target = safe(EVIDENCE / (('cost_' if cost else 'train_') + arm))
    if target.exists() or (not cost and checkpoint(arm).exists()):
        raise FileExistsError('preserve previous complete/partial training')
    reservation = None if cost else budget()
    if not cost:
        completed_activity('evaluate', None)  # New public-VAL parent answers first.
        from tokenizers import Tokenizer
        _read_eval('parent', bundle, Tokenizer.from_file(str(monitor.natural.TOKENIZER)))
    for name, expected in (('train.bin', monitor.base.NATIVE_TRAIN_SHA), ('val.bin', monitor.base.NATIVE_VAL_SHA)):
        if digest(monitor.base.NATIVE / name) != expected:
            raise ValueError('native bytes changed')
    windows = reader(ROOT, bundle['contract'])
    if len(windows) != 2816:
        raise ValueError('complete same2816 native windows required before model admission')
    idle_before_gpu(); authority(training=True)
    target.mkdir(parents=True, exist_ok=False); began = time.perf_counter()
    _, model, cfg, tok, initial = monitor.base.load_parent()
    if initial != monitor.base.PARENT_CORE:
        raise ValueError('main route accepts only exact original P090B core')
    model = model.cuda(); torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    torch.cuda.reset_peak_memory_stats()
    optimizers = monitor.base.make_optimizers(model)
    monitor.original.validate_groups(optimizers[2])
    if not cost and optimizers[2] != read_training(arm, cost=True, bundle=bundle)['actual_optimizer_groups']:
        raise ValueError('actual cost/train optimizer groups changed before first update')
    probe = lambda: dict(dev=dev_probe(model, bundle['dev']), native=monitor.base.native_probe(model))
    before = None if cost else probe()
    os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(prefix='p106b_broad_')
    forward = torch.compile(model, mode='default')
    result = train_updates(model, cfg, tok, bundle, arm, target, cost=cost, forward=forward,
                          native_windows=windows, probe=probe, optimizers=optimizers)
    result.update(info(), status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING', arm=arm,
        initial_core_sha256=initial, final_core_sha256=state_fingerprint(model), frozen_sha256=digest(CACHE / 'frozen.json'),
        checkpoint_written=not cost, optimizer_saved=False, fresh_optimizer=True, before=before, reservation=reservation,
        peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
        peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20, peak_scope='torch allocator only')
    if not cost:
        with safe(checkpoint(arm)).open('xb') as stream:
            torch.save(dict(model=model.state_dict(), cfg=asdict(cfg), step=UPDATES,
                tokenizer_sha256=monitor.natural.TOK_SHA, optimizer_saved=False,
                broad_curriculum=dict(tag=TAG, arm=arm, passes=2, objective='token')), stream)
        result.update(checkpoint=str(checkpoint(arm).relative_to(ROOT)), checkpoint_sha256=digest(checkpoint(arm)))
    result['whole_seconds'] = time.perf_counter() - began
    write(target / 'report.json', result); read_training(arm, cost=cost, bundle=bundle)
    del model; gc.collect(); torch.cuda.empty_cache()
    return 0


def emit_dialogue(model, cfg, tok, messages):
    from tinylm.infer.generate import sample
    from scripts.diag_p101a_mtp_parity import CaptureTokens, PrecisionForward
    prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
    prefix = tok.encode(prompt).ids
    if len(prefix) + 128 > cfg.max_seq_len:
        raise ValueError('actual complete history plus128 exceeds context')
    capture = CaptureTokens(tok)
    _, meta = sample(PrecisionForward(model, 'fp32_math'), cfg, capture, prompt, max_new=128,
        temperature=0., top_k=1, device='cuda', use_cache=True, logits_last_only=True,
        return_metadata=True, stop_token_sequences=[[4]])
    ids = capture.decoded_ids
    if ids[:len(prefix)] != prefix or len(ids) - len(prefix) != meta['generated_tokens']:
        raise ValueError('actual dialogue prefix/generated ID receipt differs')
    generated = ids[len(prefix):]; reason = meta['finish_reason']
    terminal = [4] if reason == 'STOP_SEQUENCE' else [2] if reason == 'EOS' else []
    if (reason not in ('STOP_SEQUENCE', 'EOS', 'MAX_NEW')
            or terminal and generated[-1:] != terminal or not terminal and len(generated) != 128
            or reason == 'STOP_SEQUENCE' and meta.get('matched_stop_sequence') != [4]
            or reason != 'STOP_SEQUENCE' and meta.get('matched_stop_sequence') is not None):
        raise ValueError('actual128 authenticated terminal required')
    content = generated[:-1] if terminal else generated
    if any(v in (2, 4) for v in content):
        raise ValueError('a terminal token cannot remain inside dialogue content')
    answer = tok.decode(content, skip_special_tokens=False)
    meta.update(max_new=128, precision='FP32_MATH', use_cache=True, temperature=0., top_k=1, mtp=False,
        candidate_answers_supplied=False, prompt_tokens=len(prefix), prompt_sha256=sha(prompt),
        prompt_ids_sha256=sha(prefix), generated_ids=generated, generated_ids_sha256=sha(generated),
        content_ids_sha256=sha(content), terminal_ids=terminal,
        body_utf8_sha256=hashlib.sha256(answer.encode()).hexdigest().upper(), terminal_only_removed=True)
    return answer, meta


def run_dialogue(case, emit, tok):
    """Pure orchestration: only previously generated answers enter later prompts."""
    history, turns = [], []
    for index, source_turn in enumerate(case['turns']):
        authority()
        prompt_messages = history + copy.deepcopy(source_turn['additions'])
        prompt = serialize(dict(messages=prompt_messages), 'chatml', add_generation_prompt=True)
        if len(tok.encode(prompt).ids) + 128 > CONTEXT:
            turns.append(dict(turn=index + 1, status='NOT_RUN_CONTEXT_BUDGET',
                actual_prompt_messages=prompt_messages, source_gold=source_turn['source_gold']))
            break
        answer, generation = emit(prompt_messages)
        turns.append(dict(turn=index + 1, status='ACTUAL_MODEL_ANSWER', actual_prompt_messages=prompt_messages,
            actual_prompt_messages_sha256=sha(prompt_messages), answer=answer, generation=generation,
            source_gold=source_turn['source_gold'], source_gold_used_in_prompt=False, semantic_correct=None))
        history = prompt_messages + [dict(role='assistant', content=[dict(type='text', text=answer)])]
    return dict(id=case['id'], case_sha256=sha(case), language=case['language'], source_meta=case['source_meta'],
        source_messages=case['source_messages'], turns=turns, actual_history=True,
        source_gold_history_used=False, quality='HUMAN_REVIEW_REQUIRED_NO_AUTOMATIC_PASS')


def reused_parent_monitor(bundle, tok):
    report = monitor.required(monitor.EVIDENCE / 'evaluate_parent/report.json')
    lineage = report.get('lineage', {})
    if (report.get('status') != 'ACTUAL_FIRST_ANSWERS_RECORDED'
            or report.get('core_before') != monitor.base.PARENT_CORE or report.get('core_after') != monitor.base.PARENT_CORE
            or report.get('cases_sha256') != sha(bundle['monitor'])
            or lineage.get('checkpoint_sha256') != monitor.base.PARENT_SHA
            or lineage.get('checkpoint') != str(monitor.base.PARENT.relative_to(ROOT))):
        raise ValueError('exact old1694 parent provenance required for explicit reuse')
    directory = monitor.LOCAL / 'evaluate_parent'
    if digest(directory / 'answers_shards_manifest.json') != report['answer_manifest_sha256']:
        raise ValueError('reused parent manifest changed')
    events = monitor.read_rows(directory, report['answer_manifest'], 'answers', 1694)
    if any(event.get('lineage') != dict(tag=monitor.TAG, **lineage) for event in events):
        raise ValueError('old parent actual-answer lineage differs')
    summary = monitor.recount(events, bundle['monitor'], tokenizer=tok)
    if summary != report['summary']:
        raise ValueError('old parent actual answer recount differs')
    return events, dict(origin='REUSED_EXACT_OLD_PARENT_MONITOR_NOT_NEW_MODEL_CALLS',
        report=str((monitor.EVIDENCE / 'evaluate_parent/report.json').relative_to(ROOT)),
        report_sha256=digest(monitor.EVIDENCE / 'evaluate_parent/report.json'), summary=summary)


def evaluate(arm=None):
    import torch
    from tinylm.infer.generate import _strip
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    from scripts.p106b_gate_runtime import idle_before_gpu
    if arm is not None and arm not in ARMS:
        raise ValueError('parent or exact trained arm required')
    bundle = prepared(); label = arm or 'parent'
    trained = None
    if arm:
        completed_activity('train', arm); trained = read_training(arm, cost=False, bundle=bundle)
    target, raw = safe(EVIDENCE / ('evaluate_' + label)), safe(RAW / ('evaluate_' + label))
    if target.exists() or raw.exists():
        raise FileExistsError('preserve old actual monitor/dialogue answers')
    idle_before_gpu(); authority()
    _, model, cfg, tok, initial = monitor.base.load_parent()
    if initial != monitor.base.PARENT_CORE:
        raise ValueError('exact original parent loader required')
    if arm:
        saved = torch.load(checkpoint(arm), map_location='cpu', weights_only=True)
        if (saved.get('broad_curriculum') != dict(tag=TAG, arm=arm, passes=2, objective='token')
                or saved.get('cfg') != asdict(cfg) or saved.get('step') != UPDATES
                or saved.get('tokenizer_sha256') != monitor.natural.TOK_SHA):
            raise ValueError('exact child cfg/recipe/tokenizer required')
        model.load_state_dict(_strip(saved['model']), strict=True); del saved
    before = state_fingerprint(model)
    expected = trained['final_core_sha256'] if arm else monitor.base.PARENT_CORE
    if before != expected:
        raise ValueError('actual evaluation body differs')
    model = model.cuda(); model.eval(); model.freeze_quant()
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    torch.cuda.reset_peak_memory_stats()
    target.mkdir(parents=True, exist_ok=False); raw.mkdir(parents=True, exist_ok=False)
    lineage = dict(tag=TAG, endpoint=label, checkpoint=str((checkpoint(arm) if arm else monitor.base.PARENT).relative_to(ROOT)),
        checkpoint_sha256=trained['checkpoint_sha256'] if arm else monitor.base.PARENT_SHA, expected_core_sha256=before)
    began = time.perf_counter()
    with torch.no_grad():
        if arm:
            writer = ShardWriter(raw, 'monitor_answers', limit=19_999_999); events = []
            for index, case in enumerate(bundle['monitor']):
                authority()
                if monitor.case_encoding(case, tok) != case['encoding']:
                    raise ValueError('same complete monitor prompt/encoding required')
                answer, generation = monitor.emit64(model, cfg, tok, case['messages'])
                event = dict(id=case['id'], case_sha256=sha(case), answer=answer, generation=generation,
                             metrics=monitor.classify_case(case, answer), lineage=lineage)
                writer.append(event); events.append(event)
                if case['id'] in bundle['contract']['monitor_display_ids']:
                    show_monitor(case, event, label, 'NEW_ACTUAL_MONITOR',
                                 lambda line: print(line, flush=True))
                if (index + 1) % 256 == 0:
                    print('[BROAD_MONITOR] ' + label + ' ' + str(index + 1) + '/1694', flush=True)
            manifest = writer.close(lineage=lineage)
            monitor_result = dict(origin='NEW_ACTUAL_FIRST_ANSWERS', summary=monitor.recount(events, bundle['monitor'], tokenizer=tok),
                manifest=manifest, manifest_sha256=digest(raw / 'monitor_answers_shards_manifest.json'))
        else:
            events, monitor_result = reused_parent_monitor(bundle, tok)
            for case, event in zip(bundle['monitor'], events):
                if case['id'] in bundle['contract']['monitor_display_ids']:
                    show_monitor(case, event, label, 'REUSED_EXACT_OLD_PARENT_MONITOR',
                                 lambda line: print(line, flush=True))
        writer = ShardWriter(raw, 'dialogue_answers', limit=19_999_999); dialogues = []
        for case in bundle['dialogues']:
            result = run_dialogue(case, lambda messages: emit_dialogue(model, cfg, tok, messages), tok)
            result['lineage'] = lineage; writer.append(result); dialogues.append(result)
            show_dialogue(result, case, label, lambda line: print(line, flush=True))
        dialogue_manifest = writer.close(lineage=lineage)
    model.clear_quant(); after = state_fingerprint(model)
    if before != after:
        raise ValueError('evaluation changed actual body')
    native = monitor.base.native_probe(model)
    report = dict(info(), status='ACTUAL_MONITOR_AND_DIALOGUES_RECORDED', endpoint=label, lineage=lineage,
        core_before=before, core_after=after, monitor=monitor_result, dialogue_manifest=dialogue_manifest,
        dialogue_manifest_sha256=digest(raw / 'dialogue_answers_shards_manifest.json'),
        monitor_cases_sha256=bundle['contract']['monitor_cases_sha256'], dialogue_cases_sha256=bundle['contract']['dialogue_cases_sha256'],
        dialogue_summary=dialogue_summary(dialogues), native32_fp32=native,
        whole_seconds=time.perf_counter() - began, peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
        weights_changed=False, checkpoints_written=0, quality='NOT_ESTABLISHED_HUMAN_REVIEW_REQUIRED')
    write(target / 'report.json', report)
    del model; gc.collect(); torch.cuda.empty_cache()
    return 0


def dialogue_summary(events):
    cells = defaultdict(Counter)
    for event in events:
        cell = cells[event['language']]; cell['episodes'] += 1
        for turn in event['turns']:
            cell['actual_answers' if turn['status'] == 'ACTUAL_MODEL_ANSWER' else 'not_run_context'] += 1
            if turn['status'] == 'ACTUAL_MODEL_ANSWER':
                cell['empty'] += int(turn['answer'] == '')
                cell['max_new'] += int(turn['generation']['finish_reason'] == 'MAX_NEW')
    return dict(languages=dict(cells), scope='actual-history bookkeeping; no automatic semantic score', semantic_pass=None)


def validate_dialogues(events, cases, tok, lineage):
    if len(events) != 16 or len(cases) != 16:
        raise ValueError('complete16 original public-VAL episodes required')
    for event, case in zip(events, cases):
        if (event.get('id') != case['id'] or event.get('case_sha256') != sha(case)
                or event.get('lineage') != lineage or event.get('actual_history') is not True
                or event.get('language') != case['language'] or event.get('source_meta') != case['source_meta']
                or event.get('source_gold_history_used') is not False or event.get('source_messages') != case['source_messages']
                or not 1 <= len(event['turns']) <= len(case['turns'])):
            raise ValueError('exact actual/source dialogue provenance required')
        history = []
        for index, turn in enumerate(event['turns']):
            expected = history + case['turns'][index]['additions']
            if turn.get('actual_prompt_messages') != expected or turn.get('source_gold') != case['turns'][index]['source_gold']:
                raise ValueError('dialogue used a source-gold or different earlier history')
            prompt = serialize(dict(messages=expected), 'chatml', add_generation_prompt=True)
            if turn['status'] == 'NOT_RUN_CONTEXT_BUDGET':
                if len(tok.encode(prompt).ids) + 128 <= CONTEXT or index != len(event['turns']) - 1:
                    raise ValueError('only actual context shortage may skip remaining source turns')
                break
            generation, answer = turn['generation'], turn['answer']
            ids = generation['generated_ids']; terminal = generation['terminal_ids']
            reason = generation.get('finish_reason')
            if (not isinstance(ids, list) or any(type(v) is not int or not 0 <= v < 32768 for v in ids)
                    or type(terminal) is not list or reason not in ('STOP_SEQUENCE', 'EOS', 'MAX_NEW')
                    or reason == 'STOP_SEQUENCE' and (terminal != [4] or generation.get('matched_stop_sequence') != [4])
                    or reason == 'EOS' and (terminal != [2] or generation.get('matched_stop_sequence') is not None)
                    or reason == 'MAX_NEW' and (terminal or len(ids) != 128 or generation.get('matched_stop_sequence') is not None)
                    or terminal and ids[-len(terminal):] != terminal):
                raise ValueError('authenticated dialogue terminal/real token IDs required')
            content = ids[:-len(terminal)] if terminal else ids
            if (turn.get('source_gold_used_in_prompt') is not False or turn.get('semantic_correct') is not None
                    or generation.get('max_new') != 128 or generation.get('precision') != 'FP32_MATH'
                    or generation.get('temperature') != 0. or generation.get('top_k') != 1
                    or generation.get('use_cache') is not True or generation.get('mtp') is not False
                    or generation.get('candidate_answers_supplied') is not False
                    or generation.get('stop_token_sequences') != [[4]]
                    or generation.get('prompt_sha256') != sha(prompt)
                    or generation.get('prompt_ids_sha256') != sha(tok.encode(prompt).ids)
                    or generation.get('generated_ids_sha256') != sha(ids)
                    or not 1 <= len(ids) <= 128 or generation.get('generated_tokens') != len(ids)
                    or tok.decode(content, skip_special_tokens=False) != answer
                    or generation.get('content_ids_sha256') != sha(content)
                    or any(v in (2, 4) for v in content)
                    or generation.get('body_utf8_sha256') != hashlib.sha256(answer.encode()).hexdigest().upper()):
                raise ValueError('authenticated actual128 dialogue answer required')
            history = expected + [dict(role='assistant', content=[dict(type='text', text=answer)])]
        if (len(event['turns']) != len(case['turns'])
                and event['turns'][-1]['status'] != 'NOT_RUN_CONTEXT_BUDGET'):
            raise ValueError('unreported dialogue turns cannot be credited')


def _read_eval(label, bundle, tok):
    arm = None if label == 'parent' else label
    completed_activity('evaluate', arm)
    trained = None if arm is None else read_training(arm, cost=False, bundle=bundle)
    report = required(EVIDENCE / ('evaluate_' + label) / 'report.json')
    expected_core = monitor.base.PARENT_CORE if arm is None else trained['final_core_sha256']
    lineage = dict(tag=TAG, endpoint=label, checkpoint=str((monitor.base.PARENT if arm is None else checkpoint(arm)).relative_to(ROOT)),
        checkpoint_sha256=monitor.base.PARENT_SHA if arm is None else trained['checkpoint_sha256'], expected_core_sha256=expected_core)
    if (report.get('status') != 'ACTUAL_MONITOR_AND_DIALOGUES_RECORDED'
            or any(report.get(k) != v for k, v in info().items()) or report.get('lineage') != lineage
            or report.get('core_before') != expected_core or report.get('core_after') != expected_core
            or report.get('monitor_cases_sha256') != bundle['contract']['monitor_cases_sha256']
            or report.get('dialogue_cases_sha256') != bundle['contract']['dialogue_cases_sha256']
            or report.get('weights_changed') is not False or report.get('checkpoints_written') != 0):
        raise ValueError('complete current-code/case/body actual evaluation required')
    native = report.get('native32_fp32', {})
    if (native.get('targets') != 32768 or native.get('windows') != 32
            or native.get('precision') != 'FP32_MATH' or native.get('val_sha256') != monitor.base.NATIVE_VAL_SHA
            or type(native.get('ce')) not in (int, float) or not math.isfinite(native['ce']) or native['ce'] <= 0):
        raise ValueError('same fixed32 native FP32 receipt required')
    raw = RAW / ('evaluate_' + label)
    manifest = report['dialogue_manifest']
    if (manifest.get('lineage') != lineage or required(raw / 'dialogue_answers_shards_manifest.json') != manifest
            or digest(raw / 'dialogue_answers_shards_manifest.json') != report['dialogue_manifest_sha256']):
        raise ValueError('actual dialogue manifest content/SHA/lineage differs')
    dialogues = monitor.read_rows(raw, manifest, 'dialogue_answers', 16)
    validate_dialogues(dialogues, bundle['dialogues'], tok, lineage)
    if dialogue_summary(dialogues) != report['dialogue_summary']:
        raise ValueError('actual dialogue bookkeeping differs')
    if arm is None:
        events, reused = reused_parent_monitor(bundle, tok)
        if reused != report['monitor']:
            raise ValueError('explicit old parent reuse receipt differs')
    else:
        manifest = report['monitor']['manifest']
        if (manifest.get('lineage') != lineage or required(raw / 'monitor_answers_shards_manifest.json') != manifest
                or digest(raw / 'monitor_answers_shards_manifest.json') != report['monitor']['manifest_sha256']):
            raise ValueError('fresh monitor manifest content/SHA/lineage differs')
        events = monitor.read_rows(raw, manifest, 'monitor_answers', 1694)
        if any(event.get('lineage') != lineage for event in events):
            raise ValueError('fresh actual monitor lineage differs')
        if monitor.recount(events, bundle['monitor'], tokenizer=tok) != report['monitor']['summary']:
            raise ValueError('actual monitor recount differs')
    return report, events, dialogues


def readback():
    from tokenizers import Tokenizer
    bundle = prepared(); tok = Tokenizer.from_file(str(monitor.natural.TOKENIZER))
    reports, events = {}, {}
    for label in ('parent', *ARMS):
        report, rows, dialogues = _read_eval(label, bundle, tok)
        reports[label] = dict(monitor=report['monitor']['summary'], dialogue=report['dialogue_summary'],
            native=report['native32_fp32'], report_sha256=digest(EVIDENCE / ('evaluate_' + label) / 'report.json'))
        events[label] = rows
    paired = defaultdict(Counter)
    flags = {r['id']: r['exact_or_root_overlap'] for r in bundle['contract']['monitor_overlap']['cases']}
    for case, left, right in zip(bundle['monitor'], events['mixed'], events['staged']):
        if case['lane'] == 'user_seen':
            continue
        key = (case['lane'], case['family'], case['language'], 'FLAGGED' if flags[case['id']] else 'CLEAN_TECHNICAL')
        a, b = bool(left['metrics']['correct']), bool(right['metrics']['correct'])
        paired[key].update(n=1, mixed=int(a), staged=int(b), mixed_only=int(a and not b), staged_only=int(b and not a))
    write(EVIDENCE / 'readback.json', dict(info(), status='BROAD_ACTUAL_READBACK_COMPLETE', errors=0,
        reports=reports, paired=[dict(stratum=list(k), **dict(v)) for k, v in sorted(paired.items())],
        monitor_scope='repeated monitor; technical clean subset is not a full decontamination certificate',
        dialogues='same original publicVAL16; actual model histories; human review remains required',
        old_parent_monitor_explicitly_reused=True, new_training=0, checkpoints_written=0))
    print('[BROAD_READBACK] actual monitor/dialogue receipts verified; semantic quality not established', flush=True)
    return 0


def worker(mode, arm, max_wall_sec):
    authority()
    if mode == 'source':
        source_pins(); print('[BROAD_SOURCE] exact inputs/code; admission only in CPU prepare', flush=True); return 0
    if mode == 'preflight':
        prepared(); print('[BROAD_PREFLIGHT] all passes/DEV actual consumers verified; model/GPU NOT_RUN', flush=True); return 0
    if mode == 'budget':
        print('[BROAD_BUDGET] ' + json.dumps(budget()), flush=True); return 0
    from scripts.p106b_gate_runtime import wall_limit
    key = activity_key(mode, arm); activity = safe(EVIDENCE / ('activity_' + key + '.json'))
    if activity.exists():
        raise FileExistsError('preserve previous complete/partial worker activity')
    training = mode in ('prepare', 'cost', 'train')
    reserve = EVAL_RESERVE + RECORD_RESERVE if training else RECORD_RESERVE
    absolute = authority(training=training) - (0 if training else RECORD_RESERVE)
    if max_wall_sec > min(absolute, ACTIVE_LIMIT - spent_seconds() - reserve):
        raise Pending('bounded worker plus stage/deadline reserves does not fit')
    began, code = time.perf_counter(), None
    try:
        with wall_limit(max_wall_sec):
            if mode == 'prepare': returned = prepare()
            elif mode in ('cost', 'train'): returned = train(arm, cost=mode == 'cost')
            elif mode == 'evaluate': returned = evaluate(arm)
            elif mode == 'readback': returned = readback()
            else: raise ValueError('registered worker mode required')
            if returned != 0:
                raise ValueError('successful owned worker must return0')
            completion_binding(mode, arm, required_report=True)
            code = returned
        return code
    finally:
        write(activity, dict(schema=SCHEMA, tag=TAG, key=key, mode=mode, arm=arm,
            seconds=time.perf_counter() - began, returncode=code, complete=code == 0,
            max_wall_sec=max_wall_sec, code_sha256=info()['code_sha256'], recorded_at=datetime.now(timezone.utc).isoformat(),
            **completion_binding(mode, arm, required_report=False),
            scope='actual worker wall including full input verification; regression/wrapper excluded'))


def phase_commands(mode, arm, max_wall_sec):
    if (mode not in MODES or mode in ('cost', 'train') and arm not in ARMS
            or mode == 'evaluate' and arm is not None and arm not in ARMS
            or mode not in ('cost', 'train', 'evaluate') and arm is not None):
        raise ValueError('exact mode/arm pair; evaluate without arm is fixed parent only')
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 7200:
        raise ValueError('bounded60..7200 wall seconds required')
    py = [sys.executable, '-B', '-X', 'utf8']; script = ['scripts/diag_p106b_broad_curriculum.py']
    execute = py + script + ['--mode', mode, '--worker', '--execute', '--max-wall-sec', str(max_wall_sec)]
    if arm is not None: execute += ['--arm', arm]
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_broad_course',
                                'scripts.test_p106b_broad_curriculum', '-v']),
            ('PREFLIGHT', py + script + ['--mode', 'source' if mode in ('source', 'prepare') else 'preflight',
                                        '--worker', '--execute', '--max-wall-sec', '600']),
            ('EXECUTE', execute)]


def launch(command, timeout):
    process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, start_new_session=True)
    try:
        return process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        interrupted = sys.exc_info()[0] is KeyboardInterrupt
        try:
            if process.poll() is None and os.getpgid(process.pid) == process.pid:
                os.killpg(process.pid, signal.SIGTERM)
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if process.poll() is None: os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
        except ProcessLookupError:
            pass
        return 130 if interrupted else 124


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=MODES); parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--worker', action='store_true'); parser.add_argument('--max-wall-sec', type=int, default=3600)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        phases = phase_commands(args.mode, args.arm, args.max_wall_sec)
        if args.check_only:
            print('[BROAD_CHECK_ONLY] ' + json.dumps(info(), sort_keys=True), flush=True); return 0
        if args.worker: return worker(args.mode, args.arm, args.max_wall_sec)
        return pipeline(phases, lambda command: launch(command, min(args.max_wall_sec + 120, authority())),
            lambda line: print(line, flush=True), experiment='P106B_BROAD_' + activity_key(args.mode, args.arm))['returncode']
    except builder.SourceUnavailable as exc:
        print('[BROAD_FINAL] SOURCE_UNAVAILABLE8: ' + str(exc), flush=True); return 8
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        status, code = monitor.base.failure_status(exc)
        if code == 9:
            import traceback
            traceback.print_exc()
        print('[BROAD_FINAL] ' + status + str(code) + ': ' + str(exc), flush=True); return code


if __name__ == '__main__':
    raise SystemExit(main())
