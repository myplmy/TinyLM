"""Closed partial cache validation and finalizer errors that cannot hide reports."""
import math
import numpy as np


def feature_contract(array,*,tokens,width=1024):
    if (not isinstance(array,np.ndarray)or array.shape!=(tokens,width)or array.dtype!=np.float32
            or not array.flags.c_contiguous or not bool(np.isfinite(array).all())):
        raise ValueError('complete original contiguous finite FP32 native feature matrix required')


def acceptance_contract(position,mapping,modes):
    token=position['teacher_native_argmax']
    if type(token)is not int or not 0<=token<len(mapping)or len(mapping)!=len(modes):raise ValueError('native argmax ID outside exact source map')
    mode=modes[token];student=mapping[token];good=mode in (1,3)and type(student)is int and 0<=student<32768
    if (position['accepted']!=good or position['mapping_mode']!=mode
            or position['mapped_student_argmax']!=(student if good else None)
            or not math.isfinite(position['teacher_native_argmax_logit'])
            or not math.isfinite(position['teacher_native_logsumexp'])
            or position['teacher_native_argmax_logit']>position['teacher_native_logsumexp']+1e-5):
        raise ValueError('native full-token acceptance/probability evidence changed')
    return good


def close_outputs(writers,*,lineage):
    manifests={};errors={}
    for name,writer in writers:
        if writer is None:continue
        try:manifests[name]=writer.close(lineage=lineage)
        except BaseException as exc:errors[name]=repr(exc)
    return manifests,errors
