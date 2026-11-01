#!/usr/bin/env python3
"""FINAL200 동결/기존 두 모델의 첫답 수집. 새 학습/설치/체크포인트 저장 없음."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_final_holdout as data
from scripts import interactive_research_infer as manual
from scripts import diag_p106b_resource_matrix as resource
from scripts.diag_p107_adaptive_training import VramWatch, ResourceHold, identity as shared_identity
from scripts.diag_p107_hybrid_mntp import close_owned_cuda, independent_final_checks
from scripts.p106b_shards import ShardWriter, verify as verify_shards

DEADLINE = datetime(2026, 11, 1, 2, 0, tzinfo=timezone.utc)
CACHE = ROOT / 'data_cache/p106b_final200_v1_20261101'
OUTPUT = ROOT / 'test_result/evidence/p106b_final200_v1_20261101'
OWN = ('scripts/p106b_final_holdout.py', 'scripts/diag_p106b_final_holdout.py',
       'scripts/test_p106b_final_holdout.py', 'scripts/p106b_shards.py')


def identity():
    value = dict(shared_identity()['files'])
    value.update({name: resource.digest(resource.safe(name)) for name in OWN})
    return dict(files=value, sha256=resource.sha(value))


def prepare():
    final, dev = data.build('final'), data.build('dev')
    contract = data.validate(final, dev)
    resource.need((DEADLINE - datetime.now(timezone.utc)).total_seconds() > 180, 'CPU closure deadline')
    resource.need(not CACHE.exists() and not OUTPUT.exists(), 'fresh evaluation namespaces required')
    source = identity()
    infer_manifest = manual.verify_manifest()
    tokenizer = manual.local_tokenizer(infer_manifest)
    from tinylm.chat.serialize import serialize
    lengths = [len(tokenizer.encode(serialize(dict(messages=manual.prompt_messages(row['prompt'])),
                'chatml', add_generation_prompt=True)).ids) for row in final + dev]
    resource.need(all(length + data.MAX_NEW <= 1024 for length in lengths), 'CPU prompt overflow; never truncate')
    models = {}
    for name in data.MODELS:
        spec = manual.resolve_model(name)
        record = manual.inspect_model(spec)
        resource.need(record['status'] == 'READY_METADATA_ONLY', 'closed full-trained model metadata required')
        report = record['report']
        checkpoint = resource.safe(spec.checkpoint)
        digest = resource.digest(checkpoint)
        resource.need(digest == report['checkpoint_sha256'], 'checkpoint differs from closed training')
        models[name] = dict(checkpoint=spec.checkpoint, checkpoint_sha256=digest,
                            checkpoint_bytes=checkpoint.stat().st_size, core_sha256=report['final_core_sha256'],
                            training_report_sha256=record['report_sha256'], completed_updates=spec.updates)
    manifest = dict(schema=data.SCHEMA, status='FINAL200_CPU_FROZEN', source=source,
        created_at=datetime.now(timezone.utc).isoformat(), authority_directive=104, deadline=DEADLINE.isoformat(),
        contract=contract, models=models, tokenizer_sha256=manual.TOKENIZER_SHA,
        prompt_token_contract=dict(checked_rows=len(lengths), minimum=min(lengths), maximum=max(lengths),
                                   max_with_generation=max(lengths) + data.MAX_NEW, limit=1024, overlong=0),
        precision='FP32_MATH', chat_format='EXISTING_MANUAL_CHATML', temperature=0., top_k=1,
        use_cache=True, mtp=False, max_new=data.MAX_NEW, training=0, checkpoint_writes=0,
        final_file='data_cache/p106b_final200_v1_20261101/final.json',
        dev_file='data_cache/p106b_final200_v1_20261101/dev.json',
        declared_use='HELD_OUT_FIRST_RESPONSE_ONLY_NEVER_TRAIN_OR_TEACHER',
        new_general_intelligence_gain_claim=False, source_language_quality='ROOT_AUTHORED_REVIEW_NOT_EXTERNAL_HUMAN_APPROVAL')
    CACHE.mkdir(parents=True)
    (OUTPUT / 'prepare').mkdir(parents=True)
    resource.write_new(CACHE / 'final.json', final)
    resource.write_new(CACHE / 'dev.json', dev)
    resource.write_new(CACHE / 'manifest.json', manifest)
    resource.write_new(OUTPUT / 'prepare/report.json', manifest)
    print(json.dumps(dict(status=manifest['status'], final_rows=200, dev_rows=20,
                          profile_sha256=resource.digest(CACHE / 'manifest.json'))), flush=True)
    return 0


def read_inputs(profile_path, profile_sha):
    manifest = resource.read_ref(dict(path=profile_path, sha256=profile_sha))
    resource.need(manifest['schema'] == data.SCHEMA and manifest['status'] == 'FINAL200_CPU_FROZEN',
                  'closed CPU profile required')
    resource.need(manifest['source'] == identity() and manifest['authority_directive'] == 104
                  and manifest['deadline'] == DEADLINE.isoformat(), 'source/authority/deadline differs')
    final = json.loads(resource.safe(manifest['final_file']).read_text())
    dev = json.loads(resource.safe(manifest['dev_file']).read_text())
    resource.need(data.validate(final, dev) == manifest['contract'], 'frozen FINAL/DEV contract differs')
    resource.need(manifest['max_new'] == data.MAX_NEW and set(manifest['models']) == set(data.MODELS),
                  'fixed response budget/models differ')
    return manifest, final


def collect(active, cases, writer, budget, report, *, emit=manual.emit):
    for case in cases:
        budget.check()
        started = time.perf_counter()
        answer, metadata = emit(active, case['prompt'], max_new=data.MAX_NEW)
        if not isinstance(answer, str) or type(metadata.get('generated_tokens')) is not int:
            raise ValueError('actual answer/token receipt required')
        row = dict(case, model=report['model'], answer=answer, metadata=metadata,
                   seconds=time.perf_counter() - started,
                   reference_match=data.reference_match(answer, case),
                   review_signals=data.review_signals(answer, metadata, case),
                   semantic_review='NOT_RUN', stable=None, responsive=None, correct=None)
        writer.append(row)
        report['completed_rows'] += 1
        report['last_completed_id'] = case['id']
        if report['completed_rows'] % 20 == 0:
            print(json.dumps(dict(completed=report['completed_rows'], model=report['model'])), flush=True)
        budget.check()


def evaluate(args):
    manifest, final = read_inputs(args.profile, args.profile_sha256)
    resource.need(args.arm in data.MODELS, 'fixed full-trained model required')
    resource.need(60 <= args.max_wall_sec <= 1800, 'bounded 30-minute maximum required')
    resource.need((DEADLINE - datetime.now(timezone.utc)).total_seconds() > args.max_wall_sec + 120,
                  'deadline reserve required')
    if args.check_only:
        print(json.dumps(dict(status='INPUTS_READY_GPU_NOT_RUN', model=args.arm, rows=len(final))))
        return 0
    import torch
    output = OUTPUT / args.arm
    resource.need(not output.exists(), 'fresh model answer output required')
    output.mkdir(parents=True)
    report = dict(schema=data.SCHEMA, status='STARTED', model=args.arm, source=identity(),
        profile_sha256=args.profile_sha256, final_input_sha256=manifest['contract']['final_sha256'],
        max_new=data.MAX_NEW, completed_rows=0, quality_review='NOT_RUN', training=0, checkpoint_writes=0,
        model_metadata=manifest['models'][args.arm], wall_budget_seconds=args.max_wall_sec,
        resource_limit_bytes=8_000_000_000, torch_allocator_cap_bytes=6 * 2**30)
    watch = writer = None
    code = 9
    try:
        report['gpu_admission'] = manual.require_idle_gpu()
        watch = VramWatch()
        watch.start()
        properties = torch.cuda.get_device_properties(0)
        torch.cuda.set_per_process_memory_fraction(6 * 2**30 / properties.total_memory)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        budget = resource.Budget(args.max_wall_sec, deadline=DEADLINE)
        with resource.wall(args.max_wall_sec):
            with manual.selected_runtime(manual.resolve_model(args.arm)) as active:
                report['actual_model'] = {k: active[k] for k in
                    ('name', 'checkpoint', 'checkpoint_sha256', 'core_sha256', 'tokenizer_sha256',
                     'quantization_route', 'precision', 'manifest_sha256')}
                resource.need(active['checkpoint_sha256'] == manifest['models'][args.arm]['checkpoint_sha256'],
                              'actual checkpoint differs from frozen profile')
                torch.cuda.reset_peak_memory_stats()
                writer = ShardWriter(output / 'answers', 'responses', limit=4_000_000)
                collect(active, final, writer, budget, report)
                report['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
                report['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
                resource.need(report['peak_reserved_bytes'] <= 6 * 2**30, 'allocator cap exceeded')
        resource.need(report['completed_rows'] == 200, 'complete FINAL200 required')
        report['status'], code = 'RESPONSES_COMPLETE_SEMANTIC_REVIEW_NOT_RUN', 0
    except (TimeoutError, ResourceHold) as exc:
        report.update(status='HOLD', error_type=type(exc).__name__, error=str(exc)[:1000])
        code = 8
    except Exception as exc:
        report.update(status='ERROR', error_type=type(exc).__name__, error=str(exc)[:1000])
        code = 9
    finally:
        def finish_writer():
            if writer is not None and report['completed_rows']:
                report['answers'] = writer.close(lineage=dict(model=args.arm,
                    final_input_sha256=manifest['contract']['final_sha256'], partial=code != 0,
                    purpose='EVALUATION_ONLY_NEVER_TRAIN_OR_TEACHER'))
                verify_shards(output / 'answers', report['answers'])
        def finish_watch():
            if watch is not None:
                report['vram_watch'] = watch.stop()
        def parent_unchanged():
            spec = manifest['models'][args.arm]
            report['parent_unchanged'] = resource.digest(resource.safe(spec['checkpoint'])) == spec['checkpoint_sha256']
            resource.need(report['parent_unchanged'], 'original checkpoint changed')
        def source_unchanged():
            report['source_unchanged'] = manifest['source'] == identity()
            resource.need(report['source_unchanged'], 'frozen code changed')
        gc.collect()
        good = independent_final_checks(report, [('watch', finish_watch), ('answers', finish_writer),
            ('cuda', lambda: close_owned_cuda(torch, report)), ('parent', parent_unchanged), ('source', source_unchanged)])
        if not good:
            report['status'], code = 'ERROR', 9
        elif report.get('vram_watch', {}).get('reason') is not None and code != 9:
            report['status'], code = 'HOLD', 8
        report['final_exit'] = code
        resource.write_new(output / 'report.json', report)
        print(json.dumps(dict(status=report['status'], completed_rows=report['completed_rows'], final_exit=code)), flush=True)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'evaluate'), required=True)
    parser.add_argument('--arm', choices=data.MODELS)
    parser.add_argument('--profile')
    parser.add_argument('--profile-sha256')
    parser.add_argument('--max-wall-sec', type=int, default=1800)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.execute == args.check_only:
        parser.error('실행/읽기전용 중 하나만 지정')
    if args.mode == 'prepare':
        if args.check_only:
            print(json.dumps(data.validate(data.build(), data.build('dev')), ensure_ascii=False))
            return 0
        return prepare()
    if not all((args.profile, args.profile_sha256, args.arm)):
        parser.error('평가는 고정 profile/SHA/모델 필요')
    return evaluate(args)


if __name__ == '__main__':
    raise SystemExit(main())
