#!/usr/bin/env python3
"""Use the pinned official HFLM single-token-context logit reuse, batch4 unchanged."""
import ast
from contextlib import contextmanager
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tinylm import paths as _paths
from scripts import diag_p106b_falcon_mmlu as base

ORIGIN_PROFILE,ORIGIN_OUTPUT=base.PROFILE,base.OUTPUT
ORIGIN_PRIOR,ORIGIN_OLD=base.prior,base.old
ORIGINAL_OBSERVER=base.observe_backend
PROFILE=ROOT/'data_cache/p106b_falcon_logitreuse_v1_20261101/profile.json'
OUTPUT=ROOT/'test_result/evidence/p106b_falcon_logitreuse_v1_20261101'


def policy(shots):
    value=ORIGIN_PRIOR.policy(shots)
    value['logits_cache']=True
    return value


class PriorProxy:
    policy=staticmethod(policy)
    def __getattr__(self,name):return getattr(ORIGIN_PRIOR,name)


class RuntimeProxy:
    def __getattr__(self,name):return getattr(ORIGIN_OLD,name)
    @contextmanager
    def model_runtime(self,*args,**kwargs):
        with ORIGIN_OLD.model_runtime(*args,**kwargs) as (lm,proof):
            assert lm.logits_cache is False
            lm.logits_cache=True
            proof['official_context_logit_reuse_enabled']=True
            yield lm,proof


@contextmanager
def observer(lm,torch,report):
    assert lm.logits_cache is True and lm.batch_size==4
    report['batch_shape_counts']={}
    with ORIGINAL_OBSERVER(lm,torch,report):
        original=lm._model_call
        def call(inputs,*args,**kwargs):
            n,t=inputs.shape
            assert n<=4 and t<=1024 and inputs.numel()<=4096
            key=str(n)+'x'+str(t)
            report['batch_shape_counts'][key]=report['batch_shape_counts'].get(key,0)+1
            return original(inputs,*args,**kwargs)
        lm._model_call=call
        try:yield
        finally:lm._model_call=original


base.PROFILE,base.OUTPUT=PROFILE,OUTPUT
base.prior,base.old=PriorProxy(),RuntimeProxy()
base.observe_backend=observer
base.OWN=base.OWN+('scripts/diag_p106b_falcon_logitreuse.py','scripts/test_p106b_falcon_logitreuse.py',
                  'scripts/diag_p106b_falcon_tokenbatch.py')

# Reuse only the completed differential-check function, never import its driver/configuration.
helper=ROOT/'scripts/diag_p106b_falcon_tokenbatch.py'
node=next(n for n in ast.parse(helper.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='require_cost_parity')
exec(compile(ast.Module(body=[node],type_ignores=[]),str(helper)+'::parity_only','exec'),globals())


def freeze():
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    configure_hf_cache()
    old=json.loads(ORIGIN_PROFILE.read_text())
    assert all(base.data.digest(ROOT/p)==sha for p,sha in old['source']['files'].items())
    assert old['models']==base.model_assets() and old['runtime']==base.runtime_proof()
    assert not PROFILE.exists() and not OUTPUT.exists()
    continuation_count=0
    for part in old['cpu_lengths']['shards']:
        p=ORIGIN_OUTPUT/'contract/lengths'/part['path']
        assert base.data.digest(p)==part['sha256']
        for line in p.read_text().splitlines():
            row=json.loads(line)
            for choice in row['choices']:
                assert choice['continuation_tokens']==1
                continuation_count+=1
    assert continuation_count==112336
    value=dict(old)
    value.update(created_at=datetime.now(timezone.utc).isoformat(),source=base.identity(),
        policies={str(n):policy(n) for n in (0,5)},
        inherited_cpu_contract=dict(profile=str(ORIGIN_PROFILE.relative_to(ROOT)),profile_sha256=base.data.digest(ORIGIN_PROFILE),
            tokens_and_prompts_unchanged=True,one_token_continuations=continuation_count),
        variant=dict(official_hflm_context_logit_reuse=True,model_kv_cache=False,batch_size=4,
            official_driver_evaluate_body_unchanged=True,auto_batch_search=False,quality_selection=False))
    PROFILE.parent.mkdir(parents=True,exist_ok=False);OUTPUT.mkdir(parents=True,exist_ok=False)
    base.resource.write_new(PROFILE,value);base.resource.write_new(OUTPUT/'contract.json',value)
    print(json.dumps(dict(status='FIXED_OFFICIAL_ONE_TOKEN_REUSE_CONTRACT',
        profile_sha256=base.data.digest(PROFILE),source=value['source']['sha256'],continuations=continuation_count,gpu=0)))
    return 0


def main():
    mode=sys.argv[sys.argv.index('--mode')+1]
    if mode=='contract' and '--execute' in sys.argv:return freeze()
    if mode=='full':require_cost_parity(save=False)
    code=base.main()
    if mode=='cost' and '--execute' in sys.argv and code==0:require_cost_parity(save=True)
    return code


if __name__=='__main__':raise SystemExit(main())
