"""Selection contracts for bounded actual winner probes, no model execution."""
import hashlib
import numpy as np
from scripts import p108e_math as geometry


def mix(current,proposal,alpha):
    if not 0<=alpha<=1 or set(current)!=set(proposal):raise ValueError("same coordinates and bounded step required")
    result={}
    for layer in current:
        if current[layer].shape!=proposal[layer].shape:raise ValueError("coordinate shape changed")
        result[layer]=((1-alpha)*current[layer]+alpha*proposal[layer]).astype(np.float64)
        if not np.isfinite(result[layer]).all():raise ValueError("non-finite proposal interpolation")
    return result


def signature(coordinates):
    digest=hashlib.sha256()
    for layer in sorted(coordinates):
        array=np.asarray(coordinates[layer],dtype=np.float64)
        digest.update(str((layer,array.shape)).encode());digest.update(array.tobytes())
    return digest.hexdigest().upper()


def select(probes,current,*,budget,hinge_resolution=1e-5,guard_logit_tolerance=.002):
    eligible=[row for row in probes if row["guard_argmax_mismatches"]==0
              and row["guard_logit_max_error"]<=guard_logit_tolerance
              and row["actual_norm"]<=budget*(1+2e-5)]
    if not eligible:return None,"NO_PHYSICALLY_ELIGIBLE_PROBE"
    chosen=min(eligible,key=geometry.rank_key)
    old,new=current["score"],chosen["score"]
    if(new["questions_all_gold"]>old["questions_all_gold"]or
       new["questions_all_gold"]==old["questions_all_gold"]and
       new["mean_hinge"]<old["mean_hinge"]-hinge_resolution):
        return chosen,"ACTUAL_FULL_VOCAB_IMPROVEMENT"
    return None,"NO_RESOLVED_ACTUAL_IMPROVEMENT"


def physical_path(before,after):
    if set(before)!=set(after):raise ValueError("same physical owners required")
    return float(np.sqrt(sum(np.sum((after[layer].astype(np.float64)-before[layer].astype(np.float64))**2)
                              for layer in before)))


def after_xor(before,after):
    if(before.dtype!=np.float32 or after.dtype!=np.float32 or before.shape!=after.shape
       or not np.isfinite(before).all()or not np.isfinite(after).all()):
        raise ValueError("same complete finite FP32 matrices required")
    return np.bitwise_xor(np.ascontiguousarray(before).view(np.uint32),
                         np.ascontiguousarray(after).view(np.uint32))


def restore_xor(before,encoded):
    if before.dtype!=np.float32 or encoded.dtype!=np.uint32 or before.shape!=encoded.shape:
        raise ValueError("exact FP32 parent and lossless uint32 XOR patch required")
    result=np.bitwise_xor(np.ascontiguousarray(before).view(np.uint32),encoded).view(np.float32).copy()
    if not np.isfinite(result).all():raise ValueError("non-finite restored weight")
    return result
