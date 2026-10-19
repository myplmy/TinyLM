#!/usr/bin/env python3
"""Write-once content-objective comparison on the unchanged question course.

Only content weights change. The old controller, corpus, checkpoints, product
defaults and native objective stay unchanged. A complete stage receipt is not
evidence of general intelligence. No interactive input or downloads are used.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
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
from scripts import diag_p106b_question_transfer as source
from scripts import p106b_content_objective as objective
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_stage_receipt import pipeline

TAG = 'p106b_content_recovery_v1_s1337'
SCHEMA = 'P106B_CONTENT_RECOVERY_V1'
SOURCE_ARM = 'varied_balanced'
ARMS = ('token', 'content')
MODES = ('source', 'prepare', 'preflight', 'cost', 'budget', 'train', 'evaluate', 'readback')
CACHE = ROOT / 'data_cache' / TAG
RAW = ROOT / 'runs/eval' / TAG
EVIDENCE = ROOT / 'test_result/evidence' / TAG
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
TRAIN_STOP = END - timedelta(hours=3)
UPDATES, ROWS, CONTEXT, MAX_NEW = 384, 12288, 1024, 64
ACTIVE_LIMIT, EVAL_RESERVE, RECORD_RESERVE = 21600, 1200, 600
OWN_CODE = ('scripts/diag_p106b_content_recovery.py', 'scripts/test_p106b_content_recovery.py',
            'scripts/p106b_content_objective.py', 'scripts/test_p106b_content_objective.py')
CODE = tuple(sorted(set((*source.CODE, *OWN_CODE))))
safe, digest, sha = source.safe, source.digest, source.sha
Pending = source.Pending


def info():
    pins = {name: digest(safe(ROOT / name)) if (ROOT / name).is_file() else 'NOT_CREATED' for name in CODE}
    return dict(schema=SCHEMA, tag=TAG, source_tag=source.TAG, source_arm=SOURCE_ARM,
        code_sha256=pins, code_complete=all(value != 'NOT_CREATED' for value in pins.values()),
        source_report=str((source.CORPUS / 'report.json').relative_to(ROOT)),
        parent=str(source.base.PARENT.relative_to(ROOT)), parent_sha256=source.base.PARENT_SHA,
        expected_parent_core=source.base.PARENT_CORE, tokenizer_sha256=source.natural.TOK_SHA,
        micro_bs=8, accum=16, seq=CONTEXT, grad_checkpoint=True, compile='default',
        adam_lr=5e-5, muon_lr=2e-4, all_group_weight_decay=0., grad_clip=1.,
        epochs=4, updates=UPDATES, seed=1337, scheduler='constant', native_targets_per_update=8192,
        max_new=MAX_NEW, mtp=False, teacher_calls=0, new_head_parameters=0,
        authority_end_utc=END.isoformat(), training_stop_utc=TRAIN_STOP.isoformat(),
        active_limit_seconds=ACTIVE_LIMIT, automatic_adoption=False,
        general_intelligence='NOT_ESTABLISHED', formal_train_ready=False)


def authority(training=False, now=None):
    current = datetime.now(timezone.utc) if now is None else now
    if current.tzinfo is None:
        raise ValueError('aware clock required')
    remaining = ((TRAIN_STOP if training else END) - current).total_seconds()
    if remaining <= 0:
        raise Pending('explicit user authority or reserved training deadline expired')
    return remaining


def write(path, value):
    path = safe(path)
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(payload) >= 20_000_000:
        raise ValueError('single JSON must stay below20MB; shard raw records instead')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(payload)


def required(path):
    path = safe(path)
    if not path.is_file():
        raise Pending('required exact owned artifact absent: ' + str(path.relative_to(ROOT)))
    return json.loads(path.read_text(encoding='utf-8'))


def checkpoint(arm):
    if arm not in ARMS:
        raise ValueError('declared content-objective arm required')
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_content_' + TAG + '_' + arm + '.pt')


def source_state():
    frozen, rows, course = source.read_prepared()
    if not info()['code_complete']:
        raise ValueError('all new source/test files must exist before preparation')
    proof = source.validate_training_inputs(frozen, SOURCE_ARM)
    return frozen, rows, course, proof


def signature(plan):
    return dict(policy=plan.policy, targets=plan.targets, content_targets=plan.content_targets,
        eot_targets=plan.eot_targets, content_rows=plan.content_rows,
        row_content_counts=list(plan.row_content_counts))


def weight_mass(plan, rows):
    cells = defaultdict(lambda: dict(rows=0, targets=0, content_targets=0, eot_targets=0,
                                   content_mass=0., eot_mass=0.))
    for index, record in enumerate(rows):
        lane, language = record.get('lane', 'unknown'), record.get('language', 'unknown')
        cell = cells[(lane, language)]
        cell['rows'] += 1
        for target, owner, weight in zip(record['y'], record['segments'], plan.weights[index]):
            if target == -100:
                if weight != 0:
                    raise ValueError('ignored source target acquired loss weight')
                continue
            if owner <= 0 or weight < 0 or not math.isfinite(weight):
                raise ValueError('positive target/finite weight contract differs')
            terminal = target == 4
            cell['targets'] += 1
            cell['eot_targets' if terminal else 'content_targets'] += 1
            cell['eot_mass' if terminal else 'content_mass'] += weight
    return [dict(lane=key[0], language=key[1], **value) for key, value in sorted(cells.items())]


def prepare():
    authority(training=True)
    for path in (CACHE, EVIDENCE, RAW):
        safe(path)
        if path.exists():
            raise FileExistsError('previous complete/partial namespace preserved: ' + str(path))
    frozen, _, _, consumer = source_state()
    summaries = []
    for epoch in range(4):
        stem = SOURCE_ARM + '_e' + str(epoch + 1)
        wires = source.read_rows(source.CORPUS, frozen['manifests'][stem], stem, ROWS)
        records = [source.unwire(value) for value in wires]
        for slot, group in enumerate(source.schedule(epoch)):
            indices = [i for micro in group for i in micro]
            chosen = [records[i] for i in indices]
            weight = {arm: objective.make_weights(chosen, eot_id=4, policy=arm) for arm in ARMS}
            denominator = frozen['exposure'][SOURCE_ARM][epoch]['update_target_denominators'][slot]
            if any(plan.targets != denominator for plan in weight.values()):
                raise ValueError('same whole-update target denominator differs')
            summaries.append(dict(update=epoch * 96 + slot + 1, epoch=epoch + 1,
                row_order_sha256=sha([wires[i]['id'] for i in indices]),
                x_tokens=sum(record.x_tokens for record in chosen),
                policies={arm: dict(signature(plan), mass=weight_mass(plan, [wires[i] for i in indices]))
                          for arm, plan in weight.items()}))
    if len(summaries) != UPDATES:
        raise ValueError('all384 source updates required before any model access')
    CACHE.mkdir(parents=True, exist_ok=False)
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    RAW.mkdir(parents=True, exist_ok=False)
    result = dict(info(), status='CONTENT_OBJECTIVE_CPU_VERIFIED', model_loaded=False,
        optimizer_updates=0, checkpoint_writes=0, source_report_sha256=digest(source.CORPUS / 'report.json'),
        source_manifest_sha256=sha(frozen['manifests']), consumer=consumer,
        source_exposure=frozen['exposure'][SOURCE_ARM], native_offsets_sha256=sha(frozen['native_train_offsets']),
        cases_sha256=frozen['cases_sha256'], updates_manifest=summaries,
        no_source_corpus_copy=True, ignored_source_targets_remain_ignored=True)
    write(CACHE / 'frozen_reference.json', result)
    public = {key: value for key, value in result.items() if key != 'updates_manifest'}
    public['frozen_reference_sha256'] = digest(CACHE / 'frozen_reference.json')
    public['updates_weight_signature_sha256'] = sha(summaries)
    write(EVIDENCE / 'cpu_contract.json', public)
    print('[CONTENT_CPU] same4passes/384updates verified; model/GPU not started', flush=True)
    return 0


def prepared():
    frozen, _, _, consumer = source_state()
    report = required(CACHE / 'frozen_reference.json')
    if (report.get('status') != 'CONTENT_OBJECTIVE_CPU_VERIFIED'
            or any(report.get(key) != value for key, value in info().items())
            or report.get('source_report_sha256') != digest(source.CORPUS / 'report.json')
            or report.get('source_manifest_sha256') != sha(frozen['manifests'])
            or report.get('cases_sha256') != frozen['cases_sha256'] or report.get('consumer') != consumer
            or report.get('native_offsets_sha256') != sha(frozen['native_train_offsets'])):
        raise ValueError('same source/code/exposure/current consumer required before model access')
    public = {key: value for key, value in report.items() if key != 'updates_manifest'}
    public['frozen_reference_sha256'] = digest(CACHE / 'frozen_reference.json')
    public['updates_weight_signature_sha256'] = sha(report['updates_manifest'])
    if required(EVIDENCE / 'cpu_contract.json') != public:
        raise ValueError('independent public/reference binding differs')
    return frozen, report


def spent_seconds():
    seconds = 0.
    if EVIDENCE.exists():
        for path in EVIDENCE.glob('activity_*.json'):
            value = required(path)
            if value.get('tag') != TAG or not math.isfinite(float(value.get('seconds', -1))) or value['seconds'] < 0:
                raise ValueError('invalid owned activity record')
            seconds += value['seconds']
    return seconds


def completed_activity(mode, arm=None):
    key = mode + ('_' + arm if arm else '')
    report = required(EVIDENCE / ('activity_' + key + '.json'))
    if (report.get('schema') != SCHEMA or report.get('tag') != TAG
            or report.get('key') != key or report.get('mode') != mode or report.get('arm') != arm
            or report.get('complete') is not True or type(report.get('returncode')) is not int
            or report.get('returncode') != 0 or report.get('code_sha256') != info()['code_sha256']
            or type(report.get('max_wall_sec')) is not int or not 60 <= report['max_wall_sec'] <= 7200
            or type(report.get('seconds')) not in (int, float)
            or not math.isfinite(report['seconds']) or report['seconds'] < 0):
        raise ValueError('complete successful same-code owned worker activity required')
    return report


def read_training(arm, *, cost):
    if arm not in ARMS or type(cost) is not bool:
        raise ValueError('declared training identity required')
    directory = EVIDENCE / (('cost_' if cost else 'train_') + arm)
    report = required(directory / 'report.json')
    expected = 8 if cost else UPDATES
    if (report.get('status') != ('COST8_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING')
            or any(report.get(key) != value for key, value in info().items())
            or report.get('arm') != arm or report.get('actual_updates') != expected
            or report.get('initial_core_sha256') != source.base.PARENT_CORE
            or report.get('frozen_reference_sha256') != digest(CACHE / 'frozen_reference.json')
            or report.get('checkpoint_written') != (not cost)):
        raise ValueError('complete same-code/source/parent training report required')
    manifest = report.get('event_manifest')
    if not isinstance(manifest, dict) or manifest.get('lineage') != dict(tag=TAG, arm=arm, cost=cost):
        raise ValueError('exact event manifest lineage required')
    verify(directory, manifest)
    events = [json.loads(line) for item in manifest['shards']
              for line in (directory / item['path']).read_text(encoding='utf-8').splitlines()]
    if (len(events) != expected or report['step_seconds'] != [event['step_seconds'] for event in events]
            or any(event['update'] != i + 1 or event['native_targets'] != 8192
                   or not all(math.isfinite(float(event[key])) for key in
                              ('assistant_ce', 'content_ce', 'eot_ce', 'native_ce', 'gradient_norm', 'step_seconds'))
                   or event['step_seconds'] <= 0 for i, event in enumerate(events))):
        raise ValueError('raw timing/finite losses/native denominator differs')
    reference = required(CACHE / 'frozen_reference.json')
    if (not isinstance(report.get('final_core_sha256'), str)
            or len(report['final_core_sha256']) != 64
            or any(char not in '0123456789ABCDEF' for char in report['final_core_sha256'])):
        raise ValueError('final body fingerprint required')
    for i, event in enumerate(events):
        expected_update = reference['updates_manifest'][i]
        expected_policy = expected_update['policies'][arm]
        if (event.get('epoch') != i // 96 + 1 or event.get('positive_rows') != 128
                or event.get('x_tokens') != expected_update['x_tokens']
                or event.get('assistant_targets') != expected_policy['targets']
                or event.get('content_targets') != expected_policy['content_targets']
                or event.get('eot_targets') != expected_policy['eot_targets']
                or not math.isfinite(float(event.get('weighted_assistant_objective', float('nan'))))):
            raise ValueError('actual exposure/content/EOT/weighted objective differs')
    if (report.get('grad_max') != max(event['gradient_norm'] for event in events)
            or report.get('clip_events') != sum(event['gradient_norm'] > 1. for event in events)
            or any(report['totals'].get(key) != sum(event[key] for event in events)
                   for key in ('positive_rows', 'x_tokens', 'assistant_targets',
                               'content_targets', 'eot_targets', 'native_targets'))):
        raise ValueError('raw gradient/clipping/exposure totals differ')
    source.original.validate_groups(report['actual_optimizer_groups'])
    if not cost:
        if (report.get('checkpoint') != str(checkpoint(arm).relative_to(ROOT))
                or digest(checkpoint(arm)) != report.get('checkpoint_sha256')):
            raise ValueError('exact new checkpoint lineage differs')
    return report


def completed_training(arm, *, cost):
    # train() self-validation happens before its worker finally record exists.
    # Only later consumers require the successful, completed activity barrier.
    completed_activity('cost' if cost else 'train', arm)
    return read_training(arm, cost=cost)


def budget():
    prepared()
    estimates = {}
    for arm in ARMS:
        report = completed_training(arm, cost=True)
        times = report['step_seconds']
        prediction = times[0] + max(times[1:]) * (UPDATES - 1) * 1.25 + 240.
        if (EVIDENCE / ('train_' + arm) / 'report.json').is_file():
            completed_training(arm, cost=False)
            prediction = 0.
        estimates[arm] = prediction
    whole = spent_seconds() + sum(estimates.values()) + EVAL_RESERVE + RECORD_RESERVE
    if whole > ACTIVE_LIMIT or sum(estimates.values()) > authority(training=True):
        raise Pending('measured costs plus evaluation/record reserves exceed stage or user budget')
    return dict(admission=True, estimated_training_seconds=estimates, total_reserved_seconds=whole,
        active_limit_seconds=ACTIVE_LIMIT, evaluation_reserve_seconds=EVAL_RESERVE,
        record_reserve_seconds=RECORD_RESERVE, prediction_not_actual_training=True)


def train(arm, *, cost):
    import torch
    from tinylm.train import mtp_sft as core
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    from scripts.p106b_native_windows import reader
    from scripts.p106b_gate_runtime import idle_before_gpu
    frozen, own = prepared()
    authority(training=True)
    target = safe(EVIDENCE / (('cost_' if cost else 'train_') + arm))
    if target.exists() or (not cost and checkpoint(arm).exists()):
        raise FileExistsError('previous complete/partial training is preserved')
    reservation = None if cost else budget()
    for name, value in (('train.bin', source.base.NATIVE_TRAIN_SHA), ('val.bin', source.base.NATIVE_VAL_SHA)):
        if digest(source.base.NATIVE / name) != value:
            raise ValueError('native source bytes changed')
    # Source consumer and both DEV/pass/owner checks finish before this gate.
    idle_before_gpu()
    target.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(target, 'updates', limit=19_999_999)
    began = time.perf_counter()
    _, model, cfg, tok, initial = source.base.load_parent()
    if initial != source.base.PARENT_CORE or not cfg.grad_checkpoint or cfg.mtp_aux:
        raise ValueError('same fresh actual parent/ckptON/MTPoff required')
    windows = reader(ROOT, frozen)
    if len(windows) != UPDATES * 8:
        raise ValueError('same3072 native TRAIN windows required')
    model = model.cuda()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.cuda.reset_peak_memory_stats()
    native_before = None if cost else source.base.native_probe(model)
    dev_before = None if cost else source.dev_probe(model, tok, frozen)
    os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(prefix='p106b_content_recovery_')
    forward = torch.compile(model, mode='default')
    adam, muon, groups = source.base.make_optimizers(model)
    source.original.validate_groups(groups)
    if not cost and groups != completed_training(arm, cost=True)['actual_optimizer_groups']:
        raise ValueError('actual optimizer groups changed after cost8')
    totals, times, history = Counter(), [], []
    updates = clips = 0
    gmax = 0.
    write(target / 'start.json', dict(info(), arm=arm, cost=cost, reservation=reservation))
    for epoch in range(4):
        records = source.records_for(frozen, SOURCE_ARM, epoch)
        for slot, group in enumerate(source.schedule(epoch)):
            authority(training=True)
            tick = time.perf_counter()
            indices = [index for micro in group for index in micro]
            selected = [records[index] for index in indices]
            plan = objective.make_weights(selected, eot_id=4, policy=arm)
            expected = own['updates_manifest'][epoch * 96 + slot]['policies'][arm]
            if signature(plan) != {key: expected[key] for key in signature(plan)}:
                raise ValueError('actual whole-update weights differ from CPU frozen reference')
            adam.zero_grad(set_to_none=True)
            muon.zero_grad(set_to_none=True)
            sums_ = Counter()
            observed = 0
            for offset in range(0, 128, 8):
                batch = selected[offset:offset + 8]
                x, y, owners = core.pad_records(batch, 0, 'cuda', fixed_width=1024, batch_size=8)
                weights = objective.make_tensor(plan, list(range(offset, offset + 8)),
                    width=1024, device='cuda', dtype=torch.float32)
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    values, counts = objective.components(model, forward(x, return_hidden=True),
                        y, owners, weights, eot_id=4)
                if counts['targets'] != sum(record.targets for record in batch):
                    raise ValueError('actual micro target count differs')
                loss = values['weighted']
                if not bool(torch.isfinite(loss)):
                    raise ValueError('nonfinite weighted assistant objective')
                loss.backward()
                observed += counts['targets']
                for key in ('weighted', 'raw', 'content', 'eot'):
                    sums_[key] += float(values[key].detach())
            if observed != plan.targets:
                raise ValueError('whole-update assistant target count differs')
            native = [core.Record(value[:-1].astype('int64').tolist(), value[1:].astype('int64').tolist(), [1] * 1024)
                      for value in windows[updates * 8:(updates + 1) * 8]]
            nx, ny, ns = core.pad_records(native, 0, 'cuda', fixed_width=1024, batch_size=8)
            with torch.autocast('cuda', dtype=torch.bfloat16):
                values, counts = core.components(model, forward(nx, return_hidden=True), ny, ns, horizons=())
                native_loss = values[1] / 8192
            if counts[1] != 8192 or not bool(torch.isfinite(native_loss)):
                raise ValueError('unchanged native mean contract differs')
            native_loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            if not bool(torch.isfinite(norm)):
                raise ValueError('nonfinite gradient')
            adam.step()
            muon.step()
            updates += 1
            torch.cuda.synchronize()
            times.append(time.perf_counter() - tick)
            gmax = max(gmax, float(norm))
            clips += int(norm > 1.)
            x_count = sum(record.x_tokens for record in selected)
            event = dict(update=updates, epoch=epoch + 1, assistant_ce=sums_['raw'] / plan.targets,
                content_ce=sums_['content'] / plan.content_targets if plan.content_targets else 0.,
                eot_ce=sums_['eot'] / plan.eot_targets if plan.eot_targets else 0.,
                weighted_assistant_objective=sums_['weighted'], native_ce=float(native_loss.detach()),
                assistant_targets=plan.targets, content_targets=plan.content_targets, eot_targets=plan.eot_targets,
                native_targets=8192, positive_rows=128, x_tokens=x_count,
                gradient_norm=float(norm), clipped=bool(norm > 1.), step_seconds=times[-1])
            writer.append(event)
            totals.update(positive_rows=128, x_tokens=x_count, assistant_targets=plan.targets,
                          content_targets=plan.content_targets, eot_targets=plan.eot_targets, native_targets=8192)
            if updates <= 8 or updates % 32 == 0:
                print('[CONTENT_UPDATE] ' + json.dumps(dict(arm=arm, **event)), flush=True)
            if cost and updates == 8:
                break
        if cost:
            break
        history.append(dict(epoch=epoch + 1, updates=updates,
            dev=source.dev_probe(model, tok, frozen), native=source.base.native_probe(model)))
    if updates != (8 if cost else UPDATES):
        raise ValueError('complete declared update count required')
    result = dict(info(), status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING',
        arm=arm, actual_updates=updates, initial_core_sha256=initial, final_core_sha256=state_fingerprint(model),
        frozen_reference_sha256=digest(CACHE / 'frozen_reference.json'), actual_optimizer_groups=groups,
        totals=dict(totals), history=history, native_before=native_before, dev_before=dev_before,
        step_seconds=times, grad_max=gmax, clip_events=clips, checkpoint_written=not cost,
        optimizer_saved=False, reservation=reservation, peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
        peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
        memory_scope='torch allocator, not whole-device peak')
    if not cost:
        with safe(checkpoint(arm)).open('xb') as stream:
            torch.save(dict(model=model.state_dict(), cfg=asdict(cfg), step=updates,
                tokenizer_sha256=source.natural.TOK_SHA, optimizer_saved=False,
                content_recovery=dict(tag=TAG, arm=arm, source_arm=SOURCE_ARM, epochs=4)), stream)
        result.update(checkpoint=str(checkpoint(arm).relative_to(ROOT)), checkpoint_sha256=digest(checkpoint(arm)))
    result['event_manifest'] = writer.close(lineage=dict(tag=TAG, arm=arm, cost=cost))
    result['whole_seconds'] = time.perf_counter() - began
    write(target / 'report.json', result)
    read_training(arm, cost=cost)
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return 0


def evaluate(arm):
    import torch
    from tinylm.infer.generate import _strip
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    from scripts.p106b_gate_runtime import idle_before_gpu
    frozen, _ = prepared()
    trained = completed_training(arm, cost=False)
    target = safe(EVIDENCE / ('evaluate_' + arm))
    raw = safe(RAW / ('evaluate_' + arm))
    if target.exists() or raw.exists():
        raise FileExistsError('old actual answers preserved')
    cases = source.read_rows(source.CORPUS, frozen['manifests']['cases'], 'cases', source.EXPECTED_ANSWERS)
    if sha(cases) != frozen['cases_sha256']:
        raise ValueError('same complete1694 evaluation cases required')
    idle_before_gpu()
    _, model, cfg, tok, _ = source.base.load_parent()
    payload = torch.load(safe(checkpoint(arm)), map_location='cpu', weights_only=True)
    if (payload.get('content_recovery') != dict(tag=TAG, arm=arm, source_arm=SOURCE_ARM, epochs=4)
            or payload.get('step') != UPDATES or payload.get('cfg') != asdict(cfg)
            or payload.get('tokenizer_sha256') != source.natural.TOK_SHA):
        raise ValueError('exact owned child content recipe required')
    model.load_state_dict(_strip(payload['model']), strict=True)
    del payload
    model.set_anneal(1.)
    model.eval()
    before = state_fingerprint(model)
    if before != trained['final_core_sha256']:
        raise ValueError('actual child body differs')
    model = model.cuda()
    model.freeze_quant()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.cuda.reset_peak_memory_stats()
    target.mkdir(parents=True, exist_ok=False)
    raw.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(raw, 'answers', limit=19_999_999)
    events = []
    lineage = dict(tag=TAG, arm=arm, checkpoint=str(checkpoint(arm).relative_to(ROOT)),
                   checkpoint_sha256=trained['checkpoint_sha256'], expected_core_sha256=before)
    display = set(frozen['display_ids'])
    began = time.perf_counter()
    with torch.no_grad():
        for index, case in enumerate(cases):
            authority()
            if source.case_encoding(case, tok) != case['encoding']:
                raise ValueError('actual tokenizer/prefix/reference encoding changed')
            answer, generation = source.emit64(model, cfg, tok, case['messages'])
            event = dict(id=case['id'], case_sha256=sha(case), answer=answer,
                generation=generation, metrics=source.classify_case(case, answer), lineage=lineage)
            writer.append(event)
            events.append(event)
            if case['id'] in display:
                print('[CONTENT_ACTUAL_ANSWER] ' + json.dumps(dict(arm=arm, id=case['id'],
                    family=case['family'], question=case['messages'], answer=answer,
                    finish=generation['finish_reason'], metrics=event['metrics']), ensure_ascii=False), flush=True)
            elif (index + 1) % 256 == 0:
                print('[CONTENT_EVAL_PROGRESS] ' + str(index + 1) + '/1694', flush=True)
    summary = source.recount(events, cases, tokenizer=tok)
    model.clear_quant()
    after = state_fingerprint(model)
    if after != before:
        raise ValueError('evaluation changed weights')
    native = source.base.native_probe(model)
    manifest = writer.close(lineage=lineage)
    result = dict(info(), status='ACTUAL_FIRST_ANSWERS_RECORDED', arm=arm, lineage=lineage,
        summary=summary, answer_manifest=manifest, answer_manifest_sha256=digest(raw / 'answers_shards_manifest.json'),
        cases_sha256=sha(cases), core_before=before, core_after=after, native32_fp32=native,
        peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
        whole_seconds=time.perf_counter() - began, model_training=False,
        weights_changed=False, checkpoints_written=0)
    write(target / 'report.json', result)
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return 0


def validate_evaluation(report, arm, cases, lineage):
    if (report.get('status') != 'ACTUAL_FIRST_ANSWERS_RECORDED'
            or any(report.get(key) != value for key, value in info().items())
            or report.get('arm') != arm or report.get('lineage') != lineage
            or report.get('cases_sha256') != sha(cases)
            or report.get('model_training') is not False or report.get('weights_changed') is not False
            or report.get('checkpoints_written') != 0
            or report.get('core_before') != lineage['expected_core_sha256']
            or report.get('core_after') != lineage['expected_core_sha256']
            or not isinstance(report.get('answer_manifest'), dict)
            or report['answer_manifest'].get('lineage') != lineage):
        raise ValueError('actual evaluation/code/case/body/manifest identity differs')
    native = report.get('native32_fp32', {})
    if (native.get('targets') != 32768 or native.get('windows') != 32
            or native.get('precision') != 'FP32_MATH' or native.get('val_sha256') != source.base.NATIVE_VAL_SHA
            or type(native.get('ce')) not in (int, float) or not math.isfinite(native['ce']) or native['ce'] <= 0):
        raise ValueError('fixed32 native FP32 receipt differs')


def readback():
    from tokenizers import Tokenizer
    frozen, _ = prepared()
    cases = source.read_rows(source.CORPUS, frozen['manifests']['cases'], 'cases', source.EXPECTED_ANSWERS)
    tok = Tokenizer.from_file(str(source.natural.TOKENIZER))
    models, raw_answers = {}, {}
    for arm in ARMS:
        trained = completed_training(arm, cost=False)
        completed_activity('evaluate', arm)
        report = required(EVIDENCE / ('evaluate_' + arm) / 'report.json')
        directory = RAW / ('evaluate_' + arm)
        manifest = report['answer_manifest']
        expected_lineage = dict(tag=TAG, arm=arm, checkpoint=str(checkpoint(arm).relative_to(ROOT)),
            checkpoint_sha256=trained['checkpoint_sha256'], expected_core_sha256=trained['final_core_sha256'])
        validate_evaluation(report, arm, cases, expected_lineage)
        stored_manifest = required(directory / 'answers_shards_manifest.json')
        if (stored_manifest != manifest
                or digest(directory / 'answers_shards_manifest.json') != report.get('answer_manifest_sha256')):
            raise ValueError('stored answer manifest SHA/content differs')
        verify(directory, manifest)
        events = [json.loads(line) for shard in manifest['shards']
                  for line in (directory / shard['path']).read_text(encoding='utf-8').splitlines()]
        if (report.get('arm') != arm or report.get('lineage') != expected_lineage
                or report.get('cases_sha256') != sha(cases)
                or any(event.get('lineage') != expected_lineage for event in events)
                or report.get('core_before') != trained['final_core_sha256']
                or report.get('core_after') != trained['final_core_sha256']):
            raise ValueError('case/checkpoint/endpoint lineage differs')
        summary = source.recount(events, cases, tokenizer=tok)
        if summary != report['summary']:
            raise ValueError('independent actual-answer recount differs')
        models[arm] = dict(summary=summary, native32_fp32=report['native32_fp32'],
                          report_sha256=digest(EVIDENCE / ('evaluate_' + arm) / 'report.json'))
        raw_answers[arm] = events
    paired = defaultdict(Counter)
    for case, left, right in zip(cases, raw_answers['token'], raw_answers['content']):
        if case['lane'] == 'user_seen':
            continue
        key = (case['lane'], case.get('split', 'monitor'), case['family'], case['language'])
        a, b = bool(left['metrics']['correct']), bool(right['metrics']['correct'])
        paired[key].update(n=1, token_correct=int(a), content_correct=int(b),
                           token_only=int(a and not b), content_only=int(b and not a))
    write(EVIDENCE / 'readback.json', dict(info(), status='CONTENT_ACTUAL_READBACK_COMPLETE',
        errors=0, actual_fresh_answers=source.EXPECTED_ANSWERS * 2, models=models,
        paired=[dict(stratum=list(key), **dict(value)) for key, value in sorted(paired.items())],
        new_training=0, checkpoints_written=0, source_corpus_changed=False,
        interpretation='single learning seed; monitored cohort; no automatic scientific adoption'))
    print('[CONTENT_READBACK] actual3388 first answers verified; intelligence not established', flush=True)
    return 0


def worker(mode, arm, max_wall_sec):
    authority()
    if mode == 'source':
        source_state()
        print('[CONTENT_SOURCE] unchanged source/consumer verified; model/GPU not loaded', flush=True)
        return 0
    if mode == 'preflight':
        prepared()
        print('[CONTENT_PREFLIGHT] exact source/weights/DEV references; model/GPU not loaded', flush=True)
        return 0
    if mode == 'budget':
        print('[CONTENT_BUDGET] ' + json.dumps(budget()), flush=True)
        return 0
    from scripts.p106b_gate_runtime import wall_limit
    key = mode + ('_' + arm if arm else '')
    activity = safe(EVIDENCE / ('activity_' + key + '.json'))
    if activity.exists():
        raise FileExistsError('owned worker activity already exists')
    reserve = EVAL_RESERVE + RECORD_RESERVE if mode in ('prepare', 'cost', 'train') else RECORD_RESERVE
    absolute = authority(training=mode in ('prepare', 'cost', 'train'))
    if mode in ('evaluate', 'readback'):
        absolute -= RECORD_RESERVE
    remaining = min(absolute, ACTIVE_LIMIT - spent_seconds() - reserve)
    if max_wall_sec > remaining:
        raise Pending('requested bounded worker plus reserves exceeds authority/stage budget')
    began = time.perf_counter()
    code = None
    try:
        with wall_limit(max_wall_sec):
            if mode == 'prepare':
                code = prepare()
            elif mode in ('cost', 'train'):
                code = train(arm, cost=mode == 'cost')
            elif mode == 'evaluate':
                code = evaluate(arm)
            elif mode == 'readback':
                code = readback()
            else:
                raise ValueError('registered worker mode required')
        return code
    finally:
        write(activity, dict(schema=SCHEMA, tag=TAG, key=key, mode=mode, arm=arm,
            seconds=time.perf_counter() - began, returncode=code, complete=code == 0,
            max_wall_sec=max_wall_sec, recorded_at=datetime.now(timezone.utc).isoformat(),
            code_sha256=info()['code_sha256'],
            scope='worker wall including input validation; no regression/wrapper wall'))


def phase_commands(mode, arm, max_wall_sec):
    if mode not in MODES or (mode in ('cost', 'train', 'evaluate')) != (arm in ARMS):
        raise ValueError('exact registered mode/arm pair required')
    if arm is not None and mode not in ('cost', 'train', 'evaluate'):
        raise ValueError('unused arm selector rejected')
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 7200:
        raise ValueError('explicit60..7200 second wall required')
    py = [sys.executable, '-B', '-X', 'utf8']
    driver = py + ['scripts/diag_p106b_content_recovery.py']
    execution = driver + ['--mode', mode, '--worker', '--execute', '--max-wall-sec', str(max_wall_sec)]
    if arm:
        execution += ['--arm', arm]
    prior = 'source' if mode in ('source', 'prepare') else 'preflight'
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_content_objective',
                                'scripts.test_p106b_content_recovery', '-v']),
            ('PREFLIGHT', driver + ['--mode', prior, '--worker', '--execute', '--max-wall-sec', '600']),
            ('EXECUTE', execution)]


def launch(command, timeout):
    """Supervise only the new session's own process group, never user PIDs."""
    process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, start_new_session=True)
    try:
        return process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        interrupted = sys.exc_info()[0] is KeyboardInterrupt
        if process.poll() is None and os.getpgid(process.pid) == process.pid:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        return 130 if interrupted else 124


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, required=True)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--max-wall-sec', type=int, default=3600)
    parser.add_argument('--worker', action='store_true')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true')
    action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    phases = phase_commands(args.mode, args.arm, args.max_wall_sec)
    if args.check_only:
        print('[CONTENT_CHECK_ONLY] ' + json.dumps(info(), sort_keys=True), flush=True)
        return 0
    try:
        if args.worker:
            return worker(args.mode, args.arm, args.max_wall_sec)
        return pipeline(phases, lambda command: launch(command, min(args.max_wall_sec + 120, authority())),
            lambda line: print(line, flush=True), experiment='P106B_CONTENT_RECOVERY_' + args.mode + '_' + str(args.arm or 'all'))['returncode']
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        status, code = source.base.failure_status(exc)
        if code == 9:
            import traceback
            traceback.print_exc()
        print('[CONTENT_FINAL] ' + status + str(code) + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
