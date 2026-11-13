#!/usr/bin/env python3
"""User-only literal V3 recovery; strict old gates until a new policy is chosen.

Contract/family pilots are fresh V3, production is fresh V3, final corpus/student
are fresh V4. Successful V2 complex4 is hash-locked compatibility evidence only:
its explicit complex prompt/parser path is unchanged, not a new execution PASS.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager,ExitStack
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gemma_output_recovery as previous
from scripts import p106b_gemma_task_contract_v3 as tasks
from scripts import p106b_gemma_task_contract_v2 as complex_tasks
from scripts.p106b_mixed_scale import safe_repo_path,digest
from scripts.p106b_shards import verify

STRUCTURE=ROOT/'HF/sft_ready/p106b_gemma_task_structure4_v2'
STRUCTURE_SHA='B9E45E8D8141386D5D5698AFEAE2B6E07CF35B15BA9E4DD4891A34EABAFE6EF4'
STRUCTURE_CANON_SHA='59A3011EE7227EE8ADD85F14E6175CD62E51E97D3EF364AB1D7C392F874F82B9'
PILOTS=dict(contract16=ROOT/'HF/sft_ready/p106b_gemma_task_contract16_v3',
            family64=ROOT/'HF/sft_ready/p106b_gemma_task_family64_v3',structure4=STRUCTURE)
PATHS=dict(OUTPUT=ROOT/'HF/sft_ready/p106b_gemma_deficit_v3',
           CORPUS=ROOT/'HF/sft_ready/p106b_capability_gemma_v4',
           WIRE=ROOT/'HF/sft_ready/p106b_capability_gemma_wire_v4',
           STUDENT=ROOT/'HF/sft_ready/p106b_capability_gemma_student_v4',
           EVALUATION=ROOT/'HF/sft_ready/p106b_gemma_capability_multiaxis_v4')
TAG='p106b_s4_gemma_capability300m_chat32_literalv3_s1337'
REGRESSION=previous.REGRESSION+['scripts.test_p106b_gemma_literal_contract',
                                'scripts.test_p106b_gemma_literal_recovery']


def require_pinned_structure4():
    p=safe_repo_path(STRUCTURE/'report.json')
    if not p.is_file():raise FileNotFoundError('pinned prior complex4 absent; no model started')
    if digest(p)!=STRUCTURE_SHA:raise ValueError('pinned prior complex4 changed')
    report=json.loads(p.read_text(encoding='utf-8'));info=report.get('input',{})
    if (report.get('schema')!='P106B_GEMMA_TASK_PILOT_V1'
            or report.get('status')!='TASK_PILOT_COMPLETE' or report.get('accepted_groups')!=4
            or info.get('mode')!='structure4' or info.get('wire_contract')!=complex_tasks.CONTRACT
            or info.get('role_report_sha256')!=previous.gate.ROLE_SHA
            or report.get('candidate_manifest',{}).get('rows')!=4
            or report['candidate_manifest'].get('concat_sha256')!=STRUCTURE_CANON_SHA):
        raise ValueError('prior complex4 proof identity differs')
    # Its exact shared complex prompt, parser, wrapper and mask code has not changed.
    for name,sha in info.get('producer_code_sha256',{}).items():
        if digest(safe_repo_path(ROOT/name))!=sha:
            raise ValueError('complex4 shared runtime changed: '+name)
    if not info.get('producer_code_sha256'):raise ValueError('complex4 runtime fingerprint absent')
    verify(p.parent,report['candidate_manifest']);verify(p.parent,report['raw_manifest'])
    return STRUCTURE_SHA


@contextmanager
def literal_scope():
    original_pipeline=previous.pipeline
    def literal_pipeline(phases,launch,emit,*,experiment):
        label=experiment.replace('P106B_GEMMA_OUTPUT_V2_','P106B_GEMMA_LITERAL_V3_',1)
        return original_pipeline(phases,launch,emit,experiment=label)
    with ExitStack() as stack:
        for name,value in (('tasks',tasks),('PILOTS',PILOTS),('PATHS',PATHS),('TAG',TAG),
                           ('REGRESSION',REGRESSION),('require_structure4',require_pinned_structure4),
                           ('pipeline',literal_pipeline)):
            stack.enter_context(patch.object(previous,name,value))
        yield


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('contract16','family64','produce','resume','finalize','wire','train','eval'),required=True)
    parser.add_argument('--max-wall-sec',type=int,default=21600)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    child=['literal','--mode',args.mode]
    if args.check_only:child.append('--check-only')
    elif args.execute:child.append('--execute')
    if '--max-wall-sec' in sys.argv:child+=['--max-wall-sec',str(args.max_wall_sec)]
    print('[LITERAL_CONTRACT] '+json.dumps(dict(version=tasks.CONTRACT,
        gate_policy='STRICT16_STRICT64_UNCHANGED',prior_structure4_sha256=STRUCTURE_SHA,
        prior_structure4_reuse='unchanged explicit complex path; current V3 complex generation NOT_RUN',
        model_student_coload='NOT_RUN',adaptive_validation_feedback='NOT_IMPLEMENTED'),ensure_ascii=False),flush=True)
    with literal_scope(),patch.object(sys,'argv',child):
        return previous.main()


if __name__=='__main__':raise SystemExit(main())
