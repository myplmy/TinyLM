#!/usr/bin/env python3
"""Read-only same-instruction view1/3 probe after the primary full evaluations.

No training, checkpoint writes, source reselection or legacy gate completion.
The complete TEST64 source is inherited from the already frozen parent panel.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from datetime import datetime, timezone
import gc
import json
import time
from scripts import p106b_night_order_probe as method
from scripts import diag_p106b_night_parent_panel as panel
from scripts import diag_p106b_night_diversity_scope_eval_v2 as unique
from scripts import diag_p106b_night_prompt_eval as prompt
from scripts.p106b_shards import ShardWriter

e, qa = panel.e, panel.qa
TAG = 'p106b_night_order_probe_v1_s1337'
FROZEN = ROOT / 'HF/sft_ready' / TAG / 'source'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
LOCAL = ROOT / 'test_result/evidence/local' / TAG
ENDPOINTS = ('base_qa', 'unique32k')
CODE = ('scripts/diag_p106b_night_order_probe.py', 'scripts/test_p106b_night_order_probe_runtime.py',
        'scripts/p106b_night_order_probe.py', 'scripts/test_p106b_night_order_probe.py',
        *panel.CODE, *unique.CODE, *prompt.CODE)


def info():
    return dict(schema='P106B_NIGHT_ORDER_PROBE_RUNTIME_V1', tag=TAG,
        code_sha256={p: qa.data.digest(ROOT / p) for p in sorted(set(CODE))},
        source_panel_cpu_sha256=qa.data.digest(panel.FROZEN / 'report.json'),
        original_eval_cpu_sha256=qa.data.digest(e.FROZEN / 'report.json'),
        unique_eval_cpu_sha256=qa.data.digest(unique.FROZEN / 'report.json'),
        endpoints=list(ENDPOINTS), roots=64, per_language=32, views=[1, 3],
        precision='FP32_MATH', temperature=0., top_k=1, max_new=128, context=1024,
        use_cache=True, mtp=False, updates=0, checkpoints_written=0,
        legacy_order_training_gate_credited=False, source_selection_changed=False,
        required_primary_evaluations=list(prompt.ENDPOINTS) + list(unique.ENDPOINTS),
        cohort='same repeatedly observed development articles; not a newly unseen TEST',
        interpretation='input field-order effect within two fixed models; not architecture causality or world truth')


def safe():
    for target in (FROZEN, EVIDENCE, LOCAL):
        for parent in (target, *target.parents):
            if parent.is_symlink(): raise ValueError('linked order-probe namespace')
            if parent == ROOT: break


def wire(pairs, tok):
    from tinylm.chat.serialize import serialize
    proof = method.source_proof(pairs); lengths = []
    for index, pair in enumerate(pairs):
        values = {}
        for view in method.VIEWS:
            prompt = serialize(dict(messages=method.messages(pair, view)), 'chatml', add_generation_prompt=True)
            count = len(tok.encode(prompt).ids)
            if count + 128 > 1024: raise ValueError('complete input plus128 must fit; no truncation')
            if qa.data.sha(prompt) != proof['cases'][index]['prompt_sha256'][str(view)]:
                raise ValueError('same actual complete source prompt required')
            values[str(view)] = count
        lengths.append(values)
    review = []
    for language in ('ko', 'en'):
        indices = [i for i, pair in enumerate(pairs) if pair['language'] == language]
        review.extend(sorted(indices, key=lambda i: qa.data.sha([20261017, 'order-probe-review', pairs[i]['root']]))[:4])
    schedule = [[i, view] for i in range(64) for view in ((1, 3) if i % 2 == 0 else (3, 1))]
    return dict(source=proof, prompt_tokens=lengths, review_indices=sorted(review),
        schedule=schedule, schedule_sha256=qa.data.sha(schedule),
        max_prompt_tokens=max(max(v.values()) for v in lengths),
        token_length_differences=sum(v['1'] != v['3'] for v in lengths))


def prepare():
    import torch
    from tokenizers import Tokenizer
    safe(); _, _, cases = panel.read_inputs(); pairs = cases['natural']
    if FROZEN.exists() or EVIDENCE.exists(): raise FileExistsError('old probe source preserved')
    proof = wire(pairs, Tokenizer.from_file(str(qa.data.TOKENIZER)))
    if torch.cuda.is_initialized(): raise ValueError('CPU source binding initialized CUDA')
    qa.write(FROZEN / 'cases.json', pairs)
    result = dict(info(), status='ORDER_PROBE_CPU_FROZEN', wire=proof,
        cases_file_sha256=qa.data.digest(FROZEN / 'cases.json'),
        cuda_initialized=False, model_loaded=False, model_forward=False)
    qa.write(FROZEN / 'report.json', result); qa.write(EVIDENCE / 'inputs.json', result)
    print('[ORDER_PROBE_CPU] ' + json.dumps(dict(roots=64, views=[1, 3],
        max_prompt=proof['max_prompt_tokens'], token_length_differences=proof['token_length_differences'])), flush=True)
    return 0


def read_inputs():
    from tokenizers import Tokenizer
    safe(); result = qa.required(FROZEN / 'report.json'); _, _, cases = panel.read_inputs()
    pairs = cases['natural']; actual = wire(pairs, Tokenizer.from_file(str(qa.data.TOKENIZER)))
    if (result.get('status') != 'ORDER_PROBE_CPU_FROZEN' or result.get('code_sha256') != info()['code_sha256']
            or result.get('source_panel_cpu_sha256') != info()['source_panel_cpu_sha256']
            or result.get('original_eval_cpu_sha256') != info()['original_eval_cpu_sha256']
            or result.get('unique_eval_cpu_sha256') != info()['unique_eval_cpu_sha256']
            or qa.required(EVIDENCE / 'inputs.json') != result or result['wire'] != actual
            or qa.required(FROZEN / 'cases.json') != pairs
            or qa.data.digest(FROZEN / 'cases.json') != result['cases_file_sha256']):
        raise ValueError('complete same-code/source wire required')
    return result, pairs


def full_endpoint(endpoint):
    if endpoint not in ENDPOINTS: raise ValueError('two preregistered final checkpoints only')
    return verified_primary(e if endpoint == 'base_qa' else unique, endpoint)


def verified_primary(provider, endpoint):
    _, inputs, cases = e.read_inputs()
    if provider is not e:
        other_inputs, other_cases = provider.read_inputs()
        if other_inputs != inputs or other_cases != cases: raise ValueError('identical primary full source required')
    path = provider.EVIDENCE / (endpoint + '_report.json'); report = qa.required(path)
    provider.endpoint_contract(report, endpoint, inputs)
    selected = provider.checkpoint_spec(endpoint); cp, identity = selected[:2]
    core = report['initial_core_sha256'] if provider is e else selected[2]
    if (report['code_sha256'] != provider.info()['code_sha256']
            or report['input_report_sha256'] != qa.data.digest(provider.FROZEN / 'report.json')
            or report['checkpoint'] != str(cp.relative_to(ROOT)) or report['checkpoint_sha256'] != identity
            or report['initial_core_sha256'] != core or qa.data.digest(cp) != identity):
        raise ValueError('full primary evaluation/source/strict checkpoint proof required')
    for lane in e.OUTPUTS:
        receipt = provider.read_receipt(endpoint, lane, cases) if provider is e else provider.read_receipt(endpoint, lane, cases, inputs)
        if (receipt['output'] != report['outputs'][lane]
                or qa.data.digest(provider.receipt_path(endpoint, lane)) != report['receipt_sha256'][lane]):
            raise ValueError('all primary full raw/body/receipt lanes must be complete')
    natural = list(e.old.stream(provider.LOCAL / endpoint, report['outputs']['natural']['manifest']))
    return cp, identity, core, qa.data.digest(path), natural


def primary_prerequisites():
    result = {}
    for provider, endpoints in ((e, ('base_qa',)), (prompt, prompt.ENDPOINTS), (unique, unique.ENDPOINTS)):
        for endpoint in endpoints:
            _, _, _, identity, _ = verified_primary(provider, endpoint)
            result[endpoint] = identity
    return result


def recount(events, pairs, frozen):
    counts = method.summarize(events, pairs)
    for event in events:
        expected = frozen['wire']['prompt_tokens'][event['frozen_row_index']][str(event['view'])]
        if event['generation']['prompt_tokens'] != expected: raise ValueError('actual tokenizer prompt count differs')
    return counts


def repeat_agreement(events, old_natural):
    original = {(r['language'], r['root']):r for r in old_natural if r['view'] == 1}
    current = [r for r in events if r['view'] == 1]; changed = []
    for event in current:
        old = original[event['language'], event['root']]
        if event['messages'] != old['messages']: raise ValueError('baseline redecode prompt changed')
        if event['answer'] != old['answer']: changed.append(dict(root=event['root'], language=event['language']))
    return dict(n=len(current), same_answer=len(current) - len(changed), changed=changed,
        different_answer_is_not_automatically_incorrect=True, correctness_not_inferred_from_repeat_agreement=True)


def endpoint_report(endpoint, frozen, pairs):
    cp, identity, core, full_hash, old_natural = full_endpoint(endpoint)
    primary = primary_prerequisites()
    path = EVIDENCE / endpoint / 'report.json'; report = qa.required(path)
    if (report.get('status') != 'READONLY_ORDER_PROBE_COMPLETE' or report.get('endpoint') != endpoint
            or report.get('code_sha256') != info()['code_sha256']
            or report.get('input_report_sha256') != qa.data.digest(FROZEN / 'report.json')
            or report.get('primary_full_report_sha256') != full_hash
            or report.get('required_primary_report_sha256') != primary
            or report.get('checkpoint') != str(cp.relative_to(ROOT))
            or report.get('checkpoint_sha256') != identity or report.get('initial_core_sha256') != core
            or report.get('body_proof') != e.body_proof(dict(kind='NEW_MODEL_INFERENCE'), core, core)
            or report.get('directory') != str((LOCAL / endpoint).relative_to(ROOT))
            or report.get('updates') != 0 or report.get('checkpoints_written') != 0
            or report.get('manifest', {}).get('rows') != 128):
        raise ValueError('complete read-only probe/source/strict body proof required')
    events = list(e.old.stream(LOCAL / endpoint, report['manifest']))
    if recount(events, pairs, frozen) != report['counts'] or repeat_agreement(events, old_natural) != report['repeat_agreement']:
        raise ValueError('exact probe raw/source/generation recount differs')
    return report, events


def evaluate(endpoint, seconds):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    frozen, pairs = read_inputs(); primary = primary_prerequisites()
    cp, identity, core, full_hash, old_natural = full_endpoint(endpoint)
    completed = []
    for name in ENDPOINTS:
        if (EVIDENCE / name / 'report.json').exists(): endpoint_report(name, frozen, pairs); completed.append(name)
    remaining = (qa.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds()
    needed = 900 * (len(ENDPOINTS) - len(completed)) + 300
    if needed >= remaining: raise ValueError('extra probe reserve does not fit before09:00')
    directory = LOCAL / endpoint; target = EVIDENCE / endpoint / 'report.json'
    if target.exists() or directory.exists(): raise FileExistsError('old complete/partial probe preserved')
    idle_before_gpu(); directory.mkdir(parents=True, exist_ok=False); began = time.perf_counter()
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    with wall_limit(min(seconds, int(remaining))):
        model, cfg, device = load_model(arch='dense', ckpt_path=str(cp), device='cuda')
        initial = panel.foundation.runtime.state_fingerprint(model)
        if initial != core: raise ValueError('strict loaded selected model body differs')
        tok = Tokenizer.from_file(str(qa.data.TOKENIZER)); emit = e.old.emit_function(model, cfg, tok, 128)
        writer = ShardWriter(directory, 'answers'); events = []; per_root = {}; torch.cuda.reset_peak_memory_stats()
        with torch.no_grad():
            for index, view in frozen['wire']['schedule']:
                e.train.deadline(training=True)
                pair = pairs[index]; answer, generation = emit(method.messages(pair, view))
                event = method.make_event(pair, index, view, answer, generation); writer.append(event); events.append(event)
                per_root.setdefault(index, {})[view] = answer
                if len(per_root[index]) == 2 and index in frozen['wire']['review_indices']:
                    print('[ORDER_PROBE_REVIEW] ' + json.dumps(dict(index=index, language=pair['language'],
                        question=pair['question'], aliases=pair['aliases'], answers=per_root[index]), ensure_ascii=False), flush=True)
                if len(events) % 32 == 0: print('[ORDER_PROBE_PROGRESS] ' + str(len(events)), flush=True)
        final = panel.foundation.runtime.state_fingerprint(model)
        body = e.body_proof(dict(kind='NEW_MODEL_INFERENCE'), initial, final)
        if qa.data.digest(cp) != identity: raise ValueError('read-only probe changed checkpoint file')
        manifest = writer.close(lineage=info()); counts = recount(events, pairs, frozen)
        result = dict(info(), status='READONLY_ORDER_PROBE_COMPLETE', endpoint=endpoint,
            input_report_sha256=qa.data.digest(FROZEN / 'report.json'), primary_full_report_sha256=full_hash,
            required_primary_report_sha256=primary,
            checkpoint=str(cp.relative_to(ROOT)), checkpoint_sha256=identity, initial_core_sha256=core,
            body_proof=body, directory=str(directory.relative_to(ROOT)), manifest=manifest, counts=counts,
            repeat_agreement=repeat_agreement(events, old_natural), whole_seconds=time.perf_counter() - began,
            peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20, peak_scope='torch allocator only')
        qa.write(target, result); endpoint_report(endpoint, frozen, pairs)
        print('[ORDER_PROBE_COMPLETE] ' + json.dumps(dict(endpoint=endpoint, seconds=result['whole_seconds'],
            by_language=counts['by_language'], repeat_agreement=result['repeat_agreement']), ensure_ascii=False), flush=True)
    del model; gc.collect(); torch.cuda.empty_cache()
    return 0


def readback():
    frozen, pairs = read_inputs(); reports = {}
    for endpoint in ENDPOINTS:
        report, events = endpoint_report(endpoint, frozen, pairs)
        reports[endpoint] = dict(report_sha256=qa.data.digest(EVIDENCE / endpoint / 'report.json'),
            counts=report['counts'], repeat_agreement=report['repeat_agreement'])
    qa.write(EVIDENCE / 'paired_readback.json', dict(info(), status='ORDER_PROBE_RAW_RECOUNTED', errors=0,
        input_report_sha256=qa.data.digest(FROZEN / 'report.json'), endpoints=reports,
        primary_comparison='within each fixed model: same source and instruction, different field order',
        secondary_between_models='8k-four-pass versus32k-once package, one learning seed and slightly different actual x tokens'))
    print('[ORDER_PROBE_READBACK] complete_two_models raw_recount_errors=0', flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('freeze', 'evaluate', 'readback'), required=True)
    p.add_argument('--endpoint', choices=ENDPOINTS); p.add_argument('--max-wall-sec', type=int, default=900)
    g = p.add_mutually_exclusive_group(required=True); g.add_argument('--execute', action='store_true'); g.add_argument('--check-only', action='store_true')
    a = p.parse_args()
    if not 60 <= a.max_wall_sec <= 900: p.error('bounded60..900 wall required')
    if a.check_only: print(json.dumps(info())); return 0
    try:
        e.train.deadline()
        if a.mode == 'freeze': return prepare()
        if a.mode == 'readback': return readback()
        if a.endpoint is None: p.error('explicit endpoint required')
        return evaluate(a.endpoint, a.max_wall_sec)
    except KeyboardInterrupt: print('[ORDER_PROBE_INTERRUPTED] partial preserved'); return 130
    except Exception as exc:
        import traceback
        traceback.print_exc(); print('[ORDER_PROBE_ERROR] ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
