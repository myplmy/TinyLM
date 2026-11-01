"""Reuse all prior full-root predicates; only bind the fresh shot/path/source."""
import ast
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
OLD=ROOT/'handoff/audit/nov01_independent'
CURRENT=Path(__file__).parent


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def root_function():
    from scripts import diag_p106b_falcon_logitreuse_shots as new
    original=OLD/'falcon_logitreuse_root_readback_v2.py'
    prior=load('prior_falcon_root',original)
    node=next(n for n in ast.parse(original.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='one')
    counts={'shot_assertion':0,'raw_path':0}
    class Rebind(ast.NodeTransformer):
        def visit_Assert(self,n):
            if ast.unparse(n.test)=='shot == 0':
                n.test=ast.Compare(ast.Name('shot',ast.Load()),[ast.Eq()],[ast.Constant(5)])
                counts['shot_assertion']+=1
            return self.generic_visit(n)
        def visit_Assign(self,n):
            if any(isinstance(t,ast.Name) and t.id=='raw' for t in n.targets):
                n.value=ast.parse("ROOT/'test_result/101_log_20261101_P106B_Stage14jW_mmlu_falcon5_logitreuse_full.txt'",mode='eval').body
                counts['raw_path']+=1
            return self.generic_visit(n)
    tree=ast.Module(body=[Rebind().visit(node)],type_ignores=[]);ast.fix_missing_locations(tree)
    assert counts=={'shot_assertion':1,'raw_path':1}
    namespace=dict(prior.__dict__)
    namespace.update(driver=new.base,PROFILE=new.PROFILE,
        PROFILE_SHA=new.base.data.digest(new.PROFILE),policy=new.base.prior.policy,__file__=str(Path(__file__)))
    exec(compile(tree,str(Path(__file__))+'::bound_full_root','exec'),namespace)
    return namespace['one'],dict(transform_counts=counts,original_sha256=new.base.data.digest(original))


def compare_function():
    original=OLD/'mmlu_external_comparison_v2.py'
    prior=load('prior_mmlu_compare',original)
    node=next(n for n in ast.parse(original.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='compare')
    counts={'falcon5_input':0,'new_output':0}
    class Rebind(ast.NodeTransformer):
        def visit_Assign(self,n):
            if any(isinstance(t,ast.Name) and t.id=='path' for t in n.targets) and ast.unparse(n.value).startswith("FALCON /"):
                n.value=ast.parse("(FALCON5 if shot==5 else FALCON)/('mmlu_falcon'+str(shot)+'_full_readback_v2.json')",mode='eval').body
                counts['falcon5_input']+=1
            return self.generic_visit(n)
        def visit_Constant(self,n):
            if n.value=='MMLU_EXTERNAL_COMPARISON_v2.json':
                n.value='MMLU_EXTERNAL_COMPARISON_v3.json';counts['new_output']+=1
            return n
    tree=ast.Module(body=[Rebind().visit(node)],type_ignores=[]);ast.fix_missing_locations(tree)
    assert counts=={'falcon5_input':1,'new_output':1}
    namespace=dict(prior.__dict__)
    namespace.update(FALCON5=ROOT/'test_result/evidence/p106b_falcon_logitreuse_shots_v1_20261101/readback',__file__=str(Path(__file__)))
    # The prior function reads immutable baselines from AUDIT and writes its new filename there.
    # That path is new; preserve every v1/v2 comparison.
    exec(compile(tree,str(Path(__file__))+'::six_run_compare','exec'),namespace)
    return namespace['compare'],dict(transform_counts=counts,original_sha256=prior.digest(original))


if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='contract':
        _,a=root_function();_,b=compare_function()
        print(json.dumps(dict(status='CPU_ROOT_REBIND_ONLY',root=a,compare=b,model_calls=0)))
    elif mode=='root':
        run,proof=root_function();run(5)
        (CURRENT/'FALCON5_ROOT_BINDING_v1.json').write_text(json.dumps(proof,indent=2)+chr(10))
    elif mode=='compare':
        run,proof=compare_function();run(False)
        (CURRENT/'MMLU_SIX_COMPARE_BINDING_v1.json').write_text(json.dumps(proof,indent=2)+chr(10))
    else:raise ValueError('contract/root/compare')
