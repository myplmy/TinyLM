"""Complete student-vocabulary head mapping/init; no file I/O or model import."""
from __future__ import annotations

from collections import Counter

from scripts.p106b_alm_bytes import student_piece_bytes
from scripts.p106b_dvlm_pts import AdmissionHold


def native_vocabulary(raw):
    if raw.get('model',{}).get('type') != 'BPE' or raw.get('decoder',{}).get('type') != 'ByteLevel':
        raise AdmissionHold('explicit native BPE/ByteLevel head vocabulary required')
    added={row['id']:row for row in raw.get('added_tokens',[])}
    if any(type(index) is not int or index < 0 for index in added):
        raise AdmissionHold('added native token IDs must be nonnegative integers')
    result={}
    for spelling,index in raw['model']['vocab'].items():
        if type(index) is not int or index < 0 or index in result:
            raise AdmissionHold('unique nonnegative native vocabulary IDs required')
        if index in added:
            token=added[index]
            semantics=tuple(token.get(key,'UNDECLARED') for key in ('special','single_word','lstrip','rstrip','normalized'))
            result[index]=('ADDED_LITERAL',token['content'].encode('utf-8'),semantics)
        else:
            result[index]=('ORDINARY_BYTES',student_piece_bytes(spelling),())
    for index,token in added.items():
        if index not in result:
            semantics=tuple(token.get(key,'UNDECLARED') for key in ('special','single_word','lstrip','rstrip','normalized'))
            result[index]=('ADDED_LITERAL',token['content'].encode('utf-8'),semantics)
    return result


def initialization_map(student_raw,teacher_raw,*,decode_student,encode_teacher,decode_teacher):
    student,teacher=native_vocabulary(student_raw),native_vocabulary(teacher_raw)
    if set(student) != set(range(len(student))):
        raise AdmissionHold('complete dense student head IDs required; missing rows need an explicit policy')
    inverse={}
    for index,piece in teacher.items():
        inverse.setdefault(piece,[]).append(index)
    records=[]
    for index in range(len(student)):
        native=student[index];shared=inverse.get(native,[])
        record=dict(student_id=index,method='HOLD',teacher_ids=None)
        if len(shared)==1:
            record.update(method='SHARED_NATIVE_PIECE',teacher_ids=shared)
        elif len(shared)>1:
            record['reason']='AMBIGUOUS_SHARED_NATIVE_PIECE'
        else:
            try:
                piece=native[1]
                if not piece:
                    raise AdmissionHold('EMPTY_STUDENT_NATIVE_PIECE')
                text=piece.decode('utf-8',errors='strict')
                if decode_student([index]) != text:
                    raise AdmissionHold('STANDALONE_STUDENT_HEAD_DECODE_DIFFERS')
                ids=list(encode_teacher(text))
                if (not ids or any(type(i) is not int or i not in teacher for i in ids)
                        or decode_teacher(ids) != text):
                    raise AdmissionHold('UNMATCHED_HEAD_ROW_NOT_LOSSLESSLY_RETOKENIZABLE')
                record.update(method='MEAN_RETOKENIZED',teacher_ids=ids)
            except (UnicodeError,AdmissionHold) as error:
                record['reason']=type(error).__name__+': '+str(error)
        records.append(record)
    counts=dict(Counter(row['method'] for row in records))
    return dict(records=records,counts=counts,student_vocab_size=len(student),
        teacher_native_vocab_size=len(teacher),complete=counts.get('HOLD',0)==0,
        shared_matching='RAW_BYTES_AND_KIND_AND_DECLARED_ADDED_TOKEN_PROPERTIES',
        unmatched_policy='STANDALONE_LOSSLESS_UTF8_TEACHER_RETOKENIZATION;NO_RANDOM_OR_ZERO_FILL',
        quality_claim=False)


def initialize_head(torch,teacher_head,mapping,*,chunk_rows=128):
    records=mapping['records']
    if not mapping['complete'] or any(row['method']=='HOLD' for row in records):
        raise AdmissionHold('complete full-vocabulary mapping required before head allocation')
    if (teacher_head.ndim != 2 or not teacher_head.is_floating_point()
            or not bool(torch.isfinite(teacher_head).all()) or type(chunk_rows) is not int or chunk_rows < 1
            or [row['student_id'] for row in records] != list(range(mapping['student_vocab_size']))
            or any(not row['teacher_ids'] or any(type(i) is not int or not 0<=i<len(teacher_head)
                for i in row['teacher_ids']) for row in records)):
        raise AdmissionHold('complete ordered native head rows and finite source weight required')
    output=teacher_head.new_empty((len(records),teacher_head.shape[1]))
    with torch.no_grad():
        for start in range(0,len(records),chunk_rows):
            rows=records[start:start+chunk_rows]
            width=max(len(row['teacher_ids']) for row in rows)
            ids=torch.tensor([row['teacher_ids']+[0]*(width-len(row['teacher_ids'])) for row in rows],
                dtype=torch.long,device=teacher_head.device)
            valid=torch.tensor([[1.]*len(row['teacher_ids'])+[0.]*(width-len(row['teacher_ids'])) for row in rows],
                dtype=teacher_head.dtype,device=teacher_head.device)
            values=teacher_head.detach()[ids]
            output[start:start+len(rows)]=(values*valid[:,:,None]).sum(1)/valid.sum(1)[:,None]
    return torch.nn.Parameter(output,requires_grad=True)


def independent_row_oracle(torch,head,teacher_head,mapping,*,atol=1e-5,rtol=1e-4):
    actual=head.detach().cpu()
    source=teacher_head.detach().cpu()
    expected=torch.stack([source[row['teacher_ids']].double().mean(0).to(actual.dtype) for row in mapping['records']])
    close=torch.isclose(actual,expected,atol=atol,rtol=rtol)
    finite=bool(torch.isfinite(actual).all() and torch.isfinite(expected).all())
    return dict(rows=len(actual),hidden_size=actual.shape[1],atol=atol,rtol=rtol,
        passed=finite and bool(close.all()),finite=finite,violating_rows=int((~close.all(-1)).sum().item()),
        max_abs=float((actual-expected).abs().max().item()) if finite else None,
        reference='ALL_ROWS_CPU_FP64_MEAN_CAST_TO_ACTUAL_DTYPE;GPU_CHUNKED_SUM_INDEPENDENT')


def head_gradient_probe(torch,head,hidden,head_targets):
    if hidden.ndim != 2 or len(hidden) != len(head_targets):
        raise AdmissionHold('full private-head hidden/next-target coverage required')
    chosen=[i for i,target in enumerate(head_targets) if target != -100]
    if not chosen or any(type(head_targets[i]) is not int or not 0<=head_targets[i]<len(head) for i in chosen):
        raise AdmissionHold('original nonempty next-student supervision required')
    features=hidden.detach()[chosen].to(device=head.device,dtype=head.dtype).clone()
    labels=torch.tensor([head_targets[i] for i in chosen],dtype=torch.long,device=head.device)
    logits=features@head.T
    total=torch.nn.functional.cross_entropy(logits,labels,reduction='sum')
    loss=total/len(chosen)
    loss.backward()
    gradient=head.grad
    finite=bool(torch.isfinite(loss) and gradient is not None and torch.isfinite(gradient).all())
    return dict(supervised_targets=len(chosen),CE_sum=float(total.detach()),CE_mean=float(loss.detach()),
        full_student_vocab=len(head),finite=finite,gradient_nonzero=gradient is not None and bool((gradient!=0).any()),
        gradient_norm=float(gradient.norm().item()) if finite else None,
        optimizer_updates=0,training_steps=0,checkpoint_writes=0,quality_claim=False,
        semantics='UNTRAINED_HEAD_INITIALIZATION_AND_BACKWARD_WIRING_ONLY')
