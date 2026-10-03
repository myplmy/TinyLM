"""Closed-world P106C B batch plans; pair, color, language and target mass matched."""
from __future__ import annotations
from collections import Counter
import random


def make_plan(train, rehearsal, train_encoded, rehearsal_encoded, eligible, *, steps=32, cap=16):
    if steps not in (8, 16, 32) or cap <= 0:
        raise ValueError("bounded B plan needs8/16/32 steps and positive cap")
    rng = random.Random(20261003)
    def pairs(rows, encoded):
        if len(rows) != len(encoded) or len(rows) % 2:
            raise ValueError("paired records and encodings differ")
        out = []
        for i in range(0, len(rows), 2):
            a,b=rows[i:i+2]
            if a['pair_id']!=b['pair_id'] or a['language']!=b['language'] or a['gold']==b['gold']:
                raise ValueError("invalid source question pair")
            out.append({'id':i//2,'rows':[i,i+1],'lang':a['language'],'gold':(a['gold'],b['gold']),
                        'key':(a['language'],a['gold'],b['gold'],len(encoded[i][0]),len(encoded[i+1][0]),encoded[i][2],encoded[i+1][2])})
        return out
    tp,rp=pairs(train,train_encoded),pairs(rehearsal,rehearsal_encoded)
    counts={name:Counter() for name in ('baseline','selected','rehearsal')}
    top={p['id'] for p in tp if p['rows'][0]//32 in eligible}
    def balanced(pool, counter):
        result=[]
        for lang in ('ko','en'):
            colors=sorted({c for p in pool if p['lang']==lang for c in p['gold']})
            if len(colors)!=4:
                raise ValueError("four code-gold colors required per language")
            rng.shuffle(colors)
            for k in range(4):
                desired={colors[k], colors[(k+1)%4]}
                candidates=[p for p in pool if p['lang']==lang and set(p['gold'])==desired and counter[p['id']]<cap]
                if not candidates:
                    raise ValueError("color-balanced schedule infeasible; no silent repetition")
                p=rng.choice(candidates);counter[p['id']]+=1;result.append(p)
        return result
    result={'baseline':[],'selected':[],'selected_top_pairs':0,'candidate_pairs':8*steps}
    for step in range(steps):
        base=balanced(tp,counts['baseline']); rehearse=balanced(rp,counts['rehearsal'])
        selected=[]
        for slot,original in enumerate(base):
            candidates=[p for p in tp if p['key']==original['key'] and counts['selected'][p['id']]<cap
                        and p['id'] not in {v['id'] for v in selected}]
            preferred=[p for p in candidates if p['id'] in top] if slot%4<2 else []
            if not candidates:
                raise ValueError("matched pair schedule infeasible")
            chosen=rng.choice(preferred or candidates)
            counts['selected'][chosen['id']]+=1;selected.append(chosen)
            result['selected_top_pairs']+=chosen['id'] in top
        rh=[i for p in rehearse for i in p['rows']]
        for arm,chosen in (('baseline',base),('selected',selected)):
            result[arm].append({'candidate':[i for p in chosen for i in p['rows']], 'rehearsal':rh})
    result['max_pair_exposures']={k:max(c.values(),default=0) for k,c in counts.items()}
    result['selected_top_fraction']=result['selected_top_pairs']/result['candidate_pairs']
    result['steps']=steps
    return result
