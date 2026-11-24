"""Recount fresh raw answers and save ROOT's explicit human-readable review."""
from pathlib import Path
from collections import Counter
import json
from scripts import diag_p108b_norm_sweep as study
from scripts import diag_p108b_policy as raw
from scripts import p108b_policy as flags
from scripts import p108_weight_space as metrics
from scripts import interactive_research_infer as manual
from scripts import diag_p108b_value_library as library

BASE=study.BASE;ROOT=study.ROOT
READABLE=ROOT/'review_request/20261116_PM_P108B_새질문_원본편집_대응_v1'

# Ordered open turns: first and follow-up for topics0..7,then first turns8..15.
# G=grammar,N=naturalness,R=answer relevance,each0..2;A=adequate full request0/1.
# These are ROOT judgments after reading every actual answer, not classifier output.
ROOT_SCORES={
 ('ko','original'):[(2,2,2,1),(2,2,2,1),(0,0,1,0),(0,0,0,0),(2,1,0,0),(2,1,0,0),
 (1,0,1,0),(2,1,1,0),(0,0,0,0),(0,0,0,0),(1,0,1,0),(1,0,1,0),
 (1,0,0,0),(2,1,0,0),(1,0,1,0),(0,0,1,0),(2,1,0,0),(0,0,0,0),
 (0,0,0,0),(1,0,0,0),(1,0,1,0),(2,1,0,0),(0,0,0,0),(0,0,0,0)],
 ('ko','edited'):[(2,2,2,1),(2,2,2,1),(0,0,1,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),
 (0,0,1,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(2,1,1,0),(0,0,1,0),
 (2,1,0,0),(2,1,0,0),(0,0,1,0),(0,0,1,0),(0,0,1,0),(0,0,0,0),
 (0,0,1,0),(0,0,0,0),(0,0,1,0),(0,0,0,0),(0,0,0,0),(2,0,0,0)],
 ('en','original'):[(1,0,1,0),(2,0,1,0),(2,1,0,0),(1,0,0,0),(2,1,2,1),(2,0,1,0),
 (0,0,1,0),(0,0,1,0),(2,1,0,0),(2,0,0,0),(2,1,1,0),(1,0,1,0),
 (1,0,1,0),(0,0,0,0),(2,1,0,0),(2,0,0,0),(2,1,0,0),(2,1,0,0),
 (2,1,1,0),(1,0,1,0),(2,0,1,0),(2,1,1,0),(2,1,0,0),(1,0,0,0)],
 ('en','edited'):[(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),
 (0,0,1,0),(2,1,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),
 (0,0,0,0),(0,0,0,0),(2,1,0,0),(2,1,0,0),(0,0,0,0),(2,1,1,0),
 (0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,1,0)]}


def run():
    selected=study.read(BASE/'norm_selection_v1.json')['name'];names=['original',selected]
    reports={};answers={};sources={};summaries={};manual_rows=[]
    for name in names:
        directory=BASE/'pm_fresh_final_v1'/name;path=directory/'report.json';r=study.read(path)
        if(r['status']!='FRESH_FINAL_COMPLETE_ROOT_REVIEW_PENDING' or not r['original_core_restored'] or
                r['cuda_allocated_after_bytes'] or r['cuda_reserved_after_bytes']):
            raise ValueError('two closed native final states with complete cleanup required')
        rows=raw.read_answers(directory,r['answers_manifest'])
        if metrics.summarize(rows)!=r['summary']:raise ValueError('raw full summary differs')
        for row in rows:
            if row['exact']!=(None if row['expected'] is None else metrics.exact_answer(row['answer'],row['expected'])):
                raise ValueError('raw strict answer owner differs')
        sources[name]=dict(path=str(path.relative_to(ROOT)),sha256=manual.file_sha(path));answers[name]=rows
        summaries[name]=dict(summary=r['summary'],unwanted_loops=flags.unwanted_loops(rows),
            languages={},full_input_role='POST_DEV_FROZEN_FRESH_FINAL_NO_RESELECTION')
        for language in ('ko','en'):
            panel=[x for x in rows if x['language']==language]
            open_rows=[x for x in panel if x['family']=='open']
            scores=ROOT_SCORES[(language,'original' if name=='original' else 'edited')]
            if len(scores)!=len(open_rows) or len(open_rows)!=24:raise ValueError('complete24 open turns/language review')
            for row,score in zip(open_rows,scores):
                manual_rows.append(dict(model=name,id=row['id'],language=language,turn=row['turn'],
                    grammar=score[0],naturalness=score[1],relevance=score[2],adequate=score[3],
                    actual_question=row['question'],actual_answer=row['answer'],actual_history=row['actual_history']))
            summaries[name]['languages'][language]=dict(
                family={f:dict(n=len([x for x in panel if x['family']==f]),
                    scored=sum(x['expected']is not None for x in panel if x['family']==f),
                    exact=sum(bool(x['exact'])for x in panel if x['family']==f)) for f in ('target','other','protect')},
                open_turns=24,grammar_complete=sum(s[0]==2 for s in scores),natural_2=sum(s[1]==2 for s in scores),
                relevant_2=sum(s[2]==2 for s in scores),adequate=sum(s[3]for s in scores),
                initial_adequate=sum(s[3]for row,s in zip(open_rows,scores) if row['turn']==1),
                literal_Rome_replies=sum(x['answer']=='Rome'for x in panel),
                missing_referent_clarification_adequate=0)
        reports[name]=r
    before,after=(answers[n] for n in names)
    pairs=[]
    for a,b in zip(before,after):
        if any(a[k]!=b[k]for k in ('id','question','expected','language','family','turn')):
            raise ValueError('paired exact inputs/order differ')
        pairs.append(dict(id=a['id'],question=a['question'],expected=a['expected'],language=a['language'],family=a['family'],
            actual_original=a,actual_edited=b))
    if len(pairs)!=144 or len(manual_rows)!=96:raise ValueError('exact144 pairs and96 fully read open utterances')
    if READABLE.exists():raise FileExistsError('preserve previous reading pack')
    READABLE.mkdir();parts=[]
    for start in range(0,len(pairs),24):
        group=pairs[start:start+24];path=READABLE/f'paired_answers_{start//24+1:03d}.txt'
        lines=['새 질문의 원본·동결 편집 모델 실제 답변','각 후속 답변은 해당 모델 자신의 앞 답변을 문맥으로 받았습니다.','']
        for row in group:
            lines.extend([row['id'],'질문> '+row['question'],'원본 답변> '+row['actual_original']['answer'],
                '편집 답변> '+row['actual_edited']['answer'],'엄격 기준> '+str(row['expected']),''])
        with path.open('x',encoding='utf-8') as stream:stream.write('\n'.join(lines)+'\n')
        parts.append(dict(path=str(path.relative_to(ROOT)),sha256=manual.file_sha(path)))
    library.write_new(READABLE/'SOURCE_PAIRS_v1.json',dict(sources=sources,pairs=pairs))
    findings=dict(schema='P108B_PM_FRESH_ROOT_REVIEW_V1',sources=sources,manual_scores=manual_rows,summaries=summaries,
        rubric=dict(grammar='0 broken/fragment,1 recoverable with defects,2 grammatical complete unit appropriate to request',
            naturalness='0 broken/repetitive or not a natural reply,1 understandable but awkward,2 natural',
            relevance='0 does not answer,1 partial/topical without enough substance,2 directly answers',
            adequate='1 sufficiently satisfies the whole request;does not follow merely from sentence grammar'),
        judgment_scope='ROOT judgment,not blind second-rater validation;96 actual open turns plus16 missing-referent replies read in full',
        short_correct_answer_policy='single words/formulae may be valid answers;H2O for plant needs is recorded as partial relevant information',
        strict_results_recounted=True,selection_not_changed=True,formal_training_or_adoption_claim=False,
        instruction_defect='some Korean number/repeat templates choose 를 without checking final consonants;preserve all128/88 primary,do not edit questions or rescore English failures away',
        limitations='same facts across paraphrases/languages are clustered;pretraining overlap unknown;no general intelligence inference',parts=parts)
    library.write_new(READABLE/'ROOT_REVIEW_v1.json',findings)
    library.write_new(ROOT/'handoff/audit/nov16_pm_p108b/FRESH_LANGUAGE_READBACK_v1.json',findings)
    print(json.dumps(summaries,ensure_ascii=False))


if __name__=='__main__':run()
