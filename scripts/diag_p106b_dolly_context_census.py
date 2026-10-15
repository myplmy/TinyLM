#!/usr/bin/env python3
"""Pinned cached Dolly context/span census; no model, semantic judge or admission."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import time
from scripts.p106b_shards import ShardWriter,verify
from tinylm.chat.canonical import normalize,validate
TAG='p106b_dolly_context_census_v1_s1337'
OUTPUT=ROOT/'HF/sft_ready'/TAG
EVIDENCE=ROOT/'test_result/evidence'/TAG
INVENTORY=ROOT/'HF/sft_ready/p106b_capability_source_inventory_v1/report.json'
TOKENIZER=ROOT/'data_cache/tok-ko-en-32768-chat32.json'
TOK_SHA='9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
SOURCES={'en':'HF/sft_sources/p106b_aya_collection_en_a3af2fde/english/train-00003-of-00007.parquet',
         'ko':'HF/sft_sources/aya_collection_ko/korean/train-00001-of-00002.parquet'}
MARKER='\nContext:'
DEADLINE=datetime(2026,10,15,8,0,tzinfo=timezone.utc)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(16*2**20),b''):h.update(chunk)
    return h.hexdigest().upper()


def declared_language(spec,language):
    if language not in ('ko','en') or spec.get('language',language)!=language:
        raise ValueError('declared source language mismatch')
    return {**spec,'language':language}


def exact_span(question,answer):
    count=question.count(MARKER)
    if count!=1:return dict(status='NO_UNIQUE_CONTEXT_MARKER',marker_count=count)
    split=question.index(MARKER);start=split+len(MARKER);context=question[start:]
    if not question[:split].strip() or not context.strip() or not answer.strip():
        return dict(status='EMPTY_QUESTION_CONTEXT_OR_TARGET',marker_count=count)
    hits=[];position=0
    while True:
        found=context.find(answer,position)
        if found<0:break
        hits.append(found);position=found+1
        if len(hits)>1:break
    if len(hits)!=1:return dict(status='NO_UNIQUE_LITERAL_TARGET',marker_count=count,occurrences_at_least=len(hits),context_start=start)
    a=start+hits[0];b=a+len(answer)
    if question[a:b]!=answer:raise ValueError('literal source slice differs')
    return dict(status='UNIQUE_LITERAL_SPAN',marker_count=count,context_start=start,context_end=len(question),answer_start=a,answer_end=b,
        scope='technical exact alignment only; not answer correctness')


def token_span(question,answer,span,tok):
    from tinylm.chat.serialize import serialize
    prefix=serialize(dict(messages=[dict(role='user',content=question)]),'chatml',add_generation_prompt=True)
    if prefix.count(question)!=1:raise ValueError('unambiguous full user body location required')
    origin=prefix.index(question);encoded=tok.encode(prefix)
    lo=origin+span['context_start'];hi=origin+span['context_end'];end=origin+span['answer_end']
    positions=[i for i,(a,b) in enumerate(encoded.offsets) if a<hi and b>lo]
    touching=[i for i,(a,b) in enumerate(encoded.offsets) if a<end and b>end-1]
    if not positions or not touching:raise ValueError('source/token endpoint unavailable')
    target=max(touching);predictor=len(encoded.ids)-1
    if target not in positions or positions[-1]>=predictor:raise ValueError('reference must precede assistant predictor')
    return dict(reference_token_positions=positions,answer_end_token=target,assistant_predictor=predictor,
        prefix_tokens=len(encoded.ids),offset_unit='UNICODE_CHAR',prefix_has_answer_body=False)


def metadata():
    r=json.loads(INVENTORY.read_text());specs={s['path']:s for s in r['input']['sources']}
    if digest(TOKENIZER)!=TOK_SHA:raise ValueError('tokenizer changed')
    selected=[]
    for language,path in SOURCES.items():
        p=ROOT/path
        if p.is_symlink() or not p.resolve().is_relative_to((ROOT/'HF/sft_sources').resolve()):
            raise ValueError('only exact regular cached public sources allowed')
        selected.append(declared_language(specs[path],language))
    return dict(schema='P106B_CACHED_DOLLY_CONTEXT_CENSUS_V1',tag=TAG,sources=selected,
        tokenizer_sha256=TOK_SHA,inventory_sha256=digest(INVENTORY),
        code_sha256={p:digest(ROOT/p) for p in ('scripts/diag_p106b_dolly_context_census.py','scripts/test_p106b_dolly_context_census.py')},
        collection_card='https://huggingface.co/datasets/CohereLabs/aya_collection_language_split',collection_card_license='Apache-2.0',
        underlying_card='https://huggingface.co/datasets/databricks/databricks-dolly-15k',underlying_card_license='CC-BY-SA-3.0',
        rights_status='ISOLATED_CANDIDATES; no blanket subsource clearance or legal conclusion',
        student_training_allowed=False,semantic_truth='NOT_REVIEWED',source_unchanged=True,models_loaded=0,gpu_used=False,downloads=0,
        counter_scope='raw serialization counts; no new followups/source cap/dedup/75M eligibility applied')


def execute(args):
    import pyarrow.dataset as ds
    from tokenizers import Tokenizer
    from tinylm.train.mtp_sft import encode_record
    from scripts.p106b_gate_runtime import wall_limit
    info=metadata()
    if OUTPUT.exists() or EVIDENCE.exists():raise FileExistsError('prior census preserved')
    for spec in info['sources']:
        if digest(ROOT/spec['path'])!=spec['sha256']:raise ValueError('pinned source changed')
    tok=Tokenizer.from_file(str(TOKENIZER));OUTPUT.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    writers={};counts={};identities={};manifests={};status='CENSUS_ERROR';rc=9;error=None
    try:
        with wall_limit(args.max_wall_sec):
            for spec in info['sources']:
                language=spec['language'];totals=Counter();questions=set();contexts=set();tasks=Counter();counts[language]=totals
                scanner=ds.dataset(ROOT/spec['path'],format='parquet').scanner(
                    columns=['id','inputs','targets','dataset_name','task_type','template_id','sub_dataset_name'],
                    filter=ds.field('dataset_name').isin(['Dolly-v2','Dolly-v2 (T)']),batch_size=512,use_threads=False)
                for batch in scanner.to_batches():
                    if datetime.now(timezone.utc)>=DEADLINE:raise TimeoutError('17:00 deadline')
                    for raw in batch.to_pylist():
                        q,a=raw['inputs'],raw['targets'];totals['rows']+=1;tasks[str(raw['task_type'])]+=1
                        if not isinstance(q,str) or not isinstance(a,str) or not q.strip() or not a.strip():
                            totals['blank_or_nontext_rows']+=1;continue
                        row=validate(normalize(dict(messages=[dict(role='user',content=q),dict(role='assistant',content=a)],
                            meta=dict(source='CACHED_DOLLY_ALIGNMENT_CANDIDATE',source_repo=spec['repo'],
                                source_revision=spec['revision'],source_family=raw['dataset_name'],source_id=str(raw['id']),
                                source_path=spec['path'],source_sha256=spec['sha256'],language=language,
                                source_transform='EXACT_CONTEXT_SPAN_CANDIDATE_ONLY',truth='PUBLIC_SOURCE_UNVERIFIED',
                                source_rights_status='DOLLY_CC_BY_SA_3_0_ISOLATED_PENDING_REVIEW',
                                training_admission='NOT_DECIDED',semantic_truth='NOT_REVIEWED'))))
                        rec=encode_record(row,tok);totals.update(encoded_rows=1,actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets)
                        signature=hashlib.sha256(q.encode()).hexdigest();questions.add(signature)
                        if rec.x_tokens<=1024:totals.update(within1024_rows=1,within1024_x_tokens=rec.x_tokens)
                        span=exact_span(q,a);totals[span['status']]+=1
                        if span.get('context_start') is not None:contexts.add(hashlib.sha256(q[span['context_start']:].encode()).hexdigest())
                        if span['status']!='UNIQUE_LITERAL_SPAN' or rec.x_tokens>1024:continue
                        try:tokens=token_span(q,a,span,tok)
                        except ValueError:
                            totals['literal_span_without_token_boundary']+=1;continue
                        starts=[i for i,v in enumerate(rec.y) if v!=-100 and (i==0 or rec.y[i-1]==-100)]
                        if starts!=[tokens['assistant_predictor']]:raise ValueError('SFT assistant boundary differs from prefix')
                        row['meta'].update(alignment_span=span,alignment_tokens=tokens,actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets)
                        if language not in writers:writers[language]=ShardWriter(OUTPUT,'aligned_'+language)
                        writers[language].append(row)
                        totals.update(aligned_within1024_rows=1,aligned_x_tokens=rec.x_tokens,aligned_assistant_targets=rec.targets)
                    print('[DOLLY_CENSUS_PROGRESS] '+json.dumps(dict(language=language,rows=totals['rows'],aligned=totals['aligned_within1024_rows'])),flush=True)
                identities[language]=dict(unique_exact_questions=len(questions),unique_exact_contexts=len(contexts),task_types=dict(tasks),
                    uniqueness_scope='within-language exact strings only; semantic/cross-language concept correspondence NOT_RUN')
            status='CENSUS_COMPLETE';rc=0
    except KeyboardInterrupt:status='INTERRUPTED';rc=130;error='user interruption'
    except TimeoutError as exc:status='BUDGET_PAUSE';rc=8;error=str(exc)
    except Exception as exc:error=type(exc).__name__+': '+str(exc)
    finally:
        for language,writer in writers.items():
            if writer._total_rows:manifests[language]=writer.close(lineage=info);verify(OUTPUT,manifests[language])
        report=dict(info,status=status,returncode=rc,counts={k:dict(v) for k,v in counts.items()},identities=identities,
            candidate_manifests=manifests,candidate_directory=str(OUTPUT.relative_to(ROOT)),whole_sec=time.perf_counter()-began,
            error=error,formal_train_ready=False,student_training='NOT_RUN',legal_review='NOT_PERFORMED',
            timing_scope='body excludes earlier full source SHA verification; wrapper log includes setup',
            warning='exact alignment is not semantic correctness; incidental substrings possible; no main corpus admission or model rights conclusion')
        body=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        if len(body.encode())>=20_000_000:raise ValueError('20MB report limit')
        EVIDENCE.mkdir(parents=True,exist_ok=False)
        with (EVIDENCE/'report.json').open('x',encoding='utf-8') as stream:stream.write(body)
        print('[DOLLY_CENSUS_FINAL] '+json.dumps(dict(status=status,returncode=rc,counts=report['counts'],whole_sec=report['whole_sec'],error=error)),flush=True)
    return rc


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=1200)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    if not 60<=args.max_wall_sec<=1800:p.error('bounded60..1800')
    if args.check_only:print('[CHECK_ONLY] '+json.dumps(metadata()));return 0
    if not args.execute:p.error('explicit census execution required')
    remaining=int((DEADLINE-datetime.now(timezone.utc)).total_seconds())-600
    if remaining<60:p.error('17:00 deadline margin required')
    args.max_wall_sec=min(args.max_wall_sec,remaining)
    return execute(args)


if __name__=='__main__':raise SystemExit(main())
