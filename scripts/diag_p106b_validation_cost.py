#!/usr/bin/env python3
"""Time the exact frozen-course development paths, with no optimizer or checkpoint."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
import json
import math
import time
from scripts import diag_p106b_state_update_aux as state
from scripts import diag_p106b_joint_decimal as joint
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
TAG='p106b_validation_cost_v1_s1337'


def new_head(variant,dim,device='cpu'):
    return (state.driver.method if variant=='state' else joint.method).new_head(dim,device)


def projection(step_p95,updates,validation_sec,epochs=4):
    values=(step_p95,validation_sec)
    if any(not math.isfinite(v) or v<=0 for v in values) or type(updates) is not int or updates<1 or epochs!=4:
        raise ValueError('finite positive observed timings and four-pass schedule required')
    return dict(step_p95=step_p95,updates=updates,validation_sec=validation_sec,epochs=epochs,
        estimated_train_sec=step_p95*updates+epochs*validation_sec*1.5+300,
        validation_buffer=1.5,scope='parent-path single observation plus operational buffer; not a statistical p95 guarantee')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',choices=('state','joint'),required=True)
    mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--execute',action='store_true');mode.add_argument('--check-only',action='store_true')
    p.add_argument('--max-wall-sec',type=int,default=900);args=p.parse_args();state.driver.base.deadline()
    module=state if args.variant=='state' else joint
    report,rows=module.read_course();parent=state.parent_ref(True)
    evidence=ROOT/'test_result/evidence'/TAG/args.variant;local=ROOT/'test_result/evidence/local'/TAG/args.variant
    if evidence.exists() or local.exists():raise FileExistsError('previous validation timing retained')
    if args.check_only:
        print('[VALIDATION_COST_PREFLIGHT] '+json.dumps(dict(variant=args.variant,dev_rows=len(rows['dev']),parent=parent,
            model_loaded=False,optimizer_updates=0)),flush=True);return 0
    from tinylm.train import mtp_sft as core
    idle_before_gpu();start=time.perf_counter();components={}
    with wall_limit(args.max_wall_sec):
        torch,model,cfg,tok,initial=state.load_from_parent('parent_ntp');model=model.cuda()
        records=[core.encode_record(row,tok) for row in rows['dev']]
        pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('pad absent')
        head=new_head(args.variant,cfg.dim,'cuda')
        def timed(name,fn):
            torch.cuda.synchronize();tick=time.perf_counter();value=fn();torch.cuda.synchronize()
            components[name]=time.perf_counter()-tick;return value
        training=state.driver.base.training
        val=timed('sft_dev',lambda:training.evaluate(model,records,pad))
        native=timed('native32',lambda:training.native_ce(model,state.driver.base.NATIVE))
        auxiliary=timed('auxiliary_dev',lambda:module.auxiliary_dev(model,head,tok,rows['dev'],pad,report['dev_contracts']))
        generated=timed('dev_free_generation',lambda:state.driver.base.generate(model,cfg,tok,
            state.driver.base.dev_sample(rows['dev']),local,'parent_cost_dev'))
        final=training.state_fingerprint(model)
        if final!=initial:raise ValueError('read-only timing changed model weights')
        result=dict(schema='P106B_VALIDATION_COST_V1',tag=TAG,variant=args.variant,status='VALIDATION_PATH_TIMED',
            parent=parent,course_report_sha256=training.data.digest(module.CORPUS/'report.json'),
            source_code_sha256={v:training.data.digest(ROOT/v) for v in module.CODE},
            own_code_sha256=training.data.digest(Path(__file__)),components_sec=components,
            validation_sum_sec=sum(components.values()),whole_sec=time.perf_counter()-start,
            dev_rows=len(records),generation_rows=len(state.driver.base.dev_sample(rows['dev'])),
            val=val,native=native,auxiliary=auxiliary,generation=generated,
            body_before=initial,body_after=final,optimizer_updates=0,checkpoint_saved=False,
            quality_scope='parent timing only; not candidate quality or exact trained-endpoint timing')
        training.write(evidence/'report.json',result)
    print('[VALIDATION_COST] '+json.dumps({k:result[k] for k in ('variant','status','components_sec','validation_sum_sec','whole_sec','dev_rows','generation_rows','optimizer_updates')}),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
