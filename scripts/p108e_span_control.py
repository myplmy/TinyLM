"""Keep all violated affine winner constraints in a fixed output subspace."""
import numpy as np
from scripts import p108d_winner as margins_owner
from scripts import p108e_math as QP


def solve(head,base,keys,gold,gate,required,budget,*,rounds=32,check=None):
    head=margins_owner.finite_matrix(head,"variable head")
    base=margins_owner.finite_matrix(base,"fixed logit offset")
    keys=margins_owner.finite_matrix(keys,"fixed keys")
    gold=np.asarray(gold,dtype=np.int64);required=np.asarray(required,dtype=np.float64)
    if base.shape!=(len(keys),len(head))or required.shape!=(len(keys),):raise ValueError("same fixed rows and vocabulary required")
    theta=np.zeros(head.shape[1]*keys.shape[1]);constraints=[];known=set();trace=[]
    status="ROUND_LIMIT"
    for iteration in range(rounds+1):
        if check is not None:check()
        scores=base+gate*((keys@theta.reshape(head.shape[1],keys.shape[1]).T)@head.T)
        actual,rivals=margins_owner.winner_margins(scores,gold)
        violation=required-actual
        if float(violation.max())<=1e-5:status="ALL_AFFINE_WINNER_CONSTRAINTS_FEASIBLE";break
        if iteration==rounds:break
        added=0
        for position in np.where(violation>1e-5)[0]:
            item=(int(position),int(rivals[position]))
            if item not in known:constraints.append(item);known.add(item);added+=1
        if not added:status="WORKING_SET_NOT_RESOLVED_WITHIN_BUDGET_OR_SOLVER_LIMIT";break
        positions=np.array([item[0]for item in constraints]);others=np.array([item[1]for item in constraints])
        differences=gate*(head[gold[positions]]-head[others])
        planes=np.einsum("ni,nj->nij",differences,keys[positions]).reshape(len(constraints),-1)
        original=base[positions,gold[positions]]-base[positions,others]
        shifted=original-required[positions]+.10
        result,solver=QP.proposal({0:planes},{0:np.zeros_like(theta)},shifted,[0],budget,desired=.10)
        theta=result[0]
        trace.append(dict(round=iteration+1,constraints=len(constraints),added=added,solver=solver))
    scores=base+gate*((keys@theta.reshape(head.shape[1],keys.shape[1]).T)@head.T)
    actual,rivals=margins_owner.winner_margins(scores,gold)
    return theta.reshape(head.shape[1],keys.shape[1]),dict(status=status,trace=trace,constraints=constraints,
        maximum_raw_violation=float((required-actual).max()),correct=int(np.sum(scores.argmax(axis=1)==gold)),
        positions=len(keys),norm=float(np.linalg.norm(theta)),all_previous_rivals_kept=True)
