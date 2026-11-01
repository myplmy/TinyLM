#!/usr/bin/env python3
"""MMLU 공식0/5shot의 CPU 계약과 기존 모델 평가. 학습·설치·다운로드 없음."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
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
from scripts import p106b_official_mmlu as data
from scripts import diag_p106b_resource_matrix as resource
from scripts.diag_p106b_final_holdout import identity as base_identity
from scripts.diag_p107_adaptive_training import VramWatch, ResourceHold
from scripts.diag_p107_hybrid_mntp import close_owned_cuda, independent_final_checks
from scripts.p106b_shards import ShardWriter, verify as verify_shards

DEADLINE = datetime(2026, 11, 1, 2, 0, tzinfo=timezone.utc)
OWN = ('scripts/p106b_official_mmlu.py', 'scripts/diag_p106b_official_mmlu.py',
       'scripts/test_p106b_official_mmlu.py', 'scripts/p106b_official_lm_adapter.py',
       'scripts/prepare_p106b_official_eval.py', 'scripts/diag_p106b_official_core6.py')
OFFLINE = dict(HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1', TRANSFORMERS_OFFLINE='1', USE_HUB_KERNELS='0')


def identity():
    files = dict(base_identity()['files'])
    files.update({name:data.digest(ROOT / name) for name in OWN})
    return dict(files=files, sha256=resource.sha(files))


def policy(shots):
    if shots not in data.SHOTS:
        raise ValueError('고정0/5shot만 허용')
    return dict(num_fewshot=shots, chat_template=False, max_length=1024, batch_size=4,
        precision='FP32_MATH_TF32_OFF', seed=1337, use_cache=False,
        request_cache=False, logits_cache=False, bootstrap_iters=100000,
        target='COMPLETE_SUM_LOGLIKELIHOOD_A_B_C_D',
        context_truncation='EXISTING_HFLM_LEFT_TRUNCATION_REPORTED_NOT_SILENT',
        group_aggregation='OFFICIAL_SIZE_WEIGHTED_ACC', training=0, checkpoint_writes=0)


def prepare_contract():
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    from scripts.p106b_official_lm_adapter import prepare_harness, LikelihoodCore, _adapter_type, plan_tokens
    from scripts import interactive_research_infer as manual
    configure_hf_cache()
    template, framework = prepare_harness(runtime_root=Path(sysconfig.get_paths()['purelib']))
    manifest = data.verify_assets()
    tokenizer = manual.local_tokenizer(manual.verify_manifest())
    vocab = tokenizer.get_vocab_size()
    def forbidden_forward(_):
        raise RuntimeError('CPU 계약에서 모델 forward 금지')
    core = LikelihoodCore(vocab_size=vocab, pad_id=tokenizer.token_to_id('<pad>'),
                          score_batch=forbidden_forward, batch_size=4)
    lm = _adapter_type(template)(core=core, tokenizer=tokenizer, prefix_id=tokenizer.token_to_id('<bos>'),
        eos_id=tokenizer.token_to_id('<eos>'), provenance=dict(tokenizer_sha256=manual.TOKENIZER_SHA, device='cpu'))
    folder = data.OUTPUT / 'contract_v2'
    if folder.exists():
        raise FileExistsError('계약 원형 보존; 새 namespace 필요')
    folder.mkdir()
    writer = ShardWriter(folder / 'lengths', 'requests', limit=4_000_000)
    totals = {}
    for shots in data.SHOTS:
        tasks, _, _ = data.load_tasks(shots)
        total = dict(rows=0, requests=0, input_positions=0, truncated_requests=0,
                     removed_context_tokens=0, maximum_original_input=0, maximum_actual_input=0)
        for name, task in tasks.items():
            for index, doc in enumerate(task.eval_docs):
                items = []
                for request in data.requests(task, doc, shots, index):
                    context, continuation = lm._encode_pair(*request.args)
                    plan = plan_tokens(context, continuation, vocab, 1024)
                    items.append(dict(context_tokens=len(context), continuation_tokens=len(continuation),
                        input_tokens=len(plan.input_ids), removed_context_tokens=plan.truncated_context_tokens))
                total['rows'] += 1
                total['requests'] += 4
                for row in items:
                    total['input_positions'] += row['input_tokens']
                    total['truncated_requests'] += row['removed_context_tokens'] > 0
                    total['removed_context_tokens'] += row['removed_context_tokens']
                    total['maximum_original_input'] = max(total['maximum_original_input'], row['context_tokens'] + row['continuation_tokens'] - 1)
                    total['maximum_actual_input'] = max(total['maximum_actual_input'], row['input_tokens'])
                writer.append(dict(shots=shots, task=name, doc_id=index, choices=items))
            print(json.dumps(dict(event='CPU_LENGTH_TASK', shots=shots, task=name, rows=len(task.eval_docs))), flush=True)
        resource.need(total['rows'] == data.COUNT and total['requests'] == 4 * data.COUNT, '공식 전체 요청 분모')
        totals[str(shots)] = total
    lengths = writer.close(lineage=dict(purpose='EVALUATION_ONLY', models=list(data.MODELS), shots=[0, 5]))
    lm.close()
    models = {}
    for name in data.MODELS:
        spec = manual.resolve_model(name)
        record = manual.inspect_model(spec)
        resource.need(record['status'] == 'READY_METADATA_ONLY', '학습완료 모델 원형 필요')
        checkpoint = ROOT / spec.checkpoint
        resource.need(data.digest(checkpoint) == record['report']['checkpoint_sha256'], '원CP변질')
        models[name] = dict(checkpoint=spec.checkpoint, checkpoint_sha256=data.digest(checkpoint),
            core_sha256=record['report']['final_core_sha256'], completed_updates=spec.updates,
            training_report_sha256=record['report_sha256'])
    profile = dict(schema='P106B_OFFICIAL_MMLU_PROFILE_V1', status='OFFICIAL_REQUEST_CONTRACT_COMPLETE',
        created_at=datetime.now(timezone.utc).isoformat(), source=identity(), authority_directive=104,
        deadline=DEADLINE.isoformat(), assets_sha256=data.digest(data.CACHE / 'assets.json'),
        models=models, tokenizer_sha256=manual.TOKENIZER_SHA, framework=framework, shots=totals,
        policies={str(n):policy(n) for n in data.SHOTS}, cpu_lengths=lengths,
        training=0, checkpoint_writes=0, model_loads=0, gpu_runs=0,
        test_train_or_teacher_reuse='PROHIBITED', original_data_unchanged=True)
    resource.write_new(data.CACHE / 'profile.json', profile)
    resource.write_new(folder / 'report.json', profile)
    print(json.dumps(dict(status=profile['status'], profile_sha256=data.digest(data.CACHE / 'profile.json'), shots=totals)))
    return 0


def read_profile(path, expected):
    resource.need(path == str((data.CACHE / 'profile.json').relative_to(ROOT)), '고정 평가 profile 경로 필요')
    resource.need(data.digest(ROOT / path) == expected, '고정 profile SHA 불일치')
    profile = json.loads((ROOT / path).read_text())
    resource.need(profile['source'] == identity() and profile['authority_directive'] == 104
                  and profile['deadline'] == DEADLINE.isoformat(), 'source/허가/마감 불일치')
    resource.need(profile['assets_sha256'] == data.digest(data.CACHE / 'assets.json'), '자료 manifest 변형')
    data.verify_assets()
    return profile


def admit_full(cost, profile_sha, model, shots, input_positions, now):
    if (cost.get('status') != 'LIMITED_COST_DIAGNOSTIC' or cost.get('final_exit') != 0
            or cost.get('model') != model or cost.get('shots') != shots or cost.get('profile_sha256') != profile_sha
            or cost.get('source') != identity() or cost.get('policy') != policy(shots)
            or cost.get('actual_rows') != 114 or len(cost.get('audits', {})) != 57):
        raise ValueError('동일 조건57과제×2 비용 영수증 필요')
    seconds, positions = cost.get('scorer_seconds'), cost.get('scored_input_positions')
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or v <= 0
           for v in (seconds, positions, input_positions)):
        raise ValueError('실제 양수 backend 시간/입력량 필요')
    forecast = seconds * input_positions / positions * 1.8 + 300
    if forecast > 5400 or now + forecast + 120 >= DEADLINE.timestamp():
        raise ResourceHold('전체 예상이90분 또는11시예비120초를 초과')
    return dict(forecast_seconds=forecast, forecast_scope='TOKEN_LINEAR_ESTIMATE_WITH_1_8_FACTOR_NOT_GUARANTEE',
                hard_cap_seconds=min(5400, int(DEADLINE.timestamp() - now - 120)))


@contextmanager
def timed_backend(lm, torch, report):
    original = lm._loglikelihood_tokens
    def run(requests, **kwargs):
        torch.cuda.synchronize()
        started = time.monotonic()
        value = original(requests, **kwargs)
        torch.cuda.synchronize()
        report['scorer_seconds'] += time.monotonic() - started
        return value
    lm._loglikelihood_tokens = run
    try:
        yield
    finally:
        lm._loglikelihood_tokens = original


def evaluate(args):
    profile = read_profile(args.profile, args.profile_sha256)
    resource.need(args.model in data.MODELS and args.shots in data.SHOTS, '사전 고정 모델/shot 필요')
    cost_path = data.OUTPUT / args.model / ('shot' + str(args.shots)) / 'cost/report.json'
    admission = (admit_full(json.loads(cost_path.read_text()), args.profile_sha256, args.model, args.shots,
        profile['shots'][str(args.shots)]['input_positions'], time.time()) if args.mode == 'full'
        else dict(hard_cap_seconds=600))
    resource.need(time.time() + admission['hard_cap_seconds'] + 120 < DEADLINE.timestamp() + 1, '마감 예비 필요')
    if args.check_only:
        print(json.dumps(dict(status='READY_GPU_NOT_RUN', admission=admission, model=args.model, shots=args.shots)))
        return 0
    folder = data.OUTPUT / args.model / ('shot' + str(args.shots)) / args.mode
    resource.need(not folder.exists(), '완료/부분 원형을 덮지 않는다')
    folder.mkdir(parents=True)
    report = dict(schema='P106B_OFFICIAL_MMLU_RUN_V1', status='STARTED', model=args.model, shots=args.shots,
        profile_sha256=args.profile_sha256, source=identity(), policy=policy(args.shots), admission=admission,
        model_metadata=profile['models'][args.model], actual_rows=0, audits={}, official_results={}, samples={},
        scorer_seconds=0., training=0, checkpoint_writes=0, resource_limit_bytes=8_000_000_000,
        torch_allocator_cap_bytes=6 * 2**30, started_at=datetime.now(timezone.utc).isoformat(),
        contamination='ALL_PRETRAINING_SEMANTIC_OVERLAP_NOT_AUDITED')
    watch = lengths = None
    code, started = 9, time.monotonic()
    try:
        for key, value in OFFLINE.items():
            os.environ[key] = value
        from scripts.prepare_p106b_official_eval import configure_hf_cache
        configure_hf_cache()
        tasks, assets, framework = data.load_tasks(args.shots)
        from scripts.p106b_official_lm_adapter import research_adapter
        from scripts import diag_p106b_official_core6 as old
        from scripts import interactive_research_infer as manual
        from lm_eval.evaluator import simple_evaluate
        from lm_eval.tasks import TaskManager
        from lm_eval.api.metrics import aggregate_subtask_metrics
        import torch
        from torch.nn.attention import sdpa_kernel, SDPBackend
        torch.set_num_threads(4)
        torch.manual_seed(1337)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        report['gpu_admission'] = manual.require_idle_gpu()
        watch = VramWatch()
        watch.start()
        torch.cuda.set_per_process_memory_fraction(6 * 2**30 / torch.cuda.get_device_properties(0).total_memory)
        manager = TaskManager()
        lengths = ShardWriter(folder / 'lengths', 'requests', limit=4_000_000)
        with resource.wall(admission['hard_cap_seconds']), sdpa_kernel(SDPBackend.MATH), torch.no_grad():
            with research_adapter(args.model, runtime_root=Path(sysconfig.get_paths()['purelib']), batch_size=4) as lm:
                resource.need(lm.provenance['checkpoint_sha256'] == profile['models'][args.model]['checkpoint_sha256'], '실제 원CP가 다름')
                report['model_proof'] = lm.provenance
                report['numerical_canary'] = old.numerical_canary(lm, torch)
                record_start = len(lm.core.records)
                torch.cuda.reset_peak_memory_stats()
                with old.length_observer(lm, lengths) as length_summary, timed_backend(lm, torch, report):
                    result = simple_evaluate(model=lm, tasks=list(tasks.values()), num_fewshot=args.shots,
                        task_manager=manager, batch_size=4, device='cuda', use_cache=None, cache_requests=False,
                        limit=2 if args.mode == 'cost' else None, bootstrap_iters=100000, log_samples=True,
                        apply_chat_template=False, fewshot_as_multiturn=False, random_seed=1337,
                        numpy_random_seed=1337, torch_random_seed=1337, fewshot_random_seed=1337)
                report['length_summary'] = length_summary
                records = lm.core.records[record_start:]
                report['scored_input_positions'] = sum(row['input_tokens'] for row in records)
                resource.need(set(result['samples']) == set(tasks), '57공식 과제 전체 필요')
                values, sizes = [], []
                for name, task in tasks.items():
                    rows = old.plain(result['samples'][name])
                    expected = 2 if args.mode == 'cost' else len(task.eval_docs)
                    audit = data.independent_scores(rows, expected)
                    actual = result['results'][name]['acc,none']
                    resource.need(math.isclose(actual, audit['accuracy'], abs_tol=1e-12), '공식/독립 aggregate 불일치')
                    writer = ShardWriter(folder / 'samples' / name, 'responses', limit=4_000_000)
                    for row in rows:
                        writer.append(row)
                    report['samples'][name] = writer.close(lineage=dict(task=name, model=args.model,
                        shots=args.shots, mode=args.mode, evaluation_only=True))
                    report['audits'][name] = audit
                    report['official_results'][name] = old.plain(result['results'][name])
                    report['actual_rows'] += expected
                    values.append(actual)
                    sizes.append(expected)
                report['weighted_accuracy'] = aggregate_subtask_metrics(values, sizes, weight_by_size=True)
                independent = sum(row['correct'] for row in report['audits'].values()) / sum(sizes)
                resource.need(math.isclose(report['weighted_accuracy'], independent, abs_tol=1e-12), '공식 크기가중 재집계 불일치')
                report['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
                report['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
                resource.need(report['peak_reserved_bytes'] <= 6 * 2**30, 'allocator 상한 초과')
                report['framework'] = framework
                report['dataset_revision'] = assets['dataset_revision']
        resource.need(report['actual_rows'] == (114 if args.mode == 'cost' else data.COUNT), '전체 분모 불일치')
        report['status'], code = ('LIMITED_COST_DIAGNOSTIC' if args.mode == 'cost' else 'OFFICIAL_MMLU_FULL_COMPLETE'), 0
    except (TimeoutError, ResourceHold) as exc:
        report.update(status='HOLD', error_type=type(exc).__name__, error=str(exc)[:1500])
        code = 8
    except Exception as exc:
        report.update(status='ERROR', error_type=type(exc).__name__, error=str(exc)[:1500])
        code = 9
    finally:
        def finish_lengths():
            if lengths is not None and lengths._total_rows:
                report['lengths_manifest'] = lengths.close(lineage=dict(model=args.model, shots=args.shots, mode=args.mode, partial=code != 0))
                verify_shards(folder / 'lengths', report['lengths_manifest'])
        def stop_watch():
            if watch is not None:
                report['vram_watch'] = watch.stop()
        def close_cuda():
            if 'torch' in sys.modules:
                close_owned_cuda(sys.modules['torch'], report)
        def check_parent():
            spec = profile['models'][args.model]
            report['parent_unchanged'] = data.digest(ROOT / spec['checkpoint']) == spec['checkpoint_sha256']
            resource.need(report['parent_unchanged'], '원 체크포인트 변질')
        def check_source():
            report['source_unchanged'] = profile['source'] == identity()
            resource.need(report['source_unchanged'], '고정 소스 변형')
            data.verify_assets()
            report['original_assets_unchanged'] = True
        gc.collect()
        good = independent_final_checks(report, [('watch', stop_watch), ('lengths', finish_lengths),
            ('cuda', close_cuda), ('parent', check_parent), ('source', check_source)])
        if not good:
            report['status'], code = 'ERROR', 9
        elif report.get('vram_watch', {}).get('reason') is not None and code != 9:
            report['status'], code = 'HOLD', 8
        report.update(final_exit=code, wall_seconds=time.monotonic() - started,
                      ended_at=datetime.now(timezone.utc).isoformat())
        resource.write_new(folder / 'report.json', report)
        print(json.dumps({key:report[key] for key in ('status', 'model', 'shots', 'actual_rows', 'final_exit', 'wall_seconds')}), flush=True)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('assets', 'contract', 'cost', 'full'), required=True)
    parser.add_argument('--model', choices=data.MODELS)
    parser.add_argument('--shots', type=int, choices=data.SHOTS)
    parser.add_argument('--profile')
    parser.add_argument('--profile-sha256')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.execute == args.check_only:
        parser.error('실행 또는 읽기전용 하나만 명시')
    resource.need((DEADLINE - datetime.now(timezone.utc)).total_seconds() > 120, '마감 예비120초')
    if args.mode in ('assets', 'contract'):
        if args.check_only:
            print(json.dumps(dict(status='CPU_PREPARATION_NOT_RUN', mode=args.mode, source=identity())))
            return 0
        for key, value in OFFLINE.items():
            os.environ[key] = value
        with resource.wall(900):
            if args.mode == 'assets':
                value = data.prepare_assets()
                print(json.dumps(dict(status=value['status'], subjects=len(value['subjects']), test_rows=data.COUNT)))
                return 0
            return prepare_contract()
    if args.model is None or args.shots is None or not args.profile or not args.profile_sha256:
        parser.error('고정 모델/shot/profile/SHA 필요')
    return evaluate(args)


if __name__ == '__main__':
    raise SystemExit(main())
