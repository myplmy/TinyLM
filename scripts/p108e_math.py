"""Guarded low-rank coordinates and local winner QP proposals, never quality."""
from __future__ import annotations
import math
import numpy as np
from scripts import p108d_winner as prior


def orient_rows(rows):
    rows=np.array(rows,dtype=np.float64,copy=True)
    if rows.ndim!=2 or not np.isfinite(rows).all():raise ValueError("finite matrix required")
    for row in rows:
        pivot=int(np.argmax(np.abs(row)))
        if row[pivot]<0:row*=-1
    return rows


def right_basis(target_keys,all_fit_keys,protected_keys,question_weights,*,prompt_extra=16,rank_rtol=1e-8):
    target=prior.finite_matrix(target_keys,"target keys")
    full=prior.finite_matrix(all_fit_keys,"complete FIT keys")
    protected=prior.finite_matrix(protected_keys,"protected keys")
    weights=np.asarray(question_weights,dtype=np.float64)
    if(target.shape[1]!=full.shape[1]or full.shape[1]!=protected.shape[1]or
       weights.shape!=(len(full),)or not np.isfinite(weights).all()or np.any(weights<=0)):
        raise ValueError("same feature coordinates and positive per-position question weights required")
    _,singular,normal=np.linalg.svd(protected,full_matrices=False)
    normal_rank=int(np.sum(singular>rank_rtol*singular[0]))if singular[0]else 0
    normal=normal[:normal_rank]
    target_projected=target-(target@normal.T)@normal
    full_projected=full-(full@normal.T)@normal
    _,target_singular,target_right=np.linalg.svd(target_projected,full_matrices=False)
    cutoff=rank_rtol*max(float(target_singular[0]),float(np.linalg.norm(full_projected)))
    target_rank=int(np.sum(target_singular>cutoff))
    target_right=target_right[:target_rank]
    prompt=full_projected-(full_projected@target_right.T)@target_right
    prompt*=np.sqrt(weights[:,None])
    _,prompt_singular,prompt_right=np.linalg.svd(prompt,full_matrices=False)
    extra=min(prompt_extra,int(np.sum(prompt_singular>cutoff)))
    combined=np.concatenate([target_right,prompt_right[:extra]])
    if len(combined):
        combined=np.linalg.qr(combined.T,mode="reduced")[0].T
        combined=orient_rows(combined)
        orthogonality=float(np.max(np.abs(combined@combined.T-np.eye(len(combined)))))
    else:orthogonality=0.
    reconstruction=(target_projected@combined.T)@combined
    return combined,dict(target_rank=target_rank,prompt_extra_rank=extra,rank=len(combined),
        normal_rank=normal_rank,orthogonality_max=orthogonality,
        protected_response_norm=float(np.linalg.norm(combined@protected.T)),
        target_span_relative_residual=float(np.linalg.norm(target_projected-reconstruction))/
            max(float(np.linalg.norm(target_projected)),1e-30),
        prompt_weighted_energy_retained=(float(np.sum(prompt_singular[:extra]**2))/
            max(float(np.sum(prompt_singular**2)),1e-30)))


def left_basis(planes,question_weights,*,retention=.9999,rank_cap=128):
    planes=np.asarray(planes,dtype=np.float64)
    weights=np.asarray(question_weights,dtype=np.float64)
    if(planes.ndim!=3 or not np.isfinite(planes).all()or weights.shape!=(len(planes),)
       or not 0<retention<=1 or rank_cap<1):raise ValueError("finite native planes and valid rank policy required")
    output=planes.shape[1]
    covariance=np.zeros((output,output),dtype=np.float64)
    for plane,weight in zip(planes,weights):covariance+=weight*(plane@plane.T)
    eigen,vectors=np.linalg.eigh(covariance)
    eigen=np.maximum(eigen[::-1],0.);vectors=vectors[:,::-1]
    total=float(eigen.sum())
    if total<=0:return np.zeros((output,0)),covariance,dict(rank=0,retained_energy=0.,rank_cap_hit=False)
    required=int(np.searchsorted(np.cumsum(eigen)/total,retention))+1
    rank=min(required,rank_cap,output)
    basis=orient_rows(vectors[:,:rank].T).T
    return basis,covariance,dict(rank=rank,required_rank=required,rank_cap_hit=rank<required,
        retained_energy=float(eigen[:rank].sum()/total),target_retention=retention,
        eigenvalues=eigen.tolist(),orthogonality_max=float(np.max(np.abs(basis.T@basis-np.eye(rank)))))


def reconstruct(theta,left,right):
    theta=np.asarray(theta,dtype=np.float64)
    if(theta.size!=left.shape[1]*right.shape[0]or not np.isfinite(theta).all()
       or left.shape[1]<1 or right.shape[0]<1):raise ValueError("finite supported coordinates required")
    return left@theta.reshape(left.shape[1],right.shape[0])@right


def proposal(blocks,current,margins,allowed,budget,*,desired=.10,dual_cap=1e4,max_iter=5000):
    from scipy.optimize import minimize
    margins=np.asarray(margins,dtype=np.float64)
    if(not np.isfinite(margins).all()or not math.isfinite(budget)or budget<=0
       or set(blocks)!=set(current)or not set(allowed).issubset(blocks)):
        raise ValueError("same finite coordinate blocks and explicit allowed layers required")
    active=[layer for layer in allowed if blocks[layer].shape[1]>0]
    if not active:return {k:v.copy()for k,v in current.items()},dict(status="NO_ACTIVE_DIRECTION")
    count=len(margins);norm2=np.zeros(count);rhs=desired-margins
    for layer in active:
        matrix=np.asarray(blocks[layer],dtype=np.float64)
        if matrix.ndim!=2 or len(matrix)!=count or matrix.shape[1]!=len(current[layer]):
            raise ValueError("complete native plane rows and coordinate sizes required")
        norm2+=np.sum(matrix**2,axis=1)
        rhs+=matrix@current[layer]
    row_norm=np.sqrt(norm2);usable=row_norm>1e-14
    if not usable.any():return {k:v.copy()for k,v in current.items()},dict(status="ZERO_NATIVE_SENSITIVITY")
    normalized={layer:blocks[layer][usable]/row_norm[usable,None]for layer in active}
    bound=rhs[usable]/row_norm[usable]
    gram=sum(matrix@matrix.T for matrix in normalized.values())

    def objective(dual):
        product=gram@dual
        return .5*float(dual@product)-float(bound@dual),product-bound

    result=minimize(objective,np.zeros(len(bound)),method="L-BFGS-B",jac=True,
        bounds=[(0.,dual_cap)]*len(bound),
        options=dict(ftol=0.,gtol=1e-11,maxiter=max_iter,maxls=80,maxcor=40))
    dual=np.asarray(result.x)
    if not np.isfinite(dual).all():raise RuntimeError("non-finite local dual")
    candidate={layer:value.copy()for layer,value in current.items()}
    for layer in active:candidate[layer]=normalized[layer].T@dual
    fixed=sum(float(value@value)for layer,value in current.items()if layer not in active)
    remaining=math.sqrt(max(0.,budget**2-fixed))
    active_norm=math.sqrt(sum(float(candidate[layer]@candidate[layer])for layer in active))
    clip=min(1.,remaining*(1-1e-6)/max(active_norm,1e-30))
    for layer in active:candidate[layer]*=clip
    predicted=margins.copy()
    for layer in active:predicted+=blocks[layer]@(candidate[layer]-current[layer])
    gradient=gram@dual-bound
    projected=np.where(((dual<=1e-12)&(gradient>0))|((dual>=dual_cap-1e-12)&(gradient<0)),0.,gradient)
    return candidate,dict(status="LOCAL_QP_PROPOSAL_NOT_GLOBAL_OPTIMUM",allowed_layers=list(active),
        solver_success=bool(result.success),solver_message=str(result.message),iterations=int(result.nit),
        projected_kkt_max=float(np.max(np.abs(projected))),dual_cap_active=int(np.sum(dual>=dual_cap-1e-8)),
        zero_derivative_violations=int(np.sum((~usable)&(rhs>0))),unclipped_active_norm=active_norm,
        available_norm=remaining,post_clip=clip,predicted_margins=predicted.tolist(),
        predicted_mean_hinge=float(np.mean(np.maximum(desired-predicted,0.))),
        coefficient_norm=math.sqrt(sum(float(v@v)for v in candidate.values())))


def score(margins,offsets,*,desired=.10):
    margins=np.asarray(margins,dtype=np.float64)
    if margins.ndim!=1 or not np.isfinite(margins).all():raise ValueError("finite full-vocabulary margins required")
    full=sum(bool(np.all(margins[start:end]>0))for start,end in offsets)
    return dict(questions_all_gold=full,positions_gold=int(np.sum(margins>0)),
        mean_hinge=float(np.mean(np.maximum(desired-margins,0.))),minimum_margin=float(margins.min()))


def rank_key(record):
    outcome=record["score"]
    return(-outcome["questions_all_gold"],outcome["mean_hinge"],record["actual_norm"],
           record.get("alpha",0.),record.get("layer",-1))
