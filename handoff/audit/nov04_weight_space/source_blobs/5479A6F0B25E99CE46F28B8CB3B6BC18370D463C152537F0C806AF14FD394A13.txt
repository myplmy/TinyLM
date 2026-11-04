#!/usr/bin/env python3
"""Frozen confirmation with actual-delta support/spectrum-matched controls.

Usage: python -m scripts.diag_p108_fixed_support prepare|confirm
This adds a stronger control before reading any test answers. Prior profiles
and all search results remain immutable. No training or original writes.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import time

from scripts import diag_p108_weight_space as common
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as repair
from scripts.p108_signed_control import row_sign_control, control_receipt
from scripts.p106b_shards import ShardWriter, verify as verify_shards

TAG, MODEL = 'p108w_v2_20261104', 'new595-broad-q'
EXTRA_SOURCES = ('scripts/p108_signed_control.py', 'scripts/test_p108_signed_control.py',
                 'scripts/diag_p108_fixed_support.py')


def prepare():
    base, _ = common.locations(TAG, MODEL)
    profile = common.verify_profile(base)
    winner = common.read_json(base / 'search' / 'report.json')['selected']
    path = base / 'fixed_support_profile.json'
    common.write_json(path, dict(schema='P108_FIXED_SUPPORT_V1', authority_directive=107,
        deadline=common.DEADLINE.isoformat(), base_profile_sha256=manual.file_sha(base / 'profile.json'),
        search_sha256=manual.file_sha(base / 'search' / 'report.json'),
        sources={name: manual.file_sha(common.ROOT / name) for name in EXTRA_SOURCES},
        primary=winner, seeds=profile['random_seeds'],
        rationale='LATENT_QUANTIZATION_CHANGED_COLUMNS_OUTSIDE_THE_REQUESTED_SPARSE_SUPPORT',
        controls='ROW_SIGNS_OF_ACTUAL_EFFECTIVE_DELTA_PRESERVE_SUPPORT_ABS_VALUES_AND_SINGULAR_VALUES',
        control_realization='CONTINUOUS_CACHE_NOT_TERNARY_DEPLOYMENT',
        test_selection=False, max_phase_seconds=2400, reverse_delta_diagnostic=True))
    print('[FROZEN] ' + manual.file_sha(path), flush=True)


def verify(base):
    common.verify_profile(base)
    profile = common.read_json(base / 'fixed_support_profile.json')
    if (profile['schema'] != 'P108_FIXED_SUPPORT_V1' or profile['authority_directive'] != 107
            or profile['deadline'] != common.DEADLINE.isoformat()
            or manual.file_sha(base / 'profile.json') != profile['base_profile_sha256']
            or manual.file_sha(base / 'search' / 'report.json') != profile['search_sha256']):
        raise ValueError('fixed confirmation binding differs')
    for name, sha in profile['sources'].items():
        if manual.file_sha(common.ROOT / name) != sha:
            raise ValueError('confirmation source changed')
    return profile


def run():
    base, runtime = common.locations(TAG, MODEL)
    extra = verify(base)
    profile = common.verify_profile(base)
    budget = common.Budget(dict(profile, max_phase_seconds=extra['max_phase_seconds']))
    budget.check()
    directory = base / 'confirm_fixed_support'
    if directory.exists():
        raise FileExistsError('confirmation namespace already exists')
    writer = ShardWriter(directory, 'answers', limit=3_000_000)
    final = dict(schema='P108_FIXED_SUPPORT_V1', authority_directive=107, variants=[],
                 fixed_profile_sha256=manual.file_sha(base / 'fixed_support_profile.json'),
                 primary=extra['primary'], training_tokens=0, optimizer_updates=0,
                 scientific_scope='FROZEN_PRACTICE_AND_MANUAL_DIALOGUE_NOT_OFFICIAL_BENCHMARK')
    baseline = common.read_json(base / 'baseline' / 'report.json')
    items = [r for r in common.read_json(base / 'data.json')['rows'] if r['split'] in ('test', 'open')]
    with manual.selected_runtime(manual.resolve_model(MODEL)) as active:
        torch = active['torch']
        torch.set_num_threads(4)
        torch.cuda.reset_peak_memory_stats()
        final['origin'] = {key: active[key] for key in ('name', 'checkpoint_sha256', 'core_sha256', 'tokenizer_sha256')}
        vectors = common.load_vectors(runtime, torch, baseline)
        modules = dict(repair.down_modules(active['model']))
        primary = extra['primary']
        _, summary = common.evaluate(active, items, writer, 'original_test', budget, profile['max_new'])
        final['variants'].append(dict(name='original_test', **summary))
        edits, specs = common.make_edits(active, vectors, baseline['direction_report'], profile,
                                        primary['gain'], primary['realization'])
        before = {index: modules[index]._wq.detach().clone() for index, _ in edits}
        with repair.edit_weights(active['model'], active['route'], edits, primary['realization']) as receipts:
            _, summary = common.evaluate(active, items, writer, 'targeted_test', budget, profile['max_new'])
            actual = [(index, modules[index]._wq.detach().clone() - before[index]) for index, _ in edits]
        final['variants'].append(dict(name='targeted_test', **summary, receipts=receipts, specs=specs))
        for seed in extra['seeds']:
            controls = [(index, row_sign_control(delta, seed + index)) for index, delta in actual]
            matching = [dict(layer=index, **control_receipt(delta, control))
                        for (index, delta), (_, control) in zip(actual, controls)]
            if not all(r['same_support'] and r['same_absolute_coefficients'] for r in matching):
                raise RuntimeError('strong random control matching failed')
            with repair.edit_weights(active['model'], active['route'], controls, 'effective') as receipts:
                realized = []
                for index, control in controls:
                    current = modules[index]._wq.detach() - before[index]
                    bound = 2 * torch.finfo(control.dtype).eps * float(before[index].abs().max() + control.abs().max())
                    error = float((current - control).abs().max())
                    if error > bound:
                        raise RuntimeError('control realization exceeds FP32 rounding bound')
                    realized.append(dict(layer=index, requested_realized_max_abs=error,
                        rounding_bound=bound, realized_norm=float(current.norm()),
                        requested_norm=float(control.norm()),
                        support_mismatch=int((current.ne(0) != control.ne(0)).sum())))
                _, summary = common.evaluate(active, items, writer, f'row_sign_{seed}_test', budget, profile['max_new'])
            final['variants'].append(dict(name=f'row_sign_{seed}_test', **summary, matching=matching,
                                         realized_matching=realized, receipts=receipts))
        if extra['reverse_delta_diagnostic']:
            with repair.edit_weights(active['model'], active['route'], [(i, -d) for i, d in actual], 'effective') as receipts:
                _, summary = common.evaluate(active, items, writer, 'reverse_actual_delta_test', budget, profile['max_new'])
            final['variants'].append(dict(name='reverse_actual_delta_test', **summary, receipts=receipts))
        final['vram'] = dict(torch_allocated_peak_bytes=torch.cuda.max_memory_allocated(),
                             torch_reserved_peak_bytes=torch.cuda.max_memory_reserved())
    verify(base)
    manifest = writer.close(lineage=dict(fixed_profile_sha256=final['fixed_profile_sha256'],
                                        checkpoint_sha256=final['origin']['checkpoint_sha256']))
    verify_shards(directory, manifest)
    final.update(original_core_unchanged=True, answers_manifest_sha256=manual.file_sha(directory / 'answers_shards_manifest.json'),
                 wall_seconds=time.monotonic() - budget.start, status='TECHNICAL_COMPLETE_QUALITY_SEPARATE')
    common.write_json(directory / 'report.json', final)
    print('[FINAL] ' + json.dumps(dict(status=final['status'], variants=[{k:r[k] for k in
        ('name','exact','scored','loop_indicators','empty','protected_exact')} for r in final['variants']],
        wall_seconds=final['wall_seconds']), ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'confirm'))
    args = parser.parse_args()
    try:
        prepare() if args.phase == 'prepare' else run()
    except TimeoutError as exc:
        print('[HOLD] ' + str(exc), flush=True)
        return 8
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
