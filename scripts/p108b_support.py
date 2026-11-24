"""Alternative sparse utilities with no proposal-denominator singularity."""
import torch
from scripts import p108b_solver as solver


def scores(criterion,gradient,proposal,moment):
    g,p,c=(x.detach().cpu().double()for x in(gradient,proposal,moment))
    if g.shape!=p.shape or c.shape!=(p.shape[1],p.shape[1])or not bool((c.diagonal()>0).all()):
        raise ValueError('matching gradient/proposal and positive covariance diagonal required')
    if any(not bool(torch.isfinite(x).all())for x in(g,p,c)):raise ValueError('finite score inputs required')
    if criterion=='MAG':return p.abs()
    if criterion=='ABSGAIN':return -g*p
    if criterion=='GRADCOST':return g.square()/c.diagonal()[None,:]
    raise ValueError('explicit sparse utility required')


def select(criterion,denominator,gradient,proposal,moment):
    utility=scores(criterion,gradient,proposal,moment)
    mask=solver.select_support(proposal,denominator=denominator,score=utility)
    return mask,dict(criterion=criterion,denominator=denominator,allowed_entries=int(mask.sum()),
        selected_utility_sum=float(utility[mask].sum()),
        limitation='diagonal/local approximation; refitted increment and final nonlinear gain must be measured')
