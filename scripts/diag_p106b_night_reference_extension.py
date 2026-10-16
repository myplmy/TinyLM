#!/usr/bin/env python3
"""Extend the frozen reference readback without changing its17-endpoint scope.

Only existing raw answers/receipts/checkpoints are read; no new logits or models.
The two source-bound bare64 panels share MC768, not natural512, with students.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import json
from scripts import diag_p106b_night_falcon_readback as reference
from scripts import diag_p106b_night_order_probe as probe

panel, unique, qa, e = probe.panel, probe.unique, probe.qa, probe.e
TAG = 'p106b_night_reference_extension_v1_s1337'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
LABELS = ('parent64.base_parent', 'parent64.foundation_native',
          'unique_scope.unique32k', 'unique_scope.unique32k_best')
CODE = ('scripts/diag_p106b_night_reference_extension.py',
        'scripts/test_p106b_night_reference_extension.py', *reference.CODE, *probe.CODE)


def info():
    return dict(schema='P106B_NIGHT_REFERENCE_EXTENSION_V1', tag=TAG,
        code_sha256={p: qa.data.digest(ROOT / p) for p in sorted(set(CODE))},
        reference_reader_cpu_sha256=qa.data.digest(reference.EVIDENCE / 'inputs.json'),
        parent64_cpu_sha256=qa.data.digest(panel.FROZEN / 'report.json'),
        unique_scope_eval_cpu_sha256=qa.data.digest(unique.FROZEN / 'report.json'),
        labels=list(LABELS), mc_tasks=sorted(reference.method.MC_TASKS),
        old17_unavailable_are_not_completed=True, natural64_not_natural512=True,
        model_loaded=False, new_logits=False, new_generation=False,
        checkpoints_written=0, updates=0, official_harness_equivalence=False,
        all_pretraining_contamination_audited=False, learning_seeds=1,
        multiple_comparisons_adjusted=False, tokenizers_cross_model_ce_comparable=False)


def safe():
    for p in (EVIDENCE, *EVIDENCE.parents):
        if p.is_symlink(): raise ValueError('linked reference-extension namespace')
        if p == ROOT: break


def prepare():
    import torch
    safe(); reference.falcon.read_inputs(); panel.read_inputs(); unique.read_inputs()
    old = qa.required(reference.EVIDENCE / 'inputs.json')
    if old.get('code_sha256') != reference.info()['code_sha256']:
        raise ValueError('original reader CPU source must be unchanged')
    if EVIDENCE.exists(): raise FileExistsError('old extension evidence preserved')
    if torch.cuda.is_initialized(): raise ValueError('CPU-only extension binding required')
    qa.write(EVIDENCE / 'inputs.json', dict(info(), status='REFERENCE_EXTENSION_CPU_BOUND', cuda_initialized=False))
    print('[REFERENCE_EXTENSION_CPU] fixed_additional_labels=4 new_model_calls=0', flush=True)
    return 0


def read_inputs():
    safe(); r = qa.required(EVIDENCE / 'inputs.json')
    if (r.get('status') != 'REFERENCE_EXTENSION_CPU_BOUND'
            or any(r.get(k) != v for k, v in info().items())
            or r.get('cuda_initialized') is not False):
        raise ValueError('complete same-code/reference/source CPU binding required')
    return r


def bare_contract(report, endpoint, cp, identity, core, input_sha):
    if (endpoint not in panel.BARE or report.get('status') != 'BOUNDED_PARENT_EVAL_COMPLETE'
            or report.get('endpoint') != endpoint or report.get('code_sha256') != panel.info()['code_sha256']
            or report.get('body_unchanged') is not True or report.get('initial_core_sha256') != core
            or report.get('checkpoint') != str(cp.relative_to(ROOT)) or report.get('checkpoint_sha256') != identity
            or report.get('input_report_sha256') != input_sha
            or report.get('directory') != str((panel.LOCAL / endpoint).relative_to(ROOT))
            or set(report.get('outputs', {})) != set(panel.LANES)
            or set(report.get('receipt_sha256', {})) != set(panel.LANES)):
        raise ValueError('complete bare64 report/source/body/checkpoint path required')


def bare(endpoint):
    from tokenizers import Tokenizer
    frozen, inputs, cases = panel.read_inputs(); cp, identity, core = panel.expected_checkpoint(endpoint)
    bounded = qa.required(panel.EVIDENCE / 'bounded_parent_readback.json')
    if (bounded.get('status') != 'BOUNDED_PARENT_AND_TRAINED_RAW_RECOUNTED'
            or bounded.get('errors') != 0 or bounded.get('code_sha256') != panel.info()['code_sha256']
            or bounded.get('input_report_sha256') != qa.data.digest(panel.FROZEN / 'report.json')
            or bounded.get('selection') != frozen['selection']):
        raise ValueError('actual parent64 and full trained readback required')
    path = panel.EVIDENCE / (endpoint + '_report.json'); report = qa.required(path)
    if bounded['endpoint_reports_sha256'][endpoint] != qa.data.digest(path):
        raise ValueError('parent64 endpoint changed after raw readback')
    input_sha = qa.data.digest(panel.FROZEN / 'report.json')
    bare_contract(report, endpoint, cp, identity, core, input_sha)
    tok = Tokenizer.from_file(str(qa.data.TOKENIZER)); raw = None
    for lane in panel.LANES:
        path = panel.EVIDENCE / endpoint / (lane + '_receipt.json'); receipt = qa.required(path)
        if (qa.data.digest(path) != report['receipt_sha256'][lane]
                or receipt.get('status') != 'PANEL_LANE_COMPLETE' or receipt.get('endpoint') != endpoint
                or receipt.get('lane') != lane or receipt.get('checkpoint_sha256') != identity
                or receipt.get('code_sha256') != panel.info()['code_sha256']
                or receipt.get('input_report_sha256') != input_sha
                or receipt.get('body_proof') != e.body_proof(dict(kind='NEW_MODEL_INFERENCE'), core, core)
                or receipt.get('output') != report['outputs'][lane]):
            raise ValueError('complete same-source/body parent64 receipt required')
        output = receipt['output']
        if lane in ('native32', 'native256'): e.native_contract(lane, output, inputs)
        else:
            events = list(e.old.stream(panel.LOCAL / endpoint, output['manifest']))
            if panel.recount(lane, events, cases, tok) != output['counts']:
                raise ValueError('parent64 source/raw recount differs')
            if lane == 'public_mc': raw = events
    return report, raw


def grouped_checkpoints(reports):
    if set(reports) != set(LABELS): raise ValueError('exact four additional endpoint labels required')
    groups = {}
    for label in LABELS:
        r = reports[label]; identity = r.get('checkpoint_sha256')
        if not isinstance(identity, str) or len(identity) != 64: raise ValueError('checkpoint SHA required')
        groups.setdefault(identity, []).append(label)
    return groups


def run():
    read_inputs(); proof, rows = reference.falcon.read_inputs(); tok = reference.tokens()
    cost, _, _ = reference.reference_trial('cost8', proof, rows, tok)
    final, _, checked = reference.reference_trial('english896', proof, rows, tok)
    old = qa.required(reference.EVIDENCE / 'readback.json')
    if (old.get('status') != 'REFERENCE_RAW_RECOUNTED' or old.get('errors') != 0
            or old.get('code_sha256') != reference.info()['code_sha256']
            or old.get('cost_report_sha256') != qa.data.digest(reference.falcon.EVIDENCE / 'cost8/report.json')
            or old.get('reference_report_sha256') != qa.data.digest(reference.falcon.EVIDENCE / 'english896/report.json')
            or old.get('raw_summary') != checked['summary']):
        raise ValueError('original17 raw readback must precede extension; no unavailable-to-pass promotion')
    target = EVIDENCE / 'readback.json'
    if target.exists(): raise FileExistsError('old extension readback preserved')
    reports, comparisons, hashes = {}, {}, {}
    for endpoint in panel.BARE:
        label = 'parent64.' + endpoint; report, raw = bare(endpoint)
        reports[label] = report; comparisons[label] = reference.common_comparison(checked['mc_outcomes'], raw)
        hashes[label] = qa.data.digest(panel.EVIDENCE / (endpoint + '_report.json'))
    for endpoint in unique.ENDPOINTS:
        label = 'unique_scope.' + endpoint; probe.verified_primary(unique, endpoint)
        path = unique.EVIDENCE / (endpoint + '_report.json'); report = qa.required(path)
        raw = list(e.old.stream(unique.LOCAL / endpoint, report['outputs']['public']['manifest']))
        reports[label] = report; comparisons[label] = reference.common_comparison(checked['mc_outcomes'], raw)
        hashes[label] = qa.data.digest(path)
    result = dict(info(), status='REFERENCE_EXTENSION_RAW_RECOUNTED', errors=0,
        input_report_sha256=qa.data.digest(EVIDENCE / 'inputs.json'),
        original17_report_sha256=qa.data.digest(reference.EVIDENCE / 'readback.json'),
        original17_unavailable=old['unavailable'], additional_endpoint_report_sha256=hashes,
        checkpoint_alias_groups=grouped_checkpoints(reports), comparisons=comparisons)
    qa.write(target, result)
    print('[REFERENCE_EXTENSION] ' + json.dumps(dict(comparisons=comparisons,
        checkpoint_alias_groups=result['checkpoint_alias_groups'], old_unavailable=old['unavailable'])), flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('freeze', 'readback'), required=True); p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    if not a.execute: p.error('explicit CPU execution required')
    try: return prepare() if a.mode == 'freeze' else run()
    except Exception as exc:
        import traceback
        traceback.print_exc(); print('[REFERENCE_EXTENSION_ERROR] ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
