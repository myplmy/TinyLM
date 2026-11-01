#!/usr/bin/env python3
"""완료0shot 원형을 보존한 공식5shot의 명시 감시/계측 경계 복구."""
from __future__ import annotations
import argparse
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_official_mmlu as original
from scripts import diag_p106b_resource_matrix as resource
from scripts.p106b_nvml_probe import watcher_class

OLD_PROFILE = original.PROFILE
OLD_SHA = 'A2DA0A92D7B9E9264F7D558B581D50F36FA39E313FABD3152F56718C87CBCBFB'
PROFILE = ROOT / 'data_cache/p106b_mmlu_nvml_v1_20261101/profile.json'
OUTPUT = ROOT / 'test_result/evidence/p106b_mmlu_nvml_v1_20261101'
PROBE = ROOT / 'test_result/evidence/p106b_nvml_probe_v2_20261101/report.json'
OWN = ('scripts/diag_p106b_mmlu_nvml_recovery.py', 'scripts/test_p106b_mmlu_nvml_recovery.py',
       'scripts/p106b_nvml_probe.py', 'scripts/test_p106b_nvml_probe.py', 'scripts/diag_p106b_nvml_probe.py')
UNCHANGED = ('policy', 'read_profile', 'admit_full', 'evaluate')
BOUNDARIES = ('VramWatch', 'identity', 'PROFILE', 'data.OUTPUT', 'timed_backend')


def identity():
    files = dict(original.identity()['files'])
    files.update({name:original.data.digest(ROOT / name) for name in OWN})
    return dict(files=files, sha256=resource.sha(files))


def function_ast(function):
    return ast.dump(ast.parse(inspect.getsource(function)), include_attributes=False)


@contextmanager
def timed_backend(lm, torch, report):
    """예외가 나도 실제 경과/완료 forward량만 남기며 점수는 그대로 반환한다."""
    old_likelihood, old_batch = lm._loglikelihood_tokens, lm.core.score_batch
    start_record = len(lm.core.records)
    report.update(backend_forward_batches_completed=0, backend_requests_completed=0)
    def batch(value):
        result = old_batch(value)
        report['backend_forward_batches_completed'] += 1
        report['backend_requests_completed'] += len(result)
        if report['backend_requests_completed'] % 4000 == 0:
            print(json.dumps(dict(event='BACKEND_PROGRESS',
                completed_requests=report['backend_requests_completed'])), flush=True)
        return result
    def run(requests, **kwargs):
        torch.cuda.synchronize()
        started = time.monotonic()
        try:
            return old_likelihood(requests, **kwargs)
        finally:
            report['scorer_seconds'] += time.monotonic() - started
    lm._loglikelihood_tokens, lm.core.score_batch = run, batch
    try:
        yield
    finally:
        # 모델 참조를 CUDA 정리보다 먼저 원상 복구한다.
        lm._loglikelihood_tokens, lm.core.score_batch = old_likelihood, old_batch
        rows = lm.core.records[start_record:]
        report['scored_input_positions'] = sum(row['input_tokens'] for row in rows)
        report['completed_record_requests'] = len(rows)
        report['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
        report['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
        report['partial_telemetry_is_not_official_score'] = True


def private_driver():
    spec = importlib.util.spec_from_file_location('_p106b_mmlu_nvml_private', original.__file__)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    driver.VramWatch = watcher_class()
    driver.identity, driver.PROFILE = identity, PROFILE
    driver.data = SimpleNamespace(**vars(original.data))
    driver.data.OUTPUT = OUTPUT
    driver.timed_backend = timed_backend
    for name in UNCHANGED:
        resource.need(function_ast(getattr(driver, name)) == function_ast(getattr(original, name)),
                      '원평가 함수 본문 변경: ' + name)
    return driver


def verify_probe():
    proof = json.loads(PROBE.read_text())
    resource.need(proof['status'] == 'IDLE_BUSY_NVML_PARITY_COMPLETE' and proof['final_exit'] == 0,
                  '완료된 v2 idle/busy 실물 대조 필요')
    resource.need(proof['source_unchanged'] and not proof['final_verification_errors'], '프로브 종결 검산 필요')
    resource.need(proof['client']['closed'] and proof['client']['query_errors'] == 0
                  and proof['client']['successful_queries'] == 80 and len(proof['rows']) == 80,
                  '80조회와 소유 프로브 종결 필요')
    for name, digest in proof['source'].items():
        resource.need(original.data.digest(ROOT / name) == digest, '실물 검증 소스 변형: ' + name)
    resource.need(proof['final_cuda_cleanup']['allocated_bytes'] == 0
                  and proof['final_cuda_cleanup']['reserved_bytes'] == 0, '소유 CUDA0 필요')
    return dict(path=str(PROBE.relative_to(ROOT)), sha256=original.data.digest(PROBE),
        policy=dict(query_timeout_seconds=3, interval_seconds=.5, maximum_consecutive_failures=3,
                    shared_increment_limit_bytes=8_000_000_000),
        memory_definition='NVML_V2_USED_WITH_RESERVED_SEPARATE_DEVICE_VALIDATED',
        exact_process_peak_claim=False)


def prepare_contract():
    resource.need(original.data.digest(OLD_PROFILE) == OLD_SHA, '이전 동결 profile 변형')
    prior = json.loads(OLD_PROFILE.read_text())
    resource.need(prior['source'] == original.identity(), '성공0shot 원소스 변형')
    proof = verify_probe()
    driver = private_driver()
    for n in (0, 5):
        resource.need(driver.policy(n) == prior['policies'][str(n)], '평가 정책 변경 금지')
    result = dict(prior)
    result.update(created_at=datetime.now(timezone.utc).isoformat(), source=identity(),
        origin_profile=dict(path=str(OLD_PROFILE.relative_to(ROOT)), sha256=OLD_SHA),
        recovery=dict(allowed_bindings=list(BOUNDARIES), unchanged_function_ast={
            name:resource.sha(function_ast(getattr(driver, name))) for name in UNCHANGED},
            monitor=proof, completed_0shot_reexecution=False, supported_arms=['native5','broad5']),
        cpu_contract_reuse='SAME_OFFICIAL_REQUESTS_TOKENIZER_MODELS_LENGTHS_POLICIES_SOURCE_VERIFIED')
    # 이전 계약의 요청/정답/길이/모델을 변환하거나 새로 고르지 않는다.
    resource.need(all(result[name] == prior[name] for name in ('assets_sha256','models','tokenizer_sha256',
        'framework','shots','policies','cpu_lengths','test_train_or_teacher_reuse')), '계약 복사 불변성')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    PROFILE.parent.mkdir(parents=True, exist_ok=False)
    resource.write_new(PROFILE, result)
    resource.write_new(OUTPUT / 'contract.json', result)
    print(json.dumps(dict(status='NVML_RECOVERY_PROFILE_FROZEN', profile_sha256=original.data.digest(PROFILE),
        source_sha256=result['source']['sha256'], gpu_runs=0)))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('contract','cost','full'), required=True)
    parser.add_argument('--arm', choices=('native5','broad5'))
    parser.add_argument('--profile')
    parser.add_argument('--profile-sha256')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.execute == args.check_only:
        parser.error('실행 또는 읽기전용을 하나 선택')
    resource.need(time.time() + 120 < original.DEADLINE.timestamp(), '11시 예비120초')
    if args.mode == 'contract':
        if args.check_only:
            print(json.dumps(dict(status='RECOVERY_CPU_CONTRACT_NOT_RUN', source=identity())))
            return 0
        return prepare_contract()
    if not args.arm or not args.profile or not args.profile_sha256:
        parser.error('고정 arm/profile/SHA 필요')
    frozen = json.loads(PROFILE.read_text())
    resource.need(frozen['recovery']['monitor'] == verify_probe(), '실물 프로브 종속성 변경')
    driver = private_driver()
    args.model, args.shots = driver.ARMS[args.arm]
    return driver.evaluate(args)


if __name__ == '__main__':
    raise SystemExit(main())
