#!/usr/bin/env python3
"""User-only paired NTP learning-rate scale, exactly one pass of the frozen8M."""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p101a_sft_mtp as prior

SOURCE_TAG='p101a_sft_mtp_v1_s1337'
SOURCE_SHA='C4F7E2CBFAA467ACAE43486A30956897AF83658C69D77FCF754A9AF9145C16BC'
TAGS={1.:'p101a_sft_mtp_lrhi_v2_s1337',.1:'p101a_sft_mtp_lrlo_v2_s1337'}


def scale_optimizers(factory,model,scale):
    optimizers=factory(model)
    for optimizer in optimizers:
        for group in optimizer.param_groups:group['lr']*=scale
    return optimizers


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('calibrate','train','compare'),required=True)
    p.add_argument('--lr-scale',type=float,choices=(1.,.1),required=True)
    p.add_argument('--max-wall-sec',type=int,default=5400)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=10800:p.error('bounded wall time required')
    a.tag=TAGS[a.lr_scale];a.arm='parent_ntp'
    corpus,_=prior.paths(SOURCE_TAG);_,evidence=prior.paths(a.tag)
    if prior.data.digest(corpus/'report.json')!=SOURCE_SHA:raise ValueError('frozen8M identity changed')
    report=prior.corpus_report(corpus)
    info=dict(prior.info(a),schema='P101A_LR_RETENTION_V1',epochs=1,lr=1e-4*a.lr_scale,
        muon_lr=4e-4*a.lr_scale,lr_scale=a.lr_scale,initializers=['parent'],horizons=[],
        auxiliary_total_weight=0.,processed_x_target_approx=report['actual_unique_train_x_tokens'],
        frozen_source_tag=SOURCE_TAG,frozen_source_sha256=SOURCE_SHA,
        code_sha256={**prior.info(a)['code_sha256'],**{name:prior.data.digest(ROOT/name) for name in
            ('scripts/diag_p101a_lr_retention.py','scripts/test_p101a_lr_retention.py')}},
        quality_scope='same one-epoch exposures; QA/native retention tradeoff, not 300M or broad intelligence')
    if a.check_only:print('[CHECK_ONLY] '+json.dumps(info));return 0
    if a.mode=='compare':
        reports={}
        for scale,tag in TAGS.items():
            _,directory=prior.paths(tag)
            path=prior.report_path(directory,'parent_ntp')
            value=json.loads(path.read_text())
            if value.get('status')!='SFT_MTP_TRAINED_EVAL_PENDING' or value.get('epochs')!=1:
                raise FileNotFoundError('both completed one-pass LR arms required')
            reports[str(scale)]=dict(report=str(path.relative_to(ROOT)),report_sha256=prior.data.digest(path),
                source_sha=value['corpus_sha256'],initial_core_sha=value['initial_core_sha256'],
                x=value['actual_processed_x_tokens'],targets=value['assistant_targets'],updates=value['updates'],
                initial_native_ce=value['initial_native_ce'],final_native_ce=value['final_native_ce'],
                final_answers=value['final_answers'],history=value['history'],grad_max=value['grad_max'])
        left,right=reports.values()
        for k in ('source_sha','initial_core_sha','x','targets','updates'):
            if left[k]!=right[k]:raise ValueError('unmatched LR controls: '+k)
        prior.write(ROOT/'test_result/evidence/p101a_lr_retention_pair_v2_s1337/report.json',
            dict(schema='P101A_LR_RETENTION_PAIR_V1',status='LR_PAIR_READ',reports=reports,
                 semantic_truth='RAW_ANSWERS_REQUIRE_REVIEW',broad_quality_claim='NOT_ESTABLISHED_SINGLE_SEED'))
        print('[LR_PAIR] '+json.dumps(reports));return 0
    original=prior.optimizers
    out=ROOT/'runs/ckpt'/('m100s10_ko-en_8M_dense_chat32_'+a.tag+'_parent_ntp.pt')
    with ExitStack() as stack:
        stack.enter_context(patch.object(prior,'optimizers',lambda model:scale_optimizers(original,model,a.lr_scale)))
        stack.enter_context(patch.object(prior,'checkpoint',lambda _tag,_arm:out))
        return prior.train_arm(a,corpus,evidence,info,calibrate=a.mode=='calibrate',epochs=1)


if __name__=='__main__':raise SystemExit(main())
