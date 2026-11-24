"""Explicit optional raw-byte policy for only strict invalid-UTF8 head HOLDs.

No model, tensors or tokenizer imports. This new initialization variant never
changes the original strict UTF8 map, PTS admission or native HPA gate.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from scripts.p106b_dvlm_head import native_vocabulary
from scripts.p106b_dvlm_pts import AdmissionHold

def extend_invalid_utf8(mapping,student_raw,teacher_raw,*,bpe_tokenize):
    student,teacher=native_vocabulary(student_raw),native_vocabulary(teacher_raw)
    rows=deepcopy(mapping['records'])
    if (mapping['student_vocab_size']!=len(student) or set(student)!=set(range(len(student)))
            or [row['student_id'] for row in rows]!=list(range(len(student)))):
        raise AdmissionHold('complete original strict ordered map required')
    spellings={value:key for key,value in student_raw['model']['vocab'].items()}
    changes=[]
    for row in rows:
        if row['method']!='HOLD':continue
        index=row['student_id'];piece=student[index]
        # This policy does not rescue ambiguous shared pieces or added tokens.
        if piece[0]!='ORDINARY_BYTES' or not row.get('reason','').startswith('UnicodeDecodeError:'):
            continue
        try:piece[1].decode('utf-8',errors='strict')
        except UnicodeDecodeError:pass
        else:raise AdmissionHold('claimed strict invalidUTF8 HOLD contains valid text')
        ids=list(bpe_tokenize(spellings[index]))
        if (not ids or any(type(i)is not int or i not in teacher or teacher[i][0]!='ORDINARY_BYTES' for i in ids)
                or b''.join(teacher[i][1] for i in ids)!=piece[1]):
            raise AdmissionHold('native BPE decomposition must reconstruct exact original bytes')
        original=deepcopy(row)
        row.update(method='MEAN_NATIVE_BYTE_BPE',teacher_ids=ids,
            original_strict_hold=original,byte_identity=piece[1].hex().upper(),
            byte_policy='DIRECT_TEACHER_BPE_MODEL_ON_ORIGINAL_BYTELEVEL_SPELLING;NO_NORMALIZATION_OR_DECODE')
        row.pop('reason',None)
        changes.append(dict(student_id=index,original=original,new_teacher_ids=ids,bytes_hex=piece[1].hex().upper()))
    counts=dict(Counter(row['method'] for row in rows))
    return dict(mapping,records=rows,counts=counts,complete=counts.get('HOLD',0)==0,
        original_strict_counts=dict(mapping['counts']),changes=changes,
        unmatched_policy='STRICT_UTF8_MAP_PLUS_EXPLICIT_INVALID_UTF8_RAW_BYTE_BPE_MEAN_VARIANT',
        adoption=False,quality_claim=False,HPA_gate_changed=False,PTS_admission_changed=False)
