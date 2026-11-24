#!/usr/bin/env python3
"""P108B: complete only the ten missing layers of the frozen value library.

The completed Nov13 four-layer study is referenced without rerunning it. This
driver owns a fresh namespace, an explicit Nov16 authority, and auxiliary value
optimization only. It does not write model checkpoints or change old modules.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import subprocess
import time
import traceback

import tinylm  # Install the project's cache policy before any optional HF import.
import torch

from scripts import interactive_research_infer as manual
from scripts import diag_p108_weight_space as io
from scripts import diag_p108_value_edit as old
from scripts import diag_p108_query_value as query
from scripts import p108_query_value as positions
from scripts import p108_value_edit as value
from scripts import p108_wsp_attention as wsp
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'test_result/evidence/p108b_layer_transfer_v2_s1337'
SOURCE = ROOT / 'test_result/evidence/p108_query_value_v1_20261113'
DEADLINE = datetime(2026, 11, 16, 4, tzinfo=timezone.utc)  # 13:00 KST.
PLAN = 'test_plan/P108_직접가중치-방향수리와-학습개입.md'
SOURCES = (
    'scripts/diag_p108b_value_library.py', 'scripts/test_p108b_library.py',
    'scripts/diag_p108_value_edit.py', 'scripts/diag_p108_query_value.py',
    'scripts/p108_query_value.py', 'scripts/p108_value_edit.py',
    'scripts/p108_wsp_attention.py', 'scripts/p108_weight_space.py',
    'scripts/diag_p108_weight_space.py',
    'scripts/diag_p107_hybrid_mntp.py', 'scripts/diag_p106b_resource_matrix.py',
    'scripts/diag_p014e_packed_deploy.py',
)


def write_new(path, data):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('linked output is forbidden')
    raw = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2,
                      allow_nan=False) + '\n').encode('utf-8')
    if len(raw) >= 20_000_000:
        raise ValueError('one result must stay below20MB')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def library_grid(rows, layer_count=14):
    if type(layer_count) is not int or layer_count != 14:
        raise ValueError('this sealed TinyLM study requires all14 physical layers')
    facts = list(dict.fromkeys(r['fact'] for r in rows if r.get('fact')))
    if len(facts) != 12 or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('the original12 fact-language groups and unique IDs are required')
    for fact in facts:
        fits = [r for r in rows if r['fact'] == fact and r['split'] == 'fit']
        if len(fits) != 2 or len({r['expected'] for r in fits}) != 1:
            raise ValueError('two consistent original fit prompts per fact are required')
    return [(fact, layer) for fact in facts for layer in range(layer_count)]


def verify_candidate(candidate, fact, layer, dim=768):
    if candidate.get('fact') != fact or candidate.get('layer') != layer:
        raise ValueError('candidate identity differs')
    delta = candidate.get('value_delta')
    if not isinstance(delta, list) or len(delta) != dim:
        raise ValueError('candidate must contain the complete value vector')
    t = torch.tensor(delta, dtype=torch.float32)
    if not bool(torch.isfinite(t).all()):
        raise ValueError('nonfinite candidate')
    if candidate.get('optimization', {}).get('value_optimizer_updates') != 40:
        raise ValueError('the40-step auxiliary recipe must remain fixed')
    if candidate.get('oracle_fit', {}).get('items') != 2:
        raise ValueError('two oracle fit observations are required')
    return candidate


class Budget:
    def __init__(self, seconds=7200):
        self.started, self.seconds = time.monotonic(), seconds

    def check(self):
        if (time.monotonic() - self.started > self.seconds or
                (DEADLINE - datetime.now(timezone.utc)).total_seconds() < 900):
            raise TimeoutError('Nov16 authority or15-minute cleanup reserve reached')


def resources():
    manual.require_idle_gpu()
    reply = subprocess.run(['nvidia-smi', '--query-gpu=memory.free',
                            '--format=csv,noheader,nounits'], check=True,
                           capture_output=True, text=True, timeout=10)
    if not reply.stdout.strip().isdigit() or int(reply.stdout.strip()) < 4096:
        raise MemoryError('library requires4096MiB free at entry')
    return dict(free_mib=int(reply.stdout.strip()), continuous_or_oom_guarantee=False)


def cleanup(report):
    """Use the existing strict allocator/cuBLAS cleanup, keeping failure proof."""
    if not torch.cuda.is_initialized():
        report.update(cuda_allocated_after_bytes=0, cuda_reserved_after_bytes=0,
                      cuda_cleanup_scope='CUDA_NOT_INITIALIZED')
        return None
    try:
        close_owned_cuda(torch, report)
    except BaseException as exc:
        report['status_before_cleanup_error'] = report['status']
        report['status'] = 'ERROR_FINAL_CUDA_CLEANUP'
        report['cleanup_error'] = repr(exc)
        return exc
    finally:
        report['cuda_allocated_after_bytes'] = torch.cuda.memory_allocated()
        report['cuda_reserved_after_bytes'] = torch.cuda.memory_reserved()
    return None


def prepare():
    if BASE.exists() or BASE.is_symlink():
        raise FileExistsError('fresh P108B namespace required')
    Budget().check()
    profile = io.read_json(SOURCE / 'profile.json')
    data = io.read_json(SOURCE / 'data.json')
    grid = library_grid(data['rows'])
    references = {}
    reused = []
    for fact, layer in grid:
        if layer not in profile['layers']:
            continue
        path = SOURCE / 'actual' / f'{fact}_layer{layer}_fit.json'
        verify_candidate(io.read_json(path), fact, layer)
        references[str(path.relative_to(ROOT))] = manual.file_sha(path)
        reused.append([fact, layer])
    if len(reused) != 48 or profile['layers'] != [2, 5, 8, 11]:
        raise ValueError('exact completed48 candidates are required')
    for path in (SOURCE / 'profile.json', SOURCE / 'data.json', SOURCE / 'actual/report.json',
                 SOURCE / 'actual/answers_shards_manifest.json'):
        references[str(path.relative_to(ROOT))] = manual.file_sha(path)
    sources = dict(manual.required_source_pins())
    sources.update({name: manual.file_sha(ROOT / name) for name in SOURCES})
    parameters = {name: profile[name] for name in (
        'model', 'value_steps', 'value_lr', 'value_parameterization', 'kl_weight',
        'value_regularization', 'value_norm_cap', 'max_new')}
    manifest = manual.verify_manifest()
    origin = io.read_json(SOURCE / 'actual/report.json')['origin']
    write_new(BASE / 'data.json', data)
    write_new(BASE / 'library_profile.json', dict(
        parameters, schema='P108B_VALUE_LIBRARY_V1', authority_directive=140,
        deadline=DEADLINE.isoformat(), source_origin=origin, sources=sources,
        references=references, data_sha256=manual.file_sha(BASE / 'data.json'),
        manifest_sha256=manual.canonical_sha(manifest),
        reused_pairs=reused, all_pairs=[list(pair) for pair in grid],
        new_pairs=120, new_auxiliary_updates=4800, body_optimizer_updates=0,
        checkpoint_writes=0, position='LAST_PROMPT_TOKEN', max_phase_seconds=7200,
        plan_sha256=manual.file_sha(ROOT / PLAN), seed=1337,
        original_questions_already_exposed_not_independent=True))
    with (BASE / 'library_initial_plan.md').open('xb') as stream:
        stream.write((ROOT / PLAN).read_bytes())
    print('[PREPARED] P108B library:48 reused+120 new,14 layers', flush=True)


def verify():
    p = io.read_json(BASE / 'library_profile.json')
    if p['authority_directive'] != 140 or p['deadline'] != DEADLINE.isoformat():
        raise ValueError('authority differs')
    Budget().check()
    for name, expected in dict(p['sources'], **p['references']).items():
        if manual.file_sha(ROOT / name) != expected:
            raise ValueError('source/reference changed: ' + name)
    if manual.file_sha(BASE / 'data.json') != p['data_sha256']:
        raise ValueError('sealed data changed')
    if manual.file_sha(BASE / 'library_initial_plan.md') != p['plan_sha256']:
        raise ValueError('sealed initial plan changed')
    if manual.canonical_sha(manual.verify_manifest()) != p['manifest_sha256']:
        raise ValueError('original models changed')
    return p


def load_candidates():
    p = io.read_json(BASE / 'library_profile.json')
    output = []
    reused = {tuple(pair) for pair in p['reused_pairs']}
    for fact, layer in p['all_pairs']:
        path = ((SOURCE / 'actual') if (fact, layer) in reused else
                (BASE / 'library')) / f'{fact}_layer{layer}_fit.json'
        if path.is_file():
            output.append(verify_candidate(io.read_json(path), fact, layer))
    return output


def canary():
    """Actual14-layer zero-intervention/auxiliary-gradient contract, not quality."""
    p = verify()
    started = time.monotonic()
    report = dict(schema='P108B_FULL14_CANARY_V1', status='RUNNING', layers=[],
                  body_optimizer_updates=0, value_optimizer_updates=0, checkpoint_writes=0)
    active = module = delta = loss = gradient = capture = None
    failure = None
    try:
        report['entry_resources'] = resources()
        torch.set_num_threads(4)
        with manual.selected_runtime(manual.resolve_model(p['model'])) as active:
            modules = wsp.outputs(active['model'])
            row = next(r for r in io.read_json(BASE / 'data.json')['rows'] if r['split'] == 'fit')
            item = query.pack(active, row)
            with torch.no_grad():
                reference = float(old.target_nll(active, item))
            with value.freeze_parameters(active['model']):
                for layer in range(14):
                    Budget().check()
                    module = modules[f'mlp:{layer}']
                    value.refresh_autograd_views(active['model'], active['route'])
                    delta = torch.zeros(active['cfg'].dim, device='cuda', requires_grad=True)
                    capture = {}
                    with value.inject(module, item['position'], delta, capture=capture):
                        loss = old.target_nll(active, item)
                    gradient, = torch.autograd.grad(loss, delta)
                    if float(loss.detach()) != reference or not bool(torch.isfinite(gradient).all()):
                        raise RuntimeError('zero injection parity or auxiliary gradient failed')
                    if capture['key'].numel() != module.weight.shape[1]:
                        raise RuntimeError('key/output orientation differs')
                    report['layers'].append(dict(layer=layer, zero_nll=reference,
                        gradient_norm=float(gradient.norm()),
                        key_shape=list(capture['key'].shape), weight_shape=list(module.weight.shape)))
                    delta = loss = gradient = capture = None
            report['registered_core_unchanged'] = manual.state_fingerprint(active['model']) == active['core_sha256']
            if not report['registered_core_unchanged'] or len(report['layers']) != 14:
                raise RuntimeError('full14 or unchanged-core contract failed')
            report['status'] = 'FULL14_ZERO_PARITY_AND_VALUE_GRADIENT_VERIFIED'
    except BaseException as exc:
        failure = exc
        report.update(status='TECHNICAL_ERROR', error=repr(exc), traceback=traceback.format_exc())
    finally:
        active = module = modules = delta = loss = gradient = capture = item = None
        gc.collect()
        cleanup_error = cleanup(report)
        if failure is None:
            failure = cleanup_error
        report['wall_seconds'] = time.monotonic() - started
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        write_new(BASE / 'canary' / f'report_{stamp}.json', report)
        print('[CANARY_END] '+json.dumps({k:report.get(k) for k in
              ('status','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes')}), flush=True)
    if failure is not None:
        raise failure


def run(resume=False):
    p = verify()
    out = BASE / 'library'
    if out.exists() and not resume:
        raise FileExistsError('use explicit --resume for the same sealed partial library')
    if resume and not out.is_dir():
        raise ValueError('no partial library to resume')
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    report = dict(schema=p['schema'], attempt=stamp, status='RUNNING',
                  body_optimizer_updates=0, checkpoint_writes=0, new_completed=[],
                  reused_candidates=48, resumed=resume)
    active = modules = module = v = None
    started = time.monotonic()
    budget = Budget(p['max_phase_seconds'])
    optimize = positions.adapt_optimizer(old.optimize_value, query.pack, query.oracle)
    failure = None
    try:
        report['entry_resources'] = resources()
        torch.set_num_threads(4)
        torch.manual_seed(p['seed'])
        with manual.selected_runtime(manual.resolve_model(p['model'])) as active:
            torch.cuda.reset_peak_memory_stats()
            report['origin'] = {k: active[k] for k in p['source_origin']}
            if report['origin'] != p['source_origin']:
                raise ValueError('completed model identity changed')
            modules = wsp.outputs(active['model'])
            if sorted(int(k.split(':')[1]) for k in modules if k.startswith('mlp:')) != list(range(14)):
                raise ValueError('all14 distinct physical MLP outputs are required')
            data = io.read_json(BASE / 'data.json')
            existing = {(r['fact'], r['layer']) for r in load_candidates()}
            reused = {tuple(pair) for pair in p['reused_pairs']}
            with value.freeze_parameters(active['model']):
                for fact, layer in p['all_pairs']:
                    if (fact, layer) in existing:
                        continue
                    budget.check()
                    fits = [r for r in data['rows'] if r['fact'] == fact and r['split'] == 'fit']
                    subject = fits[0]['subject']
                    questions = ([f'{subject}에 관해 간단히 소개하세요.', f'{subject}에 관한 정보를 알려주세요.']
                                 if fits[0]['language'] == 'ko' else
                                 [f'Give a short introduction to {subject}.', f'Tell me something about {subject}.'])
                    anchors = [dict(fits[0], id=f'{fact}:anchor:{i}', question=q, expected=None)
                               for i, q in enumerate(questions)]
                    module = modules[f'mlp:{layer}']
                    value.refresh_autograd_views(active['model'], active['route'])
                    _, v, stats = optimize(active, module, fits, anchors, p, budget)
                    answers = []
                    for row in fits:
                        with query.oracle(active, module, row, v.to(module.weight)):
                            answer, generation = manual.emit(active, row['question'], max_new=64)
                        answers.append(dict(row, answer=answer, generation=generation,
                                            exact=old.metrics.exact_answer(answer, row['expected'])))
                    candidate = dict(fact=fact, layer=layer, optimization=stats,
                                     oracle_fit=dict(items=2, exact=sum(r['exact'] for r in answers)),
                                     value_delta=v.tolist(), oracle_fit_answers=answers,
                                     base_core_sha256=active['core_sha256'],
                                     data_sha256=p['data_sha256'],
                                     is_one_global_edited_model=False)
                    verify_candidate(candidate, fact, layer)
                    write_new(out / f'{fact}_layer{layer}_fit.json', candidate)
                    report['new_completed'].append(dict(fact=fact, layer=layer,
                        supervised_target_token_exposures=stats['supervised_target_token_exposures']))
                    print('[VALUE] '+json.dumps(dict(fact=fact, layer=layer,
                        fit=candidate['oracle_fit']['exact'], new=len(report['new_completed'])), ensure_ascii=False), flush=True)
                    v = None
            report['peak_allocated_mib'] = torch.cuda.max_memory_allocated() / 2**20
            report['peak_reserved_mib'] = torch.cuda.max_memory_reserved() / 2**20
            report['registered_core_unchanged'] = manual.state_fingerprint(active['model']) == active['core_sha256']
            if not report['registered_core_unchanged']:
                raise RuntimeError('library changed model weights')
            report['complete_candidates'] = len(load_candidates())
            report['status'] = ('TECHNICAL_COMPLETE_QUALITY_SEPARATE' if report['complete_candidates'] == 168
                                else 'INCOMPLETE_LIBRARY')
    except BaseException as exc:
        report['status'] = 'PAUSED_BUDGET' if isinstance(exc, TimeoutError) else 'TECHNICAL_ERROR'
        report['error'] = repr(exc)
        report['traceback'] = traceback.format_exc()
        report['inflight_exposures_exact_if_error'] = False
        failure = exc
    finally:
        active = modules = module = v = None
        gc.collect()
        cleanup_error = cleanup(report)
        if failure is None:
            failure = cleanup_error
        report['wall_seconds'] = time.monotonic() - started
        report['new_auxiliary_updates_completed'] = 40 * len(report['new_completed'])
        write_new(out / f'report_{stamp}.json', report)
        print('[LIBRARY_END] '+json.dumps({k: report.get(k) for k in
              ('status', 'complete_candidates', 'new_auxiliary_updates_completed', 'wall_seconds',
               'cuda_allocated_after_bytes', 'cuda_reserved_after_bytes')}, ensure_ascii=False), flush=True)
    if failure is not None:
        raise failure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'canary', 'run'])
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.resume and args.phase != 'run':
        parser.error('--resume is only valid for run')
    if args.phase == 'prepare':
        prepare()
    elif args.phase == 'canary':
        canary()
    else:
        run(args.resume)


if __name__ == '__main__':
    main()
