#!/usr/bin/env python3
"""Lossless retention-case recovery; fixed scientific inputs and lane receipts.

Old source code and saved answers are immutable. Preparation validates every
frozen retention occurrence, then carries already-complete parent raw lanes.
Only missing, never-started lanes are run. No training or checkpoint writing.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gc
import json
import math
import time
from scripts import diag_p106b_night_eval as old
from scripts import p106b_night_retention_v2 as retention
from scripts import p106b_night_evaluation as method
from scripts import p106b_night_learning as metrics
from scripts.p106b_shards import ShardWriter

c, train = old.c, old.train
FROZEN = c.CORPUS.parent / 'evaluation_v2'
EVIDENCE = c.EVIDENCE / 'evaluate_v2'
LOCAL = ROOT / 'test_result/evidence/local' / c.TAG / 'evaluate_v2'
ENDPOINTS = ('parent', 'ce', 'consistent')
FOUNDATION_ENDPOINTS = ('base_parent', 'foundation_native', 'base_qa', 'base_qa_best', 'cpt_qa', 'cpt_qa_best')
OUTPUTS = old.OUTPUTS
CODE = (*old.CODE, 'scripts/diag_p106b_night_eval_recovery.py',
        'scripts/test_p106b_night_eval_recovery.py', 'scripts/p106b_night_retention_v2.py',
        'scripts/test_p106b_night_retention_v2.py',
        'scripts/diag_p106b_night_foundation.py', 'scripts/p106b_night_foundation_data.py')
OLD_PARENT_LOG = ROOT / 'test_result/101_log_20261017_P106B_Stage4dmWa_night_parent_actual_answers_000119.txt'


def info():
    return dict(schema='P106B_NIGHT_ACTUAL_EVALUATION_RECOVERY_V2', tag=c.TAG,
        code_sha256={p: c.data.digest(ROOT / p) for p in sorted(set(CODE))},
        original_input_report_sha256=c.data.digest(old.FROZEN / 'report.json'),
        scientific_inputs_changed=False, decoding_changed=False,
        event_identity='SHA(lane,frozen_row_index,full_original_row),language,turn,history',
        precision='FP32_MATH', temperature=0., top_k=1, use_cache=True,
        max_new_natural=128, max_new_retention=64, mtp=False,
        teacher_calls=0, updates=0, checkpoints_written=0,
        deadline_utc=c.DEADLINE.isoformat(), gpu_stop_utc=c.TRAIN_STOP.isoformat(),
        inference_quality='raw source-scored scope only; no semantic truth certification')


def safe():
    for target in (FROZEN, EVIDENCE, LOCAL):
        for parent in (target, *target.parents):
            if parent.is_symlink(): raise ValueError('linked recovery namespace')
            if parent == ROOT: break


def generation_proof(event, messages):
    from tinylm.chat.serialize import serialize
    prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
    meta = event['generation']
    if (meta.get('actual_prompt_sha256') != c.data.sha(prompt)
            or meta.get('raw_answer_sha256') != c.data.sha(event['answer'])):
        raise ValueError('complete actual prompt/raw-answer SHA differs')


def natural_recount(events, originals):
    expected = {(p['language'], p['root'], v): p for p in originals for v in (0, 1, 2)}
    seen = set()
    for event in events:
        key = (event['language'], event['root'], event['view'])
        if key in seen or key not in expected: raise ValueError('duplicate/unknown natural case')
        seen.add(key); original = expected[key]
        if any(event[k] != original[k] for k in ('article_id', 'language', 'aliases', 'source_sha256', 'question', 'context')):
            raise ValueError('natural original/gold differs')
        messages = original['views'][str(event['view'])]['messages'][:1]
        if event['messages'] != messages: raise ValueError('natural full source prompt differs')
        generation_proof(event, messages)
    if seen != set(expected): raise ValueError('incomplete natural cases')
    return method.summarize_natural(events)


def recount(lane, events, cases):
    if lane == 'natural': return natural_recount(events, cases[lane])
    if lane == 'cube':
        for event in events: generation_proof(event, event['messages'])
        return method.summarize_cube(events)
    if lane in ('role', 'recovery', 'code'): return retention.verify(events, cases[lane], lane)
    if lane == 'public': return old.public_recount(events, cases['public'])
    raise ValueError('explicit raw lane required')


def source_wire(cases):
    """Actual frozen occurrence coverage, not an answer-quality evaluation."""
    from tinylm.chat.serialize import serialize
    def emit(messages):
        prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
        answer = 'CPU_WIRE_NOT_MODEL_ANSWER'
        return answer, dict(finish_reason='CPU_FIXTURE_ONLY',
            actual_prompt_sha256=c.data.sha(prompt), raw_answer_sha256=c.data.sha(answer))
    totals = {}; prompt_golds = defaultdict(set)
    for lane in ('role', 'recovery', 'code'):
        events = []
        for index, row in enumerate(cases[lane]):
            for turn in range(1, len(row['messages']) // 2 + 1):
                prompt_golds[c.data.sha(row['messages'][:2 * turn - 1])].add(c.data.text(row['messages'][2 * turn - 1]))
            events.extend(retention.collect(row, emit, lane=lane, row_index=index))
        totals[lane] = dict(original_rows=len(cases[lane]), raw_events=len(events),
            counts=retention.verify(events, cases[lane], lane))
    conflicts = {key: len(values) for key, values in prompt_golds.items() if len(values) > 1}
    if conflicts: raise ValueError('identical frozen complete input has conflicting gold: ' + str(conflicts))
    return dict(status='FROZEN_RETENTION_OCCURRENCES_WIRED', lanes=totals,
        identical_prompt_conflicting_gold=0, model_forward=False, cuda=False)


def validate_foundation_report(report, arm, expected):
    if (report.get('status') != 'FOUNDATION_TRAIN_COMPLETE' or report.get('arm') != arm
            or any(report.get(k) != v for k, v in expected.items())
            or report.get('actual_oom') is not False or report.get('checkpoint_written') is not True):
        raise ValueError('complete matched foundation arm/update/source/initializer contract required')
    if arm != 'native':
        history = report.get('history', [])
        if (len(history) != 4 or type(report.get('best_dev_epoch')) is not int
                or not 1 <= report['best_dev_epoch'] <= 4
                or report['best_dev_epoch'] != 1 + min(range(4), key=lambda i: history[i]['dev']['ce'])
                or report['best_dev_ce'] != history[report['best_dev_epoch'] - 1]['dev']['ce']):
            raise ValueError('four-pass and exact DEV-only best checkpoint selection required')


def checkpoint_spec(endpoint):
    if endpoint in ENDPOINTS: return old.checkpoint_spec(endpoint)
    from scripts import diag_p106b_night_foundation as foundation
    if endpoint == 'base_parent': return foundation.data.PARENT, foundation.data.PARENT_SHA
    arm = 'native' if endpoint == 'foundation_native' else endpoint.removesuffix('_best')
    if arm not in foundation.ARMS: raise ValueError('unknown independent endpoint')
    contract = c.required(foundation.data.CORPUS / 'native_contract.json')
    foundation.data.validate_contract(contract)
    report = c.required(foundation.data.EVIDENCE / arm / 'report.json')
    parent_path, parent_sha = foundation.data.PARENT, foundation.data.PARENT_SHA
    if arm == 'cpt_qa': parent_path, parent_sha = checkpoint_spec('foundation_native')
    qr = c.required(c.CORPUS / 'report.json')
    expected = dict(code_sha256=foundation.info()['code_sha256'],
        updates=contract['steps'] if arm == 'native' else 640,
        source_qa_sha256=foundation.data.LOCKED_QA_SHA,
        contract_sha256=c.data.digest(foundation.data.CORPUS / 'native_contract.json'),
        initializer=str(parent_path.relative_to(ROOT)), initializer_sha256=parent_sha,
        checkpoint=str(foundation.checkpoint(arm).relative_to(ROOT)),
        actual_x_tokens=contract['actual_draw_tokens'] if arm == 'native' else qr['exposure']['expected_four_pass']['x_tokens'],
        actual_targets=contract['actual_draw_tokens'] if arm == 'native' else qr['exposure']['expected_four_pass']['assistant_targets'],
        native_replay_x=0 if arm == 'native' else 5242880)
    validate_foundation_report(report, arm, expected)
    best = endpoint.endswith('_best')
    path = report['best_dev_checkpoint'] if best else report['checkpoint']
    identity = report['best_dev_checkpoint_sha256'] if best else report['checkpoint_sha256']
    expected_path = foundation.checkpoint(arm, best and report['best_dev_epoch'] != 4)
    if path != str(expected_path.relative_to(ROOT)): raise ValueError('exact final/DEV selected checkpoint path required')
    return ROOT / path, identity


def receipt_path(endpoint, lane):
    return EVIDENCE / endpoint / (lane + '_receipt.json')


def body_proof(origin, initial, final):
    if origin.get('kind') == 'NEW_MODEL_INFERENCE':
        if not isinstance(initial, str) or len(initial) != 64 or initial != final:
            raise ValueError('lane body unchanged proof required before receipt publication')
        return dict(status='UNCHANGED_WITHIN_THIS_LANE', initial_core_sha256=initial, final_core_sha256=final)
    if origin.get('kind') != 'CARRIED_VERIFIED_RAW': raise ValueError('explicit receipt origin required')
    return dict(status='HISTORICAL_END_FINGERPRINT_NOT_RECORDED', initial_core_sha256=None, final_core_sha256=None)


def receipt(endpoint, lane, spec, origin, core=None, final_core=None):
    cp, identity = checkpoint_spec(endpoint)
    return dict(info(), endpoint=endpoint, lane=lane, status='LANE_COMPLETE',
        directory=str((LOCAL / endpoint).relative_to(ROOT)), checkpoint=str(cp.relative_to(ROOT)),
        checkpoint_sha256=identity, initial_core_sha256=core, output=spec, origin=origin,
        body_proof=body_proof(origin, core, final_core))


def read_receipt(endpoint, lane, cases):
    r = c.required(receipt_path(endpoint, lane))
    cp, identity = checkpoint_spec(endpoint)
    if (r['status'] != 'LANE_COMPLETE' or r['endpoint'] != endpoint or r['lane'] != lane
            or r['code_sha256'] != info()['code_sha256']
            or r['original_input_report_sha256'] != info()['original_input_report_sha256']
            or r['checkpoint_sha256'] != identity or c.data.digest(cp) != identity
            or r['directory'] != str((LOCAL / endpoint).relative_to(ROOT))):
        raise ValueError('same-code/input/checkpoint complete lane receipt required')
    spec = r['output']
    proof = r.get('body_proof', {})
    if proof != body_proof(r['origin'], proof.get('initial_core_sha256'), proof.get('final_core_sha256')):
        raise ValueError('complete per-lane body evidence differs')
    if r['origin']['kind'] == 'CARRIED_VERIFIED_RAW':
        origin = r['origin']; old_directory = old.LOCAL / 'parent'
        if (endpoint != 'parent' or lane not in ('natural', 'cube', 'role', 'recovery', 'code')
                or origin['old_directory'] != str(old_directory.relative_to(ROOT))
                or origin['old_manifest_sha256'] != c.data.digest(old_directory / (lane + '_shards_manifest.json'))
                or origin['old_log_sha256'] != c.data.digest(OLD_PARENT_LOG)
                or origin['old_code_sha256'] != old.info()['code_sha256']):
            raise ValueError('lossless historical origin proof differs')
    if lane not in ('native32', 'native256'):
        events = list(old.stream(LOCAL / endpoint, spec['manifest']))
        if r['origin']['kind'] == 'CARRIED_VERIFIED_RAW':
            original_manifest = c.required(old.LOCAL / 'parent' / (lane + '_shards_manifest.json'))
            original_events = list(old.stream(old.LOCAL / 'parent', original_manifest))
            if lane in ('role', 'recovery', 'code'):
                original_events = retention.augment_legacy(original_events, cases[lane], lane)
            if events != original_events: raise ValueError('carried raw is not the exact preserved original answer set')
        if recount(lane, events, cases) != spec['counts']: raise ValueError('receipt raw recount differs')
    else:
        native_contract(lane, spec, old.read_inputs()[0])
    return r


def native_contract(lane, spec, inputs):
    if (type(spec.get('ce')) not in (int, float) or not math.isfinite(spec['ce']) or spec['ce'] < 0
            or spec.get('val_sha256') != inputs['native_val_sha256']):
        raise ValueError('finite native/source required')
    if lane == 'native32':
        if spec.get('crops') != 32 or spec.get('targets') != 32768: raise ValueError('native32 denominator')
    elif (spec.get('windows') != 256 or spec.get('targets') != 262144
            or spec.get('precision') != 'FP32_MATH'
            or spec.get('offsets_sha256') != c.data.sha(inputs['native256_val_offsets'])):
        raise ValueError('native256 windows/targets/precision/offsets')


def pending_lanes(directory, completed):
    known = set()
    for lane in completed:
        known.add(lane + '_shards_manifest.json')
        manifest = directory / (lane + '_shards_manifest.json')
        if manifest.exists(): known.update(s['path'] for s in c.required(manifest)['shards'])
    unknown = [p.name for p in directory.iterdir() if p.name not in known] if directory.exists() else []
    if unknown: raise FileExistsError('unreceipted partial raw preserved: ' + str(unknown))
    return [lane for lane in ('natural', 'cube', 'role', 'recovery', 'code', 'public', 'native32', 'native256') if lane not in completed]


def prepare():
    import torch
    safe(); inputs, cases = old.read_inputs()
    if FROZEN.exists() or EVIDENCE.exists() or LOCAL.exists(): raise FileExistsError('recovery namespace preserved')
    wire = source_wire(cases)
    original = old.LOCAL / 'parent'
    carried = {}
    for lane in ('natural', 'cube', 'role', 'recovery', 'code'):
        manifest_path = original / (lane + '_shards_manifest.json')
        manifest = c.required(manifest_path)
        if manifest['lineage']['code_sha256'] != old.info()['code_sha256']:
            raise ValueError('legacy raw code differs')
        events = list(old.stream(original, manifest))
        if lane in ('role', 'recovery', 'code'): events = retention.augment_legacy(events, cases[lane], lane)
        counts = recount(lane, events, cases)
        carried[lane] = (events, counts, c.data.digest(manifest_path))
    cp, identity = checkpoint_spec('parent')
    if c.data.digest(cp) != identity: raise ValueError('current preserved parent checkpoint differs')
    log = OLD_PARENT_LOG.read_text(encoding='utf-8')
    if 'duplicate retention event' not in log or '종료코드 9' not in log:
        raise ValueError('exact historical failed attempt required')
    if torch.cuda.is_initialized(): raise ValueError('CPU source wire initialized CUDA')
    FROZEN.mkdir(parents=True, exist_ok=False)
    c.write(FROZEN / 'report.json', dict(info(), status='RECOVERY_CPU_FROZEN', source_wire=wire,
        original_counts=inputs['counts'], old_parent_log_sha256=c.data.digest(OLD_PARENT_LOG),
        original_parent_body_end_fingerprint='NOT_RECORDED_DUE_TO_AGGREGATION_FAILURE',
        original_source_code_frozen=True))
    for lane, (events, counts, manifest_sha) in carried.items():
        writer = ShardWriter(LOCAL / 'parent', lane)
        for event in events: writer.append(event)
        origin = dict(kind='CARRIED_VERIFIED_RAW', inference_repeated=False,
            old_manifest_sha256=manifest_sha, old_directory=str(original.relative_to(ROOT)),
            old_log_sha256=c.data.digest(OLD_PARENT_LOG), old_code_sha256=old.info()['code_sha256'],
            historical_body_end_fingerprint='NOT_RECORDED_DUE_TO_AGGREGATION_FAILURE')
        spec = dict(manifest=writer.close(lineage=dict(info(), origin=origin)), counts=counts)
        c.write(receipt_path('parent', lane), receipt('parent', lane, spec, origin))
    c.write(EVIDENCE / 'inputs.json', c.required(FROZEN / 'report.json'))
    print('[NIGHT_RECOVERY_CPU] ' + json.dumps(dict(status='RECOVERY_CPU_FROZEN',
        carried_lanes=list(carried), source_wire=wire), ensure_ascii=False), flush=True)
    return 0


def read_inputs():
    safe(); r = c.required(FROZEN / 'report.json'); inputs, cases = old.read_inputs()
    if (r['status'] != 'RECOVERY_CPU_FROZEN' or r['code_sha256'] != info()['code_sha256']
            or r['original_input_report_sha256'] != info()['original_input_report_sha256']
            or c.required(EVIDENCE / 'inputs.json') != r):
        raise ValueError('same-code/input frozen recovery required')
    # The final marker is written only after all historical raw carries. A
    # preparation interruption must never silently regenerate a missing carry.
    for lane in ('natural', 'cube', 'role', 'recovery', 'code'):
        ready = read_receipt('parent', lane, cases)
        if ready['origin']['kind'] != 'CARRIED_VERIFIED_RAW':
            raise ValueError('all five immutable historical carries required before GPU')
    return r, inputs, cases


def public_events(model, cfg, tok, device, cases):
    import torch
    import torch.nn.functional as F
    from scripts import diag_p106b_authorized_benchmark as public
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from tinylm.infer.generate import sample
    wrapped = PrecisionForward(model, 'fp32_math')
    for task in (*public.TASKS, 'korquad_free', 'gsm8k_free'):
        rows = [r for r in cases if r['task'] == task]
        if task in public.TASKS:
            for start in range(0, len(rows), 16):
                train.deadline()
                res = public.suite.run_mc(task, [r['item'] for r in rows[start:start + 16]],
                    wrapped, tok, device, 1024, torch, F, False)
                for e in res['rows']: yield dict(e, task=task, kind='mc', skipped=False)
                for e in res['skip_rows']: yield dict(e, task=task, kind='mc', skipped=True)
        else:
            for row in rows:
                train.deadline()
                if row['prompt_tokens'] + 128 > 1024:
                    yield dict(task=task, id=row['id'], kind='gen', skipped=True, reason='complete_prompt_budget')
                    continue
                output, generation = sample(wrapped, cfg, tok, row['prompt'], max_new=128,
                    temperature=0., top_k=1, device='cuda', use_cache=True, logits_last_only=True,
                    return_metadata=True, stop_token_sequences=[tok.encode('<|im_end|>').ids])
                prefix = tok.decode(tok.encode(row['prompt']).ids)
                if not output.startswith(prefix): raise ValueError('public prompt extraction differs')
                raw = output[len(prefix):].split('<|im_end|>', 1)[0]; answer = raw.strip()
                scores = public.answer_scores(answer, row['golds'])
                if task == 'gsm8k_free':
                    scores['numeric_exact'] = int(public.numerical(answer) is not None and public.numerical(answer) == public.numerical(row['golds'][0]))
                yield dict(task=task, id=row['id'], kind='gen', skipped=False, answer=answer,
                    raw_answer=raw, prompt=row['prompt'], golds=row['golds'], generation=generation, scores=scores)
        print('[NIGHT_RECOVERY_PUBLIC] ' + json.dumps(dict(task=task)), flush=True)


def lane_events(lane, model, cfg, tok, device, cases):
    emit = old.emit_function(model, cfg, tok)
    if lane == 'natural':
        for index, pair in enumerate(cases[lane]):
            for view in (0, 1, 2):
                messages = pair['views'][str(view)]['messages'][:1]; answer, generation = emit(messages)
                yield dict(root=pair['root'], article_id=pair['article_id'], language=pair['language'], view=view,
                    source_sha256=pair['source_sha256'], question=pair['question'], context=pair['context'],
                    messages=messages, answer=answer, aliases=pair['aliases'], generation=generation,
                    scores=metrics.qa_scores(answer, pair['aliases'], pair['language']))
            if (index + 1) % 64 == 0: print('[NIGHT_RECOVERY_QA] ' + str(index + 1), flush=True)
    elif lane == 'cube':
        for row in cases[lane]:
            answer, generation = emit(row['messages']); yield dict(row, answer=answer, generation=generation)
    elif lane in ('role', 'recovery', 'code'):
        short = old.emit_function(model, cfg, tok, 64)
        for index, row in enumerate(cases[lane]):
            yield from retention.collect(row, short, lane=lane, row_index=index)
    elif lane == 'public': yield from public_events(model, cfg, tok, device, cases[lane])
    else: raise ValueError('raw-answer lane required')


def evaluate(endpoint, max_wall_sec):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    _, inputs, cases = read_inputs()
    target = EVIDENCE / (endpoint + '_report.json'); directory = LOCAL / endpoint
    if target.exists(): raise FileExistsError('complete endpoint preserved')
    existing = {lane: read_receipt(endpoint, lane, cases) for lane in OUTPUTS if receipt_path(endpoint, lane).exists()}
    pending = pending_lanes(directory, existing)
    cp, identity = checkpoint_spec(endpoint)
    if c.data.digest(cp) != identity: raise ValueError('fixed endpoint checkpoint changed')
    idle_before_gpu(); directory.mkdir(parents=True, exist_ok=True); began = time.perf_counter()
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    with wall_limit(max_wall_sec):
        model, cfg, device = load_model(arch='dense', ckpt_path=str(cp), device='cuda')
        tok = Tokenizer.from_file(str(c.data.TOKENIZER)); initial = train.runtime.state_fingerprint(model)
        for r in existing.values():
            if r['origin']['kind'] == 'NEW_MODEL_INFERENCE' and r['initial_core_sha256'] != initial:
                raise ValueError('saved lane came from a different strict model body')
        torch.cuda.reset_peak_memory_stats()
        with torch.no_grad():
            for lane in pending:
                train.deadline()
                if lane in ('native32', 'native256'):
                    spec = train.runtime.native_ce(model, c.NATIVE) if lane == 'native32' else old.native256(model, inputs, tok)
                    native_contract(lane, spec, inputs); model.eval(); model.freeze_quant()
                else:
                    writer = ShardWriter(directory, lane); events = []
                    for event in lane_events(lane, model, cfg, tok, device, cases):
                        writer.append(event); events.append(event)
                    manifest = writer.close(lineage=info())
                    spec = dict(manifest=manifest, counts=recount(lane, events, cases))
                final_core = train.runtime.state_fingerprint(model)
                if c.data.digest(cp) != identity: raise ValueError('lane changed checkpoint file')
                completed = receipt(endpoint, lane, spec,
                    dict(kind='NEW_MODEL_INFERENCE', inference_repeated=False), initial, final_core)
                c.write(receipt_path(endpoint, lane), completed)
                print('[NIGHT_RECOVERY_LANE] ' + json.dumps(dict(endpoint=endpoint, lane=lane,
                    rows=spec.get('manifest', {}).get('rows'), status='LANE_COMPLETE')), flush=True)
        if train.runtime.state_fingerprint(model) != initial: raise ValueError('read-only inference changed model body')
        if c.data.digest(cp) != identity: raise ValueError('read-only inference changed checkpoint file')
        receipts = {lane: read_receipt(endpoint, lane, cases) for lane in OUTPUTS}
        result = dict(info(), status='ACTUAL_EVALUATION_COMPLETE', endpoint=endpoint,
            directory=str(directory.relative_to(ROOT)), checkpoint=str(cp.relative_to(ROOT)), checkpoint_sha256=identity,
            current_inference_body_unchanged=True, initial_core_sha256=initial,
            original_carried_body_end_fingerprint='NOT_RECORDED' if any(r['origin']['kind'] == 'CARRIED_VERIFIED_RAW' for r in receipts.values()) else 'NOT_APPLICABLE',
            outputs={lane: r['output'] for lane, r in receipts.items()},
            origins={lane: r['origin'] for lane, r in receipts.items()},
            receipt_sha256={lane: c.data.digest(receipt_path(endpoint, lane)) for lane in OUTPUTS},
            input_report_sha256=c.data.digest(FROZEN / 'report.json'),
            whole_seconds=time.perf_counter() - began, peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
        endpoint_contract(result, endpoint, inputs)
        c.write(target, result)
        print('[NIGHT_RECOVERY_ENDPOINT] ' + json.dumps(dict(endpoint=endpoint,
            whole_seconds=result['whole_seconds'], newly_run=pending,
            natural=result['outputs']['natural']['counts'], cube=result['outputs']['cube']['counts']), ensure_ascii=False), flush=True)
    del model; gc.collect(); torch.cuda.empty_cache()
    return 0


def endpoint_contract(report, endpoint, inputs):
    if (report.get('status') != 'ACTUAL_EVALUATION_COMPLETE' or report.get('endpoint') != endpoint
            or report.get('updates') != 0 or report.get('checkpoints_written') != 0
            or report.get('current_inference_body_unchanged') is not True
            or report.get('directory') != str((LOCAL / endpoint).relative_to(ROOT))
            or set(report.get('outputs', {})) != OUTPUTS or set(report.get('receipt_sha256', {})) != OUTPUTS):
        raise ValueError('complete exact endpoint/lane/receipt contract required')
    for lane, spec in report['outputs'].items():
        if lane in ('native32', 'native256'): native_contract(lane, spec, inputs)
        elif (not isinstance(spec.get('counts'), dict) or not spec['counts']
                or spec.get('manifest', {}).get('rows', 0) <= 0 or not spec['manifest'].get('shards')):
            raise ValueError('complete nonempty raw manifest/counts required')


def readback(foundation=False):
    _, inputs, cases = read_inputs(); results = {}; natural = {}
    endpoints = FOUNDATION_ENDPOINTS if foundation else ENDPOINTS
    for endpoint in endpoints:
        path = EVIDENCE / (endpoint + '_report.json'); r = c.required(path)
        endpoint_contract(r, endpoint, inputs)
        if r['code_sha256'] != info()['code_sha256'] or r['input_report_sha256'] != c.data.digest(FROZEN / 'report.json'):
            raise ValueError('complete same-code/current source report required')
        for lane in OUTPUTS:
            checked = read_receipt(endpoint, lane, cases)
            if checked['output'] != r['outputs'][lane] or c.data.digest(receipt_path(endpoint, lane)) != r['receipt_sha256'][lane]:
                raise ValueError('exact endpoint/receipt proof differs')
        natural[endpoint] = list(old.stream(LOCAL / endpoint, r['outputs']['natural']['manifest']))
        results[endpoint] = c.data.digest(path)
    pairs = (('base_parent', 'base_qa'), ('foundation_native', 'cpt_qa'), ('base_qa', 'cpt_qa'),
             ('base_qa_best', 'cpt_qa_best')) if foundation else (('parent', 'ce'), ('parent', 'consistent'), ('ce', 'consistent'))
    comparisons = {a + '__' + b: method.paired_natural(natural[a], natural[b]) for a, b in pairs}
    c.write(EVIDENCE / ('foundation_readback.json' if foundation else 'paired_readback.json'),
        dict(info(), status='RAW_RECOUNTED', errors=0, endpoints_sha256=results, paired=comparisons,
             inference_seeds=1, scope='fixed case/article CI, not learning-seed variance or broad truth'))
    print('[NIGHT_RECOVERY_READBACK] ' + json.dumps(comparisons, ensure_ascii=False), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('freeze', 'evaluate', 'readback', 'foundation-readback'), required=True)
    parser.add_argument('--endpoint', choices=ENDPOINTS + FOUNDATION_ENDPOINTS)
    parser.add_argument('--max-wall-sec', type=int, default=7200)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true'); group.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.check_only: print('[NIGHT_RECOVERY_CHECK] ' + json.dumps(info())); return 0
    if args.mode == 'evaluate' and args.endpoint is None: parser.error('explicit endpoint required')
    try:
        train.deadline()
        if args.mode == 'freeze': return prepare()
        if args.mode in ('readback', 'foundation-readback'): return readback(args.mode == 'foundation-readback')
        remaining = int((c.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds())
        if remaining < 60: raise RuntimeError('09:00 documentation reserve')
        return evaluate(args.endpoint, min(args.max_wall_sec, remaining))
    except KeyboardInterrupt:
        print('[NIGHT_RECOVERY_INTERRUPTED] partial raw preserved'); return 130
    except Exception as exc:
        import traceback
        traceback.print_exc(); print('[NIGHT_RECOVERY_ERROR] ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
