"""Fresh implicit-missing / supported / common-QA / arithmetic first-answer panel."""
from __future__ import annotations
import argparse
import gc
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import diag_p101a_sft_mtp as training
from scripts.diag_p101a_mtp_parity import PrecisionForward,CaptureTokens
from scripts.diag_p106b_context_quality import exact
from scripts.p106b_shards import ShardWriter,verify
SOURCE=ROOT/'test_result/evidence/p106b_context_clarify_v1_s1337'
TARGET=ROOT/'test_result/evidence/p106b_context_transfer_v1_s1337'
BROAD=False


def cases():
    data=[]
    queries={'ko':[
        '2013년에 완공된 건물에는 무엇이 들어서 있습니까?',
        '대통령이 어떤 장소에서 연설을 했나요?',
        '그 도서관은 어디에 있나요?',
        '그 사람이 쓴 책의 제목은 무엇인가요?'],
        'en':['What institution is inside the building completed in 2013?',
              'Where did the president give the speech?',
              'Where is that library?',
              'What is the title of the book that person wrote?']}
    refs={'ko':[
        ('가상 자료: 2013년 준공 연구관에는 전자공학과가 있고, 2014년 준공 경영관에는 회계학과가 있습니다.','전자공학과'),
        ('가상 기록: 김 대표 대통령은 서연공원에서 연설했습니다.','서연공원'),
        ('가상 자료: 새봄도서관의 위치는 산호마을 광장 동쪽입니다.','산호마을 광장 동쪽'),
        ('가상 기록: 작가 민수가 쓴 책의 제목은 푸른길입니다.','푸른길')],
        'en':[
        ('Fictional record: the hall completed in2013 houses Physics; the hall completed in2014 houses History.','Physics'),
        ('Fictional record: President Mina gave the speech in Cedar Park.','Cedar Park'),
        ('Fictional record: Dawn Library is east of Coral Square.','east of Coral Square'),
        ('Fictional record: the author Noah wrote a book titled Blue Road.','Blue Road')]}
    for language in ('ko','en'):
        for i,q in enumerate(queries[language]):
            data.append(dict(id=f'{language}_implicit_{i}',group='IMPLICIT_MISSING',language=language,
                question=q,gold=None,rubric='CLARIFICATION_POSTHOC'))
            ref,gold=refs[language][i]
            instruction='자료에 있는 답 내용만 쓰세요.' if language=='ko' else 'Give only the answer from the record.'
            data.append(dict(id=f'{language}_supported_{i}',group='SUPPORTED_NEW_VALUE',language=language,
                question=ref+'\n'+q+'\n'+instruction,gold=gold,rubric='EXACT_SCALAR'))
    for ident,language,q,gold,group in (
        ('ko_capital1','ko','대한민국의 수도 이름만 한 단어로 답하세요.','서울','COMMON_QA'),
        ('ko_capital2','ko','프랑스의 수도 이름만 한 단어로 답하세요.','파리','COMMON_QA'),
        ('en_capital1','en','Give only the capital of South Korea.','Seoul','COMMON_QA'),
        ('en_capital2','en','Give only the capital of France.','Paris','COMMON_QA'),
        ('ko_smallmath1','ko','2+3의 결과를 정수 하나로만 답하세요.','5','SMALL_ARITHMETIC'),
        ('ko_smallmath2','ko','7-4의 결과를 정수 하나로만 답하세요.','3','SMALL_ARITHMETIC'),
        ('en_smallmath1','en','Calculate 2+3. Reply with one integer only.','5','SMALL_ARITHMETIC'),
        ('en_smallmath2','en','Calculate 7-4. Reply with one integer only.','3','SMALL_ARITHMETIC')):
        data.append(dict(id=ident,group=group,language=language,question=q,gold=gold,
            rubric='EXACT_INTEGER' if group=='SMALL_ARITHMETIC' else 'EXACT_SCALAR'))
    return data


def preflight():
    if TARGET.exists() or TARGET.is_symlink():raise FileExistsError('test output exists; preserve it')
    subjects=[dict(id='parent',path=str(training.PARENT.relative_to(ROOT)),sha=training.PARENT_SHA)]
    for name in (('ntp_hi','ntp_mid') if BROAD else ('ntp_hi','ntp_lo','mtp_hi')):
        p=SOURCE/name/'report.json';d=json.loads(p.read_text())
        if d['status']!='CONTEXT_SFT_COMPLETE_REVIEW_PENDING' or d['updates']!=(256 if BROAD else 128):
            raise FileNotFoundError('completed exact course arm required')
        subjects.append(dict(id=name,path=d['checkpoint'],sha=d['checkpoint_sha256'],
            report=str(p.relative_to(ROOT)),report_sha=training.data.digest(p)))
    for s in subjects:
        p=ROOT/s['path']
        if p.is_symlink() or training.data.digest(p)!=s['sha']:raise ValueError('saved weights changed')
    if training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:raise ValueError('tokenizer changed')
    return subjects,dict(schema='P106B_CONTEXT_TRANSFER_FIRST_ANSWER_V1',subjects=subjects,
        case_sha256=training.data.text_digest(json.dumps(cases(),sort_keys=True,ensure_ascii=False)) if hasattr(training.data,'text_digest')
            else __import__('hashlib').sha256(json.dumps(cases(),sort_keys=True,ensure_ascii=False).encode()).hexdigest().upper(),
        tokenizer_sha256=training.data.TOK_SHA,code_sha256={p:training.data.digest(ROOT/p) for p in
            ('scripts/diag_p106b_context_transfer.py','scripts/diag_p106b_context_quality.py',
             'scripts/diag_p101a_mtp_parity.py','tinylm/infer/generate.py')},
        world_reference_scope='four elementary capital references, not a broad independently verified benchmark',
        max_new=64,precision='FP32_MATH_NO_TF32',cache=True,mtp_tokens=1,training='NOT_RUN',checkpoint_save=False,
        test_scope='DEVELOPMENT_REPEAT_NOT_INDEPENDENT' if BROAD else 'FRESH_FIRST_PANEL')


def execute(args):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model,sample
    from tinylm.chat.serialize import serialize
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    subjects,info=preflight();idle_before_gpu();TARGET.mkdir(parents=True,exist_ok=False)
    writer=ShardWriter(TARGET,'answers');began=time.perf_counter();summaries=[];rc=9;status='STARTED'
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    tok=Tokenizer.from_file(str(training.data.TOKENIZER))
    try:
        with wall_limit(args.max_wall_sec),torch.no_grad():
            for subject in subjects:
                base,cfg,_=load_model(ckpt_path=ROOT/subject['path'],device='cuda',mtp_heads='off')
                model=PrecisionForward(base,'fp32_math')
                for case in cases():
                    prompt=serialize(dict(messages=[dict(role='user',content=case['question'])]),'chatml',add_generation_prompt=True)
                    wrapped=CaptureTokens(tok)
                    decoded,meta=sample(model,cfg,wrapped,prompt,max_new=64,temperature=0.,top_k=1,
                        device='cuda',logits_last_only=True,return_metadata=True,
                        stop_token_sequences=[tok.encode('<|im_end|>').ids])
                    prefix=tok.decode(tok.encode(prompt).ids)
                    if not decoded.startswith(prefix):raise ValueError('prompt extraction failed')
                    answer=decoded[len(prefix):]
                    judged=exact(answer,case['gold'],case['rubric']) if case['gold'] is not None else None
                    record=dict(case,subject=subject['id'],answer=answer,generated_ids=wrapped.decoded_ids[len(tok.encode(prompt).ids):],
                        generation=meta,exact_reference_contract=judged,free_clarification='PENDING_OFFLINE_REVIEW')
                    writer.append(record);summaries.append({k:record[k] for k in ('id','subject','group','exact_reference_contract')})
                    print('[IMPLICIT_TRANSFER_ANSWER] '+json.dumps({k:record[k] for k in
                        ('id','subject','group','question','answer','gold','exact_reference_contract')},ensure_ascii=False),flush=True)
                del model,base;gc.collect();torch.cuda.empty_cache()
        rc=0;status='CONTEXT_TRANSFER_COLLECTION_COMPLETE'
    except BaseException as exc:
        rc=130 if isinstance(exc,KeyboardInterrupt) else 9;status='INTERRUPTED' if rc==130 else 'EXECUTION_ERROR'
        info['error']=dict(type=type(exc).__name__,reason=str(exc)[:1000])
    finally:
        manifest=writer.close(lineage=info);verify(TARGET,manifest)
        training.write(TARGET/'report.json',dict(info,status=status,returncode=rc,results=summaries,
            raw_manifest=manifest,whole_sec=time.perf_counter()-began,
            model_adopted=False,semantic_free_questions='PENDING_GPT_OFFLINE',
            future_training_with_this_test='FORBIDDEN_CURRENT_COMPARISON'))
    return rc


def main():
    global BROAD,SOURCE,TARGET
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=600)
    p.add_argument('--broad',action='store_true',help='reuse old24 development cases, never call independent test')
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=900:p.error('bounded evaluation required')
    if a.broad:
        BROAD=True;SOURCE=ROOT/'test_result/evidence/p106b_context_broad_v2_s1337'
        TARGET=ROOT/'test_result/evidence/p106b_context_transfer_broaddev_v2_s1337'
    if a.check_only:print('[CHECK_ONLY] '+json.dumps(preflight()[1]));return 0
    return execute(a)

if __name__=='__main__':raise SystemExit(main())
