"""Preserve the first local-actual source/profile/raw failure before a repair."""
import hashlib
import json
from pathlib import Path

BASE=Path('handoff/audit/nov04_weight_space')
EVIDENCE=Path('test_result/evidence/p108_attenuation_v1_20261104/new595-broad-q')


def main():
    output=BASE/'ATTENUATION_FIRST_FAILURE_v1.json'
    if output.exists():raise FileExistsError(output)
    profile=EVIDENCE/'gpu_profile.json'
    value=json.loads(profile.read_text(encoding='utf-8'))
    names=['scripts/diag_p108_attenuation_gpu.py','scripts/test_p108_attenuation_gpu.py']
    records=[]
    for name in names:
        raw=Path(name).read_bytes();digest=hashlib.sha256(raw).hexdigest().upper()
        if value['source_pins'][name]!=digest:raise ValueError('first executed source changed')
        blob=BASE/'source_blobs'/(digest+'.txt')
        if blob.exists():
            if blob.read_bytes()!=raw:raise ValueError('hash-addressed blob differs')
        else:
            with blob.open('xb') as stream:stream.write(raw)
        records.append(dict(path=name,sha256=digest,bytes=len(raw),blob=str(blob)))
    log=Path('test_result/108_log_20261104_P108_Stage6bW_calibration_local_actual.txt')
    raw=log.read_bytes()
    if b'owned CUDA allocation did not return to zero' not in raw or b'[BODY_UNCHANGED]' not in raw:
        raise ValueError('expected original raw failure absent')
    result=dict(schema='P108_LOCAL_ACTUAL_FIRST_FAILURE_V1',stage='Stage6bW',actual_exit=1,
        executed_calibration_rows=4,full_report_written=False,completed_scientific_verdict=False,
        profile=dict(path=str(profile),sha256=hashlib.sha256(profile.read_bytes()).hexdigest().upper()),
        log=dict(path=str(log),sha256=hashlib.sha256(raw).hexdigest().upper(),bytes=len(raw)),
        archived_sources=records,
        observed='Original core and logits restored; owned allocator cleanup check failed.',
        cause_before_new_measurement='Suspected retained cuBLAS workspace; ordinary cleanup omitted the existing close_cuda helper.',
        new_phase_must_preserve_this_failure=True,original_log_writes=0,checkpoint_writes=0)
    with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2);stream.write(chr(10))
    print(json.dumps(dict(path=str(output),actual_exit=1,archived_sources=len(records))))


if __name__=='__main__':main()
