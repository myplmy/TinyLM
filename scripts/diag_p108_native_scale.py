#!/usr/bin/env python3
"""User109-only P108 fixed-scale native search and sealed confirmation.

Usage: python -m scripts.diag_p108_native_scale prepare|search|confirm TAG
No defaults, old profiles, test-guided reselection or original CP writes.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import re
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as repair
from scripts import p108_native_scale as native
from scripts import p108_native_practice as practice
from scripts import diag_p108_weight_space as previous
from scripts.p108_balanced_practice import StrictWriter, make_data as old_balanced
from scripts.p106b_shards import ShardWriter
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

MODEL = 'new595-broad-q'
DEADLINE = datetime(2026, 11, 5, 8, tzinfo=timezone.utc)
SCHEMA = 'P108_NATIVE_SCALE_V1'
PLAN = 'test_plan/P108_직접가중치-방향수리와-학습개입.md'
OLD_BASE = ROOT / 'test_result/evidence/p108w_v2_20261104' / MODEL
OLD_RUNTIME = ROOT / 'runs/isolated/p108w_v2_20261104' / MODEL
SOURCE_PATHS = (
    'scripts/p108_native_scale.py', 'scripts/p108_native_practice.py',
    'scripts/diag_p108_native_scale.py', 'scripts/test_p108_native_scale.py',
    'scripts/p108_weight_space.py', 'scripts/diag_p108_weight_space.py',
    'scripts/p108_balanced_practice.py', 'scripts/p106b_shards.py',
    'scripts/diag_p107_hybrid_mntp.py',
)


def paths(tag):
    if not re.fullmatch(r'p108_native_v[1-9][0-9]*_20261105', tag):
        raise ValueError('fresh explicit native P108 namespace required')
    return (manual.owned_path(f'test_result/evidence/{tag}/{MODEL}'),
            manual.owned_path(f'runs/isolated/{tag}/{MODEL}'))


def prepare(tag):
    base, runtime = paths(tag)
    if base.exists() or runtime.exists():
        raise FileExistsError('native namespace already exists')
    rows = practice.make_data()
    blocked = {r['question'] for r in previous.make_data() + old_balanced()
               if r.get('expected') is not None}
    overlap = [r['id'] for r in rows if r['expected'] is not None and r['question'] in blocked]
    if overlap:
        raise ValueError('new prompt repeats an old scored prompt: ' + str(overlap))
    manifest = manual.verify_manifest()
    old_report = previous.read_json(OLD_BASE / 'baseline/report.json')
    if manual.file_sha(OLD_RUNTIME / 'directions.pt') != old_report['directions_sha256']:
        raise ValueError('preserved direction tensor differs')
    files = {}
    for split in ('dev', 'test', 'open'):
        selected = [r for r in rows if r['split'] == split or (split == 'open' and r['split'].startswith('open_'))]
        target = base / (split + '.json')
        previous.write_json(target, dict(schema=SCHEMA, rows=selected))
        files[split] = dict(path=str(target.relative_to(ROOT)), sha256=manual.file_sha(target), rows=len(selected))
    snapshot = base / 'initial_plan.md'
    with snapshot.open('xb') as stream:
        stream.write((ROOT / PLAN).read_bytes())
    sources = dict(manual.required_source_pins())
    sources.update({p: manual.file_sha(ROOT / p) for p in SOURCE_PATHS})
    references = {str(p.relative_to(ROOT)): manual.file_sha(p) for p in
                  (OLD_BASE / 'baseline/report.json', OLD_BASE / 'profile.json', OLD_RUNTIME / 'directions.pt')}
    profile = dict(schema=SCHEMA, authority_directive=109, deadline=DEADLINE.isoformat(),
        tag=tag, model=MODEL, sources=sources, references=references, data=files,
        initial_plan_sha256=manual.file_sha(snapshot), manual_manifest_sha256=manual.canonical_sha(manifest),
        gains=[.5, 1., 2.], native_modes=['sign', 'codes'], seeds=[17, 29, 43],
        projection_coordinates='LATENT_MASTER_COMMON_DELTA_FOR_ALL_REALIZATIONS',
        layers=2, columns=32, max_new=96, max_phase_seconds=1800,
        precision='FP32_MATH', tf32=False, mtp=False, recurrence='R1', cache=True,
        optimizer_updates=0, training_tokens=0, old_exact_scored_prompt_overlap=0,
        practice_contract=practice.validate(rows),
        exclusions=['OTHER_SESSION_CLEANING', 'TinyDataset', 'NEW_300M', 'INSTALL_DOWNLOAD',
                    'ORIGINAL_CP_WRITES', 'OLD_TEST_FOR_SELECTION', 'GLOBAL_QUALITY_CLAIM'])
    previous.write_json(base / 'profile.json', profile)
    print('[PREPARED] ' + json.dumps(dict(tag=tag, profile_sha256=manual.file_sha(base / 'profile.json'),
        practice=profile['practice_contract'], old_scored_prompt_overlap=0)), flush=True)


def verify(base):
    profile = previous.read_json(base / 'profile.json')
    if (profile.get('schema') != SCHEMA or profile.get('authority_directive') != 109
            or profile.get('deadline') != DEADLINE.isoformat() or profile.get('model') != MODEL):
        raise ValueError('native profile authority/schema/model/deadline differs')
    for name, expected in dict(profile['sources'], **profile['references']).items():
        if manual.file_sha(manual.owned_path(name)) != expected:
            raise ValueError('frozen native source/reference changed: ' + name)
    for entry in profile['data'].values():
        if manual.file_sha(manual.owned_path(entry['path'])) != entry['sha256']:
            raise ValueError('native practice data changed')
    if manual.file_sha(base / 'initial_plan.md') != profile['initial_plan_sha256']:
        raise ValueError('native initial design snapshot changed')
    if manual.canonical_sha(manual.verify_manifest()) != profile['manual_manifest_sha256']:
        raise ValueError('native independent loader binding changed')
    return profile


class Budget:
    def __init__(self, profile):
        self.started = time.monotonic()
        self.maximum = profile['max_phase_seconds']

    def check(self):
        if datetime.now(timezone.utc).timestamp() + 600 >= DEADLINE.timestamp():
            raise TimeoutError('user109 deadline reserve reached')
        if time.monotonic() - self.started >= self.maximum:
            raise TimeoutError('native phase time budget reached')


def data_rows(profile, split):
    return previous.read_json(manual.owned_path(profile['data'][split]['path']))['rows']


def score_key(summary):
    return (-summary['exact'], -summary['protected_exact'], summary['empty'],
            summary['question_echoes'], summary['loop_indicators'], summary.get('actual_delta_norm', 0.))


def make_native(active, vectors, old_report, profile, gain, mode):
    proposals, specs = previous.make_edits(active, vectors, old_report['direction_report'],
                                         profile, gain, 'latent')
    modules = dict(repair.down_modules(active['model']))
    packets, metrics = [], []
    for (layer, delta), spec in zip(proposals, specs):
        module = modules[layer]
        group = module.cfg.micro_group or module.weight.shape[1]
        original = module._wq.detach()
        target = native.project(original, delta, group, allow_zero=mode == 'codes')
        data = native.packet(original, target, group)
        allowed = delta.ne(0)
        if bool(((target != original) & ~allowed).any()):
            raise RuntimeError('native target affects values outside projection support')
        packets.append((layer, data))
        metrics.append(dict(layer=layer, columns=spec['columns'], group=group,
            desired_delta_norm=float(delta.norm()), actual_delta_norm=float((target - original).norm()),
            desired_discretization_error=float((target - original - delta).norm()),
            changed=len(data['indices']), changed_outside_projection=0,
            original_sha256=data['original_sha256'], target_sha256=data['target_sha256'],
            scales_sha256=data['scales_sha256']))
    return packets, metrics


def identity(packets):
    return manual.canonical_sha(sorted((layer, p['target_sha256']) for layer, p in packets))


def summary_meta(summary, name, **extra):
    return dict(summary, name=name, **extra)


def eval_rows(active, rows, writer, name, budget, profile):
    active['torch'].cuda.reset_peak_memory_stats()
    return previous.evaluate(active, rows, StrictWriter(writer), name, budget, profile['max_new'])


def search_session(profile, base, out, writer, budget):
    variants, cache, selected = [], {}, []
    old_report = previous.read_json(OLD_BASE / 'baseline/report.json')
    with manual.selected_runtime(manual.resolve_model(MODEL)) as active:
        vectors = previous.load_vectors(OLD_RUNTIME, active['torch'], old_report)
        rows = data_rows(profile, 'dev')  # Test answers are never parsed by search.
        _, summary = eval_rows(active, rows, writer, 'original_dev', budget, profile)
        variants.append(summary_meta(summary, 'original_dev', evaluation_alias_of=None))
        unchanged = [(layer, dict(target_sha256=repair.tensor_sha(module._wq)))
                     for layer, module in repair.down_modules(active['model'])
                     if layer in old_report['direction_report']['selected_layers']]
        cache[identity(unchanged)] = variants[-1]
        common_delta, _ = previous.make_edits(active, vectors, old_report['direction_report'], profile, 1., 'latent')
        for realization in ('effective', 'latent'):
            name = 'continuous_common_g1_dev' if realization == 'effective' else 'requant_common_g1_dev'
            with repair.edit_weights(active['model'], active['route'], common_delta, realization) as receipts:
                _, summary = eval_rows(active, rows, writer, name, budget, profile)
                variants.append(summary_meta(summary, name, receipts=receipts, evaluation_alias_of=None))
        for mode in profile['native_modes']:
            for gain in profile['gains']:
                budget.check()
                packets, metrics = make_native(active, vectors, old_report, profile, gain, mode)
                name = f'native_{mode}_g{gain}_dev'
                fingerprint = identity(packets)
                with native.apply(active['model'], active['route'], packets, mode) as receipts:
                    alias = cache.get(fingerprint)
                    if alias is None:
                        _, summary = eval_rows(active, rows, writer, name, budget, profile)
                        alias_name = None
                    else:
                        summary = {key: alias[key] for key in
                            ('items', 'scored', 'exact', 'protected_items', 'protected_exact', 'loop_indicators',
                             'question_echoes', 'empty', 'max_new', 'generated_tokens')}
                        summary.update(seconds=0., allocated_peak_bytes=None, reserved_peak_bytes=None)
                        alias_name = alias['name']
                    entry = summary_meta(summary, name, gain=gain, mode=mode, receipts=receipts,
                        metrics=metrics, native_changed=sum(m['changed'] for m in metrics),
                        actual_delta_norm=sum(m['actual_delta_norm'] ** 2 for m in metrics) ** .5,
                        target_identity=fingerprint, evaluation_alias_of=alias_name)
                packet_path = out / (name + '_packet.json')
                previous.write_json(packet_path, dict(schema=SCHEMA, edits=packets, mode=mode, gain=gain))
                entry['packet'] = str(packet_path.relative_to(ROOT))
                entry['packet_sha256'] = manual.file_sha(packet_path)
                variants.append(entry)
                cache.setdefault(fingerprint, entry)
                if entry['native_changed']:
                    selected.append(entry)
                print('[NATIVE] ' + json.dumps({k: entry[k] for k in
                    ('name', 'exact', 'loop_indicators', 'native_changed', 'evaluation_alias_of')}), flush=True)
        winner = min(selected, key=score_key) if selected else None
        origin = {k: active[k] for k in ('name', 'core_sha256', 'checkpoint_sha256', 'tokenizer_sha256', 'quantization_route')}
    return dict(variants=variants, selected=winner, origin=origin,
                status='DEV_CANDIDATE_SEALED' if winner else 'GATE_NEGATIVE_NO_DISCRETE_EDIT',
                test_answers_parsed=False, optimizer_updates=0)


def confirm_session(profile, base, out, writer, budget):
    search = previous.read_json(base / 'search/report.json')
    winner = search.get('selected')
    if not winner:
        raise ValueError('no nonzero native candidate; confirmation would duplicate original')
    packet_path = manual.owned_path(winner['packet'])
    if manual.file_sha(packet_path) != winner['packet_sha256']:
        raise ValueError('selected native packet changed after dev')
    payload = previous.read_json(packet_path)
    packets = [(i, data) for i, data in payload['edits']]
    original_report = previous.read_json(OLD_BASE / 'baseline/report.json')
    variants = []
    with manual.selected_runtime(manual.resolve_model(MODEL)) as active:
        rows = data_rows(profile, 'test') + data_rows(profile, 'open')
        vectors = previous.load_vectors(OLD_RUNTIME, active['torch'], original_report)
        common_delta, _ = previous.make_edits(active, vectors, original_report['direction_report'], profile, 1., 'latent')
        _, original = eval_rows(active, rows, writer, 'original_test', budget, profile)
        variants.append(summary_meta(original, 'original_test'))
        with repair.edit_weights(active['model'], active['route'], common_delta, 'latent') as receipts:
            _, summary = eval_rows(active, rows, writer, 'requant_common_g1_test', budget, profile)
            variants.append(summary_meta(summary, 'requant_common_g1_test', receipts=receipts))
        with native.apply(active['model'], active['route'], packets, payload['mode']) as receipts:
            _, targeted = eval_rows(active, rows, writer, 'targeted_test', budget, profile)
            variants.append(summary_meta(targeted, 'targeted_test', receipts=receipts))
        modules = dict(repair.down_modules(active['model']))
        control_metadata = []
        for seed in profile['seeds']:
            controls = []
            for layer, data in packets:
                q = modules[layer]._wq.detach()
                target = native.unpack(q, data)
                shuffled = native.random_control(q, target, data['group'], seed + layer * 101)
                control = native.packet(q, shuffled, data['group'])
                controls.append((layer, control))
                control_metadata.append(dict(seed=seed, layer=layer,
                    same_transition_histogram=control['transition_sha256'] == data['transition_sha256'],
                    same_target=control['target_sha256'] == data['target_sha256'],
                    target_changed=len(data['indices']), control_changed=len(control['indices'])))
            name = f'native_random_{seed}_test'
            previous.write_json(out / (name + '_packet.json'), dict(schema=SCHEMA, edits=controls, mode=payload['mode']))
            with native.apply(active['model'], active['route'], controls, payload['mode']) as receipts:
                _, summary = eval_rows(active, rows, writer, name, budget, profile)
                variants.append(summary_meta(summary, name, receipts=receipts))
        origin = {k: active[k] for k in ('name', 'core_sha256', 'checkpoint_sha256', 'tokenizer_sha256', 'quantization_route')}
    quality = (targeted['exact'] > original['exact'] and targeted['protected_exact'] >= original['protected_exact']
               and targeted['empty'] <= original['empty'] and targeted['question_echoes'] <= original['question_echoes'])
    return dict(variants=variants, selected=winner, origin=origin, native_controls=control_metadata,
                status='REVIEW_REQUIRED_LIMITED_POSITIVE' if quality else 'GATE_NEGATIVE',
                general_intelligence_claim=False, optimizer_updates=0)


def execute(phase, tag):
    base, runtime = paths(tag)
    profile = verify(base)
    budget = Budget(profile); budget.check()
    out = base / phase
    if out.exists():
        raise FileExistsError('native phase already started; preserve partial evidence and use a fresh stage')
    out.mkdir(parents=True)
    writer = ShardWriter(out, 'answers', limit=4_000_000)
    report = dict(schema=SCHEMA, authority_directive=109, phase=phase,
                  profile_sha256=manual.file_sha(base / 'profile.json'),
                  training_tokens=0, optimizer_updates=0, original_checkpoint_writes=0)
    started = time.monotonic()
    failed = None
    try:
        result = (search_session if phase == 'search' else confirm_session)(profile, base, out, writer, budget)
        report.update(result)
    except BaseException as exc:
        failed = exc
        report.update(status='ERROR', error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
    finally:
        try:
            manifest = writer.close(lineage=dict(profile_sha256=report['profile_sha256'], phase=phase, model=MODEL))
            report['answers_manifest_sha256'] = manual.file_sha(out / 'answers_shards_manifest.json')
            report['answer_rows'] = manifest['rows']
        except BaseException as exc:
            report['writer_error'] = str(exc)
            if failed is None: failed = exc
        gc.collect()
        try:
            import torch
            close_owned_cuda(torch, report)
        except BaseException as exc:
            report['cleanup_error'] = str(exc)
            if failed is None: failed = exc
        try:
            verify(base)
            report['final_source_and_original_bindings_unchanged'] = True
        except BaseException as exc:
            report['final_integrity_error'] = str(exc)
            if failed is None: failed = exc
        if failed is not None: report['status'] = 'ERROR'
        report['wall_seconds'] = time.monotonic() - started
        previous.write_json(out / 'report.json', report)
    print('[FINAL] ' + json.dumps(dict(phase=phase, status=report.get('status'),
        wall_seconds=report['wall_seconds'], report=str((out / 'report.json').relative_to(ROOT)))), flush=True)
    if failed is not None: raise failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'search', 'confirm'))
    parser.add_argument('tag')
    args = parser.parse_args()
    if args.phase == 'prepare': prepare(args.tag)
    else: execute(args.phase, args.tag)


if __name__ == '__main__':
    main()
