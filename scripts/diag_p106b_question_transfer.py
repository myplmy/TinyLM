#!/usr/bin/env python3
"""Isolated, write-once question wording x position study.

Check-only reads code, not data or models. Public execute runs regression,
source preflight and one bounded worker. Structural correctness is not broad
intelligence. Existing research controllers, datasets and checkpoints stay put.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import gc
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_relation_bind as base
from scripts import diag_p106b_subject_role as original
from scripts import diag_p106d_history_scope as history
from scripts import p106b_night_qa_data as natural
from scripts import p106b_question_transfer_data as data
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_stage_receipt import pipeline

TAG = 'p106b_question_transfer_v1_s1337'
SCHEMA = 'P106B_QUESTION_TRANSFER_V1'
ARMS = ('fixed_last', 'varied_last', 'fixed_balanced', 'varied_balanced')
ENDPOINTS = ('parent', *ARMS)
MODES = ('source', 'prepare', 'preflight', 'cost', 'budget', 'train', 'evaluate', 'readback')
LOCAL = ROOT / 'test_result/evidence/local' / TAG
CORPUS = LOCAL / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
CONTEXT, MAX_NEW, ROWS, UPDATES = 1024, 64, 12288, 384
EXPECTED_ANSWERS = 1694
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
EVAL_RESERVE, RECORD_RESERVE, ACTIVE_LIMIT = 7200, 3600, 28800
TRAIN_STOP = END - timedelta(seconds=EVAL_RESERVE + RECORD_RESERVE)
OWN_CODE = ('scripts/p106b_question_transfer_data.py', 'scripts/test_p106b_question_transfer_data.py',
            'scripts/diag_p106b_question_transfer.py', 'scripts/test_p106b_question_transfer.py')
CODE = tuple(sorted(set((*OWN_CODE, *original.CODE, *history.OWN_CODE,
    'scripts/p106b_context_quality.py', 'scripts/p106b_relation_fields.py',
    'tinylm/data/sft.py', 'scripts/p106b_stage_receipt.py'))))
safe, digest, sha, required, write = base.safe, natural.digest, natural.sha, base.required, base.write
Pending = base.PrerequisitePending


class BudgetExclusion(ValueError):
    """One complete source exceeds declared token budgets, not a mask defect."""


def info():
    codes = {p: digest(safe(ROOT / p)) if (ROOT / p).is_file() else 'NOT_CREATED' for p in CODE}
    return dict(schema=SCHEMA, tag=TAG, code_sha256=codes,
        code_complete=all(h != 'NOT_CREATED' for h in codes.values()), arms=list(ARMS),
        parent=str(base.PARENT.relative_to(ROOT)), parent_sha256=base.PARENT_SHA,
        expected_parent_core_sha256=base.PARENT_CORE, tokenizer_sha256=natural.TOK_SHA,
        micro_bs=8, accum=16, seq=CONTEXT, grad_checkpoint=True, compile='default',
        seed=1337, epochs=4, training_updates_per_arm=UPDATES, rows_per_pass=ROWS,
        adam_lr=5e-5, muon_lr=2e-4, all_group_weight_decay=0., grad_clip=1.,
        fresh_optimizer=True, schedule='constant', mtp=False, teacher_calls=0,
        native_targets_per_update=8192, native_windows=3072,
        native_access='INDEXED_TRAIN_ONLY',
        native_train_file=str((base.NATIVE / 'train.bin').relative_to(ROOT)),
        native_train_sha256=base.NATIVE_TRAIN_SHA, native_val_sha256=base.NATIVE_VAL_SHA,
        expected_answers_per_endpoint=EXPECTED_ANSWERS, max_new=MAX_NEW,
        generation_protocol='FP32_MATH_GREEDY0_TOPK1_KV_ON_MTP_OFF_AUTHENTICATED_TERMINAL64',
        authority_end_utc=END.isoformat(), training_stop_utc=TRAIN_STOP.isoformat(),
        active_limit_seconds=ACTIVE_LIMIT, evaluation_reserve_seconds=EVAL_RESERVE,
        record_reserve_seconds=RECORD_RESERVE, formal_train_ready=False,
        automatic_adoption=False, broad_intelligence='NOT_ESTABLISHED')


def authority(training=False, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None:
        raise ValueError('timezone-aware authority time required')
    remaining = ((TRAIN_STOP if training else END) - now).total_seconds()
    if not math.isfinite(remaining) or remaining <= 0:
        raise Pending('current authority or reserved training cutoff ended')
    return remaining


def finite(value, positive=False):
    return type(value) in (float, int) and math.isfinite(value) and (not positive or value > 0)


def normalized_assistant_loss(total, denominator):
    if type(denominator) is not int or denominator <= 0:
        raise ValueError('whole-update positive assistant token denominator required')
    return total / denominator


def read_rows(directory, manifest, stem, count):
    """Reject wrong stems and paths before any payload hashing or opening."""
    safe(directory)
    specs = manifest.get('shards')
    if type(count) is not int or count <= 0 or manifest.get('rows') != count or not isinstance(specs, list) or not specs:
        raise ValueError('explicit full nonempty shard population required')
    for i, spec in enumerate(specs):
        if (spec.get('path') != f'{stem}_{i:06d}.jsonl' or type(spec.get('bytes')) is not int
                or not 0 < spec['bytes'] < 20_000_000):
            raise ValueError('ordered exact source stem and below20MB row shards required')
    for spec in specs:
        safe(directory / spec['path'])
    if required(directory / (stem + '_shards_manifest.json')) != manifest:
        raise ValueError('declared manifest differs from disk')
    verify(directory, manifest)
    rows = [json.loads(line) for spec in specs for line in
            (directory / spec['path']).read_text(encoding='utf-8').splitlines()]
    if len(rows) != count:
        raise ValueError('row denominator differs')
    return rows


def text(message):
    return natural.text(message)


def calculation(op, a, b):
    if op not in ('+', '-', '*') or type(a) is not int or type(b) is not int:
        raise ValueError('declared signed integer addition/subtraction required')
    return (op, *sorted((a, b))) if op in ('+', '*') else (op, a, b)


def replay_calculations(row):
    """Only the exact registered code producer's arithmetic grammars."""
    meta = row.get('meta', {})
    if meta.get('kind') not in ('arithmetic', 'update'):
        return []
    if meta.get('generation_version') != 'P106B_VISIBLE_CONTEXT_CLARIFY_V1':
        raise ValueError('unknown arithmetic producer; do not infer semantics')
    lang = meta['language']; questions = [text(m) for m in row['messages'] if m['role'] == 'user']
    if meta['kind'] == 'arithmetic':
        pattern = (r'(-?\d+)([+-])(-?\d+)의 계산 결과를 정수 하나로만 답하세요\.' if lang == 'ko' else
                   r'Calculate (-?\d+)([+-])(-?\d+)\. Reply with only one integer\.')
    else:
        pattern = (r'(-?\d+)\+(-?\d+)의 값을 정수 하나로만 답하세요\.' if lang == 'ko' else
                   r'Give (-?\d+)\+(-?\d+) as one integer only\.')
    m = re.fullmatch(pattern, questions[0])
    if m is None:
        raise ValueError('registered replay calculation grammar changed')
    if meta['kind'] == 'arithmetic':
        a, op, b = int(m[1]), m[2], int(m[3])
    else:
        a, op, b = int(m[1]), '+', int(m[2])
    result = [calculation(op, a, b)]
    if meta['kind'] == 'update':
        pattern = (r'같은 계산에서 두 번째 수 (-?\d+)를 (-?\d+)로 바꿨습니다\. 바뀐 결과만 답하세요\.' if lang == 'ko' else
                   r'In that calculation, replace the second number (-?\d+) with (-?\d+)\. Give only the updated result\.')
        n = re.fullmatch(pattern, questions[1])
        if n is None or int(n[1]) != b:
            raise ValueError('registered update calculation grammar changed')
        result.append(calculation('+', a, int(n[2])))
    return result


def source_inputs():
    source, rows = base.old_source()
    if len(rows['train']) != 8192 or len(rows['replay']) != 4096:
        raise ValueError('existing exact natural/replay source required')
    d_report, probes, _ = history.read_prepared()
    blocked = {calculation('+', 1, 1), calculation('+', 2, 2)}
    for i in range(12):
        blocked.add(calculation('+', i + 2, (i * 7 + 3) % 17 + 1))
    for row in rows['replay']:
        blocked.update(replay_calculations(row))
    for probe in probes:
        if probe['family'] == 'arithmetic':
            for p in (probe['initial_payload'], probe['current_payload']):
                blocked.add(calculation(p['op'], p['a'], p['b']))
    declarations = dict(arithmetic=[list(v) for v in sorted(blocked)],
        boolean_name_pairs=[list(v) for v in itertools.combinations('ABCD', 2)],
        format_literals=sorted({str(p['neutral_definition']['value']) for p in probes if p['family'] == 'format'}),
        lookup_parent_signatures=[])
    binding = dict(natural_source_manifests_sha256=sha(source['manifests']),
        replay_rows_sha256=sha(rows['replay']), natural_train_roots_sha256=sha([p['root'] for p in rows['train']]),
        history_cpu_report_sha256=digest(history.CORPUS / 'report.json'),
        history_probe_sha256=d_report['probes_sha256'], exclusions_sha256=sha(declarations),
        scope='known procedural monitors/replay and D initial/current; not whole parent pretraining',
        parser='exact registered producer grammar, not semantic phrase detection')
    return rows, declarations, binding


def natural_row(pair, position):
    if position not in ('CQ', 'QC'):
        raise ValueError('one question in one declared position required')
    lang = pair['language']
    instruction = ('자료를 읽고 질문의 답만 짧게 쓰세요.' if lang == 'ko' else
                   'Read the reference and give only the short answer.')
    context_label, question_label = ('자료:\n', '질문:\n') if lang == 'ko' else ('Reference:\n', 'Question:\n')
    pieces = {'C': context_label + pair['context'], 'Q': question_label + pair['question']}
    user = instruction + '\n' + '\n'.join(pieces[c] for c in position)
    return dict(messages=[dict(role='user', content=user),
                          dict(role='assistant', content=pair['answers'][0]['text'])],
                meta=dict(kind='question_transfer_natural', language=lang, source_split=pair['split'],
                    parent_concept_id=pair['root'], article_id=pair['article_id'],
                    original_source_path=pair['source_path'], original_source_sha256=pair['source_sha256'],
                    original_question_sha256=sha(pair['question']), original_context_sha256=sha(pair['context']),
                    position=position, supervised_assistant_turns=[1], teacher_calls=0,
                    semantic_truth='ORIGINAL_SOURCE_SPAN_NOT_FULL_SEMANTIC_REVIEW'))


def encode_row(row, tok):
    from tinylm.chat.canonical import normalize, validate
    from tinylm.chat.serialize import serialize
    from tinylm.train.mtp_sft import encode_record
    canonical = validate(normalize(row))
    record = encode_record(canonical, tok, context=CONTEXT)
    prompt = serialize(dict(messages=canonical['messages'][:1]), 'chatml', add_generation_prompt=True)
    prompt_ids = tok.encode(prompt).ids
    positions = [i for i, value in enumerate(record.y) if value != -100]
    target = [record.y[i] for i in positions]
    if len(target) > MAX_NEW or len(prompt_ids) + MAX_NEW > CONTEXT:
        raise BudgetExclusion('complete source does not fit declared prompt/answer budget')
    if (not target or target[-1] != tok.token_to_id('<|im_end|>') or positions[0] != len(prompt_ids) - 1
            or record.x[:len(prompt_ids)] != prompt_ids):
        raise ValueError('complete prompt/answer64/EOT/causal-first-token contract')
    return record, dict(row_sha256=sha(canonical), prompt_sha256=sha(prompt),
        prompt_ids_sha256=sha(prompt_ids), prompt_tokens=len(prompt_ids),
        target_ids_sha256=sha(target), assistant_targets=len(target),
        eot_targets=target.count(tok.token_to_id('<|im_end|>')))


def wire(record, identity, lane, language, parent, evidence=None):
    return dict(id=identity, lane=lane, language=language, parent_group_id=parent,
        x=record.x, y=record.y, segments=record.segments, x_tokens=record.x_tokens,
        assistant_targets=record.targets, encoding=evidence,
        record_sha256=sha(dict(x=record.x, y=record.y, segments=record.segments)))


def unwire(value):
    from tinylm.train.mtp_sft import Record
    if (set(value) != {'id', 'lane', 'language', 'parent_group_id', 'x', 'y', 'segments', 'x_tokens',
                       'assistant_targets', 'encoding', 'record_sha256'}
            or not isinstance(value['x'], list) or not 1 <= len(value['x']) <= CONTEXT
            or len(value['x']) != len(value['y']) or len(value['x']) != len(value['segments'])
            or any(type(x) is not int or not 0 <= x < 32768 for x in value['x'])
            or any(type(y) is not int or (y != -100 and not 0 <= y < 32768) for y in value['y'])
            or any(type(s) is not int or s < 0 for s in value['segments'])):
        raise ValueError('strict complete encoded record wire contract')
    r = Record(value['x'], value['y'], value['segments'])
    if (r.x_tokens != value['x_tokens'] or r.targets != value['assistant_targets'] or r.targets <= 0
            or sha(dict(x=r.x, y=r.y, segments=r.segments)) != value['record_sha256']
            or any((y == -100) != (s == 0) for y, s in zip(r.y, r.segments))):
        raise ValueError('encoded targets/segments/record fingerprint differ')
    return r


def schedule(epoch, count=ROWS):
    if type(epoch) is not int or not 0 <= epoch < 4 or count != ROWS:
        raise ValueError('exact four-pass12288 schedule required')
    indices = list(range(count)); random.Random(20261019 + epoch).shuffle(indices)
    return [[indices[start + m * 8:start + (m + 1) * 8] for m in range(16)]
            for start in range(0, count, 128)]


def natural_layout(arm, epoch, rotation):
    if arm not in ARMS or type(epoch) is not int or not 0 <= epoch < 4 or type(rotation) is not int or not 0 <= rotation < 4:
        raise ValueError('natural layout uses same declared arm/epoch/rotation')
    return 'QC' if arm.endswith('_balanced') and (epoch + rotation) % 2 else 'CQ'


def choose_natural(rows, tok):
    chosen = []
    for lang in ('ko', 'en'):
        eligible = []
        for p in sorted((v for v in rows['train'] if v['language'] == lang), key=lambda p: sha([TAG, p['root']])):
            try:
                a, ae = encode_row(natural_row(p, 'CQ'), tok)
                b, be = encode_row(natural_row(p, 'QC'), tok)
            except BudgetExclusion:
                continue
            if [v for v in a.y if v != -100] != [v for v in b.y if v != -100]:
                raise ValueError('natural position changed assistant target IDs')
            eligible.append(p)
        if len(eligible) < 2048:
            raise Pending('eligible natural question supply below2048/' + lang)
        for i, p in enumerate(eligible[:2048]):
            chosen.append(dict(p, transfer_rotation=i % 4))
    return chosen


def selected_natural_monitor(rows):
    result = []
    for lang in ('ko', 'en'):
        selected = sorted((p for p in rows['test'] if p['language'] == lang),
                          key=lambda p: sha([20261017, 'MONITOR', p['root']]))[:32]
        if len(selected) != 32:
            raise Pending('same32 natural monitor roots per language required')
        result.extend(selected)
    return result


def evaluation_cases(course, rows):
    selection = data.evaluation_problems(course); cases = []
    for split, styles in (('test', (0, 2)), ('train', (2, 3))):
        for p in selection[split]:
            for lang in ('ko', 'en'):
                for style in styles:
                    for pos in ('CQ', 'QC'):
                        row = data.render(p, lang, style, pos)
                        cases.append(dict(id=sha([TAG, split, p['query_id'], lang, style, pos]),
                            lane='coded', split=split, family=p['family'], language=lang,
                            problem=p, group_id=p['parent_group_id'], wording=style, position=pos,
                            messages=row['messages'][:1], gold=p['target_by_language'][lang]))
    for p in selected_natural_monitor(rows):
        for pos in ('CQ', 'QC'):
            cases.append(dict(id=sha([TAG, 'NATURAL_MONITOR', p['root'], pos]), lane='natural',
                split='old_test_monitor', family='natural', language=p['language'],
                group_id=p['article_id'], root=p['root'], wording='ORIGINAL', position=pos,
                messages=natural_row(p, pos)['messages'][:1], aliases=p['aliases'], gold=p['answers'][0]['text']))
    for lang in ('ko', 'en'):
        for i in range(12):
            a, b = i + 2, (i * 7 + 3) % 17 + 1
            q = f'{a}+{b}의 값은? 정수만 답하세요.' if lang == 'ko' else f'What is {a}+{b}? Answer only the integer.'
            cases.append(dict(id=sha([TAG, 'MATH_MONITOR', lang, i]), lane='canary', family='arithmetic',
                language=lang, group_id='math_' + str(i), messages=[dict(role='user', content=q)], gold=str(a + b)))
    questions = ('1+1은?', '2+2는?', 'A는 사과고 B는 당근이다 B는?',
        '문맥: 민수는 사과 3개, 영희는 사과 5개를 가지고 있습니다. 질문: 영희의 사과는 몇 개입니까? 답만 쓰세요.',
        '사과에 대해 알려줘', '농구란?')
    for i, q in enumerate(questions):
        cases.append(dict(id=sha([TAG, 'USER_SEEN', i]), lane='user_seen', family='user_seen',
            language='ko', group_id='user_seen_' + str(i), messages=[dict(role='user', content=q)],
            semantic_truth='NOT_AUTOMATICALLY_ADJUDICATED'))
    if len(cases) != EXPECTED_ANSWERS or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('full1694 unique preregistered responses required')
    return cases


def case_encoding(case, tok):
    from tinylm.chat.serialize import serialize
    prompt = serialize(dict(messages=case['messages']), 'chatml', add_generation_prompt=True)
    ids = tok.encode(prompt).ids
    if len(ids) + MAX_NEW > CONTEXT:
        raise ValueError('entire evaluation question exceeds1024-minus64')
    target_ids = None
    if 'gold' in case:
        row = dict(messages=case['messages'] + [dict(role='assistant', content=case['gold'])],
                   meta=dict(kind='question_transfer_eval_reference'))
        r, e = encode_row(row, tok); target_ids = [y for y in r.y if y != -100]
    return dict(prompt_sha256=sha(prompt), prompt_ids_sha256=sha(ids), prompt_tokens=len(ids),
                gold_target_ids_sha256=sha(target_ids) if target_ids is not None else None,
                gold_target_tokens=len(target_ids) if target_ids is not None else None)


def put(stem, values):
    writer = ShardWriter(CORPUS, stem, limit=19_999_999)
    for row in values:
        writer.append(row)
    manifest = writer.close(lineage=dict(tag=TAG, stem=stem))
    verify(CORPUS, manifest)
    return manifest


def prepare():
    import torch
    from tokenizers import Tokenizer
    from scripts.p106b_relation_fields import encode as encode_replay
    authority(training=True)
    if not info()['code_complete']:
        raise Pending('four independent source/test files must be complete')
    if safe(LOCAL).exists() or safe(EVIDENCE).exists():
        raise FileExistsError('old complete/partial question-transfer namespace preserved')
    rows, blocked, binding = source_inputs()
    if digest(natural.TOKENIZER) != natural.TOK_SHA or digest(base.PARENT) != base.PARENT_SHA:
        raise ValueError('pinned tokenizer/parent byte identity changed')
    for name, identity in (('train.bin', base.NATIVE_TRAIN_SHA), ('val.bin', base.NATIVE_VAL_SHA)):
        if digest(base.NATIVE / name) != identity:
            raise ValueError('immutable native cache changed')
    tok = Tokenizer.from_file(str(natural.TOKENIZER)); course = data.build_course(blocked=blocked)
    data.validate_course(course); anchors = choose_natural(rows, tok)
    replay = [wire(encode_replay(r, tok)[0], sha(r), 'replay', r['meta']['language'],
                   r['meta'].get('semantic_root_id', sha(r))) for r in rows['replay']]
    if len(anchors) != 4096 or len(replay) != 4096:
        raise ValueError('full natural4096/replay4096 required')
    cases = evaluation_cases(course, rows)
    for c in cases:
        c['encoding'] = case_encoding(c, tok)
    # Select display cases by source/IDs before model answers exist.
    display = []
    for lane in ('coded', 'natural', 'canary', 'user_seen'):
        group = [c for c in cases if c['lane'] == lane]
        if lane == 'coded':
            for family in data.FAMILIES:
                for lang in ('ko', 'en'):
                    for split in ('test', 'train'):
                        options = [c for c in group if c['family'] == family and c['language'] == lang and c['split'] == split]
                        display.append(min(options, key=lambda c: sha([TAG, 'DISPLAY', c['id']]))['id'])
        elif lane == 'user_seen':
            display.extend(c['id'] for c in group)
        else:
            for lang in ('ko', 'en'):
                display.extend(c['id'] for c in sorted((c for c in group if c['language'] == lang), key=lambda c: sha([TAG, 'DISPLAY', c['id']]))[:2])
    CORPUS.mkdir(parents=True, exist_ok=False); manifests = {}; summaries = {}; target_baseline = {}
    manifests['coded'] = put('coded', [dict(split=s, problem=p) for s in ('train', 'dev', 'test') for p in course[s]])
    manifests['cases'] = put('cases', cases)
    for arm in ARMS:
        summaries[arm] = []
        for epoch in range(4):
            current = []
            for p in course['train']:
                view = data.schedule_view(p, arm, epoch)
                for lang in ('ko', 'en'):
                    r, e = encode_row(data.render(p, lang, view['wording'], view['position']), tok)
                    current.append(wire(r, sha(['CODED', p['query_id'], lang]), 'coded', lang, p['parent_group_id'], e))
            for p in anchors:
                pos = natural_layout(arm, epoch, p['transfer_rotation'])
                r, e = encode_row(natural_row(p, pos), tok)
                current.append(wire(r, sha(['NATURAL', p['root']]), 'natural', p['language'], p['article_id'], e))
            current.extend(replay)
            if len(current) != ROWS or len({v['id'] for v in current}) != ROWS:
                raise ValueError('exact unique12288 per-pass rows required')
            target_identity = sha([[v['id'], [y for y in v['y'] if y != -100], v['segments']] for v in current])
            # Segment positions change with prompt length; compare supervised IDs and turn owners, not masked prompt offsets.
            supervised_identity = sha([[v['id'], [(y, s) for y, s in zip(v['y'], v['segments']) if y != -100]] for v in current])
            if target_baseline and supervised_identity != target_baseline['sha256']:
                raise ValueError('arm/epoch changed assistant target IDs or supervised-turn owners')
            target_baseline = dict(sha256=supervised_identity)
            stem = arm + '_e' + str(epoch + 1); manifests[stem] = put(stem, current)
            counts = Counter(positive_rows=ROWS, x_tokens=sum(v['x_tokens'] for v in current),
                assistant_targets=sum(v['assistant_targets'] for v in current),
                eot_targets=sum(v['y'].count(4) for v in current),
                content_targets=sum(v['assistant_targets'] - v['y'].count(4) for v in current))
            batches = schedule(epoch)
            words = [sum(current[i]['assistant_targets'] for m in g for i in m) for g in batches]
            if len(batches) != 96 or sorted(i for g in batches for m in g for i in m) != list(range(ROWS)):
                raise ValueError('schedule did not use every source exactly once per pass')
            summaries[arm].append(dict(epoch=epoch + 1, counts=dict(counts),
                record_order_sha256=sha([v['id'] for v in current]),
                target_alignment_sha256=supervised_identity, full_masked_wire_sha256=target_identity,
                schedule_sha256=sha(batches), update_target_denominators=words,
                lane_targets={lane:sum(v['assistant_targets'] for v in current if v['lane']==lane) for lane in ('coded','natural','replay')},
                language_rows=dict(Counter(v['language'] for v in current))))
    reference = summaries[ARMS[0]]
    for arm in ARMS:
        for left, right in zip(reference, summaries[arm]):
            for k in ('record_order_sha256', 'target_alignment_sha256', 'schedule_sha256', 'update_target_denominators', 'lane_targets', 'language_rows'):
                if left[k] != right[k]:
                    raise ValueError('same source/target/update normalization differs:' + k)
    dev = []
    for p in course['dev']:
        for lang in ('ko', 'en'):
            r, e = encode_row(data.render(p, lang, 0, 'CQ'), tok)
            dev.append(wire(r, sha(['DEV', p['query_id'], lang]), 'coded', lang, p['parent_group_id'], e))
    manifests['dev'] = put('dev', dev)
    offsets = original.native_offsets(count=UPDATES * 8, seed=20261019)
    result = dict(info(), status='QUESTION_TRANSFER_CPU_VERIFIED', source_binding=binding,
        blocked=blocked, course_sha256=sha(course), manifests=manifests, exposure=summaries,
        native_train_offsets=offsets, native_train_offsets_sha256=sha(offsets),
        cases_sha256=sha(cases), display_ids=display, display_selection_sha256=sha(display),
        supervised_targets_sha256=target_baseline['sha256'],
        natural_selected_roots_sha256=sha([p['root'] for p in anchors]),
        coded_counts={s:dict(Counter(p['family'] for p in course[s])) for s in ('train','dev','test')},
        code_course_summary=course['metadata']['summary'], actual_source_exclusions_verified=True,
        factual_scope='code instances and old public annotations; not new75Mknowledge',
        model_loaded=False, optimizer_updates=0, checkpoints_written=0, cuda_initialized=torch.cuda.is_initialized())
    if result['cuda_initialized']:
        raise ValueError('CPU preparation initialized CUDA')
    write(CORPUS / 'report.json', result)
    public = {k:v for k,v in result.items() if k not in ('manifests','native_train_offsets','blocked')}
    public['corpus_report_sha256'] = digest(CORPUS / 'report.json')
    write(EVIDENCE / 'cpu_contract.json', public)
    print('[QUESTION_TRANSFER_CPU] full source, group split, target, schedule and64-budget verified; model/GPU NOT_RUN', flush=True)
    return 0


def read_prepared():
    report = base.stage_report(CORPUS / 'report.json')
    if report.get('status') != 'QUESTION_TRANSFER_CPU_VERIFIED' or any(report.get(k) != v for k,v in info().items()):
        raise ValueError('frozen independent code/recipe/corpus changed')
    rows, blocked, binding = source_inputs()
    if blocked != report['blocked'] or binding != report['source_binding']:
        raise ValueError('old source or exact exclusion declaration changed')
    if digest(natural.TOKENIZER) != natural.TOK_SHA or digest(base.PARENT) != base.PARENT_SHA:
        raise ValueError('parent/tokenizer bytes changed')
    coded = read_rows(CORPUS, report['manifests']['coded'], 'coded', 2432)
    course = data.build_course(blocked=blocked); data.validate_course(course)
    if (sha(course) != report['course_sha256']
            or coded != [dict(split=s, problem=p) for s in ('train','dev','test') for p in course[s]]):
        raise ValueError('code-owned state/gold/group reconstruction differs')
    if report['native_train_offsets'] != original.native_offsets(count=UPDATES * 8, seed=20261019):
        raise ValueError('shared native TRAIN offset vector changed')
    public = {k:v for k,v in report.items() if k not in ('manifests','native_train_offsets','blocked')}
    public['corpus_report_sha256'] = digest(CORPUS / 'report.json')
    if required(EVIDENCE / 'cpu_contract.json') != public:
        raise ValueError('public/source CPU binding changed')
    return report, rows, course


def records_for(frozen, arm, epoch):
    stem = arm + '_e' + str(epoch + 1)
    values = read_rows(CORPUS, frozen['manifests'][stem], stem, ROWS)
    records = [unwire(v) for v in values]
    receipt = frozen['exposure'][arm][epoch]
    if (sha([v['id'] for v in values]) != receipt['record_order_sha256']
            or sha([[v['id'], [(y,s) for y,s in zip(v['y'],v['segments']) if y != -100]] for v in values]) != receipt['target_alignment_sha256']
            or [sum(records[i].targets for m in g for i in m) for g in schedule(epoch)] != receipt['update_target_denominators']):
        raise ValueError('actual training consumer targets/order/whole-update denominators changed')
    return records


def checkpoint(arm):
    if arm not in ARMS:
        raise ValueError('registered new arm required')
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_question_transfer_' + TAG + '_' + arm + '.pt')


def spent_seconds():
    values = []
    if EVIDENCE.is_dir():
        for p in sorted(EVIDENCE.glob('activity_*.json')):
            r = read_activity(p)
            values.append(r['seconds'])
    return sum(values)


def read_activity(path, *, mode=None, arm=None, endpoint=None, completed=False):
    path=safe(path);r=required(path)
    keys={'schema','tag','key','mode','arm','endpoint','seconds','returncode','complete','limit',
          'recorded_at','scope','code_sha256','corpus_sha256'}
    if (not isinstance(r,dict) or set(r)!=keys or r.get('schema')!=SCHEMA or r.get('tag')!=TAG
            or r.get('mode') not in ('prepare','cost','train','evaluate','readback')
            or not finite(r.get('seconds'),True) or type(r.get('limit')) is not int or not 60<=r['limit']<=7200
            or type(r.get('complete')) is not bool
            or not (r.get('returncode') is None or type(r.get('returncode')) is int and r['returncode']==0)
            or r['complete'] is not (r['returncode']==0) or r.get('code_sha256')!=info()['code_sha256']
            or r.get('scope')!='actual worker wall including input verification; regression/preflight wrapper excluded'):
        raise ValueError('complete typed activity schema/code/status required; no zero imputation')
    phases=phase_commands(r['mode'],r['arm'],r['endpoint'],r['limit'])
    if not phases or r['key']!=activity_key(r['mode'],r['arm'],r['endpoint']) or path.name!='activity_'+r['key']+'.json':
        raise ValueError('activity filename/mode/selectors differ')
    stamp=datetime.fromisoformat(r['recorded_at'])
    if stamp.tzinfo is None:
        raise ValueError('activity completion timezone required')
    if r['complete'] and (not (CORPUS/'report.json').is_file() or r['corpus_sha256']!=digest(CORPUS/'report.json')):
        raise ValueError('closed activity/current corpus binding differs')
    if mode is not None and (r['mode'],r['arm'],r['endpoint'])!=(mode,arm,endpoint):
        raise ValueError('activity belongs to another stage')
    if completed and not r['complete']:
        raise Pending('interrupted or failed activity retained; not completed cost/train evidence')
    return r


def budget():
    frozen, _, _ = read_prepared(); estimates = {}; costs = {}
    for arm in ARMS:
        r = base.stage_report(EVIDENCE / ('cost_' + arm) / 'report.json')
        verify_training(r, arm, frozen, cost=True)
        read_activity(EVIDENCE/('activity_cost_'+arm+'.json'),mode='cost',arm=arm,completed=True)
        t = r['step_seconds']
        estimate = t[0] + sum(t[1:]) / 7 * (UPDATES - 1) * 1.25 + 240.
        done_path = EVIDENCE / ('train_' + arm) / 'report.json'
        if done_path.exists():
            done = required(done_path); verify_training(done, arm, frozen, cost=False)
            read_activity(EVIDENCE/('activity_train_'+arm+'.json'),mode='train',arm=arm,completed=True)
            estimates[arm] = 0.
        else:
            estimates[arm] = estimate
        costs[arm] = dict(first=t[0], warm7_mean=sum(t[1:])/7, estimated_training_seconds=estimate)
    spent = spent_seconds(); total = spent + sum(estimates.values()) + EVAL_RESERVE + RECORD_RESERVE
    if total > ACTIVE_LIMIT or sum(estimates.values()) > authority(training=True):
        raise Pending('new complete four-arm budget exceeds8h or reserved authority window')
    return dict(spent_actual=spent, estimated_remaining_training=estimates, costs=costs,
        evaluation_reserve_seconds=EVAL_RESERVE, record_reserve_seconds=RECORD_RESERVE,
        total_reserved_seconds=total, active_limit=ACTIVE_LIMIT, admission=True,
        prediction_not_measured_training=True)


def verify_training(report, arm, frozen, cost):
    if arm not in ARMS or type(cost) is not bool:
        raise ValueError('registered training identity required')
    n = 8 if cost else UPDATES
    if not cost and report.get('checkpoint') != str(checkpoint(arm).relative_to(ROOT)):
        raise ValueError('exact owned checkpoint path required before any checkpoint I/O')
    if (report.get('status') != ('COST8_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING')
            or report.get('arm') != arm or report.get('updates') != n
            or any(report.get(k)!=v for k,v in info().items() if k!='updates')
            or report.get('corpus_sha256') != digest(CORPUS / 'report.json')
            or report.get('initial_core_sha256') != base.PARENT_CORE
            or report.get('checkpoint_written') != (not cost)):
        raise ValueError('same independent code/source/parent/update completion required')
    original.validate_groups(report.get('actual_optimizer_groups'))
    if (not isinstance(report.get('event_manifest'),dict)
            or report['event_manifest'].get('lineage')!=dict(tag=TAG,arm=arm,cost=cost)
            or not isinstance(report.get('final_core_sha256'),str)
            or re.fullmatch('[0-9A-F]{64}',report['final_core_sha256']) is None):
        raise ValueError('training raw manifest/final body identity differs')
    directory = EVIDENCE / (('cost_' if cost else 'train_') + arm)
    events = read_rows(directory, report['event_manifest'], 'updates', n)
    if len(report.get('step_seconds', [])) != n or report['step_seconds'] != [e['step_seconds'] for e in events]:
        raise ValueError('complete actual timing cohort differs')
    for i,e in enumerate(events):
        epoch = i // 96; slot = i % 96
        if (e['update'] != i+1 or e['epoch'] != epoch+1
                or e['assistant_targets'] != frozen['exposure'][arm][epoch]['update_target_denominators'][slot]
                or e['native_targets'] != 8192
                or any(not finite(e[k]) for k in ('assistant_ce','native_ce','gradient_norm','step_seconds'))
                or not finite(e['step_seconds'], True)):
            raise ValueError('raw update/finite losses/whole-update target denominator differs')
    if (report['grad_max'] != max(e['gradient_norm'] for e in events)
            or report['clip_events'] != sum(e['gradient_norm'] > 1. for e in events)
            or report['totals']['assistant_targets'] != sum(e['assistant_targets'] for e in events)
            or report['totals']['native_targets'] != 8192*n
            or report['totals']['positive_rows'] != 128*n
            or report['totals']['x_tokens'] != sum(e['x_tokens'] for e in events)):
        raise ValueError('raw gradient/exposure sums differ')
    if not cost:
        expected = {k:sum(v['counts'][k] for v in frozen['exposure'][arm]) for k in ('x_tokens','assistant_targets','positive_rows')}
        if (any(report['totals'][k] != v for k,v in expected.items())
                or report['checkpoint'] != str(checkpoint(arm).relative_to(ROOT))
                or digest(checkpoint(arm)) != report['checkpoint_sha256']):
            raise ValueError('full384 source exposure/checkpoint identity differs')
    return events


def dev_probe(model, tok, frozen):
    import torch
    from tinylm.train import mtp_sft as core
    rows = read_rows(CORPUS, frozen['manifests']['dev'], 'dev', 384)
    records = [unwire(v) for v in rows]; total = 0.; targets = 0
    model.eval(); model.freeze_quant()
    try:
        with torch.no_grad():
            for start in range(0,len(records),8):
                batch = records[start:start+8]
                x,y,s = core.pad_records(batch,tok.token_to_id('<pad>'),'cuda',fixed_width=1024,batch_size=8)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    sums, counts = core.components(model,model(x,return_hidden=True),y,s,horizons=())
                total += float(sums[1]); targets += counts[1]
    finally:
        model.clear_quant(); model.train()
    if not finite(total) or targets != sum(r.targets for r in records):
        raise ValueError('DEV target/finite loss contract differs')
    return dict(ce=total/targets, assistant_targets=targets, records=384,
                precision='BF16_AUTO_HEAD_FP32', scope='code-owned T0CQ DEV CE, not free answers')


def train(arm, cost=False):
    import torch
    from tinylm.train import mtp_sft as core
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    from scripts.p106b_native_windows import reader
    from scripts.p106b_gate_runtime import idle_before_gpu
    frozen, _, _ = read_prepared(); authority(training=True)
    target = safe(EVIDENCE / (('cost_' if cost else 'train_')+arm))
    if target.exists() or (not cost and checkpoint(arm).exists()):
        raise FileExistsError('old complete/partial training preserved')
    reservation = None if cost else budget()
    for name,h in (('train.bin',base.NATIVE_TRAIN_SHA),('val.bin',base.NATIVE_VAL_SHA)):
        if digest(base.NATIVE/name) != h:
            raise ValueError('native TRAIN/VAL changed')
    idle_before_gpu(); authority(training=True); target.mkdir(parents=True,exist_ok=False)
    writer = ShardWriter(target,'updates',limit=19_999_999); began=time.perf_counter()
    torch, model, cfg, tok, initial = base.load_parent()
    if initial != base.PARENT_CORE or cfg.grad_checkpoint is not True or cfg.mtp_aux or cfg.max_seq_len!=1024:
        raise ValueError('fresh actual parent/ckptON/MTPoff/seq1024 required')
    windows=reader(ROOT,frozen)
    if len(windows)!=UPDATES*8:
        raise ValueError('all3072 same unique native windows required')
    model=model.cuda();torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.cuda.reset_peak_memory_stats()
    native_before=None if cost else base.native_probe(model)
    dev_before=None if cost else dev_probe(model,tok,frozen)
    os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106b_question_transfer_')
    forward=torch.compile(model,mode='default');adam,muon,groups=base.make_optimizers(model)
    original.validate_groups(groups)
    if not cost and groups!=required(EVIDENCE/('cost_'+arm)/'report.json')['actual_optimizer_groups']:
        raise ValueError('training actual optimizer groups differ from cost8')
    totals=Counter();times=[];events=[];progress=[];updates=0;gmax=0.;clips=0
    write(target/'start.json',dict(info(),arm=arm,cost=cost,reservation=reservation))
    for epoch in range(4):
        records=records_for(frozen,arm,epoch)
        for slot,group in enumerate(schedule(epoch)):
            authority(training=True);tick=time.perf_counter()
            denominator=sum(records[i].targets for micro in group for i in micro)
            if denominator!=frozen['exposure'][arm][epoch]['update_target_denominators'][slot] or denominator<=0:
                raise ValueError('whole-update assistant denominator differs')
            adam.zero_grad(set_to_none=True);muon.zero_grad(set_to_none=True)
            observed=0;ce_sum=torch.zeros((),device='cuda');x_count=0
            for micro in group:
                batch=[records[i] for i in micro]
                if len(batch)!=8:
                    raise ValueError('physical micro8 required')
                x,y,s=core.pad_records(batch,0,'cuda',fixed_width=1024,batch_size=8)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    sums,counts=core.components(model,forward(x,return_hidden=True),y,s,horizons=())
                    objective=normalized_assistant_loss(sums[1],denominator)
                if counts[1]!=sum(r.targets for r in batch) or not bool(torch.isfinite(objective)):
                    raise ValueError('micro numerator/finite CE contract differs')
                objective.backward();observed+=counts[1];ce_sum+=sums[1].detach();x_count+=sum(r.x_tokens for r in batch)
            if observed!=denominator:
                raise ValueError('actual assistant target sum differs')
            native_records=[core.Record(v[:-1].astype('int64').tolist(),v[1:].astype('int64').tolist(),[1]*1024)
                for v in windows[updates*8:(updates+1)*8]]
            nx,ny,ns=core.pad_records(native_records,0,'cuda',fixed_width=1024,batch_size=8)
            with torch.autocast('cuda',dtype=torch.bfloat16):
                sums,counts=core.components(model,forward(nx,return_hidden=True),ny,ns,horizons=())
                native_loss=sums[1]/8192
            if counts[1]!=8192 or not bool(torch.isfinite(native_loss)):
                raise ValueError('native complete8192 target denominator differs')
            native_loss.backward();grad=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
            if not bool(torch.isfinite(grad)):
                raise ValueError('nonfinite gradient')
            gmax=max(gmax,float(grad));clips+=int(grad>1.)
            adam.step();muon.step();updates+=1;torch.cuda.synchronize();times.append(time.perf_counter()-tick)
            totals.update(positive_rows=128,x_tokens=x_count,assistant_targets=observed,native_targets=8192)
            event=dict(update=updates,epoch=epoch+1,assistant_ce=float(ce_sum)/denominator,
                assistant_targets=denominator,x_tokens=x_count,native_ce=float(native_loss.detach()),native_targets=8192,
                gradient_norm=float(grad),clipped=bool(grad>1.),step_seconds=times[-1])
            writer.append(event);events.append(event)
            if updates<=8 or updates%32==0:
                print('[QUESTION_TRANSFER_UPDATE] '+json.dumps(dict(arm=arm,**event)),flush=True)
            if cost and updates==8:break
        if cost:break
        progress.append(dict(epoch=epoch+1,updates=updates,dev=dev_probe(model,tok,frozen),native=base.native_probe(model)))
    if updates!=(8 if cost else UPDATES):
        raise ValueError('planned complete update count differs')
    result=dict(info(),status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING',
        arm=arm,updates=updates,initial_core_sha256=initial,final_core_sha256=state_fingerprint(model),
        corpus_sha256=digest(CORPUS/'report.json'),totals=dict(totals),history=progress,
        dev_before=dev_before,native_before=native_before,grad_max=gmax,clip_events=clips,
        step_seconds=times,actual_optimizer_groups=groups,checkpoint_written=not cost,
        optimizer_saved=False,whole_seconds=time.perf_counter()-began,reservation=reservation,
        peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
        peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,memory_scope='torch allocator not whole device peak')
    if not cost:
        with safe(checkpoint(arm)).open('xb') as stream:
            torch.save(dict(model=model.state_dict(),cfg=asdict(cfg),step=updates,
                tokenizer_sha256=natural.TOK_SHA,optimizer_saved=False,
                question_transfer_course=dict(tag=TAG,arm=arm,epochs=4)),stream)
        result.update(checkpoint=str(checkpoint(arm).relative_to(ROOT)),checkpoint_sha256=digest(checkpoint(arm)))
    result['event_manifest']=writer.close(lineage=dict(tag=TAG,arm=arm,cost=cost))
    verify_training(result,arm,frozen,cost);write(target/'report.json',result)
    del model;gc.collect();torch.cuda.empty_cache()
    return 0


def emit64(model,cfg,tok,messages):
    """Same FP32 sampler, explicit64 budget; remove only authenticated final ID."""
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample
    from scripts.diag_p101a_mtp_parity import CaptureTokens,PrecisionForward
    prompt=serialize(dict(messages=messages),'chatml',add_generation_prompt=True);prefix=tok.encode(prompt).ids
    if len(prefix)+MAX_NEW>cfg.max_seq_len:
        raise ValueError('full evaluation prompt plus64 exceeds context')
    capture=CaptureTokens(tok)
    _,meta=sample(PrecisionForward(model,'fp32_math'),cfg,capture,prompt,max_new=MAX_NEW,
        temperature=0.,top_k=1,device='cuda',use_cache=True,logits_last_only=True,
        return_metadata=True,stop_token_sequences=[[tok.token_to_id('<|im_end|>')]])
    ids=capture.decoded_ids
    if not isinstance(ids,list) or ids[:len(prefix)]!=prefix or len(ids)-len(prefix)!=meta['generated_tokens']:
        raise ValueError('actual full tokens differ from complete prefix/generation receipt')
    generated=ids[len(prefix):];terminal=[];reason=meta['finish_reason']
    if reason=='STOP_SEQUENCE':
        terminal=[tok.token_to_id('<|im_end|>')]
        if generated[-1:]!=terminal or meta['matched_stop_sequence']!=terminal:
            raise ValueError('actual terminal EOT receipt differs')
    elif reason=='EOS':
        terminal=[tok.token_to_id('<eos>')]
        if generated[-1:]!=terminal or meta.get('matched_stop_sequence') is not None:
            raise ValueError('actual terminal EOS receipt differs')
    elif reason!='MAX_NEW':
        raise ValueError('declared EOT/EOS/MAX_NEW only')
    content=generated[:-1] if terminal else generated
    answer=tok.decode(content,skip_special_tokens=False)
    meta.update(precision='FP32_MATH',temperature=0.,top_k=1,use_cache=True,mtp=False,
        candidate_answers_supplied=False,prompt_sha256=sha(prompt),prompt_ids_sha256=sha(prefix),
        prompt_tokens=len(prefix),generated_ids_sha256=sha(generated),content_ids_sha256=sha(content),
        generated_ids=generated,terminal_ids=terminal,body_utf8_sha256=hashlib.sha256(answer.encode('utf-8')).hexdigest().upper(),
        terminal_only_removed=True)
    return answer,meta


def classify_case(case,answer):
    if case['lane']=='coded':
        return dict(correct=data.classify(case['problem'],case['language'],answer))
    if case['lane']=='natural':
        from scripts.p106b_night_learning import qa_scores
        result=qa_scores(answer,case['aliases'],case['language'])
        return dict(correct=bool(result['em']),**result,scope='annotation/lexical metric not semantic certainty')
    if case['lane']=='canary':
        clean=answer.strip()
        return dict(correct=bool(re.fullmatch(r'[+-]?[0-9]+',clean)) and int(clean)==int(case['gold']))
    return dict(correct=None,semantic_review='NOT_AUTOMATICALLY_ADJUDICATED')


def recount(events,cases,tokenizer=None):
    if len(events)!=len(cases) or len({v['id'] for v in events})!=len(cases):
        raise Pending('full unique1694 actual answers required')
    cells=defaultdict(Counter);finish=Counter();byid={};groups=defaultdict(list);invariance=defaultdict(list)
    for event,case in zip(events,cases):
        if event.get('id')!=case['id'] or event.get('case_sha256')!=sha(case) or not isinstance(event.get('answer'),str):
            raise ValueError('ordered case/answer provenance differs')
        score=classify_case(case,event['answer'])
        if event['metrics']!=score:
            raise ValueError('raw answer score differs')
        g=event['generation'];proof=case['encoding']
        if (type(g.get('generated_ids')) is not list
                or any(type(v) is not int or not 0<=v<32768 for v in g['generated_ids'])
                or type(g.get('terminal_ids')) is not list
                or any(type(v) is not int or v not in (2,4) for v in g['terminal_ids'])):
            raise ValueError('actual token IDs must be a list of real in-vocabulary integers')
        if (g.get('max_new')!=MAX_NEW or g.get('precision')!='FP32_MATH' or g.get('mtp') is not False
                or g.get('use_cache') is not True or g.get('candidate_answers_supplied') is not False
                or g.get('stop_token_sequences')!=[[4]]
                or any(g.get(k)!=proof[k] for k in ('prompt_sha256','prompt_ids_sha256','prompt_tokens'))
                or g.get('temperature')!=0. or g.get('top_k')!=1
                or type(g.get('generated_tokens')) is not int
                or len(g.get('generated_ids',[]))!=g.get('generated_tokens')
                or sha(g['generated_ids'])!=g.get('generated_ids_sha256')
                or not 1<=g['generated_tokens']<=MAX_NEW
                or hashlib.sha256(event['answer'].encode('utf-8')).hexdigest().upper()!=g.get('body_utf8_sha256')):
            raise ValueError('actual FP32/64/prefix/fulltoken receipt differs')
        terminal=g.get('terminal_ids');reason=g.get('finish_reason')
        if (not isinstance(terminal,list) or reason not in ('STOP_SEQUENCE','EOS','MAX_NEW')
                or reason=='STOP_SEQUENCE' and (terminal!=[4] or g.get('matched_stop_sequence')!=[4])
                or reason=='EOS' and (terminal!=[2] or g.get('matched_stop_sequence') is not None)
                or reason=='MAX_NEW' and (terminal or g['generated_tokens']!=MAX_NEW)
                or terminal and g['generated_ids'][-len(terminal):]!=terminal):
            raise ValueError('raw authenticated EOT/EOS/MAX_NEW boundary differs')
        content=g['generated_ids'][:-len(terminal)] if terminal else g['generated_ids']
        if sha(content)!=g.get('content_ids_sha256') or any(v in (2,4) for v in content):
            raise ValueError('actual content/terminal token boundary differs')
        if tokenizer is not None:
            if ((tokenizer.token_to_id('<eos>'),tokenizer.token_to_id('<|im_end|>'))!=(2,4)
                    or tokenizer.decode(content,skip_special_tokens=False)!=event['answer']):
                raise ValueError('actual content IDs do not decode to recorded full answer')
        key=(case['lane'],case.get('split','monitor'),case['family'],case['language'],str(case.get('wording','monitor')),case.get('position','monitor'))
        cells[key].update(n=1,correct=int(score['correct']) if score['correct'] is not None else 0,
            scored=int(score['correct'] is not None),empty_exact=int(event['answer']==''),generated_tokens=g['generated_tokens'])
        if case['lane']=='coded':
            p=case['problem'];family=case['family'];lang=case['language']
            groups[(case['split'],family,lang,str(case['wording']),case['position'],case['group_id'])].append(bool(score['correct']))
            invariance[(case['split'],family,lang,p['query_id'])].append(bool(score['correct']))
            if family=='boolean':
                cells[key].update(gold_true=int(p['target_by_language'][lang]=='true'),
                    gold_false=int(p['target_by_language'][lang]=='false'),
                    predicted_true=int(event['answer'].strip().casefold()=='true'),
                    predicted_false=int(event['answer'].strip().casefold()=='false'))
            elif family=='lookup':
                table={(s,a):v for s,a,v in p['state']['facts']};q=p['query'];target=p['target_by_language'][lang]
                def word(attribute,index):
                    return (data.COLOURS if attribute=='colour' else data.OBJECTS)[lang][index]
                first=p['state']['facts'][0]
                cells[key].update(first_fact_correct=int(word(first[1],first[2])==target),
                    subject_only_correct=int(word('colour',table[q['subject'],'colour'])==target),
                    attribute_only_correct=int(word(q['attribute'],table[min(p['state']['subjects']),q['attribute']])==target))
        finish[g['finish_reason']]+=1;byid[event['id']]=event
    parent_cells=defaultdict(Counter);invariance_cells=defaultdict(Counter)
    for key,passed in groups.items():
        family=key[1]
        if family in ('lookup','format') and len(passed)!=(4 if family=='lookup' else 2):
            raise ValueError('all queries of selected lookup/JSON parent required')
        parent_cells[key[:-1]].update(groups=1,all_queries_correct=int(all(passed)),queries=len(passed))
    for key,passed in invariance.items():
        if len(passed)!=4:
            raise ValueError('four wording/position responses per selected query required')
        invariance_cells[key[:-1]].update(queries=1,all_four_conditions_correct=int(all(passed)))
    return dict(cells=[dict(zip(('lane','split','family','language','wording','position'),key),**dict(v)) for key,v in sorted(cells.items())],
        parent_group_scores=[dict(stratum=list(k),**dict(v)) for k,v in sorted(parent_cells.items())],
        query_invariance_scores=[dict(stratum=list(k),**dict(v)) for k,v in sorted(invariance_cells.items())],
        token_body_correspondence='FROZEN_TOKENIZER_DECODE_VERIFIED' if tokenizer is not None else 'NOT_CHECKED_BY_PURE_RECOUNT',
        actual_answers=len(events),finish_reasons=dict(finish),new_training=0,automatic_adoption=False)


def identity(endpoint,frozen=None):
    if endpoint not in ENDPOINTS:
        raise ValueError('registered endpoint required before any checkpoint access')
    if endpoint=='parent':
        return dict(endpoint=endpoint,checkpoint=str(base.PARENT.relative_to(ROOT)),checkpoint_sha256=base.PARENT_SHA,
                    expected_core_sha256=base.PARENT_CORE)
    r=base.stage_report(EVIDENCE/('train_'+endpoint)/'report.json')
    if r.get('checkpoint')!=str(checkpoint(endpoint).relative_to(ROOT)):
        raise ValueError('exact owned child checkpoint path required before stat/digest/open')
    if frozen is None:
        frozen,_,_=read_prepared()
    verify_training(r,endpoint,frozen,cost=False)
    read_activity(EVIDENCE/('activity_train_'+endpoint+'.json'),mode='train',arm=endpoint,completed=True)
    return dict(endpoint=endpoint,checkpoint=r['checkpoint'],checkpoint_sha256=r['checkpoint_sha256'],expected_core_sha256=r['final_core_sha256'])


def validate_evaluation(report,endpoint,frozen,cases,lineage):
    if (len(cases)!=EXPECTED_ANSWERS or sha(cases)!=frozen['cases_sha256']
            or report.get('status')!='ACTUAL_FIRST_ANSWERS_RECORDED'
            or any(report.get(k)!=v for k,v in info().items())
            or report.get('endpoint')!=endpoint or report.get('lineage')!=lineage
            or report.get('corpus_sha256')!=digest(CORPUS/'report.json')
            or report.get('cases_sha256')!=frozen['cases_sha256']
            or report.get('core_before')!=lineage['expected_core_sha256']
            or report.get('core_after')!=lineage['expected_core_sha256']
            or report.get('model_training') is not False or report.get('weights_changed') is not False
            or report.get('checkpoints_written')!=0
            or report.get('answer_manifest',{}).get('lineage')!=dict(tag=TAG,**lineage)):
        raise ValueError('complete owned evaluation/code/corpus/cases/body/raw lineage required')
    native=report.get('native32_fp32',{})
    if (native.get('targets')!=32768 or native.get('windows')!=32
            or native.get('precision')!='FP32_MATH' or native.get('val_sha256')!=base.NATIVE_VAL_SHA
            or not finite(native.get('ce'),True)):
        raise ValueError('fixed32 native VAL receipt/denominator/precision differs')


def evaluate(endpoint):
    import torch
    from tinylm.infer.generate import _strip
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    from scripts.p106b_gate_runtime import idle_before_gpu
    frozen,_,_=read_prepared();lineage=identity(endpoint,frozen)
    if digest(ROOT/lineage['checkpoint'])!=lineage['checkpoint_sha256']:
        raise ValueError('evaluated checkpoint bytes changed')
    cases=read_rows(CORPUS,frozen['manifests']['cases'],'cases',EXPECTED_ANSWERS)
    if sha(cases)!=frozen['cases_sha256']:
        raise ValueError('frozen evaluation case identity differs')
    target=safe(EVIDENCE/('evaluate_'+endpoint));local=safe(LOCAL/('evaluate_'+endpoint))
    if target.exists() or local.exists():
        raise FileExistsError('old evaluation preserved')
    idle_before_gpu();authority();target.mkdir(parents=True,exist_ok=False);local.mkdir(parents=True,exist_ok=False)
    writer=ShardWriter(local,'answers',limit=19_999_999);began=time.perf_counter()
    torch,model,cfg,tok,_=base.load_parent()
    if endpoint!='parent':
        saved=torch.load(ROOT/lineage['checkpoint'],map_location='cpu',weights_only=True)
        if (saved.get('question_transfer_course')!=dict(tag=TAG,arm=endpoint,epochs=4)
                or saved.get('step')!=UPDATES or saved.get('tokenizer_sha256')!=natural.TOK_SHA):
            raise ValueError('child course/step/tokenizer differs')
        model.load_state_dict(_strip(saved['model']),strict=True);del saved
    before=state_fingerprint(model)
    if before!=lineage['expected_core_sha256']:
        raise ValueError('actual evaluated body differs')
    model=model.cuda();model.eval();model.freeze_quant();torch.cuda.reset_peak_memory_stats()
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    events=[]
    with torch.no_grad():
        for i,case in enumerate(cases):
            authority()
            if case_encoding(case,tok)!=case['encoding']:
                raise ValueError('actual complete prompt or gold reference encoding differs')
            answer,generation=emit64(model,cfg,tok,case['messages'])
            event=dict(id=case['id'],case_sha256=sha(case),answer=answer,generation=generation,
                metrics=classify_case(case,answer),lineage=dict(tag=TAG,**lineage))
            writer.append(event);events.append(event)
            if (i+1)%128==0:
                print('[QUESTION_TRANSFER_EVAL] '+json.dumps(dict(endpoint=endpoint,responses=i+1,expected=len(cases))),flush=True)
    summary=recount(events,cases,tok);model.clear_quant();native=base.native_probe(model);after=state_fingerprint(model)
    if before!=after or digest(ROOT/lineage['checkpoint'])!=lineage['checkpoint_sha256']:
        raise ValueError('evaluation modified body or original checkpoint')
    manifest=writer.close(lineage=dict(tag=TAG,**lineage));verify(local,manifest)
    result=dict(info(),status='ACTUAL_FIRST_ANSWERS_RECORDED',endpoint=endpoint,lineage=lineage,
        corpus_sha256=digest(CORPUS/'report.json'),cases_sha256=sha(cases),core_before=before,core_after=after,
        summary=summary,answer_manifest=manifest,answer_manifest_sha256=digest(local/'answers_shards_manifest.json'),
        native32_fp32=native,whole_seconds=time.perf_counter()-began,model_training=False,weights_changed=False,
        checkpoints_written=0,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
    validate_evaluation(result,endpoint,frozen,cases,lineage)
    write(target/'report.json',result)
    byid={e['id']:e for e in events};lookup={c['id']:c for c in cases}
    for key in frozen['display_ids']:
        print('[QUESTION_TRANSFER_ACTUAL_QUESTION_ANSWER] '+json.dumps(dict(endpoint=endpoint,
            question=lookup[key]['messages'],answer=byid[key]['answer'],metrics=byid[key]['metrics'],
            generation=byid[key]['generation']['finish_reason'],case_id=key,
            selection_sha256=frozen['display_selection_sha256']),ensure_ascii=False),flush=True)
    del model;gc.collect();torch.cuda.empty_cache()
    return 0


def readback():
    from tokenizers import Tokenizer
    frozen,_,_=read_prepared();cases=read_rows(CORPUS,frozen['manifests']['cases'],'cases',EXPECTED_ANSWERS)
    if sha(cases)!=frozen['cases_sha256'] or digest(natural.TOKENIZER)!=natural.TOK_SHA:
        raise ValueError('frozen exact evaluation cases/tokenizer bytes required')
    tok=Tokenizer.from_file(str(natural.TOKENIZER))
    models={};events_by={}
    for endpoint in ENDPOINTS:
        r=base.stage_report(EVIDENCE/('evaluate_'+endpoint)/'report.json');link=identity(endpoint,frozen)
        validate_evaluation(r,endpoint,frozen,cases,link)
        read_activity(EVIDENCE/('activity_evaluate_'+endpoint+'.json'),mode='evaluate',endpoint=endpoint,completed=True)
        if (r.get('status')!='ACTUAL_FIRST_ANSWERS_RECORDED' or r.get('code_sha256')!=info()['code_sha256']
                or r.get('lineage')!=link or r.get('cases_sha256')!=sha(cases)
                or r.get('core_before')!=link['expected_core_sha256'] or r.get('core_after')!=link['expected_core_sha256']
                or digest(ROOT/link['checkpoint'])!=link['checkpoint_sha256']):
            raise ValueError('actual source/code/CP/evaluation receipt differs')
        directory=LOCAL/('evaluate_'+endpoint)
        if digest(directory/'answers_shards_manifest.json')!=r['answer_manifest_sha256']:
            raise ValueError('actual answer manifest changed')
        events=read_rows(directory,r['answer_manifest'],'answers',EXPECTED_ANSWERS)
        if any(e.get('lineage')!=dict(tag=TAG,**link) for e in events) or recount(events,cases,tok)!=r['summary']:
            raise ValueError('independent raw answer recount differs')
        models[endpoint]=r;events_by[endpoint]={e['id']:e for e in events}
    contrasts=[]
    for a,b,axis in (('fixed_last','varied_last','wording_at_CQ'),('fixed_balanced','varied_balanced','wording_balanced'),
                     ('fixed_last','fixed_balanced','position_at_T0'),('varied_last','varied_balanced','position_varied')):
        cells=defaultdict(Counter)
        for case in cases:
            left=events_by[a][case['id']]['metrics']['correct'];right=events_by[b][case['id']]['metrics']['correct']
            if left is None or right is None:continue
            key=(case['lane'],case.get('split','monitor'),case['family'],case['language'],str(case.get('wording','monitor')),case.get('position','monitor'))
            cells[key].update(n=1,left=int(left),right=int(right),left_only=int(left and not right),right_only=int(right and not left))
        contrasts.append(dict(left=a,right=b,axis=axis,cells=[dict(stratum=list(k),**dict(v)) for k,v in sorted(cells.items())],
            learning_seeds=1,inference='descriptive paired observed cohort; no seed CI or automatic adoption'))
    result=dict(info(),status='FOUR_ARM_ACTUAL_READBACK_COMPLETE',errors=0,actual_answers=EXPECTED_ANSWERS*5,
        cases_sha256=sha(cases),models=models,paired_contrasts=contrasts,new_training=0,checkpoints_written=0,
        intelligence='NOT_ESTABLISHED',source_annotation_semantics='NOT_FULLY_REVIEWED')
    write(EVIDENCE/'readback.json',result)
    print('[QUESTION_TRANSFER_READBACK] complete8470 actual first answers; no automatic adoption',flush=True)
    return 0


def activity_key(mode,arm=None,endpoint=None):
    return mode+('_'+str(arm or endpoint) if arm or endpoint else '')


def run_worker(mode,arm=None,endpoint=None,max_wall_sec=7200):
    authority()
    if mode=='source':
        source_inputs();print('[QUESTION_TRANSFER_SOURCE] exact prior source verified; model/GPU NOT_RUN');return 0
    if mode=='preflight':
        read_prepared();print('[QUESTION_TRANSFER_PREFLIGHT] exact code/source verified; model/GPU NOT_RUN');return 0
    if mode=='budget':
        print('[QUESTION_TRANSFER_BUDGET] '+json.dumps(budget(),sort_keys=True));return 0
    from scripts.p106b_gate_runtime import wall_limit
    key=activity_key(mode,arm,endpoint);path=safe(EVIDENCE/('activity_'+key+'.json'))
    if path.exists():
        raise FileExistsError('previous complete/partial worker activity preserved')
    reserve=RECORD_RESERVE if mode in ('evaluate','readback') else EVAL_RESERVE+RECORD_RESERVE
    absolute=authority(training=mode in ('prepare','cost','train'))
    if mode in ('evaluate','readback'):
        absolute-=RECORD_RESERVE
    remaining=min(absolute,ACTIVE_LIMIT-spent_seconds()-reserve)
    if max_wall_sec>remaining:
        raise Pending('requested bounded activity plus reserves does not fit current authority/budget')
    began=time.perf_counter();code=None
    try:
        with wall_limit(max_wall_sec):
            if mode=='prepare':code=prepare()
            elif mode in ('cost','train'):code=train(arm,cost=mode=='cost')
            elif mode=='evaluate':code=evaluate(endpoint)
            elif mode=='readback':code=readback()
            else:raise ValueError('registered worker mode required')
        return code
    finally:
        elapsed=time.perf_counter()-began
        write(path,dict(schema=SCHEMA,tag=TAG,key=key,mode=mode,arm=arm,endpoint=endpoint,
            seconds=elapsed,returncode=code,complete=code==0,limit=max_wall_sec,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            code_sha256=info()['code_sha256'],corpus_sha256=digest(CORPUS/'report.json') if (CORPUS/'report.json').is_file() else None,
            scope='actual worker wall including input verification; regression/preflight wrapper excluded'))


def phase_commands(mode,arm=None,endpoint=None,max_wall_sec=7200):
    if mode not in MODES or (mode in ('cost','train'))!=(arm in ARMS) or (mode=='evaluate')!=(endpoint in ENDPOINTS):
        raise ValueError('exact owned mode/arm/endpoint selection required')
    if arm is not None and mode not in ('cost','train') or endpoint is not None and mode!='evaluate':
        raise ValueError('unused selector rejected')
    if type(max_wall_sec) is not int or not 60<=max_wall_sec<=7200:
        raise ValueError('explicit60..7200 worker wall required')
    py=[sys.executable,'-B','-X','utf8'];driver=py+['scripts/diag_p106b_question_transfer.py']
    command=driver+['--mode',mode,'--max-wall-sec',str(max_wall_sec),'--worker','--execute']
    if arm is not None:command+=['--arm',arm]
    if endpoint is not None:command+=['--endpoint',endpoint]
    prior='source' if mode in ('source','prepare') else 'preflight'
    return [('REGRESSION',py+['-m','unittest','scripts.test_p106b_question_transfer_data',
        'scripts.test_p106b_question_transfer','-v']),
        ('PREFLIGHT',driver+['--mode',prior,'--worker','--execute','--max-wall-sec','600']),
        ('EXECUTE',command)]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=MODES,required=True)
    parser.add_argument('--arm',choices=ARMS)
    parser.add_argument('--endpoint',choices=ENDPOINTS)
    parser.add_argument('--max-wall-sec',type=int,default=7200)
    parser.add_argument('--worker',action='store_true')
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute',action='store_true');action.add_argument('--check-only',action='store_true')
    args=parser.parse_args(argv)
    phases=phase_commands(args.mode,args.arm,args.endpoint,args.max_wall_sec)
    if args.check_only:
        print('[QUESTION_TRANSFER_CHECK_ONLY] '+json.dumps(info(),sort_keys=True));return 0
    try:
        if args.worker:return run_worker(args.mode,args.arm,args.endpoint,args.max_wall_sec)
        def launch(command):
            print('[PHASE_COMMAND] '+json.dumps(command),flush=True)
            try:return subprocess.run(command,cwd=ROOT,stdin=subprocess.DEVNULL,timeout=args.max_wall_sec+600).returncode
            except subprocess.TimeoutExpired:return 9
        return pipeline(phases,launch,lambda line:print(line,flush=True),
            experiment='P106B_QUESTION_TRANSFER_'+args.mode+'_'+str(args.arm or args.endpoint or 'all'))['returncode']
    except BaseException as exc:
        if isinstance(exc,SystemExit):raise
        status,code=base.failure_status(exc)
        if code==9:
            import traceback
            traceback.print_exc()
        print('[QUESTION_TRANSFER_FINAL] '+status+str(code)+': '+str(exc),flush=True)
        return code


if __name__=='__main__':raise SystemExit(main())
