#!/usr/bin/env python3
"""Fresh-process read-only resume of the completed Stage5W synthetic boundary."""
from datetime import datetime,timezone
import gc
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import tinylm
import torch
from scripts import diag_p107_disk_resume as disk
from tinylm.train.boundary_store import load_complete

base=disk.old
DEADLINE=datetime(2026,11,1,6,0,tzinfo=timezone.utc)
SCHEMA='P107_FRESH_PROCESS_OLD_BOUNDARY_REPLAY_V1'
TAG='p107_process_resume_v1_20261101'
PROFILE=ROOT/'handoff/audit/nov01_afternoon/P107_PROCESS_PROFILE_v1.json'
CPU=ROOT/'handoff/audit/nov01_afternoon/P107_PROCESS_CPU_CONTRACT_v1.json'
OUTPUT=ROOT/'test_result/evidence'/TAG
PREVIOUS_PROFILE=ROOT/'handoff/audit/nov01_afternoon/P107_DISK_PROFILE_v1.json'
PREVIOUS_REPORT=ROOT/'test_result/evidence/p107_session_disk_v1_20261101/resume/report.json'
PREVIOUS_ROOT=ROOT/'handoff/audit/nov01_afternoon/P107_DISK_ACTUAL_ROOT_v1.json'
ARCHIVED_DEFAULT=ROOT/'handoff/audit/nov01_afternoon/adaptive_training_before_kd_v1.py'
base.OWN=base.OWN+('scripts/diag_p107_process_resume.py','scripts/test_p107_process_resume.py',
    'scripts/test_p107_causal_integration.py','scripts/test_p107_causal_teacher.py',
    'tinylm/train/causal_teacher.py','tinylm/train/trainer.py',
    str(ARCHIVED_DEFAULT.relative_to(ROOT)))
base.DEADLINE,base.SCHEMA,base.TAG=DEADLINE,SCHEMA,TAG


def reference(path):
    return dict(path=str(path.relative_to(ROOT)),sha256=base.resource.digest(path))


def check_historical_contract():
    previous=json.loads(PREVIOUS_PROFILE.read_text())
    original=previous['source']['files']
    different=[name for name,value in original.items() if base.resource.digest(ROOT/name)!=value]
    base.need(different==['tinylm/train/adaptive_training.py'],'only the proved optional KD hook may differ')
    base.need(base.resource.digest(ARCHIVED_DEFAULT)==original['tinylm/train/adaptive_training.py'],
        'exact old default source archive required')
    report=json.loads(PREVIOUS_REPORT.read_text())
    base.need(report['final_exit']==0 and report['resume_equivalence']=='EXACT'
        and report['physical_optimizer_updates']==6 and report['causal_kd'] is False,
        'completed no-KD predecessor required')
    root=json.loads(PREVIOUS_ROOT.read_text())
    base.need(root['actual_parent_exit']==0 and root['disk_payload_exact'] is True
        and root['snapshot_parts']==49,'independent previous readback required')
    return previous,report


def resume(model,initial,profile,budget,report):
    previous,original=check_historical_contract()
    stored=load_complete(ROOT/original['snapshot']['path'])
    base.need(disk.hashes(stored)==original['snapshot_saved_state_hashes'],'old disk payload changed')
    model.clear_quant();model.load_state_dict(initial,strict=True);model.train()
    # Keep the original source/schedule signature deliberately, guarded by the
    # archived default equivalence CPU test and this actual GPU state replay.
    session=disk.engine(model,previous)
    session.load_state_dict(stored)
    stored=None;gc.collect();torch.cuda.empty_cache()
    report.update(fresh_worker_pid=os.getpid(),previous_gpu_session=69640,
        predecessor_already_finished=True,reused_snapshot=original['snapshot']['path'],
        compatibility='V1_NONE_DEFAULT_EXACT_ARCHIVE_CPU_AND_NEW_GPU_REPLAY',
        explicit_source_contract=session.trainer.source.contract)
    report['resumed']=[]
    for _ in range(2):base.measured_update(session,budget,report['resumed'])
    final=session.state_dict()
    report['actual_hashes']=disk.hashes(final)
    report['expected_hashes']=original['expected_hashes']
    base.need(report['actual_hashes']==report['expected_hashes'],'fresh process full state differs')
    keys=('loss','masked_targets','causal_targets','schedule_lrs')
    base.need([{k:r[k] for k in keys} for r in report['resumed']]==
        [{k:r[k] for k in keys} for r in original['continued']],'fresh process loss/targets/LR differ')
    report.update(resume_equivalence='EXACT',physical_optimizer_updates=2,checkpoint_writes=0,
        separate_process_restart_test=True,power_loss_test=False,
        not_measured=['POWER_FAILURE','CORPUS_BIAS','FULL_TRAINING_QUALITY','PRODUCTION_CLI','GPU_KD_RESUME'])
    final=session=None;model.zero_grad(set_to_none=True);model.clear_quant();gc.collect();torch.cuda.empty_cache()


def prepare():
    previous,report=check_historical_contract()
    cpu=json.loads(CPU.read_text())
    base.need(cpu['actual_exit']==0 and cpu['gpu_runs']==0 and cpu['source']==base.identity(),
        'current CPU contracts required')
    base.need(not PROFILE.exists() and not OUTPUT.exists(),'fresh output only')
    value=dict(schema=SCHEMA,tag=TAG,authority_directive=105,deadline=DEADLINE.isoformat(),
        source=base.identity(),source_sha256=base.identity()['sha256'],
        native_reference=previous['native_reference'],previous_profile=reference(PREVIOUS_PROFILE),
        previous_report=reference(PREVIOUS_REPORT),previous_root=reference(PREVIOUS_ROOT),
        snapshot_manifest=reference(ROOT/report['snapshot']['path']/'manifest.json'),
        cpu_contract=reference(CPU),output=str(OUTPUT.relative_to(ROOT)),
        corpus_training=False,max_wall_sec=300,planned_optimizer_updates=2,checkpoint_writes=0,
        vram_limit_bytes=base.LIMIT,allocator_cap_bytes=base.ALLOCATOR_CAP)
    base.resource.write_new(PROFILE,value)
    print(json.dumps(dict(status='FRESH_PROCESS_REPLAY_PREPARED',sha256=base.resource.digest(PROFILE),
        source=value['source_sha256'],gpu_runs=0,checkpoint_writes=0)))
    return 0


def validate(args):
    value=base.resource.read_ref(dict(path=args.profile,sha256=args.profile_sha256))
    base.need(value['schema']==SCHEMA and value['tag']==TAG and value['authority_directive']==105
        and value['source']==base.identity() and value['deadline']==DEADLINE.isoformat()
        and value['output']==str(OUTPUT.relative_to(ROOT)) and value['corpus_training'] is False
        and value['checkpoint_writes']==0 and value['planned_optimizer_updates']==2
        and value['vram_limit_bytes']==base.LIMIT and value['allocator_cap_bytes']==base.ALLOCATOR_CAP
        and args.mode=='resume' and args.max_wall_sec==300,'fresh read-only replay contract required')
    base.need((DEADLINE-datetime.now(timezone.utc)).total_seconds()>420,'deadline reserve insufficient')
    for key in ('previous_profile','previous_report','previous_root','snapshot_manifest'):
        base.resource.read_ref(value[key])
    cpu=base.resource.read_ref(value['cpu_contract'])
    base.need(cpu['actual_exit']==0 and cpu['source']==base.identity(),'CPU source changed')
    base.need(base.resource.digest(base.resource.safe(cpu['raw']['path']))==cpu['raw']['sha256'],'CPU log changed')
    check_historical_contract()
    native=base.resource.read_ref(value['native_reference'])
    spec=next(x for x in native['models'] if x['id']=='native595-q')
    return value,native,spec


base.resume,base.validate=resume,validate
if __name__=='__main__':
    if sys.argv[1:]==['--prepare']:raise SystemExit(prepare())
    raise SystemExit(base.main())
