"""Native predictor-only views and streaming global-update shares for DWA.

No source acquisition, model load, file I/O or CUDA operation on import.
The cached teacher has one hidden row per original next-token predictor.
"""
from __future__ import annotations
import math
from scripts.p106b_dwa_cma import NativeView, AdmissionHold

def predictor_view(torch,ids,supervised,predictor_hidden,embedding):
    ids,mask=tuple(ids),tuple(supervised)
    if (len(ids)<2 or len(mask)!=len(ids) or predictor_hidden.ndim!=2
            or len(predictor_hidden)!=len(ids)-1 or any(type(i)is not int or i<0 for i in ids)
            or any(type(v)is not bool for v in mask)):
        raise AdmissionHold('exact full native IDs/mask and L-1 predictor hidden rows required')
    positions=tuple(i for i in range(len(ids)-1) if mask[i+1])
    if not positions:raise AdmissionHold('nonempty original native next-target view required')
    next_positions=tuple(i+1 for i in positions)
    current=torch.tensor([ids[i] for i in positions],device=predictor_hidden.device,dtype=torch.long)
    target=torch.tensor([ids[i] for i in next_positions],device=predictor_hidden.device,dtype=torch.long)
    return NativeView(embedding(current),embedding(target),predictor_hidden[list(positions)],target,positions,next_positions)

def streaming_share(packet,*,global_student_targets,ce_rate=1.,kd_rate=1.,dtw_rate=1.):
    if (type(global_student_targets)is not int or not 0<packet['student_count']<=global_student_targets
            or any(not math.isfinite(rate) or rate<0 for rate in (ce_rate,kd_rate,dtw_rate))):
        raise AdmissionHold('explicit complete-update denominator and finite nonnegative rates required')
    raw=packet['raw']
    return (ce_rate*raw['student_ce']+kd_rate*(raw['projector_ce']+raw['student_kd']+raw['teacher_kd'])
        +dtw_rate*(raw['dtw_hidden']+raw['dtw_embedding']))/global_student_targets

def close_accounting(rows,*,expected_ids,student_targets,teacher_targets):
    if ([row['row_id'] for row in rows]!=list(expected_ids)
            or len(set(expected_ids))!=len(expected_ids)
            or sum(row['student_count'] for row in rows)!=student_targets
            or sum(row['teacher_count'] for row in rows)!=teacher_targets):
        raise AdmissionHold('entire ordered update and original native target counts must close')
    return dict(rows=len(rows),student_targets=student_targets,teacher_targets=teacher_targets,
        normalization='SUM_OF_ALL_RAW_ROW_TERMS_DIVIDED_BY_COMPLETE_STUDENT_TARGET_COUNT')
