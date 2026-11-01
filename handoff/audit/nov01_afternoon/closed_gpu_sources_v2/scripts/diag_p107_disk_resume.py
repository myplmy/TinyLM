#!/usr/bin/env python3
"""Opt-in Native synthetic documents plus scheduled, sharded disk resume."""
from datetime import datetime,timezone
import gc
import json
import random
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import tinylm
import numpy as np
import torch
from scripts import diag_p107_adaptive_training as old
from scripts.p106b_nvml_probe import watcher_class
from tinylm.train.adaptive_masking import PolicyConfig
from tinylm.train.adaptive_training import AdaptiveMNTPTrainer
from tinylm.train.document_source import ExplicitDocumentSource
from tinylm.train.hybrid_session import HybridTrainingSession
from tinylm.train.boundary_store import save_new,load_complete

DEADLINE=datetime(2026,11,1,6,0,tzinfo=timezone.utc)
TAG='p107_session_disk_v1_20261101'
SCHEMA='P107_EXPLICIT_DOCUMENT_DISK_RESUME_V1'
PROFILE=ROOT/'handoff/audit/nov01_afternoon/P107_DISK_PROFILE_v1.json'
SNAPSHOT=ROOT/'runs/isolated'/TAG/'boundary_u2'
OUTPUT=ROOT/'test_result/evidence'/TAG
old.OWN=old.OWN+('tinylm/train/document_source.py','tinylm/train/hybrid_session.py',
    'tinylm/train/boundary_store.py','tinylm/train/anneal_schedule.py',
    'scripts/diag_p107_disk_resume.py','scripts/test_p107_disk_resume_driver.py',
    'scripts/test_p107_session_boundary.py','scripts/p106b_nvml_probe.py')
old.DEADLINE,old.SCHEMA,old.TAG=DEADLINE,SCHEMA,TAG
old.VramWatch=watcher_class()


def engine(model,profile):
    torch.manual_seed(1337);torch.cuda.manual_seed_all(1337)
    random.seed(1337);np.random.seed(1337)
    generator=torch.Generator(device='cpu').manual_seed(20261101)
    docs=[torch.randint(35,32768,(4097,),generator=generator) for _ in range(4)]
    source=ExplicitDocumentSource(docs,['synthetic-'+str(i) for i in range(4)],
        batch=8,length=1024,micros=16,vocab=32768,seed=1337)
    config=PolicyConfig(32768,.15,.2,2,'keep',1337,34,13,source.corpus_sha256,profile['source_sha256'])
    trainer=AdaptiveMNTPTrainer(model,old.optimizers(model),source,policy_config=config,
        mode='adaptive',masked_micros=8,signature=old.resource.sha(dict(source=source.signature,run=profile['source_sha256'])),
        collect_ids=lambda logits,targets:old.collect_ids(logits,targets,'full')[0],
        autocast_dtype=torch.bfloat16,clip=1.)
    return HybridTrainingSession(trainer,total_updates=8,warmup_updates=2,schedule='cosine')


def hashes(state):
    return {key:old.tree_sha(value) for key,value in state.items()}


def resume(model,initial,profile,budget,report):
    model.clear_quant();model.load_state_dict(initial,strict=True);model.train()
    session=engine(model,profile)
    report['explicit_source_contract']=session.trainer.source.contract
    report['prefix']=[]
    for _ in range(2):old.measured_update(session,budget,report['prefix'])
    budget.check();at=time.perf_counter()
    saved=session.state_dict()
    report['snapshot_saved_state_hashes']=hashes(saved)
    stored=save_new(saved,SNAPSHOT)
    report['snapshot']=dict(path=str(SNAPSHOT.relative_to(ROOT)),manifest=stored,
        full_save_seconds=time.perf_counter()-at,context='RESEARCH_SYNTHETIC_RESUME_ONLY_NOT_DEPLOY_MODEL')
    saved=None;gc.collect();budget.check()
    report['continued']=[]
    for _ in range(2):old.measured_update(session,budget,report['continued'])
    end=session.state_dict();report['expected_hashes']=hashes(end);end=None
    session=None;model.zero_grad(set_to_none=True);model.clear_quant();gc.collect();torch.cuda.empty_cache()
    budget.check();at=time.perf_counter()
    restored=load_complete(SNAPSHOT)
    old.need(hashes(restored)==report['snapshot_saved_state_hashes'],'디스크 payload가 저장 상태와 다름')
    session=engine(model,profile)
    session.load_state_dict(restored)
    report['disk_load_and_restore_seconds']=time.perf_counter()-at
    restored=None;gc.collect();torch.cuda.empty_cache()
    report['resumed']=[]
    for _ in range(2):old.measured_update(session,budget,report['resumed'])
    end=session.state_dict();report['actual_hashes']=hashes(end);end=None
    old.need(report['actual_hashes']==report['expected_hashes'],'스케줄 포함 전체 재개가 다름')
    compare=('loss','masked_targets','causal_targets','schedule_lrs')
    old.need([{k:r[k] for k in compare} for r in report['continued']]==
        [{k:r[k] for k in compare} for r in report['resumed']],'재개 후 loss/target/LR가 다름')
    report.update(resume_equivalence='EXACT',physical_optimizer_updates=6,
        checkpoint_writes=1,checkpoint_payload_parts=len(stored['parts']),corpus_training=False,
        fresh_optimizer_source_session=True,same_model_object_reloaded=True,
        separate_process_or_power_loss_test=False,production_cli_complete=False,causal_kd=False)
    report['not_measured']=['CORPUS_BIAS','FULL_TRAINING_QUALITY','PRODUCTION_LOADER_CLI',
        'GRADSCALER_COMPILE','CAUSAL_KD','SEPARATE_PROCESS_POWER_FAILURE']
    session=None;model.zero_grad(set_to_none=True);model.clear_quant();gc.collect();torch.cuda.empty_cache()


def prepare():
    legacy=json.loads((ROOT/'handoff/audit/nov01_independent/p107_training_profile_v1.json').read_text())
    native=old.resource.read_ref(legacy['native_reference'])
    spec=next(x for x in native['models'] if x['id']=='native595-q')
    old.need(spec['route']=='ternary' and spec['cfg']['grad_checkpoint'] is True,'원 Native 경로 필요')
    receipt=ROOT/'handoff/audit/nov01_afternoon/P107_CPU_CONTRACT_v1.json'
    cpu=json.loads(receipt.read_text())
    old.need(cpu['actual_exit']==0 and cpu['tests']==15 and cpu['source']==old.identity()
        and cpu['gpu_runs']==0,'같은 소스의 실제 CPU15 회귀 필요')
    raw=old.resource.read_ref(cpu['raw'])
    old.need(raw['tests']==15 and raw['actual_exit']==0,'CPU 원로그 영수증 필요')
    log=old.resource.safe(raw['log']['path'])
    old.need(old.resource.digest(log)==raw['log']['sha256'] and 'Ran 15 tests' in log.read_text()
        and log.read_text().rstrip().endswith('OK'),'CPU15 원로그 변형')
    old.need(not PROFILE.exists() and not OUTPUT.exists() and not SNAPSHOT.exists(),'새 출력만 허용')
    value=dict(schema=SCHEMA,tag=TAG,authority_directive=105,deadline=DEADLINE.isoformat(),
        source_sha256=old.identity()['sha256'],source=old.identity(),native_reference=legacy['native_reference'],
        cpu_contracts=[dict(path=str(receipt.relative_to(ROOT)),sha256=old.resource.digest(receipt)),cpu['raw']],
        output=str(OUTPUT.relative_to(ROOT)),snapshot=str(SNAPSHOT.relative_to(ROOT)),
        max_wall_sec=900,corpus_training=False,planned_optimizer_updates=6,planned_checkpoint_snapshots=1,
        model_loads=0,gpu_runs=0,
        saved_payload_part_limit=16_000_000,recipe=dict(micro=8,accum=16,seq=1024,causal_micros=8,masked_micros=8,
            scheduler='cosine',warmup=2,horizon=8,grad_checkpoint=True,teacher=None,compile=False),
        vram_limit_bytes=old.LIMIT,allocator_cap_bytes=old.ALLOCATOR_CAP)
    old.resource.write_new(PROFILE,value)
    print(json.dumps(dict(status='FRESH_DISK_TECHNICAL_CONTRACT',profile_sha256=old.resource.digest(PROFILE),
        source=value['source_sha256'],gpu=0,model_loads=0)))
    return 0


def validate(args):
    value=old.resource.read_ref(dict(path=args.profile,sha256=args.profile_sha256))
    old.need(value['schema']==SCHEMA and value['tag']==TAG and value['authority_directive']==105
        and value['deadline']==DEADLINE.isoformat() and value['source']==old.identity()
        and value['output']==str(OUTPUT.relative_to(ROOT)) and value['snapshot']==str(SNAPSHOT.relative_to(ROOT))
        and value['corpus_training'] is False and args.mode=='resume' and args.max_wall_sec==900,'새 서명·동작·경계 필요')
    old.need((DEADLINE-datetime.now(timezone.utc)).total_seconds()>1020,'마감 예비 부족')
    old.need(not SNAPSHOT.exists(),'이전 snapshot·부분 출력은 보존한다')
    for item in value['cpu_contracts']:old.resource.read_ref(item)
    native=old.resource.read_ref(value['native_reference'])
    spec=next(x for x in native['models'] if x['id']=='native595-q')
    old.need(spec['cfg']['vocab_size']==32768 and spec['cfg']['grad_checkpoint'] is True,'고정 native cfg 필요')
    return value,native,spec


old.resume,old.validate=resume,validate

if __name__=='__main__':
    if sys.argv[1:]==['--prepare']:
        raise SystemExit(prepare())
    raise SystemExit(old.main())
