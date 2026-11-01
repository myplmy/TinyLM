"""CPU-only post-run auditing of this session's four possible full evaluations."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).parent
EVAL = ROOT/'data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python'
DEADLINE = datetime(2026,11,1,2,0,tzinfo=timezone.utc).timestamp()
os.environ.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
    OPENBLAS_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',
    HF_DATASETS_OFFLINE='1',TRANSFORMERS_OFFLINE='1',USE_HUB_KERNELS='0')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def tasks():
    result = []
    for alias,model,suffix in [('native','native595-q','Wa'),('broad','new595-broad-q','Wb')]:
        base = ROOT/'test_result/evidence/p106b_gsm8k_nvml_v1_20261101'
        result.append(dict(name='gsm8k_'+alias,script='gsm8k_root_readback_v1.py',argument=alias,
            report=base/model/'full/report.json',output=base/'readback'/('gsm8k_'+alias+'_full_readback_v1.json'),
            raw=ROOT/('test_result/101_log_20261101_P106B_Stage8z'+suffix+'_gsm8k_'+alias+'_full.txt')))
    for shot,suffix in [(0,'Wc'),(5,'Wd')]:
        base = ROOT/'test_result/evidence/p106b_falcon_mmlu_v3_20261101'
        result.append(dict(name='mmlu_falcon'+str(shot),script='falcon_mmlu_root_readback_v1.py',argument=str(shot),
            report=base/('shot'+str(shot))/'full/report.json',
            output=base/'readback'/('mmlu_falcon'+str(shot)+'_full_readback_v1.json'),
            raw=ROOT/('test_result/101_log_20261101_P106B_Stage14c'+suffix+'_mmlu_falcon'+str(shot)+'_full.txt')))
    return result


def main():
    receipt = AUDIT/'COMPLETED_BENCHMARK_CPU_READBACKS_v1.json'
    assert not receipt.exists()
    work = tasks()
    identities = {t['script']:digest(AUDIT/t['script']) for t in work}
    records = {}
    for t in work:
        assert not t['output'].exists(), 'Preserve existing root evidence; use another version.'
    next_progress = 0
    while time.time()<DEADLINE-60:
        for t in work:
            if t['name'] in records or not t['report'].is_file():
                continue
            report = json.loads(t['report'].read_text())
            if report.get('final_exit')!=0:
                records[t['name']] = dict(status='NOT_AUDITED_RUN_FAILED_OR_HELD',worker_exit=report.get('final_exit'))
                continue
            if not t['raw'].is_file() or 'actual_exit=0;' not in t['raw'].read_text():
                continue
            remaining = DEADLINE-time.time()-60
            if remaining<120:
                continue
            assert digest(AUDIT/t['script'])==identities[t['script']]
            started = time.monotonic()
            command = [str(EVAL),'-B','-X','utf8',str(AUDIT/t['script']),t['argument']]
            raw = AUDIT/(t['name']+'_automatic_root_v1.log')
            assert not raw.exists()
            try:
                completed = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=min(600,remaining))
                code,stdout,stderr = completed.returncode,completed.stdout,completed.stderr
            except subprocess.TimeoutExpired as exc:
                code = 124
                stdout = exc.stdout.decode(errors='replace') if isinstance(exc.stdout,bytes) else exc.stdout or ''
                stderr = exc.stderr.decode(errors='replace') if isinstance(exc.stderr,bytes) else exc.stderr or ''
            with raw.open('x',encoding='utf-8') as f:
                f.write(stdout);f.write(stderr)
            record = dict(status='ROOT_COMPLETE' if code==0 else 'ROOT_ERROR',actual_exit=code,
                raw_log=str(raw.relative_to(ROOT)),raw_log_sha256=digest(raw),
                seconds=time.monotonic()-started,auditor_sha256=identities[t['script']])
            if code==0:
                assert t['output'].is_file() and not json.loads(t['output'].read_text())['errors']
                record.update(output=str(t['output'].relative_to(ROOT)),output_sha256=digest(t['output']))
            records[t['name']] = record
            print(json.dumps(dict(event='CPU_ROOT_FINISHED',name=t['name'],record=record)),flush=True)
        queue = AUDIT/'FALCON_QUEUE_RECEIPT_v2.json'
        if queue.is_file():
            for t in work:
                if t['name'] not in records and not t['report'].exists():
                    records[t['name']] = dict(status='NOT_RUN_FULL_WORKER',actual_exit=None)
        if len(records)==len(work):
            break
        if time.time()>=next_progress:
            print(json.dumps(dict(event='CPU_ROOT_WAIT',closed=sorted(records),
                remaining_seconds=int(DEADLINE-time.time()))),flush=True)
            next_progress = time.time()+60
        time.sleep(10)
    for t in work:
        records.setdefault(t['name'],dict(status='NOT_AUDITED_BY_DEADLINE',actual_exit=None))
    payload = dict(schema='COMPLETED_BENCHMARK_CPU_READBACKS_V1',records=records,
        created_at=datetime.now(timezone.utc).isoformat(),model_runs=0,gpu_runs=0,
        source_hashes=identities,quality_gain_claim=False)
    with receipt.open('x') as f:json.dump(payload,f,ensure_ascii=False,indent=2)
    failures = [name for name,r in records.items() if r['status']=='ROOT_ERROR']
    print(json.dumps(dict(event='CPU_READBACK_CONTROLLER_CLOSED',records=records,errors=failures)),flush=True)
    return int(bool(failures))


if __name__=='__main__':
    raise SystemExit(main())
