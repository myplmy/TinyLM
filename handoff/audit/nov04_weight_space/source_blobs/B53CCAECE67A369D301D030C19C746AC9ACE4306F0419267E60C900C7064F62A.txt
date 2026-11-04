"""Stateful explicit-document sampling; no file reads or inferred boundaries."""
from __future__ import annotations

import hashlib
import json
import torch


class ExplicitDocumentSource:
    def __init__(self, documents, source_ids, *, batch, length, micros, vocab, seed, pad_id=0):
        ints=(batch,length,micros,vocab,seed,pad_id)
        if any(type(x) is not int for x in ints) or min(batch,micros)<1 or length<2:
            raise ValueError('명시한 정수 형상과 seed가 필요합니다')
        if not (vocab>35 and 0<=pad_id<=34 and 0<=seed<2**63):
            raise ValueError('어휘·예약 PAD·seed 범위가 다릅니다')
        if not documents or len(documents)!=len(source_ids):
            raise ValueError('문서와 고유 source_id가 필요합니다')
        if any(not isinstance(x,str) or not x.strip() for x in source_ids) or len(set(source_ids))!=len(source_ids):
            raise ValueError('문서 식별자가 비었거나 중복됩니다')
        digest=hashlib.sha256()
        copied=[]
        for name,document in zip(source_ids,documents):
            if (not isinstance(document,torch.Tensor) or document.device.type!='cpu'
                    or document.dtype!=torch.long or document.ndim!=1 or document.numel()<3
                    or bool((document<0).any()) or bool((document>=vocab).any())
                    or bool((document==13).any())):
                raise ValueError('각 원문은 예약 mask가 없는 CPU int64 문서여야 합니다')
            value=document.detach().clone().contiguous()
            raw=name.encode('utf-8')
            digest.update(len(raw).to_bytes(8,'little'));digest.update(raw)
            digest.update(value.numel().to_bytes(8,'little'));digest.update(value.numpy().tobytes())
            copied.append(value)
        self.documents,self.source_ids=tuple(copied),tuple(source_ids)
        self.batch,self.length,self.micros,self.vocab,self.pad_id=batch,length,micros,vocab,pad_id
        self.corpus_sha256=digest.hexdigest().upper()
        self.contract=dict(schema='P107_EXPLICIT_DOCUMENT_SOURCE_V1',corpus_sha256=self.corpus_sha256,
            batch=batch,length=length,micros=micros,vocab=vocab,seed=seed,pad_id=pad_id,
            sampling='UNIFORM_DOCUMENT_WITH_REPLACEMENT_THEN_UNIFORM_FULL_CROP',documents=len(copied))
        self.signature=hashlib.sha256(json.dumps(self.contract,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()
        self.rng=torch.Generator(device='cpu').manual_seed(seed)
        self.cursor=0

    def next_update(self):
        output=[]
        for _ in range(self.micros):
            tokens=torch.full((self.batch,self.length+1),self.pad_id,dtype=torch.long)
            docs=torch.full_like(tokens,-1)
            for row in range(self.batch):
                index=int(torch.randint(len(self.documents),(1,),generator=self.rng))
                document=self.documents[index]
                start=int(torch.randint(max(1,document.numel()-self.length),(1,),generator=self.rng))
                crop=document[start:start+self.length+1]
                tokens[row,:crop.numel()]=crop
                docs[row,:crop.numel()]=index
            output.append((tokens,docs))
        self.cursor+=1
        return output

    def state_dict(self):
        return dict(schema='P107_EXPLICIT_DOCUMENT_SOURCE_STATE_V1',signature=self.signature,
            cursor=self.cursor,rng=self.rng.get_state().clone())

    def load_state_dict(self,state):
        if (state.get('schema')!='P107_EXPLICIT_DOCUMENT_SOURCE_STATE_V1'
                or state.get('signature')!=self.signature or type(state.get('cursor')) is not int
                or state['cursor']<0):
            raise ValueError('다른 문서·샘플러·cursor 상태입니다')
        probe=torch.Generator(device='cpu')
        probe.set_state(state['rng'])
        self.rng.set_state(probe.get_state())
        self.cursor=state['cursor']
