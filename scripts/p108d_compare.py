"""Physical ray intervals, exact norm matching and frozen column selection."""
import math
import numpy as np
from scripts import p108d_winner as constraints


def ray_interval(base, change, gold, required, *, tolerance=1e-12):
    base=constraints.finite_matrix(base,"base scores")
    change=constraints.finite_matrix(change,"score change")
    gold=np.asarray(gold,dtype=np.int64)
    required=np.asarray(required,dtype=np.float64)
    constraints.winner_margins(base,gold)
    if change.shape!=base.shape or required.shape!=(len(base),) or np.any(required<=0):
        raise ValueError("same complete scores and positive required margins")
    offsets=np.arange(len(base))
    before=base[offsets,gold,None]-base
    slope=change[offsets,gold,None]-change
    bound=required[:,None]-before
    valid=np.ones(base.shape,dtype=bool);valid[offsets,gold]=False
    positive=valid & (slope>tolerance)
    negative=valid & (slope < -tolerance)
    zeros=valid & ~(positive|negative)
    if np.any(zeros & (bound>tolerance)):
        return dict(status="NO_FEASIBLE_RAY_ZERO_SLOPE",lower=None,upper=None)
    lower=max(0.,float(np.max(bound[positive]/slope[positive]))) if positive.any() else 0.
    upper=float(np.min(bound[negative]/slope[negative])) if negative.any() else None
    return dict(status="FEASIBLE_RAY" if upper is None or lower<=upper else "EMPTY_RAY_INTERVAL",
                lower=lower,upper=upper,positive_constraints=int(positive.sum()),
                negative_constraints=int(negative.sum()))


def match_norm(before, direction, target):
    direction=constraints.finite_matrix(direction,"direction")
    energy=float(np.linalg.norm(direction))
    if energy<=0 or not math.isfinite(target) or target<=0:
        raise ValueError("nonzero finite direction and positive target norm required")
    low,high=0.,2*target/energy
    for _ in range(36):
        middle=(low+high)/2
        after,actual,physical=constraints.materialize(before,middle*direction,budget=target)
        if physical["actual_norm"]<target:low=middle
        else:high=middle
    options=[]
    for scalar in (low,high):
        after,actual,physical=constraints.materialize(before,scalar*direction,budget=target)
        options.append((abs(physical["actual_norm"]-target),scalar,after,actual,physical))
    _,scalar,after,actual,physical=min(options,key=lambda item:item[0])
    physical.update(scalar=scalar,comparison="MATCHED_ACTUAL_NET",
                    relative_norm_error=abs(physical["actual_norm"]-target)/target)
    if physical["relative_norm_error"]>2e-5:
        raise ValueError("physical norm matching outside fixed tolerance")
    return after,actual,physical


def column_selection(delta, protected, count, *, seed=None):
    delta=constraints.finite_matrix(delta,"dense solution")
    protected=constraints.finite_matrix(protected,"protected keys")
    if delta.shape[1]!=protected.shape[1] or type(count)is not int or not 0<count<=delta.shape[1]:
        raise ValueError("same feature coordinates and valid column count required")
    normal_energy=np.mean(protected**2,axis=0)
    denominator=normal_energy+.01*float(normal_energy.mean())
    if np.any(denominator<=0):raise ValueError("normal energy regularizer is degenerate")
    scores=np.sum(delta**2,axis=0)/denominator
    if seed is None:
        ranked=np.lexsort((np.arange(len(scores)),-scores))
        chosen=np.sort(ranked[:count])
    else:
        if type(seed)is not int:raise ValueError("explicit integer seed required")
        chosen=np.sort(np.random.default_rng(seed).choice(delta.shape[1],count,replace=False))
        ranked=np.lexsort((np.arange(len(scores)),-scores))
    return chosen,dict(rule="DELTA_ENERGY_OVER_NORMAL_KEY_ENERGY" if seed is None else "RANDOM_MATCHED_COLUMNS",
                       seed=seed,count=count,total=delta.shape[1],scores=scores.tolist(),
                       ranked_indices=ranked.tolist(),selected_indices=chosen.tolist())


def repair_ray(before,direction,head,residuals,keys,gold,gate,required,dual_lower_bound,*,check=None):
    head=constraints.finite_matrix(head,"head")
    baseline=residuals@head.T
    score_change=(gate*(keys@direction.T))@head.T
    interval=ray_interval(baseline,score_change,gold,required)
    if interval["status"]!="FEASIBLE_RAY":return None,dict(interval=interval,status="RAY_NOT_RECOVERED")
    low=max(1.,interval["lower"])
    high=low*(1+1e-3)
    if interval["upper"]is not None:high=min(high,interval["upper"])
    if high<low:return None,dict(interval=interval,status="RAY_NOT_RECOVERED")

    def trial(scalar):
        if check is not None:check()
        after,actual,physical=constraints.materialize(before,direction*scalar,budget=1e100)
        scores=(residuals+gate*(keys@actual.T))@head.T
        margins,_=constraints.winner_margins(scores,gold)
        violation=float(np.max(required-margins))
        return after,actual,physical,violation

    best=trial(high)
    if best[-1]>0:return None,dict(interval=interval,status="FP32_RAY_NOT_RECOVERED",violation=best[-1])
    for _ in range(22):
        middle=(low+high)/2
        sample=trial(middle)
        if sample[-1]<=0:high,best=middle,sample
        else:low=middle
    after,actual,physical,violation=best
    primal=.5*physical["actual_norm"]**2
    gap=(primal-dual_lower_bound)/max(1.,primal)
    return after,dict(status="FEASIBLE_RAY_WITH_DUAL_BOUND",interval=interval,scalar=high,
        maximum_raw_violation=violation,actual_norm=physical["actual_norm"],
        primal_objective=primal,existing_dual_lower_bound=dual_lower_bound,
        signed_relative_gap=gap,minimum_norm_numeric_gap_confirmed=bool(-1e-8<=gap<=1e-5),
        note="FP32 feasible upper bound versus old dual lower bound; no new generation or global quality claim")
