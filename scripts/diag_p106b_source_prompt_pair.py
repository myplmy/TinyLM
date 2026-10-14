"""Read-only common-source common-prompt pair; pseudo agreement is not truth."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
from collections import defaultdict
import json
from unittest.mock import patch
from scripts import diag_p106b_source_course as course
from scripts import diag_p106b_source_format_mix as mix
from scripts import diag_p106b_context_transfer as engine
from scripts.p106b_shards import verify
TAG='p106b_source_prompt_pair_v1_s1337'
LOCAL=ROOT/'test_result/evidence/local'/TAG
EVIDENCE=ROOT/'test_result/evidence'/TAG


def cases():
    _,rows=course.read_course()
    teacher=json.loads((course.OUTPUT/'teacher/report.json').read_text())
    questions={r['item']['root']:r['question'] for r in
        course.public.stream_rows(course.OUTPUT/'teacher',teacher['candidate_manifest'])}
    result=[]
    for row in rows['val'][:64]:
        if row['meta']['kind']!='source_qa':continue
        root=row['meta']['parent_concept_id'];gold=course.support.text(row['messages'][-1])
        for natural in (False,True):
            edited=mix.transform(row,questions[root],natural)
            group='NATURAL' if natural else 'CONTROLLED'
            result.append(dict(id=row['meta']['language']+'_'+root[:12]+'_'+group,
                root=root,group=group,language=row['meta']['language'],
                family=row['meta']['course_family'],question=course.support.text(edited['messages'][0]),
                gold=gold,rubric='CLARIFICATION_POSTHOC'))
    if len(result)!=64 or len({r['root'] for r in result})!=32:raise ValueError('same32 source pair required')
    return result


def preflight():
    if LOCAL.exists() or EVIDENCE.exists():raise FileExistsError('preserve prior prompt pair')
    subjects=[dict(id='parent',path=str(course.training.PARENT.relative_to(ROOT)),sha=course.training.PARENT_SHA)]
    for folder,arm,name in ((course.EVIDENCE,'sft_only','sft_only'),
                           (course.EVIDENCE,'reference_lm','reference_lm'),
                           (mix.EVIDENCE,'sft_only','format_mix')):
        r=json.loads((folder/(arm+'_report.json')).read_text())
        if r['updates']!=32:raise ValueError('completed32 endpoint required')
        if course.public.digest(ROOT/r['checkpoint'])!=r['checkpoint_sha256']:raise ValueError('saved checkpoint changed')
        subjects.append(dict(id=name,path=r['checkpoint'],sha=r['checkpoint_sha256']))
    if course.public.digest(course.training.PARENT)!=course.training.PARENT_SHA:raise ValueError('parent changed')
    if course.public.digest(course.public.TOKENIZER)!=course.public.TOK_SHA:raise ValueError('tokenizer changed')
    return subjects,dict(schema='P106B_SOURCE_PROMPT_PAIR_V1',subjects=subjects,
        case_sha256=course.support.sha(cases()),code_sha256={p:course.public.digest(ROOT/p) for p in
        ('scripts/diag_p106b_source_prompt_pair.py','scripts/diag_p106b_context_transfer.py',
         'scripts/diag_p106b_source_format_mix.py','tinylm/infer/generate.py')},
        tokenizer_sha256=course.public.TOK_SHA,precision='FP32_MATH_NO_TF32',cache=True,mtp_tokens=1,
        max_new=64,training='NOT_RUN',checkpoint_save=False,
        test_scope='SAME_FROZEN_SOURCE32_PROMPT_PAIR; DEVELOPMENT_NOT_INDEPENDENT_WORLD_TEST',
        semantic_truth='PSEUDO_UNVERIFIED; offline source-faithfulness review only')


def summarize(rows):
    matrix=defaultdict(lambda:dict(cases=0,literal_agreement=0,empty=0,max_new=0))
    for row in rows:
        key=row['subject']+':'+row['group'];v=matrix[key];v['cases']+=1
        v['literal_agreement']+=row['answer'].strip()==row['gold'].strip()
        v['empty']+=not row['answer'].strip()
        # Missing metadata must never silently become a zero count.
        v['max_new']+=row['generation']['finish_reason'] in ('MAX_NEW','MAX_NEW_EOS_DISABLED')
    return dict(matrix)


def collect(args):
    with patch.object(engine,'TARGET',LOCAL),patch.object(engine,'preflight',preflight),patch.object(engine,'cases',cases):
        rc=engine.execute(args)
    report=json.loads((LOCAL/'report.json').read_text());verify(LOCAL,report['raw_manifest'])
    matrix=summarize(course.public.stream_rows(LOCAL,report['raw_manifest']))
    report.update(descriptive_counts=dict(matrix),local_raw=str(LOCAL.relative_to(ROOT)),
                  literal_agreement_not_truth=True,model_adopted=False)
    course.training.write(EVIDENCE/'report.json',report)
    print('[COMMON_PROMPT_PAIR] '+json.dumps(dict(matrix)));return rc


def readback():
    out=EVIDENCE/'corrected_report.json'
    if out.exists():raise FileExistsError('corrected evidence preserved')
    original=LOCAL/'report.json';report=json.loads(original.read_text())
    verify(LOCAL,report['raw_manifest'])
    corrected=summarize(course.public.stream_rows(LOCAL,report['raw_manifest']))
    prior=json.loads((EVIDENCE/'report.json').read_text())['descriptive_counts']
    report.update(status='CPU_FINISH_COUNTER_READBACK_COMPLETE',descriptive_counts=corrected,
        original_report_sha256=course.public.digest(original),original_summary_sha256=course.public.digest(EVIDENCE/'report.json'),
        original_counter_error='max_new read stop_reason instead of actual finish_reason; original raw and report immutable',
        executed_code_git='cf3ee25',corrected_code_sha256=course.public.digest(Path(__file__)),
        changed_only='MAX_NEW_COUNTS; raw answers/literal agreement/empty counts unchanged',
        old_counts=prior,training='NOT_RUN',models_loaded=0,local_raw=str(LOCAL.relative_to(ROOT)))
    for key,value in corrected.items():
        if any(value[k]!=prior[key][k] for k in ('cases','literal_agreement','empty')):
            raise ValueError('unrelated count changed')
    course.training.write(out,report);print('[FINISH_COUNTER_READBACK] '+json.dumps(corrected));return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=600)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');g.add_argument('--readback',action='store_true')
    args=p.parse_args()
    if not 60<=args.max_wall_sec<=900:p.error('bounded60..900')
    if args.check_only:print('[CHECK_ONLY] '+json.dumps(preflight()[1]));return 0
    if args.readback:return readback()
    return collect(args)

if __name__=='__main__':raise SystemExit(main())
