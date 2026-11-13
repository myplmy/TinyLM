#!/usr/bin/env python3
"""Fixed-value, realized subject response, and global-edit counterfactuals.

No target/weight optimization or new holdout claim. Registered edits roll back.
"""
import argparse
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import time
import traceback
import torch
from torch.nn.attention import sdpa_kernel, SDPBackend
from scripts import interactive_research_infer as manual
from scripts import p108_key_transport as core
from scripts import p108_value_edit as value
from scripts import diag_p108_value_edit as prior
from scripts import p108_wsp_attention as wsp
from scripts import p108_weight_space as metrics
from scripts import diag_p108_weight_space as common
from scripts.p106b_shards import ShardWriter, verify as verify_shards
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

ROOT = Path(__file__).resolve().parents[1]
TAG = 'p108_key_transport_v1_20261113'
BASE = ROOT / 'test_result/evidence' / TAG
SOURCE = ROOT / 'test_result/evidence/p108_nullspace_v1_20261113'
DEADLINE = datetime(2026, 11, 13, 8, tzinfo=timezone.utc)
SOURCES = ('scripts/diag_p108_key_transport.py', 'scripts/p108_key_transport.py',
           'scripts/test_p108_key_transport.py', 'scripts/p108_value_edit.py',
           'scripts/diag_p108_value_edit.py', 'scripts/p108_wsp_attention.py',
           'scripts/p108_weight_space.py', 'scripts/diag_p108_weight_space.py',
           'scripts/p106b_shards.py', 'scripts/diag_p107_hybrid_mntp.py')


class Budget:
    def __init__(self): self.start = time.monotonic()
    def check(self):
        if time.monotonic() - self.start > 1800 or (DEADLINE - datetime.now(timezone.utc)).total_seconds() < 900:
            raise TimeoutError('Nov13 transport authority/phase reserve')


def prepare():
    if BASE.exists(): raise FileExistsError('new transport namespace required')
    if datetime.now(timezone.utc) >= DEADLINE: raise TimeoutError('authority expired')
    report = common.read_json(SOURCE / 'actual/report.json')
    old = common.read_json(SOURCE / 'profile.json')
    if report['status'] != 'TECHNICAL_COMPLETE_QUALITY_SEPARATE' or not report['registered_core_unchanged']:
        raise ValueError('closed actual-write report required')
    manifest = common.read_json(SOURCE / 'actual/answers_shards_manifest.json')
    verify_shards(SOURCE / 'actual', manifest)
    selected = old['selected']
    references = {str(p.relative_to(ROOT)): manual.file_sha(p) for p in
                  [SOURCE/'profile.json', SOURCE/'data.json', SOURCE/'actual/report.json',
                   SOURCE/'actual/answers_shards_manifest.json']}
    for s in manifest['shards']:
        p = SOURCE/'actual'/s['path']; references[str(p.relative_to(ROOT))] = manual.file_sha(p)
    for chosen in selected:
        p = ROOT/chosen['packet']; references[str(p.relative_to(ROOT))] = manual.file_sha(p)
        if references[str(p.relative_to(ROOT))] != chosen['packet_sha256']: raise ValueError('value source changed')
        p = SOURCE/'actual'/(chosen['fact']+'_fit_plus_generic_factors.json')
        references[str(p.relative_to(ROOT))] = manual.file_sha(p)
    rows = [r for r in common.read_json(SOURCE/'data.json')['rows'] if r['fact'] in {c['fact'] for c in selected}]
    if len(rows) != 19 or len({r['id'] for r in rows}) != 19: raise ValueError('frozen transport row count changed')
    common.write_json(BASE/'data.json', dict(rows=rows, scope='REUSED_FIT_DEV_WORDING_NOT_INDEPENDENT_HOLDOUT'))
    (BASE/'initial_plan.txt').write_bytes((ROOT/prior.PLAN).read_bytes())
    sources = dict(manual.required_source_pins()); sources.update({s: manual.file_sha(ROOT/s) for s in SOURCES})
    common.write_json(BASE/'profile.json', dict(schema='P108_KEY_TRANSPORT_V1', tag=TAG, authority_directive=115,
        deadline=DEADLINE.isoformat(), model=prior.MODEL, sources=sources, references=references, selected=selected,
        origin=report['origin'], data_sha256=manual.file_sha(BASE/'data.json'),
        plan_sha256=manual.file_sha(BASE/'initial_plan.txt'), manifest_sha256=manual.canonical_sha(manual.verify_manifest()),
        max_new=64, reused_test_not_independent=True, new_optimizer_updates=0, checkpoint_writes=0))
    print('[PREPARED] '+TAG, flush=True)


def verify():
    p = common.read_json(BASE/'profile.json')
    if p['authority_directive'] != 115 or p['deadline'] != DEADLINE.isoformat(): raise ValueError('authority changed')
    for name, sha in dict(p['sources'], **p['references']).items():
        if manual.file_sha(ROOT/name) != sha: raise ValueError('source/reference changed: '+name)
    for name, key in (('data.json', 'data_sha256'), ('initial_plan.txt', 'plan_sha256')):
        if manual.file_sha(BASE/name) != p[key]: raise ValueError('frozen input changed')
    if manual.canonical_sha(manual.verify_manifest()) != p['manifest_sha256']: raise ValueError('model manifest changed')
    return p


def capture(active, module, row):
    item = prior.pack(active, row)
    ids = torch.tensor([item['prompt_ids']], device='cuda')
    saved = {}
    def hook(_module, args, output):
        if saved: raise RuntimeError('unexpected repeated output visit')
        pos = item['position']
        saved['key'] = args[0][0, pos].detach().cpu().clone()
        saved['output'] = output[0, pos].detach().cpu().clone()
    handle = module.register_forward_hook(hook)
    try:
        with torch.no_grad(), sdpa_kernel(SDPBackend.MATH): active['model'](ids, logits_last_only=True)
    finally: handle.remove()
    return saved


def run():
    p = verify(); budget = Budget(); budget.check(); out = BASE/'actual'
    if out.exists(): raise FileExistsError('actual namespace exists')
    writer = ShardWriter(out, 'answers', limit=3_000_000)
    report = dict(schema=p['schema'], tag=TAG, status='RUNNING', rows=[], new_optimizer_updates=0, checkpoint_writes=0)
    active = modules = module = delta = response = None; failure = None
    try:
        with manual.selected_runtime(manual.resolve_model(p['model'])) as active:
            torch.set_num_threads(4); torch.cuda.reset_peak_memory_stats()
            report['origin'] = {k: active[k] for k in ('name', 'checkpoint_sha256', 'core_sha256', 'tokenizer_sha256')}
            if report['origin'] != p['origin']: raise ValueError('completed source model changed')
            rows = common.read_json(BASE/'data.json')['rows']; modules = wsp.outputs(active['model'])
            old = {}
            sm = common.read_json(SOURCE/'actual/answers_shards_manifest.json')
            for s in sm['shards']:
                for line in (SOURCE/'actual'/s['path']).read_text().splitlines():
                    r = json.loads(line); old[(r['variant'], r['id'])] = r
            probe = rows[0]
            _, live = manual.emit(active, probe['question'], max_new=64)
            if live['generated_ids'] != old[('original', probe['id'])]['generation']['generated_ids']:
                raise RuntimeError('source baseline token parity failed')
            for chosen in p['selected']:
                fact, layer = chosen['fact'], chosen['layer']; module = modules[f'mlp:{layer}']
                packet = common.read_json(ROOT/chosen['packet'])
                if metrics.tensor_sha(module.weight) != packet['base_weight_sha256']: raise ValueError('matrix changed')
                v = torch.tensor(packet['left'], dtype=torch.float64)
                covariance = (v[:, None] @ torch.tensor(packet['right'], dtype=torch.float64)[None, :]).float()
                if metrics.tensor_sha(covariance) != packet['delta_sha256']: raise ValueError('rank-one packet changed')
                b = common.read_json(SOURCE/'actual'/(fact+'_fit_plus_generic_factors.json'))
                protected = (torch.tensor(b['left'], dtype=torch.float64) @ torch.tensor(b['right'], dtype=torch.float64)).float()
                if metrics.tensor_sha(protected) != b['delta_sha256']: raise ValueError('protected factors changed')
                for index, row in enumerate(r for r in rows if r['fact'] == fact):
                    budget.check(); original = capture(active, module, row)
                    baseline = old[('original', row['id'])]
                    writer.append(dict(baseline, reused_source=str(SOURCE.relative_to(ROOT))))
                    with prior.oracle(active, module, row, v.to(module.weight)):
                        fixed = prior.generated(active, row, writer, fact+':fixed_value_subject')
                    rr = dict(id=row['id'], fact=fact, split=row['split'], layer=layer,
                              original_exact=baseline['exact'], fixed_value_exact=fixed['exact'], arms=[])
                    for name, cpu_delta in (('source_covariance', covariance), ('fit_plus_generic', protected)):
                        budget.check(); previous = old[(fact+':'+name, row['id'])]
                        writer.append(dict(previous, reused_source=str(SOURCE.relative_to(ROOT))))
                        delta = cpu_delta.to(module.weight)
                        with wsp.edit(active['model'], active['route'], [(f'mlp:{layer}', delta)]) as receipt:
                            edited = capture(active, module, row)
                            if not torch.equal(edited['key'], original['key']): raise RuntimeError('upstream subject key changed')
                            if index == 0:
                                _, parity = manual.emit(active, row['question'], max_new=64)
                                if parity['generated_ids'] != previous['generation']['generated_ids']:
                                    raise RuntimeError('global edit token parity failed')
                        response = edited['output'] - original['output']
                        analytic = cpu_delta.double() @ original['key'].double()
                        with prior.oracle(active, module, row, response.to(module.weight)):
                            subject = prior.generated(active, row, writer, fact+':'+name+':subject_response')
                        rr['arms'].append(dict(name=name, geometry=core.response_geometry(analytic, v),
                            realized_geometry=core.response_geometry(response, v),
                            analytical_realized_max_abs=float((analytic-response.double()).abs().max()),
                            subject_exact=subject['exact'], full_exact=previous['exact'], receipt=receipt,
                            evidence=core.evidence_flags(baseline['exact'], fixed['exact'], subject['exact'], previous['exact'])))
                        delta = response = None
                    report['rows'].append(rr)
                    print('[TRANSPORT] '+json.dumps(dict(id=row['id'], fixed=fixed['exact'],
                        arms=[dict(name=a['name'], subject=a['subject_exact'], full=a['full_exact']) for a in rr['arms']])), flush=True)
                module = None
            _, parity = manual.emit(active, probe['question'], max_new=64)
            if parity['generated_ids'] != old[('original', probe['id'])]['generation']['generated_ids']:
                raise RuntimeError('final rollback parity failed')
            report['registered_core_unchanged'] = True; report['final_rollback_token_parity'] = True
            report['peak_allocated_bytes'] = torch.cuda.max_memory_allocated(); report['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
            modules = module = delta = response = None
        active = None; report['status'] = 'TECHNICAL_COMPLETE_QUALITY_SEPARATE'
    except BaseException as exc:
        traceback.print_exc(); report['status'] = 'ERROR'; report['error'] = repr(exc)
        failure = RuntimeError('Original transport error: '+repr(exc))
    finally:
        active = modules = module = delta = response = None; gc.collect()
        try: close_owned_cuda(torch, report)
        except BaseException as exc:
            report['cleanup_error'] = repr(exc); report['status'] = 'ERROR'
            if failure is None: failure = RuntimeError('Transport cleanup: '+repr(exc))
        manifest = writer.close(lineage=dict(profile_sha256=manual.file_sha(BASE/'profile.json')))
        verify_shards(out, manifest)
        report['seconds'] = time.monotonic()-budget.start; report['answer_rows'] = manifest['rows']
        common.write_json(out/'report.json', report)
    if failure is not None: raise failure
    print('[COMPLETE] '+json.dumps(dict(status=report['status'], seconds=report['seconds'], rows=len(report['rows']))), flush=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('phase', choices=['prepare', 'run']); args = parser.parse_args()
    (prepare if args.phase == 'prepare' else run)()


if __name__ == '__main__': main()
