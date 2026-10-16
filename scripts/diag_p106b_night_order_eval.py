#!/usr/bin/env python3
"""Same frozen cohort for field-order-only views0/3 and DEV representatives.

No training/checkpoint writing. This is a repeated development comparison after
the first CE/KL study, not a newly untouched benchmark or semantic verifier.
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
from scripts import diag_p106b_night_order as training
from scripts import diag_p106b_night_diversity_eval as baseline
from scripts import diag_p106b_night_eval_recovery as evaluation
from scripts.p106b_shards import ShardWriter

qa, previous = training.qa, training.previous
FROZEN = training.CORPUS.parent / 'evaluation'
EVIDENCE = training.EVIDENCE / 'evaluate'
LOCAL = ROOT / 'test_result/evidence/local' / training.TAG / 'evaluate'
ENDPOINTS = ('question_first', 'question_first_best')
CODE = ('scripts/diag_p106b_night_order_eval.py', 'scripts/test_p106b_night_order_eval.py',
        *training.CODE, *evaluation.CODE, *baseline.CODE)


def info():
    return dict(schema='P106B_NIGHT_ORDER_ACTUAL_EVALUATION_V1', tag=training.TAG,
        code_sha256={path: qa.data.digest(ROOT / path) for path in sorted(set(CODE))},
        endpoints=list(ENDPOINTS), original_scientific_input_sha256=evaluation.info()['original_input_report_sha256'],
        recovery_input_sha256=qa.data.digest(evaluation.FROZEN / 'report.json'),
        training_cpu_sha256=qa.data.digest(training.CORPUS / 'report.json'),
        scientific_inputs_changed=False, precision='FP32_MATH', temperature=0., top_k=1,
        max_new_natural=128, max_new_retention=64, use_cache=True, mtp=False,
        model_training_seeds=1, updates=0, checkpoints_written=0,
        selection='final640 primary; separate DEV CE minimum, never TEST-selected',
        cohort_scope='same held-from-training articles; now repeatedly observed development cohort',
        native_metric_vocab_comparison='same TinyLM tokenizer only',
        semantic_truth='scoped source/code metrics and separate manual reading, not general intelligence')


def namespace():
    for target in (FROZEN, EVIDENCE, LOCAL):
        for parent in (target, *target.parents):
            if parent.is_symlink(): raise ValueError('linked question_first evaluation namespace')
            if parent == ROOT: break


def prepare():
    import torch
    namespace(); _, inputs, cases = evaluation.read_inputs()
    cpu = qa.required(training.CORPUS / 'report.json')
    if cpu['status'] != 'ORDER_CPU_FROZEN' or cpu['code_sha256'] != training.info()['code_sha256']:
        raise ValueError('same-code real question_first training CPU required')
    if FROZEN.exists() or EVIDENCE.exists(): raise FileExistsError('old evaluation source preserved')
    if torch.cuda.is_initialized(): raise ValueError('CPU evaluation binding initialized CUDA')
    FROZEN.mkdir(parents=True, exist_ok=False)
    result = dict(info(), status='ORDER_EVAL_INPUTS_FROZEN', original_counts=inputs['counts'],
        actual_case_sets_sha256={lane: qa.data.sha(rows) for lane, rows in cases.items()},
        cuda_initialized=False, model_loaded=False, optimizer_updates=0)
    qa.write(FROZEN / 'report.json', result); qa.write(EVIDENCE / 'inputs.json', result)
    print('[ORDER_EVAL_CPU] ' + json.dumps(dict(status=result['status'], counts=inputs['counts'])), flush=True)
    return 0


def read_inputs():
    namespace(); frozen = qa.required(FROZEN / 'report.json'); _, inputs, cases = evaluation.read_inputs()
    if (frozen['status'] != 'ORDER_EVAL_INPUTS_FROZEN' or frozen['code_sha256'] != info()['code_sha256']
            or frozen['recovery_input_sha256'] != info()['recovery_input_sha256']
            or frozen['training_cpu_sha256'] != info()['training_cpu_sha256']
            or qa.required(EVIDENCE / 'inputs.json') != frozen
            or frozen['actual_case_sets_sha256'] != {lane: qa.data.sha(rows) for lane, rows in cases.items()}):
        raise ValueError('complete same-code/input bound evaluation required')
    return inputs, cases


def checkpoint_spec(endpoint):
    if endpoint not in ENDPOINTS: raise ValueError('registered question_first endpoint required')
    best = endpoint.endswith('_best')
    proof = qa.required(training.CORPUS / 'report.json')
    if not training.completed(proof): raise ValueError('full same-source640 question_first training required')
    report = qa.required(training.EVIDENCE / 'question_first/report.json')
    history = report['history']; quarter = report['best_dev_quarter']
    if (len(history) != 4 or type(quarter) is not int or not 1 <= quarter <= 4
            or quarter != 1 + min(range(4), key=lambda i: history[i]['dev']['ce'])
            or report['best_dev_ce'] != history[quarter - 1]['dev']['ce']):
        raise ValueError('exact DEV-only quarter selection required')
    path = report['best_dev_checkpoint'] if best else report['checkpoint']
    identity = report['best_dev_checkpoint_sha256'] if best else report['checkpoint_sha256']
    core = report['best_dev_core_sha256'] if best else report['final_core_sha256']
    if path != str(training.checkpoint(best and quarter != 4).relative_to(ROOT)):
        raise ValueError('exact final/DEV question_first checkpoint path required')
    cp = ROOT / path
    if qa.data.digest(cp) != identity: raise ValueError('saved selected question_first body changed')
    return cp, identity, core


def receipt_path(endpoint, lane):
    return EVIDENCE / endpoint / (lane + '_receipt.json')


def endpoint_contract(report, endpoint, inputs):
    if (report.get('status') != 'ACTUAL_EVALUATION_COMPLETE' or report.get('endpoint') != endpoint
            or report.get('updates') != 0 or report.get('checkpoints_written') != 0
            or report.get('body_unchanged') is not True
            or report.get('directory') != str((LOCAL / endpoint).relative_to(ROOT))
            or set(report.get('outputs', {})) != evaluation.OUTPUTS
            or set(report.get('receipt_sha256', {})) != evaluation.OUTPUTS):
        raise ValueError('complete two-endpoint endpoint/lane contract required')
    for lane, spec in report['outputs'].items():
        if lane in ('native32', 'native256'): evaluation.native_contract(lane, spec, inputs)
        elif (not isinstance(spec.get('counts'), dict) or not spec['counts']
                or not spec.get('manifest', {}).get('shards') or spec['manifest'].get('rows', 0) <= 0):
            raise ValueError('nonempty complete actual-answer lane required')


def read_receipt(endpoint, lane, cases, inputs):
    r = qa.required(receipt_path(endpoint, lane)); cp, identity, core = checkpoint_spec(endpoint)
    if (r.get('status') != 'LANE_COMPLETE' or r.get('endpoint') != endpoint or r.get('lane') != lane
            or r.get('code_sha256') != info()['code_sha256']
            or r.get('checkpoint_sha256') != identity or r.get('initial_core_sha256') != core
            or r.get('body_proof') != evaluation.body_proof(dict(kind='NEW_MODEL_INFERENCE'), core, core)
            or r.get('input_report_sha256') != qa.data.digest(FROZEN / 'report.json')):
        raise ValueError('complete same-code/strict-body/source lane proof required')
    output = r['output']
    if lane in ('native32', 'native256'): evaluation.native_contract(lane, output, inputs)
    else:
        events = list(evaluation.old.stream(LOCAL / endpoint, output['manifest']))
        if evaluation.recount(lane, events, cases) != output['counts']:
            raise ValueError('question_first endpoint raw/original/gold/history recount differs')
    return r


def evaluate(endpoint, max_wall_sec):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    inputs, cases = read_inputs(); cp, identity, expected_core = checkpoint_spec(endpoint)
    target = EVIDENCE / (endpoint + '_report.json'); directory = LOCAL / endpoint
    if target.exists() or directory.exists(): raise FileExistsError('old complete/partial question_first answers preserved')
    idle_before_gpu(); directory.mkdir(parents=True, exist_ok=False); began = time.perf_counter()
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    with wall_limit(max_wall_sec):
        model, cfg, device = load_model(arch='dense', ckpt_path=str(cp), device='cuda')
        initial = training.foundation.runtime.state_fingerprint(model)
        if initial != expected_core: raise ValueError('strict loaded question_first body differs from selected checkpoint')
        tok = Tokenizer.from_file(str(qa.data.TOKENIZER)); torch.cuda.reset_peak_memory_stats(); outputs = {}
        with torch.no_grad():
            for lane in ('natural', 'cube', 'role', 'recovery', 'code', 'public', 'native32', 'native256'):
                previous.deadline()
                if lane in ('native32', 'native256'):
                    output = training.foundation.runtime.native_ce(model, qa.NATIVE) if lane == 'native32' else evaluation.old.native256(model, inputs, tok)
                    model.eval(); model.freeze_quant(); evaluation.native_contract(lane, output, inputs)
                else:
                    writer = ShardWriter(directory, lane); values = []
                    for event in evaluation.lane_events(lane, model, cfg, tok, device, cases):
                        writer.append(event); values.append(event)
                    output = dict(manifest=writer.close(lineage=info()), counts=evaluation.recount(lane, values, cases))
                final_core = training.foundation.runtime.state_fingerprint(model)
                proof = evaluation.body_proof(dict(kind='NEW_MODEL_INFERENCE'), initial, final_core)
                if qa.data.digest(cp) != identity: raise ValueError('read-only evaluation changed checkpoint file')
                receipt = dict(info(), status='LANE_COMPLETE', endpoint=endpoint, lane=lane,
                    checkpoint_sha256=identity, initial_core_sha256=initial, body_proof=proof,
                    input_report_sha256=qa.data.digest(FROZEN / 'report.json'), output=output)
                qa.write(receipt_path(endpoint, lane), receipt); outputs[lane] = output
                print('[ORDER_EVAL_LANE] ' + json.dumps(dict(endpoint=endpoint, lane=lane)), flush=True)
        result = dict(info(), status='ACTUAL_EVALUATION_COMPLETE', endpoint=endpoint,
            checkpoint=str(cp.relative_to(ROOT)), checkpoint_sha256=identity, initial_core_sha256=initial,
            directory=str(directory.relative_to(ROOT)), body_unchanged=True,
            input_report_sha256=qa.data.digest(FROZEN / 'report.json'), outputs=outputs,
            receipt_sha256={lane: qa.data.digest(receipt_path(endpoint, lane)) for lane in evaluation.OUTPUTS},
            whole_seconds=time.perf_counter() - began, peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
        endpoint_contract(result, endpoint, inputs)
        for lane in evaluation.OUTPUTS: read_receipt(endpoint, lane, cases, inputs)
        qa.write(target, result)
        print('[ORDER_EVAL_COMPLETE] ' + json.dumps(dict(endpoint=endpoint, whole_seconds=result['whole_seconds'])), flush=True)
    del model; gc.collect(); torch.cuda.empty_cache()
    return 0


def readback():
    inputs, cases = read_inputs(); reports = {}; natural = {}
    for endpoint in ENDPOINTS:
        path = EVIDENCE / (endpoint + '_report.json'); r = qa.required(path)
        endpoint_contract(r, endpoint, inputs)
        cp, identity, core = checkpoint_spec(endpoint)
        if (r['code_sha256'] != info()['code_sha256']
                or r['input_report_sha256'] != qa.data.digest(FROZEN / 'report.json')
                or r.get('checkpoint') != str(cp.relative_to(ROOT))
                or r.get('checkpoint_sha256') != identity or r.get('initial_core_sha256') != core):
            raise ValueError('same-code/current frozen source complete endpoint required')
        for lane in evaluation.OUTPUTS:
            receipt = read_receipt(endpoint, lane, cases, inputs)
            if (receipt['output'] != r['outputs'][lane]
                    or qa.data.digest(receipt_path(endpoint, lane)) != r['receipt_sha256'][lane]):
                raise ValueError('complete endpoint/receipt identity mismatch')
        natural[endpoint] = list(evaluation.old.stream(LOCAL / endpoint, r['outputs']['natural']['manifest']))
        reports[endpoint] = qa.data.digest(path)
    # Same32k question/answer exposure; only one input field order changes.
    for endpoint in ('unique32k', 'unique32k_best'):
        path = baseline.EVIDENCE / (endpoint + '_report.json'); r = qa.required(path)
        baseline.endpoint_contract(r, endpoint, inputs)
        if (r['code_sha256'] != baseline.info()['code_sha256']
                or r['input_report_sha256'] != qa.data.digest(baseline.FROZEN / 'report.json')):
            raise ValueError('same frozen unique32k baseline source required')
        for lane in evaluation.OUTPUTS:
            receipt = baseline.read_receipt(endpoint, lane, cases, inputs)
            if (receipt['output'] != r['outputs'][lane]
                    or qa.data.digest(baseline.receipt_path(endpoint, lane)) != r['receipt_sha256'][lane]):
                raise ValueError('complete unique32k baseline raw/receipt proof differs')
        reports[endpoint] = qa.data.digest(path)
        natural[endpoint] = list(evaluation.old.stream(baseline.LOCAL / endpoint, r['outputs']['natural']['manifest']))
    pairs = (('unique32k', 'question_first'), ('unique32k_best', 'question_first_best'),
             ('question_first', 'question_first_best'))
    comparisons = {a + '__' + b: evaluation.method.paired_natural(natural[a], natural[b]) for a, b in pairs}
    qa.write(EVIDENCE / 'paired_readback.json', dict(info(), status='RAW_RECOUNTED', errors=0,
        endpoints_sha256=reports, paired=comparisons,
        best_comparison_is_dev_selection_package=True, learning_seed_variance_measured=False))
    print('[ORDER_EVAL_READBACK] ' + json.dumps(comparisons, ensure_ascii=False), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('freeze', 'evaluate', 'readback'), required=True)
    parser.add_argument('--endpoint', choices=ENDPOINTS)
    parser.add_argument('--max-wall-sec', type=int, default=7200)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true'); group.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if not 60 <= args.max_wall_sec <= 21600: parser.error('bounded60..21600 wall seconds required')
    if args.check_only: print('[ORDER_EVAL_CHECK] ' + json.dumps(info())); return 0
    if args.mode == 'evaluate' and args.endpoint is None: parser.error('explicit endpoint required')
    try:
        previous.deadline()
        if args.mode == 'freeze': return prepare()
        if args.mode == 'readback': return readback()
        remaining = int((qa.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds())
        if remaining < 60: raise ValueError('09:00 final documentation reserve')
        return evaluate(args.endpoint, min(args.max_wall_sec, remaining))
    except KeyboardInterrupt: print('[ORDER_EVAL_INTERRUPTED] partial raw preserved'); return 130
    except Exception as exc:
        import traceback
        traceback.print_exc(); print('[ORDER_EVAL_ERROR] ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
