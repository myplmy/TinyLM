"""All512 frozen code-known validation generations; source-first baseline reported separately."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
from collections import defaultdict,Counter
import json
from unittest.mock import patch
from scripts import diag_p106b_binding_course as course
from scripts import diag_p106b_context_transfer as engine
TARGET=ROOT/'test_result/evidence/p106b_binding_fullval_v1_s1337'


def cases():
    _,rows=course.read_course();result=[]
    for i,row in enumerate(rows['val']):
        m=row['meta'];result.append(dict(id=f'val_{i:04d}',root=m['semantic_root_id'],group=m['language'],language=m['language'],
            question=course.prior.data.text(row,0),gold=course.prior.data.text(row,-1),rubric='EXACT_SCALAR',
            requested_entity=m['requested_entity'],ordered_entities=m['ordered_entities'],
            target_is_first=m['target_is_first'],first_value=m['same_fact_mapping'][m['ordered_entities'][0]],
            code_truth='PROJECT_AUTHORED_CODE_FACT_CONTRACT'))
    if len(result)!=512:raise ValueError('same frozen512 required')
    return result


def preflight():
    if TARGET.exists():raise FileExistsError('all validation raw preserved')
    r=json.loads((course.EVIDENCE/'lookup_balanced/report.json').read_text())
    if r['updates']!=128 or course.training.data.digest(ROOT/r['checkpoint'])!=r['checkpoint_sha256']:raise ValueError('completed exact128 student required')
    subjects=[dict(id='lookup_balanced',path=r['checkpoint'],sha=r['checkpoint_sha256'])]
    return subjects,dict(
        schema='P106B_CODE_BINDING_FULLVAL_V1',subjects=subjects,case_sha256=course.prior.data.sha(cases()),
        student_report_sha256=course.training.data.digest(course.EVIDENCE/'lookup_balanced/report.json'),
        source_corpus_sha256=course.training.data.digest(course.CORPUS/'report.json'),
        precision='FP32_MATH_NO_TF32',cache=True,mtp_tokens=1,max_new=64,training='NOT_RUN',checkpoint_save=False,
        test_scope='FULL_EXISTING_FROZEN512_COURSE_VALIDATION; not independent general/world benchmark',
        first_value_baseline='not a randomized null; exact code heuristic, two requested targets and two orders per root',
        code_sha256={p:course.training.data.digest(ROOT/p) for p in ('scripts/diag_p106b_binding_fullval.py','scripts/diag_p106b_context_transfer.py','tinylm/infer/generate.py')})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=600)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=600:p.error('bounded60..600')
    if a.check_only:print('[CHECK_ONLY] '+json.dumps(preflight()[1]));return 0
    if not a.execute:p.error('explicit execution required')
    with patch.object(engine,'TARGET',TARGET),patch.object(engine,'preflight',preflight),patch.object(engine,'cases',cases):rc=engine.execute(a)
    report=json.loads((TARGET/'report.json').read_text());counts=Counter();bylang={};roots=defaultdict(list)
    for r in course.training.data.stream_rows(TARGET,report['raw_manifest']):
        ok=r['exact_reference_contract'] is True;counts.update(cases=1,exact=int(ok),first_value_baseline=int(r['gold']==r['first_value']),
            empty=int(not r['answer'].strip()),max_new=int(r['generation']['finish_reason']=='MAX_NEW'))
        l=bylang.setdefault(r['language'],Counter());l.update(cases=1,exact=int(ok),baseline=int(r['gold']==r['first_value']))
        roots[r['root']].append(r)
    if any(len(v)!=4 for v in roots.values()):raise ValueError('complete root quadruples required')
    counts['roots']=len(roots);counts['all4_exact_roots']=sum(all(r['exact_reference_contract'] is True for r in group) for group in roots.values())
    summary=dict(schema='P106B_FULLVAL_BINDING_READBACK_V1',counts=dict(counts),by_language={k:dict(v) for k,v in bylang.items()},
        report_sha256=course.training.data.digest(TARGET/'report.json'),raw_manifest=report['raw_manifest'],whole_sec=report['whole_sec'],
        source_first_is_not_truth_verifier=True,random_null_or_sigma='NOT_ESTABLISHED',general_intelligence='NOT_ESTABLISHED')
    course.training.write(TARGET/'summary.json',summary);print('[FULL512_BINDING] '+json.dumps(summary['counts']));return rc

if __name__=='__main__':raise SystemExit(main())
