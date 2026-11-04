#!/usr/bin/env python3
"""CPU proof and write-once synthetic profile for the new P107 command path."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import re
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import train_p107_documents as cli
from tinylm.train.document_input import canonical_sha, load_document_input

BASE = ROOT/cli.AUDIT


def write_new(path, value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+chr(10)).encode('utf-8')
    if len(raw) >= 20_000_000:
        raise ValueError('per-file 20MB bound')
    with path.open('xb') as stream:
        stream.write(raw)


def ref(path):
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size,
                sha256=cli.manual.file_sha(path))


def cpu_raw(version):
    stage = 'Stage8aWb' if version == 1 else 'Stage8aWc'+str(version)
    return ROOT/'test_result'/('107_log_20261104_P107_'+stage+'_document_cli_cpu.txt')


def cpu(version):
    import torch
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '' or torch.cuda.is_initialized():
        raise ValueError('CPU proof child must explicitly hide CUDA')
    output = BASE/('CPU_RUN_v'+str(version)+'.json')
    if output.exists():
        raise FileExistsError('old CPU proof must be preserved')
    before = cli.source_pins()
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'scripts.test_p107_document_input', 'scripts.test_p107_document_cli'])
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    unchanged = cli.source_pins() == before
    cuda = torch.cuda.is_initialized()
    code = 0 if result.wasSuccessful() and result.testsRun == 30 and unchanged and not cuda else 1
    record = dict(schema='P107_DOCUMENT_CLI_CPU_RUN_V1', actual_exit=code,
        tests=result.testsRun, source_pins=before, source_unchanged=unchanged,
        failures=len(result.failures), errors=len(result.errors),
        cuda_initialized=cuda, model_checkpoint_loads=0,
        cpu_synthetic_model_fixture=True, quality_claim=False,
        raw_log=str(cpu_raw(version).relative_to(ROOT)), seconds=time.perf_counter()-started)
    BASE.mkdir(parents=True, exist_ok=True)
    write_new(output, record)
    print('[P107_CPU] '+json.dumps({k:record[k] for k in ('actual_exit','tests','source_unchanged','cuda_initialized','seconds')}))
    return code


def prepare(version):
    profile_path = ROOT/cli.PROFILE_PATH
    if profile_path.exists():
        raise FileExistsError('profile is write-once')
    sources = cli.source_pins()
    proof_path = BASE/('CPU_RUN_v'+str(version)+'.json')
    proof = json.loads(proof_path.read_text(encoding='utf-8'))
    if (proof['actual_exit'] != 0 or proof['tests'] != 30 or proof['source_pins'] != sources
            or proof['source_unchanged'] is not True or proof['cuda_initialized'] is not False):
        raise ValueError('current-source actual CPU30 proof required')
    raw_path = cpu_raw(version)
    raw_text = raw_path.read_text(encoding='utf-8')
    codes = re.findall(r'종료코드\s+(-?\d+)', raw_text)
    if not codes or codes[-1] != '0' or 'Ran 30 tests' not in raw_text or 'FAILED' in raw_text:
        raise ValueError('closed successful raw CPU log required')
    smoke_path = ROOT/cli.SMOKE_REPORT
    smoke = json.loads(smoke_path.read_text(encoding='utf-8'))
    if (smoke.get('returncode') != 0 or smoke.get('complete') is not True
            or smoke.get('failed_calls') != 0 or smoke.get('source_pins_unchanged') is not True
            or smoke.get('original_synthetic_unchanged') is not True):
        raise ValueError('successful current full smoke required before profile')
    for name, digest in smoke['source_pins_after'].items():
        if name in sources and sources[name] != digest:
            raise ValueError('smoke product source changed')
    baseline = (ROOT/'docs/EXPERIMENT_BASELINES.md').read_text(encoding='utf-8')
    if cli.TAG not in baseline:
        raise ValueError('namespace must be reserved before GPU')
    directory = ROOT/cli.INPUT_ROOT/('v'+str(version))
    if directory.exists():
        raise FileExistsError('old/partial input packets must be preserved')
    directory.mkdir(parents=True)
    rng = random.Random(20261104)
    rows = []
    for index in range(4):
        tokens = [rng.randrange(35,32768) for _ in range(4097)]
        rows.append(dict(source_id='synthetic-document-'+str(index), token_ids=tokens,
                         language='synthetic', source_sha256=canonical_sha(tokens)))
    data_path = directory/'documents.jsonl'
    raw = (chr(10).join(json.dumps(row, sort_keys=True) for row in rows)+chr(10)).encode('utf-8')
    if len(raw) >= 20_000_000:
        raise ValueError('input shard bound')
    with data_path.open('xb') as stream:
        stream.write(raw)
    manifest = dict(schema='P107_DOCUMENT_INPUT_V1', purpose='SYNTHETIC_TECHNICAL', split='train',
        tokenizer=dict(sha256=cli.manual.TOKENIZER_SHA, vocab_size=32768),
        admission=dict(status='TECHNICAL_FIXTURE_ONLY', training_authorized=False,
                       authority_ref='USER107_BOUNDED_TECHNICAL_ONLY', evidence=None),
        shards=[dict(file=ref(data_path), documents=4, tokens=4*4097)])
    input_manifest = directory/'manifest.json';write_new(input_manifest, manifest)
    packet = load_document_input(ROOT, ref(input_manifest), allowed_root=cli.INPUT_ROOT,
        tokenizer_sha256=cli.manual.TOKENIZER_SHA, vocab_size=32768, allow_admitted=False)
    contract_path = BASE/('CPU_CONTRACT_v'+str(version)+'.json')
    write_new(contract_path, dict(schema='P107_DOCUMENT_CLI_CPU_V1', actual_exit=0, tests=30,
        source_pins=sources, raw_logs=[ref(raw_path)], cpu_run=ref(proof_path),
        model_checkpoint_loads=0, gpu_runs=0, corpus_training=False))
    manual = cli.manual.verify_manifest()
    value = dict(schema=cli.SCHEMA, tag=cli.TAG, authority_directive=107,
        deadline=cli.DEADLINE.isoformat(), model='native595-q', recipe=cli.RECIPE,
        profile_path=cli.PROFILE_PATH, source_pins=sources, purpose='SYNTHETIC_TECHNICAL',
        input_root=cli.INPUT_ROOT, input_manifest=ref(input_manifest), input_contract=packet.contract,
        output=cli.OUTPUT, snapshot=cli.SNAPSHOT, max_wall_sec=cli.MAX_WALL,
        allocator_cap_bytes=cli.ALLOCATOR, shared_gpu_increase_bytes=cli.VRAM_INCREASE,
        corpus_training=False, cpu_contract=ref(contract_path), smoke=ref(smoke_path),
        manual_manifest_sha256=cli.manual.canonical_sha(manual))
    cli.validate_profile_object(value, sources, datetime.now(timezone.utc))
    write_new(profile_path, value)
    print('[P107_PROFILE] '+json.dumps(dict(path=cli.PROFILE_PATH, sha256=cli.manual.file_sha(profile_path),
        documents=4, tokens=16388, cpu_tests=30, model_loads=0, gpu_runs=0)))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('cpu','prepare'))
    parser.add_argument('version', type=int)
    args = parser.parse_args()
    if not 1 <= args.version <= 9:
        raise ValueError('explicit small new revision required')
    raise SystemExit(cpu(args.version) if args.phase == 'cpu' else prepare(args.version))
