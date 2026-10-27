#!/usr/bin/env python3
"""Bounded native GGUF TF-probability canary; no student or checkpoint writes.

Reuse the existing pinned Qwen assets and owned server lifecycle. Explicit
spec-type none is required: one requested token does not itself disable MTP.
Import/check-only touches source files only, never models/GPU/assets.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA = 'P106B_TEACHER_TF_CANARY_V1'
OUTPUT = ROOT / 'test_result/evidence/p106b_qwen_tf_v1_s1337'
DEADLINE = datetime(2026, 10, 23, 7, 30, tzinfo=timezone.utc)
CASES = ('User: 1+1은?\nAssistant:', 'The capital of France is')
BIASES = (20, 100, 200)
ATOL = 1e-5
SOURCES = ('scripts/diag_p106b_teacher_tf.py', 'scripts/test_p106b_teacher_tf.py',
    'scripts/p106b_qwen_teacher.py', 'scripts/diag_p106b_qwen_coload.py',
    'scripts/diag_p106b_mtp_teacher.py', 'scripts/diag_p106_coload.py',
    'scripts/diag_p106b_online_rate5.py', 'scripts/diag_p106_vram_sample.py',
    'scripts/p106b_gate_runtime.py', 'scripts/p106b_shards.py')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest().upper()


def sources():
    return {name: digest(ROOT / name) for name in SOURCES}


def command(profile, port, key):
    values = list(profile.command(port, key))
    for flag in ('--spec-type', '--spec-draft-n-max'):
        index = values.index(flag)
        del values[index:index+2]
    values[values.index('--ctx-size')+1] = '1024'
    values += ['--spec-type', 'none']
    return values


def payload(prefix, target=None, bias=100):
    if (not isinstance(prefix, list) or not prefix
            or any(type(i) is not int or i < 0 for i in prefix) or len(prefix) >= 1024):
        raise ValueError('exact nonempty bounded prefix token IDs required')
    result = dict(prompt=prefix, n_predict=1, n_probs=2, temperature=0.0,
        post_sampling_probs=False, stream=False, cache_prompt=False, seed=1337,
        repeat_penalty=1.0, presence_penalty=0.0, frequency_penalty=0.0,
        top_p=1.0, top_k=0, min_p=0.0)
    if target is not None:
        if type(target) is not int or target < 0 or bias not in BIASES:
            raise ValueError('known nonnegative target and preregistered bias required')
        result['logit_bias'] = [[target, bias]]
    return result


def probability_entry(reply):
    if not isinstance(reply, dict): raise ValueError('native response object required')
    rows = reply.get('completion_probabilities')
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError('native one-token completion_probabilities schema required')
    row = rows[0]
    def valid(item):
        if not isinstance(item, dict) or type(item.get('id')) is not int or item['id'] < 0:
            raise ValueError('exact returned integer token ID required')
        value = item.get('logprob')
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not -1e30 < value <= 1e-6):
            raise ValueError('invalid/pre-sampling logprob or underflow sentinel')
        return dict(id=item['id'], logprob=float(value))
    chosen = valid(row)
    top = row.get('top_logprobs')
    if not isinstance(top, list) or len(top) < 2:
        raise ValueError('two raw top_logprobs required')
    top = [valid(item) for item in top]
    if len({item['id'] for item in top}) != len(top):
        raise ValueError('duplicate raw top IDs')
    return dict(chosen=chosen, top=top)


def evaluate_forcing(reference, observations, baseline_top=None):
    """Compare to independently observed original target p, never only forces."""
    rows = []
    for bias, observed in observations:
        forced = observed['chosen']['id'] == reference['id']
        delta = abs(observed['chosen']['logprob'] - reference['logprob']) if forced else None
        top_same = None
        if baseline_top is not None:
            top_same = (len(baseline_top) == len(observed['top']) and all(
                a['id'] == b['id'] and abs(a['logprob']-b['logprob']) <= ATOL
                for a, b in zip(baseline_top, observed['top'])))
        rows.append(dict(bias=bias, target_id=reference['id'], actual_id=observed['chosen']['id'],
            forced=forced, status='NOT_FORCED' if not forced else 'MATCH' if delta <= ATOL else 'LOGPROB_CHANGED',
            target_logprob=observed['chosen']['logprob'] if forced else None, absolute_difference=delta,
            original_top_logprobs_unchanged=top_same))
    return dict(rows=rows, passed=all(row['status'] == 'MATCH' and row['original_top_logprobs_unchanged'] is not False for row in rows))


@contextmanager
def session_for(profile):
    from scripts import diag_p106b_qwen_coload as runtime
    adapter = SimpleNamespace(command=lambda port, key: command(profile, port, key))
    session = runtime.QwenSession('qwen_tf_mtp_off')
    with patch.object(runtime, 'profile', adapter):
        with session as active: yield active


def write_report(path, value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    if len(raw) >= 20_000_000: raise ValueError('report must be below20MB')
    with path.open('xb') as stream: stream.write(raw)


def recorded_request(session, writer, report, route, value, kind):
    """Preserve the attempted payload before I/O, including bounded failures."""
    report['http_attempted'] += 1
    completion = route == '/completion'
    report['completion_attempted'] += int(completion)
    attempt = report['http_attempted']
    writer.append(dict(event='request_attempt', attempt=attempt, route=route, kind=kind, payload=value))
    try:
        reply = session.request(route, value, timeout=90)
    except BaseException as exc:
        error = dict(type=type(exc).__name__, message=str(exc).replace(session.key, '<REDACTED>')[:1200])
        if isinstance(exc, HTTPError):
            from scripts.p106b_http_errors import capture_http_error
            error['http'] = capture_http_error(exc, session.key)
        writer.append(dict(event='request_failed', attempt=attempt, route=route, kind=kind, error=error))
        raise
    report['http_succeeded'] += 1
    report['requests'] += int(completion)
    writer.append(dict(event='request_succeeded', attempt=attempt, route=route, kind=kind, reply=reply))
    return reply


def execute():
    if datetime.now(timezone.utc).timestamp()+600 > DEADLINE.timestamp():
        raise ValueError('600-second canary does not fit current model deadline')
    if OUTPUT.exists() or OUTPUT.is_symlink(): raise FileExistsError('prior/partial output preserved')
    from scripts import p106b_qwen_teacher as profile
    from scripts.p106b_gate_runtime import wall_limit, idle_before_gpu
    from scripts.p106b_shards import ShardWriter, verify
    input_sources = sources()
    assets = profile.assets(True)
    idle_before_gpu()
    if datetime.now(timezone.utc).timestamp()+600 > DEADLINE.timestamp():
        raise ValueError('600-second canary no longer fits after asset/admission checks')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(OUTPUT, 'raw')
    report = dict(schema=SCHEMA, status='STARTED', returncode=9, source_sha256=input_sources,
        assets=assets, mtp=False, spec_type='none', student_loads=0, checkpoint_writes=0,
        teacher_probability_definition='QUANTIZED_MAIN_MODEL_PRE_SAMPLING_TARGET_LOGPROB',
        quality_claim=False, absolute_tolerance=ATOL, requests=0, cases=[],
        http_attempted=0, http_succeeded=0, completion_attempted=0)
    began = time.perf_counter()
    session = None
    try:
        with wall_limit(600), session_for(profile) as session:
            report.update(props=session.props, startup_seconds=session.startup_sec,
                redacted_command=command(profile, session.port, '<REDACTED>'))
            for text in CASES:
                session.check()
                tokenized = recorded_request(session, writer, report, '/tokenize',
                    dict(content=text, add_special=True, with_pieces=False), 'ids')
                ids = tokenized.get('tokens')
                pieces = recorded_request(session, writer, report, '/tokenize',
                    dict(content=text, add_special=True, with_pieces=True), 'token_pieces')
                piece_rows = pieces.get('tokens')
                if (not isinstance(piece_rows, list) or any(not isinstance(row, dict)
                        or type(row.get('id')) is not int or not isinstance(row.get('piece'), (str, list)) for row in piece_rows)
                        or [row['id'] for row in piece_rows] != ids):
                    raise ValueError('native pieces must preserve exact token IDs')
                base_payload = payload(ids)
                base = recorded_request(session, writer, report, '/completion', base_payload, 'base')
                original = probability_entry(base)
                reference = original['top'][1]
                if reference['id'] == original['chosen']['id']:
                    raise ValueError('independent non-argmax top2 target unavailable')
                observed = []
                for bias in BIASES:
                    session.check()
                    forced_payload = payload(ids, reference['id'], bias)
                    reply = recorded_request(session, writer, report, '/completion', forced_payload, 'forced_top2')
                    observed.append((bias, probability_entry(reply)))
                comparison = evaluate_forcing(reference, observed, original['top'])
                tail = []
                outside = next(i for i in range(1000, 2000) if i not in {p['id'] for p in original['top']})
                for bias in BIASES:
                    session.check()
                    forced_payload = payload(ids, outside, bias)
                    reply = recorded_request(session, writer, report, '/completion', forced_payload, 'forced_outside_top2')
                    parsed = probability_entry(reply)
                    tail.append(dict(bias=bias, **parsed))
                forced_tail = [r['chosen']['logprob'] for r in tail if r['chosen']['id'] == outside]
                tail_consistent = len(forced_tail) == 3 and max(forced_tail)-min(forced_tail) <= ATOL
                report['cases'].append(dict(text=text, prefix_ids=ids, original=original,
                    reference=reference, comparison=comparison, outside_top2_id=outside,
                    tail_observations=tail, tail_forced_logprob_consistent=tail_consistent,
                    tail_absolute_unbiased_probability='NOT_MEASURED',
                    passed=comparison['passed'] and tail_consistent))
                print('[TF_CANARY] '+json.dumps(report['cases'][-1], ensure_ascii=False), flush=True)
            report.update(memory=session.memory(), server_tail=session.tail, signals=session.signals)
        passed = len(report['cases']) == 2 and all(r['passed'] for r in report['cases'])
        report.update(status='TF_SIGNAL_CANARY_COMPLETE' if passed else 'TF_SIGNAL_CANARY_NEGATIVE', returncode=0 if passed else 8)
    except BaseException as exc:
        report.update(status='TF_SIGNAL_EXECUTION_ERROR', returncode=9,
            error_type=type(exc).__name__, error=str(exc)[:2000])
    finally:
        if session is not None:
            report.update(server_tail=session.tail, signals=session.signals,
                telemetry_errors=session.errors, successful_memory_samples=len(session.samples))
        if writer._total_rows:
            manifest = writer.close(lineage=dict(schema=SCHEMA, teacher_sha256=profile.MODEL_SHA))
            verify(OUTPUT, manifest)
            report['raw_manifest'] = manifest
        report['sources_unchanged'] = sources() == input_sources
        if not report['sources_unchanged']: report.update(status='SOURCE_CHANGED', returncode=9)
        report['wall_seconds'] = time.perf_counter()-began
        write_report(OUTPUT / 'report.json', report)
        print('[TF_FINAL] '+json.dumps({k:report.get(k) for k in ('status','returncode','requests','wall_seconds','quality_claim')}, ensure_ascii=False), flush=True)
    return report['returncode']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    if args.check_only:
        print(json.dumps(dict(schema=SCHEMA, sources=sources(), model_loads=0, gpu_calls=0,
            asset_reads=0, expected_completion_requests=14, status='SOURCE_ONLY'), ensure_ascii=False))
        return 0
    return execute()


if __name__ == '__main__':
    raise SystemExit(main())
