#!/usr/bin/env python3
"""고정 GSM8K CPU 계약/공식 생성 평가. 추가학습·패키지설치·다운로드 없음."""
from __future__ import annotations
import argparse
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
from types import MethodType

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_official_gsm8k as data
from scripts import diag_p106b_resource_matrix as resource
from scripts.diag_p106b_official_mmlu import identity as prior_identity, OFFLINE
from scripts.diag_p107_adaptive_training import VramWatch, ResourceHold
from scripts.diag_p107_hybrid_mntp import close_owned_cuda, independent_final_checks
from scripts.p106b_shards import ShardWriter, verify as verify_shards

DEADLINE = datetime(2026, 11, 1, 2, 0, tzinfo=timezone.utc)
ARMS = {'native': 'native595-q', 'broad': 'new595-broad-q'}
PROFILE = data.CACHE / 'profile.json'
OWN = ('scripts/p106b_official_gsm8k.py', 'scripts/diag_p106b_official_gsm8k.py',
       'scripts/test_p106b_official_gsm8k.py', 'scripts/p106b_official_archive.py',
       'scripts/test_p106b_official_archive.py')


def identity():
    files = dict(prior_identity()['files'])
    files.update({name:data.digest(ROOT / name) for name in OWN})
    return dict(files=files, sha256=resource.sha(files))


def policy():
    return dict(num_fewshot=5, max_gen_toks=256, max_length=1024, batch_size=1, chat_template=False,
        precision='FP32_MATH_TF32_OFF', temperature=0., top_k=1, do_sample=False, use_cache=True, mtp=False,
        random_seed=1337, fewshot_random_seed=1337, request_cache=False, bootstrap_iters=100000,
        native_sampler='UNCHANGED_TINYLM_SAMPLE', text_stop='UPSTREAM_POSTPROCESS_PREFIX',
        training=0, checkpoint_writes=0)


def prepare_contract():
    from scripts import interactive_research_infer as manual
    task, assets = data.load_task()
    tokenizer = manual.local_tokenizer(manual.verify_manifest())
    task.build_all_requests(limit=None, rank=0, world_size=1, cache_requests=False,
        rewrite_requests_cache=False, system_instruction=None, apply_chat_template=False, fewshot_as_multiturn=False)
    requests = task.instances
    resource.need(len(requests) == 1319 and [request.doc_id for request in requests] == list(range(1319)), '공식 생성 전체 ID 필요')
    cases = []
    for request in requests:
        resource.need(request.request_type == 'generate_until' and len(request.args) == 2, '공식 generate_until 필요')
        prompt, kwargs = request.args
        maximum, _ = data.options(kwargs)
        resource.need(maximum == 256, '공식 backend 기본256생성 필요')
        ids = tokenizer.encode(prompt, add_special_tokens=False).ids
        kept = ids[-768:]
        cases.append(dict(doc_id=request.doc_id, prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest().upper(),
            generation_kwargs=kwargs, original_prompt_tokens=len(ids), kept_prompt_tokens=len(kept),
            removed_prompt_tokens=len(ids) - len(kept), prefix_ids_sha256=resource.sha(kept)))
    metric_oracle = data.metric_oracle(task)
    model_source = ROOT / 'data_cache/p106b_mmlu_official_v1_20261101/profile_v2.json'
    resource.need(data.digest(model_source) == 'A2DA0A92D7B9E9264F7D558B581D50F36FA39E313FABD3152F56718C87CBCBFB', '이전 동결 모델 메타데이터 필요')
    models = json.loads(model_source.read_text())['models']
    for spec in models.values():
        resource.need(data.digest(ROOT / spec['checkpoint']) == spec['checkpoint_sha256'], '원CP 변형')
    result = dict(schema='P106B_OFFICIAL_GSM8K_PROFILE_V1', status='CPU_CONTRACT_COMPLETE',
        created_at=datetime.now(timezone.utc).isoformat(), source=identity(), models=models,
        assets_sha256=data.digest(data.CACHE / 'assets.json'), cases=cases, policy=policy(),
        metric_oracle=metric_oracle, authority_directive=104, deadline=DEADLINE.isoformat(),
        context_summary=dict(rows=1319, requests=1319, truncated=sum(c['removed_prompt_tokens'] > 0 for c in cases),
            removed_tokens=sum(c['removed_prompt_tokens'] for c in cases),
            maximum_original=max(c['original_prompt_tokens'] for c in cases), maximum_kept=max(c['kept_prompt_tokens'] for c in cases)),
        benchmark_train_split='OFFICIAL_FEWSHOT_ONLY_NOT_WEIGHT_TRAINING', models_loaded=0, gpu_runs=0)
    folder = data.OUTPUT / 'contract'
    resource.need(not folder.exists() and not PROFILE.exists(), '새 CPU계약 출력 필요')
    folder.mkdir()
    resource.write_new(PROFILE, result)
    resource.write_new(folder / 'report.json', result)
    print(json.dumps(dict(status=result['status'], profile_sha256=data.digest(PROFILE), context=result['context_summary'])))
    return 0


def read_profile(path, expected):
    resource.need(path == str(PROFILE.relative_to(ROOT)) and data.digest(PROFILE) == expected, '고정 profile 경로/SHA 필요')
    value = json.loads(PROFILE.read_text())
    resource.need(value['source'] == identity() and value['policy'] == policy() and value['deadline'] == DEADLINE.isoformat(), 'source/policy/마감 불일치')
    resource.need(value['assets_sha256'] == data.digest(data.CACHE / 'assets.json'), '고정 자료 manifest 다름')
    data.verify_assets()
    return value


def admit_full(cost, model, profile_sha, now):
    if (cost.get('status') != 'LIMITED_COST_DIAGNOSTIC' or cost.get('model') != model
            or cost.get('final_exit') != 0 or cost.get('actual_rows') != 8
            or cost.get('source') != identity() or cost.get('policy') != policy()
            or cost.get('profile_sha256') != profile_sha):
        raise ValueError('동일 source/model/policy/profile의8생성 비용 필요')
    measured = cost.get('generation_seconds')
    if isinstance(measured, bool) or not isinstance(measured, (int, float)) or not math.isfinite(measured) or measured <= 0:
        raise ValueError('실제 양수 생성시간 필요')
    forecast = measured / 8 * 1319 * 1.5 + 120
    if forecast > 10800 or now + forecast + 120 >= DEADLINE.timestamp():
        raise ResourceHold('전량 예상이3시간 또는11시 예비를 초과')
    return dict(forecast_seconds=forecast, forecast_scope='EMPIRICAL_MEAN_TIMES1_5_NOT_GUARANTEE',
                hard_cap_seconds=min(10800, int(DEADLINE.timestamp() - now - 120)))


def sample_audits(rows, expected):
    result = {}
    for name in ('strict-match', 'flexible-extract'):
        group = [row for row in rows if row['filter'] == name]
        if len(group) != expected or [row['doc_id'] for row in group] != list(range(expected)):
            raise ValueError('각 official filter의 전체 분모/순서 필요')
        values = [row['exact_match'] for row in group]
        if any(value not in (0, 1, 0., 1.) for value in values):
            raise ValueError('공식 item exact-match 값 오류')
        result[name] = dict(rows=expected, correct=int(sum(values)), exact_match=sum(values) / expected)
    if len(rows) != 2 * expected:
        raise ValueError('두 filter 외 중복/누락 sample')
    return result


def numeric_canary(lm, torch):
    from scripts.diag_p106b_official_core6 import numerical_canary
    return numerical_canary(lm, torch)


def cache_canary(active):
    """고정 동일 이력의 마지막 logits를 KV 증분/전체 재계산으로 독립 대조한다."""
    from scripts import interactive_research_infer as manual
    torch = active['torch']
    _, proxy = manual.precision_types()
    forward = proxy(active['model'], 'fp32_math')
    history = active['tokenizer'].encode('Question: two plus three? Answer:', add_special_tokens=False).ids
    forced = active['tokenizer'].encode(' five.', add_special_tokens=False).ids + [2]
    past, results = None, []
    for index in range(3):
        incremental_input = history if past is None else history[-1:]
        incremental, past = forward(torch.tensor([incremental_input], device='cuda'), past_kv=past, use_cache=True)
        rebuilt = forward(torch.tensor([history], device='cuda'), use_cache=False)
        left, right = incremental[:, -1].float(), rebuilt[:, -1].float()
        close = bool(torch.allclose(left, right, atol=1e-4, rtol=1e-4))
        results.append(dict(index=index, history_tokens=len(history), max_abs=float((left-right).abs().max()),
            argmax_equal=bool(left.argmax(-1).eq(right.argmax(-1)).all()), float_close=close,
            atol=1e-4, rtol=1e-4, comparison='SAME_HISTORY_NO_SEMANTIC_GOLD'))
        resource.need(close, '고정 이력의 KV/재계산 float oracle 음성')
        history.append(forced[index % len(forced)])
    return results


def evaluate(args):
    profile = read_profile(args.profile, args.profile_sha256)
    model = ARMS[args.arm]
    cost_path = data.OUTPUT / model / 'cost/report.json'
    try:
        admission = (admit_full(json.loads(cost_path.read_text()), model, args.profile_sha256, time.time())
                     if args.mode == 'full' else dict(hard_cap_seconds=900))
    except ResourceHold as exc:
        print(json.dumps(dict(status='NOT_RUN_RESOURCE_HOLD', actual_model_runs=0, reason=str(exc))), flush=True)
        return 8
    resource.need(time.time() + admission['hard_cap_seconds'] + 120 <= DEADLINE.timestamp(), '시간 예비 필요')
    if args.check_only:
        print(json.dumps(dict(status='READY_GPU_NOT_RUN', model=model, admission=admission)))
        return 0
    folder = data.OUTPUT / model / args.mode
    resource.need(not folder.exists(), '이전/부분 출력을 덮지 않는다')
    folder.mkdir(parents=True)
    report = dict(schema='P106B_OFFICIAL_GSM8K_RUN_V1', status='STARTED', model=model,
        mode=args.mode, policy=policy(), source=identity(), profile_sha256=args.profile_sha256,
        admission=admission, model_metadata=profile['models'][model], actual_rows=0, generation_seconds=0.,
        generated_tokens=0, resource_limit_bytes=8_000_000_000, training=0, checkpoint_writes=0,
        benchmark_train_split='FEWSHOT_IN_PROMPT_ONLY', contamination='ALL_PRETRAINING_SEMANTIC_OVERLAP_UNKNOWN')
    started, code, watch, writer = time.monotonic(), 9, None, None
    try:
        for key, value in OFFLINE.items(): os.environ[key] = value
        task, assets = data.load_task()
        from scripts.p106b_official_lm_adapter import research_adapter
        from scripts import interactive_research_infer as manual
        from scripts.diag_p106b_official_core6 import plain
        from lm_eval.evaluator import simple_evaluate
        from lm_eval.tasks import TaskManager
        import torch
        from torch.nn.attention import sdpa_kernel, SDPBackend
        torch.set_num_threads(4)
        torch.manual_seed(1337)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        report['gpu_admission'] = manual.require_idle_gpu()
        watch = VramWatch(); watch.start()
        torch.cuda.set_per_process_memory_fraction(6 * 2**30 / torch.cuda.get_device_properties(0).total_memory)
        manager = TaskManager()
        writer = ShardWriter(folder / 'generation', 'responses', limit=4_000_000)
        budget = resource.Budget(admission['hard_cap_seconds'], deadline=DEADLINE)
        with resource.wall(min(admission['hard_cap_seconds'], int(DEADLINE.timestamp() - time.time() - 120))), sdpa_kernel(SDPBackend.MATH), torch.no_grad():
            with research_adapter(model, runtime_root=Path(sysconfig.get_paths()['purelib']), batch_size=1) as lm:
                report['model_proof'] = lm.provenance
                resource.need(lm.provenance['checkpoint_sha256'] == profile['models'][model]['checkpoint_sha256'], '실제 모델 원형 다름')
                report['numerical_canary'] = numeric_canary(lm, torch)
                active = lm.core.score_batch.runtime
                report['cache_canary'] = cache_canary(active)
                original_generate = lm.generate_until
                def generate(bound, requests, disable_tqdm=False):
                    outputs = []
                    for request in requests:
                        budget.check()
                        context, kwargs = request.args
                        case = profile['cases'][request.doc_id]
                        resource.need(hashlib.sha256(context.encode()).hexdigest().upper() == case['prompt_sha256']
                                      and kwargs == case['generation_kwargs'], '공식 CPU동결 문맥/생성요청 다름')
                        tick = time.monotonic()
                        answer, metadata = data.emit_plain(active, context, kwargs)
                        torch.cuda.synchronize()
                        report['generation_seconds'] += time.monotonic() - tick
                        resource.need(resource.sha(metadata['actual_prefix_ids']) == case['prefix_ids_sha256'], '실제 prompt prefix 다름')
                        writer.append(dict(doc_id=request.doc_id, prompt_sha256=case['prompt_sha256'],
                            answer=answer, metadata=metadata, role='OFFICIAL_TEST_GENERATION_NEVER_TRAIN'))
                        report['actual_rows'] += 1
                        report['generated_tokens'] += metadata['generated_tokens']
                        outputs.append(answer)
                        bound.cache_hook.add_partial('generate_until', (context, kwargs), answer)
                        if report['actual_rows'] % 50 == 0:
                            print(json.dumps(dict(model=model, completed=report['actual_rows'], generated=report['generated_tokens'])), flush=True)
                    return outputs
                lm.generate_until = MethodType(generate, lm)
                try:
                    result = simple_evaluate(model=lm, tasks=[task], num_fewshot=5, task_manager=manager,
                        batch_size=1, device='cuda', use_cache=None, cache_requests=False,
                        limit=8 if args.mode == 'cost' else None, bootstrap_iters=100000, log_samples=True,
                        apply_chat_template=False, fewshot_as_multiturn=False, random_seed=1337,
                        numpy_random_seed=1337, torch_random_seed=1337, fewshot_random_seed=1337)
                finally:
                    lm.generate_until = original_generate
                    active = original_generate = None
                expected = 8 if args.mode == 'cost' else 1319
                resource.need(set(result['samples']) == {'gsm8k'} and report['actual_rows'] == expected, '공식 실제생성 분모 필요')
                samples = plain(result['samples']['gsm8k'])
                audits = sample_audits(samples, expected)
                sample_writer = ShardWriter(folder / 'samples', 'responses', limit=4_000_000)
                for row in samples: sample_writer.append(row)
                report['samples'] = sample_writer.close(lineage=dict(model=model, mode=args.mode,
                    generated_documents=expected, filter_rows=2 * expected, evaluation_only=True))
                for name, audit in audits.items():
                    resource.need(math.isclose(result['results']['gsm8k']['exact_match,' + name], audit['exact_match'], abs_tol=1e-12), '공식 filter 집계 불일치')
                report['audits'], report['official_result'] = audits, plain(result['results']['gsm8k'])
                report['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
                report['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
                resource.need(report['peak_reserved_bytes'] <= 6 * 2**30, 'allocator 상한 초과')
        report['status'], code = ('LIMITED_COST_DIAGNOSTIC' if args.mode == 'cost' else 'OFFICIAL_GSM8K_FULL_COMPLETE'), 0
    except (TimeoutError, ResourceHold) as exc:
        report.update(status='HOLD', error_type=type(exc).__name__, error=str(exc)[:1500]); code = 8
    except Exception as exc:
        report.update(status='ERROR', error_type=type(exc).__name__, error=str(exc)[:1500]); code = 9
    finally:
        def finish_writer():
            if writer is not None and report['actual_rows']:
                report['generation'] = writer.close(lineage=dict(model=model, mode=args.mode, partial=code != 0))
                verify_shards(folder / 'generation', report['generation'])
        def stop_watch():
            if watch is not None: report['vram_watch'] = watch.stop()
        def close_cuda():
            if 'torch' in sys.modules: close_owned_cuda(sys.modules['torch'], report)
        def original_unchanged():
            spec = profile['models'][model]
            report['parent_unchanged'] = data.digest(ROOT / spec['checkpoint']) == spec['checkpoint_sha256']
            report['source_unchanged'] = profile['source'] == identity()
            resource.need(report['parent_unchanged'] and report['source_unchanged'], '원형/소스 변질')
            data.verify_assets(); report['assets_unchanged'] = True
        gc.collect()
        good = independent_final_checks(report, [('watch', stop_watch), ('generation', finish_writer),
            ('cuda', close_cuda), ('original', original_unchanged)])
        if not good: report['status'], code = 'ERROR', 9
        elif report.get('vram_watch', {}).get('reason') is not None and code != 9: report['status'], code = 'HOLD', 8
        report.update(final_exit=code, wall_seconds=time.monotonic() - started)
        resource.write_new(folder / 'report.json', report)
        print(json.dumps({key:report[key] for key in ('status', 'model', 'mode', 'actual_rows', 'final_exit', 'wall_seconds')}), flush=True)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('assets', 'contract', 'cost', 'full'), required=True)
    parser.add_argument('--arm', choices=tuple(ARMS))
    parser.add_argument('--profile')
    parser.add_argument('--profile-sha256')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.execute == args.check_only: parser.error('실행/읽기전용 하나만 명시')
    resource.need((DEADLINE - datetime.now(timezone.utc)).total_seconds() > 120, '마감 예비 필요')
    if args.mode in ('assets', 'contract'):
        if args.check_only:
            print(json.dumps(dict(status='CPU_NOT_RUN', source=identity()))); return 0
        for key, value in OFFLINE.items(): os.environ[key] = value
        with resource.wall(900):
            if args.mode == 'assets':
                value = data.prepare_assets(); print(json.dumps(dict(status=value['status']))); return 0
            return prepare_contract()
    if args.arm is None or not args.profile or not args.profile_sha256: parser.error('고정 arm/profile/SHA 필요')
    return evaluate(args)


if __name__ == '__main__':
    raise SystemExit(main())
