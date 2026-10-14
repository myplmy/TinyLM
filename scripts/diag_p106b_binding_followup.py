"""Same32 development lookup after balanced curriculum; old128 endpoints inherited."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
import json
from unittest.mock import patch
from scripts import diag_p106b_binding_course as course
from scripts import diag_p106b_source_binding as binding
from scripts import diag_p106b_context_transfer as engine
TARGET=ROOT/'test_result/evidence/p106b_binding_followup_v1_s1337'


def preflight():
    if TARGET.exists():raise FileExistsError('followup raw preserved')
    path=course.EVIDENCE/'lookup_balanced/report.json';r=json.loads(path.read_text())
    if r['updates']!=128 or r['status']!='CONTEXT_SFT_COMPLETE_REVIEW_PENDING':raise FileNotFoundError('completed128 student required')
    if course.training.data.digest(ROOT/r['checkpoint'])!=r['checkpoint_sha256']:raise ValueError('saved new student changed')
    previous=json.loads((binding.TARGET/'report.json').read_text())
    if previous['returncode']!=0 or previous['case_sha256']!=binding.course.support.sha(binding.cases()):raise ValueError('old panel controls changed')
    subjects=[dict(id='lookup_balanced',path=r['checkpoint'],sha=r['checkpoint_sha256'])]
    return subjects,dict(schema='P106B_BALANCED_BINDING_DEVELOPMENT_FOLLOWUP_V1',subjects=subjects,
        case_sha256=previous['case_sha256'],prior_report=str((binding.TARGET/'report.json').relative_to(ROOT)),
        prior_report_sha256=course.training.data.digest(binding.TARGET/'report.json'),inherited_results=previous['results'],
        parent_sha256=course.training.PARENT_SHA,tokenizer_sha256=course.training.data.TOK_SHA,
        precision='FP32_MATH_NO_TF32',cache=True,mtp_tokens=1,max_new=64,training='NOT_RUN',checkpoint_save=False,
        test_scope='DEVELOPMENT_REUSED32_AFTER_DATA_DESIGN; diagnostic names excluded from train/val; not independent general test',
        code_sha256={p:course.training.data.digest(ROOT/p) for p in ('scripts/diag_p106b_binding_followup.py','scripts/diag_p106b_source_binding.py','scripts/diag_p106b_context_transfer.py','tinylm/infer/generate.py')})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=600)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    if not 60<=args.max_wall_sec<=600:p.error('bounded60..600')
    if args.check_only:print('[CHECK_ONLY] '+json.dumps(preflight()[1]));return 0
    if args.execute:
        with patch.object(engine,'TARGET',TARGET),patch.object(engine,'preflight',preflight),patch.object(engine,'cases',binding.cases):return engine.execute(args)
    p.error('explicit mode required')

if __name__=='__main__':raise SystemExit(main())
