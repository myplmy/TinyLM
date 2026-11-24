#!/usr/bin/env python3
"""Real float TinyLM boundary/resume admission on explicit synthetic inputs.

Nine optimizer updates verify the protocol, not language quality or training
efficiency. The original parent is restored and all snapshots stay in RAM.
"""
import argparse
import gc
import json
import time
import traceback
import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_policy as packets
from scripts import p108b_boundary as boundary
from scripts import diag_p107_adaptive_training as owner
from scripts import interactive_research_infer as manual
from scripts import p108_wsp_attention as outputs
from tinylm.train.adaptive_training import AdaptiveMNTPTrainer,SyntheticDocumentStream,cpu_copy
from tinylm.train.adaptive_masking import PolicyConfig

BASE=atlas.BASE
OUT=BASE/'boundary_gpu_v3'
PROFILE=BASE/'boundary_gpu_profile_v3.json'
INITIAL=BASE/'boundary_gpu_initial_plan_v3.md'
CODE=('scripts/diag_p108b_boundary_gpu.py','scripts/test_p108b_boundary_gpu.py',
      'scripts/p108b_boundary.py','scripts/test_p108b_boundary.py',
      'scripts/diag_p107_adaptive_training.py','tinylm/train/adaptive_training.py',
      'tinylm/train/adaptive_masking.py','tinylm/train/hybrid_mntp.py',
      'tinylm/train/muon.py','tinylm/train/optimizer_audit.py')


def refresh_route(model,route):
    route.assert_active();model.clear_quant()
    if not model.training:
        with torch.no_grad():model.freeze_quant()
    route.assert_active()


def native_config(cfg,mode):
    if mode!='float' or cfg.mtp_aux or cfg.n_layers!=14:
        raise ValueError('strict original float14/MTPoff boundary admission required')
    return dict(layers=cfg.n_layers,max_seq_len=cfg.max_seq_len,grad_checkpoint=cfg.grad_checkpoint,
        mtp_aux=cfg.mtp_aux,route=mode,precision='FP32_MATH_EAGER')


def prepare():
    p=atlas.verify();path=BASE/'geometry/layer09_packet.npz'
    library.write_new(PROFILE,dict(schema='P108B_REAL_BOUNDARY_GPU_V3',model=p['model'],origin=p['origin'],
        sources={name:manual.file_sha(atlas.ROOT/name)for name in CODE},packet_path=str(path.relative_to(atlas.ROOT)),
        packet_sha256=manual.file_sha(path),proposal_scale=.01,synthetic_source=dict(batch=2,length=64,micros=2,vocab=32768,seed=20261116),
        policies=['keep','reset_changed'],max_seconds=900,expected_optimizer_updates=9,expected_input_slots=2304,
        scope='ACTUAL_FLOAT14_SYNTHETIC_BOUNDARY_PROTOCOL_ONLY_NOT_LANGUAGE_QUALITY',checkpoint_writes=0,
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN)))
    with INITIAL.open('xb')as f:f.write((atlas.ROOT/library.PLAN).read_bytes())
    print('[BOUNDARY_GPU_PREPARED] nine synthetic updates; no model/GPU yet',flush=True)


def verify():
    atlas.verify();p=json.loads(PROFILE.read_text(encoding='utf-8'))
    for name,sha in p['sources'].items():
        if manual.file_sha(atlas.ROOT/name)!=sha:raise ValueError('boundary GPU source changed: '+name)
    if manual.file_sha(atlas.ROOT/p['packet_path'])!=p['packet_sha256']:raise ValueError('frozen delta changed')
    if manual.file_sha(INITIAL)!=p['initial_plan_sha256']:raise ValueError('boundary initial plan changed')
    return p


def engine(model,profile):
    source=SyntheticDocumentStream(**profile['synthetic_source']);signature=manual.canonical_sha(profile)
    config=PolicyConfig(32768,.15,.2,2,'keep',1337,34,13,manual.canonical_sha(source.state_dict()),signature)
    return AdaptiveMNTPTrainer(model,owner.optimizers(model),source,policy_config=config,mode='uniform',
        masked_micros=1,signature=signature,autocast_dtype=None,clip=1.)


def actual():
    p=verify();resources=library.resources();budget=library.Budget(p['max_seconds'])
    if OUT.exists():raise FileExistsError('preserve prior real boundary attempt')
    OUT.mkdir();started=time.monotonic();torch.set_num_threads(4);torch.manual_seed(1337)
    report=dict(schema=p['schema'],scope=p['scope'],status='STARTED',arms=[],checkpoint_writes=0,
        source_profile_sha256=manual.file_sha(PROFILE),entry_resources=resources,physical_optimizer_updates=0,
        physical_input_slots=0,physical_supervised_targets=0,validation_forwards=0)
    active=model=trainer=controller=parameter=probe=None;failure=None
    original=common=saved=end_state=None
    try:
        with manual.selected_runtime(manual.resolve_model(p['model']))as active,sdpa_kernel(SDPBackend.MATH):
            model=active['model'];original=cpu_copy(model.state_dict());was_training=model.training
            flags={n:v.requires_grad for n,v in model.named_parameters()}
            report['native_cfg']=native_config(active['cfg'],active['route'].mode)
            probe=torch.tensor([[35,36,37,38,39,40,41,42]],device='cuda')
            def refresh(body):refresh_route(body,active['route'])
            def update():
                budget.check();row=controller.update();report['physical_optimizer_updates']+=1
                report['physical_input_slots']+=row['executed_input_tokens']
                report['physical_supervised_targets']+=row['causal_targets']+row['masked_targets']
                return {k:row[k]for k in('update','loss','executed_input_tokens','causal_targets','masked_targets','model_forwards','seconds')}
            def validate(body,accept):
                budget.check();torch.rand(3,device='cuda');torch.rand(3);trainer.source.next_update()
                with torch.no_grad():value=float(F.cross_entropy(body(probe)[:,:-1].reshape(-1,32768),probe[:,1:].reshape(-1)))
                report['validation_forwards']+=1
                return dict(accept=accept,measurements=dict(synthetic_probe_ce=value,technical_acceptance_only=True))
            try:
                for parameter in model.parameters():parameter.requires_grad_(True)
                model.train();refresh(model);trainer=engine(model,p)
                controller=boundary.BoundaryController(trainer,refresh=refresh)
                report['prefix_update']=update();common=controller.state_dict();common_sha=owner.tree_sha(common)
                target=outputs.outputs(model)['mlp:9'].weight
                name=next(n for n,value in model.named_parameters()if value is target);target=None
                delta=packets.npz_tensors(atlas.ROOT/p['packet_path'])['requested']*p['proposal_scale']
                recipe=dict(id='technical:original_single9_direction',source_role='TRAIN_CORRECTION',
                    delta_packet_sha256=p['packet_sha256'],scale=p['proposal_scale'],natural_language_quality_claim=False)
                report['rejection']=controller.try_edit({name:delta},validate=lambda body:validate(body,False),
                    recipe=recipe,moment_policy='keep')
                # A rejected attempt is logged, but the trainer state must match.
                if owner.tree_sha(controller.state_dict()['trainer'])!=owner.tree_sha(common['trainer']):
                    raise RuntimeError('rejected edit leaked complete trainer state')
                for policy in p['policies']:
                    controller.load_state_dict(common)
                    receipt=controller.try_edit({name:delta},validate=lambda body:validate(body,True),recipe=recipe,moment_policy=policy)
                    if receipt['status']!='ACCEPTED_PERSISTENT'or receipt['changed_entries']==0:
                        raise RuntimeError('explicit protocol acceptance did not persist real coordinates')
                    saved=controller.state_dict()
                    packet=atlas.write_npz(OUT/(policy+'_accepted.npz'),requested=delta,after=saved['trainer']['model'][name])
                    continued=[update()for _ in range(2)];end_state=controller.state_dict();expected=owner.tree_sha(end_state)
                    end_state=None;controller.load_state_dict(saved);resumed=[update()for _ in range(2)]
                    end_state=controller.state_dict();observed=owner.tree_sha(end_state);end_state=None
                    if expected!=observed or [r['loss']for r in continued]!=[r['loss']for r in resumed]:
                        raise RuntimeError('real complete boundary/history next-update replay is not exact')
                    report['arms'].append(dict(moment_policy=policy,common_state_sha256=common_sha,
                        receipt=receipt,packet=packet,continued=continued,resumed=resumed,
                        expected_complete_state_sha256=expected,observed_complete_state_sha256=observed,exact_resume=True))
                    saved=None;print('[REAL_BOUNDARY_ARM] '+json.dumps(dict(policy=policy,exact_resume=True,losses=[r['loss']for r in continued])),flush=True)
                if report['physical_optimizer_updates']!=9 or report['physical_input_slots']!=2304:
                    raise RuntimeError('actual technical exposure differs from planned nine updates')
                report.update(status='REAL_FLOAT_BOUNDARY_EXACT_RESUME_TECHNICAL_COMPLETE',
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
            finally:
                model.zero_grad(set_to_none=True);trainer=controller=None;gc.collect()
                model.load_state_dict(original,strict=True)
                for name,parameter in model.named_parameters():parameter.requires_grad_(flags[name])
                model.train(was_training);refresh(model)
                report['original_core_restored']=manual.state_fingerprint(model)==p['origin']['core_sha256']
                if not report['original_core_restored']:raise RuntimeError('real training copy not restored to original')
                probe=parameter=model=None
    except BaseException as error:
        failure=error;report.update(status='REAL_BOUNDARY_ERROR',error=str(error),traceback=traceback.format_exc())
    finally:
        active=model=trainer=controller=parameter=probe=original=common=saved=end_state=None
        gc.collect();cleanup_error=library.cleanup(report)
        if failure is None:failure=cleanup_error
        report['wall_seconds']=time.monotonic()-started;library.write_new(OUT/'report.json',report)
        print('[REAL_BOUNDARY_END] '+json.dumps({k:report.get(k)for k in('status','physical_optimizer_updates','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved real boundary admission failure')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='check':verify();print('[REAL_BOUNDARY_CHECK] sealed CPU-only inputs')
    else:actual()


if __name__=='__main__':main()
