"""New broad course reuses the assistant-only trainer; old namespace unchanged."""
from __future__ import annotations
import argparse
from contextlib import contextmanager,ExitStack
import json
from pathlib import Path
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_context_quality as prior
from scripts import p106b_context_broad as data
from scripts import diag_p101a_sft_mtp as training
TAG='p106b_context_broad_v2_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus';EVIDENCE=ROOT/'test_result/evidence'/TAG
ARMS={'ntp_hi':('parent_ntp',1e-4),'ntp_mid':('parent_ntp',5e-5)}
CODE=tuple(dict.fromkeys(prior.CODE+('scripts/p106b_context_broad.py','scripts/diag_p106b_context_broad.py',
    'scripts/test_p106b_context_broad.py')))


def info():
    return dict(schema=data.VERSION,tag=TAG,parent_sha256=training.PARENT_SHA,
        tokenizer_sha256=training.data.TOK_SHA,seed=1337,micro_bs=8,accum=16,seq=1024,
        grad_checkpoint=True,compile='default',epochs=4,expected_updates=256,
        train_rows=8192,val_rows=1024,code_sha256={p:training.data.digest(ROOT/p) for p in CODE},
        same_initial_body=True,world_knowledge_claim=False,formal_train_ready=False,
        actual_draw='MEASURE_SEPARATELY_FROM_PADDING',inference_precision='FP32_MATH_NO_TF32',
        current_independent_test='new wording/values; old implicit24 is development-only, never training')


@contextmanager
def scope():
    values=((prior,'TAG',TAG),(prior,'CORPUS',CORPUS),(prior,'EVIDENCE',EVIDENCE),
        (prior,'ARMS',ARMS),(prior,'CODE',CODE),(prior,'info',info),(prior,'data',data))
    with ExitStack() as stack:
        for module,name,value in values:stack.enter_context(patch.object(module,name,value))
        yield


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('corpus','train'),required=True)
    p.add_argument('--arm',choices=tuple(ARMS),default='ntp_hi');p.add_argument('--max-wall-sec',type=int,default=1800)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=3600:p.error('bounded new course gate required')
    with scope():
        if a.check_only:
            if a.mode=='train':prior.read_course()
            print('[CHECK_ONLY] '+json.dumps(info(),ensure_ascii=False));return 0
        if a.mode=='corpus':return prior.corpus()
        existed=(EVIDENCE/a.arm).exists()
        try:return prior.train(a)
        except BaseException as exc:
            target=EVIDENCE/a.arm;rc=130 if isinstance(exc,KeyboardInterrupt) else 9
            if not existed and target.is_dir() and not (target/'report.json').exists():
                training.write(target/'report.json',dict(info(),arm=a.arm,status='INTERRUPTED' if rc==130 else 'EXECUTION_ERROR',
                    returncode=rc,error_type=type(exc).__name__,reason=str(exc)[:1000],checkpoint_valid='NOT_ESTABLISHED'))
            print('[BROAD_CONTEXT_ERROR] '+type(exc).__name__+': '+str(exc),flush=True);return rc

if __name__=='__main__':raise SystemExit(main())
