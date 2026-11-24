"""Finite endpoint secants with actual physical step coordinates."""
import numpy as np


def secants(before,plus,minus,t_plus,t_minus):
    before=np.asarray(before,dtype=np.float64)
    plus=np.asarray(plus,dtype=np.float64);minus=np.asarray(minus,dtype=np.float64)
    if(before.shape!=plus.shape or before.shape!=minus.shape
       or not all(np.isfinite(x).all()for x in (before,plus,minus))
       or not np.isfinite(t_plus)or not np.isfinite(t_minus)or t_plus<=0 or t_minus>=0):
        raise ValueError("finite same endpoint shapes and positive/negative actual steps required")
    system=np.asarray([[t_plus,t_plus*t_plus],[t_minus,t_minus*t_minus]])
    if np.linalg.cond(system)>1e8:raise ValueError("secant coordinate system is ill-conditioned")
    rhs=np.stack([plus-before,minus-before])
    derivative,curvature=np.linalg.solve(system,rhs.reshape(2,-1)).reshape((2,*before.shape))
    return derivative,curvature


def physical_coordinate(original,after,direction):
    change=np.asarray(after,dtype=np.float64)-original
    direction=np.asarray(direction,dtype=np.float64);energy=float(np.sum(direction**2))
    if change.shape!=direction.shape or energy<=0:raise ValueError("same nonzero physical direction required")
    scalar=float(np.sum(change*direction)/energy)
    residual=change-scalar*direction
    return dict(scalar=scalar,norm=float(np.linalg.norm(change)),
                orthogonal_rounding_norm=float(np.linalg.norm(residual)))


def choose(rows,*,resolution=1e-5):
    if not rows:raise ValueError("complete predicted candidate rows required")
    best=max(r["score"]["questions_all_gold"]for r in rows)
    eligible=[r for r in rows if r["score"]["questions_all_gold"]==best]
    minimum=min(r["score"]["mean_hinge"]for r in eligible)
    tied=[r for r in eligible if r["score"]["mean_hinge"]<=minimum+resolution]
    return min(tied,key=lambda r:r["layer"])
