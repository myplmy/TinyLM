"""Source-only question contract and reference-token objective; no semantic judge."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tinylm.chat.canonical import normalize,validate
from tinylm.chat.serialize import serialize
from tinylm.data.sft import IGNORE
from tinylm.train import mtp_sft as core
from scripts import p106b_visible_source as source
VERSION='P106B_PUBLIC_REFERENCE_COURSE_V1'
ENCODE=core.encode_record


def document_keys(row):
    meta=row['meta'];keys={meta.get('parent_concept_id') or meta.get('source_group_id') or source.sha(row['messages'])}
    for m in row['messages']:
        value=source.text(m)
        if len(value)>=200:keys.add(hashlib.sha256(value.encode()).hexdigest().upper())
    return keys


def family(row):
    value=row['meta'].get('source_family','').lower()
    if 'nq-open' in value:return 'NQ'
    if 'coqa' in value:return 'COQA'
    if 'adversarial' in value:return 'ADVERSARIAL'
    if 'aya' in value:return 'AYA'
    if 'oasst' in value:return 'OASST'
    return None


def views(candidate,question,split):
    meta=candidate['meta'];lang=meta['language']
    refs=meta['source_reference_trace'];reference='\n'.join(s['text'] for s in refs)
    prefix=('제시된 자료만 근거로 답하세요. 자료가 주어지지 않으면 자료를 요청하세요.\n' if lang=='ko' else
            'Answer using only the supplied reference. If it is not supplied, request the reference.\n')
    mark='자료:\n' if lang=='ko' else 'Reference:\n';qm='질문:\n' if lang=='ko' else 'Question:\n'
    answer=source.text(candidate['messages'][-1])
    result=[]
    for supported in (True,False):
        user=prefix+(mark+reference+'\n' if supported else '')+qm+question
        response=answer if supported else ('답할 근거 자료를 제공해 주세요.' if lang=='ko' else 'Please provide the reference needed to answer.')
        info=dict(meta,source_course=VERSION,source_split=split,kind='source_qa' if supported else 'request_reference',
            rubric='CLARIFICATION_POSTHOC',semantic_root_id=meta['parent_concept_id'],
            reference_text=reference if supported else '',reference_marker=mark,
            reference_required_contract='PRODUCER_EXPLICIT_SOURCE_ONLY; not inferred from wording',
            semantic_truth='PSEUDO_UNVERIFIED' if supported else 'PRODUCER_MISSING_INPUT_CONTRACT')
        row=validate(normalize(dict(messages=[dict(role='user',content=user),dict(role='assistant',content=response)],meta=info)))
        result.append(row)
    return result


def record(row,tok,encode=ENCODE):
    result=encode(row,tok);native=[IGNORE]*len(result.y)
    reference=row['meta'].get('reference_text','')
    if reference:
        text=serialize(row,'chatml');marker=row['meta']['reference_marker']
        begin=text.find(marker)
        if begin<0:raise ValueError('producer reference marker absent')
        begin+=len(marker);end=begin+len(reference)
        if text[begin:end]!=reference:raise ValueError('reference bytes not in student input')
        encoded=tok.encode(text)
        for j,(a,b) in enumerate(encoded.offsets):
            if j>0 and b>a and a>=begin and b<=end:
                if result.y[j-1]!=IGNORE:raise ValueError('reference overlaps assistant label')
                native[j-1]=encoded.ids[j]
    result.reference_y=native
    return result


def native_count(rec):return sum(x!=IGNORE for x in rec.reference_y)


class ReferenceObjective:
    """Same backbone/input, separate update-level denominators; default product unchanged."""
    def __init__(self,weight):
        if weight not in (0.,.1):raise ValueError('preregistered0/.1 only')
        self.weight=weight;self.reference_y=None;self.executed_targets=0
    def __enter__(self):
        from contextlib import ExitStack
        from unittest.mock import patch
        self.stack=ExitStack();pad=core.pad_records;count=core.count_record;parts=core.components;loss=core.normalized_loss
        def counted(rec,*args,**kwargs):return dict(count(rec,*args,**kwargs),**{'reference':native_count(rec)})
        def padded(records,pad_id,device='cpu',**kwargs):
            import torch
            x,y,seg=pad(records,pad_id,device,**kwargs);width=x.shape[1]
            native=[r.reference_y+[IGNORE]*(width-len(r.reference_y)) for r in records]
            native+=[[IGNORE]*width for _ in range(x.shape[0]-len(native))]
            self.reference_y=torch.tensor(native,dtype=y.dtype,device=device)
            return x,y,seg
        def components(model,hidden,y,segments,**kwargs):
            sums,counts=parts(model,hidden,y,segments,**kwargs)
            if self.weight and hidden.requires_grad:
                native=self.reference_y
                if native is None or native.shape!=y.shape:raise ValueError('reference labels not aligned')
                extra,valid=parts(model,hidden,native,native.ne(IGNORE).long(),horizons=())
                sums['reference']=extra[1];counts['reference']=valid[1]
                self.executed_targets+=int(native.ne(IGNORE).sum())
            return sums,counts
        def normalized(sums,denoms,weights):
            result=loss(sums,denoms,weights)
            if self.weight and 'reference' in sums:
                if denoms.get('reference',0)<=0:raise ValueError('positive global reference denominator required')
                result=result+self.weight*sums['reference']/denoms['reference']
            return result
        for name,value in [('encode_record',record),('count_record',counted),('pad_records',padded),
                           ('components',components),('normalized_loss',normalized)]:self.stack.enter_context(patch.object(core,name,value))
        return self
    def __exit__(self,*args):return self.stack.__exit__(*args)
