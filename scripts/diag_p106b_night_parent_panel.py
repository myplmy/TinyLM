#!/usr/bin/env python3
"""Separate bounded bare-parent panel; never fills old six-model completion.

The four trained foundation endpoints retain their original full eight lanes.
This new namespace compares bare parents only on a source-selected 64-root panel
and the same 768 English MC items. Original partial answers are never resumed or
overwritten, and neither old foundation_readback nor its downstream gates change.
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
from scripts import diag_p106b_night_eval_recovery as e
from scripts import diag_p106b_night_foundation as foundation
from scripts import p106b_night_parent_panel as method
from scripts.p106b_shards import ShardWriter

qa = e.c
TAG = 'p106b_night_parent_panel_v1_s1337'
FROZEN = ROOT / 'HF/sft_ready' / TAG / 'evaluation'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
LOCAL = ROOT / 'test_result/evidence/local' / TAG / 'evaluate'
BARE = ('base_parent', 'foundation_native')
TRAINED = ('base_qa', 'base_qa_best', 'cpt_qa', 'cpt_qa_best')
LANES = ('natural', 'public_mc', 'native32', 'native256')
CODE = ('scripts/diag_p106b_night_parent_panel.py',
        'scripts/test_p106b_night_parent_panel_runtime.py',
        'scripts/p106b_night_parent_panel.py', 'scripts/test_p106b_night_parent_panel.py',
        *e.CODE, *foundation.CODE)


def info():
    return dict(schema='P106B_NIGHT_PARENT_PANEL_RUNTIME_V1', tag=TAG,
        code_sha256={p: qa.data.digest(ROOT / p) for p in sorted(set(CODE))},
        recovery_inputs_sha256=qa.data.digest(e.FROZEN / 'report.json'),
        old_source_sha256=e.info()['original_input_report_sha256'],
        bare_endpoints=list(BARE), trained_endpoints=list(TRAINED),
        source_only_selection_seed=20261017, per_language=32, natural_views=[0, 1, 2],
        precision='FP32_MATH', max_new_natural=128, temperature=0., top_k=1,
        precision_by_lane=dict(natural='FP32_MATH', public_mc='FP32_MATH',
            native32='CUDA_BF16_AUTOCAST_EXISTING_HELPER', native256='FP32_MATH'),
        use_cache=True, mtp=False, updates=0, checkpoints_written=0,
        old_six_endpoint_complete=False, old_downstream_prerequisites_unchanged=True,
        semantic_truth='source aliases/local MC metrics only; no world-truth certification')


def namespace():
    for target in (FROZEN, EVIDENCE, LOCAL):
        for parent in (target, *target.parents):
            if parent.is_symlink(): raise ValueError('linked panel namespace')
            if parent == ROOT: break


def selection(cases):
    pairs, proof = method.select_pairs(cases['natural'])
    mc = [r for r in cases['public'] if r['kind'] == 'mc' and r['task'] in ('piqa', 'hellaswag', 'arc_easy')]
    if len(mc) != 768 or any(r['expected_skip'] is not None for r in mc):
        raise ValueError('same complete eligible English768 MC source required')
    return dict(natural=pairs, public_mc=mc), proof


def prepare():
    import torch
    namespace(); _, inputs, cases = e.read_inputs()
    if FROZEN.exists() or EVIDENCE.exists(): raise FileExistsError('old panel source preserved')
    selected, proof = selection(cases)
    if torch.cuda.is_initialized(): raise ValueError('CPU panel freeze initialized CUDA')
    qa.write(FROZEN / 'cases.json', selected)
    result = dict(info(), status='PARENT_PANEL_CPU_FROZEN', selection=proof,
        actual_case_sets_sha256={k: qa.data.sha(v) for k, v in selected.items()},
        cases_file_sha256=qa.data.digest(FROZEN / 'cases.json'),
        native_val_sha256=inputs['native_val_sha256'], cuda_initialized=False,
        model_loaded=False, endpoint_inference=False)
    qa.write(FROZEN / 'report.json', result); qa.write(EVIDENCE / 'inputs.json', result)
    print('[PARENT_PANEL_CPU] ' + json.dumps(dict(status=result['status'], roots=len(selected['natural']), mc=len(selected['public_mc']))), flush=True)
    return 0


def read_inputs():
    namespace(); frozen = qa.required(FROZEN / 'report.json'); _, inputs, cases = e.read_inputs()
    selected, proof = selection(cases)
    if (frozen['status'] != 'PARENT_PANEL_CPU_FROZEN' or frozen['code_sha256'] != info()['code_sha256']
            or frozen['selection'] != proof or qa.required(EVIDENCE / 'inputs.json') != frozen
            or frozen['cases_file_sha256'] != qa.data.digest(FROZEN / 'cases.json')
            or qa.required(FROZEN / 'cases.json') != selected
            or frozen['actual_case_sets_sha256'] != {k: qa.data.sha(v) for k, v in selected.items()}
            or frozen['recovery_inputs_sha256'] != info()['recovery_inputs_sha256']):
        raise ValueError('same code/exact source-selected panel required')
    return frozen, inputs, selected


def expected_checkpoint(endpoint):
    if endpoint not in BARE: raise ValueError('only registered bare endpoints')
    cp, identity = e.checkpoint_spec(endpoint)
    r = qa.required(foundation.data.CORPUS / 'report.json') if endpoint == 'base_parent' else qa.required(foundation.data.EVIDENCE / 'native/report.json')
    core = r['original_core_sha256'] if endpoint == 'base_parent' else r['final_core_sha256']
    if qa.data.digest(cp) != identity: raise ValueError('selected bare checkpoint changed')
    return cp, identity, core


def recount(lane, events, cases, tok):
    if lane == 'natural': return e.natural_recount(events, cases['natural'])
    if lane == 'public_mc': return method.public_mc_recount(events, cases['public_mc'], tok)
    raise ValueError('explicit raw lane required')


def evaluate(endpoint, seconds):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    _, inputs, cases = read_inputs(); cp, identity, expected = expected_checkpoint(endpoint)
    target = EVIDENCE / (endpoint + '_report.json'); directory = LOCAL / endpoint
    if target.exists() or directory.exists(): raise FileExistsError('old complete/partial panel preserved')
    idle_before_gpu(); directory.mkdir(parents=True, exist_ok=False); began = time.perf_counter()
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    with wall_limit(seconds):
        model, cfg, device = load_model(arch='dense', ckpt_path=str(cp), device='cuda')
        initial = foundation.runtime.state_fingerprint(model)
        if initial != expected: raise ValueError('strict selected bare model body differs')
        tok = Tokenizer.from_file(str(qa.data.TOKENIZER)); outputs = {}; receipts = {}
        torch.cuda.reset_peak_memory_stats()
        with torch.no_grad():
            for lane in LANES:
                e.train.deadline()
                if lane in ('native32', 'native256'):
                    output = foundation.runtime.native_ce(model, qa.NATIVE) if lane == 'native32' else e.old.native256(model, inputs, tok)
                    model.eval(); model.freeze_quant(); e.native_contract(lane, output, inputs)
                else:
                    writer = ShardWriter(directory, lane); events = []
                    iterator = e.lane_events('natural', model, cfg, tok, device, cases) if lane == 'natural' else e.public_events(model, cfg, tok, device, cases['public_mc'])
                    original_mc = {(r['task'], r['item']['_iid']):r for r in cases['public_mc']}
                    for event in iterator:
                        if lane == 'public_mc':
                            original = original_mc[(event['task'], event['id'])]
                            event = dict(event, source_item=original['item'], index=original['index'])
                        writer.append(event); events.append(event)
                    output = dict(manifest=writer.close(lineage=info()), counts=recount(lane, events, cases, tok))
                final = foundation.runtime.state_fingerprint(model)
                body = e.body_proof(dict(kind='NEW_MODEL_INFERENCE'), initial, final)
                if qa.data.digest(cp) != identity: raise ValueError('read-only panel changed checkpoint')
                receipt = dict(info(), status='PANEL_LANE_COMPLETE', endpoint=endpoint, lane=lane,
                    checkpoint_sha256=identity, initial_core_sha256=initial, body_proof=body,
                    input_report_sha256=qa.data.digest(FROZEN / 'report.json'), output=output)
                path = EVIDENCE / endpoint / (lane + '_receipt.json'); qa.write(path, receipt)
                outputs[lane] = output; receipts[lane] = qa.data.digest(path)
                print('[PARENT_PANEL_LANE] ' + json.dumps(dict(endpoint=endpoint, lane=lane)), flush=True)
        result = dict(info(), status='BOUNDED_PARENT_EVAL_COMPLETE', endpoint=endpoint,
            directory=str(directory.relative_to(ROOT)), checkpoint=str(cp.relative_to(ROOT)),
            checkpoint_sha256=identity, initial_core_sha256=initial, body_unchanged=True,
            input_report_sha256=qa.data.digest(FROZEN / 'report.json'), outputs=outputs, receipt_sha256=receipts,
            whole_seconds=time.perf_counter() - began, peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
        qa.write(target, result)
        print('[PARENT_PANEL_COMPLETE] ' + json.dumps(dict(endpoint=endpoint, whole_seconds=result['whole_seconds'], natural=outputs['natural']['counts']['by_language'])), flush=True)
    del model; gc.collect(); torch.cuda.empty_cache()
    return 0


def trained_reports(inputs, cases):
    results, natural = {}, {}
    for endpoint in TRAINED:
        path = e.EVIDENCE / (endpoint + '_report.json'); r = qa.required(path)
        e.endpoint_contract(r, endpoint, inputs)
        if r['code_sha256'] != e.info()['code_sha256'] or r['input_report_sha256'] != qa.data.digest(e.FROZEN / 'report.json'):
            raise ValueError('same-code complete trained foundation endpoint required')
        for lane in e.OUTPUTS:
            receipt = e.read_receipt(endpoint, lane, cases)
            if receipt['output'] != r['outputs'][lane] or qa.data.digest(e.receipt_path(endpoint, lane)) != r['receipt_sha256'][lane]:
                raise ValueError('trained full raw/lane proof differs')
        natural[endpoint] = list(e.old.stream(e.LOCAL / endpoint, r['outputs']['natural']['manifest']))
        results[endpoint] = qa.data.digest(path)
    return results, natural


def readback(trained_only=False):
    from tokenizers import Tokenizer
    frozen, inputs, selected = read_inputs(); _, _, cases = e.read_inputs()
    hashes, natural = trained_reports(inputs, cases)
    full = {a + '__' + b:e.method.paired_natural(natural[a], natural[b])
        for a, b in (('base_qa', 'cpt_qa'), ('base_qa_best', 'cpt_qa_best'), ('base_qa', 'base_qa_best'), ('cpt_qa', 'cpt_qa_best'))}
    result = dict(info(), status='TRAINED_FOUNDATION_FOUR_RAW_RECOUNTED', errors=0,
        endpoint_reports_sha256=hashes, full512_comparisons=full,
        original_six_endpoint_readback='NOT_RUN: bare full512 interrupted/deferred',
        input_report_sha256=qa.data.digest(FROZEN / 'report.json'),
        scope='repeatedly observed development cohort; one training seed, not broad intelligence')
    if trained_only:
        qa.write(EVIDENCE / 'trained_foundation_readback.json', result)
    else:
        tok = Tokenizer.from_file(str(qa.data.TOKENIZER)); keep = {p['root'] for p in selected['natural']}; panels = {}
        for endpoint, events in natural.items():
            panels[endpoint] = [r for r in events if r['root'] in keep]
            e.natural_recount(panels[endpoint], selected['natural'])
        for endpoint in BARE:
            cp, identity, core = expected_checkpoint(endpoint)
            path = EVIDENCE / (endpoint + '_report.json'); report = qa.required(path)
            if (report.get('status') != 'BOUNDED_PARENT_EVAL_COMPLETE' or report.get('endpoint') != endpoint
                    or report.get('code_sha256') != info()['code_sha256'] or report.get('body_unchanged') is not True
                    or report.get('initial_core_sha256') != core or report.get('checkpoint_sha256') != identity
                    or report.get('input_report_sha256') != qa.data.digest(FROZEN / 'report.json')
                    or report.get('directory') != str((LOCAL / endpoint).relative_to(ROOT))
                    or set(report.get('outputs', {})) != set(LANES) or set(report.get('receipt_sha256', {})) != set(LANES)):
                raise ValueError('complete independent bounded panel/body/source proof required')
            for lane in LANES:
                receipt_path = EVIDENCE / endpoint / (lane + '_receipt.json'); receipt = qa.required(receipt_path)
                if (qa.data.digest(receipt_path) != report['receipt_sha256'][lane]
                        or receipt.get('status') != 'PANEL_LANE_COMPLETE' or receipt.get('endpoint') != endpoint
                        or receipt.get('lane') != lane or receipt.get('checkpoint_sha256') != identity
                        or receipt.get('code_sha256') != info()['code_sha256']
                        or receipt.get('input_report_sha256') != qa.data.digest(FROZEN / 'report.json')
                        or receipt.get('body_proof') != e.body_proof(dict(kind='NEW_MODEL_INFERENCE'), core, core)
                        or receipt['output'] != report['outputs'][lane]):
                    raise ValueError('exact complete panel lane receipt required')
                output = receipt['output']
                if lane in ('native32', 'native256'): e.native_contract(lane, output, inputs)
                else:
                    events = list(e.old.stream(LOCAL / endpoint, output['manifest']))
                    if recount(lane, events, selected, tok) != output['counts']: raise ValueError('panel raw/source recount differs')
                    if lane == 'natural': panels[endpoint] = events
            hashes[endpoint] = qa.data.digest(path)
        result.update(status='BOUNDED_PARENT_AND_TRAINED_RAW_RECOUNTED', selection=frozen['selection'],
            panel64_comparisons={a + '__' + b:e.method.paired_natural(panels[a], panels[b])
                for a, b in (('base_parent', 'foundation_native'), ('base_parent', 'base_qa'), ('foundation_native', 'cpt_qa'), ('base_qa', 'cpt_qa'))})
        qa.write(EVIDENCE / 'bounded_parent_readback.json', result)
    print('[PARENT_PANEL_READBACK] ' + json.dumps(dict(status=result['status'], endpoints=list(hashes), errors=0)), flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('freeze', 'evaluate', 'trained-readback', 'panel-readback'), required=True)
    p.add_argument('--endpoint', choices=BARE); p.add_argument('--max-wall-sec', type=int, default=1800)
    g = p.add_mutually_exclusive_group(required=True); g.add_argument('--execute', action='store_true'); g.add_argument('--check-only', action='store_true')
    a = p.parse_args()
    if a.check_only: print(json.dumps(info())); return 0
    try:
        e.train.deadline()
        if a.mode == 'freeze': return prepare()
        if a.mode.endswith('readback'): return readback(a.mode == 'trained-readback')
        if a.endpoint is None: p.error('explicit bare endpoint required')
        remaining = int((qa.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds())
        if remaining < 60: raise RuntimeError('09:00 GPU stop reserve')
        return evaluate(a.endpoint, min(a.max_wall_sec, remaining))
    except KeyboardInterrupt:
        print('[PARENT_PANEL_INTERRUPTED] partial preserved'); return 130
    except Exception as exc:
        import traceback
        traceback.print_exc(); print('[PARENT_PANEL_ERROR] ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
