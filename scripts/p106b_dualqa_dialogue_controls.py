"""Two-view dialogue evaluation; normal identical questions are never rejected."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter,defaultdict
import copy
from scripts import diag_p106b_dualqa_eval as reference
from scripts.p106b_shards import ShardWriter,verify
from tinylm.chat.canonical import normalize,validate
PATTERNS=('contrast','repeat')


def collect(row,parity,tok,emit,pattern):
    if pattern not in PATTERNS:raise ValueError('explicit declared test pattern required')
    view=reference.course.data.view(row,pattern,parity,tok);messages=view['messages'];history=[];events=[]
    for turn in (0,1):
        history.append(copy.deepcopy(messages[2*turn]));prefix=validate(normalize(dict(messages=history)))['messages']
        answer,generation=emit(prefix)
        if not isinstance(answer,str):raise ValueError('actual output string required, empty is preserved')
        events.append(dict(root=row['meta']['semantic_root_id'],language=row['meta']['language'],order=parity,turn=turn+1,
            history='ACTUAL_MODEL',messages=copy.deepcopy(prefix),answer=answer,gold=reference.course.data.text(messages[2*turn+1]),
            generation=generation,teacher_record_id=row['meta']['teacher_record_id'],source_truth='TEACHER_PSEUDO_UNVERIFIED',test_pattern=pattern))
        history.append(dict(role='assistant',content=[dict(type='text',text=answer)]))
    prefix=copy.deepcopy(messages[:3]);answer,generation=emit(prefix)
    events.append(dict(root=row['meta']['semantic_root_id'],language=row['meta']['language'],order=parity,turn=2,
        history='GOLD_REFERENCE',messages=prefix,answer=answer,gold=reference.course.data.text(messages[3]),generation=generation,
        teacher_record_id=row['meta']['teacher_record_id'],source_truth='TEACHER_PSEUDO_UNVERIFIED',test_pattern=pattern))
    return events


def source(model,cfg,tok,rows,directory,label,pattern,lineage):
    import torch
    if len(rows)!=256 or Counter(r['meta']['language'] for r in rows)!=dict(ko=128,en=128):raise ValueError('all128/128 source documents required')
    if len({r['meta']['semantic_root_id'] for r in rows})!=256:raise ValueError('unique source documents required')
    writer=ShardWriter(directory,'source_'+pattern);counts=defaultdict(Counter);emit=reference.emit_function(model,cfg,tok)
    model.eval();model.freeze_quant()
    try:
        with torch.no_grad():
            for index,row in enumerate(rows):
                for parity in (0,1):
                    for event in collect(row,parity,tok,emit,pattern):
                        value=reference.score(event);event['scores']=value;writer.append(event)
                        counts[event['history']+':'+event['language']+':turn'+str(event['turn'])].update(value)
                if (index+1)%32==0:print('[DUALQA_CONTROL_PROGRESS] '+__import__('json').dumps(dict(endpoint=label,pattern=pattern,contexts=index+1,total=256)),flush=True)
    finally:model.clear_quant();model.train()
    manifest=writer.close(lineage=dict(lineage,test_pattern=pattern));verify(directory,manifest)
    if manifest['rows']!=1536:raise ValueError('all actual1024 and gold-second512 events required')
    return dict(counts={k:dict(v) for k,v in counts.items()},manifest=manifest,directory=str(directory.relative_to(ROOT)),
        actual_answers=1024,gold_second_answers=512,test_pattern=pattern,semantic_truth='NOT_RUN',
        scope='pseudo-target literal fidelity only; same-answer copying is descriptive, not grading or regeneration')


def behaviour(mixed,repeated):
    if set(mixed)!=set(repeated):raise ValueError('all paired document/order/turn/history keys required')
    totals=Counter()
    for root,order,turn,history in sorted(mixed):
        if turn!=1 or history!='ACTUAL_MODEL':continue
        a=mixed[root,order,1,history];b=repeated[root,order,1,history]
        if a['messages']!=b['messages'] or a['gold']!=b['gold']:raise ValueError('identical first prompt and target required across patterns')
        ma=mixed[root,order,2,history];rb=repeated[root,order,2,history]
        if b['gold']!=rb['gold']:raise ValueError('normal repeated question must retain the same target')
        totals.update(conversations=1,first_output_same=int(a['answer']==b['answer']),
            mixed_first_literal=int(reference.score(a)['literal']),repeat_first_literal=int(reference.score(b)['literal']),
            mixed_second_literal=int(reference.score(ma)['literal']),repeat_second_literal=int(reference.score(rb)['literal']),
            mixed_both_literal=int(reference.score(a)['literal'] and reference.score(ma)['literal']),
            repeat_both_literal=int(reference.score(b)['literal'] and reference.score(rb)['literal']),
            mixed_copy_first=int(ma['answer'].strip()==a['answer'].strip()),
            repeat_copy_first=int(rb['answer'].strip()==b['answer'].strip()),
            repeat_first_wrong_second_literal=int(not reference.score(b)['literal'] and reference.score(rb)['literal']),
            repeat_first_literal_second_wrong=int(reference.score(b)['literal'] and not reference.score(rb)['literal']))
    return dict(totals,first_output_disagreements=totals['conversations']-totals['first_output_same'],
        automatic_quality_pass=False,scope='same first input across patterns; copying a wrong first answer is not a desired success, aliases require reading')
