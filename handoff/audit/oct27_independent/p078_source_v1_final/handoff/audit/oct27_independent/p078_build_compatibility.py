"""Root audit of exactly two body-source transitions; metadata reads only."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import diag_p078_route_training as base


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def nodes(tree):
    return {v.name:v for v in tree.body if isinstance(v,ast.FunctionDef)}


def expression(text):
    return ast.dump(ast.parse(text,mode='eval').body)


class ReplaceExact(ast.NodeTransformer):
    def __init__(self, pairs):
        self.pairs={expression(k):ast.parse(v,mode='eval').body for k,v in pairs.items()}
    def visit(self,node):
        if isinstance(node,ast.expr) and ast.dump(node) in self.pairs:
            return copy.deepcopy(self.pairs[ast.dump(node)])
        return super().visit(node)


def encode(node):
    return ast.dump(ast.Module(body=node,type_ignores=[]))


def main():
    directory=Path(__file__).parent
    old_path=directory/'p078_route_driver_legacy.source'
    current_path=ROOT/'scripts/diag_p078_route_training.py'
    old=ast.parse(old_path.read_text()); new=ast.parse(current_path.read_text())
    old_functions=nodes(old); new_functions=nodes(new)
    old_closed=old_functions['closed']
    normalize=ReplaceExact({
        'digest(path(report_name(mode, arm, args)))':'report_sha256',
        'namespace(args)':'expected_tag',
    })
    original_guard=normalize.visit(copy.deepcopy(ast.Module(body=old_closed.body[3:],type_ignores=[])))
    helper_guard=new_functions['validate_closed_receipt'].body[1:]
    assert ast.dump(original_guard)==encode(helper_guard),'receipt validation changed beyond explicit inputs'
    expected_wrapper=ast.parse("""def closed(args, mode, arm):
    info = signature(args)
    value = read(report_name(mode, arm, args)); activity = read(activity_name(mode, arm, args))
    return validate_closed_receipt(value, activity, info,
        report_sha256=digest(path(report_name(mode, arm, args))), expected_tag=namespace(args))
""").body[0]
    assert ast.dump(new_functions['closed'])==ast.dump(expected_wrapper)
    old_loaded=old_functions['loaded']; new_loaded=new_functions['loaded']
    old_if=next(v for v in ast.walk(old_loaded) if isinstance(v,ast.If) and ast.dump(v.test)==expression('not trained'))
    new_if=next(v for v in ast.walk(new_loaded) if isinstance(v,ast.If) and ast.dump(v.test)==expression('not trained'))
    assert len(old_if.orelse)==len(new_if.orelse)==1 and isinstance(old_if.orelse[0],ast.If)
    normalize_header=ReplaceExact({'update_count(inputs(args))':'updates','TOK_SHA':'tokenizer_sha256',
        'signature(args)':'expected_input'})
    old_header=normalize_header.visit(copy.deepcopy(old_if.orelse[0]))
    new_header=new_functions['validate_student_header'].body[1]
    assert ast.dump(old_header)==ast.dump(new_header),'student header validation changed'
    expected_call=ast.parse("validate_student_header(state, updates=update_count(inputs(args)), tokenizer_sha256=TOK_SHA, arm=arm, expected_input=signature(args))").body[0]
    assert ast.dump(new_if.orelse[0])==ast.dump(expected_call)
    new_if.body=copy.deepcopy(old_if.body);new_if.orelse=copy.deepcopy(old_if.orelse)
    normalized=[]
    for node in new.body:
        if isinstance(node,ast.FunctionDef) and node.name in ('validate_closed_receipt','validate_student_header'):
            continue
        normalized.append(copy.deepcopy(old_closed) if isinstance(node,ast.FunctionDef) and node.name=='closed' else node)
    assert encode(old.body)==encode(normalized),'another body-driver computation changed'
    old_holdout_path=directory/'p078_holdout_reader_legacy.source'
    current_holdout_path=ROOT/'scripts/p078_router_holdout_data.py'
    old_holdout=ast.parse(old_holdout_path.read_text()); new_holdout=ast.parse(current_holdout_path.read_text())
    old_holdout_functions=nodes(old_holdout); new_holdout_functions=nodes(new_holdout)
    original_reader=old_holdout_functions['read_prepared']
    extracted_reader=copy.deepcopy(new_holdout_functions['read_prepared_contract'])
    extracted_reader.name='read_prepared'; extracted_reader.args=copy.deepcopy(original_reader.args)
    extracted_reader.body=extracted_reader.body[1:]
    extracted_reader=ReplaceExact({'expected_source_sha256':'{p:base.digest(base.path(p)) for p in CODE}'}).visit(extracted_reader)
    assert ast.dump(extracted_reader)==ast.dump(original_reader),'holdout source/row/exclusion guard changed'
    expected_reader_wrapper=ast.parse("""def read_prepared(expected_sha, corpus_sha):
    return read_prepared_contract(expected_sha, corpus_sha,
        expected_source_sha256={p:base.digest(base.path(p)) for p in CODE})
""").body[0]
    assert ast.dump(new_holdout_functions['read_prepared'])==ast.dump(expected_reader_wrapper)
    normalized_holdout=[]
    for node in new_holdout.body:
        if isinstance(node,ast.FunctionDef) and node.name=='read_prepared_contract':continue
        normalized_holdout.append(copy.deepcopy(original_reader) if isinstance(node,ast.FunctionDef) and node.name=='read_prepared' else node)
    assert encode(old_holdout.body)==encode(normalized_holdout),'another holdout producer computation changed'
    old_report=ROOT/'test_result/evidence/p078_route_training_v1_s1337_cleanv3/train_balanced_count/report.json'
    report=json.loads(old_report.read_text())
    assert digest(old_path)==report['input']['source_sha256']['scripts/diag_p078_route_training.py']
    reference_path=directory/'p078_reference_equivalence_v1.json'
    reference=json.loads(reference_path.read_text())
    assert reference['cases_count']==24 and reference['normalized_complete_module_ast_equal']
    assert reference['original_sources_unchanged'] and not reference['cuda_initialized']
    assert all(v['exact_loss_equal'] and v['exact_gradient_equal'] for v in reference['cases'])
    args=SimpleNamespace(corpus=base.CLEAN_CORPUS,corpus_sha256='7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20',
        adam_lr=5e-5,muon_lr=2e-4)
    current=base.signature(args)
    inputs=[old_path,current_path,ROOT/'tinylm/train/mtp_sft.py',directory/'p078_mtp_reference_legacy.source',
        reference_path,directory/'p078_reference_probe.py',old_holdout_path,current_holdout_path,Path(__file__)]
    proof=dict(schema='P078_BODY_COMPATIBILITY_V1',reference_cpu_cases=24,
        reference_module_ast_equal=True,validator_guard_ast_equal=True,header_guard_ast_equal=True,
        remaining_driver_ast_equal=True,holdout_reader_ast_equal=True,default_closed_uses_current_input=True,
        old_source_sha256=report['input']['source_sha256'],current_source_sha256=current['source_sha256'],
        proof_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=digest(p)) for p in inputs],
        model_loads=0,gpu_calls=0,historical_training_reproduced=False)
    output=directory/'p078_body_compatibility_v2.json'
    with output.open('x',encoding='utf-8') as stream:
        json.dump(proof,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
    print(json.dumps({k:proof[k] for k in ('reference_cpu_cases','validator_guard_ast_equal','header_guard_ast_equal','remaining_driver_ast_equal')}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
