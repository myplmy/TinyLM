"""Small weighted prediction calibrators; no model, source I/O or edit selection."""
import numpy as np

METHODS=("ZERO","RAW","MEAN","SCALAR","AFFINE","QUADRATIC_DEPTH")


def semantic_group(fact):
    return fact.removesuffix("_ko").removesuffix("_en")


def fold_indices(layers,groups,layer,group):
    layers=np.asarray(layers);groups=np.asarray(groups)
    if layers.shape!=groups.shape or layers.ndim!=1:raise ValueError("aligned fold metadata required")
    train=(layers!=layer)&(groups!=group);test=(layers==layer)&(groups==group)
    if not train.any()or not test.any():raise ValueError("nonempty separated fold required")
    return train,test


def group_weights(groups):
    groups=np.asarray(groups)
    weights=np.array([1./sum(groups==g)for g in groups],dtype=float)
    return weights/weights.sum()


def predict(method,p,depth,y,weights,test_p,test_depth):
    p,depth,y,weights,test_p,test_depth=[np.asarray(v,dtype=float)for v in (p,depth,y,weights,test_p,test_depth)]
    if (method not in METHODS or p.ndim!=1 or p.shape!=y.shape or p.shape!=depth.shape
        or p.shape!=weights.shape or test_p.shape!=test_depth.shape
        or not all(np.isfinite(v).all()for v in (p,depth,y,weights,test_p,test_depth))
        or np.any(weights<=0)):
        raise ValueError("finite aligned calibration data and positive weights required")
    weights=weights/weights.sum()
    if method=="ZERO":return np.zeros_like(test_p),dict(kind=method)
    if method=="RAW":return test_p.copy(),dict(kind=method)
    if method=="MEAN":
        mean=float(np.sum(weights*y));return np.full_like(test_p,mean),dict(kind=method,mean=mean)
    if method=="SCALAR":
        denominator=float(np.sum(weights*p*p))
        gain=float(np.sum(weights*p*y))/denominator if denominator>1e-20 else 0.
        return gain*test_p,dict(kind=method,gain=gain)
    train=np.stack([p]if method=="AFFINE"else[p,p*p,depth],axis=1)
    test=np.stack([test_p]if method=="AFFINE"else[test_p,test_p*test_p,test_depth],axis=1)
    center=np.sum(weights[:,None]*train,axis=0)
    scale=np.sqrt(np.sum(weights[:,None]*(train-center)**2,axis=0));scale=np.maximum(scale,1e-12)
    x=np.column_stack([np.ones(len(p)),(train-center)/scale])
    z=np.column_stack([np.ones(len(test_p)),(test-center)/scale])
    ridge=.01 if method=="QUADRATIC_DEPTH"else 0.
    a=x*np.sqrt(weights[:,None]);b=y*np.sqrt(weights)
    if ridge:
        penalty=np.eye(x.shape[1])*np.sqrt(ridge);penalty[0,0]=0
        a=np.vstack([a,penalty]);b=np.concatenate([b,np.zeros(x.shape[1])])
    coefficient,_,rank,singular=np.linalg.lstsq(a,b,rcond=None)
    return z@coefficient,dict(kind=method,coefficient=coefficient.tolist(),center=center.tolist(),
        scale=scale.tolist(),ridge=ridge,rank=int(rank),singular_values=singular.tolist())


def average_ranks(values):
    values=np.asarray(values);order=np.argsort(values,kind="stable");ranks=np.empty(len(values),float);i=0
    while i<len(order):
        j=i+1
        while j<len(order)and values[order[j]]==values[order[i]]:j+=1
        ranks[order[i:j]]=(i+j-1)/2.;i=j
    return ranks


def auc(scores,labels):
    labels=np.asarray(labels,dtype=bool);positive=int(labels.sum());negative=len(labels)-positive
    if not positive or not negative:return None
    ranks=average_ranks(scores)+1
    return float((ranks[labels].sum()-positive*(positive+1)/2)/(positive*negative))


def evaluate(rows,predictions):
    actual=np.array([r["actual_ce_gain"]for r in rows]);guess=np.asarray(predictions,float)
    weights=group_weights([r["semantic_group"]for r in rows]);error=guess-actual
    ranking=[]
    for case in sorted({r["case_id"]for r in rows}):
        indexes=[i for i,r in enumerate(rows)if r["case_id"]==case]
        chosen=min(indexes,key=lambda i:(-guess[i],rows[i]["layer"]))
        best=max(actual[i]for i in indexes)
        a,b=average_ranks(actual[indexes]),average_ranks(guess[indexes])
        correlation=float(np.corrcoef(a,b)[0,1])if np.std(a)>0 and np.std(b)>0 else None
        ranking.append(dict(case_id=case,chosen_layer=rows[chosen]["layer"],
            actual_chosen_gain=float(actual[chosen]),best_gain=float(best),regret=float(best-actual[chosen]),
            chosen_is_best=bool(actual[chosen]==best),spearman=correlation))
    return dict(semantic_weighted_rmse=float(np.sqrt(np.sum(weights*error**2))),
        semantic_weighted_mae=float(np.sum(weights*np.abs(error))),
        sign_accuracy=float(np.mean((guess>0)==(actual>0))),
        mean_case_regret=float(np.mean([r["regret"]for r in ranking])),
        best_layer_hits=sum(r["chosen_is_best"]for r in ranking),cases=len(ranking),
        generated_exact_auc=auc(guess,[r["generated_exact"]for r in rows]),ranking=ranking)
