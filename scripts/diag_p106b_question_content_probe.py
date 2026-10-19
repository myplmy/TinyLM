#!/usr/bin/env python3
"""Isolated final-fit/surface-transfer diagnosis; no learning or checkpoint writes.

Check-only is source-free. Actual workers bind only the explicitly frozen v2
encoded projection, never its old_source/source_inputs/read_prepared admission
chain. Teacher-forced scores and actual user-only free answers stay separate.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import gc
import hashlib
import importlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_question_transfer_data as data
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_stage_receipt import pipeline

TAG = 'p106b_question_content_probe_v1_s1337'
SCHEMA = 'P106B_QUESTION_CONTENT_PROBE_V1'
SOURCE_REPORT_SHA = 'F708CE04D09B6C710C64D67CF2B267C375BB91CCA06DE1B8F40C5E2B3393676C'
ENDPOINTS = ('parent', 'fixed_last', 'varied_balanced')
ARMS = ENDPOINTS[1:]
MODES = ('source', 'prepare', 'preflight', 'evaluate', 'readback')
CORPUS = ROOT / 'data_cache' / TAG / 'corpus'
LOCAL = ROOT / 'data_cache' / TAG
EVIDENCE = ROOT / 'test_result/evidence' / TAG
OWN_CODE = ('scripts/diag_p106b_question_content_probe.py', 'scripts/test_p106b_question_content_probe.py')
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
RECORD_RESERVE = 3600
LIMITS = dict(source=300, prepare=300, preflight=300, evaluate=600, readback=600)
EXPECTED_CASES, CONTEXT, MAX_NEW = 256, 1024, 64
PROJECTION_SCOPE = ('exact frozen v2 coded/wire/closed-scalar execution projection; '
                    'no renewed HF/natural/replay-source/native-cache audit')


class Pending(RuntimeError):
    pass


def upstream():
    return importlib.import_module('scripts.diag_p106b_question_transfer')


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest().upper()


def safe(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    if '..' in path.parts or '\\' in str(path):
        raise ValueError('parent/backslash path components forbidden')
    relative = path.relative_to(ROOT)
    current = ROOT
    for component in (None, *relative.parts):
        if component is not None:
            current /= component
        if current.is_symlink():
            raise ValueError('linked path forbidden before descendant access')
    return path


def digest(path):
    path = safe(path)
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest().upper()


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError('duplicate JSON key')
        value[key] = item
    return value


def required(path):
    path = safe(path)
    if not path.is_file():
        raise Pending('required completed artifact absent: ' + str(path.relative_to(ROOT)))
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def write(path, value):
    path = safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def info():
    """Static/source-only contract; do not import the upstream asset consumer."""
    return dict(schema=SCHEMA, tag=TAG, source_report_sha256=SOURCE_REPORT_SHA,
        endpoints=list(ENDPOINTS), cases_per_endpoint=EXPECTED_CASES, fresh_answers=768,
        context=CONTEXT, max_new=MAX_NEW, modes=list(MODES), worker_limits=LIMITS,
        authority_end_utc=END.isoformat(), record_reserve_seconds=RECORD_RESERVE,
        source_scope=PROJECTION_SCOPE, new_training=0, optimizer_updates=0,
        checkpoints_written=0, teacher_calls=0, automatic_adoption=False,
        scientific_acceptance_threshold='NONE', source_assets='NOT_READ_IN_CHECK_ONLY')


def code_pins(up):
    names = sorted(set((*up.CODE, *OWN_CODE, 'scripts/diag_p101a_mtp_parity.py',
        'tinylm/infer/generate.py', 'tinylm/model/transformer.py',
        'scripts/p106b_shards.py', 'scripts/p106b_stage_receipt.py')))
    return {name: digest(ROOT / name) for name in names}


def activity_path(mode, endpoint=None):
    need(mode in ('prepare', 'evaluate', 'readback')
         and ((mode == 'evaluate') == (endpoint in ENDPOINTS))
         and (endpoint is None or mode == 'evaluate'), 'exact activity identity required')
    return safe(EVIDENCE / ('activity_' + mode + ('_' + endpoint if endpoint else '') + '.json'))


def activity_time(value):
    need(type(value) is str, 'worker activity requires an aware timestamp string')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('worker activity timestamp is not valid ISO time') from exc
    need(parsed.tzinfo is not None and parsed.utcoffset() is not None,
         'worker activity timestamp must be timezone-aware')
    return parsed.astimezone(timezone.utc)


def completed_activity(mode, endpoint, corpus_sha256, *, up=None, now=None):
    """Downstream admission only; a report written before cleanup is not closure."""
    path = activity_path(mode, endpoint)
    receipt = required(path)
    up = upstream() if up is None else up
    need(all(receipt.get(k) == v for k, v in info().items())
         and receipt.get('mode') == mode and receipt.get('endpoint') == endpoint
         and receipt.get('code_sha256') == code_pins(up)
         and receipt.get('corpus_report_sha256') == corpus_sha256,
         'worker activity identity/code/corpus binding differs')
    status = receipt.get('status')
    if status in ('NOT_RUN', 'STARTED', 'RUNNING') and receipt.get('returncode') is None \
            and receipt.get('complete') is False:
        raise Pending('required worker activity is not closed: ' + mode)
    need(status == 'COMPLETE' and type(receipt.get('returncode')) is int
         and receipt['returncode'] == 0 and receipt.get('complete') is True,
         'required worker activity failed or has contradictory completion')
    need(finite(receipt.get('seconds')) and receipt['seconds'] >= 0
         and type(receipt.get('requested_limit')) is int
         and 60 <= receipt['requested_limit'] <= LIMITS[mode]
         and receipt['seconds'] <= receipt['requested_limit']
         and receipt.get('within_requested_time_and_authority') is True,
         'completed worker activity timing contract differs')
    started, recorded = (activity_time(receipt.get(k)) for k in ('started_at', 'recorded_at'))
    now = datetime.now(timezone.utc) if now is None else now
    need(isinstance(now, datetime) and now.tzinfo is not None and now.utcoffset() is not None,
         'activity admission UTC time must be timezone-aware')
    need(started <= recorded <= END - timedelta(seconds=RECORD_RESERVE)
         and recorded <= now.astimezone(timezone.utc)
         and (recorded - started).total_seconds() <= receipt['requested_limit'],
         'worker activity UTC interval/cutoff/admission contradicts bounded completion')
    return dict(path=str(path.relative_to(ROOT)), sha256=digest(path))


def authority(seconds=0, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('timezone-aware authority time required')
    left = (END - now).total_seconds() - RECORD_RESERVE
    if left <= 0 or seconds > left:
        raise Pending('bounded work plus one-hour record reserve exceeds current authority')
    return left


def read_rows(directory, manifest, stem, count, *, up=None):
    """Validate every exact basename before any delegated digest/open."""
    safe(directory)
    specs = manifest.get('shards')
    need(manifest.get('schema') == 'P106B_WRITE_ONCE_SHARDS_V1'
         and manifest.get('rows') == count and isinstance(specs, list) and bool(specs),
         'complete exact declared shard population required')
    for i, spec in enumerate(specs):
        need(spec.get('path') == f'{stem}_{i:06d}.jsonl'
             and type(spec.get('bytes')) is int and 0 < spec['bytes'] < 20_000_000,
             'exact bounded shard basename required before hashing')
    for spec in specs:
        safe(directory / spec['path'])
    need(required(directory / (stem + '_shards_manifest.json')) == manifest,
         'manifest file differs from declared immutable manifest')
    if up is not None:
        return up.read_rows(directory, manifest, stem, count)
    verify(directory, manifest)
    result = [json.loads(line, object_pairs_hook=_pairs) for spec in specs
              for line in (directory / spec['path']).read_text(encoding='utf-8').splitlines()]
    need(len(result) == count, 'raw row denominator differs')
    return result


def closed_training(up, frozen, arm):
    """Metadata admission BEFORE scalar/wire payload reads; no checkpoint I/O."""
    directory = safe(up.EVIDENCE / ('train_' + arm))
    report = required(directory / 'report.json')
    start = required(directory / 'start.json')
    current = up.info()
    need(report.get('status') == 'TRAIN_COMPLETE_EVALUATION_PENDING'
         and report.get('arm') == arm and report.get('updates') == 384
         and report.get('checkpoint_written') is True and report.get('optimizer_saved') is False,
         'completed384 weight-only source training required')
    need(all(report.get(k) == v and start.get(k) == v for k, v in current.items()),
         'source start/report code and recipe binding changed')
    need(start.get('arm') == arm and start.get('cost') is False,
         'same actual non-cost source training start required')
    expected_checkpoint = str(up.checkpoint(arm).relative_to(ROOT))
    need(report.get('checkpoint') == expected_checkpoint
         and report.get('initial_core_sha256') == frozen['expected_parent_core_sha256']
         and report.get('corpus_sha256') == SOURCE_REPORT_SHA
         and re.fullmatch('[0-9A-F]{64}', report.get('checkpoint_sha256', '')) is not None
         and re.fullmatch('[0-9A-F]{64}', report.get('final_core_sha256', '')) is not None,
         'exact source/checkpoint-claim/body lineage required before payload reads')
    need([(h.get('epoch'), h.get('updates')) for h in report.get('history', [])]
         == [(e + 1, (e + 1) * 96) for e in range(4)], 'source four executed epochs required')
    expected = {key: sum(v['counts'][key] for v in frozen['exposure'][arm])
                for key in ('positive_rows', 'assistant_targets', 'x_tokens')}
    expected['native_targets'] = 384 * 8192
    need(report.get('totals') == expected, 'closed source totals differ from frozen exposure')
    manifest = report.get('event_manifest', {})
    need(manifest.get('lineage') == dict(tag=up.TAG, arm=arm, cost=False),
         'closed execution manifest lineage differs')
    return dict(report=report, start=start, directory=directory, manifest=manifest,
        report_sha256=digest(directory / 'report.json'), start_sha256=digest(directory / 'start.json'))


def read_projection(up=None):
    up = upstream() if up is None else up
    source_path = safe(up.CORPUS / 'report.json')
    need(digest(source_path) == SOURCE_REPORT_SHA, 'exact F708 frozen source report changed')
    frozen = required(source_path)
    current = up.info()
    need(frozen.get('status') == 'QUESTION_TRANSFER_CPU_VERIFIED'
         and all(frozen.get(k) == v for k, v in current.items()),
         'current full upstream info/source map differs from pinned freeze')
    public = {k: v for k, v in frozen.items() if k not in ('manifests', 'native_train_offsets', 'blocked')}
    public['corpus_report_sha256'] = SOURCE_REPORT_SHA
    need(required(up.EVIDENCE / 'cpu_contract.json') == public, 'frozen public CPU binding differs')
    stems = [arm + '_e' + str(e + 1) for arm in ARMS for e in range(4)]
    for stem in stems:
        need(frozen['manifests'][stem].get('lineage') == dict(tag=up.TAG, stem=stem),
             'exact eight source pass stem lineage required before payload reads')
    training = {arm: closed_training(up, frozen, arm) for arm in ARMS}
    # All source metadata admissions above precede these explicitly allowed rows.
    for arm, entry in training.items():
        events = read_rows(entry['directory'], entry['manifest'], 'updates', 384, up=up)
        report = entry['report']
        need(report['step_seconds'] == [e['step_seconds'] for e in events], 'source timing cohort differs')
        for i, event in enumerate(events):
            epoch, slot = divmod(i, 96)
            need(event.get('update') == i + 1 and event.get('epoch') == epoch + 1
                 and event.get('assistant_targets') == frozen['exposure'][arm][epoch]['update_target_denominators'][slot]
                 and event.get('native_targets') == 8192
                 and all(finite(event.get(k)) for k in ('assistant_ce', 'native_ce', 'gradient_norm', 'step_seconds'))
                 and event['step_seconds'] > 0, 'executed source update/epoch/denominator differs')
        need(report['grad_max'] == max(e['gradient_norm'] for e in events)
             and report['clip_events'] == sum(e['gradient_norm'] > 1. for e in events)
             and sum(e['x_tokens'] for e in events) == report['totals']['x_tokens'],
             'source scalar raw recount differs')
        entry['events'] = events
        entry['manifest_sha256'] = digest(entry['directory'] / 'updates_shards_manifest.json')
    coded = read_rows(up.CORPUS, frozen['manifests']['coded'], 'coded', 2432, up=up)
    course = data.build_course(blocked=frozen['blocked'])
    data.validate_course(course)
    need(sha(course) == frozen['course_sha256']
         and coded == [dict(split=s, problem=p) for s in ('train', 'dev', 'test') for p in course[s]],
         'frozen coded2432 reconstruction/projection differs')
    return dict(frozen=frozen, course=course, training=training,
                source_report_sha256=SOURCE_REPORT_SHA, upstream=up)


def select_problems(course):
    cohort = data.evaluation_problems(course)
    result = []
    for split in ('train', 'test'):
        for family in data.FAMILIES:
            values = [p for p in cohort[split] if p['family'] == family]
            if family in ('lookup', 'format'):
                groups = defaultdict(list)
                for problem in values:
                    groups[problem['parent_group_id']].append(problem)
                width = 4 if family == 'lookup' else 2
                selected = sorted(groups, key=lambda k: sha([TAG, 'parent', split, family, k]))[:8 // width]
                chosen = [p for key in selected for p in sorted(groups[key], key=lambda p: p['query_id'])]
                need(all(len(groups[k]) == width for k in selected), 'whole source parent required')
            else:
                chosen = sorted(values, key=lambda p: sha([TAG, 'query', split, family, p['query_id']]))[:8]
            need(len(chosen) == 8, 'source-first eight-query supply missing')
            result.extend(chosen)
    need(len(result) == 64 and len({p['query_id'] for p in result}) == 64, '64 neutral source queries required')
    return result


def validate_wire(value):
    x, y, owners = value['x'], value['y'], value['segments']
    need(isinstance(x, list) and len(x) == len(y) == len(owners) and 0 < len(x) <= CONTEXT,
         'complete equal-length encoded source record required')
    need(all(type(v) is int and 0 <= v < 32768 for v in x)
         and all(type(v) is int and (v == -100 or 0 <= v < 32768) for v in y)
         and all(type(v) is int and v >= 0 for v in owners), 'encoded vocabulary/mask/owner differs')
    need(all(v == -100 or owner > 0 for v, owner in zip(y, owners)), 'supervised owner zero forbidden')
    need(value['record_sha256'] == sha(dict(x=x, y=y, segments=owners))
         and value['assistant_targets'] == sum(v != -100 for v in y)
         and value['x_tokens'] == len(x), 'encoded record SHA/counts changed')


def validate_encoding(case, eot):
    wire = case['wire']; validate_wire(wire)
    p, targets = case['prompt_ids'], case['target_ids']
    positions = [i for i, y in enumerate(wire['y']) if y != -100]
    need(bool(targets) and targets[-1] == eot and targets.count(eot) == 1 and len(targets) <= MAX_NEW,
         'one final EOT and complete target budget required')
    need(len(p) + MAX_NEW <= CONTEXT and positions == list(range(len(p) - 1, len(p) - 1 + len(targets)))
         and wire['x'][:len(p)] == p and wire['x'][len(p):len(p) + len(targets) - 1] == targets[:-1]
         and [wire['y'][i] for i in positions] == targets, 'exact causal prefix/shift/complete targets required')
    evidence = case['encoding']
    need(evidence['prompt_ids_sha256'] == sha(p) and evidence['target_ids_sha256'] == sha(targets)
         and evidence['prompt_tokens'] == len(p) and evidence['assistant_targets'] == len(targets),
         'frozen prompt/target encoding evidence differs')
    return positions


def build_cases(course, tok, up):
    result = []
    for problem in select_problems(course):
        for language in ('ko', 'en'):
            for wording in (0, 2):
                row = data.render(problem, language, wording, 'CQ')
                record, encoding = up.encode_row(row, tok)
                prompt = serialize_messages(row['messages'][:1])
                encoded = tok.encode(prompt)
                need(record.x[:len(encoded.ids)] == encoded.ids, 'free prefix differs from training encoding')
                identity = sha([TAG, problem['query_id'], language, wording, 'CQ'])
                case = dict(id=identity, problem=problem, split=problem['split'], family=problem['family'],
                    language=language, wording=wording, position='CQ', group_id=problem['parent_group_id'],
                    messages=row['messages'][:1], gold=problem['target_by_language'][language],
                    wire=up.wire(record, identity, 'coded', language, problem['parent_group_id'], encoding),
                    encoding=encoding, prompt_ids=list(encoded.ids),
                    target_ids=[y for y in record.y if y != -100],
                    question_sha256=row['meta']['question_sha256'], context_sha256=row['meta']['context_sha256'])
                validate_encoding(case, tok.token_to_id('<|im_end|>'))
                case['lengths'] = token_lengths(problem, language, wording, prompt, encoded)
                result.append(case)
    need(len(result) == EXPECTED_CASES and len({c['id'] for c in result}) == EXPECTED_CASES,
         'complete256 unique diagnostic cases required')
    return result


def display_ids(cases):
    result = []
    for si, split in enumerate(('train', 'test')):
        for fi, family in enumerate(data.FAMILIES):
            lang = ('ko', 'en')[(si + fi) % 2]
            candidates = [c for c in cases if c['split'] == split and c['family'] == family
                          and c['language'] == lang and c['wording'] == 0]
            base = min(candidates, key=lambda c: sha([TAG, 'display', c['problem']['query_id']]))
            result.extend(c['id'] for c in cases if c['problem']['query_id'] == base['problem']['query_id']
                          and c['language'] == lang)
    need(len(result) == 16 and len(set(result)) == 16, 'fixed small paired display population differs')
    return result


def d_pairs(cases):
    groups = defaultdict(list)
    for case in cases:
        if len(case['target_ids']) == 2:
            groups[(case['split'], case['family'], case['language'], case['wording'], case['question_sha256'])].append(case)
    result = []
    for group in groups.values():
        options = [(a, b) for a, b in itertools.combinations(sorted(group, key=lambda c: c['id']), 2)
                   if a['group_id'] != b['group_id'] and a['context_sha256'] != b['context_sha256']
                   and a['target_ids'][0] != b['target_ids'][0]]
        if options:
            a, b = min(options, key=lambda pair: sha([TAG, 'D', pair[0]['id'], pair[1]['id']]))
            result.append(dict(left=a['id'], right=b['id'], left_token=a['target_ids'][0], right_token=b['target_ids'][0]))
    return sorted(result, key=lambda p: (p['left'], p['right']))


def membership(projection, cases):
    """Prefix exposure ignores y/owners; conflict counters name the first boundary."""
    up, frozen = projection['upstream'], projection['frozen']
    trie = {}
    for case in cases:
        node = trie
        for token in case['prompt_ids']:
            node = node.setdefault(token, {})
        node.setdefault(None, []).append(case)
    proof = {arm: {c['id']: dict(prompt_prefix_seen_count=0, exact_full_record_matches=0,
        supervised_boundary_matches=0, masked_context_prefix_matches=0,
        conflicting_first_target_matches=0, conflicting_first_owner_matches=0,
        occurrences=[]) for c in cases} for arm in ARMS}
    for arm in ARMS:
        closed = projection['training'][arm]
        for epoch in range(4):
            stem = arm + '_e' + str(epoch + 1)
            manifest = frozen['manifests'][stem]
            rows = read_rows(up.CORPUS, manifest, stem, 12288, up=up)
            schedule = up.schedule(epoch)
            need(sha(schedule) == frozen['exposure'][arm][epoch]['schedule_sha256'], 'executed schedule changed')
            slots = {index: (slot, micro, j) for slot, group in enumerate(schedule)
                     for micro, indices in enumerate(group) for j, index in enumerate(indices)}
            need(len(slots) == 12288, 'schedule did not consume the entire declared pass')
            offset = 0; locations = {}
            for spec in manifest['shards']:
                for line in range(spec['rows']):
                    locations[offset + line] = (spec['path'], line + 1)
                offset += spec['rows']
            for index, wire in enumerate(rows):
                node = trie
                for token in wire['x']:
                    node = node.get(token)
                    if node is None:
                        break
                    for case in node.get(None, []):
                        validate_wire(wire)
                        entry = proof[arm][case['id']]; entry['prompt_prefix_seen_count'] += 1
                        k = len(case['prompt_ids']) - 1
                        expected_y, expected_owner = case['wire']['y'][k], case['wire']['segments'][k]
                        observed_y, observed_owner = wire['y'][k], wire['segments'][k]
                        entry['masked_context_prefix_matches'] += int(observed_y == -100)
                        entry['supervised_boundary_matches'] += int(observed_y == expected_y and observed_owner == expected_owner)
                        entry['conflicting_first_target_matches'] += int(observed_y != -100 and observed_y != expected_y)
                        entry['conflicting_first_owner_matches'] += int(observed_owner != expected_owner)
                        exact = all(wire[key] == case['wire'][key] for key in ('x', 'y', 'segments'))
                        if exact:
                            validate_wire(wire)
                            need(wire['encoding'] == case['encoding'], 'exact source row metadata/prompt/target evidence differs')
                            need(wire['id'] == sha(['CODED', case['problem']['query_id'], case['language']]),
                                 'exact seen record has an unexpected source identity')
                            entry['exact_full_record_matches'] += 1
                        slot, micro, within = slots[index]
                        event = closed['events'][epoch * 96 + slot]
                        path, line = locations[index]
                        entry['occurrences'].append(dict(epoch=epoch + 1, stem=stem, shard=path, line=line,
                            index=index, update=event['update'], micro=micro, within_micro=within,
                            full_record_exact=exact, source_row_id=wire['id'], source_record_sha256=wire['record_sha256'],
                            source_manifest_sha256=sha(manifest), event_manifest_sha256=closed['manifest_sha256'],
                            train_report_sha256=closed['report_sha256']))
            del rows
    conflicts = []
    for arm in ARMS:
        for case in cases:
            entry = proof[arm][case['id']]
            expected = (4 if arm == 'fixed_last' else 1) if case['split'] == 'train' and case['wording'] == 0 else 0
            if (entry['prompt_prefix_seen_count'] != expected or entry['exact_full_record_matches'] != expected
                    or entry['masked_context_prefix_matches'] or entry['conflicting_first_target_matches']
                    or entry['conflicting_first_owner_matches']):
                conflicts.append(dict(arm=arm, case_id=case['id'], expected=expected,
                    prefix=entry['prompt_prefix_seen_count'], exact=entry['exact_full_record_matches']))
            if expected and entry['prompt_prefix_seen_count'] == expected and entry['exact_full_record_matches'] == expected:
                expected_epochs = [e + 1 for e in range(4) if data.schedule_view(case['problem'], arm, e) == dict(wording=0, position='CQ')]
                need([o['epoch'] for o in entry['occurrences']] == expected_epochs, 'actual seen view is not the executed declared rotation')
    if conflicts:
        raise Pending('prefix/target/owner exposure is unresolved, not unseen: ' + json.dumps(conflicts[:4], sort_keys=True))
    return proof


def serialize_messages(messages):
    from tinylm.chat.serialize import serialize
    return serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)


def token_lengths(problem, language, wording, prompt, encoded):
    offsets = getattr(encoded, 'offsets', None)
    need(isinstance(offsets, list) and len(offsets) == len(encoded.ids),
         'complete prompt token offsets required for length/distance description')
    context, question = data._context(problem, language), data._question(problem, language, wording)
    result = dict(prompt_tokens=len(encoded.ids), basis='intersections with exact full-prompt token offsets')
    for label, value in (('context', context), ('question', question)):
        need(prompt.count(value) == 1, 'unique renderer-owned context/question span required')
        start = prompt.index(value); end = start + len(value)
        positions = [i for i, (a, b) in enumerate(offsets) if b > start and a < end]
        need(bool(positions), 'renderer span has no prompt-token coverage')
        result[label + '_tokens'] = len(positions)
        if label == 'question':
            result['query_end_to_predictor_tokens'] = len(encoded.ids) - 1 - max(positions)
    return result


def source_binding(projection):
    up = projection['upstream']
    return dict(source_report_sha256=SOURCE_REPORT_SHA,
        public_cpu_sha256=digest(up.EVIDENCE / 'cpu_contract.json'),
        upstream_info_sha256=sha(up.info()), course_sha256=projection['frozen']['course_sha256'],
        source_scope=PROJECTION_SCOPE,
        closed_training={arm: {k: entry[k] for k in ('report_sha256', 'start_sha256', 'manifest_sha256')}
                         for arm, entry in projection['training'].items()})


def tokenizer():
    up = upstream()
    need(digest(up.natural.TOKENIZER) == up.natural.TOK_SHA, 'exact frozen tokenizer bytes required')
    from tokenizers import Tokenizer
    return Tokenizer.from_file(str(up.natural.TOKENIZER))


def put(directory, stem, rows, lineage):
    writer = ShardWriter(directory, stem, limit=19_999_999)
    try:
        for row in rows:
            writer.append(row)
        return writer.close(lineage=lineage)
    finally:
        if writer._file is not None:
            writer._file.flush(); writer._file.close(); writer._file = None


def prepare():
    up = upstream()
    for path in (CORPUS, EVIDENCE):
        if safe(path).exists():
            raise FileExistsError('old complete/partial diagnostic namespace preserved')
    projection = read_projection(up)
    tok = tokenizer()
    cases = build_cases(projection['course'], tok, up)
    proof = membership(projection, cases)
    selected = display_ids(cases); pairs = d_pairs(cases)
    CORPUS.mkdir(parents=True, exist_ok=False)
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    manifest = put(CORPUS, 'cases', cases, dict(tag=TAG, source_report_sha256=SOURCE_REPORT_SHA))
    result = dict(info(), status='QUESTION_CONTENT_CPU_FROZEN', code_sha256=code_pins(up),
        source_binding=source_binding(projection), cases_sha256=sha(cases), manifest=manifest,
        display_ids=selected, display_sha256=sha(selected), d_pairs=pairs,
        membership=proof, membership_sha256=sha(proof),
        tokenizer_sha256=up.natural.TOK_SHA, eot_id=tok.token_to_id('<|im_end|>'),
        eos_id=tok.token_to_id('<eos>'), pad_id=tok.token_to_id('<pad>'),
        model_loaded=False, cuda_initialized=False)
    write(CORPUS / 'report.json', result)
    public = {k: v for k, v in result.items() if k not in ('membership', 'manifest')}
    public['corpus_report_sha256'] = digest(CORPUS / 'report.json')
    write(EVIDENCE / 'cpu_contract.json', public)
    print('[QUESTION_CONTENT_CPU] frozen256 cases; model/GPU NOT_RUN', flush=True)
    return 0


def read_prepared(*, reencode=True):
    up = upstream()
    report = required(CORPUS / 'report.json')
    need(report.get('status') == 'QUESTION_CONTENT_CPU_FROZEN'
         and all(report.get(k) == v for k, v in info().items())
         and report.get('code_sha256') == code_pins(up), 'frozen new code/CPU contract differs')
    activity = completed_activity('prepare', None, digest(CORPUS / 'report.json'), up=up)
    projection = read_projection(up)
    projection['activity_prepare'] = activity
    need(report['source_binding'] == source_binding(projection), 'frozen source projection differs')
    cases = read_rows(CORPUS, report['manifest'], 'cases', EXPECTED_CASES)
    need(sha(cases) == report['cases_sha256'], 'new diagnostic cases changed')
    need(display_ids(cases) == report['display_ids'] and sha(report['display_ids']) == report['display_sha256']
         and d_pairs(cases) == report['d_pairs'], 'pre-outcome display/D selection differs')
    if reencode:
        tok = tokenizer()
        need(build_cases(projection['course'], tok, up) == cases, 'actual full prompt/target encoding changed')
        need(report['tokenizer_sha256'] == up.natural.TOK_SHA
             and report['eot_id'] == tok.token_to_id('<|im_end|>')
             and report['eos_id'] == tok.token_to_id('<eos>')
             and report['pad_id'] == tok.token_to_id('<pad>'), 'tokenizer/control ID binding changed')
    for case in cases:
        validate_encoding(case, report['eot_id'])
    proof = membership(projection, cases)
    need(proof == report['membership'] and sha(proof) == report['membership_sha256'],
         'actual executed input-prefix/full-record membership changed')
    public = {k: v for k, v in report.items() if k not in ('membership', 'manifest')}
    public['corpus_report_sha256'] = digest(CORPUS / 'report.json')
    need(required(EVIDENCE / 'cpu_contract.json') == public, 'new public CPU projection differs')
    return report, cases, projection


def score_vector(logits, gold, eot, eos, other=None):
    """Small synthetic reference implementation; production uses batched tensors."""
    need(isinstance(logits, list) and len(logits) >= 4 and all(finite(x) for x in logits),
         'finite complete vocabulary logits required')
    need(all(type(i) is int and 0 <= i < len(logits) for i in (gold, eot, eos)), 'vocabulary ID out of range')
    z = logits[gold]; maximum = max(logits)
    log_z = maximum + math.log(sum(math.exp(x - maximum) for x in logits))
    top = max(range(len(logits)), key=lambda i: logits[i])
    def best(excluded):
        ids = [i for i in range(len(logits)) if i not in excluded]
        index = max(ids, key=lambda i: logits[i]) if ids else None
        return index, logits[index] if index is not None else None
    any_id, any_z = best({gold}); non_id, non_z = best({gold, eot, eos})
    return target_row(gold=gold, gold_logit=z, log_normalizer=log_z, top_id=top,
        top_logit=logits[top], vocab=len(logits), rank_low=1 + sum(x > z for x in logits),
        ties=sum(x == z for x in logits), any_id=any_id, any_logit=any_z,
        nonterminal_id=non_id, nonterminal_logit=non_z, eot_logit=logits[eot],
        eos_logit=logits[eos], other_logit=logits[other] if other is not None else None, other_id=other)


def target_row(*, gold, gold_logit, log_normalizer, top_id, top_logit, vocab,
               rank_low, ties, any_id, any_logit, nonterminal_id, nonterminal_logit,
               eot_logit, eos_logit, other_logit, other_id=None):
    return dict(gold_id=int(gold), gold_logit=float(gold_logit),
        log_normalizer=float(log_normalizer), nll=float(log_normalizer) - float(gold_logit),
        argmax_id=int(top_id), argmax_logit=float(top_logit), argmax_correct=int(top_id) == int(gold),
        vocab=int(vocab), rank_low=int(rank_low), rank_high=int(rank_low + ties - 1), ties=int(ties),
        best_any_nongold_id=any_id, best_any_nongold_logit=any_logit,
        margin_any_nongold=float(gold_logit) - any_logit if any_logit is not None else None,
        best_nongold_nonterminal_id=nonterminal_id, best_nongold_nonterminal_logit=nonterminal_logit,
        margin_nongold_nonterminal=float(gold_logit) - nonterminal_logit if nonterminal_logit is not None else None,
        eot_logit=float(eot_logit), eos_logit=float(eos_logit),
        margin_eot=float(gold_logit) - float(eot_logit), margin_eos=float(gold_logit) - float(eos_logit),
        d_other_id=other_id, d_other_logit=other_logit,
        d_gap=float(gold_logit) - other_logit if other_logit is not None else None)


def score_tensor(logits, targets, eot, eos, other=None):
    """FP32 observed logits/logsumexp; Python scalar subtraction defines NLL."""
    import torch
    need(logits.ndim == 2 and logits.shape[0] == len(targets)
         and bool(torch.isfinite(logits).all()), 'complete finite selected-vocabulary tensor required')
    logits = logits.float()
    gold = torch.tensor(targets, dtype=torch.long, device=logits.device)
    z = logits.gather(1, gold[:, None]).squeeze(1)
    top_z, top = logits.max(dim=1)
    log_z = torch.logsumexp(logits, dim=1)
    ranks = 1 + (logits > z[:, None]).sum(dim=1)
    ties = (logits == z[:, None]).sum(dim=1)
    masked = logits.clone(); masked.scatter_(1, gold[:, None], -torch.inf)
    any_z, any_id = masked.max(dim=1)
    masked[:, [eot, eos]] = -torch.inf
    non_z, non_id = masked.max(dim=1)
    others = logits[:, other] if other is not None else torch.full_like(z, torch.nan)
    fields = torch.stack((z, log_z, top_z, top.float(), ranks.float(), ties.float(),
        any_z, any_id.float(), non_z, non_id.float(), logits[:, eot], logits[:, eos], others), dim=1).cpu().tolist()
    result = []
    for target, row in zip(targets, fields):
        a, b, c, d, r, t, az, ai, nz, ni, ez, sz, oz = row
        result.append(target_row(gold=target, gold_logit=a, log_normalizer=b,
            top_id=int(d), top_logit=c, vocab=logits.shape[1], rank_low=int(r), ties=int(t),
            any_id=int(ai) if math.isfinite(az) else None, any_logit=az if math.isfinite(az) else None,
            nonterminal_id=int(ni) if math.isfinite(nz) else None,
            nonterminal_logit=nz if math.isfinite(nz) else None, eot_logit=ez, eos_logit=sz,
            other_logit=oz if other is not None else None, other_id=other))
    return result


def tf_score(model, tok, case, frozen, other=None):
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    positions = validate_encoding(case, frozen['eot_id'])
    need(model.training is False and not torch.is_grad_enabled(), 'TF inference must be eval/no-grad')
    x = torch.tensor([case['wire']['x']], dtype=torch.long, device='cuda')
    prefix = torch.tensor([case['prompt_ids']], dtype=torch.long, device='cuda')
    with sdpa_kernel(SDPBackend.MATH), torch.autocast('cuda', enabled=False):
        forward = PrecisionForward(model, 'fp32_math')
        # Deliberately normal FULL-SEQUENCE main head, no hidden/head layout shortcut.
        full = forward(x, use_cache=False)
        rows = score_tensor(full[0, positions].float(), case['target_ids'], frozen['eot_id'], frozen['eos_id'])
        initial, _ = forward(prefix, use_cache=True, logits_last_only=True)
        first = score_tensor(initial[0, -1:, :].float(), case['target_ids'][:1],
                             frozen['eot_id'], frozen['eos_id'], other=other)[0]
        delta = float((initial[0, -1].float() - full[0, positions[0]].float()).abs().max())
    return dict(targets=rows, first_prefix=first, first_full=rows[0],
        first_predictor_position=positions[0], first_prefix_ids_sha256=sha(case['prompt_ids']),
        prefix_vs_full_max_abs=delta,
        prefix_vs_full_argmax_equal=first['argmax_id'] == rows[0]['argmax_id'],
        precision='FP32_MATH', full_head='NORMAL_FULL_SEQUENCE', no_grad=True,
        interpretation='first-token path comparison; later divergence mechanism unresolved')


def json_metrics(problem, raw):
    duplicates = []
    def pairs(items):
        d = {}
        for key, value in items:
            if key in d:
                duplicates.append(key)
            d[key] = value
        return d
    result = dict(syntax=False, object=False, unique_keys=False, requested_key_set=False,
                  payload_string_exact=False, strict=False)
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    except (TypeError, ValueError, RecursionError):
        return result
    result.update(syntax=True, object=isinstance(value, dict), unique_keys=not duplicates)
    if isinstance(value, dict):
        key = problem['query']['key']
        result['requested_key_set'] = set(value) == {key} and not duplicates
        result['payload_string_exact'] = type(value.get(key)) is str and value[key] == problem['state']['literal']
        result['strict'] = result['requested_key_set'] and result['payload_string_exact']
    return result


def divergence(reference, generated, prompt):
    index = next((i for i, (a, b) in enumerate(zip(reference, generated)) if a != b),
                 min(len(reference), len(generated)) if len(reference) != len(generated) else None)
    if index is None:
        return dict(index=None, exact_ids_equal=True, reached=True, equal_prefix=True,
                    scope='identical full generated reference including terminal')
    equal = reference[:index] == generated[:index]
    reached = index < len(reference) and index < len(generated)
    return dict(index=index, exact_ids_equal=False, reached=reached, equal_prefix=equal,
        reference_id=reference[index] if index < len(reference) else None,
        generated_id=generated[index] if index < len(generated) else None,
        reference_prefix_sha256=sha(prompt + reference[:index]),
        actual_prefix_sha256=sha(prompt + generated[:index]),
        mechanism='UNRESOLVED_BEYOND_FIRST' if index else 'FIRST_TOKEN_PATH_DIAGNOSTIC_NOT_BUG_PROOF')


def answer_metrics(case, answer, generated):
    result = dict(correct=data.classify(case['problem'], case['language'], answer),
        canonical_body_bytes_equal=answer == case['gold'],
        canonical_generated_ids_equal=generated == case['target_ids'])
    if case['family'] == 'format':
        result['json'] = json_metrics(case['problem'], answer)
        need(result['json']['strict'] == result['correct'], 'strict JSON/classifier definitions differ')
    return result


def validate_generation(case, answer, generation, frozen, tok=None):
    need(type(answer) is str, 'full raw answer string required')
    g = generation; ids = g.get('generated_ids'); terminal = g.get('terminal_ids')
    need(type(ids) is list and all(type(v) is int and 0 <= v < 32768 for v in ids)
         and type(terminal) is list and 1 <= len(ids) <= MAX_NEW, 'actual generated token-list schema differs')
    need(g.get('max_new') == MAX_NEW and g.get('precision') == 'FP32_MATH'
         and g.get('temperature') == 0. and g.get('top_k') == 1 and g.get('use_cache') is True
         and g.get('mtp') is False and g.get('candidate_answers_supplied') is False
         and g.get('terminal_only_removed') is True
         and g.get('stop_token_sequences') == [[frozen['eot_id']]]
         and g.get('generated_tokens') == len(ids) and g.get('generated_ids_sha256') == sha(ids)
         and all(g.get(k) == case['encoding'][k] for k in ('prompt_sha256', 'prompt_ids_sha256', 'prompt_tokens')),
         'unchanged actual user-only FP32 greedy64 generation receipt differs')
    reason = g.get('finish_reason')
    need((reason == 'STOP_SEQUENCE' and terminal == [frozen['eot_id']]
          and g.get('matched_stop_sequence') == terminal)
         or (reason == 'EOS' and terminal == [frozen['eos_id']]
             and g.get('matched_stop_sequence') is None)
         or (reason == 'MAX_NEW' and terminal == [] and len(ids) == MAX_NEW
             and g.get('matched_stop_sequence') is None), 'authenticated terminal/finish differs')
    need(not terminal or ids[-1:] == terminal, 'terminal is not the actual last generated ID')
    content = ids[:-1] if terminal else ids
    need(g.get('content_ids_sha256') == sha(content)
         and g.get('body_utf8_sha256') == hashlib.sha256(answer.encode('utf-8')).hexdigest().upper(),
         'raw body/content hash differs')
    if tok is not None:
        need(tok.decode(content, skip_special_tokens=False) == answer, 'actual content IDs do not decode to raw body')


def validate_target(row, gold, eot, eos, other=None):
    need(row['gold_id'] == gold and all(finite(row[k]) for k in (
        'gold_logit', 'log_normalizer', 'nll', 'argmax_logit', 'eot_logit', 'eos_logit')),
        'finite target logit receipt required')
    need(row['nll'] == row['log_normalizer'] - row['gold_logit']
         and row['nll'] >= 0 and row['log_normalizer'] >= row['argmax_logit']
         and type(row['argmax_correct']) is bool
         and row['argmax_correct'] == (row['argmax_id'] == gold)
         and all(type(row[k]) is int for k in ('argmax_id', 'vocab', 'rank_low', 'rank_high', 'ties'))
         and 0 <= row['argmax_id'] < row['vocab']
         and row['vocab'] >= 4
         and 1 <= row['rank_low'] <= row['rank_high'] <= row['vocab']
         and row['rank_high'] - row['rank_low'] + 1 == row['ties'],
         'target NLL/strict argmax/rank interval recount differs')
    for label, excluded in (('any_nongold', {gold}), ('nongold_nonterminal', {gold, eot, eos})):
        key = 'best_' + label
        value = row[key + '_logit']; identity = row[key + '_id']
        need(type(identity) is int and 0 <= identity < row['vocab'] and identity not in excluded
             and finite(value) and row['margin_' + label] == row['gold_logit'] - value,
             'finite existing global competing-token readout required')
    maximum = max(row['gold_logit'], row['best_any_nongold_logit'])
    need(row['argmax_logit'] == maximum
         and (row['rank_low'] == 1) == (row['gold_logit'] == maximum)
         and row['best_nongold_nonterminal_logit'] <= row['best_any_nongold_logit']
         and row['eot_logit'] <= maximum and row['eos_logit'] <= maximum,
         'contradictory observed maximum/rank/terminal logits')
    if row['argmax_correct']:
        need(row['argmax_logit'] == row['gold_logit']
             and (row['ties'] > 1) == (row['best_any_nongold_logit'] == row['gold_logit']),
             'chosen-gold strict argmax/tie consistency differs')
    else:
        need(row['best_any_nongold_id'] == row['argmax_id']
             and row['best_any_nongold_logit'] == row['argmax_logit'],
             'nongold chosen argmax is not the strongest recorded competitor')
        if row['rank_low'] == 1:
            need(row['ties'] >= 2 and row['argmax_id'] < gold,
                 'rank-one nonchosen gold must be a lower-index argmax tie')
    for identity, value in ((gold, row['gold_logit']),
                            (row['argmax_id'], row['argmax_logit']),
                            (row['best_any_nongold_id'], row['best_any_nongold_logit'])):
        if identity == eot:
            need(value == row['eot_logit'], 'EOT self-logit inconsistent')
        if identity == eos:
            need(value == row['eos_logit'], 'EOS self-logit inconsistent')
    need(row['margin_eot'] == row['gold_logit'] - row['eot_logit']
         and row['margin_eos'] == row['gold_logit'] - row['eos_logit'], 'terminal margin differs')
    need(row.get('d_other_id') == other and (row['d_other_logit'] is None) == (other is None),
         'paired readout token ID differs from preselected source pair')
    need(other is not None or row['d_gap'] is None, 'absent paired token must have no gap')
    if row['d_other_logit'] is not None:
        need(finite(row['d_other_logit']) and row['d_other_logit'] <= maximum
             and row['d_gap'] == row['gold_logit'] - row['d_other_logit'],
             'offline paired one-token gap differs')
    known = {}
    observations = [(gold, row['gold_logit']), (eot, row['eot_logit']), (eos, row['eos_logit']),
        (row['argmax_id'], row['argmax_logit']),
        (row['best_any_nongold_id'], row['best_any_nongold_logit']),
        (row['best_nongold_nonterminal_id'], row['best_nongold_nonterminal_logit'])]
    if other is not None:
        observations.append((other, row['d_other_logit']))
    for identity, value in observations:
        need(type(identity) is int and 0 <= identity < row['vocab']
             and (identity not in known or known[identity] == value),
             'same observed vocabulary ID has contradictory logits')
        known[identity] = value
        need(value <= maximum and (value != maximum or identity >= row['argmax_id']),
             'strict argmax contradicts an observed lower-index maximum')
    need(row['rank_low'] >= 1 + sum(value > row['gold_logit'] for value in known.values())
         and row['ties'] >= sum(value == row['gold_logit'] for value in known.values()),
         'rank/tie counts contradict the saved observed vocabulary subset')


def evaluate_cases(cases, frozen, score, generate, lineage, append, *, check_authority=None):
    """Dependency-injected core permits zero-model synthetic end-to-end tests."""
    partners = {}
    for pair in frozen['d_pairs']:
        partners[pair['left']] = pair['right_token']; partners[pair['right']] = pair['left_token']
    events = []
    for case in cases:
        if check_authority is not None:
            check_authority()
        tf = score(case, partners.get(case['id']))
        need(all(m.get('role') == 'user' for m in case['messages']), 'free generation must receive user-only messages')
        answer, generation = generate(case['messages'])  # NEVER gold or candidate arguments.
        difference = divergence(case['target_ids'], generation['generated_ids'], case['prompt_ids'])
        perfect = all(r['argmax_correct'] for r in tf['targets'])
        event = dict(id=case['id'], case_sha256=sha(case), lineage=lineage,
            tf=tf, answer=answer, generation=generation,
            metrics=answer_metrics(case, answer, generation['generated_ids']), divergence=difference,
            all_tf_targets_argmax_correct=perfect,
            tf_perfect_free_ids_differ=perfect and not difference['exact_ids_equal'],
            path_flag_scope='numeric/path diagnostic, not automatic bug or intelligence proof')
        append(event); events.append(event)
    return events


def recount(events, cases, frozen, *, tok=None, lineage=None):
    if len(events) != EXPECTED_CASES or len(cases) != EXPECTED_CASES or len({e['id'] for e in events}) != EXPECTED_CASES:
        raise Pending('full256 ordered unique actual events required; missing is NOT_RUN, not wrong')
    cells = defaultdict(lambda: dict(n=0, correct=0, content_nll=0., content_targets=0,
        eot_nll=0., eot_targets=0, macro_content_ce_sum=0., tf_argmax_correct=0,
        tf_targets=0, tf_perfect=0, tf_perfect_free_ids_differ=0, canonical_ids_equal=0,
        first_prefix_full_argmax_equal=0, finish=Counter(), gold_true=0, gold_false=0,
        predicted_true=0, predicted_false=0, json=Counter()))
    byid = {}; d_other = {}
    for pair in frozen['d_pairs']:
        d_other[pair['left']] = pair['right_token']; d_other[pair['right']] = pair['left_token']
    for event, case in zip(events, cases):
        need(event.get('id') == case['id'] and event.get('case_sha256') == sha(case)
             and (lineage is None or event.get('lineage') == lineage), 'ordered raw case/lineage binding differs')
        validate_encoding(case, frozen['eot_id'])
        validate_generation(case, event['answer'], event['generation'], frozen, tok)
        need(event['metrics'] == answer_metrics(case, event['answer'], event['generation']['generated_ids']),
             'raw model-answer score differs')
        tf = event['tf']; rows = tf['targets']
        need(len(rows) == len(case['target_ids']) and tf['first_full'] == rows[0]
             and tf['first_predictor_position'] == len(case['prompt_ids']) - 1
             and tf['first_prefix_ids_sha256'] == sha(case['prompt_ids'])
             and tf['precision'] == 'FP32_MATH' and tf['no_grad'] is True
             and tf['full_head'] == 'NORMAL_FULL_SEQUENCE'
             and finite(tf['prefix_vs_full_max_abs']) and tf['prefix_vs_full_max_abs'] >= 0,
             'complete same-prefix normal full-TF receipt differs')
        for row, target in zip(rows, case['target_ids']):
            validate_target(row, target, frozen['eot_id'], frozen['eos_id'])
        validate_target(tf['first_prefix'], case['target_ids'][0], frozen['eot_id'], frozen['eos_id'], d_other.get(case['id']))
        need(tf['prefix_vs_full_argmax_equal'] == (tf['first_prefix']['argmax_id'] == rows[0]['argmax_id']),
             'first-token prefix/full argmax comparison differs')
        diff = divergence(case['target_ids'], event['generation']['generated_ids'], case['prompt_ids'])
        perfect = all(row['argmax_correct'] for row in rows)
        need(event['divergence'] == diff and event['all_tf_targets_argmax_correct'] == perfect
             and event['tf_perfect_free_ids_differ'] == (perfect and not diff['exact_ids_equal']),
             'TF/free exact-token path flag differs')
        key = (case['split'], case['family'], case['language'], case['wording'])
        cell = cells[key]; content = sum(row['nll'] for row in rows[:-1]); count = len(rows) - 1
        need(count > 0, 'content denominator must be nonempty')
        cell['n'] += 1; cell['correct'] += int(event['metrics']['correct'])
        cell['content_nll'] += content; cell['content_targets'] += count
        cell['macro_content_ce_sum'] += content / count
        cell['eot_nll'] += rows[-1]['nll']; cell['eot_targets'] += 1
        cell['tf_targets'] += len(rows); cell['tf_argmax_correct'] += sum(r['argmax_correct'] for r in rows)
        cell['tf_perfect'] += int(perfect); cell['tf_perfect_free_ids_differ'] += int(event['tf_perfect_free_ids_differ'])
        cell['canonical_ids_equal'] += int(diff['exact_ids_equal'])
        cell['first_prefix_full_argmax_equal'] += int(tf['prefix_vs_full_argmax_equal'])
        cell['finish'][event['generation']['finish_reason']] += 1
        if case['family'] == 'boolean':
            cell['gold_true'] += int(case['gold'] == 'true'); cell['gold_false'] += int(case['gold'] == 'false')
            cell['predicted_true'] += int(event['answer'].strip().casefold() == 'true')
            cell['predicted_false'] += int(event['answer'].strip().casefold() == 'false')
        if case['family'] == 'format':
            cell['json'].update({k: int(v) for k, v in event['metrics']['json'].items()})
        byid[case['id']] = event
    need(len(cells) == 32 and all(v['n'] == 8 for v in cells.values()), 'exact32 eight-query strata required')
    output = []
    for key, values in sorted(cells.items()):
        cell = dict(values); cell['finish'] = dict(cell['finish']); cell['json'] = dict(cell['json'])
        cell.update(stratum=list(key), content_ce=cell['content_nll'] / cell['content_targets'],
                    content_ce_macro=cell['macro_content_ce_sum'] / cell['n'], eot_ce=cell['eot_nll'] / cell['eot_targets'])
        if key[1] == 'boolean':
            cell['constant_true_correct'] = cell['gold_true']; cell['constant_false_correct'] = cell['gold_false']
        output.append(cell)
    paired = []
    groups = defaultdict(dict)
    for case in cases:
        groups[(case['problem']['query_id'], case['language'])][case['wording']] = case
    for key, pair in sorted(groups.items()):
        need(set(pair) == {0, 2}, 'same-state paired T0/T2 questions required')
        a, b = (byid[pair[w]['id']] for w in (0, 2))
        paired.append(dict(query_id=key[0], language=key[1], split=pair[0]['split'], family=pair[0]['family'],
            t0_correct=a['metrics']['correct'], t2_correct=b['metrics']['correct'],
            t0_content_ce=sum(r['nll'] for r in a['tf']['targets'][:-1]) / (len(a['tf']['targets']) - 1),
            t2_content_ce=sum(r['nll'] for r in b['tf']['targets'][:-1]) / (len(b['tf']['targets']) - 1)))
    d = []
    for pair in frozen['d_pairs']:
        a, b = byid[pair['left']], byid[pair['right']]
        need(a['tf']['first_prefix']['d_other_logit'] is not None
             and b['tf']['first_prefix']['d_other_logit'] is not None, 'preselected offline D readout absent')
        d.append(dict(**pair, left_gap=a['tf']['first_prefix']['d_gap'], right_gap=b['tf']['first_prefix']['d_gap']))
    neutral = {c['problem']['query_id']: (c['split'], c['family'], c['group_id']) for c in cases}
    need(len(neutral) == 64, '64 neutral queries (not independent groups) required')
    parent_groups = []
    for split in ('train', 'test'):
        for family in data.FAMILIES:
            values = [v for v in neutral.values() if v[:2] == (split, family)]
            parent_groups.append(dict(split=split, family=family, neutral_queries=len(values),
                                      parent_groups=len({v[2] for v in values})))
    return dict(actual_answers=len(events), cells=output, paired=paired, d_status='APPLICABLE' if d else 'NOT_APPLICABLE',
        d_pairs=d, neutral_query_count=len(neutral), family_parent_group_counts=parent_groups,
        numerical_readback_scope=('scalar consistency and fixed-order aggregation only; exact vocabulary rank counts '
                                 'remain model-logit observations, not independently recomputed without full logits'),
        interpretation='exploratory repeated source cohort; no seed CI, new blind benchmark or automatic adoption')


def endpoint_identity(endpoint, projection):
    need(endpoint in ENDPOINTS, 'registered endpoint required before any checkpoint access')
    up = projection['upstream']
    if endpoint == 'parent':
        return dict(endpoint=endpoint, checkpoint=str(up.base.PARENT.relative_to(ROOT)),
            checkpoint_sha256=up.base.PARENT_SHA, core_sha256=up.base.PARENT_CORE)
    report = projection['training'][endpoint]['report']
    return dict(endpoint=endpoint, checkpoint=report['checkpoint'], checkpoint_sha256=report['checkpoint_sha256'],
                core_sha256=report['final_core_sha256'], train_report_sha256=projection['training'][endpoint]['report_sha256'])


def show(cases, events, frozen, endpoint):
    answers = {e['id']: e for e in events}; source = {c['id']: c for c in cases}
    for identity in frozen['display_ids']:
        case, event = source[identity], answers[identity]
        print('[QUESTION_CONTENT_ACTUAL_QUESTION_ANSWER] ' + json.dumps(dict(endpoint=endpoint,
            case_id=identity, question=case['messages'], answer=event['answer'],
            finish=event['generation']['finish_reason'], correct=event['metrics']['correct'],
            selection_sha256=frozen['display_sha256']), ensure_ascii=False), flush=True)


def evaluate(endpoint):
    frozen, cases, projection = read_prepared()
    up = projection['upstream']; identity = endpoint_identity(endpoint, projection)
    path = safe(ROOT / identity['checkpoint'])
    need(digest(path) == identity['checkpoint_sha256'], 'exact checkpoint bytes changed before load')
    local = safe(LOCAL / ('evaluate_' + endpoint)); target = safe(EVIDENCE / ('evaluate_' + endpoint))
    if local.exists() or target.exists():
        raise FileExistsError('old complete/partial endpoint evidence preserved')
    from scripts.p106b_gate_runtime import idle_before_gpu
    idle_before_gpu(); authority()
    local.mkdir(parents=True, exist_ok=False); target.mkdir(parents=True, exist_ok=False)
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    from tinylm.infer.generate import _strip
    torch, model, cfg, tok, _ = up.base.load_parent()
    if endpoint != 'parent':
        saved = torch.load(path, map_location='cpu', weights_only=True)
        need(saved.get('question_transfer_course') == dict(tag=up.TAG, arm=endpoint, epochs=4)
             and saved.get('step') == 384 and saved.get('tokenizer_sha256') == up.natural.TOK_SHA
             and saved.get('cfg') == asdict(cfg), 'exact child cfg/weight-only lineage differs')
        model.load_state_dict(_strip(saved['model']), strict=True); del saved
    before = state_fingerprint(model)
    need(before == identity['core_sha256'], 'loaded endpoint body differs')
    model = model.cuda(); model.eval(); model.freeze_quant()
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    writer = ShardWriter(local, 'answers', limit=19_999_999); began = time.perf_counter()
    lineage = dict(tag=TAG, **identity, corpus_report_sha256=digest(CORPUS / 'report.json'))
    try:
        with torch.no_grad():
            events = evaluate_cases(cases, frozen,
                lambda case, other: tf_score(model, tok, case, frozen, other),
                lambda messages: up.emit64(model, cfg, tok, messages), lineage,
                writer.append, check_authority=authority)
        summary = recount(events, cases, frozen, tok=tok, lineage=lineage)
        model.clear_quant(); model.eval()
        after = state_fingerprint(model)
        need(before == after and digest(path) == identity['checkpoint_sha256'], 'body/checkpoint changed during inference')
        manifest = writer.close(lineage=lineage)
        result = dict(info(), status='QUESTION_CONTENT_ACTUAL_COMPLETE', endpoint=endpoint,
            code_sha256=code_pins(up), source_binding=frozen['source_binding'],
            activity_prepare=projection['activity_prepare'],
            cases_sha256=frozen['cases_sha256'], corpus_report_sha256=lineage['corpus_report_sha256'],
            lineage=lineage, core_before=before, core_after=after, manifest=manifest,
            manifest_sha256=digest(local / 'answers_shards_manifest.json'), summary=summary,
            model_training=False, weights_changed=False, whole_seconds=time.perf_counter() - began,
            tf_scope='final FP32-MATH normal full-sequence logits, not logged BF16 training CE')
        write(target / 'report.json', result)
        show(cases, events, frozen, endpoint)
    finally:
        if writer._file is not None:
            writer._file.flush(); writer._file.close(); writer._file = None
        model.clear_quant(); model.eval(); del model; gc.collect(); torch.cuda.empty_cache()
    return 0


def readback():
    frozen, cases, projection = read_prepared()
    tok = tokenizer(); models = {}
    for endpoint in ENDPOINTS:
        activity = completed_activity('evaluate', endpoint, digest(CORPUS / 'report.json'),
                                      up=projection['upstream'])
        identity = endpoint_identity(endpoint, projection)
        directory = LOCAL / ('evaluate_' + endpoint)
        report = required(EVIDENCE / ('evaluate_' + endpoint) / 'report.json')
        lineage = dict(tag=TAG, **identity, corpus_report_sha256=digest(CORPUS / 'report.json'))
        need(report.get('status') == 'QUESTION_CONTENT_ACTUAL_COMPLETE'
             and all(report.get(k) == v for k, v in info().items())
             and report.get('endpoint') == endpoint
             and report.get('lineage') == lineage and report.get('code_sha256') == code_pins(projection['upstream'])
             and report.get('source_binding') == frozen['source_binding']
             and report.get('corpus_report_sha256') == lineage['corpus_report_sha256']
             and report.get('cases_sha256') == frozen['cases_sha256']
             and report.get('activity_prepare') == projection['activity_prepare']
             and report.get('manifest', {}).get('lineage') == lineage
             and report.get('core_before') == identity['core_sha256'] == report.get('core_after')
             and report.get('model_training') is False and report.get('weights_changed') is False,
             'complete exact endpoint evaluation required')
        need(digest(ROOT / identity['checkpoint']) == identity['checkpoint_sha256']
             and digest(directory / 'answers_shards_manifest.json') == report['manifest_sha256'],
             'endpoint checkpoint/raw manifest bytes changed')
        events = read_rows(directory, report['manifest'], 'answers', EXPECTED_CASES)
        summary = recount(events, cases, frozen, tok=tok, lineage=lineage)
        need(summary == report['summary'], 'independent scalar/answer recount differs')
        models[endpoint] = dict(report_sha256=digest(EVIDENCE / ('evaluate_' + endpoint) / 'report.json'),
                                activity_evaluate=activity, lineage=lineage, summary=summary)
        show(cases, events, frozen, endpoint)
    result = dict(info(), status='QUESTION_CONTENT_READBACK_COMPLETE', actual_answers=768,
        errors=0, cases_sha256=frozen['cases_sha256'], models=models,
        new_model_calls=0, source_scope=PROJECTION_SCOPE)
    write(EVIDENCE / 'readback.json', result)
    print('[QUESTION_CONTENT_READBACK]768 actual first answers; no automatic adoption', flush=True)
    return 0


def run_worker(mode, endpoint, max_wall_sec):
    need(mode in MODES and type(max_wall_sec) is int and 60 <= max_wall_sec <= LIMITS[mode],
         'bounded registered worker mode required')
    authority(max_wall_sec)
    if mode == 'source':
        with wall_context(max_wall_sec):
            read_projection()
        print('[QUESTION_CONTENT_SOURCE] exact frozen encoded projection; model0', flush=True); return 0
    if mode == 'preflight':
        with wall_context(max_wall_sec):
            read_prepared()
        print('[QUESTION_CONTENT_PREFLIGHT] complete frozen diagnostic verified; model0', flush=True); return 0
    path = activity_path(mode, endpoint)
    if path.exists():
        raise FileExistsError('old worker activity preserved')
    began = time.perf_counter(); started = datetime.now(timezone.utc)
    code = None; status = 'NOT_RUN'
    try:
        with wall_context(max_wall_sec):
            if mode == 'prepare':
                code = prepare()
            elif mode == 'evaluate':
                code = evaluate(endpoint)
            elif mode == 'readback':
                code = readback()
            else:
                raise ValueError('known actual worker mode required')
        status = 'COMPLETE' if code == 0 else 'ERROR'
    except KeyboardInterrupt:
        code = 130; status = 'INTERRUPTED'; raise
    except Pending:
        code = 8; status = 'HOLD'; raise
    except BaseException:
        code = 9; status = 'TOOL_ERROR'; raise
    finally:
        corpus_report = safe(CORPUS / 'report.json')
        pins = code_pins(upstream())
        corpus_sha256 = digest(corpus_report) if corpus_report.is_file() else None
        elapsed = time.perf_counter() - began; recorded = datetime.now(timezone.utc)
        bounded = (0 <= elapsed <= max_wall_sec and started <= recorded
            and (recorded - started).total_seconds() <= max_wall_sec
            and recorded <= END - timedelta(seconds=RECORD_RESERVE))
        if status == 'COMPLETE' and not bounded:
            code = 8; status = 'HOLD'
        write(path, dict(info(), mode=mode, endpoint=endpoint, returncode=code,
            status=status, complete=code == 0, seconds=elapsed,
            code_sha256=pins,
            requested_limit=max_wall_sec, started_at=started.isoformat(), recorded_at=recorded.isoformat(),
            within_requested_time_and_authority=bounded,
            corpus_report_sha256=corpus_sha256,
            scope=('inner worker/projection/cleanup through final receipt assembly; final receipt I/O, '
                   'regression/wrapper and independent OS-exit authentication excluded')))
    return code


def wall_context(seconds):
    from scripts.p106b_gate_runtime import wall_limit
    return wall_limit(seconds)


def phase_commands(mode, endpoint=None, max_wall_sec=None):
    need(mode in MODES and ((mode == 'evaluate') == (endpoint in ENDPOINTS)), 'exact mode/endpoint selection required')
    need(endpoint is None or mode == 'evaluate', 'unused endpoint forbidden')
    limit = LIMITS[mode] if max_wall_sec is None else max_wall_sec
    need(type(limit) is int and 60 <= limit <= LIMITS[mode], 'declared worker limit must be 60 through mode cap')
    py = [sys.executable, '-B', '-X', 'utf8']
    driver = py + ['scripts/diag_p106b_question_content_probe.py']
    actual = driver + ['--mode', mode, '--max-wall-sec', str(limit), '--worker', '--execute']
    if endpoint is not None:
        actual += ['--endpoint', endpoint]
    prior = 'source' if mode in ('source', 'prepare') else 'preflight'
    preflight = driver + ['--mode', prior, '--max-wall-sec', '300', '--worker', '--execute']
    if mode == 'source':
        preflight[-1] = '--check-only'
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_question_content_probe', '-v']),
            ('PREFLIGHT', preflight), ('EXECUTE', actual)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, required=True)
    parser.add_argument('--endpoint', choices=ENDPOINTS)
    parser.add_argument('--max-wall-sec', type=int)
    parser.add_argument('--worker', action='store_true')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        phases = phase_commands(args.mode, args.endpoint, args.max_wall_sec)
        limit = LIMITS[args.mode] if args.max_wall_sec is None else args.max_wall_sec
        if args.check_only:
            print('[QUESTION_CONTENT_CHECK_ONLY] ' + json.dumps(info(), sort_keys=True), flush=True); return 0
        if args.worker:
            return run_worker(args.mode, args.endpoint, limit)
        def launch(command):
            print('[PHASE_COMMAND] ' + json.dumps(command), flush=True)
            bound = int(command[command.index('--max-wall-sec') + 1]) if '--max-wall-sec' in command else 300
            try:
                return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, timeout=bound).returncode
            except subprocess.TimeoutExpired:
                return 9
        return pipeline(phases, launch, lambda line: print(line, flush=True),
            experiment='P106B_QUESTION_CONTENT_' + args.mode + '_' + str(args.endpoint or 'all'))['returncode']
    except Pending as exc:
        print('[QUESTION_CONTENT_HOLD8] ' + str(exc), flush=True); return 8
    except KeyboardInterrupt:
        print('[QUESTION_CONTENT_INTERRUPTED130]', flush=True); return 130
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError) as exc:
        print('[QUESTION_CONTENT_TOOL_ERROR9] ' + type(exc).__name__ + ': ' + str(exc), flush=True); return 9


if __name__ == '__main__':
    raise SystemExit(main())
