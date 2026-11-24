"""Matched case/answer exposure for single, correction, or alternating views."""
import random

ARMS=('SINGLE_ONLY','CORRECTION_ONLY','MIXED_CROSSOVER')

def pairs(rows):
    grouped={}
    for row in rows:
        meta=row['meta'];identifier=meta['case_id'];view=meta['view']
        if view not in('single','correction')or meta['root_teacher_review']!='ROOT_ACTUAL_TEXT_REVIEWED':
            raise ValueError('explicit reviewed paired views required')
        entry=grouped.setdefault(identifier,{})
        if view in entry:raise ValueError('duplicate case view')
        entry[view]=row
    if not grouped:raise ValueError('nonempty paired cohort required')
    for identifier,entry in grouped.items():
        if set(entry)!={'single','correction'}:raise ValueError('both case views required')
        s,m=entry['single'],entry['correction']
        if([turn.get('role')for turn in s['messages']]!=['user','assistant']or
           [turn.get('role')for turn in m['messages']]!=['user','assistant','user','assistant']or
           s['messages'][0]!=m['messages'][0]or
           s['messages'][-1]!=m['messages'][-1]or
           s['meta']['language']!=m['meta']['language']or s['meta']['source_group_id']!=m['meta']['source_group_id']or
           s['meta']['supervised_assistant_turns']!=[1]or m['meta']['supervised_assistant_turns']!=[2]):
            raise ValueError('same source/question/correct answer and explicit turn owners required')
    return grouped

def epoch_plan(cohort,arm,epoch,*,seed=1337):
    if arm not in ARMS or type(epoch)is not int or not 0<=epoch<4:
        raise ValueError('declared arm and one of four epochs required')
    order=sorted(cohort);random.Random(seed+epoch).shuffle(order);assignment={}
    for language in sorted({p['single']['meta']['language']for p in cohort.values()}):
        selected=sorted(i for i,p in cohort.items()if p['single']['meta']['language']==language)
        assignment.update({i:('single'if (j+epoch)%2==0 else'correction')for j,i in enumerate(selected)})
    return [dict(case_id=i,view=('single'if arm=='SINGLE_ONLY'else'correction'if arm=='CORRECTION_ONLY'else assignment[i]))for i in order]
