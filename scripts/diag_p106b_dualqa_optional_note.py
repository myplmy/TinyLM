#!/usr/bin/env python3
"""Saved-response reparse and a separate actual v2 pilot; original v1 immutable."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
from contextlib import ExitStack,contextmanager
from datetime import datetime,timezone
import copy
import json
from unittest.mock import patch
from scripts import diag_p106b_dualqa_teacher as driver
from scripts import p106b_dualqa_optional_note as method
from scripts.p106b_gate_runtime import GateNegative
TAG='p106b_dualqa_teacher_pilot_v2_s1337'
OUTPUT=ROOT/'HF/sft_ready'/TAG
EVIDENCE=ROOT/'test_result/evidence'/TAG
READBACK=ROOT/'test_result/evidence/p106b_dualqa_note_reparse_v2_s1337'
SOURCE_TAG=driver.TAG
SOURCE_OUTPUT=driver.OUTPUT
SOURCE_INFO=driver.info
ORIGINAL_PAYLOAD=driver.method.payload
CODE=(*driver.CODE,'scripts/p106b_dualqa_optional_note.py','scripts/diag_p106b_dualqa_optional_note.py',
      'scripts/test_p106b_dualqa_optional_note.py')


def old_inputs():
    r=driver.source.required(SOURCE_OUTPUT/'report.json')
    if r['status']!='DUALQA_TEACHER_PILOT_COLLECTED' or r['error'] is not None:raise GateNegative('completed immutable v1 collection required, not v1 wire PASS')
    if r['code_sha256']!=SOURCE_INFO()['code_sha256']:raise ValueError('v1 pilot code changed')
    items=list(driver.source.public.stream_rows(SOURCE_OUTPUT,r['source_manifest']))
    if len(items)!=8:raise ValueError('same8 sources required')
    return r,items


def info(old):
    value=SOURCE_INFO();value.update(schema=method.VERSION,tag=TAG,
        code_sha256={p:driver.source.public.digest(ROOT/p) for p in sorted(set(CODE))},
        original_v1_report_sha256=driver.source.public.digest(SOURCE_OUTPUT/'report.json'),
        original_v1_verdict_preserved=True,original_v1_wire_ready=old['technical_wire_ready'],
        required_fields='Q1/A1 and Q2/A2 when requested; NOTE optional and code-owned default',
        no_preface_or_reasoning_extraction=True,shared_sources_sha256=old['source_manifest']['concat_sha256'],
        same_v1_source_root_attempt_seeds=True,
        prompt_revision='optional NOTE, concise local fact selection, source-relative temporal scope',
        process_local_overrides=['messages','parse_fields','VERSION','payload seed remap','fresh output paths'],
        reparse_is_not_a_new_gpu_run=True)
    return value


def seed(tag,root,attempt):return int(driver.method.sha([tag,root,attempt])[:12],16)%(2**31-1)


def remapped_payload(job,n,new_seed,feedback=''):
    for attempt in range(1,driver.method.MAX_ATTEMPTS+1):
        if new_seed==seed(TAG,job['root'],attempt):
            return ORIGINAL_PAYLOAD(job,n,seed(SOURCE_TAG,job['root'],attempt),feedback)
    raise ValueError('declared source/root/attempt seed required')


@contextmanager
def runtime(old,items,run_info):
    with ExitStack() as stack:
        for name,value in dict(TAG=TAG,OUTPUT=OUTPUT,EVIDENCE=EVIDENCE,
                jobs=lambda tok:(copy.deepcopy(items),old),info=lambda:copy.deepcopy(run_info)).items():
            stack.enter_context(patch.object(driver,name,value))
        for name,value in dict(messages=method.messages,parse_fields=method.parse_fields,
                VERSION=method.VERSION,payload=remapped_payload).items():
            stack.enter_context(patch.object(driver.method,name,value))
        yield


def reparse(old):
    from tokenizers import Tokenizer
    if READBACK.exists():raise GateNegative('old readback preserved')
    tok=Tokenizer.from_file(str(driver.source.public.TOKENIZER));counter=Counter();groups={};failures=Counter();rows=[]
    for raw in driver.source.public.stream_rows(SOURCE_OUTPUT,old['raw_manifest']):
        if 'channels' not in raw:raise ValueError('HTTP/nonreply record is not reparsed as content')
        counter['actual_old_physical_reply_rows']+=1
        key=(raw['order'],raw['requested_pairs'],raw['job']['root']);fields=None;reason=''
        try:
            if raw['channels']['finish_reason']!='stop':raise ValueError('old reply incomplete')
            fields=method.parse_fields(raw['channels']['final'],raw['requested_pairs'])
            if fields['status']=='QA_FIELDS_COMPLETE':
                driver.method.wrap(raw['job'],fields,tok,record_id=raw['raw_record_id'])
                if raw['requested_pairs']==2:driver.method.wrap(raw['job'],fields,tok,repeat_first=True,record_id=raw['raw_record_id'])
                counter['reparsed_content_complete_rows']+=1
                counter['empty_note_defaulted_rows']+=fields['empty_note_filled_by_code']
                if key not in groups:groups[key]=dict(order=key[0],pairs=key[1],root=key[2],language=raw['job']['language'],
                    first_valid_old_attempt=raw['attempt'],raw_record_id=raw['raw_record_id'])
        except ValueError as exc:reason=str(exc);failures[reason]+=1
        rows.append(dict(raw_record_id=raw['raw_record_id'],order=raw['order'],pairs=raw['requested_pairs'],
            root=raw['job']['root'],attempt=raw['attempt'],new_content_complete=bool(fields and fields['status']=='QA_FIELDS_COMPLETE' and not reason),
            optional_note_defaulted=bool(fields and fields.get('empty_note_filled_by_code')),remaining_structural_reason=reason))
    result=dict(info(old),status='SAVED_V1_RESPONSES_REPARSED',counts=dict(counter),remaining_failures=dict(failures),
        logical_groups_with_valid_saved_content=len(groups),logical_qa_in_valid_groups=sum(x['pairs'] for x in groups.values()),
        groups=list(groups.values()),row_outcomes=rows,model_loading=False,new_gpu_requests=0,source_raw_edited=False,
        actual_old_physical_request_cost_not_subtracted=True,hypothetical_early_stop_speed_claim=False,
        old_original_acceptance=old['candidate_conversations'],world_truth='NOT_RUN',
        scope='same saved outputs under an optional-metadata parser; NOT a fresh runtime/quality result')
    driver.source.training.write(READBACK/'report.json',result)
    print('[OPTIONAL_NOTE_SAVED_REPARSE] '+json.dumps({k:result[k] for k in ('status','counts','logical_groups_with_valid_saved_content','logical_qa_in_valid_groups','remaining_failures','new_gpu_requests')}),flush=True)
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('reparse','pilot'),required=True)
    p.add_argument('--max-wall-sec',type=int,default=3600)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=3600:p.error('bounded60..3600')
    try:
        old,items=old_inputs();run_info=info(old)
        if a.check_only:print('[OPTIONAL_NOTE_CHECK_ONLY] '+json.dumps(run_info));return 0
        if not a.execute:p.error('explicit execution required')
        if a.mode=='reparse':return reparse(old)
        driver.source.deadline();a.max_wall_sec=min(a.max_wall_sec,int((driver.source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-600)
        if a.max_wall_sec<60:raise GateNegative('authorized deadline margin')
        with runtime(old,items,run_info):return driver.execute(a)
    except GateNegative as exc:print('[OPTIONAL_NOTE_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[OPTIONAL_NOTE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
