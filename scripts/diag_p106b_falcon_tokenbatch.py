#!/usr/bin/env python3
"""Explicit bounded batching variant of the pinned Falcon MMLU driver.

No framework/model file is changed. Short requests use8, long requests use4;
every actual forward must fit4096 padded tokens and the existing6GiB cap.
"""
import ast
from contextlib import contextmanager
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import sys
from types import MethodType

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tinylm import paths as _paths
from scripts import diag_p106b_falcon_mmlu as base

ORIGIN_PROFILE=base.PROFILE
ORIGIN_OUTPUT=base.OUTPUT
ORIGIN_PRIOR=base.prior
PROFILE=ROOT/'data_cache/p106b_falcon_tokenbatch_v1_20261101/profile.json'
OUTPUT=ROOT/'test_result/evidence/p106b_falcon_tokenbatch_v1_20261101'
ORIGINAL_OBSERVER=base.observe_backend
ORIGINAL_OLD=base.old


def policy(shots):
    value=ORIGIN_PRIOR.policy(shots)
    value['batch_size']='BOUNDED_8_IF_LENGTH_LE512_ELSE4'
    value['maximum_forward_padded_positions']=4096
    return value


class PriorProxy:
    policy=staticmethod(policy)
    def __getattr__(self,name):return getattr(ORIGIN_PRIOR,name)


class OldRuntimeProxy:
    def __getattr__(self,name):return getattr(ORIGINAL_OLD,name)
    def numerical_canary(self,lm,torch):
        lm._batch_scheduler=MethodType(scheduler,lm)
        return ORIGINAL_OLD.numerical_canary(lm,torch)


def scheduler(self,pos,requests):
    if pos==0:
        long=sum(min(len(r[1])+len(r[2])-1,1024)>512 for r in requests)
        self._p106b_long_boundary=((long+3)//4)*4
    return 4 if pos<self._p106b_long_boundary else 8


@contextmanager
def observer(lm,torch,report):
    lm._batch_scheduler=MethodType(scheduler,lm)
    report['batch_shape_counts']={}
    with ORIGINAL_OBSERVER(lm,torch,report):
        original=lm._model_call
        def call(inputs,*args,**kwargs):
            n,t=inputs.shape
            assert n<=8 and t<=1024 and inputs.numel()<=4096
            key=str(n)+'x'+str(t)
            report['batch_shape_counts'][key]=report['batch_shape_counts'].get(key,0)+1
            return original(inputs,*args,**kwargs)
        lm._model_call=call
        try:yield
        finally:lm._model_call=original


def transformed_evaluate():
    original=ast.parse(Path(base.__file__).read_text())
    node=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='evaluate')
    tree=ast.Module(body=[node],type_ignores=[])
    counts={'set':0,'assert':0,'call':0}
    class BatchTransform(ast.NodeTransformer):
        def visit_Assign(self,n):
            if any(ast.unparse(t)=='lm.batch_size_per_gpu' for t in n.targets):
                assert isinstance(n.value,ast.Constant) and n.value.value==4
                n.value=ast.Constant('auto');counts['set']+=1
            return self.generic_visit(n)
        def visit_Compare(self,n):
            if ast.unparse(n.left)=='lm.batch_size' and len(n.comparators)==1:
                assert isinstance(n.comparators[0],ast.Constant) and n.comparators[0].value==4
                n.comparators=[ast.Constant('auto')];counts['assert']+=1
            return self.generic_visit(n)
        def visit_Call(self,n):
            if ast.unparse(n.func)=='simple_evaluate':
                for kw in n.keywords:
                    if kw.arg=='batch_size':
                        assert isinstance(kw.value,ast.Constant) and kw.value.value==4
                        kw.value=ast.Constant('auto');counts['call']+=1
            return self.generic_visit(n)
    tree=BatchTransform().visit(tree);ast.fix_missing_locations(tree)
    assert counts=={'set':1,'assert':1,'call':1},counts
    namespace=dict(base.__dict__)
    namespace['observe_backend']=observer
    namespace['old']=OldRuntimeProxy()
    exec(compile(tree,str(Path(__file__))+'::evaluate_batch_variant','exec'),namespace)
    return namespace['evaluate'],counts


base.prior=PriorProxy()
base.PROFILE,base.OUTPUT=PROFILE,OUTPUT
base.OWN=base.OWN+('scripts/diag_p106b_falcon_tokenbatch.py','scripts/test_p106b_falcon_tokenbatch.py')
base.evaluate,TRANSFORM_COUNTS=transformed_evaluate()


def freeze():
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    configure_hf_cache()
    old=json.loads(ORIGIN_PROFILE.read_text())
    assert old['status']=='CPU_CONTRACT_COMPLETE' and old['model_loads']==0
    expected=dict(old['source']['files'])
    assert all(base.data.digest(ROOT/p)==sha for p,sha in expected.items())
    assert old['models']==base.model_assets() and old['runtime']==base.runtime_proof()
    assert not PROFILE.exists() and not OUTPUT.exists()
    value=dict(old)
    value.update(created_at=datetime.now(timezone.utc).isoformat(),source=base.identity(),
        policies={str(n):policy(n) for n in (0,5)},
        inherited_cpu_contract=dict(profile=str(ORIGIN_PROFILE.relative_to(ROOT)),
            profile_sha256=base.data.digest(ORIGIN_PROFILE),output=str(ORIGIN_OUTPUT.relative_to(ROOT)),
            token_and_prompt_metadata_unchanged=True),
        batching_variant=dict(transform_counts=TRANSFORM_COUNTS,long_threshold=512,short_batch=8,long_batch=4,
            max_padded_positions=4096,auto_batch_search=False,quality_selection=False),
        origin_cost0_sha256=base.data.digest(ORIGIN_OUTPUT/'shot0/cost/report.json'))
    assert value['shots']==old['shots'] and value['cpu_lengths']==old['cpu_lengths']
    PROFILE.parent.mkdir(parents=True,exist_ok=False)
    OUTPUT.mkdir(parents=True,exist_ok=False)
    base.resource.write_new(PROFILE,value)
    base.resource.write_new(OUTPUT/'contract.json',value)
    print(json.dumps(dict(status='REUSED_EXACT_CPU_TOKENS_AND_NEW_BOUNDED_BATCHING',
        profile_sha256=base.data.digest(PROFILE),source=value['source']['sha256'],gpu=0,model_loads=0)))
    return 0


def require_cost_parity(save=False):
    old=json.loads((ORIGIN_OUTPUT/'shot0/cost/report.json').read_text())
    new=json.loads((OUTPUT/'shot0/cost/report.json').read_text())
    assert old['final_exit']==new['final_exit']==0 and old['actual_rows']==new['actual_rows']==114
    assert old['shots']==new['shots']==0 and set(old['samples'])==set(new['samples'])
    maximum,checked=0.,0
    for name in old['samples']:
        pairs=[]
        for folder,report in [(ORIGIN_OUTPUT,old),(OUTPUT,new)]:
            rows=[]
            for part in report['samples'][name]['shards']:
                p=folder/'shot0/cost/samples'/name/part['path']
                assert base.data.digest(p)==part['sha256']
                rows.extend(json.loads(v) for v in p.read_text().splitlines())
            pairs.append(rows)
        assert len(pairs[0])==len(pairs[1])==2
        for a,b in zip(*pairs):
            assert a['doc_id']==b['doc_id'] and a['arguments']==b['arguments']
            left,right=[v[0] for v in a['filtered_resps']],[v[0] for v in b['filtered_resps']]
            assert len(left)==len(right)==4
            assert all(math.isclose(x,y,abs_tol=1e-4,rel_tol=1e-4) for x,y in zip(left,right))
            assert max(range(4),key=lambda i:left[i])==max(range(4),key=lambda i:right[i])
            maximum=max(maximum,max(abs(x-y) for x,y in zip(left,right)));checked+=1
    value=dict(rows=checked,loglikelihoods=checked*4,all_argmax_equal=True,max_abs=maximum,
        atol=1e-4,rtol=1e-4,profile_sha256=base.data.digest(PROFILE),
        original_cost_sha256=base.data.digest(ORIGIN_OUTPUT/'shot0/cost/report.json'),
        variant_cost_sha256=base.data.digest(OUTPUT/'shot0/cost/report.json'),quality_selection=False)
    assert checked==114
    path=OUTPUT/'cost_parity.json'
    if save:
        assert not path.exists();base.resource.write_new(path,value)
    else:assert json.loads(path.read_text())==value
    print(json.dumps(dict(cost_parity_rows=checked,loglikelihoods=checked*4,max_abs=maximum)),flush=True)
    return value


def main():
    if '--mode' in sys.argv and sys.argv[sys.argv.index('--mode')+1]=='contract' and '--execute' in sys.argv:
        return freeze()
    mode=sys.argv[sys.argv.index('--mode')+1]
    if mode=='full':require_cost_parity(save=False)
    code=base.main()
    if mode=='cost' and '--execute' in sys.argv and code==0:require_cost_parity(save=True)
    return code


if __name__=='__main__':raise SystemExit(main())
