"""Exact decimal/carry supervision and fixed state supervision, training only."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import re
from scripts import p106b_state_update_aux as state
source=state.source
VERSION='P106B_JOINT_DECIMAL_AUX_V1'


def decimal_parts(a,b):
    if type(a) is not int or type(b) is not int or not 0<=a<=99 or not 0<=b<=99:
        raise ValueError('known nonnegative two-digit operands only')
    carry=(a%10+b%10)//10;ones=(a%10+b%10)%10;tens=a//10+b//10+carry
    total=10*tens+ones
    if total!=a+b:raise ValueError('independent decimal reconstruction differs')
    return total,ones,tens,carry


def exclude_parent_pairs(rows):
    result={(2,3)}
    for values in rows.values():
        for row in values:
            m=row['meta']
            if m['kind'] not in ('arithmetic','update') or m.get('truth')!='PRODUCER_CODE_FACT_CONTRACT':continue
            match=re.search(r'(\d+)\s*\+\s*(\d+)',source.text(row,0))
            if match is None:continue
            a,b=map(int,match.groups())
            if source.text(row,1)!=str(a+b):raise ValueError('known parent arithmetic producer differs')
            if 0<=a<=99 and 0<=b<=99:result.add(tuple(sorted((a,b))))
            if m['kind']=='update':
                changed=int(source.text(row,-1))-a
                if 0<=a<=99 and 0<=changed<=99:result.add(tuple(sorted((a,changed))))
    return result


def addition_rows(excluded):
    pairs=[(a,b) for a in range(100) for b in range(a,100) if (a,b) not in excluded]
    pairs.sort(key=lambda pair:source.sha([VERSION,20261015,list(pair)]))
    if len(pairs)<2560:raise ValueError('new unordered addition-pair supply insufficient')
    result={};offset=0
    from tinylm.chat.canonical import normalize,validate
    for split,n in (('train',2048),('dev',256),('test',256)):
        values=[]
        for pair in pairs[offset:offset+n]:
            total,ones,tens,carry=decimal_parts(*pair);root=source.sha([VERSION,'addition',list(pair)])
            for language in ('ko','en'):
                for view,(a,b) in enumerate((pair,tuple(reversed(pair)))):
                    if language=='ko':
                        question=(f'계산: {a} + {b}. 결과 정수 하나만 쓰세요.' if not view else
                            f'상자에 사과가 {a}개 있습니다. 사과 {b}개를 더 넣었습니다. 지금 사과는 모두 몇 개인가요? 정수 하나만 답하세요.')
                    else:
                        question=(f'Calculate {a}+{b}. Reply with one integer only.' if not view else
                            f'A box has {a} apples. Add {b} more apples. How many apples are now in the box? Reply with one integer only.')
                    values.append(validate(normalize(dict(messages=[dict(role='user',content=question),dict(role='assistant',content=str(total))],
                        meta=dict(language=language,kind='addition',rubric='EXACT_INTEGER',lhs=a,rhs=b,total=total,
                            ones=ones,tens=tens,carry=carry,source_split=split,semantic_root_id=root,
                            course_version=VERSION,source='PROJECT_AUTHORED_CODE',source_license='project_authored_synthetic',
                            truth='PRODUCER_CODE_FACT_CONTRACT',view='symbolic' if not view else 'apples_word_problem',
                            world_facts='CODE_ONLY',unordered_pair=list(pair))))))
        result[split]=values;offset+=n
    return result


def approved(values):
    return {source.sha(r['messages']):copy.deepcopy(r['meta']) for r in values
        if r['meta']['kind']=='addition' or r['meta']['kind'].startswith('state_update_')}


def label(row,contract):
    m=row['meta']
    if m['kind'].startswith('state_update_'):return state.label(row,contract)
    if m['kind']!='addition':return None
    signature=source.sha(row['messages']);trusted=contract.get(signature)
    if trusted is None or m.get('course_version')!=VERSION:raise ValueError('exact addition producer required')
    for field in ('lhs','rhs','total','ones','tens','carry','semantic_root_id'):
        if m[field]!=trusted[field]:raise ValueError('untrusted decimal metadata: '+field)
    parts=decimal_parts(m['lhs'],m['rhs'])
    if parts!=(m['total'],m['ones'],m['tens'],m['carry']) or source.text(row,-1)!=str(parts[0]):
        raise ValueError('addition word target/decimal verification differs')
    return 1000+m['total']+200*m['carry']


def valid_label(value,root=None,permuted=False):
    if value is None:return None
    if permuted or type(value) is not int:raise ValueError('declared integer labels only, no permutation')
    if value in (0,1):return value
    raw=value-1000
    if raw<0 or raw//200 not in (0,1) or not 0<=raw%200<=198:raise ValueError('decimal code out of bounds')
    return value


def new_head(dim,device='cpu'):
    import torch
    with torch.random.fork_rng(devices=[]):head=torch.nn.Linear(dim,34)
    with torch.no_grad():head.weight.zero_();head.bias.zero_()
    return head.to(device)


def last_position(row,record,tok):
    from tinylm.chat.serialize import serialize
    prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
    expected=len(tok.encode(prompt).ids)-1
    starts=[i for i,v in enumerate(record.y) if v!=-100 and (not i or record.y[i-1]==-100)]
    spans=2 if row['meta']['kind'].startswith('state_update_') else 1
    if len(starts)!=spans or starts[-1]!=expected:raise ValueError('known final assistant boundary differs')
    return expected


def objective(head,hidden,y,labels,windows,beta=1.,dense=False):
    import torch
    if beta not in (0.,1.) or dense:raise ValueError('declared last-position decimal contrast only')
    selected=[i for i,v in enumerate(labels) if v is not None];positions=[]
    if not selected:return hidden.sum()*0+sum(p.sum()*0 for p in head.parameters()),0,0,0
    for i in selected:
        value=valid_label(labels[i]);window=windows[i]
        starts=[j for j,v in enumerate(y[i].tolist()) if v!=-100 and (not j or int(y[i,j-1])==-100)]
        if len(starts)!=(1 if value>=1000 else 2) or window!=[starts[-1]]:
            raise ValueError('no future answer body; exact last assistant predictor required')
        positions.append(window[0])
    logits=head(hidden[torch.tensor(selected,device=hidden.device),torch.tensor(positions,device=hidden.device)]).float()
    values=torch.tensor([labels[i] for i in selected],device=hidden.device);maths=values.ge(1000);states=~maths
    loss=logits.sum()*0;correct=0
    if bool(states.any()):
        state_loss=torch.nn.functional.cross_entropy(logits[states,:2],values[states],reduction='sum')
        loss=loss+2*state_loss;correct+=int(logits[states,:2].argmax(-1).eq(values[states]).sum())
    if bool(maths.any()):
        encoded=values[maths]-1000;total=encoded%200;carry=encoded//200;targets=(total%10,total//10,carry)
        slices=(logits[maths,2:12],logits[maths,12:32],logits[maths,32:34])
        losses=[torch.nn.functional.cross_entropy(a,b,reduction='sum') for a,b in zip(slices,targets)]
        loss=loss+2*beta*sum(losses)/3
        correct+=int(torch.stack([a.argmax(-1).eq(b) for a,b in zip(slices,targets)]).all(0).sum())
    return loss,len(selected),correct,len(selected)
