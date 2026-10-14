"""Code-proven conditional answer pairs and ORPO-style math, never a word blacklist.

Method read: https://arxiv.org/html/2403.07691v2 sections4.1-4.3, equations3-7.
This task-specific extension keeps native replay and token-normalized SFT;
it is not a replication of the paper's data, models, or complete recipe.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
from scripts import p106b_retention_course as source
VERSION='P106B_CODE_CONDITIONAL_ORPO_V1'
BETAS={'pair_zero':0.,'pair010':.1,'pair030':.3,'positive030':.3}
NEW_NAMES={
    'ko':['서우','유하','지율','서진','민재','준호','도현','하은','시온','채윤','서율','예서'],
    'en':['Adrian','Bella','Caleb','Diana','Eli','Fiona','Gavin','Hazel','Isaac','Julia','Miles','Nora']}


def correct_own_question(row):
    """Repair this producer's particle join, never screen arbitrary teacher text."""
    result=copy.deepcopy(row);m=result['meta']
    if m.get('kind')=='binding_color' and m.get('language')=='ko':
        block=result['messages'][0]['content'][0]
        old=block['text'];new=old.replace('의 색상는','의 색상은')
        block['text']=new
        if old!=new:m.update(question_grammar_revision='OWN_COLOR_PARTICLE_V1',original_question_signature=source.sha(row['messages']))
    return result


def make_pair(row,approved_hashes):
    """Only byte-matched original producer questions, not model-declared labels."""
    meta=row['meta'];signature=source.sha(row['messages'])
    if (signature not in approved_hashes or meta['kind'] not in ('binding_color','binding_department')
            or meta['rubric']!='EXACT_SCALAR' or len(row['messages'])!=2
            or meta.get('course_version')!=source.VERSION):
        raise ValueError('no verified producer one-value output contract')
    mapping=meta['mapping'];asked=meta['requested_entity']
    if len(mapping)!=2 or len(set(mapping.values()))!=2 or asked not in mapping:
        raise ValueError('two unambiguous distinct values required')
    gold=source.text(row,-1)
    if gold!=mapping[asked]:raise ValueError('positive answer differs from producer fact')
    mode='wrong_target' if (int(meta['semantic_root_id'][:8],16)+int(meta['target_is_first']))%2 else 'unrequested_repeat'
    alternative=next(v for k,v in mapping.items() if k!=asked)
    rejected=alternative if mode=='wrong_target' else gold+' '+gold
    if rejected==gold or not rejected.strip():raise ValueError('empty/equal pair')
    negative=copy.deepcopy(row)
    negative['messages'][-1]['content']=[dict(type='text',text=rejected)]
    return dict(chosen=copy.deepcopy(row),rejected=negative,mode=mode,root=meta['semantic_root_id'],
                source_signature=signature,contract='ONE_VALUE_ONLY_FROM_PINNED_CODE_PRODUCER',
                repeat_scope='single answer violating one-value contract; never duplicate valid multi-answers')


def fresh_test(base_rows):
    result=[];old_roots={r['meta']['semantic_root_id'] for values in base_rows.values() for r in values}
    for row in base_rows['test']:
        if not row['meta']['kind'].startswith('binding_'):continue
        item=correct_own_question(row);m=item['meta'];language=m['language']
        renaming=dict(zip(source.NAMES[language]['test'],NEW_NAMES[language]))
        for message in item['messages']:
            for block in message['content']:
                for old,new in renaming.items():block['text']=block['text'].replace(old,new)
        m['mapping']={renaming[k]:v for k,v in m['mapping'].items()}
        m['requested_entity']=renaming[m['requested_entity']]
        m['ordered_entities']=[renaming[k] for k in m['ordered_entities']]
        m['semantic_root_id']=source.sha(dict(task='orpo_fresh_binding',language=language,kind=m['kind'],mapping=m['mapping']))
        m.update(source_split='orpo_test',course_version=VERSION)
        if m['semantic_root_id'] in old_roots:raise ValueError('fresh root collision')
        result.append(item)
    attempt=0
    while len(result)<640:
        i=len(result)-512;language=('ko','en')[i%2]
        kind=('arithmetic','boolean','json','update')[(i//2)%4]
        row=source.make(kind,language,18100000+attempt,novel=True);attempt+=1
        root=row['meta']['semantic_root_id']
        if root in old_roots:continue
        old_roots.add(root);row['meta'].update(source_split='orpo_test',course_version=VERSION)
        result.append(row)
        if attempt>100000:raise ValueError('fresh task supply exhausted')
    if len({source.sha(r['messages']) for r in result})!=640:raise ValueError('duplicate test')
    return result


def log_odds(logp):
    import torch
    if not torch.isfinite(logp).all() or bool((logp>0).any()):raise ValueError('finite log probability required')
    bounded=logp.clamp(max=-1e-6)
    return bounded-torch.log(-torch.expm1(bounded))


def preference_loss(chosen_logp,rejected_logp):
    import torch.nn.functional as F
    if chosen_logp.shape!=rejected_logp.shape:raise ValueError('paired shape differs')
    return F.softplus(-(log_odds(chosen_logp)-log_odds(rejected_logp)))


def extra_loss(arm,chosen_logp,rejected_logp):
    if arm not in BETAS:raise ValueError('registered arm required')
    return -chosen_logp if arm=='positive030' else preference_loss(chosen_logp,rejected_logp)


def sequence_logps(model,hidden,y):
    """Mean supervised answer log probability, including end token, per record."""
    import torch
    from tinylm.data.sft import IGNORE
    mask=y.ne(IGNORE);counts=mask.sum(1)
    if bool((counts==0).any()):raise ValueError('empty answer mask')
    positions=mask.nonzero(as_tuple=False)
    features=hidden[mask].unsqueeze(0)
    logits=model._head_logits(features).squeeze(0).float()
    ll=torch.log_softmax(logits,-1).gather(1,y[mask].unsqueeze(1)).squeeze(1)
    sums=torch.zeros(y.shape[0],device=hidden.device,dtype=ll.dtype).index_add(0,positions[:,0],ll)
    return sums/counts
