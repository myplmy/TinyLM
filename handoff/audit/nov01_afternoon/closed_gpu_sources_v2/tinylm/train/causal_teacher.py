"""Same-vocabulary causal-only teacher KL; never an answer-quality judge."""
from __future__ import annotations

import math
import re
import torch
from .trainer import _kd_kl


class CausalTeacherKL:
    def __init__(self, teacher, *, vocab_size, student_tokenizer_sha256,
                 teacher_tokenizer_sha256, teacher_identity_sha256,
                 coefficient=.1, temperature=1., chunk_rows=256):
        fingerprints=(student_tokenizer_sha256,teacher_tokenizer_sha256,teacher_identity_sha256)
        if any(not isinstance(x,str) or re.fullmatch('[0-9A-F]{64}',x) is None for x in fingerprints):
            raise ValueError('명시한 tokenizer·교사 identity SHA가 필요합니다')
        if student_tokenizer_sha256!=teacher_tokenizer_sha256:
            raise ValueError('다른 tokenizer의 KL 정렬은 지원하지 않습니다')
        if (type(vocab_size) is not int or vocab_size<2 or type(chunk_rows) is not int or chunk_rows<1
                or type(coefficient) not in (int,float) or not math.isfinite(coefficient) or not 0<coefficient<=1
                or type(temperature) not in (int,float) or not math.isfinite(temperature) or temperature<=0):
            raise ValueError('명시한 어휘·유한 계수/온도·행 청크가 필요합니다')
        self.teacher=teacher
        self.contract=dict(schema='P107_SAME_VOCAB_CAUSAL_KD_V1',vocab_size=vocab_size,
            tokenizer_sha256=student_tokenizer_sha256,teacher_identity_sha256=teacher_identity_sha256,
            coefficient=float(coefficient),temperature=float(temperature),chunk_rows=chunk_rows,
            normalization='VALID_CAUSAL_TARGET_MEAN',combination='CE_PLUS_COEFFICIENT_TIMES_KL',
            visibility='SAME_EXPLICIT_CAUSAL_MASK_ONLY',identity_validation='CALLER_VERIFIES_FROZEN_TEACHER_BEFORE_AFTER')
        self._frozen_teacher()

    def _frozen_teacher(self):
        if self.teacher.training or any(p.requires_grad for p in self.teacher.parameters()):
            raise ValueError('교사는 이미 eval·gradient 동결 상태여야 합니다')

    def bind_student(self,model,vocab_size):
        self._frozen_teacher()
        student=list(model.parameters());teacher=list(self.teacher.parameters())
        if vocab_size!=self.contract['vocab_size'] or not student or not teacher:
            raise ValueError('명시한 같은 어휘의 두 모델이 필요합니다')
        if set(map(id,student))&set(map(id,teacher)):
            raise ValueError('교사와 학생 파라미터가 공유됩니다')
        student_storage={(str(p.device),p.untyped_storage().data_ptr()) for p in student if p.numel()}
        teacher_storage={(str(p.device),p.untyped_storage().data_ptr()) for p in teacher if p.numel()}
        if student_storage&teacher_storage:
            raise ValueError('서로 다른 Parameter가 같은 저장소를 공유합니다')
        if {p.device for p in student}!={p.device for p in teacher} or len({p.device for p in student})!=1:
            raise ValueError('같은 단일 장치의 두 모델만 지원합니다')

    def loss(self,student_logits,batch,ce):
        self._frozen_teacher()
        mask=batch.attention_mask
        if (batch.objective!='CAUSAL' or mask.dtype!=torch.bool or mask.device.type!='cpu'
                or mask.shape!=(batch.inputs.shape[0],1,batch.inputs.shape[1],batch.inputs.shape[1])
                or bool(torch.triu(mask,diagonal=1).any())):
            raise ValueError('교사 KL은 명시 causal 배치에만 적용합니다')
        if (student_logits.shape[:2]!=batch.targets.shape or student_logits.ndim!=3
                or student_logits.shape[-1]!=self.contract['vocab_size'] or ce.ndim!=0):
            raise ValueError('학생 logits·target·CE 형상이 다릅니다')
        valid=batch.targets.reshape(-1)!=-100
        total=int(valid.sum())
        if total<1:raise ValueError('유효한 causal target이 없습니다')
        with torch.no_grad():
            teacher_logits=self.teacher(batch.inputs.to(student_logits.device),
                attention_mask=mask.to(student_logits.device))
        if teacher_logits.shape!=student_logits.shape:
            raise ValueError('교사 logits 형상이 다릅니다')
        student=student_logits.reshape(-1,student_logits.shape[-1])
        teacher=teacher_logits.reshape_as(student)
        kl=student_logits.new_zeros((),dtype=torch.float32)
        size=self.contract['chunk_rows']
        for begin in range(0,len(valid),size):
            chosen_cpu=valid[begin:begin+size]
            count=int(chosen_cpu.sum())
            if count:
                chosen=chosen_cpu.to(student_logits.device)
                piece=_kd_kl(student[begin:begin+size][chosen],teacher[begin:begin+size][chosen],
                    self.contract['temperature'],chunk=0,fp32=True)
                kl=kl+piece*(count/total)
        if not bool(torch.isfinite(kl)) or not bool(torch.isfinite(ce)):
            raise ValueError('CE/KL이 유한하지 않습니다')
        return ce+self.contract['coefficient']*kl,dict(ce=float(ce.detach()),
            kl=float(kl.detach()),coefficient=self.contract['coefficient'],targets=total,teacher_forwards=1)
