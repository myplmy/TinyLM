#!/usr/bin/env python3
"""Independent subject/role four-query experiment; root owns actual execution.

Check-only/help read code only. prepare/preflight are tokenizer/source CPU work,
never learned-model work. GPU cost/train/evaluation require explicit execute.
Free first answers, teacher-forced candidates, original32 loss and technical
completion are separate evidence; none automatically adopts a model.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import math
import os
import random
import tempfile
import time
from scripts import diag_p106b_relation_bind as base
from scripts.diag_p106b_relation_bind import (safe, write, required, stage_report, failure_status,
    old_source, encode_old, load_parent, make_optimizers, native_probe, emit_answer)
from scripts import p106b_subject_role_data as data
from scripts import p106b_subject_role_loss as loss
from scripts import p106b_night_course as qa
from scripts import p106b_night_qa_data as natural_data
from scripts.p106b_shards import ShardWriter, verify

TAG = data.TAG
LOCAL = ROOT / 'test_result/evidence/local' / TAG
CORPUS = LOCAL / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
A_CORPUS = ROOT / 'test_result/evidence/local/p106b_relation_bind_v1_s1337/corpus'
A_EVIDENCE = ROOT / 'test_result/evidence/p106b_relation_bind_v1_s1337'
PARENT = base.PARENT
PARENT_SHA = base.PARENT_SHA
PARENT_CORE = base.PARENT_CORE
NATIVE = base.NATIVE
NATIVE_TRAIN_SHA = base.NATIVE_TRAIN_SHA
NATIVE_VAL_SHA = base.NATIVE_VAL_SHA
NATIVE_TRAIN_TOKENS = 597995000
NATIVE_SEED = 20261017
UPDATES = 896
RELATION_COUNTS = dict(data.original.COUNTS)
ARMS = ('ce', 'role_only', 'all_axes')
MODES = dict(ce='CE', role_only='ROLE_ONLY', all_axes='ALL_AXES')
ENDPOINTS = (*ARMS, 'parent')
WEIGHTS = {arm: loss.WEIGHTS[MODES[arm]] for arm in ARMS}
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
AUTHORITY_END = END
EVALUATION_SECONDS = 5400
RESERVE_SECONDS = 3600
TRAIN_STOP = END - timedelta(seconds=EVALUATION_SECONDS + RESERVE_SECONDS)
OWN_CODE = ('scripts/p106b_subject_role_data.py', 'scripts/test_p106b_subject_role_data.py',
    'scripts/p106b_subject_role_loss.py', 'scripts/test_p106b_subject_role_loss.py',
    'scripts/diag_p106b_subject_role.py', 'scripts/test_p106b_subject_role.py',
    'scripts/p106b_subject_role_entry.py', 'scripts/test_p106b_subject_role_entry.py')
CODE = tuple(sorted(set((*OWN_CODE, *base.CODE, *qa.CODE,
    'scripts/diag_p106b_night_foundation.py', 'scripts/p106b_night_foundation_data.py',
    'scripts/diag_p101a_sft_mtp.py', 'scripts/p106b_native_windows.py',
    'tinylm/chat/canonical.py', 'tinylm/chat/serialize.py', 'tinylm/train/mtp_sft.py'))))
Pending = base.PrerequisitePending


def digest(path):
    return natural_data.digest(safe(path))


def info():
    code = {p: digest(ROOT / p) if safe(ROOT / p).is_file() else 'NOT_CREATED' for p in CODE}
    return dict(schema='P106B_SUBJECT_ROLE_RUNTIME_V1', tag=TAG, code_sha256=code,
        code_complete=all(v != 'NOT_CREATED' for v in code.values()), arms=list(ARMS), modes=MODES,
        weights=WEIGHTS, parent=str(PARENT.relative_to(ROOT)), parent_sha256=PARENT_SHA,
        expected_parent_core_sha256=PARENT_CORE, tokenizer_sha256=natural_data.TOK_SHA,
        micro_bs=8, accum=16, seq=1024, grad_checkpoint=True, compile='default', seed=1337,
        epochs=4, updates=UPDATES, positive_rows_per_pass=28672, relation_questions_per_pass=8192,
        crossed_rows_per_pass=24576, native_targets_per_update=8192, native_windows=7168,
        native_train_tokens=NATIVE_TRAIN_TOKENS, native_seed=NATIVE_SEED,
        native_train_sha256=NATIVE_TRAIN_SHA, native_val_sha256=NATIVE_VAL_SHA,
        native_access='INDEXED_TRAIN_ONLY', native_train_file=str((NATIVE / 'train.bin').relative_to(ROOT)),
        experiment_budget_hours=8., relation_bundle_counts=RELATION_COUNTS,
        adam_lr=5e-5, muon_lr=2e-4, all_group_weight_decay=0., grad_clip=1., fresh_optimizer=True,
        schedule='constant', mtp=False, teacher_calls=0, extra_inference_parameters=0,
        row_negative_policy='mean selected1/3 negatives then whole-update question denominator',
        deadline_utc=END.isoformat(), training_stop_utc=TRAIN_STOP.isoformat(),
        evaluation_reserve_seconds=EVALUATION_SECONDS, record_reserve_seconds=RESERVE_SECONDS,
        expected_first_answers=1758, cf256='SEPARATE_NOT_RUN', formal_train_ready=False,
        adoption='NOT_DECIDED', scope='same familiar fictional A facts/names; one learning seed')


def authority(training=False, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None: raise ValueError('timezone-aware UTC time required')
    remaining = ((TRAIN_STOP if training else END) - now).total_seconds()
    if not math.isfinite(remaining) or remaining <= 0: raise Pending('absolute current authority/cutoff ended')
    return remaining


def bounded_wall(seconds, training=False, reserve=0):
    """Re-read current authority after resource admission, before model work."""
    remaining = int(authority(training=training) - reserve)
    if remaining < 60: raise Pending('latest authority leaves less than60s after required reserve')
    return min(seconds, remaining)


def record_identity(record):
    return natural_data.sha(dict(x=record.x, y=record.y, segments=record.segments))


def read_shards(directory, manifest, stem, expected):
    safe(directory)
    if type(manifest.get('rows')) is not int: raise ValueError('integer shard denominator required')
    if manifest['rows'] < expected: raise Pending('partial raw/source cohort; never fill missing with zeros')
    if manifest['rows'] != expected or expected <= 0: raise ValueError('exact nonempty shard cohort required')
    if required(directory / (stem + '_shards_manifest.json')) != manifest:
        raise ValueError('manifest file/report changed')
    for i, shard in enumerate(manifest.get('shards', [])):
        if shard.get('path') != f'{stem}_{i:06d}.jsonl' or shard.get('bytes', 20_000_000) >= 20_000_000:
            raise ValueError('ordered row-aligned shards below20MB required')
        safe(directory / shard['path'])
    verify(directory, manifest)
    values = [json.loads(line) for spec in manifest['shards']
              for line in (directory / spec['path']).read_text(encoding='utf-8').splitlines()]
    if len(values) != expected: raise ValueError('decoded row count differs')
    return values


def source_inputs():
    """Read frozen A/natural data, not A controller state or learned tensors."""
    frozen = stage_report(A_CORPUS / 'report.json')
    if (frozen.get('status') != 'CPU_DATA_AND_ENCODER_VERIFIED'
            or frozen.get('parent_sha256') != PARENT_SHA
            or frozen.get('expected_parent_core_sha256') != PARENT_CORE
            or frozen.get('tokenizer_sha256') != natural_data.TOK_SHA):
        raise ValueError('exact original A CPU/source/parent required')
    if any(digest(ROOT / p) != h for p, h in frozen['code_sha256'].items()):
        raise ValueError('frozen A dependency code changed')
    cpu = stage_report(A_EVIDENCE / 'cpu_contract.json')
    if cpu.get('corpus_report_sha256') != digest(A_CORPUS / 'report.json'):
        raise ValueError('original A CPU manifest/report binding differs')
    source, rows = old_source()
    if (len(rows['train']) != 8192 or len(rows['replay']) != 4096
            or digest(ROOT / frozen['natural_source_report']) != frozen['natural_source_sha256']
            or natural_data.sha(source['manifests']) != frozen['natural_manifest_sha256']):
        raise ValueError('same natural8192/replay4096 source required')
    parents = {s: read_shards(A_CORPUS, frozen['manifests'][s], s, n)
               for s, n in RELATION_COUNTS.items()}
    data.original.validate_splits(parents)
    derived = {s: [data.derive_bundle(b) for b in values] for s, values in parents.items()}
    binding = dict(a_corpus_report_sha256=digest(A_CORPUS / 'report.json'),
        a_cpu_contract_sha256=digest(A_EVIDENCE / 'cpu_contract.json'),
        natural_source_sha256=frozen['natural_source_sha256'], natural_manifest_sha256=natural_data.sha(source['manifests']),
        original_manifests_sha256=natural_data.sha(frozen['manifests']),
        parent_bundle_hashes={s: natural_data.sha([b['bundle_sha256'] for b in values]) for s, values in parents.items()})
    return frozen, rows, derived, binding


def native_offsets(length=NATIVE_TRAIN_TOKENS, *, count=7168, seed=NATIVE_SEED):
    if type(length) is not int or length < 1025 or type(count) is not int or count <= 0:
        raise ValueError('explicit native TRAIN length/window count required')
    choices = range(0, length - 1025 + 1, 1025)
    if len(choices) < count: raise ValueError('native pool cannot supply unique complete windows')
    offsets = random.Random(seed).sample(choices, count)
    ordered = sorted(offsets)
    if (len(set(offsets)) != count or any(not 0 <= v <= length - 1025 for v in offsets)
            or any(b - a < 1025 for a, b in zip(ordered, ordered[1:]))):
        raise ValueError('new same-arm native vector incomplete/overlapping')
    return offsets


def micro_records(micro, natural, relations, replay):
    if micro.kind == 'natural': return [r for i in micro.indices for r in natural[i]]
    if micro.kind == 'relation': return [r for i in micro.indices for r in relations[i][0]]
    if micro.kind == 'replay': return [replay[i] for i in micro.indices]
    raise ValueError('unknown lane')


def denominators(group, natural, relations, replay):
    words = sum(r.targets for m in group for r in micro_records(m, natural, relations, replay))
    questions = sum(4 * len(m.indices) for m in group if m.kind == 'relation')
    if words <= 0: raise ValueError('nonempty positive assistant denominator required')
    return words, questions


def relation_summary(bundles, tok):
    totals = Counter(); identities = []; candidate_lengths = Counter()
    for bundle in bundles:
        positive, crossed = data.encode_bundle(bundle, tok)
        for record in positive:
            totals.update(positive_rows=1, x_tokens=record.x_tokens, assistant_targets=record.targets)
        for record in crossed:
            totals.update(crossed_rows=1, crossed_x_tokens=record.x_tokens, crossed_content_targets=record.targets - 1)
        candidate_lengths[','.join(str(r.targets - 1) for r in positive)] += 1
        identities.append([bundle['bundle_id'], [record_identity(r) for r in positive + crossed]])
    return dict(totals=dict(totals), encoded_sha256=natural_data.sha(identities),
        candidate_lengths=dict(candidate_lengths), independent_graphs=len({b['parent_group_id'] for b in bundles}),
        shortcuts={name: sum(data.shortcut_bounds(b)[name]['correct'] for b in bundles)
                   for name in ('role_only', 'subject_only', 'constant', 'first_fact')})


def exposure(natural, replay, relation):
    count = Counter()
    for pair in natural:
        for r in pair: count.update(positive_rows=1, x_tokens=r.x_tokens, assistant_targets=r.targets)
    for r in replay: count.update(positive_rows=1, x_tokens=r.x_tokens, assistant_targets=r.targets)
    count.update(relation['totals'])
    return dict(per_pass=dict(count), four_pass={k: 4 * v for k, v in count.items()},
        padded_positive_slots=UPDATES * 128 * 1024, padded_crossed_slots=4 * 24576 * 1024,
        native_targets=UPDATES * 8192, native_windows=UPDATES * 8,
        padding_is_not_actual_tokens=True, cross_is_not_positive_supervision=True)


def schedule_proof(natural=8192, relations=2048, replay=4096):
    result = []
    for epoch in range(4):
        groups = loss.schedule(natural, relations, replay, epoch)
        seen = {k: [] for k in ('natural', 'relation', 'replay')}
        for group in groups:
            if len(group) != 16: raise ValueError('exact accum16 required')
            for micro in group: seen[micro.kind].extend(micro.indices)
        if any(sorted(seen[k]) != list(range(n)) for k, n in (('natural', natural), ('relation', relations), ('replay', replay))):
            raise ValueError('schedule omitted/duplicated a source')
        result.append(dict(epoch=epoch + 1, updates=len(groups),
            sha256=natural_data.sha([[asdict(m) for m in g] for g in groups])))
    if (natural, relations, replay) == (8192, 2048, 4096) and sum(r['updates'] for r in result) != UPDATES:
        raise ValueError('full896 updates required')
    return result


def evaluation_cases(rows, relations):
    cases = [data.evaluation_case(b, qi, view) for b in relations['test'] for view in range(3) for qi in range(4)]
    for language in ('ko', 'en'):
        selected = sorted((r for r in rows['test'] if r['language'] == language),
            key=lambda r: natural_data.sha([20261017, 'MONITOR', r['root']]))[:32]
        if len(selected) != 32: raise ValueError('same32 natural roots/language required')
        for case in selected:
            for view in range(3):
                row = natural_data.render_view(case, view)
                cases.append(dict(id=natural_data.sha(['NATURAL', case['root'], view]), lane='natural',
                    language=language, group_id=case['article_id'], root=case['root'], view=view,
                    messages=row['messages'][:1], aliases=case['aliases']))
        for i in range(12):
            a, b = i + 2, (i * 7 + 3) % 17 + 1
            question = f'{a}+{b}의 값은? 정수만 답하세요.' if language == 'ko' else f'What is {a}+{b}? Answer only the integer.'
            cases.append(dict(id=natural_data.sha(['ARITHMETIC_MONITOR', language, i]), lane='canary',
                language=language, group_id='arithmetic_' + str(i), messages=[dict(role='user', content=question)], gold=str(a + b)))
    questions = ('1+1은?', '2+2는?', 'A는 사과고 B는 당근이다 B는?',
        '문맥: 민수는 사과 3개, 영희는 사과 5개를 가지고 있습니다. 질문: 영희의 사과는 몇 개입니까? 답만 쓰세요.', '사과에 대해 알려줘', '농구란?')
    for i, question in enumerate(questions):
        cases.append(dict(id=natural_data.sha(['USER_SEEN_MONITOR', i]), lane='user_seen', language='ko',
            group_id='user_seen_' + str(i), messages=[dict(role='user', content=question)], semantic_review='NOT_AUTOMATICALLY_ADJUDICATED'))
    if len({c['id'] for c in cases}) != len(cases): raise ValueError('duplicate evaluation ID')
    return cases


def evaluation_proof(cases, tok):
    from tinylm.chat.serialize import serialize
    entries = []; counts = Counter()
    for c in cases:
        if [m['role'] for m in c['messages']] != ['user']: raise ValueError('candidate-free first answer input required')
        prompt = serialize(dict(messages=c['messages']), 'chatml', add_generation_prompt=True)
        ids = tok.encode(prompt).ids
        if not ids or len(ids) + 128 > 1024: raise ValueError('complete prompt+128 exceeds1024')
        entries.append([c['id'], natural_data.sha(prompt), natural_data.sha(ids), len(ids)])
        counts[c['lane'] + '|' + c['language']] += 1
    return dict(cases_sha256=natural_data.sha(cases), entries_sha256=natural_data.sha(entries),
        responses=len(cases), lane_counts=dict(counts), max_prompt_tokens=max(v[3] for v in entries), candidates_supplied=False)


def prepare():
    import torch
    from tokenizers import Tokenizer
    authority(training=True)
    if not info()['code_complete']: raise Pending('all eight independent code files must be frozen')
    for path in (LOCAL, EVIDENCE):
        safe(path)
        if path.exists(): raise FileExistsError('old complete/partial subject-role namespace preserved')
    a, rows, relations, binding = source_inputs()
    if digest(natural_data.TOKENIZER) != natural_data.TOK_SHA: raise ValueError('pinned tokenizer changed')
    tok = Tokenizer.from_file(str(natural_data.TOKENIZER)); natural, replay = encode_old(rows, tok)
    summaries = {s: relation_summary(v, tok) for s, v in relations.items()}
    actual = exposure(natural, replay, summaries['train'])
    if actual['per_pass']['positive_rows'] != 28672: raise ValueError('full same-positive population differs')
    for name, identity in (('train.bin', NATIVE_TRAIN_SHA), ('val.bin', NATIVE_VAL_SHA)):
        if digest(NATIVE / name) != identity: raise ValueError('immutable native cache changed')
    length = (NATIVE / 'train.bin').stat().st_size // 2
    if length != NATIVE_TRAIN_TOKENS: raise ValueError('actual uint16 native TRAIN length differs')
    offsets = native_offsets(length)
    cases = evaluation_cases(rows, relations); eval_proof = evaluation_proof(cases, tok)
    if eval_proof['responses'] != 1758: raise ValueError('exact1758 response cohort required')
    rank_specs = rank_specifications(relations['test'], tok)
    legacy_proof = old_input_proof(old_cases(rows, relations), tok)
    if legacy_proof != a['evaluation_input_proof']:
        raise ValueError('original A full990 prompt/token reconstruction differs')
    legacy = old_a_binding(rows, relations, tok)
    legacy_binding = {k: v for k, v in legacy.items() if k != 'answers'}
    if torch.cuda.is_initialized(): raise ValueError('CPU preparation initialized CUDA')
    CORPUS.mkdir(parents=True, exist_ok=False); manifests = {}
    for split, values in relations.items():
        writer = ShardWriter(CORPUS, split, limit=19_999_999)
        for bundle in values: writer.append(bundle)
        manifests[split] = writer.close(lineage=dict(tag=TAG, split=split, source_binding=binding))
        verify(CORPUS, manifests[split])
    result = dict(info(), status='SUBJECT_ROLE_CPU_VERIFIED', source_binding=binding, manifests=manifests,
        relation_reports=summaries, exposure=actual, schedules=schedule_proof(), evaluation_proof=eval_proof,
        ranking_specifications=rank_specs, ranking_specifications_sha256=natural_data.sha(rank_specs),
        original_a_evaluation_input_proof=legacy_proof, original_a_evaluation_binding=legacy_binding,
        native_access='INDEXED_TRAIN_ONLY', native_train_file=str((NATIVE / 'train.bin').relative_to(ROOT)),
        native_train_offsets=offsets, native_train_offsets_sha256=natural_data.sha(offsets),
        original_a_native_offsets_sha256=natural_data.sha(a['native_train_offsets']),
        overlap_with_a_native_windows=len(set(offsets) & set(a['native_train_offsets'])),
        native_train_sha256=NATIVE_TRAIN_SHA, native_val_sha256=NATIVE_VAL_SHA,
        model_loaded=False, model_forward=False, cuda_initialized=False, optimizer_updates=0, checkpoints_written=0)
    write(CORPUS / 'report.json', result)
    public = {k: v for k, v in result.items() if k not in ('manifests', 'native_train_offsets')}
    public['corpus_report_sha256'] = digest(CORPUS / 'report.json')
    write(EVIDENCE / 'cpu_contract.json', public)
    print('[SUBJECT_ROLE_CPU] complete source/tokenizer/encoder/schedule/native vector; model/GPU NOT_RUN', flush=True)
    return 0


def read_prepared():
    report = stage_report(CORPUS / 'report.json')
    if report.get('status') != 'SUBJECT_ROLE_CPU_VERIFIED': raise Pending('complete CPU preparation required')
    if any(report.get(k) != v for k, v in info().items()): raise ValueError('frozen code/recipe differs')
    a, rows, derived, binding = source_inputs()
    if report.get('source_binding') != binding or report.get('schedules') != schedule_proof(): raise ValueError('source/schedule changed')
    for s, n in RELATION_COUNTS.items():
        if read_shards(CORPUS, report['manifests'][s], s, n) != derived[s]: raise ValueError('derived source fact/gold/order changed')
        if report['manifests'][s].get('lineage') != dict(tag=TAG, split=s, source_binding=binding):
            raise ValueError('derived source lineage differs')
    if (report.get('native_train_offsets') != native_offsets()
            or report.get('native_train_offsets_sha256') != natural_data.sha(report['native_train_offsets'])):
        raise ValueError('new7168 native offsets changed or insufficient')
    if (not isinstance(report.get('ranking_specifications'), dict)
            or set(report['ranking_specifications']) != {b['bundle_id'] for b in derived['test']}
            or report.get('ranking_specifications_sha256') != natural_data.sha(report['ranking_specifications'])):
        raise ValueError('CPU-frozen full4x4 candidate/branch specifications changed')
    expected = {k: v for k, v in report.items() if k not in ('manifests', 'native_train_offsets')}
    expected['corpus_report_sha256'] = digest(CORPUS / 'report.json')
    if stage_report(EVIDENCE / 'cpu_contract.json') != expected: raise ValueError('public CPU contract differs')
    return report, rows, derived


def preflight():
    import torch
    from tokenizers import Tokenizer
    frozen, rows, relations = read_prepared()
    if digest(natural_data.TOKENIZER) != natural_data.TOK_SHA: raise ValueError('tokenizer changed')
    tok = Tokenizer.from_file(str(natural_data.TOKENIZER)); natural, replay = encode_old(rows, tok)
    if any(relation_summary(v, tok) != frozen['relation_reports'][s] for s, v in relations.items()):
        raise ValueError('actual derived encoder differs')
    if (exposure(natural, replay, frozen['relation_reports']['train']) != frozen['exposure']
            or evaluation_proof(evaluation_cases(rows, relations), tok) != frozen['evaluation_proof']):
        raise ValueError('actual training/evaluation consumer differs')
    if (rank_specifications(relations['test'], tok) != frozen['ranking_specifications']
            or old_input_proof(old_cases(rows, relations), tok) != frozen['original_a_evaluation_input_proof']):
        raise ValueError('actual CPU candidate/EOT-prefix or original990 prompt proof differs')
    if torch.cuda.is_initialized(): raise ValueError('CPU preflight initialized CUDA')
    print('[SUBJECT_ROLE_PREFLIGHT] source/code/encoder/native vector; no model/GPU', flush=True)
    return 0


def checkpoint(arm):
    if arm not in ARMS: raise ValueError('registered independent arm required')
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_subject_role_' + TAG + '_' + arm + '.pt')


def relation_micro(model, forward, positive, crossed, pad, eot, arm, device='cuda'):
    """One physical positive8 + crossed8x3 path for every arm, including CE."""
    from tinylm.train import mtp_sft as core
    import torch
    if arm not in ARMS or len(positive) != 8 or len(crossed) != 24:
        raise ValueError('relation micro requires two full graphs: positive8/cross24')
    x, _, _ = core.pad_records(positive, pad, device, fixed_width=1024, batch_size=8)
    p, pe, pn = loss.sequence_terms(model, forward(x, return_hidden=True), positive, eot)
    content = []; ends = []; counts = []
    for chunk in data.cross_micro_batches(crossed):
        cx, _, _ = core.pad_records(chunk, pad, device, fixed_width=1024, batch_size=8)
        c, ce, cn = loss.sequence_terms(model, forward(cx, return_hidden=True), chunk, eot)
        content.append(c); ends.append(ce); counts.extend(cn)
    c = torch.cat(content); ce = torch.cat(ends)
    matrix = loss.score_matrix(loss.content_means(p, pn), loss.content_means(c, counts))
    contrast = loss.row_contrast_sum(matrix, MODES[arm]) + ce.sum() * 0.
    return -(p + pe).sum(), contrast, dict(positive_rows=8, crossed_rows=24,
        crossed_x_tokens=sum(r.x_tokens for r in crossed), crossed_content_targets=sum(r.targets - 1 for r in crossed),
        padded_crossed_slots=24 * 1024, relation_questions=8, full_scored_sequences=32)


def finite(value, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (not positive or value > 0)


def validate_groups(groups):
    if (not isinstance(groups, list) or {v.get('optimizer') for v in groups} != {'adamw', 'muon'}
            or any(v.get('weight_decay') != 0. or not finite(v.get('lr'), True)
                   or type(v.get('parameters')) is not int or v['parameters'] <= 0 for v in groups)):
        raise ValueError('all actual optimizer groups need explicit WD0/finite LR/parameters')


def verify_training_report(report, arm, frozen, cost=False):
    expected_status = 'COST8_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING'
    if (report.get('status') != expected_status or report.get('arm') != arm or report.get('mode') != MODES[arm]
            or report.get('weight') != WEIGHTS[arm] or report.get('updates') != (8 if cost else UPDATES)
            or report.get('code_sha256') != info()['code_sha256']
            or report.get('corpus_sha256') != digest(CORPUS / 'report.json')
            or report.get('initial_core_sha256') != PARENT_CORE or report.get('checkpoint_written') != (not cost)):
        raise ValueError('same code/corpus/arm/parent complete update receipt required')
    validate_groups(report.get('actual_optimizer_groups'))
    count = 8 if cost else UPDATES
    manifest = report.get('event_manifest', {})
    if manifest.get('lineage') != dict(tag=TAG, arm=arm, mode=MODES[arm]): raise ValueError('training raw lineage differs')
    directory = EVIDENCE / (('cost_' if cost else 'train_') + arm)
    events = read_shards(directory, manifest, 'updates', count); times = report.get('step_seconds', [])
    if len(times) != count or any(not finite(v, True) for v in times): raise ValueError('complete finite timing cohort required')
    for i, event in enumerate(events):
        if (event.get('update') != i + 1 or event.get('step_seconds') != times[i]
                or event.get('lambda_weight') != WEIGHTS[arm]
                or any(not finite(event.get(k)) for k in ('correct_ce', 'native_ce', 'gradient_norm'))
                or type(event.get('relation_questions')) is not int
                or event['relation_questions'] < 0 or event['relation_questions'] % 8
                or (event['relation_questions'] and not finite(event.get('row_contrast')))):
            raise ValueError('raw training step/arm/finite denominators changed')
    if (report.get('grad_max') != max(e['gradient_norm'] for e in events)
            or report.get('clip_events') != sum(e['gradient_norm'] > 1. for e in events)
            or sum(e['assistant_targets'] for e in events) != report['totals']['assistant_targets']
            or sum(e['relation_questions'] for e in events) != report['totals']['relation_questions']):
        raise ValueError('raw gradient/clip/whole-update target recount differs')
    if not report['totals'].get('crossed_rows'): raise ValueError('actual full16 candidate path not exercised')
    if not cost:
        expected = frozen['exposure']
        if (any(report['totals'].get(k) != v for k, v in expected['four_pass'].items())
                or report['totals'].get('padded_positive_slots') != expected['padded_positive_slots']
                or report['totals'].get('padded_crossed_slots') != expected['padded_crossed_slots']
                or report['totals'].get('native_targets') != expected['native_targets']
                or report['totals'].get('relation_questions') != 32768
                or report.get('checkpoint') != str(checkpoint(arm).relative_to(ROOT))
                or digest(checkpoint(arm)) != report.get('checkpoint_sha256')
                or not isinstance(report.get('final_core_sha256'), str) or len(report['final_core_sha256']) != 64):
            raise ValueError('full896 exposure/checkpoint/body required')
    return events


def budget(hours=8., now=None, frozen=None):
    if not finite(hours, True) or hours > 8.: raise ValueError('explicit positive at-most8h experiment budget required')
    if frozen is None: frozen = read_prepared()[0]
    forecasts = {}; costs = {}; groups = None; completed_seconds = {}; pending_forecasts = {}
    for arm in ARMS:
        report = stage_report(EVIDENCE / ('cost_' + arm) / 'report.json')
        verify_training_report(report, arm, frozen, True)
        if groups is None: groups = report['actual_optimizer_groups']
        elif groups != report['actual_optimizer_groups']: raise ValueError('three cost arms changed optimizer groups')
        forecasts[arm] = max(report['step_seconds'][1:]) * UPDATES + 600
        costs[arm] = report['whole_seconds']
        if not finite(costs[arm], True): raise ValueError('actual whole cost8 wall time required')
        path = EVIDENCE / ('train_' + arm) / 'report.json'
        if path.exists():
            trained = stage_report(path); verify_training_report(trained, arm, frozen)
            if not finite(trained.get('whole_seconds'), True): raise ValueError('actual completed training wall required')
            completed_seconds[arm] = trained['whole_seconds']
        else: pending_forecasts[arm] = forecasts[arm]
    future = sum(pending_forecasts.values()) + EVALUATION_SECONDS + RESERVE_SECONDS
    remaining = authority(now=now); training_remaining = authority(training=True, now=now)
    result = dict(tag=TAG, training_forecasts=forecasts, actual_cost8_seconds=costs,
        evaluation_seconds=EVALUATION_SECONDS, record_reserve_seconds=RESERVE_SECONDS,
        completed_training_seconds=completed_seconds, pending_training_forecasts=pending_forecasts,
        future_seconds=future, total_study_forecast_seconds=future + sum(costs.values()) + sum(completed_seconds.values()),
        remaining_seconds=remaining, user_budget_seconds=hours * 3600,
        fits=future < remaining and sum(pending_forecasts.values()) < training_remaining
             and future + sum(costs.values()) + sum(completed_seconds.values()) <= hours * 3600,
        scope='worst7 warmed step extrapolation plus600s/arm; not an upper bound; source/quality not adopted')
    if not result['fits']: raise Pending('three arms/evaluation/records do not fit current budget: ' + json.dumps(result))
    return result


def dev_probe(model, rows, bundles, tok, pad, eot):
    import torch
    from tinylm.train import mtp_sft as core
    records = [core.encode_record(p['views'][str(v)], tok) for p in rows['dev'][:64] for v in (0, 1)]
    records += [r for b in bundles for r in data.encode_bundle(b, tok)[0]]
    total = 0.; targets = 0
    model.eval(); model.freeze_quant()
    try:
        with torch.no_grad():
            for start in range(0, len(records), 8):
                chunk = records[start:start + 8]
                x, _, _ = core.pad_records(chunk, pad, 'cuda', fixed_width=1024, batch_size=len(chunk))
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    c, e, _ = loss.sequence_terms(model, model(x, return_hidden=True), chunk, eot, False)
                total -= float((c + e).sum()); targets += sum(r.targets for r in chunk)
    finally:
        model.clear_quant(); model.train()
    if not targets or not finite(total): raise ValueError('complete DEV token denominator required')
    return dict(ce=total / targets, assistant_targets=targets, precision='BF16_AUTO_HEAD_FP32',
        scope='fixed correct DEV CE, not actual first answers or full validation')


def run(arm, cost, seconds, hours=8.):
    import torch
    from tinylm.train import mtp_sft as core
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    from scripts.p106b_native_windows import reader
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    began = time.perf_counter()
    if arm not in ARMS: raise ValueError('explicit independent arm required')
    frozen, rows, bundles = read_prepared(); authority(training=True)
    target = safe(EVIDENCE / (('cost_' if cost else 'train_') + arm))
    if target.exists() or (not cost and checkpoint(arm).exists()): raise FileExistsError('old trial/checkpoint preserved')
    reservation = None if cost else budget(hours, frozen=frozen)
    if cost and authority(training=True) <= min(seconds, 900) + 60: raise Pending('bounded cost8 does not fit')
    for name, h in (('train.bin', NATIVE_TRAIN_SHA), ('val.bin', NATIVE_VAL_SHA)):
        if digest(NATIVE / name) != h: raise ValueError('native cache changed')
    idle_before_gpu(); target.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(target, 'updates', limit=19_999_999)
    write(target / 'start.json', dict(info(), arm=arm, cost=cost, reservation=reservation))
    try:
        with wall_limit(bounded_wall(min(seconds, 900) if cost else seconds, training=True)):
            torch, model, cfg, tok, initial = load_parent()
            if initial != PARENT_CORE: raise ValueError('actual fresh P090B body differs')
            natural, replay = encode_old(rows, tok)
            encoded = [data.encode_bundle(b, tok) for b in bundles['train']]
            if relation_summary(bundles['train'], tok) != frozen['relation_reports']['train']: raise ValueError('training encoder changed')
            pad = tok.token_to_id('<pad>'); eot = tok.token_to_id('<|im_end|>')
            if (pad, eot) != (0, 4): raise ValueError('same actual chat32 pad/EOT required')
            windows = reader(ROOT, frozen)
            if len(windows) != 7168: raise ValueError('all new7168 native windows required')
            model = model.cuda(); torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
            torch.cuda.reset_peak_memory_stats()
            native_before = None if cost else native_probe(model)
            dev_before = None if cost else dev_probe(model, rows, bundles['dev'], tok, pad, eot)
            os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(prefix='p106b_subject_role_')
            forward = torch.compile(model, mode='default'); adam, muon, groups = make_optimizers(model); validate_groups(groups)
            if not cost and groups != stage_report(EVIDENCE / ('cost_' + arm) / 'report.json')['actual_optimizer_groups']:
                raise ValueError('fresh training optimizer groups differ from cost8')
            totals = Counter(); history = []; times = []; updates = 0; gmax = 0.; clips = 0
            for epoch in range(4):
                for group in loss.schedule(len(natural), len(encoded), len(replay), epoch):
                    authority(training=True); tick = time.perf_counter(); words, questions = denominators(group, natural, encoded, replay)
                    adam.zero_grad(set_to_none=True); muon.zero_grad(set_to_none=True)
                    stats = torch.zeros(2, device='cuda'); observed_words = observed_questions = 0
                    for micro in group:
                        positive = micro_records(micro, natural, encoded, replay)
                        if len(positive) != 8: raise ValueError('physical positive micro8 required')
                        with torch.autocast('cuda', dtype=torch.bfloat16):
                            if micro.kind == 'relation':
                                crossed = [r for i in micro.indices for r in encoded[i][1]]
                                correct, contrast, detail = relation_micro(model, forward, positive, crossed, pad, eot, arm)
                                totals.update({k: detail[k] for k in ('crossed_rows', 'crossed_x_tokens', 'crossed_content_targets', 'padded_crossed_slots')})
                                observed_questions += detail['relation_questions']
                            else:
                                x, y, seg = core.pad_records(positive, pad, 'cuda', fixed_width=1024, batch_size=8)
                                sums, _ = core.components(model, forward(x, return_hidden=True), y, seg, horizons=())
                                correct = sums[1]; contrast = correct * 0.
                            objective = loss.normalized_loss(correct, words, contrast, questions, WEIGHTS[arm])
                        if not bool(torch.isfinite(objective)): raise ValueError('nonfinite scoped objective')
                        objective.backward(); observed_words += sum(r.targets for r in positive)
                        totals.update(positive_rows=8, x_tokens=sum(r.x_tokens for r in positive),
                            assistant_targets=sum(r.targets for r in positive), padded_positive_slots=8192)
                        stats[0] += correct.detach(); stats[1] += contrast.detach()
                    if (observed_words, observed_questions) != (words, questions): raise ValueError('whole-update denominators differ')
                    native_records = [core.Record(v[:-1].astype('int64').tolist(), v[1:].astype('int64').tolist(), [1] * 1024)
                                      for v in windows[updates * 8:(updates + 1) * 8]]
                    nx, ny, ns = core.pad_records(native_records, pad, 'cuda', fixed_width=1024, batch_size=8)
                    with torch.autocast('cuda', dtype=torch.bfloat16):
                        sums, valid = core.components(model, forward(nx, return_hidden=True), ny, ns, horizons=())
                        native_loss = sums[1] / 8192
                    if valid[1] != 8192 or not bool(torch.isfinite(native_loss)): raise ValueError('native8192 target denominator differs')
                    native_loss.backward(); grad = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                    if not bool(torch.isfinite(grad)): raise ValueError('nonfinite gradient')
                    gmax = max(gmax, float(grad)); clips += int(grad > 1.)
                    adam.step(); muon.step(); updates += 1; totals.update(native_targets=8192, relation_questions=questions)
                    torch.cuda.synchronize(); times.append(time.perf_counter() - tick); values = stats.cpu().tolist()
                    event = dict(update=updates, epoch=epoch + 1, correct_ce=values[0] / words,
                        row_contrast=values[1] / questions if questions else None, assistant_targets=words,
                        relation_questions=questions, lambda_weight=WEIGHTS[arm], native_ce=float(native_loss.detach()),
                        gradient_norm=float(grad), clipped=bool(grad > 1.), step_seconds=times[-1])
                    writer.append(event)
                    if updates <= 8 or updates % 32 == 0: print('[SUBJECT_ROLE_UPDATE] ' + json.dumps(dict(arm=arm, **event)), flush=True)
                    if cost and updates == 8: break
                if cost: break
                history.append(dict(epoch=epoch + 1, updates=updates,
                    dev=dev_probe(model, rows, bundles['dev'], tok, pad, eot), native=native_probe(model)))
            if updates != (8 if cost else UPDATES): raise ValueError('planned updates incomplete')
            result = dict(info(), status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING',
                arm=arm, mode=MODES[arm], weight=WEIGHTS[arm], updates=updates, initial_core_sha256=initial,
                final_core_sha256=state_fingerprint(model), corpus_sha256=digest(CORPUS / 'report.json'),
                totals=dict(totals), history=history, native_before=native_before, dev_before=dev_before,
                step_seconds=times, grad_max=gmax, clip_events=clips, actual_optimizer_groups=groups,
                checkpoint_written=not cost, optimizer_saved=False, reservation=reservation,
                peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                memory_scope='torch allocator only; not whole device peak', semantic_adoption='NOT_DECIDED')
            if not cost:
                with safe(checkpoint(arm)).open('xb') as stream:
                    torch.save(dict(model=model.state_dict(), cfg=asdict(cfg), step=updates,
                        tokenizer_sha256=natural_data.TOK_SHA, optimizer_saved=False,
                        subject_role_course=dict(tag=TAG, arm=arm, mode=MODES[arm], epochs=4, weight=WEIGHTS[arm])), stream)
                result.update(checkpoint=str(checkpoint(arm).relative_to(ROOT)), checkpoint_sha256=digest(checkpoint(arm)))
            result['event_manifest'] = writer.close(lineage=dict(tag=TAG, arm=arm, mode=MODES[arm]))
            result['whole_seconds'] = time.perf_counter() - began
            verify_training_report(result, arm, frozen, cost); write(target / 'report.json', result)
    except BaseException as exc:
        status, code = failure_status(exc)
        write(target / 'error.json', dict(status=status, exit_code=code, arm=arm, exception=type(exc).__name__, message=str(exc), partial_raw_preserved=True))
        raise
    print('[SUBJECT_ROLE_FINAL] ' + result['status'] + '; quality evaluation pending', flush=True)
    return 0


def endpoint_identity(endpoint):
    if endpoint == 'parent':
        if digest(PARENT) != PARENT_SHA: raise ValueError('immutable parent checkpoint changed')
        return dict(endpoint=endpoint, checkpoint=str(PARENT.relative_to(ROOT)), checkpoint_sha256=PARENT_SHA,
            expected_core_sha256=PARENT_CORE, training_report_sha256=None)
    if endpoint not in ARMS: raise ValueError('registered endpoint required')
    frozen = read_prepared()[0]; path = EVIDENCE / ('train_' + endpoint) / 'report.json'
    report = stage_report(path); verify_training_report(report, endpoint, frozen)
    return dict(endpoint=endpoint, checkpoint=report['checkpoint'], checkpoint_sha256=report['checkpoint_sha256'],
        expected_core_sha256=report['final_core_sha256'], training_report_sha256=digest(path))


def validate_generation(answer, meta, messages, tok):
    from tinylm.chat.serialize import serialize
    prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True); ids = tok.encode(prompt).ids
    expected = dict(precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False,
        candidate_answers_supplied=False, prompt_sha256=natural_data.sha(prompt),
        prompt_ids_sha256=natural_data.sha(ids), prompt_tokens=len(ids), max_new=128,
        stop_token_sequences=[[tok.token_to_id('<|im_end|>')]])
    if (not isinstance(answer, str) or not isinstance(meta, dict) or any(meta.get(k) != v for k, v in expected.items())
            or type(meta.get('generated_tokens')) is not int or not 1 <= meta['generated_tokens'] <= 128
            or len(ids) + 128 > 1024 or meta.get('finish_reason') not in ('EOS', 'STOP_SEQUENCE', 'MAX_NEW', 'MAX_NEW_EOS_DISABLED', 'EOS_UNAVAILABLE')
            or not isinstance(meta.get('generated_ids_sha256'), str) or len(meta['generated_ids_sha256']) != 64):
        raise ValueError('actual candidate-free FP32 greedy prefix/termination receipt required')
    if (meta['finish_reason'] == 'STOP_SEQUENCE') != (meta.get('matched_stop_sequence') == [tok.token_to_id('<|im_end|>')]):
        raise ValueError('EOT/termination receipt differs')


def summarize_answers(events, cases, bundles, tok):
    from scripts.p106b_night_learning import qa_scores
    expected = {c['id']: c for c in cases}; seen = set(); totals = defaultdict(Counter); graph = defaultdict(list)
    if not expected or len(expected) != len(cases): raise ValueError('nonempty unique evaluation case inventory required')
    by_bundle = {b['bundle_id']: b for b in bundles}
    for event in events:
        c = expected.get(event.get('id'))
        if c is None or event['id'] in seen or event.get('case') != c: raise ValueError('unknown/duplicate/changed free-answer case')
        validate_generation(event.get('answer'), event.get('generation'), c['messages'], tok)
        seen.add(event['id']); stopped = event['generation']['finish_reason'] == 'STOP_SEQUENCE'
        key = c['lane'] + '|' + c['language'] + '|v' + str(c.get('view', 0))
        totals[key].update(responses=1, stopped=int(stopped), empty=int(not event['answer'].strip()))
        if c['lane'] == 'subject_role':
            b = by_bundle.get(c['bundle_id'])
            if b is None: raise ValueError('unknown source bundle')
            category = data.classify_answer(b, c['question_index'], event['answer'])
            correct = category == data.CORRECT
            totals[key].update({category: 1, 'exact': int(correct), 'exact_and_stopped': int(correct and stopped)})
            graph[c['language'], c['view'], c['group_id']].append((c['question_index'], correct))
        elif c['lane'] == 'natural': totals[key].update(qa_scores(event['answer'], c['aliases'], c['language']))
        elif c['lane'] == 'canary': totals[key].update(exact=int(data.original.exact_answer(event['answer']) == c['gold']))
        else: totals[key].update(unadjudicated=1)
    if seen != set(expected): raise Pending('actual first-answer cohort incomplete; no zero imputation')
    paired = defaultdict(Counter)
    for (language, view, _), values in graph.items():
        if sorted(q for q, _ in values) != [0, 1, 2, 3]: raise ValueError('four complete questions/source graph required')
        values = sorted(values); correct = [v for _, v in values]
        paired[language + '|v' + str(view)].update(graphs=1, all_four_exact=int(all(correct)),
            original_two_exact=int(all(correct[:2])), additional_two_exact=int(all(correct[2:])))
    return dict(actual_responses=len(seen), counts={k: dict(v) for k, v in sorted(totals.items())},
        graph_scores={k: dict(v) for k, v in sorted(paired.items())}, learning_seeds=1,
        primary='candidate-free greedy first answer; all4 questions correct per parent graph/language/view',
        natural_metric='previously observed development cohort; local KO character/EN word EM/F1',
        user_seen_quality='NOT_AUTOMATICALLY_ADJUDICATED', semantic_adoption='NOT_DECIDED')


def first_divergence_spec(positive, crossed, qi, ai):
    """Compare complete labels including EOT; content-prefix is an EOT branch.

    This branch diagnostic may score EOT when one whole content is a prefix.
    The training contrast still uses content-only means and never gains an
    EOT target from this diagnostic. Identical candidates/ties are not success.
    """
    pp = [i for i, y in enumerate(positive.y) if y != -100]
    cp = [i for i, y in enumerate(crossed.y) if y != -100]
    pt = [positive.y[i] for i in pp]; ct = [crossed.y[i] for i in cp]
    divergence = next((i for i, pair in enumerate(zip(pt, ct)) if pair[0] != pair[1]), None)
    if divergence is None or positive.x[:pp[divergence] + 1] != crossed.x[:cp[divergence] + 1]:
        raise ValueError('distinct complete candidates need a shared causal first-divergence prefix')
    includes_eot = divergence == len(pt) - 1 or divergence == len(ct) - 1
    return dict(question_index=qi, candidate_index=ai, branch_index=divergence,
        correct_token=pt[divergence], crossed_token=ct[divergence], includes_eot=includes_eot,
        branch_type='CONTENT_PREFIX_EOT_BRANCH' if includes_eot else 'CONTENT_INNER_DIVERGENCE',
        correct_predictor_position=pp[divergence])


def rank_specifications(bundles, tok):
    specs = {}
    for b in bundles:
        positive, crossed = data.encode_bundle(b, tok)
        records = dict(zip(data.POSITIVE_LAYOUT + data.CROSSED_LAYOUT, positive + crossed)); branches = []
        lengths = [r.targets - 1 for r in positive]
        for qi, ai in data.CROSSED_LAYOUT:
            branches.append(first_divergence_spec(records[qi, qi], records[qi, ai], qi, ai))
        specs[b['bundle_id']] = dict(content_lengths=lengths, branches=branches,
            record_sha256=natural_data.sha([record_identity(r) for r in positive + crossed]))
    return specs


def rank_probe(model, tok, bundles, actual_events):
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from tinylm.train import mtp_sft as core
    pad = tok.token_to_id('<pad>'); eot = tok.token_to_id('<|im_end|>'); output = []
    specs = rank_specifications(bundles, tok); actual = {e['id']: e for e in actual_events}
    with torch.no_grad(), sdpa_kernel(SDPBackend.MATH), torch.autocast('cuda', enabled=False):
        for b in bundles:
            positive, crossed = data.encode_bundle(b, tok); spec = specs[b['bundle_id']]
            px, _, _ = core.pad_records(positive, pad, 'cuda', fixed_width=1024, batch_size=4)
            ph = model(px, return_hidden=True); pc, pe, pn = loss.sequence_terms(model, ph, positive, eot, False)
            cross_content = []; cross_eot = []; cross_lengths = []
            for start in range(0, 12, 8):
                chunk = crossed[start:start + 8]
                cx, _, _ = core.pad_records(chunk, pad, 'cuda', fixed_width=1024, batch_size=len(chunk))
                cc, ce, cn = loss.sequence_terms(model, model(cx, return_hidden=True), chunk, eot, False)
                cross_content.extend(cc.cpu().tolist()); cross_eot.extend(ce.cpu().tolist()); cross_lengths.extend(cn)
            sums = [[None] * 4 for _ in range(4)]; ends = [[None] * 4 for _ in range(4)]
            for (qi, ai), content, end in zip(data.POSITIVE_LAYOUT + data.CROSSED_LAYOUT,
                    pc.cpu().tolist() + cross_content, pe.cpu().tolist() + cross_eot):
                sums[qi][ai] = content; ends[qi][ai] = end
            means = [[sums[q][a] / pn[a] for a in range(4)] for q in range(4)]
            first = []
            for branch in spec['branches']:
                logits = model._head_logits(ph[branch['question_index'], branch['correct_predictor_position']].reshape(1, 1, -1))[0, 0].float()
                gold = float(logits[branch['correct_token']]); other = float(logits[branch['crossed_token']])
                first.append(dict(branch, correct_logit=gold, crossed_logit=other, gap=gold - other))
            raw_answers = []
            for qi in range(4):
                event = actual.get(data.query_id(b, qi, 0))
                if event is None: raise Pending('view0 actual answer missing before TF diagnostics')
                raw_answers.append(dict(question_index=qi, answer_sha256=natural_data.sha(event['answer']),
                    error_type=data.classify_answer(b, qi, event['answer'])))
            output.append(dict(bundle_id=b['bundle_id'], group_id=b['parent_group_id'], language=b['language'], family=b['family'],
                content_sums=sums, content_means=means, eot_logp=ends, content_lengths=pn,
                first_divergence=first, actual_view0_answers=raw_answers, source_spec_sha256=natural_data.sha(spec),
                scope='teacher-forced view0 FP32 sums/own-length means/EOT; shared candidate prefix is not actual history'))
    return output


def summarize_ranks(events, bundles, specs, actual_events):
    expected = {b['bundle_id']: b for b in bundles}; actual = {e['id']: e for e in actual_events}; seen = set(); totals = defaultdict(Counter)
    if not expected or len(expected) != len(bundles): raise ValueError('nonempty unique TF source inventory required')
    for event in events:
        b = expected.get(event.get('bundle_id'))
        if b is None or b['bundle_id'] in seen: raise ValueError('unknown/duplicate TF source bundle')
        spec = specs[b['bundle_id']]
        if (event.get('group_id') != b['parent_group_id'] or event.get('language') != b['language']
                or event.get('family') != b['family'] or event.get('source_spec_sha256') != natural_data.sha(spec)
                or event.get('content_lengths') != spec['content_lengths']): raise ValueError('TF candidate source/count identity differs')
        for name in ('content_sums', 'content_means', 'eot_logp'):
            matrix = event.get(name)
            if (not isinstance(matrix, list) or len(matrix) != 4 or any(not isinstance(r, list) or len(r) != 4 for r in matrix)
                    or any(not finite(v) or v > 0 for r in matrix for v in r)): raise ValueError('finite nonpositive full4x4 raw scores required')
        means = event['content_means']; sums = event['content_sums']
        if means != [[sums[q][a] / spec['content_lengths'][a] for a in range(4)] for q in range(4)]:
            raise ValueError('own-length mean differs from saved FP32 sums')
        first = event.get('first_divergence')
        if not isinstance(first, list) or len(first) != 12: raise Pending('complete12 first-divergence comparisons required')
        for branch, required_branch in zip(first, spec['branches']):
            if (any(branch.get(k) != v for k, v in required_branch.items())
                    or any(not finite(branch.get(k)) for k in ('correct_logit', 'crossed_logit', 'gap'))
                    or branch['gap'] != branch['correct_logit'] - branch['crossed_logit']):
                raise ValueError('first-divergence token/prefix/raw logit difference differs')
        answers = []
        for qi in range(4):
            e = actual.get(data.query_id(b, qi))
            if e is None: raise Pending('same actual view0 answer required')
            answers.append(dict(question_index=qi, answer_sha256=natural_data.sha(e['answer']), error_type=data.classify_answer(b, qi, e['answer'])))
        if event.get('actual_view0_answers') != answers: raise ValueError('TF/actual-error binding differs')
        totals[b['language']].update(graphs=1,
            all4_rows_rank_correct=int(all(means[q][q] > means[q][a] for q, a in data.CROSSED_LAYOUT)),
            role_only_all4=int(all(means[q][q] > means[q][q ^ 1] for q in range(4))),
            other_subject_same_role_all4=int(all(means[q][q] > means[q][q ^ 2] for q in range(4))),
            first_divergence_all12_positive=int(all(v['gap'] > 0 for v in first)))
        seen.add(b['bundle_id'])
    if seen != set(expected): raise Pending('complete TF score cohort required')
    return {k: dict(v) for k, v in sorted(totals.items())}


def validate_evaluation(report, identity, cases, frozen):
    lineage = dict(tag=TAG, **identity)
    if (report.get('status') != 'ACTUAL_FIRST_ANSWERS_RECORDED' or report.get('lineage') != lineage
            or report.get('endpoint') != identity['endpoint'] or report.get('code_sha256') != info()['code_sha256']
            or report.get('corpus_sha256') != digest(CORPUS / 'report.json')
            or report.get('cases_sha256') != natural_data.sha(cases)
            or report.get('core_before') != identity['expected_core_sha256'] or report.get('core_after') != identity['expected_core_sha256']
            or any(report.get(k, {}).get('lineage') != lineage for k in ('answer_manifest', 'rank_manifest'))
            or report.get('model_training') is not False or report.get('weights_changed') is not False):
        raise ValueError('evaluation code/source/endpoint/core/raw identity differs')


def evaluate(endpoint, seconds):
    import gc
    import torch
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    from tinylm.infer.generate import _strip
    frozen, rows, bundles = read_prepared(); authority()
    cases = evaluation_cases(rows, bundles); identity = endpoint_identity(endpoint)
    target = safe(EVIDENCE / ('evaluate_' + endpoint)); local = safe(LOCAL / ('evaluate_' + endpoint))
    if target.exists() or local.exists(): raise FileExistsError('prior evaluation preserved')
    if authority() <= min(seconds, EVALUATION_SECONDS) + RESERVE_SECONDS: raise Pending('evaluation bound and final record reserve do not fit')
    idle_before_gpu(); target.mkdir(parents=True, exist_ok=False); local.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(local, 'answers', limit=19_999_999); began = time.perf_counter(); model = None
    try:
        with wall_limit(bounded_wall(seconds, reserve=RESERVE_SECONDS)):
            torch, model, cfg, tok, _ = load_parent()
            if endpoint != 'parent':
                saved = torch.load(ROOT / identity['checkpoint'], map_location='cpu', weights_only=True)
                if (saved.get('subject_role_course') != dict(tag=TAG, arm=endpoint, mode=MODES[endpoint], epochs=4, weight=WEIGHTS[endpoint])
                        or saved.get('tokenizer_sha256') != natural_data.TOK_SHA or saved.get('step') != UPDATES):
                    raise ValueError('saved child course/step/tokenizer differs')
                model.load_state_dict(_strip(saved['model']), strict=True); del saved
            if evaluation_proof(cases, tok) != frozen['evaluation_proof']: raise ValueError('runtime evaluation prefix proof differs')
            if rank_specifications(bundles['test'], tok) != frozen['ranking_specifications']:
                raise ValueError('runtime TF candidate/EOT-prefix specifications differ from CPU freeze')
            before = state_fingerprint(model)
            if before != identity['expected_core_sha256']: raise ValueError('actual evaluated body differs')
            model = model.cuda(); model.eval(); model.freeze_quant()
            torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
            events = []
            with torch.no_grad():
                for i, case in enumerate(cases):
                    answer, meta = emit_answer(model, cfg, tok, case['messages'])
                    validate_generation(answer, meta, case['messages'], tok)
                    event = dict(id=case['id'], case=case, answer=answer, generation=meta)
                    events.append(event); writer.append(event)
                    if (i + 1) % 128 == 0: print('[SUBJECT_ROLE_EVAL] ' + json.dumps(dict(endpoint=endpoint, responses=i + 1, expected=len(cases))), flush=True)
            ranks = rank_probe(model, tok, bundles['test'], events)
            summary = summarize_answers(events, cases, bundles['test'], tok)
            rank_summary = summarize_ranks(ranks, bundles['test'], rank_specifications(bundles['test'], tok), events)
            model.clear_quant(); native = native_probe(model); after = state_fingerprint(model)
            if before != after: raise ValueError('evaluation changed model weights')
            lineage = dict(tag=TAG, **identity); manifest = writer.close(lineage=lineage); verify(local, manifest)
            rank_writer = ShardWriter(local, 'rank', limit=19_999_999)
            for row in ranks: rank_writer.append(row)
            rank_manifest = rank_writer.close(lineage=lineage); verify(local, rank_manifest)
            result = dict(info(), status='ACTUAL_FIRST_ANSWERS_RECORDED', endpoint=endpoint, lineage=lineage,
                corpus_sha256=digest(CORPUS / 'report.json'), cases_sha256=natural_data.sha(cases),
                core_before=before, core_after=after, summary=summary, rank_summary=rank_summary,
                answer_manifest=manifest, rank_manifest=rank_manifest,
                answer_manifest_sha256=digest(local / 'answers_shards_manifest.json'),
                rank_manifest_sha256=digest(local / 'rank_shards_manifest.json'), native32_fp32=native,
                whole_seconds=time.perf_counter() - began, model_training=False, weights_changed=False, checkpoints_written=0)
            validate_evaluation(result, identity, cases, frozen); write(target / 'report.json', result)
    except BaseException as exc:
        status, code = failure_status(exc)
        write(target / 'error.json', dict(status=status, exit_code=code, endpoint=endpoint, exception=type(exc).__name__, message=str(exc), partial_raw_preserved=True))
        raise
    finally:
        del model; gc.collect(); torch.cuda.empty_cache()
    return 0


def paired_graphs(left, right, cases, draws=2000):
    a = {e['id']: e for e in left}; b = {e['id']: e for e in right}; grouped = defaultdict(lambda: defaultdict(list)); result = {}
    for c in cases:
        if c['lane'] != 'subject_role': continue
        if c['id'] not in a or c['id'] not in b: raise Pending('paired actual response missing')
        grouped[c['language'], c['view']][c['group_id']].append((
            data.original.exact_answer(a[c['id']]['answer']) == c['gold'],
            data.original.exact_answer(b[c['id']]['answer']) == c['gold']))
    for (language, view), graphs in grouped.items():
        if any(len(v) != 4 for v in graphs.values()): raise ValueError('complete graph4 paired answers required')
        differences = [int(all(v[1] for v in rows)) - int(all(v[0] for v in rows)) for rows in graphs.values()]
        rng = random.Random(20261019); n = len(differences)
        sampled = sorted(100 * sum(differences[rng.randrange(n)] for _ in range(n)) / n for _ in range(draws))
        result[language + '|v' + str(view)] = dict(independent_graphs=n,
            delta_all_four_pp=100 * sum(differences) / n,
            descriptive_ci95_pp=[sampled[int(.025 * (draws - 1))], sampled[int(.975 * (draws - 1))]],
            learning_seeds=1, draws=draws, multiple_comparisons_adjusted=False)
    return result


def readback(endpoint=None):
    from tokenizers import Tokenizer
    frozen, rows, bundles = read_prepared(); cases = evaluation_cases(rows, bundles)
    if digest(natural_data.TOKENIZER) != natural_data.TOK_SHA: raise ValueError('tokenizer changed')
    tok = Tokenizer.from_file(str(natural_data.TOKENIZER))
    if evaluation_proof(cases, tok) != frozen['evaluation_proof']: raise ValueError('exact evaluation prefix proof required')
    selected = (endpoint,) if endpoint is not None else ARMS
    reports = {}; outputs = {}
    specs = rank_specifications(bundles['test'], tok)
    if specs != frozen['ranking_specifications']: raise ValueError('raw TF source specification differs from CPU freeze')
    for label in selected:
        identity = endpoint_identity(label); path = EVIDENCE / ('evaluate_' + label) / 'report.json'
        report = stage_report(path); validate_evaluation(report, identity, cases, frozen)
        local = LOCAL / ('evaluate_' + label)
        for stem, field in (('answers', 'answer'), ('rank', 'rank')):
            manifest_path = local / (stem + '_shards_manifest.json')
            if digest(manifest_path) != report.get(field + '_manifest_sha256') or required(manifest_path) != report.get(field + '_manifest'):
                raise ValueError('evaluation manifest hash/report differs')
        events = read_shards(local, report['answer_manifest'], 'answers', len(cases))
        ranks = read_shards(local, report['rank_manifest'], 'rank', len(bundles['test']))
        if summarize_answers(events, cases, bundles['test'], tok) != report.get('summary'):
            raise ValueError('actual first-answer raw recount differs')
        if summarize_ranks(ranks, bundles['test'], specs, events) != report.get('rank_summary'):
            raise ValueError('raw candidate/first-divergence/actual-error recount differs')
        reports[label] = report; outputs[label] = events
    result = dict(info(), status='RAW_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION',
        cases_sha256=natural_data.sha(cases), source_reports_sha256={k: digest(EVIDENCE / ('evaluate_' + k) / 'report.json') for k in reports},
        summaries={k: v['summary'] for k, v in reports.items()}, learning_seeds=1,
        model_loaded=False, model_training=False, errors=0, semantic_adoption='USER_REVIEW_REQUIRED')
    if endpoint is None:
        result['role_only_minus_ce'] = paired_graphs(outputs['ce'], outputs['role_only'], cases)
        result['all_axes_minus_ce'] = paired_graphs(outputs['ce'], outputs['all_axes'], cases)
        result['all_axes_minus_role_only'] = paired_graphs(outputs['role_only'], outputs['all_axes'], cases)
    write(EVIDENCE / ('readback' + (('_' + endpoint) if endpoint else '') + '.json'), result)
    print('[SUBJECT_ROLE_READBACK] ' + json.dumps(result, ensure_ascii=False), flush=True)
    return 0


def old_cases(rows, bundles):
    """Reconstruct the exact original A case schema/order, not new4-query cases."""
    cases = []
    for b in bundles['test']:
        parent = b['parent_bundle']
        for view in range(3):
            for qi in range(2):
                row = data.original.render(parent, qi, view=view)
                cases.append(dict(id=data.original.sha(['RELATION', parent['bundle_id'], view, qi]), lane='relation',
                    language=parent['language'], family=parent['family'], group_id=parent['group_id'],
                    bundle_id=parent['bundle_id'], view=view, question_index=qi,
                    messages=row['messages'][:1], gold=parent['answers'][qi]))
    current = evaluation_cases(rows, bundles)
    for lane in ('natural', 'canary', 'user_seen'): cases.extend(c for c in current if c['lane'] == lane)
    return cases


def old_input_proof(cases, tok):
    """Exact frozen-A input proof schema, including source order and token IDs."""
    from tinylm.chat.serialize import serialize
    entries = []; counts = Counter()
    for case in cases:
        if [m['role'] for m in case['messages']] != ['user']: raise ValueError('old first-answer input must remain user-only')
        prompt = serialize(dict(messages=case['messages']), 'chatml', add_generation_prompt=True)
        ids = tok.encode(prompt).ids
        if not ids or len(ids) + 128 > 1024: raise ValueError('complete original A990 prompt budget differs')
        entries.append([case['id'], len(ids), natural_data.sha(ids)])
        counts[case['lane'] + '|' + case['language']] += 1
    if not entries: raise ValueError('nonempty original prompt proof required')
    return dict(cases_sha256=natural_data.sha(cases), actual_prompt_ids_sha256=natural_data.sha(entries),
        responses=len(cases), lane_counts=dict(counts), max_prompt_tokens=max(v[1] for v in entries),
        context=1024, generation_budget=128, oracle_candidates_in_generation=False)


def old_a_binding(rows, bundles, tok):
    readback = stage_report(A_EVIDENCE / 'readback.json'); source = stage_report(A_CORPUS / 'report.json')
    cases = old_cases(rows, bundles); expected = {c['id']: c for c in cases}; identities = {}; raw = {}; hashes = {}
    if readback.get('status') != 'RAW_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION':
        raise Pending('complete original A three-endpoint raw readback required')
    if (readback.get('errors') != 0 or readback.get('tag') != 'p106b_relation_bind_v1_s1337'
            or readback.get('code_sha256') != source['code_sha256'] or readback.get('cases_sha256') != natural_data.sha(cases)
            or set(readback.get('source_reports_sha256', {})) != {'parent', 'ce', 'contrast'}):
        raise ValueError('original A completed raw readback source binding changed')
    for label in ('parent', 'ce', 'contrast'):
        if label == 'parent':
            identity = dict(endpoint=label, checkpoint=str(PARENT.relative_to(ROOT)), checkpoint_sha256=PARENT_SHA,
                expected_core_sha256=PARENT_CORE, training_report_sha256=None)
        else:
            path = A_EVIDENCE / ('train_' + label) / 'report.json'; training = stage_report(path)
            cp = ROOT / 'runs/ckpt' / ('m100s10_ko-en_relation_p106b_relation_bind_v1_s1337_' + label + '.pt')
            if (training.get('status') != 'TRAIN_COMPLETE_EVALUATION_PENDING' or training.get('updates') != 768
                    or training.get('arm') != label or training.get('code_sha256') != source['code_sha256']
                    or training.get('corpus_sha256') != digest(A_CORPUS / 'report.json')
                    or training.get('initial_core_sha256') != PARENT_CORE
                    or training.get('checkpoint') != str(cp.relative_to(ROOT)) or digest(cp) != training.get('checkpoint_sha256')):
                raise ValueError('exact original trained endpoint required')
            identity = dict(endpoint=label, checkpoint=training['checkpoint'], checkpoint_sha256=training['checkpoint_sha256'],
                expected_core_sha256=training['final_core_sha256'], training_report_sha256=digest(path))
        if digest(ROOT / identity['checkpoint']) != identity['checkpoint_sha256']: raise ValueError('old endpoint byte hash changed')
        path = A_EVIDENCE / ('evaluate_' + label) / 'report.json'; report = stage_report(path)
        lineage = dict(tag='p106b_relation_bind_v1_s1337', **identity)
        if (report.get('status') != 'ACTUAL_FIRST_ANSWERS_RECORDED' or report.get('lineage') != lineage
                or report.get('code_sha256') != source['code_sha256'] or report.get('cases_sha256') != natural_data.sha(cases)
                or report.get('core_before') != identity['expected_core_sha256'] or report.get('core_after') != identity['expected_core_sha256']
                or digest(path) != readback['source_reports_sha256'][label]):
            raise ValueError('old endpoint/raw-readback/body binding differs')
        directory = ROOT / 'test_result/evidence/local/p106b_relation_bind_v1_s1337' / ('evaluate_' + label)
        for stem, field, n in (('answers', 'answer', len(cases)), ('rank', 'rank', len(bundles['test']))):
            if (report[field + '_manifest'].get('lineage') != lineage
                    or digest(directory / (stem + '_shards_manifest.json')) != report.get(field + '_manifest_sha256')):
                raise ValueError('old manifest lineage/hash differs')
            values = read_shards(directory, report[field + '_manifest'], stem, n)
            if stem == 'answers':
                seen = set()
                for e in values:
                    c = expected.get(e.get('id'))
                    if c is None or e['id'] in seen or e.get('case') != c: raise ValueError('old raw question/gold changed')
                    validate_generation(e.get('answer'), e.get('generation'), c['messages'], tok); seen.add(e['id'])
                if seen != set(expected): raise Pending('old full990 cohort missing')
                raw[label] = values
        identities[label] = identity; hashes[label] = digest(path)
    return dict(readback_sha256=digest(A_EVIDENCE / 'readback.json'), source_reports_sha256=hashes,
        identities=identities, answers=raw, cases_sha256=natural_data.sha(cases))


def probe_old(label, seconds):
    """Extra2x4 TF only; original990 free answers remain immutable evidence."""
    import gc
    import torch
    from tokenizers import Tokenizer
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from tinylm.train import mtp_sft as core
    from tinylm.infer.generate import _strip
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    if label not in ('ce', 'contrast'): raise ValueError('old CE/contrast model required')
    frozen, rows, bundles = read_prepared(); tok = Tokenizer.from_file(str(natural_data.TOKENIZER))
    if rank_specifications(bundles['test'], tok) != frozen['ranking_specifications']:
        raise ValueError('old2x4 candidate/branch subset differs from CPU-frozen4x4 source')
    source = old_a_binding(rows, bundles, tok); identity = source['identities'][label]
    target = safe(EVIDENCE / ('probe_old_' + label)); local = safe(LOCAL / ('probe_old_' + label))
    if target.exists() or local.exists(): raise FileExistsError('old-model diagnostic output preserved')
    if authority() <= seconds + RESERVE_SECONDS: raise Pending('old-model diagnostic/record reservation does not fit')
    idle_before_gpu(); target.mkdir(parents=True, exist_ok=False); local.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(local, 'rank2x4', limit=19_999_999); model = None
    try:
        with wall_limit(bounded_wall(seconds, reserve=RESERVE_SECONDS)):
            torch, model, cfg, actual_tok, _ = load_parent()
            if actual_tok.to_str() != tok.to_str(): raise ValueError('same tokenizer required')
            saved = torch.load(ROOT / identity['checkpoint'], map_location='cpu', weights_only=True)
            model.load_state_dict(_strip(saved['model']), strict=True); del saved
            before = state_fingerprint(model)
            if before != identity['expected_core_sha256']: raise ValueError('actual old model body differs')
            model = model.cuda(); model.eval(); model.freeze_quant(); actual = {e['id']: e for e in source['answers'][label]}
            pad = tok.token_to_id('<pad>'); eot = tok.token_to_id('<|im_end|>'); count = 0
            with torch.no_grad(), sdpa_kernel(SDPBackend.MATH), torch.autocast('cuda', enabled=False):
                for b in bundles['test']:
                    records = [data.original.complete_record(data.render(b, q, a), tok) for q in range(2) for a in range(4)]
                    x, _, _ = core.pad_records(records, pad, 'cuda', fixed_width=1024, batch_size=8)
                    hidden = model(x, return_hidden=True); content, ends, lengths = loss.sequence_terms(model, hidden, records, eot, False)
                    sums = content.cpu().tolist(); ending = ends.cpu().tolist(); branches = []
                    for q in range(2):
                        p = records[4 * q + q]; pp = [i for i, y in enumerate(p.y) if y != -100]; pt = [p.y[i] for i in pp]
                        for a in range(4):
                            if a == q: continue
                            branch = first_divergence_spec(p, records[4 * q + a], q, a)
                            logits = model._head_logits(hidden[4 * q + q, branch['correct_predictor_position']].reshape(1, 1, -1))[0, 0].float()
                            gold = float(logits[branch['correct_token']]); cross = float(logits[branch['crossed_token']])
                            branches.append(dict(branch, correct_logit=gold, crossed_logit=cross, gap=gold - cross))
                    old_answers = [actual[data.query_id(b, q)] for q in range(2)]
                    writer.append(dict(bundle_id=b['bundle_id'], parent_bundle_id=b['parent_bundle_id'], group_id=b['parent_group_id'],
                        language=b['language'], content_lengths=[lengths[q:q + 4] for q in (0, 4)],
                        content_sums=[sums[:4], sums[4:]], content_means=[[sums[i] / lengths[i] for i in range(q, q + 4)] for q in (0, 4)],
                        eot_logp=[ending[:4], ending[4:]], first_divergence=branches,
                        actual_original_answer_sha256=[natural_data.sha(e['answer']) for e in old_answers],
                        actual_original_error_types=[data.classify_answer(b, q, e['answer']) for q, e in enumerate(old_answers)]))
                    count += 1
            model.clear_quant(); after = state_fingerprint(model)
            if before != after: raise ValueError('read-only probe changed old weights')
            lineage = dict(tag=TAG, probe='ORIGINAL_A_TWO_QUESTIONS_FOUR_CANDIDATES', **identity)
            manifest = writer.close(lineage=lineage); verify(local, manifest)
            write(target / 'report.json', dict(info(), status='OLD_2X4_TF_DIAGNOSTIC_COMPLETE', model=label,
                original_readback_sha256=source['readback_sha256'], original_source_reports_sha256=source['source_reports_sha256'],
                lineage=lineage, core_before=before, core_after=after, bundles=count, additional_free_answers=0,
                rank_manifest=manifest, rank_manifest_sha256=digest(local / 'rank2x4_shards_manifest.json'), model_training=False, weights_changed=False))
    finally:
        del model; gc.collect(); torch.cuda.empty_cache()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'preflight', 'cost', 'train', 'evaluate', 'readback', 'budget', 'probe_old'), required=True)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--endpoint', choices=ENDPOINTS)
    parser.add_argument('--model', choices=('ce', 'contrast'))
    parser.add_argument('--max-wall-sec', type=int, default=7200)
    parser.add_argument('--budget-hours', type=float, default=8.)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    if not 60 <= args.max_wall_sec <= 21600 or not finite(args.budget_hours, True) or args.budget_hours > 8:
        parser.error('bounded60..21600 wall and positive at-most8h budget required')
    if args.mode in ('cost', 'train') and args.arm is None: parser.error('explicit independent arm required')
    if args.mode == 'evaluate' and args.endpoint is None: parser.error('one explicit evaluation endpoint required')
    if args.mode == 'probe_old' and args.model is None: parser.error('old model ce/contrast required')
    if args.arm is not None and args.mode not in ('cost', 'train'): parser.error('arm belongs only to cost/train')
    if args.endpoint is not None and args.mode not in ('evaluate', 'readback'): parser.error('endpoint belongs only to evaluate/readback')
    if args.model is not None and args.mode != 'probe_old': parser.error('old model belongs only to probe_old')
    if args.check_only:
        print('[SUBJECT_ROLE_CHECK_ONLY] ' + json.dumps(info())); return 0
    try:
        if args.mode == 'prepare': return prepare()
        if args.mode == 'preflight': return preflight()
        if args.mode == 'budget': print(json.dumps(budget(args.budget_hours))); return 0
        if args.mode == 'readback': return readback(args.endpoint)
        if args.mode == 'evaluate': return evaluate(args.endpoint, args.max_wall_sec)
        if args.mode == 'probe_old': return probe_old(args.model, args.max_wall_sec)
        return run(args.arm, args.mode == 'cost', args.max_wall_sec, args.budget_hours)
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        status, code = failure_status(exc)
        if code == 9:
            import traceback
            traceback.print_exc()
        print('[SUBJECT_ROLE_FINAL] ' + status + str(code) + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__': raise SystemExit(main())
