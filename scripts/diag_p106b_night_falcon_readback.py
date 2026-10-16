#!/usr/bin/env python3
"""Independent offline Falcon raw recount and fixed common-cohort comparison.

No model weights are loaded, no logits generated and no inference is repeated.
Absent complete Tiny endpoints remain NOT_COMPLETE rather than receiving zeros.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tinylm  # noqa: F401 -- process-local HF cache routing
import argparse
from collections import Counter
import json
import math
from scripts import diag_p106b_night_falcon as falcon
from scripts import p106b_night_falcon_readback as method
from scripts import diag_p106b_night_eval_recovery as prior
from scripts import diag_p106b_night_prompt_eval as prompt
from scripts import diag_p106b_night_diversity_eval as unique
from scripts import diag_p106b_night_order_eval as order

qa = falcon.qa
EVIDENCE = falcon.EVIDENCE / 'reference_reader'
PROVIDERS = ((prior, prior.ENDPOINTS + prior.FOUNDATION_ENDPOINTS),
             (prompt, prompt.ENDPOINTS), (unique, unique.ENDPOINTS), (order, order.ENDPOINTS))
CODE = ('scripts/diag_p106b_night_falcon_readback.py', 'scripts/test_p106b_night_falcon_readback_controller.py',
        'scripts/p106b_night_falcon_readback.py', 'scripts/test_p106b_night_falcon_readback.py',
        *falcon.CODE, *(path for provider, _ in PROVIDERS for path in provider.CODE))


def info():
    return dict(schema='P106B_NIGHT_FALCON_COMMON_COHORT_V1', tag=falcon.TAG,
        code_sha256={p: qa.data.digest(ROOT / p) for p in sorted(set(CODE))},
        frozen_reference_sha256=qa.data.digest(falcon.FROZEN / 'report.json'),
        declared_tiny_endpoints=[provider.__name__.rsplit('_', 1)[-1] + '.' + e for provider, endpoints in PROVIDERS for e in endpoints],
        primary='same eligible English MC source IDs; argmin summed NLL, character-normalized separately',
        new_model_logits=False, checkpoints_written=0, official_harness_equivalence=False,
        raw_gen_prompt_comparison='plain/ChatML also differ output instruction; not format-only causality',
        cross_model_ce_comparable=False, all_pretraining_contamination_audited=False)


def tokens():
    falcon.offline()
    from transformers import AutoTokenizer
    return falcon.Tokens(AutoTokenizer.from_pretrained(str(falcon.ASSET), local_files_only=True, trust_remote_code=False))


def prepare():
    import torch
    report, rows = falcon.read_inputs()
    if EVIDENCE.exists(): raise FileExistsError('old reference reader binding preserved')
    if torch.cuda.is_initialized(): raise ValueError('CPU reader binding initialized CUDA')
    # Selection is fixed before Falcon answers, not chosen by model correctness.
    gen = [r for r in rows if r['task'] == 'gsm8k_plain']
    selected = sorted(gen, key=lambda r: qa.data.sha([20261017, r['id']]))[:4]
    result = dict(info(), status='REFERENCE_READER_CPU_BOUND', rows=len(rows), cuda_initialized=False,
        source_cases_sha256=qa.data.sha(rows), review_gsm_ids=[r['id'] for r in selected])
    qa.write(EVIDENCE / 'inputs.json', result)
    print('[REFERENCE_READER_CPU] ' + json.dumps(dict(rows=len(rows), endpoints=len(result['declared_tiny_endpoints']))), flush=True)
    return 0


def reference_trial(name, proof, rows, tok):
    report = qa.required(falcon.EVIDENCE / name / 'report.json')
    status = 'FALCON_COST_COMPLETE' if name == 'cost8' else 'FALCON_REFERENCE_COMPLETE'
    if (report['status'] != status or report['code_sha256'] != falcon.info()['code_sha256']
            or report['input_sha256'] != qa.data.digest(falcon.FROZEN / 'report.json')
            or report['asset_sha256'] != proof['asset_sha256'] or report['runtime'] != proof['runtime']
            or report['initial_core_sha256'] != proof['initial_core_sha256'] or report['body_unchanged'] is not True
            or report['directory'] != str((falcon.LOCAL / name).relative_to(ROOT))):
        raise ValueError('complete same-code/reference/runtime/body/asset trial proof required')
    events = list(prior.old.stream(falcon.LOCAL / name, report['manifest']))
    originals = [r for r in rows if r['case_id'] in proof['pilot_case_ids']] if name == 'cost8' else rows
    checked = method.recount_reference(events, originals, tok)
    timing = {}
    for event in events:
        if event['skipped']: continue
        value = event['seconds']
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0: raise ValueError('positive actual event timing required')
        timing.setdefault(event['task'], []).append(value)
    if timing != report['timing'] or sum(map(sum, timing.values())) > report['whole_seconds']:
        raise ValueError('actual event timing/whole time does not match driver report')
    for task, count in checked['summary'].items():
        original = report['summary'][task]
        if any(original[key] != count[key] for key in ('n', 'correct', 'skipped')):
            raise ValueError('raw reference aggregate differs from stored summary')
        if task in falcon.TASKS[:3] and original['char_norm_correct'] != count['char_norm_correct']:
            raise ValueError('character-normalized MC raw recount differs')
    if set(report['summary']) != set(checked['summary']): raise ValueError('report task set incomplete')
    return report, events, checked


def common_comparison(reference, tiny):
    a = {r['id']:r for r in reference}
    b = {r['id']:r for r in tiny if r.get('task') in falcon.TASKS[:3] and not r.get('skipped')}
    if len(a) != len(reference) or len(b) != sum(r.get('task') in falcon.TASKS[:3] and not r.get('skipped') for r in tiny):
        raise ValueError('unique original MC IDs required')
    output = {}
    for task in falcon.TASKS[:3]:
        ids = sorted(i for i in a.keys() & b.keys() if a[i]['task'] == task)
        if not ids: raise ValueError('nonempty shared eligible English MC cohort required')
        left = []; right = []; left_norm = []; right_norm = []; golds = []
        for item_id in ids:
            x, y = a[item_id], b[item_id]
            if y['task'] != task or x['gold'] != y['gold']: raise ValueError('cross-model original task/gold changed')
            left.append(x['correct']); right.append(int(y['pred_harness'] == y['gold']))
            left_norm.append(x['char_norm_correct']); right_norm.append(int(y['pred_harness_norm'] == y['gold'])); golds.append(x['gold'])
        n = len(ids); b10 = sum(x and not y for x, y in zip(left, right)); b01 = sum(y and not x for x, y in zip(left, right))
        output[task] = dict(n_common=n, common_ids_sha256=qa.data.sha(ids),
            falcon_eligible=sum(r['task'] == task for r in reference), tiny_eligible=sum(r.get('task') == task and not r.get('skipped') for r in tiny),
            falcon_correct=sum(left), tiny_correct=sum(right), tiny_minus_falcon=(sum(right) - sum(left)) / n,
            falcon_char_norm_correct=sum(left_norm), tiny_char_norm_correct=sum(right_norm),
            discordant_falcon_only=b10, discordant_tiny_only=b01,
            paired_exact_p_unadjusted=falcon.suite.mcnemar_exact_p(b10, b01),
            falcon_wilson=falcon.suite.wilson(sum(left), n), tiny_wilson=falcon.suite.wilson(sum(right), n),
            sample_majority_baseline=max(Counter(golds).values()) / n)
    return output


def run():
    proof, rows = falcon.read_inputs(); binding = qa.required(EVIDENCE / 'inputs.json')
    if binding['status'] != 'REFERENCE_READER_CPU_BOUND' or binding['code_sha256'] != info()['code_sha256'] or binding['source_cases_sha256'] != qa.data.sha(rows):
        raise ValueError('same complete fixed reader/source binding required')
    tok = tokens(); cost, _, cost_checked = reference_trial('cost8', proof, rows, tok)
    final, events, checked = reference_trial('english896', proof, rows, tok)
    comparisons = {}; endpoint_reports = {}; unavailable = {}
    for provider, endpoints in PROVIDERS:
        for endpoint in endpoints:
            label = provider.__name__.rsplit('_', 1)[-1] + '.' + endpoint
            path = provider.EVIDENCE / (endpoint + '_report.json')
            if not path.exists():
                unavailable[label] = 'NOT_COMPLETE; no complete endpoint report, possible partial/pending raw preserved'
                continue
            report = qa.required(path); values = provider.read_inputs(); inputs, cases = values[-2:]
            provider.endpoint_contract(report, endpoint, inputs)
            if (report['code_sha256'] != provider.info()['code_sha256']
                    or report['input_report_sha256'] != qa.data.digest(provider.FROZEN / 'report.json')):
                raise ValueError('same frozen Tiny source/code endpoint required')
            receipt = provider.read_receipt(endpoint, 'public', cases) if provider is prior else provider.read_receipt(endpoint, 'public', cases, inputs)
            if receipt['output'] != report['outputs']['public'] or qa.data.digest(provider.receipt_path(endpoint, 'public')) != report['receipt_sha256']['public']:
                raise ValueError('complete Tiny public raw/receipt proof differs')
            raw = list(prior.old.stream(provider.LOCAL / endpoint, report['outputs']['public']['manifest']))
            comparisons[label] = common_comparison(checked['mc_outcomes'], raw); endpoint_reports[label] = qa.data.digest(path)
    result = dict(info(), status='REFERENCE_RAW_RECOUNTED', errors=0, model_loaded=False, new_gpu_inference=False,
        cost_report_sha256=qa.data.digest(falcon.EVIDENCE / 'cost8/report.json'),
        reference_report_sha256=qa.data.digest(falcon.EVIDENCE / 'english896/report.json'),
        raw_summary=checked['summary'], cost_cases=cost_checked['cases'], comparisons=comparisons,
        endpoint_reports_sha256=endpoint_reports, unavailable=unavailable,
        review_gsm_ids=binding['review_gsm_ids'], multiple_comparisons_adjusted=False,
        primary_mc_and_separate_gen=True, learning_seed_variance_measured=False)
    qa.write(EVIDENCE / 'readback.json', result)
    print('[REFERENCE_READBACK] ' + json.dumps(dict(summary=checked['summary'], comparisons=comparisons, unavailable=unavailable)), flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=('freeze', 'readback'), required=True); p.add_argument('--execute', action='store_true'); a = p.parse_args()
    if not a.execute: p.error('explicit CPU execution required')
    try: return prepare() if a.mode == 'freeze' else run()
    except Exception as exc:
        import traceback
        traceback.print_exc(); print('[REFERENCE_READBACK_ERROR] ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
