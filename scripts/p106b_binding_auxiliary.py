"""Training-only two-class target-connection supervision for proven code tasks.

Never infers labels from arbitrary public/teacher wording. This head is not a
candidate answer selector and is absent from the normal inference path.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
from scripts import p106b_conditional_orpo as prior
VERSION='P106B_PROVEN_BINDING_AUX_V1'
ARMS={'aux0':(0.,False),'aux03':(.3,False),'aux100':(1.,False),'auxperm100':(1.,True),'auxdense100':(1.,False)}
NAMES={'ko':['주원','연우','준서','유준','지한','시아','서아','다인','유림','은호','예성','민규'],
       'en':['Amelia','Blake','Cora','Declan','Elena','Felix','Gemma','Holden','Isla','Jonah','Keira','Luca']}


def approved_questions(split='train'):
    if split not in ('train','dev'):raise ValueError('declared producer train/dev contract required')
    result={}
    for row in prior.source.binding_rows(split):
        row=prior.correct_own_question(row)
        result[prior.source.sha(row['messages'])]=copy.deepcopy(row['meta'])
    return result


def binding_bit(row,approved):
    m=row['meta']
    if m.get('kind') not in ('binding_color','binding_department'):
        return None
    signature=prior.source.sha(row['messages'])
    if signature not in approved or m.get('rubric')!='EXACT_SCALAR':
        raise ValueError('binding label requires exact approved producer conversation')
    trusted=approved[signature]
    for key in ('mapping','ordered_entities','requested_entity','first_value','semantic_root_id'):
        if m[key]!=trusted[key]:raise ValueError('untrusted producer metadata: '+key)
    mapping=m['mapping'];ordered=m['ordered_entities'];asked=m['requested_entity']
    if len(mapping)!=2 or len(set(mapping.values()))!=2 or set(ordered)!=set(mapping) or asked not in mapping:
        raise ValueError('two distinct values and declared source order required')
    if prior.source.text(row,-1)!=mapping[asked] or m['first_value']!=mapping[ordered[0]]:
        raise ValueError('producer label/source mismatch')
    return int(asked==ordered[0])


def maybe_flip(bit,root,permuted):
    if bit is None:return None
    if bit not in (0,1):raise ValueError('binary producer label required')
    flip=int(prior.source.sha(['AUX_PERMUTED_ROOT_V1',root])[:8],16)%2
    return bit^flip if permuted else bit


def new_head(dim,device='cpu'):
    import torch
    # Initial body/RNG must be independent of adding this training-only branch.
    with torch.random.fork_rng(devices=[]):
        head=torch.nn.Linear(dim,2)
    with torch.no_grad():head.weight.zero_();head.bias.zero_()
    return head.to(device)


def first_positions(y,labels):
    import torch
    from tinylm.data.sft import IGNORE
    if len(labels)!=y.shape[0]:raise ValueError('label/batch mismatch')
    selected=[i for i,label in enumerate(labels) if label is not None]
    rows=torch.tensor(selected,device=y.device,dtype=torch.long)
    if not selected:return rows,rows
    mask=y[rows].ne(IGNORE)
    if not bool(mask.any(1).all()):raise ValueError('known record has no first assistant target')
    return rows,mask.long().argmax(1)


def auxiliary_sum(head,hidden,y,labels):
    import torch
    rows,positions=first_positions(y,labels)
    if not len(rows):
        zero=hidden.sum()*0+sum(p.sum()*0 for p in head.parameters())
        return zero,0,0
    target=torch.tensor([labels[i] for i in rows.tolist()],device=hidden.device,dtype=torch.long)
    logits=head(hidden[rows,positions,:])
    loss=torch.nn.functional.cross_entropy(logits.float(),target,reduction='sum')
    return loss,len(rows),int(logits.argmax(-1).eq(target).sum())


def causal_suffix_positions(row,tok,first):
    """Only positions after the complete queried entity, never answer-body states."""
    from tinylm.chat.serialize import serialize
    prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
    entity=row['meta']['requested_entity'];start=prompt.rfind(entity)
    if start<0 or prompt.count(entity)<2:raise ValueError('registered fact/query entity occurrences required')
    end=start+len(entity);encoded=tok.encode(prompt)
    if first!=len(encoded.ids)-1:raise ValueError('first assistant predictor differs from full prefix')
    overlaps=[i for i,(a,b) in enumerate(encoded.offsets) if a<end and b>start]
    if not overlaps:raise ValueError('queried entity token offsets absent')
    # Several byte-level tokens can share the last character offset. The LAST
    # touching token is needed before the complete entity has been observed.
    begin=max(overlaps)
    if not 0<=begin<=first or first-begin+1>128:raise ValueError('bounded causal suffix required')
    return list(range(begin,first+1))


def suffix_auxiliary_sum(head,hidden,y,labels,windows,dense=False):
    """Compute the same window logits for all arms; vary loss positions only.

    Each known row contributes one mean (dense) or its last predictor (normal).
    Global update normalization remains by known ROWS, not window length.
    """
    import torch
    rows,firsts=first_positions(y,labels)
    if len(windows)!=len(labels):raise ValueError('window/batch mismatch')
    if any(label is None and window for label,window in zip(labels,windows)):
        raise ValueError('unknown source cannot receive auxiliary positions')
    if not len(rows):
        zero=hidden.sum()*0+sum(p.sum()*0 for p in head.parameters())
        return zero,0,0,0
    rr=[];pp=[];targets=[];weights=[];last_indices=[]
    for row,first in zip(rows.tolist(),firsts.tolist()):
        positions=windows[row]
        if (not positions or positions[-1]!=first or positions!=sorted(set(positions))
                or positions[0]<0 or any(p>first for p in positions)):
            raise ValueError('auxiliary positions must end at first predictor, never later')
        rr.extend([row]*len(positions));pp.extend(positions);targets.extend([labels[row]]*len(positions))
        weights.extend([1/len(positions) if dense else float(p==first) for p in positions])
        last_indices.append(len(rr)-1)
    ri=torch.tensor(rr,device=hidden.device);pi=torch.tensor(pp,device=hidden.device)
    target=torch.tensor(targets,device=hidden.device,dtype=torch.long)
    logits=head(hidden[ri,pi,:]);ce=torch.nn.functional.cross_entropy(logits.float(),target,reduction='none')
    loss=(ce*torch.tensor(weights,device=hidden.device,dtype=ce.dtype)).sum()
    final=torch.tensor(last_indices,device=hidden.device)
    correct=int(logits[final].argmax(-1).eq(target[final]).sum())
    return loss,len(rows),correct,len(rr)


def fresh_test(old_rows):
    rows=prior.fresh_test(old_rows);result=[]
    previous={r['meta']['semantic_root_id'] for values in old_rows.values() for r in values}
    previous.update(r['meta']['semantic_root_id'] for r in rows)
    old_names={language:set(prior.NEW_NAMES[language]) for language in NAMES}
    for language in NAMES:
        seen=set().union(*(set(v) for v in prior.source.NAMES[language].values()))|old_names[language]
        if seen&set(NAMES[language]):raise ValueError('fresh binding names overlap previous producer names')
    for row in rows[:512]:
        item=copy.deepcopy(row);m=item['meta'];language=m['language']
        rename=dict(zip(prior.NEW_NAMES[language],NAMES[language]))
        for message in item['messages']:
            for block in message['content']:
                for old,new in rename.items():block['text']=block['text'].replace(old,new)
        m['mapping']={rename[k]:v for k,v in m['mapping'].items()}
        m['requested_entity']=rename[m['requested_entity']]
        m['ordered_entities']=[rename[k] for k in m['ordered_entities']]
        m['semantic_root_id']=prior.source.sha(dict(task=VERSION,language=language,kind=m['kind'],mapping=m['mapping']))
        m.update(source_split='binding_aux_test',course_version=VERSION)
        if m['semantic_root_id'] in previous:raise ValueError('fresh binding root collides')
        result.append(item)
    used=previous|{r['meta']['semantic_root_id'] for r in result};attempt=0
    while len(result)<640:
        i=len(result)-512;language=('ko','en')[i%2];kind=('arithmetic','boolean','json','update')[(i//2)%4]
        row=prior.source.make(kind,language,19100000+attempt,novel=True);attempt+=1
        root=row['meta']['semantic_root_id']
        if root in used:continue
        used.add(root);row['meta'].update(source_split='binding_aux_test',course_version=VERSION);result.append(row)
        if attempt>100000:raise ValueError('fresh rule root supply exhausted')
    return result
