#!/usr/bin/env python3
"""Bounded full-shape causal-KL connection cost, synthetic documents only."""
from datetime import datetime,timezone
import copy
import gc
import json
from pathlib import Path
import random
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import tinylm
import numpy as np
import torch
from scripts import diag_p107_adaptive_training as base
from scripts.p106b_nvml_probe import watcher_class
from tinylm.model import TiedMLPTransformer
from tinylm.train.adaptive_masking import PolicyConfig
from tinylm.train.adaptive_training import AdaptiveMNTPTrainer
from tinylm.train.causal_teacher import CausalTeacherKL
from tinylm.train.document_source import ExplicitDocumentSource
from tinylm.train.hybrid_session import HybridTrainingSession

DEADLINE=datetime(2026,11,1,6,0,tzinfo=timezone.utc)
TAG='p107_causal_kd_cost_v1_20261101'
SCHEMA='P107_CAUSAL_KD_FULL_SHAPE_TECHNICAL_COST_V1'
PROFILE=ROOT/'handoff/audit/nov01_afternoon/P107_KD_PROFILE_v1.json'
CPU=ROOT/'handoff/audit/nov01_afternoon/P107_KD_CPU_CONTRACT_v1.json'
OUTPUT=ROOT/'test_result/evidence'/TAG
LIMIT=14_000_000_000
ALLOCATOR_CAP=12*2**30
ORDER=('none','causal_kl','causal_kl','none')
base.OWN=base.OWN+('tinylm/train/document_source.py','tinylm/train/hybrid_session.py',
    'tinylm/train/anneal_schedule.py','tinylm/train/causal_teacher.py','tinylm/train/trainer.py',
    'scripts/test_p107_causal_teacher.py','scripts/test_p107_causal_integration.py',
    'scripts/test_p107_causal_kd_driver.py','scripts/diag_p107_causal_kd_cost.py',
    'scripts/p106b_nvml_probe.py')
base.DEADLINE,base.SCHEMA,base.TAG=DEADLINE,SCHEMA,TAG
base.LIMIT,base.ALLOCATOR_CAP=LIMIT,ALLOCATOR_CAP
PersistentWatch=watcher_class()


class KdWatch(PersistentWatch):
    def stop(self):
        proof=super().stop()
        proof['policy']['shared_increment_limit_bytes']=LIMIT
        return proof


base.VramWatch=KdWatch


def engine(model,teacher,mode,profile):
    torch.manual_seed(1337);torch.cuda.manual_seed_all(1337)
    random.seed(1337);np.random.seed(1337)
    generator=torch.Generator().manual_seed(20261101)
    docs=[torch.randint(35,32768,(4097,),generator=generator) for _ in range(4)]
    source=ExplicitDocumentSource(docs,['synthetic-'+str(i) for i in range(4)],
        batch=8,length=1024,micros=16,vocab=32768,seed=1337)
    config=PolicyConfig(32768,.15,.2,2,'keep',1337,34,13,source.corpus_sha256,profile['source_sha256'])
    kd=None
    if mode=='causal_kl':
        kd=CausalTeacherKL(teacher,vocab_size=32768,
            student_tokenizer_sha256=profile['tokenizer_sha256'],
            teacher_tokenizer_sha256=profile['tokenizer_sha256'],
            teacher_identity_sha256=profile['native_core_sha256'],
            coefficient=.1,temperature=1.,chunk_rows=256)
    trainer=AdaptiveMNTPTrainer(model,base.optimizers(model),source,policy_config=config,
        mode='adaptive',masked_micros=8,
        signature=base.resource.sha(dict(source=profile['source_sha256'],kd=mode)),
        collect_ids=lambda logits,targets:base.collect_ids(logits,targets,'full')[0],
        autocast_dtype=torch.bfloat16,clip=1.,causal_distillation=kd)
    return HybridTrainingSession(trainer,total_updates=8,warmup_updates=2,schedule='cosine')


def cost(model,initial,profile,budget,report):
    from scripts.interactive_research_infer import state_fingerprint
    teacher=None
    report['blocks']=[]
    report.update(teacher_quality_claim=False,teacher_kind='FROZEN_NATIVE_SAME_VOCAB_TECHNICAL_CONTROL',
        checkpoint_writes=0,not_measured=['TEACHER_KNOWLEDGE_GAIN','CROSS_TOKENIZER_KD',
            'CORPUS_BIAS','FULL_TRAINING_QUALITY','PRODUCTION_CLI','KD_GPU_RESUME'])
    try:
        torch.cuda.synchronize();allocated_before=torch.cuda.memory_allocated();at=time.perf_counter()
        teacher=TiedMLPTransformer(copy.deepcopy(model.cfg))
        teacher.load_state_dict(initial,strict=True)
        teacher.to('cuda').eval().requires_grad_(False)
        teacher.clear_quant();teacher.set_anneal(1.)
        torch.cuda.synchronize()
        report['teacher_load']=dict(seconds=time.perf_counter()-at,
            allocated_increment_bytes=torch.cuda.memory_allocated()-allocated_before,
            parameters=sum(p.numel() for p in teacher.parameters()),
            comparison_memory_scope='BOTH_ARMS_KEEP_THE_SAME_FROZEN_TEACHER_RESIDENT')
        before=state_fingerprint(teacher)
        base.need(before==profile['native_core_sha256'],'teacher core differs from declared parent')
        report['teacher_initial_core_sha256']=before
        for index,mode in enumerate(ORDER):
            model.clear_quant();model.load_state_dict(initial,strict=True);model.train()
            teacher.clear_quant()
            session=engine(model,teacher,mode,profile)
            block=dict(index=index,mode=mode,attempts=[])
            report['blocks'].append(block)
            for _ in range(4):
                row=base.measured_update(session,budget,block['attempts'])
                base.need(row.get('teacher_forwards',0)==(8 if mode=='causal_kl' else 0),
                    'teacher calls escaped causal batch boundary')
                base.need(all(p.grad is None for p in teacher.parameters()),'teacher received gradients')
            state=session.state_dict()
            block['final_equivalence']={key:base.tree_sha(state['trainer'][key])
                for key in ('model','optimizers','policy','source','rng')}
            block['losses']=[r['loss'] for r in block['attempts']]
            block['median_seconds']=statistics.median(r['seconds'] for r in block['attempts'][1:])
            block['teacher_core_sha256']=state_fingerprint(teacher)
            base.need(block['teacher_core_sha256']==before,'frozen teacher changed')
            print(json.dumps(dict(block=index,mode=mode,median_seconds=block['median_seconds'],
                peak_reserved_bytes=max(r['peak_reserved_bytes'] for r in block['attempts']))),flush=True)
            state=session=None
            model.zero_grad(set_to_none=True);model.clear_quant();gc.collect();torch.cuda.empty_cache()
        for mode in set(ORDER):
            pair=[b for b in report['blocks'] if b['mode']==mode]
            base.need(pair[0]['final_equivalence']==pair[1]['final_equivalence']
                and pair[0]['losses']==pair[1]['losses'],'repeated matched block differs')
        report['summary']={mode:dict(median_seconds=statistics.median(r['seconds']
            for b in report['blocks'] if b['mode']==mode for r in b['attempts'][1:]),
            peak_reserved_bytes=max(r['peak_reserved_bytes'] for b in report['blocks']
                if b['mode']==mode for r in b['attempts']),measured_updates=6,warm_updates=2)
            for mode in set(ORDER)}
        report.update(physical_optimizer_updates=16,teacher_forwards=64,repeated_trajectories='EXACT',
            teacher_final_core_sha256=state_fingerprint(teacher))
    finally:
        if teacher is not None:
            report['teacher_final_core_sha256']=state_fingerprint(teacher)
            report['teacher_unchanged']=report['teacher_final_core_sha256']==profile['native_core_sha256']
            teacher.clear_quant();teacher.zero_grad(set_to_none=True);teacher.to('cpu')
        teacher=None;gc.collect();torch.cuda.empty_cache()


def prepare():
    legacy=json.loads((ROOT/'handoff/audit/nov01_independent/p107_training_profile_v1.json').read_text())
    native=base.resource.read_ref(legacy['native_reference'])
    spec=next(x for x in native['models'] if x['id']=='native595-q')
    cpu=json.loads(CPU.read_text())
    base.need(cpu['actual_exit']==0 and cpu['source']==base.identity() and cpu['gpu_runs']==0,
        'current CPU integration contract required')
    base.need(not PROFILE.exists() and not OUTPUT.exists(),'new outputs only')
    value=dict(schema=SCHEMA,tag=TAG,authority_directive=105,deadline=DEADLINE.isoformat(),
        source=base.identity(),source_sha256=base.identity()['sha256'],native_reference=legacy['native_reference'],
        native_core_sha256=spec['core_sha256'],tokenizer_sha256=native['tokenizer']['sha256'],
        cpu_contract=dict(path=str(CPU.relative_to(ROOT)),sha256=base.resource.digest(CPU)),
        output=str(OUTPUT.relative_to(ROOT)),max_wall_sec=900,corpus_training=False,
        checkpoint_writes=0,planned_optimizer_updates=16,order=list(ORDER),
        vram_limit_bytes=LIMIT,allocator_cap_bytes=ALLOCATOR_CAP,
        recipe=dict(micro=8,accum=16,seq=1024,causal_micros=8,masked_micros=8,
            scheduler='cosine',warmup=2,horizon=8,grad_checkpoint=True,compile=False,
            kl_coefficient=.1,temperature=1.,chunk_rows=256))
    base.resource.write_new(PROFILE,value)
    print(json.dumps(dict(status='PREPARED_CPU_ONLY',sha256=base.resource.digest(PROFILE),
        source=value['source_sha256'],model_loads=0,gpu_runs=0)))
    return 0


def validate(args):
    value=base.resource.read_ref(dict(path=args.profile,sha256=args.profile_sha256))
    base.need(value['schema']==SCHEMA and value['tag']==TAG and value['authority_directive']==105
        and value['deadline']==DEADLINE.isoformat() and value['source']==base.identity()
        and value['output']==str(OUTPUT.relative_to(ROOT)) and value['corpus_training'] is False
        and value['vram_limit_bytes']==LIMIT and value['allocator_cap_bytes']==ALLOCATOR_CAP
        and value['planned_optimizer_updates']==16 and value['checkpoint_writes']==0
        and value['order']==list(ORDER) and args.mode=='cost' and args.max_wall_sec==900,
        'fresh full-shape technical contract required')
    base.need((DEADLINE-datetime.now(timezone.utc)).total_seconds()>1020,'deadline reserve insufficient')
    cpu=base.resource.read_ref(value['cpu_contract'])
    base.need(cpu['actual_exit']==0 and cpu['source']==base.identity(),'CPU source differs')
    base.need(base.resource.digest(base.resource.safe(cpu['raw']['path']))==cpu['raw']['sha256'],
        'CPU raw log differs')
    native=base.resource.read_ref(value['native_reference'])
    spec=next(x for x in native['models'] if x['id']=='native595-q')
    base.need(spec['cfg']['vocab_size']==32768 and spec['cfg']['grad_checkpoint'] is True
        and spec['route']=='ternary' and spec['core_sha256']==value['native_core_sha256']
        and native['tokenizer']['sha256']==value['tokenizer_sha256'],'native/tokenizer mismatch')
    return value,native,spec


base.cost,base.validate=cost,validate
if __name__=='__main__':
    if sys.argv[1:]==['--prepare']:raise SystemExit(prepare())
    raise SystemExit(base.main())
