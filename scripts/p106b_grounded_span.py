"""Offline public-QA alignment and removable, training-only span objective.

No model/data access on import. Literal alignment is not semantic validation.
The generator always uses the existing vocabulary head, never this auxiliary.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import math
import re
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
VERSION='P106B_GROUNDED_SPAN_V1'
ARMS={'span0':0.,'span03':.3}


def sha(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()


def text(message):
    blocks=message['content']
    if any(b.get('type')!='text' for b in blocks):raise ValueError('text-only source required')
    return ''.join(b['text'] for b in blocks)


def first_pair(row):
    """Only a declared CoQA list producer, never a free-text type guess."""
    meta=row['meta']
    if meta.get('source')!='p106b_public_direct' or meta.get('selection_family')!='Flan-Coqa':
        raise ValueError('declared existing public COQA family required')
    if len(row['messages'])<2 or [m['role'] for m in row['messages'][:2]]!=['user','assistant']:
        raise ValueError('original first QA roles required')
    question,answer=(text(m) for m in row['messages'][:2])
    firsts=[list(re.finditer(r'(?<!\S)1\.\s+',s)) for s in (question,answer)]
    if any(len(v)!=1 for v in firsts):raise ValueError('one explicit numbered first item required')
    q1,a1=(v[0] for v in firsts)
    q2=re.search(r'(?<!\S)2\.\s+',question[q1.end():]);a2=re.search(r'(?<!\S)2\.\s+',answer[a1.end():])
    if q2 is None or a2 is None:raise ValueError('explicit next item boundary required')
    reference=question[:q1.start()]
    q=question[q1.end():q1.end()+q2.start()].strip()
    a=answer[a1.end():a1.end()+a2.start()].strip()
    if len(reference)<200 or not q or not a:raise ValueError('nonempty complete context/question/answer required')
    if reference.count(a)!=1:raise ValueError('one literal target in reference required; no truth inference')
    start=reference.index(a)
    return dict(reference=reference,question=q,answer=a,
        original_question_range=[q1.end(),q1.end()+q2.start()],original_reference_range=[0,q1.start()],
        original_answer_range=[a1.end(),a1.end()+a2.start()],answer_reference_range=[start,start+len(a)])


def passage_keys(reference):
    """Conservative exact 24-word overlap groups, NOT a semantic-quality rule."""
    words=reference.split()
    keys={sha(['WHOLE_REFERENCE',reference])}
    for i in range(max(0,len(words)-23)):
        keys.add(sha(['EXACT_PASSAGE24',words[i:i+24]]))
    return keys


def wrap(source,pair,split):
    from tinylm.chat.canonical import normalize,validate
    language=source['meta']['language']
    if language not in ('ko','en'):raise ValueError('declared language required')
    prefix=('자료를 읽고 질문에 대한 짧은 답만 쓰세요. 자료에 없는 사실은 추가하지 마세요.\n자료:\n' if language=='ko' else
            'Read the reference and give only the short answer. Do not add facts absent from it.\nReference:\n')
    user=prefix+pair['reference']+('\n질문:\n' if language=='ko' else '\nQuestion:\n')+pair['question']
    lo=len(prefix);a,b=pair['answer_reference_range'];meta=dict(source['meta'])
    meta.update(kind='natural_first_qa',rubric='PUBLIC_LITERAL_TARGET',course_version=VERSION,source_split=split,
        semantic_root_id=sha(['REFERENCE',language,pair['reference']]),
        parent_concept_id=source['meta']['parent_concept_id'],original_messages_sha256=sha(source['messages'][:2]),
        original_first_pair=pair,user_reference_range=[lo,lo+len(pair['reference'])],
        user_answer_range=[lo+a,lo+b],source_truth='PUBLIC_SOURCE_UNVERIFIED',
        alignment_truth='UNIQUE_LITERAL_LOCATION_ONLY',teacher_reasoning_in_student=False,
        inference_uses_auxiliary=False,source_original_split=source['meta'].get('source_split'))
    return validate(normalize(dict(messages=[dict(role='user',content=user),dict(role='assistant',content=pair['answer'])],meta=meta)))


def locations(row,tok,record):
    if row['meta'].get('kind')!='natural_first_qa':return None
    from tinylm.chat.serialize import serialize
    from tinylm.data.sft import IGNORE
    user=text(row['messages'][0]);answer=text(row['messages'][1]);m=row['meta']
    lo,hi=m['user_reference_range'];a,b=m['user_answer_range']
    if not 0<=lo<=a<b<=hi<=len(user) or user[a:b]!=answer:raise ValueError('literal user span mismatch')
    prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
    if prompt.count(user)!=1:raise ValueError('unique entire user transport required')
    origin=prompt.index(user);encoded=tok.encode(prompt)
    predictor=len(encoded.ids)-1
    first=next(i for i,y in enumerate(record.y) if y!=IGNORE)
    if predictor!=first:raise ValueError('first assistant predictor differs from complete prefix')
    positions=[i for i,(x,y) in enumerate(encoded.offsets) if y>x and x>=origin+lo and y<=origin+hi]
    starts=[i for i,(x,y) in enumerate(encoded.offsets) if y>x and x<=origin+a<y]
    ends=[i for i,(x,y) in enumerate(encoded.offsets) if y>x and x<origin+b<=y]
    if not positions or not starts or not ends:raise ValueError('source/token location missing')
    start=min(starts);end=max(ends)
    if start not in positions or end not in positions or not start<=end<predictor:
        raise ValueError('source labels must precede assistant predictor and stay in reference')
    return dict(query=predictor,positions=positions,start=positions.index(start),end=positions.index(end),
        absolute_start=start,absolute_end=end,scope='causal full-prefix only; no assistant-body hidden')


def new_head(dim,device='cpu',rank=64):
    import torch
    # Independent generator means adding a head never advances body/data RNG.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(20261016)
        head=torch.nn.ModuleDict({k:torch.nn.Linear(dim,rank,bias=False) for k in ('qs','ks','qe','ke')})
    return head.to(device)


def auxiliary_sum(head,hidden,labels):
    import torch
    if len(labels)!=len(hidden):raise ValueError('batch/label mismatch')
    total=hidden.sum()*0+sum(p.sum()*0 for p in head.parameters());count=correct=both=0
    for i,label in enumerate(labels):
        if label is None:continue
        pos=label['positions'];q=label['query']
        if not pos or max(pos)>=q or q>=hidden.shape[1]:raise ValueError('future/answer state in span objective')
        source=hidden[i,pos,:];query=hidden[i,q,:];hits=[]
        for suffix,target in (('s',label['start']),('e',label['end'])):
            logits=(head['k'+suffix](source).float()@head['q'+suffix](query).float())/math.sqrt(head['qs'].out_features)
            truth=torch.tensor([target],dtype=torch.long,device=hidden.device)
            total=total+.5*torch.nn.functional.cross_entropy(logits[None],truth,reduction='sum')
            hit=int(logits.argmax())==target;correct+=hit;hits.append(hit)
        count+=1;both+=all(hits)
    return total,count,correct,both


def token_f1(answer,gold):
    def units(s):return re.findall(r'\w+|[^\w\s]',s.casefold(),re.UNICODE)
    aa,bb=units(answer),units(gold)
    if not aa or not bb:return float(aa==bb)
    overlap=sum((Counter(aa)&Counter(bb)).values())
    return 2*overlap/(len(aa)+len(bb))
