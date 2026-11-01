"""CPU-only independent readback of the new worker and immutable old snapshot."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[3]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    profile=ROOT/'handoff/audit/nov01_afternoon/P107_PROCESS_PROFILE_v1.json'
    report=ROOT/'test_result/evidence/p107_process_resume_v1_20261101/resume/report.json'
    p=json.loads(profile.read_text());r=json.loads(report.read_text())
    old=json.loads((ROOT/p['previous_report']['path']).read_text())
    assert r['status']=='COMPLETE' and r['final_exit']==0 and r['resume_equivalence']=='EXACT'
    assert r['separate_process_restart_test'] is True and r['power_loss_test'] is False
    assert type(r['fresh_worker_pid']) is int and r['fresh_worker_pid']>0
    assert r['previous_gpu_session']==69640 and r['predecessor_already_finished'] is True
    assert r['actual_hashes']==r['expected_hashes']==old['expected_hashes']
    keys=('loss','masked_targets','causal_targets','schedule_lrs')
    assert [{k:x[k] for k in keys} for x in r['resumed']]==[{k:x[k] for k in keys} for x in old['continued']]
    assert len(r['resumed'])==2 and r['completed_optimizer_updates']==r['physical_optimizer_updates']==2
    assert sum(x['executed_input_tokens'] for x in r['resumed'])==262144
    assert not r['unfinished_update_records'] and r['checkpoint_writes']==0 and r['quality_claim'] is False
    for item in ('previous_profile','previous_report','previous_root','snapshot_manifest'):
        assert sha(ROOT/p[item]['path'])==p[item]['sha256']
    snapshot=ROOT/r['reused_snapshot'];m=json.loads((snapshot/'manifest.json').read_text())
    whole=hashlib.sha256()
    assert len(m['parts'])==49 and m['bytes']==781352215
    for part in m['parts']:
        data=(snapshot/part['path']).read_bytes()
        assert len(data)==part['bytes'] and hashlib.sha256(data).hexdigest().upper()==part['sha256']
        whole.update(data)
    assert whole.hexdigest().upper()==m['sha256']
    assert r['source']==p['source'] and r['source_unchanged'] and r['parent_unchanged']
    for name,value in p['source']['files'].items():assert sha(ROOT/name)==value
    assert r['final_cuda_cleanup']['allocated_bytes']==r['final_cuda_cleanup']['reserved_bytes']==0
    assert r['vram_watch']['query_errors']==0 and r['vram_watch']['client']['closed']
    assert r['vram_watch']['thread_stopped'] and r['vram_watch']['reason'] is None
    raw=ROOT/'test_result/107_log_20261101_P107_Stage7W_fresh_process_disk_resume.txt'
    assert 'actual_exit=0' in raw.read_text()
    result=dict(schema='P107_FRESH_PROCESS_ROOT_V1',actual_exit=0,actual_gpu_session=84306,
        worker_pid=r['fresh_worker_pid'],input_positions=262144,optimizer_updates=2,
        full_state_exact=True,loss_target_lr_exact=True,old_49_parts_unchanged=True,
        current_source_unchanged=True,original_parent_unchanged=True,checkpoint_writes=0,
        quality_claim=False,power_loss_test=False,gpu_runs_here=0,
        report=dict(path=str(report.relative_to(ROOT)),sha256=sha(report)),
        raw=dict(path=str(raw.relative_to(ROOT)),sha256=sha(raw)))
    output=ROOT/'handoff/audit/nov01_afternoon/P107_PROCESS_ACTUAL_ROOT_v1.json'
    with output.open('x') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result))
    return 0


if __name__=='__main__':raise SystemExit(main())
