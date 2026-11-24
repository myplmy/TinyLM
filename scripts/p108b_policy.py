"""Frozen policy specifications and score/selection accounting, without I/O."""
from dataclasses import dataclass,replace
import math
import torch

from scripts import p108b_solver as solver


@dataclass(frozen=True)
class Policy:
    name:str
    rounds:int
    layer_rule:str
    residual_share:bool=False
    support_denominator:int=1
    support_rule:str='gain_cost'
    random_seed:int|None=None
    budget_mode:str='net'


def primary_policies():
    specs=[Policy('SINGLE1',1,'same')]
    for n in (2,4):
        specs.extend([Policy(f'SAME{n}',n,'same'),Policy(f'SEQ{n}',n,'sequence'),
                      Policy(f'EQUAL{n}',n,'sequence',residual_share=True),
                      Policy(f'ADAPT_D{n}',n,'adaptive_distinct'),Policy(f'ADAPT_R{n}',n,'adaptive_revisit')])
    for name in ('SINGLE1','ADAPT_R4'):
        original=next(s for s in specs if s.name==name)
        for denominator in (8,32):
            specs.append(replace(original,name=f'{name}_SPARSE{denominator}',support_denominator=denominator))
    for seed in (1337,2337,3337):
        specs.append(Policy(f'SINGLE1_RANDOM32_{seed}',1,'same',support_denominator=32,
                            support_rule='random',random_seed=seed))
    if len(specs)!=18 or len({s.name for s in specs})!=18:raise RuntimeError('primary matrix differs')
    return specs


def diagnostic_policies():
    by_name={s.name:s for s in primary_policies()}
    specs=[replace(by_name['SINGLE1'],name=f'SINGLE1_MAG{d}',support_denominator=d,support_rule='magnitude')for d in (8,32)]
    specs.extend(replace(by_name[n],name=n+'_PATH',budget_mode='path')for n in ('SAME4','SEQ4','ADAPT_R4'))
    specs.append(replace(by_name['ADAPT_R4'],name='ADAPT_R4_FREE_CAP',budget_mode='free_net'))
    return specs


def budget_limit(spec,round_index,total):
    if not 1<=round_index<=spec.rounds or not math.isfinite(total) or total<=0:
        raise ValueError('valid round and positive budget required')
    if spec.budget_mode=='path':return total/spec.rounds
    if spec.budget_mode=='free_net':return total
    if spec.budget_mode=='net':return total*round_index/spec.rounds
    raise ValueError('unknown budget mode')


def eligible_layers(spec,round_index,*,best_layer,fixed_order,visited):
    if sorted(fixed_order)!=list(range(14)) or best_layer not in fixed_order:
        raise ValueError('complete14 frozen baseline layer order required')
    if spec.layer_rule=='same':return [best_layer]
    if spec.layer_rule=='sequence':return [fixed_order[round_index-1]]
    if spec.layer_rule=='adaptive_distinct':return [i for i in range(14)if i not in visited]
    if spec.layer_rule=='adaptive_revisit':return list(range(14))
    raise ValueError('unknown layer selection rule')


def coordinate_scores(gradient,proposal,moment):
    g,p,c=(x.detach().cpu().double()for x in (gradient,proposal,moment))
    if g.shape!=p.shape or c.shape!=(p.shape[1],p.shape[1]) or any(not bool(torch.isfinite(x).all())for x in (g,p,c)):
        raise ValueError('finite gradient/proposal/covariance shapes required')
    cost=p.square()*c.diagonal()[None,:]
    epsilon=max(float(cost.max()),1e-30)*torch.finfo(torch.float64).eps
    return -(g*p)/(epsilon+cost),dict(epsilon=epsilon,criterion='NEGATIVE_FINAL_GRADIENT_TIMES_PROPOSAL_OVER_DIAGONAL_COST',
                                     approximation_ignores_offdiagonal_interactions=True)


def support(spec,proposal,gradient,moment):
    if spec.support_denominator==1:return None,dict(rule='dense')
    if spec.support_rule=='random':
        return solver.select_support(proposal,denominator=spec.support_denominator,seed=spec.random_seed),dict(rule='random',seed=spec.random_seed)
    if spec.support_rule=='magnitude':
        return solver.select_support(proposal,denominator=spec.support_denominator),dict(rule='magnitude')
    score,stats=coordinate_scores(gradient,proposal,moment)
    mask=solver.select_support(proposal,denominator=spec.support_denominator,score=score)
    selected=score[mask]
    return mask,dict(stats,rule='gain_cost',selected_score_quantiles=torch.quantile(selected,torch.tensor([0.,.5,1.],dtype=torch.float64)).tolist(),
                     selected_positive_scores=int((selected>0).sum()),allowed_entries=int(mask.sum()))


def unwanted_loops(rows):
    # A correct requested copy/repetition is not unwanted repetition.
    return sum(bool(r['diagnostics']['loop_indicator'])and not(r.get('protected')and r.get('exact'))for r in rows)


def dev_summary(rows):
    groups={name:[r for r in rows if r['family']==name]for name in ('target','other','protect')}
    return dict(target_exact=sum(bool(r['exact'])for r in groups['target']),
        other_exact=sum(bool(r['exact'])for r in groups['other']),
        protected_exact=sum(bool(r['exact'])for r in groups['protect']),
        protected_correct_ids=[r['id']for r in groups['protect']if r['exact']],
        unwanted_loops=unwanted_loops(rows),raw_loop_indicators=sum(r['diagnostics']['loop_indicator']for r in rows),
        question_echoes=sum(r['diagnostics']['question_echo']for r in rows),empty=sum(r['diagnostics']['empty']for r in rows))


def choose_selection(records,baseline_protected):
    """Prospective selector preserves normal repetition and rewards protection."""
    choices=[]
    for coefficient in (0.,.0625,.25):
        r=min(records,key=lambda x:(x['objective']['fit_ce']+coefficient*x['objective']['preserve_kl'],x['layer']))
        d=r['dev_corrected'];lost=len(set(baseline_protected)-set(d['protected_correct_ids']))
        key=(lost,-d['target_exact']-d['other_exact'],-d['protected_exact'],d['unwanted_loops'],
             d['question_echoes'],d['empty'],0 if coefficient==.0625 else 1 if coefficient==.25 else 2,r['layer'])
        choices.append(dict(kl_weight=coefficient,layer=r['layer'],dev_key=list(key)))
    chosen=min(choices,key=lambda r:tuple(r['dev_key']));coefficient=chosen['kl_weight']
    order=sorted(records,key=lambda r:(r['objective']['fit_ce']+coefficient*r['objective']['preserve_kl'],r['layer']))
    return dict(chosen=chosen,choices=choices,fixed_layer_order=[r['layer']for r in order],
                rule='FIT_LAYER_THEN_DEV_LOST_PROTECTION_CONTENT_PROTECTION_GAIN_UNWANTED_LOOP')
