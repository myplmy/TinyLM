"""Reuse the earlier24 development cases on source-course parent/A/B; no training."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
import json
from unittest.mock import patch
from scripts import diag_p106b_source_course as course
from scripts import diag_p106b_context_transfer as old
TARGET=ROOT/'test_result/evidence/p106b_source_dev24_v1_s1337'


def preflight():
    if TARGET.exists():raise FileExistsError('development output preserved')
    subjects=[dict(id='parent',path=str(course.training.PARENT.relative_to(ROOT)),sha=course.training.PARENT_SHA)]
    for arm in ('sft_only','reference_lm'):
        p=course.EVIDENCE/(arm+'_report.json');r=json.loads(p.read_text())
        if r['updates']!=32 or r['status']!='CONTEXT_SFT_COMPLETE_REVIEW_PENDING':raise FileNotFoundError('completed source course arm required')
        subjects.append(dict(id=arm,path=r['checkpoint'],sha=r['checkpoint_sha256'],report=str(p.relative_to(ROOT)),report_sha=course.public.digest(p)))
    for item in subjects:
        if course.public.digest(ROOT/item['path'])!=item['sha']:raise ValueError('checkpoint changed')
    if course.public.digest(course.public.TOKENIZER)!=course.public.TOK_SHA:raise ValueError('tokenizer changed')
    return subjects,dict(schema='P106B_SOURCE_COURSE_DEVELOPMENT24_V1',subjects=subjects,
        case_sha256=course.support.sha(old.cases()),precision='FP32_MATH_NO_TF32',cache=True,mtp_tokens=1,max_new=64,
        code_sha256={p:course.public.digest(ROOT/p) for p in ('scripts/diag_p106b_source_dev24.py','scripts/diag_p106b_context_transfer.py','tinylm/infer/generate.py')},
        test_scope='DEVELOPMENT_REPEAT_NOT_INDEPENDENT; old24 never inserted into current training',
        source_truth='PSEUDO_UNVERIFIED',training='NOT_RUN',checkpoint_save=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true',required=True);p.add_argument('--max-wall-sec',type=int,default=600);args=p.parse_args()
    if not 60<=args.max_wall_sec<=900:p.error('bounded read-only eval')
    with patch.object(old,'TARGET',TARGET),patch.object(old,'preflight',preflight):return old.execute(args)

if __name__=='__main__':raise SystemExit(main())
