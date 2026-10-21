#!/usr/bin/env python3
"""Independent P078 Stage3 learned prefix-router pilot (READY=False).

Closed balanced_count V3 body only. R1 parent is explicitly resource-only.
No old Runtime/authority/clock override. check-only opens source bytes only.
Actual stages require root-owned current authorization, cost and source pins.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import p078_prefix_router as router
from scripts import diag_p078_route_training as base

READY = False
TAG = 'p078_prefix_router_v1_s1337'
MODES = ('toy', 'prepare', 'cost', 'budget', 'labels', 'fit', 'evaluate', 'readback')
CODE = tuple(dict.fromkeys(('scripts/p078_prefix_router.py', 'scripts/test_p078_prefix_router.py',
    'scripts/diag_p078_prefix_router.py', *base.CODE)))
MAX_FAMILY = 144000
sha = router.route.sha
Hold = base.Hold


def namespace(args): return TAG + ('_resourceonly_r1' if args.resource_only_r1 else '')
def root_path(relative): return base.path(relative)
def report_name(args, mode): return 'test_result/evidence/' + namespace(args) + '/' + mode + '/report.json'
def activity_name(args, mode): return 'test_result/evidence/' + namespace(args) + '/activity_' + mode + '.json'
def raw_name(args, mode): return 'runs/eval/' + namespace(args) + '/' + mode


def safe_output(args, relative):
    allowed = ('test_result/evidence/' + namespace(args) + '/', 'runs/eval/' + namespace(args) + '/')
    if not any(str(relative).startswith(v) for v in allowed): raise ValueError('new router namespace only')
    return root_path(relative)


def write(args, relative, value):
    p = safe_output(args, relative)
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(raw) >= 20_000_000: raise ValueError('small JSON evidence must be below20MB')
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as stream: stream.write(raw)


def signature(args):
    return dict(schema=router.SCHEMA, tag=namespace(args), source_sha256={v: base.digest(root_path(v)) for v in CODE},
        corpus=base.CLEAN_CORPUS, corpus_report_sha256=args.corpus_sha256, tokenizer_sha256=base.TOK_SHA,
        frozen_body=base.PARENT if args.resource_only_r1 else base.cp_name('balanced_count', args),
        body_source_signature_sha256=sha(base.signature(args)), body_training='V3_BALANCED_COUNT_4PASS_704_ONLY',
        resource_only_r1=args.resource_only_r1, body_training_here=False, mtp=False, teacher=False,
        head=router.HEAD, feature=router.FEATURE_SPEC, actions=[1, 2, 3],
        split=dict(seed=1337, min_rows=128, min_language=64, unit='CONNECTED_ARTICLE_CONTEXT_ROOT_COMPONENT',
            seed_search=False, body_VAL_already_used=True, fully_blind=False),
        policy='ONLINE_PREFIX_ONLY_ARGMIN_PREDICTED_RELATIVE_CE_UNDER_FIXED_QUOTA_1_2_2_3',
        controls=list(router.POLICIES), primary='MATCHED_CHOSEN_ACTION_CE_AND_ACTUAL_FIRST_ANSWER',
        generation=dict(precision='FP32_MATH', tf32=False, cache=False, max_new=128, top_k=1, temperature=0., mtp=False),
        stdout_first_answer_samples=dict(cases=[0, 1], each_policy=True, preselected=True),
        cost_generation_selection='TWO_LONGEST_TRAIN_PREFIXES_FITTING_FULL_128; length then index; timing only, no answer selection',
        feature_overhead='MEASURE_SEPARATELY; visit equality is not FLOP/token/time equality',
        historical_gate='P078_R2_CROP_R2_NEGATIVE_AND_P070B_NUMERICAL_TOLERANCE_UNCHANGED')


def corpus_rows(args):
    report = base.inputs(args)
    if args.corpus != base.CLEAN_CORPUS or base.update_count(report) != 704: raise Hold('exact V3 22528x4/704 corpus required')
    from scripts.p101a_sft_mtp_data import stream_rows
    result = {}
    for split in ('train', 'val'):
        for part in report['manifests'][split]['shards']: root_path(args.corpus + '/' + part['path'])
        result[split] = list(stream_rows(root_path(args.corpus), report['manifests'][split]))
        if len(result[split]) != report['manifests'][split]['rows']: raise ValueError('actual pinned row count differs')
    if len(result['train']) != 22528 or len(result['val']) != 512: raise Hold('declared V3 train/VAL counts differ; no subset fallback')
    return report, result


def prepare(args):
    corpus, rows = corpus_rows(args); manifest = router.split_manifest(rows['val'])
    return dict(status='ROUTER_SPLIT_PREPARED_BODY_NOT_LOADED', split_manifest=manifest,
        train_rows=len(rows['train']), train_rows_sha256=sha([router.row_sha(r) for r in rows['train']]),
        val_rows_sha256=sha([router.row_sha(r) for r in rows['val']]), corpus_manifests=corpus['manifests'],
        corpus_counts=corpus['counts'], actual_unique_train_x_tokens=corpus['actual_unique_train_x_tokens'],
        model_loads=0, checkpoint_tensor_loads=0, tokenizer_loads=0,
        feature_labels='NOT_RUN', root_scope='explicit source lineage and normalized exact context/question, not semantic translation equivalence')


def authority(args, info):
    if not args.authorization or not args.authorization_sha256 or not args.authorization.startswith('handoff/audit/'):
        raise Hold('root-owned current independent router authorization required')
    if base.digest(root_path(args.authorization)) != args.authorization_sha256: raise ValueError('authorization byte pin changed')
    auth = base.read(args.authorization)
    now = datetime.now(timezone.utc); end = datetime.fromisoformat(auth['expires_at'])
    preparation = args.mode == 'prepare'; body_pin = auth.get('body_checkpoint_sha256')
    valid_body = ((preparation and body_pin is None) or (isinstance(body_pin, str) and len(body_pin) == 64
        and all(c in '0123456789ABCDEF' for c in body_pin)))
    if (auth.get('schema') != 'P078_PREFIX_ROUTER_EXECUTION_AUTHORIZATION_V1' or auth.get('tag') != namespace(args)
            or auth.get('input_signature_sha256') != sha(info)
            or (type(auth.get('allow_gpu_training')) is not bool if preparation else auth.get('allow_gpu_training') is not True)
            or auth.get('max_family_seconds') != MAX_FAMILY or end.tzinfo is None
            or type(auth.get('max_worker_seconds')) is not int or args.max_wall_sec > auth['max_worker_seconds']
            or auth.get('resource_only_r1') is not args.resource_only_r1 or not valid_body):
        raise Hold('exact current source/input/body/resource/40h authority required')
    remaining = (end - now).total_seconds()
    if remaining <= 0: raise Hold('router execution authorization expired')
    return auth, remaining


def closed(args, mode):
    info = signature(args)
    try:
        value = base.read(report_name(args, mode)); activity = base.read(activity_name(args, mode))
    except FileNotFoundError as exc:
        raise Hold('required closed router stage NOT_RUN: ' + mode) from exc
    auth = activity.get('authorization', {}); begin, end = (datetime.fromisoformat(activity[k]) for k in ('started_at', 'ended_at'))
    seconds = activity.get('seconds'); cap = activity.get('max_wall_sec'); admission = activity.get('admission_remaining')
    if (value.get('input') != info or activity.get('input') != info or value.get('mode') != mode or activity.get('mode') != mode or activity.get('complete') is not True
            or activity.get('returncode') != 0 or activity.get('report_sha256') != base.digest(root_path(report_name(args, mode)))
            or type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0
            or type(cap) is not int or not 60 <= cap <= MAX_FAMILY or seconds > cap + 30
            or type(admission) not in (int, float) or not math.isfinite(admission) or admission < cap
            or begin.tzinfo is None or end.tzinfo is None or begin > end
            or end > datetime.fromisoformat(auth['expires_at'])
            or activity.get('pid') != activity.get('pgid') or type(activity.get('pid')) is not int or activity['pid'] < 1
            or auth.get('schema') != 'P078_PREFIX_ROUTER_EXECUTION_AUTHORIZATION_V1'
            or auth.get('tag') != namespace(args) or auth.get('input_signature_sha256') != sha(info)
            or (type(auth.get('allow_gpu_training')) is not bool if mode == 'prepare' else auth.get('allow_gpu_training') is not True)
            or auth.get('resource_only_r1') is not args.resource_only_r1
            or auth.get('max_family_seconds') != MAX_FAMILY or auth.get('max_worker_seconds', 0) < cap
            or activity.get('authorization_canonical_sha256') != sha(auth)
            or value.get('authorization') != auth or value.get('authorization_sha256') != activity.get('authorization_sha256')
            or (mode not in ('prepare', 'budget') and value.get('body', {}).get('checkpoint_sha256') != auth.get('body_checkpoint_sha256'))):
        raise ValueError('closed exact source/input/time/body router receipt required')
    return value


def prepared(args):
    old = closed(args, 'prepare'); fresh = prepare(args)
    if any(old[k] != fresh[k] for k in fresh): raise ValueError('prepared split/rows/manifest changed')
    return old


def spent(args, info):
    total = 0.; directory = root_path('test_result/evidence/' + namespace(args))
    for file in directory.glob('activity_*.json') if directory.exists() else ():
        value = base.read(str(file.relative_to(ROOT)))
        if value.get('input') != info or value.get('complete') is not True: raise Hold('prior incomplete/source-different router stage preserved')
        v = value.get('seconds')
        if type(v) not in (int, float) or not math.isfinite(v) or v < 0: raise ValueError('finite actual family time required')
        total += v
    return total


def body_evidence(args):
    if args.resource_only_r1:
        return dict(checkpoint=base.PARENT, checkpoint_sha256=base.PARENT_SHA, scientific_body=False,
            label_quality='NOT_MEASURED_RESOURCE_ONLY_PARENT_R1')
    try:
        value = base.closed(args, 'train', 'balanced_count')
    except FileNotFoundError as exc:
        raise Hold('predeclared closed balanced_count704 body not created; scientific stages HOLD') from exc
    if (value.get('updates') != 704 or value.get('status') != 'ROUTE_SFT_COMPLETE_EVAL_REVIEW_REQUIRED'
            or value.get('checkpoint_writes') != 1 or value.get('arm') != 'balanced_count'
            or value.get('checkpoint') != base.cp_name('balanced_count', args)):
        raise Hold('closed full balanced_count704 body is not available; no R1 scientific fallback')
    if not root_path(base.cp_name('balanced_count', args)).is_file(): raise Hold('closed balanced704 checkpoint is absent; no parent fallback')
    return dict(checkpoint=base.cp_name('balanced_count', args), checkpoint_sha256=value['checkpoint_sha256'],
        core_sha256=value['final_core_sha256'],
        closed_report_sha256=base.digest(root_path(base.report_name('train', 'balanced_count', args))),
        closed_activity_sha256=base.digest(root_path(base.activity_name('train', 'balanced_count', args))), scientific_body=True)


@contextmanager
def frozen_body(args):
    evidence = body_evidence(args); auth, _ = authority(args, signature(args))
    if auth['body_checkpoint_sha256'] != evidence['checkpoint_sha256']: raise ValueError('root-authorized body differs')
    with base.loaded(args, 'balanced_count', trained=not args.resource_only_r1) as (torch, model, cfg, tok, core, reference):
        torch.set_num_threads(router.HEAD['cpu_threads'])
        router.freeze_body(model); before = reference.state_fingerprint(model)
        if before != core or (evidence.get('core_sha256') is not None and core != evidence['core_sha256']):
            raise ValueError('body changed while freezing flags or differs from closed full body core')
        evidence = dict(evidence, core_sha256=core, feature_width=3 * (cfg.emb_rank or cfg.dim) + 2,
            geometry=dict(n_layers=cfg.n_layers, n_prelude=cfg.n_prelude, n_middle=cfg.n_middle, n_coda=cfg.n_coda), owners=list(model.owner))
        try: yield torch, model, cfg, tok, evidence
        finally:
            if any(p.requires_grad or p.grad is not None for p in model.parameters()): raise ValueError('body gradient ownership changed')
            if reference.state_fingerprint(model) != before: raise ValueError('frozen body mutated; final report cannot PASS')
            if base.digest(root_path(evidence['checkpoint'])) != evidence['checkpoint_sha256']:
                raise ValueError('original frozen body CP bytes changed during stage')


def records_and_rows(args, tok):
    report, rows = corpus_rows(args); records = base.encoded(args, report, tok)
    for split in ('train', 'val'):
        if len(records[split]) != len(rows[split]): raise ValueError('record/row alignment differs')
        for row, record in zip(rows[split], records[split]):
            try: router.validate_prefix(row, record, tok)
            except ValueError as exc: raise Hold('all-row standalone prefix validation failed; no dropping or gold input: ' + str(exc)) from exc
    return records, rows


def new_writer(args, mode, stem):
    from scripts.p106b_shards import ShardWriter
    directory = safe_output(args, raw_name(args, mode))
    if directory.exists(): raise FileExistsError('prior router raw preserved')
    return ShardWriter(directory, stem, limit=19_999_999)


def raw_rows(args, mode, manifest, stem):
    from scripts.p106b_shards import verify
    directory = safe_output(args, raw_name(args, mode))
    if (manifest.get('lineage', {}).get('complete') is not True
            or base.read(raw_name(args, mode) + '/' + stem + '_shards_manifest.json') != manifest):
        raise ValueError('complete original raw manifest differs from receipt')
    for part in manifest['shards']: safe_output(args, raw_name(args, mode) + '/' + part['path'])
    verify(directory, manifest)
    for part in manifest['shards']:
        with (directory / part['path']).open(encoding='utf-8') as stream:
            for line in stream: yield json.loads(line)


def prefix_features(model, record, evidence):
    p = router.prefix(record)
    f, fingerprint = router.features(model, p, body_sha256=evidence['core_sha256'], tokenizer_sha256=base.TOK_SHA)
    return p, f, fingerprint


def generate(torch, model, cfg, tok, prefix, action):
    from scripts import interactive_research_infer as ui
    sample, capture_type, forward_type = ui.generation_tools(ROOT)
    if len(prefix.token_ids) + 128 > cfg.max_seq_len: raise Hold('full prefix+128 exceeds context; no shortening or silent truncation')
    prompt = tok.decode(list(prefix.token_ids), skip_special_tokens=False)
    class ExactPrefixCapture(capture_type):
        def encode(self, text):
            if text != prompt: raise ValueError('unexpected prompt text')
            return SimpleNamespace(ids=list(prefix.token_ids))
    capture = ExactPrefixCapture(tok); started = time.perf_counter()
    with torch.no_grad(), router.action_scope(model, action, prefix) as receipt:
        _, metadata = sample(forward_type(model, 'fp32_math'), cfg, capture, prompt, max_new=128,
            temperature=0., top_k=1, device='cuda', use_cache=False, logits_last_only=True,
            return_metadata=True, mtp_tokens=1, stop_token_sequences=[[4]])
        answer, generation = ui.answer_from_tokens(tok, list(prefix.token_ids), capture.decoded_ids, metadata, 128)
    torch.cuda.synchronize()
    return dict(input_text=prompt, prefix_ids=list(prefix.token_ids), actual_answer=answer, generation=generation,
        route=receipt, seconds=time.perf_counter() - started, attempts=1, semantic_score=None)


def cost(args):
    prepared(args); timing = []; encoded_seconds = 0.
    with frozen_body(args) as (torch, model, cfg, tok, evidence):
        tick = time.perf_counter(); records, _ = records_and_rows(args, tok); encoded_seconds = time.perf_counter() - tick
        selected_times = []; feature_times = []; rows = records['train'][:64]; features = []; labels = []; visits = targets = 0
        from torch.nn.attention import sdpa_kernel, SDPBackend
        with torch.no_grad(), sdpa_kernel(SDPBackend.MATH), torch.autocast('cuda', enabled=False):
            for start in range(0, 64, 8):
                tick = time.perf_counter(); batch = rows[start:start + 8]
                _, relative, routes = router.trial_labels(model, batch, split='train', pad_id=tok.token_to_id('<pad>') or 0)
                for record, target in zip(batch, relative):
                    feature_tick = time.perf_counter()
                    _, f, _ = prefix_features(model, record, evidence); features.append(f.cpu()); labels.append(target)
                    torch.cuda.synchronize(); feature_times.append(time.perf_counter() - feature_tick)
                torch.cuda.synchronize(); timing.append(time.perf_counter() - tick)
                visits += sum(r['visits'] for r in routes) * len(batch); targets += sum(r.targets for r in batch) * 3
            for action in (1, 2, 3):
                tick = time.perf_counter(); router.per_row_ce(model, rows[:1], action=action, pad_id=tok.token_to_id('<pad>') or 0)
                torch.cuda.synchronize(); selected_times.append(time.perf_counter() - tick)
            eligible = sorted(((-len(router.prefix(record).token_ids), i) for i, record in enumerate(records['train'])
                if len(router.prefix(record).token_ids) + 128 <= cfg.max_seq_len))
            if len(eligible) < 2: raise Hold('two declared longest TRAIN timing prefixes unavailable')
            generation_indices = [i for _, i in eligible[:2]]
            generation = [generate(torch, model, cfg, tok, router.prefix(records['train'][i]), 2) for i in generation_indices]
        x = torch.stack(features); y = torch.tensor(labels); mean = x.mean(0); scale = x.std(0, unbiased=False).clamp_min(1e-6)
        head = router.make_head(x.shape[1]); optimizer = torch.optim.Adam(head.parameters(), lr=.001)
        tick = time.perf_counter(); mse = router.head_update(head, optimizer, x, y, mean, scale); head_seconds = time.perf_counter() - tick
        tick = time.perf_counter()
        with torch.no_grad(): head(((x[:1] - mean) / scale)).tolist()
        head_predict_seconds = time.perf_counter() - tick
        return dict(status='RESOURCE_ONLY_COST8' if args.resource_only_r1 else 'ROUTER_COST8_COMPLETE', body=evidence,
            label_quality='NOT_MEASURED_RESOURCE_ONLY' if args.resource_only_r1 else 'SCIENTIFIC_BODY_COST_ONLY_NOT_QUALITY',
            cost_rows=64, trial_batch_seconds=timing, selected_row_seconds=selected_times, actual_route_row_visits=visits,
            actual_trial_assistant_targets=targets, encoded_seconds=encoded_seconds, head64_seconds=head_seconds, head64_mse=mse,
            generation_timing=generation, generation_train_indices=generation_indices, feature_row_seconds=feature_times,
            head_predict_seconds=head_predict_seconds, label_artifact_writes=0, body_optimizer_steps=0,
            peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20, gpu_total_mib=torch.cuda.get_device_properties(0).total_memory / 2**20)


def forecast(args):
    if args.resource_only_r1: raise Hold('R1 resource timing cannot authorize scientific labels/head/test')
    c = closed(args, 'cost'); p = prepared(args); count = p['split_manifest']['counts']; ndev = count['dev']['rows']; ntest = count['test']['rows']
    if c.get('status') != 'ROUTER_COST8_COMPLETE' or len(c['trial_batch_seconds']) != 8 or len(c['selected_row_seconds']) != 3:
        raise Hold('actual scientific body cost8 required')
    if len(c.get('feature_row_seconds', [])) != 64: raise ValueError('all64 measured prefix feature costs required')
    numeric = c['trial_batch_seconds'] + c['selected_row_seconds'] + c['feature_row_seconds'] + [c['head64_seconds'], c['encoded_seconds'], c['head_predict_seconds']]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in numeric): raise ValueError('finite actual timing required')
    if c['gpu_total_mib'] - c['peak_reserved_mib'] < 1024: raise Hold('observed1GiB reserve absent; not an OOM safety guarantee')
    gen = c['generation_timing']
    if len(gen) != 2 or any(not 1 <= v['generation']['generated_tokens'] <= 128 or v['seconds'] <= 0 for v in gen): raise ValueError('actual generation token cost required')
    worst_token = max(v['seconds'] / v['generation']['generated_tokens'] for v in gen)
    selected_row = max(c['selected_row_seconds']) + max(c['feature_row_seconds']) + c['head_predict_seconds']
    estimates = dict(labels=max(c['trial_batch_seconds']) * math.ceil(p['train_rows'] / 8) * 1.5 + c['encoded_seconds'] * 2,
        fit=c['head64_seconds'] * (p['train_rows'] / 64) * 5 * 1.5 + selected_row * ndev * 3 * 1.5 + c['encoded_seconds'] * 2,
        evaluate=(selected_row * ntest * 4 + worst_token * 128 * ntest * 4) * 1.5 + c['encoded_seconds'] * 2,
        readback=300.)
    for mode in tuple(estimates):
        if root_path(report_name(args, mode)).exists(): closed(args, mode); estimates[mode] = 0.
    actual = spent(args, signature(args)); _, remaining = authority(args, signature(args)); reserve = sum(estimates.values()) + 600
    return dict(status='ROUTER_BUDGET_READY' if reserve <= remaining and actual + reserve <= MAX_FAMILY else 'HOLD_BUDGET',
        fits=reserve <= remaining and actual + reserve <= MAX_FAMILY, body=c['body'], actual_spent_seconds=actual,
        forecasts_seconds=estimates, total_pending_seconds=reserve, remaining_authority_seconds=remaining,
        scope='measured conservative forecast, not completion or quality guarantee')


def require_budget(args):
    result = forecast(args)
    if not result['fits']: raise Hold('all pending labels/fit/DEV/TEST/raw verification do not fit; no shrink fallback')
    return result


def labels(args):
    budget = require_budget(args); prepared(args); writer = None; complete = False
    try:
        with frozen_body(args) as (torch, model, cfg, tok, evidence):
            if evidence != budget['body']: raise ValueError('cost body changed')
            records, rows = records_and_rows(args, tok); writer = new_writer(args, 'labels', 'train_labels'); targets = visits = 0
            from torch.nn.attention import sdpa_kernel, SDPBackend
            with torch.no_grad(), sdpa_kernel(SDPBackend.MATH), torch.autocast('cuda', enabled=False):
                for start in range(0, len(records['train']), 8):
                    batch = records['train'][start:start + 8]; tick = time.perf_counter()
                    raw_ce, relative, routes = router.trial_labels(model, batch, split='train', pad_id=tok.token_to_id('<pad>') or 0)
                    for offset, (record, losses, target) in enumerate(zip(batch, raw_ce, relative)):
                        index = start + offset; prefix, feature, fingerprint = prefix_features(model, record, evidence)
                        writer.append(dict(index=index, split='train', row_sha256=router.row_sha(rows['train'][index]),
                            prefix_ids=list(prefix.token_ids), prefix_sha256=prefix.sha256, feature=feature.cpu().tolist(),
                            feature_fingerprint=fingerprint, raw_ce=losses, relative_ce=target, assistant_targets=record.targets,
                            actual_x_tokens=record.x_tokens, first_target_owner=record.segments[len(prefix.token_ids) - 1], routes=routes))
                    targets += sum(r.targets for r in batch) * 3; visits += sum(r['visits'] for r in routes) * len(batch)
                    if start % 1024 == 0: print('[ROUTER_LABEL_PROGRESS] ' + str(start + len(batch)) + '/' + str(len(records['train'])), flush=True)
            manifest = writer.close(lineage=dict(schema=router.SCHEMA, split='TRAIN_ONLY', complete=True, body=evidence)); writer = None; complete = True
            return dict(status='TRAIN_RELATIVE_CE_LABELS_COMPLETE', body=evidence, rows=len(records['train']), raw_manifest=manifest,
                actual_trial_assistant_targets=targets, actual_route_row_visits=visits, feature_spec=router.FEATURE_SPEC, DEV_trial_labels=0, TEST_trial_labels=0)
    finally:
        if writer is not None and writer._total_rows: writer.close(lineage=dict(complete=complete, partial=True, schema=router.SCHEMA))


def verify_labels(args):
    value = closed(args, 'labels'); prepared_value = prepared(args); result = []; targets = visits = 0
    catalog = [router.readonly_plan(value['body']['geometry'], value['body']['owners'], i, ROOT) for i in range(4)]
    for i, row in enumerate(raw_rows(args, 'labels', value['raw_manifest'], 'train_labels')):
        if (row.get('index') != i or row.get('split') != 'train' or row['relative_ce'] != router.relative_ce(row['raw_ce'])
                or row['prefix_sha256'] != sha(row['prefix_ids']) or len(row['feature']) != value['body']['feature_width']
                or any(type(x) not in (int, float) or not math.isfinite(x) for x in row['feature'])
                or row['feature_fingerprint'] != sha(dict(spec=router.FEATURE_SPEC, prefix=row['prefix_ids'],
                    body=value['body']['core_sha256'], tokenizer=base.TOK_SHA, feature=row['feature']))
                or type(row.get('assistant_targets')) is not int or row['assistant_targets'] < 1
                or row.get('first_target_owner', 0) < 1 or len(row.get('routes', [])) != 3
                or [r['actual_repeats'] for r in row['routes']] != [1, 2, 3]):
            raise ValueError('independent TRAIN label/feature/prefix/raw denominator differs')
        for receipt in row['routes']:
            if type(receipt.get('index')) is not int or not 0 <= receipt['index'] < 4 or receipt != catalog[receipt['index']]:
                raise ValueError('TRAIN atomic route receipt differs from original source')
        targets += row['assistant_targets'] * 3; visits += sum(r['visits'] for r in row['routes']); result.append(row)
    if (len(result) != prepared_value['train_rows'] or len(result) != value['rows']
            or sha([r['row_sha256'] for r in result]) != prepared_value['train_rows_sha256']
            or targets != value['actual_trial_assistant_targets'] or visits != value['actual_route_row_visits']
            or targets != 3 * prepared_value['corpus_counts']['train']['assistant_targets']
            or sum(r['actual_x_tokens'] for r in result) != prepared_value['actual_unique_train_x_tokens']):
        raise ValueError('full TRAIN ordered identity/label mass differs')
    return value, result


def selected_evaluation(torch, model, cfg, tok, evidence, records, row_entries, *, policy, head=None, mean=None, scale=None, constant=None, generate_answers=False, sink=None):
    if policy not in router.POLICIES: raise ValueError('registered control required')
    from torch.nn.attention import sdpa_kernel, SDPBackend
    quota = router.Quota(len(row_entries)); events = []
    if head is not None: head.eval()
    with torch.no_grad(), sdpa_kernel(SDPBackend.MATH), torch.autocast('cuda', enabled=False):
        for i, entry in enumerate(row_entries):
            feature_tick = time.perf_counter()
            record = records[entry['index']]; prefix, feature, fingerprint = prefix_features(model, record, evidence)
            if policy in ('learned', 'untrained'):
                scores = head(((feature.cpu() - mean) / scale).unsqueeze(0)).squeeze(0).tolist()
            elif policy == 'constant_train_mean': scores = list(constant)
            else: scores = None
            action, decision = quota.choose(scores, random_choice=policy == 'random_quota')
            feature_head_seconds = time.perf_counter() - feature_tick
            tick = time.perf_counter()
            sums, counts, receipt = router.per_row_ce(model, [record], action=action, pad_id=tok.token_to_id('<pad>') or 0)
            torch.cuda.synchronize()
            event = dict(case=i, corpus_index=entry['index'], row_sha256=entry['row_sha256'], group_sha256=entry['group_sha256'],
                language=entry['language'], policy=policy, predicted_relative_ce=scores, decision=decision, route=receipt,
                feature_fingerprint=fingerprint, prefix_ids=list(prefix.token_ids), assistant_nll=sums[0],
                assistant_targets=counts[0], actual_x_tokens=record.x_tokens, forward_seconds=time.perf_counter() - tick,
                feature_head_seconds=feature_head_seconds,
                trial_candidates_executed=1, gold_used_for_selection=False)
            if generate_answers: event['first_answer'] = generate(torch, model, cfg, tok, prefix, action)
            if sink is not None: sink(event)
            if generate_answers and i in (0, 1):
                print('[P078_ROUTER_FIRST_ANSWER_SAMPLE] ' + json.dumps(dict(policy=policy, case=i, action=action,
                    first_answer=event['first_answer']), ensure_ascii=False), flush=True)
            events.append(event)
    return summarize(events), events


def summarize(events):
    if not events or len({e['policy'] for e in events}) != 1: raise ValueError('one nonempty policy lane required')
    for event in events:
        if (type(event.get('assistant_targets')) is not int or event['assistant_targets'] <= 0
                or type(event.get('assistant_nll')) not in (int, float) or not math.isfinite(event['assistant_nll']) or event['assistant_nll'] < 0
                or type(event.get('actual_x_tokens')) is not int or not 1 <= event['actual_x_tokens'] <= 1024
                or any(type(event.get(k)) not in (int, float) or not math.isfinite(event[k]) or event[k] < 0 for k in ('feature_head_seconds', 'forward_seconds'))):
            raise ValueError('positive individual rows/targets and finite actual CE/time required')
        if 'first_answer' in event: verify_answer(event)
    targets = sum(e['assistant_targets'] for e in events); nll = sum(e['assistant_nll'] for e in events)
    if targets <= 0 or not math.isfinite(nll): raise ValueError('finite actual selected-route target denominator required')
    if sum(e['decision']['action'] for e in events) != 2 * len(events): raise ValueError('complete online quota must equal R2 visit count')
    for i, event in enumerate(events):
        if (event['case'] != i or event['decision']['index'] != i or event['decision']['total'] != len(events)
                or event['trial_candidates_executed'] != 1 or event['gold_used_for_selection'] is not False
                or event['route']['actual_repeats'] != event['decision']['action']): raise ValueError('chosen route/case/one-candidate identity differs')
    return dict(rows=len(events), assistant_targets=targets, assistant_nll=nll, ce=nll / targets,
        repeats=sum(e['decision']['action'] for e in events), actual_layer_row_visits=sum(e['route']['visits'] for e in events),
        actual_x_tokens=sum(e['actual_x_tokens'] for e in events), ce_padded_slots=1024 * len(events),
        ce_padded_layer_token_visits=1024 * sum(e['route']['visits'] for e in events),
        actual_unpadded_layer_token_visits=sum(e['route']['visits'] * e['actual_x_tokens'] for e in events),
        generation_body_input_slots=sum(generation_input_slots(e) for e in events),
        generation_layer_token_visits=sum(generation_input_slots(e) * e['route']['visits'] for e in events),
        feature_head_seconds=sum(e['feature_head_seconds'] for e in events), forward_seconds=sum(e['forward_seconds'] for e in events),
        actions=dict(CounterLike(e['decision']['action'] for e in events)),
        languages={language: sum(e['language'] == language for e in events) for language in ('ko', 'en')},
        generated_answers=sum('first_answer' in e for e in events),
        finishes={reason: sum(e.get('first_answer', {}).get('generation', {}).get('finish_reason') == reason for e in events)
            for reason in ('EOS', 'STOP_SEQUENCE', 'MAX_NEW')})


def generation_input_slots(event):
    if 'first_answer' not in event: return 0
    n = event['first_answer']['generation']['generated_tokens']; prefix = len(event['prefix_ids'])
    return n * prefix + n * (n - 1) // 2  # cacheOFF; each token rebuilds its actual whole prefix


def verify_answer(event):
    answer = event['first_answer']; generation = answer['generation']; ids = generation['generated_ids']; prefix = event['prefix_ids']
    reason = generation['finish_reason']
    terminal = [4] if reason == 'STOP_SEQUENCE' else [2] if reason == 'EOS' else []
    if (not isinstance(ids, list) or any(type(v) is not int or not 0 <= v < 32768 for v in ids)
            or not 1 <= len(ids) <= 128 or reason not in ('EOS', 'STOP_SEQUENCE', 'MAX_NEW')
            or (reason == 'MAX_NEW' and len(ids) != 128)
            or not isinstance(prefix, list) or not 1 <= len(prefix) <= 896
            or any(type(v) is not int or not 0 <= v < 32768 for v in prefix)
            or answer['prefix_ids'] != prefix or answer['route'] != event['route'] or answer['attempts'] != 1
            or generation['prompt_tokens'] != len(prefix) or generation['generated_tokens'] != len(ids)
            or generation['max_new'] != 128 or generation['terminal_ids'] != terminal
            or (terminal and ids[-1:] != terminal) or any(v in (2, 4) for v in (ids[:-1] if terminal else ids))
            or generation['content_tokens'] != len(ids) - len(terminal) or generation['terminal_only_removed'] is not True
            or generation['matched_stop_sequence'] != ([4] if reason == 'STOP_SEQUENCE' else None)
            or not isinstance(answer['actual_answer'], str) or not isinstance(answer['input_text'], str)
            or type(answer['seconds']) not in (int, float) or not math.isfinite(answer['seconds']) or answer['seconds'] < 0):
        raise ValueError('actual first answer/token/finish boundary differs')


def CounterLike(values):
    result = {}
    for value in values: result[str(value)] = result.get(str(value), 0) + 1
    return result


def fit(args):
    require_budget(args); prepared_value = prepared(args); label_report, rows = verify_labels(args)
    writer = update_writer = None
    try:
        with frozen_body(args) as (torch, model, cfg, tok, evidence):
            if evidence != label_report['body']: raise ValueError('label frozen body changed')
            from scripts.p106b_shards import ShardWriter
            writer = new_writer(args, 'fit', 'dev_selected')
            update_writer = ShardWriter(safe_output(args, raw_name(args, 'fit')), 'head_updates', limit=19_999_999)
            records, _ = records_and_rows(args, tok); x = torch.tensor([r['feature'] for r in rows]); y = torch.tensor([r['relative_ce'] for r in rows])
            mean = x.mean(0); scale = x.std(0, unbiased=False).clamp_min(1e-6); constant = y.mean(0).tolist()
            head = router.make_head(x.shape[1]); opt = torch.optim.Adam(head.parameters(), lr=.001)
            best = None; history = []; updates = []; initial = sha({k: v.tolist() for k, v in head.state_dict().items()})
            for epoch in range(1, 6):
                head.train(); order = list(range(len(rows))); random.Random(1337 + epoch).shuffle(order)
                for start in range(0, len(order), 128):
                    tick = time.perf_counter(); indices = order[start:start + 128]; mse = router.head_update(head, opt, x[indices], y[indices], mean, scale)
                    event = dict(epoch=epoch, step=len(updates) + 1, rows=len(indices), mse=mse, indices_sha256=sha(indices),
                        gradient_max=max(float(p.grad.abs().max()) for p in head.parameters()), seconds=time.perf_counter() - tick,
                        micro_bs=8, accum=16, model_id=id(head), optimizer_id=id(opt), body_optimizer_steps=0)
                    updates.append(event); update_writer.append(event)
                if epoch in router.HEAD['dev_epochs']:
                    summary, _ = selected_evaluation(torch, model, cfg, tok, evidence, records['val'],
                        prepared_value['split_manifest']['splits']['dev'], policy='learned', head=head, mean=mean, scale=scale,
                        sink=lambda e: writer.append(dict(e, epoch=epoch)))
                    history.append(dict(epoch=epoch, summary=summary))
                    if best is None or summary['ce'] < best['ce']:
                        best = dict(epoch=epoch, ce=summary['ce'], state={k: v.detach().cpu().clone() for k, v in head.state_dict().items()})
            final = sha({k: v.tolist() for k, v in head.state_dict().items()})
            if final == initial: raise ValueError('head did not learn; cannot label policy as learned')
            checkpoint = raw_name(args, 'fit') + '/router_head.pt'
            manifest = writer.close(lineage=dict(schema=router.SCHEMA, split='DEV_ONLY', complete=True)); writer = None
            update_manifest = update_writer.close(lineage=dict(schema=router.SCHEMA, split='TRAIN_ONLY', complete=True)); update_writer = None
            payload = dict(schema=router.SCHEMA, head=best['state'], feature_spec=router.FEATURE_SPEC, head_spec=router.HEAD,
                mean=mean, scale=scale, constant=constant, width=x.shape[1], selected_epoch=best['epoch'], body=evidence,
                input=signature(args), train_label_concat_sha256=label_report['raw_manifest']['concat_sha256'])
            with safe_output(args, checkpoint).open('xb') as stream: torch.save(payload, stream)
            return dict(status='ROUTER_HEAD_FIT_DEV_SELECTED_TEST_UNUSED', body=evidence, train_rows=len(rows), head_updates=updates,
                head_spec=router.HEAD, dev_history=history, selected_epoch=best['epoch'], dev_raw_manifest=manifest,
                update_raw_manifest=update_manifest, initial_head_sha256=initial, final_head_sha256=final,
                head_checkpoint=checkpoint, head_checkpoint_sha256=base.digest(root_path(checkpoint)),
                body_optimizer_steps=0, TEST_evaluations=0, DEV_trial_labels=0, TEST_trial_labels=0)
    finally:
        for unfinished in (writer, update_writer):
            if unfinished is not None and unfinished._total_rows: unfinished.close(lineage=dict(complete=False, partial=True, schema=router.SCHEMA))


def evaluate(args):
    require_budget(args); prep = prepared(args); fitted = closed(args, 'fit'); label_report, _ = verify_labels(args)
    with frozen_body(args) as (torch, model, cfg, tok, evidence):
        if evidence != fitted['body'] or evidence != label_report['body']: raise ValueError('selected body changed')
        payload = read_head(torch, root_path(fitted['head_checkpoint']), fitted['head_checkpoint_sha256'])
        if (payload['input'] != signature(args) or payload['body'] != evidence or payload['head_spec'] != router.HEAD
                or payload['feature_spec'] != router.FEATURE_SPEC or payload['selected_epoch'] != fitted['selected_epoch']
                or payload['train_label_concat_sha256'] != label_report['raw_manifest']['concat_sha256']
                or payload.get('schema') != router.SCHEMA or payload['width'] != evidence['feature_width']
                or tuple(payload['mean'].shape) != (payload['width'],) or tuple(payload['scale'].shape) != (payload['width'],)
                or not bool(torch.isfinite(payload['mean']).all()) or not bool(torch.isfinite(payload['scale']).all())
                or not bool(payload['scale'].gt(0).all()) or len(payload['constant']) != 3
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in payload['constant'])):
            raise ValueError('selected TRAIN/DEV head binding/normalization differs')
        head = router.make_head(payload['width']); head.load_state_dict(payload['head'], strict=True)
        untrained = router.make_head(payload['width']); records, _ = records_and_rows(args, tok)
        entries = prep['split_manifest']['splits']['test']
        if any(len(router.prefix(records['val'][e['index']]).token_ids) + 128 > cfg.max_seq_len for e in entries):
            raise Hold('all frozen TEST prefixes must fit+128 before any generation; no sample reduction')
        writer = new_writer(args, 'evaluate', 'test_selected'); summaries = {}; complete = False
        try:
            for policy in router.POLICIES:
                summary, events = selected_evaluation(torch, model, cfg, tok, evidence, records['val'], entries,
                    policy=policy, head=untrained if policy == 'untrained' else head,
                    mean=payload['mean'], scale=payload['scale'], constant=payload['constant'], generate_answers=True, sink=writer.append)
                summaries[policy] = summary
                print('[ROUTER_TEST_POLICY_COMPLETE] ' + json.dumps(dict(policy=policy, summary=summary)), flush=True)
            manifest = writer.close(lineage=dict(schema=router.SCHEMA, split='TEST_ONCE_AFTER_DEV_SELECTION', complete=True)); writer = None; complete = True
            return dict(status='ROUTER_TEST_FIRST_ANSWERS_COMPLETE_NOT_ADOPTED', body=evidence, summaries=summaries, raw_manifest=manifest,
                head_checkpoint_sha256=fitted['head_checkpoint_sha256'], body_optimizer_steps=0, trial_labels_TEST=0,
                fully_pipeline_blind=False, quality_claim='NO_AUTOMATIC_ADOPTION; qualitative actual first answers preserved; CE is not truth')
        finally:
            if writer is not None and writer._total_rows: writer.close(lineage=dict(complete=complete, partial=True))


def read_head(torch_module, path, expected):
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno()); digest = hashlib.sha256()
        if not 0 < before.st_size < 20_000_000: raise ValueError('small nonempty private router head required')
        for part in iter(lambda: stream.read(1 << 20), b''): digest.update(part)
        if digest.hexdigest().upper() != expected: raise ValueError('selected head bytes changed')
        stream.seek(0); payload = torch_module.load(stream, map_location='cpu', weights_only=True)
        after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError('selected head changed during same-handle read')
    return payload


def readback(args):
    prep = prepared(args); label_report, labels_raw = verify_labels(args); fitted = closed(args, 'fit'); evaluation = closed(args, 'evaluate')
    updates = list(raw_rows(args, 'fit', fitted['update_raw_manifest'], 'head_updates'))
    if updates != fitted['head_updates'] or len(updates) != 5 * math.ceil(len(labels_raw) / 128): raise ValueError('independent actual head update raw differs')
    if len({v['model_id'] for v in updates}) != 1 or len({v['optimizer_id'] for v in updates}) != 1: raise ValueError('head/optimizer reset within training')
    step = 0
    for epoch in range(1, 6):
        order = list(range(len(labels_raw))); random.Random(1337 + epoch).shuffle(order)
        for start in range(0, len(order), 128):
            event = updates[step]; step += 1; indices = order[start:start + 128]
            if (event['step'] != step or event['epoch'] != epoch or event['rows'] != len(indices) or event['indices_sha256'] != sha(indices)
                    or event['micro_bs'] != 8 or event['accum'] != 16 or event['body_optimizer_steps'] != 0
                    or any(type(event[k]) not in (int, float) or not math.isfinite(event[k]) or event[k] < 0 for k in ('mse', 'gradient_max', 'seconds'))):
                raise ValueError('exact5epoch/micro8a16/head TRAIN order/actual finite step differs')
    if fitted['initial_head_sha256'] == fitted['final_head_sha256']: raise ValueError('head weights unchanged')
    if [v['epoch'] for v in fitted['dev_history']] != [1, 3, 5]: raise ValueError('predeclared DEV candidates differ')
    dev = list(raw_rows(args, 'fit', fitted['dev_raw_manifest'], 'dev_selected'))
    for history in fitted['dev_history']:
        actual = [e for e in dev if e['epoch'] == history['epoch']]
        if summarize(actual) != history['summary']: raise ValueError('independent DEV raw summary differs')
        verify_lane(actual, prep['split_manifest']['splits']['dev'], evaluation['body'])
    if fitted['selected_epoch'] != min(fitted['dev_history'], key=lambda v: (v['summary']['ce'], v['epoch']))['epoch']:
        raise ValueError('head selected by something other than fixed DEV CE')
    events = list(raw_rows(args, 'evaluate', evaluation['raw_manifest'], 'test_selected')); summaries = {}
    if len(events) != 4 * prep['split_manifest']['counts']['test']['rows']: raise ValueError('all four full TEST lanes required')
    for policy in router.POLICIES:
        lane = [e for e in events if e['policy'] == policy]; summaries[policy] = summarize(lane)
        verify_lane(lane, prep['split_manifest']['splits']['test'], evaluation['body'])
        for event in lane: verify_answer(event)
        if summaries[policy] != evaluation['summaries'][policy]: raise ValueError('independent TEST raw summary differs')
    if (label_report['body'] != fitted['body'] or fitted['body'] != evaluation['body']
            or base.digest(root_path(fitted['head_checkpoint'])) != fitted['head_checkpoint_sha256']
            or base.digest(root_path(evaluation['body']['checkpoint'])) != evaluation['body']['checkpoint_sha256']): raise ValueError('selected body/head original bytes changed')
    return dict(status='ROUTER_RAW_RECOUNTED_NOT_ADOPTED', summaries=summaries, body=evaluation['body'], model_loads=0,
        checkpoint_tensor_loads=0, body_training_here=0, fully_pipeline_blind=False,
        answer_text_redecode='NOT_DONE_NO_TOKENIZER_LOAD; ID/terminal/raw SHA verified, original actual text retained')


def verify_lane(lane, entries, evidence):
    if len(lane) != len(entries): raise ValueError('fixed complete split required')
    quota = router.Quota(len(lane))
    catalog = [router.readonly_plan(evidence['geometry'], evidence['owners'], i, ROOT) for i in range(4)]
    for event, entry in zip(lane, entries):
        _, decision = quota.choose(event['predicted_relative_ce'], random_choice=event['policy'] == 'random_quota')
        if (decision != event['decision'] or event['corpus_index'] != entry['index'] or event['row_sha256'] != entry['row_sha256']
                or event['group_sha256'] != entry['group_sha256'] or event['language'] != entry['language']
                or type(event['route'].get('index')) is not int or not 0 <= event['route']['index'] < 4
                or event['route'] != catalog[event['route']['index']] or event['route']['actual_repeats'] != decision['action']):
            raise ValueError('case/online decision/atomic route differs')


def worker(args):
    info = signature(args); tick = time.perf_counter(); began = datetime.now(timezone.utc); code = 9; error = None; auth = None; remaining = None
    if root_path(report_name(args, args.mode)).exists() or root_path(activity_name(args, args.mode)).exists(): raise FileExistsError('prior router stage preserved')
    try:
        auth, remaining = authority(args, info)
        if os.getpid() != os.getpgrp() or args.max_wall_sec > remaining or spent(args, info) + args.max_wall_sec > MAX_FAMILY:
            raise Hold('new PGID/full cap/current UTC/family40h admission required')
        with base.wall(args.max_wall_sec):
            if args.resource_only_r1 and args.mode not in ('prepare', 'cost'): raise Hold('resource-only R1 cannot label/train/select/test scientific head')
            method = dict(prepare=prepare, cost=cost, budget=forecast, labels=labels, fit=fit, evaluate=evaluate, readback=readback)[args.mode]
            result = method(args)
            if result.get('fits') is False: raise Hold('HOLD_BUDGET')
            authority(args, info)
            if signature(args) != info: raise ValueError('router/helper/product source changed during stage')
            result.update(input=info, mode=args.mode, authorization=auth, authorization_sha256=args.authorization_sha256)
            write(args, report_name(args, args.mode), result); code = 0
    except KeyboardInterrupt: code = 130; error = 'KeyboardInterrupt'
    except Hold as exc: code = 8; error = str(exc); print('[HOLD] ' + str(exc), flush=True)
    except Exception as exc: code = 9; error = type(exc).__name__; print('[ERROR] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
    finally:
        ended = datetime.now(timezone.utc)
        if code == 0 and ended > datetime.fromisoformat(auth['expires_at']):
            code = 8; error = 'authority expired before activity closure; no COMPLETE'
        write(args, activity_name(args, args.mode), dict(input=info, mode=args.mode, complete=code == 0, returncode=code, error=error,
            started_at=began.isoformat(), ended_at=ended.isoformat(), seconds=time.perf_counter() - tick,
            pid=os.getpid(), pgid=os.getpgrp(), max_wall_sec=args.max_wall_sec, admission_remaining=remaining,
            authorization=auth, authorization_sha256=args.authorization_sha256, authorization_canonical_sha256=sha(auth),
            invocation=list(sys.argv), cwd=str(ROOT),
            report_sha256=base.digest(root_path(report_name(args, args.mode))) if root_path(report_name(args, args.mode)).is_file() else None))
    return code


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', choices=MODES, required=True)
    p.add_argument('--corpus-sha256'); p.add_argument('--authorization'); p.add_argument('--authorization-sha256')
    p.add_argument('--resource-only-r1', action='store_true'); p.add_argument('--max-wall-sec', type=int, default=1800)
    p.add_argument('--worker', action='store_true'); choice = p.add_mutually_exclusive_group(required=True)
    choice.add_argument('--execute', action='store_true'); choice.add_argument('--check-only', action='store_true'); args = p.parse_args(argv)
    args.corpus = base.CLEAN_CORPUS; args.adam_lr = 5e-5; args.muon_lr = 2e-4
    try:
        if args.check_only:
            info = signature(args)
            print('[STATIC_ONLY] ' + json.dumps(dict(ready=READY, sources=len(info['source_sha256']), input_signature_sha256=sha(info),
                model_loads=0, checkpoint_tensor_loads=0, corpus_reads=0, tokenizer_loads=0, learned_head='IMPLEMENTED_UNVERIFIED_REAL_ASSETS')), flush=True)
            return 0
        if args.mode == 'toy':
            import unittest
            from scripts import test_p078_prefix_router as tests
            return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests)).wasSuccessful() else 9
        if not READY: raise Hold('root source review/real input/cost pending; router implementation gate closed')
        if not isinstance(args.corpus_sha256, str) or len(args.corpus_sha256) != 64: raise Hold('exact root-pinned V3 corpus report SHA required')
        if not 60 <= args.max_wall_sec <= MAX_FAMILY: raise ValueError('bounded explicit worker cap required')
        if args.worker: return worker(args)
        invocation = sys.argv[1:] if argv is None else argv
        command = [sys.executable, '-B', '-X', 'utf8', str(root_path('scripts/diag_p078_prefix_router.py')), *invocation, '--worker']
        proc = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, start_new_session=True)
        try: return proc.wait(timeout=args.max_wall_sec)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=30)
            except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL); proc.wait()
            return 130
    except Hold as exc: print('[HOLD] ' + str(exc), flush=True); return 8
    except Exception as exc: print('[ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True); return 9


if __name__ == '__main__': raise SystemExit(main())
