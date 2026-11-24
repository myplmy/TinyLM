#!/usr/bin/env python3
"""Replay already-frozen ROME/MEMIT adaptations and benchmark official tasks.

No new fit, optimizer, checkpoint export or historical authority modification.
Admit each arm only after exact delta/realized weight/68-generation replay.
Official prompts, tasks, likelihood implementation and audits are reused.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import sysconfig
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_orpo_official as suite
from scripts import diag_p106b_official_core6 as official
from scripts import p106b_official_lm_adapter as adapter
from scripts import p108_frozen_edit as replay
from scripts.p106b_shards import ShardWriter, verify

TAG = 'p108_frozen_edit_official_v2_20261113'
BASE = ROOT/'test_result/evidence/p108_distributed_residual_v1_20261113'
OUTPUT = ROOT/'test_result/evidence'/TAG
ARMS = ('original', 'single11', 'distributed8_11')
FROZEN = {
    'profile.json': '0011D8BDEDD2CC78F6DCD50C21E8EFC755FEBA4EB01F20F57F3C25457D47AD53',
    'data.json': 'A2C3986BE10D15B49A28A319FF060DE160EEB4EE8BB628A2C5E1D3C565A0867D',
    'actual/report.json': '603C791E45A7878C55DEEE87A3C94D6B05818559E403BAB6424BE66D4312F12E',
    'actual/packet_manifest.json': '261495541945F573C45E36485DCEC62B886FFBE5EDAB4B0F74ECDB0D77141B11',
    'actual/answers_shards_manifest.json': 'DE1FDF118C6382C1D2EFCC419B94DD39CE172CF766AAAE024EE35BC86C88057F',
}
CODE = tuple(sorted(set((*suite.CODE, 'scripts/p108_frozen_edit.py',
    'scripts/test_p108_frozen_edit.py', 'scripts/diag_p108_frozen_edit_official.py',
    'scripts/p108_wsp_attention.py', 'scripts/p108_weight_space.py',
    'scripts/interactive_research_infer.py'))))


def identity():
    files = {n: official.digest(ROOT/n) for n in CODE}
    return dict(files=files, sha256=hashlib.sha256(adapter.canonical(files)).hexdigest().upper())


def prepare_tasks():
    # This must precede lm_eval/HF imports. Preserve the existing fail-closed
    # project policy instead of changing its guard or environment rules.
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    configure_hf_cache()
    return suite.load_tasks()


def bundle():
    source = {n: replay.read_pinned(BASE/n, sha) for n, sha in FROZEN.items()}
    result = source['actual/report.json']
    manifest = source['actual/packet_manifest.json']
    if (not result['registered_core_unchanged'] or not result['original_checkpoint_unchanged']
            or result['checkpoint_writes'] != 0 or result['base_optimizer_updates'] != 0
            or not manifest['frozen_before_dev_public_protect_generations']):
        raise ValueError('closed unchanged original and frozen packets required')
    verify(BASE/'actual', source['actual/answers_shards_manifest.json'])
    import torch
    torch.set_num_threads(4)
    packets = {}
    for ref in manifest['packets']:
        if ref['path'] in ('single11_layer11_packet.json', 'distributed8_11_layer8_packet.json',
                           'distributed8_11_layer11_packet.json'):
            packet = replay.read_pinned(BASE/'actual'/ref['path'], ref['sha256'])
            packets[ref['path']] = dict(packet=packet, delta=replay.decode(packet), file=ref)
    if len(packets) != 3:
        raise ValueError('all three fixed edit packets required')
    expected = {}
    for shard in source['actual/answers_shards_manifest.json']['shards']:
        for line in (BASE/'actual'/shard['path']).read_text().splitlines():
            row = json.loads(line)
            if row['variant'] in ARMS:
                key = (row['variant'], row['id'])
                if key in expected:
                    raise ValueError('duplicate frozen answer identity')
                expected[key] = row
    rows = source['data.json']['rows']
    if len(rows) != 68 or len(expected) != 204:
        raise ValueError('exact original/single/distributed68 generation proof required')
    return source, packets, expected


@contextmanager
def model_runtime(arm, frozen, packets, expected, target):
    import torch
    from scripts import interactive_research_infer as manual
    from scripts import p108_wsp_attention as wsp
    from scripts.p108_weight_space import tensor_sha
    proof = dict(arm=arm, packet_replay=True, refit=False, optimizer_updates=0, checkpoint_writes=0)
    lm = modules = edits = None
    with manual.selected_runtime(manual.resolve_model('new595-broad-f')) as active:
        origin = {k: active[k] for k in ('name', 'checkpoint_sha256', 'core_sha256', 'tokenizer_sha256')}
        if origin != frozen['actual/report.json']['origin']:
            raise ValueError('frozen original runtime identity differs')
        proof['origin'] = origin
        proof['checkpoint'] = str(active['checkpoint'])
        modules = wsp.outputs(active['model'])
        selected = sorted(n for n in packets if n.startswith(arm+'_')) if arm != 'original' else []
        after = next((a['after_weight_sha256'] for a in frozen['actual/report.json']['arms'] if a['name']==arm), {})
        edits, validations = [], []
        for name in selected:
            item = packets[name]; packet, delta = item['packet'], item['delta']
            module = modules['mlp:'+str(packet['layer'])]
            validations.append(replay.validate_base_and_after(packet, delta, module.weight, after[str(packet['layer'])]))
            edits.append(('mlp:'+str(packet['layer']), delta.to(module.weight)))
        proof['matrix_reconstruction'] = validations
        edit_scope = wsp.edit(active['model'], active['route'], edits) if edits else nullcontext([])
        try:
            with edit_scope as receipts:
                proof['edit_receipts'] = receipts
                for item in validations:
                    if tensor_sha(modules['mlp:'+str(item['layer'])].weight) != item['after_weight_sha256']:
                        raise ValueError('installed GPU edited weight differs')
                proof['edited_core_sha256'] = manual.state_fingerprint(active['model'])
                writer = ShardWriter(target, 'generation_replay')
                for row in frozen['data.json']['rows']:
                    saved = expected[(arm, row['id'])]
                    answer, generation = manual.emit(active, row['question'], max_new=64)
                    if (answer != saved['answer']
                            or generation['generated_ids'] != saved['generation']['generated_ids']
                            or generation['prompt_sha256'] != saved['generation']['prompt_sha256']
                            or generation['finish_reason'] != saved['generation']['finish_reason']):
                        raise ValueError('frozen generation replay differs: '+row['id'])
                    writer.append(dict(id=row['id'], question=row['question'], answer=answer,
                                       generation=generation, exact_saved_tokens=True))
                proof['generation_replay_manifest'] = writer.close(lineage=dict(arm=arm, saved_tag=BASE.name))
                verify(target, proof['generation_replay_manifest'])
                proof['generation_replay_count'] = 68
                print(json.dumps(dict(event='FROZEN_EDIT_AND_GENERATION_EXACT', arm=arm, generations=68)), flush=True)
                lm = adapter.create_adapter(active, runtime_root=Path(sysconfig.get_paths()['purelib']), batch_size=8)
                yield lm, proof
                if manual.state_fingerprint(active['model']) != proof['edited_core_sha256']:
                    raise ValueError('benchmark changed edited model weights')
        finally:
            if lm is not None:
                lm.close()
            proof['final_original_core_sha256'] = manual.state_fingerprint(active['model'])
            proof['original_core_restored'] = proof['final_original_core_sha256'] == origin['core_sha256']
            if not proof['original_core_restored']:
                raise ValueError('original core rollback differs')
            edits = modules = lm = None
    gc.collect(); torch.cuda.empty_cache()


def evaluate(arm, pin, cap):
    signature = identity()
    if signature['sha256'] != pin:
        raise ValueError('explicit current source pin required')
    frozen, packets, expected = bundle()
    target = OUTPUT/arm
    if target.exists():
        raise FileExistsError('complete or failed prior output is preserved')
    target.mkdir(parents=True)
    report = dict(tag=TAG, arm=arm, status='STARTED', source_identity=signature,
        frozen_files=FROZEN, frozen_model_origin=frozen['actual/report.json']['origin'],
        policy=official.policy(), training=False, optimizer_updates=0, checkpoint_writes=0,
        new_edit_fit=False, framework_commit=adapter.COMMIT,
        metrics_scope='FROZEN_WEIGHT_EDIT_DIAGNOSTIC_NOT_NEW_TRAINING_OR_ADOPTION',
        started_at=datetime.now(timezone.utc).isoformat(), official_results={},
        independent_audits={}, actual_counts={}, sample_manifests={})
    started = time.monotonic()
    try:
        os.environ.update(official.OFFLINE, HF_EVALUATE_OFFLINE='1')
        tasks, specs, provenance = prepare_tasks()
        report.update(task_specs=specs, framework_provenance=provenance)
        import torch
        from torch.nn.attention import sdpa_kernel, SDPBackend
        from lm_eval.evaluator import simple_evaluate
        from lm_eval.tasks import TaskManager
        from scripts.diag_p106b_native_format_official import canary
        from scripts.p106b_gate_runtime import wall_limit
        torch.set_num_threads(4); torch.manual_seed(1337)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        with wall_limit(cap), sdpa_kernel(SDPBackend.MATH), torch.no_grad():
            with model_runtime(arm, frozen, packets, expected, target) as (lm, proof):
                report['model_proof'] = proof
                torch.cuda.reset_peak_memory_stats()
                report['canary'] = canary(lm, torch)
                manager = TaskManager()
                lengths_writer = ShardWriter(target, 'token_lengths')
                with official.length_observer(lm, lengths_writer) as lengths:
                    for taskname, task in tasks.items():
                        tick = time.monotonic()
                        result = simple_evaluate(model=lm, tasks=[task], num_fewshot=0,
                            task_manager=manager, batch_size=8, device='cuda', use_cache=None,
                            cache_requests=False, limit=None,
                            bootstrap_iters=0 if taskname.startswith('kobest_') else 100000,
                            log_samples=True, apply_chat_template=False, fewshot_as_multiturn=False,
                            random_seed=1337, numpy_random_seed=1337, torch_random_seed=1337,
                            fewshot_random_seed=1337)
                        rows = result.pop('samples')[taskname]
                        audit = suite.audit_task(task, rows, len(task.eval_docs))
                        for metric in ('acc', 'acc_norm'):
                            point = result['results'][taskname].get(metric+',none')
                            count = audit['correct_norm' if metric=='acc_norm' else 'correct']
                            if point is not None and not math.isclose(point, count/len(rows), abs_tol=1e-12):
                                raise ValueError('independent accuracy differs')
                        if taskname.startswith('kobest_'):
                            for metric, aggregate in task.aggregation().items():
                                if metric=='f1' and not math.isclose(aggregate([r[metric] for r in rows]),
                                        result['results'][taskname]['f1,none'], abs_tol=1e-12):
                                    raise ValueError('official macroF1 recount differs')
                        writer = ShardWriter(target, taskname+'_samples')
                        for row in rows: writer.append(official.plain(row))
                        manifest = writer.close(lineage=dict(tag=TAG, arm=arm, task=taskname,
                                                             framework_commit=adapter.COMMIT))
                        verify(target, manifest)
                        report['sample_manifests'][taskname] = manifest
                        report['independent_audits'][taskname] = audit
                        report['official_results'][taskname] = official.plain(result)
                        report['actual_counts'][taskname] = len(rows)
                        print(json.dumps(dict(event='OFFICIAL_TASK_CLOSED', arm=arm, task=taskname,
                            rows=len(rows), seconds=time.monotonic()-tick)), flush=True)
                    report['token_lengths_summary'] = lengths
                report['lengths_manifest'] = lengths_writer.close(lineage=dict(tag=TAG, arm=arm))
                verify(target, report['lengths_manifest'])
                report['peak_allocated_mib'] = torch.cuda.max_memory_allocated()/1024**2
                report['peak_reserved_mib'] = torch.cuda.max_memory_reserved()/1024**2
            report.update(status='OFFICIAL_ELEVEN_TASKS_COMPLETE', returncode=0)
    except BaseException as exc:
        report.update(status='OFFICIAL_EVALUATION_ERROR', returncode=9,
                      error_type=type(exc).__name__, error=str(exc)[:1600])
        raise
    finally:
        report.update(wall_seconds=time.monotonic()-started, sources_unchanged=identity()==signature,
            frozen_files_unchanged=all(replay.digest(BASE/n)==sha for n,sha in FROZEN.items()),
            ended_at=datetime.now(timezone.utc).isoformat())
        suite.write(target/'report.json', report)
    return dict(status=report['status'], arm=arm, actual_counts=report['actual_counts'], seconds=report['wall_seconds'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check-only', action='store_true')
    group.add_argument('--execute', action='store_true')
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--source-sha256')
    parser.add_argument('--max-wall-sec', type=int, default=1800)
    args = parser.parse_args()
    if args.check_only:
        frozen, packets, expected = bundle()
        result = dict(status='FROZEN_PACKET_CPU_RECONSTRUCTION_EXACT_NO_MODEL',
            source_identity=identity(), arms=ARMS, generation_rows=len(expected),
            packets={n: dict(file=x['file'], layer=x['packet']['layer'],
                delta_sha256=x['packet']['delta_sha256'], shape=list(x['delta'].shape)) for n,x in packets.items()},
            origin=frozen['actual/report.json']['origin'], model_load=False, gpu=False,
            optimizer_updates=0, checkpoint_writes=0)
    else:
        if args.arm is None or not 300 <= args.max_wall_sec <= 3600:
            parser.error('explicit arm and300~3600second cap required')
        result = evaluate(args.arm, args.source_sha256, args.max_wall_sec)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
