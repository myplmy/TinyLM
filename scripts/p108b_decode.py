"""Diagnostic decoder settings reusing the unchanged product sample loop."""
from dataclasses import dataclass,asdict
from types import FunctionType
import math
import torch
from scripts import interactive_research_infer as manual


@dataclass(frozen=True)
class Decoder:
    name:str
    temperature:float=0.
    top_k:int=1
    repetition_penalty:float=1.

    def __post_init__(self):
        if (not math.isfinite(self.temperature)or self.temperature<0 or type(self.top_k)is not int or self.top_k<0 or
                not math.isfinite(self.repetition_penalty)or not 1.<=self.repetition_penalty<=2.):
            raise ValueError('finite nonnegative temperature/top-k and penalty1..2 required')


def registered():
    return [Decoder('GREEDY'),Decoder('GREEDY_R110',repetition_penalty=1.1),
            Decoder('GREEDY_R120',repetition_penalty=1.2),Decoder('T070_K20',.7,20),
            Decoder('T100_K40',1.,40),Decoder('T070_K20_R110',.7,20,1.1)]


def private_function(original,**replacements):
    if original.__closure__ is not None:raise ValueError('closure-free owner function required')
    result=FunctionType(original.__code__,dict(original.__globals__,**replacements),original.__name__,original.__defaults__)
    result.__kwdefaults__=original.__kwdefaults__
    return result


class GeneratedTokenPenalty:
    """CTRL-style sign-aware penalty, generated reply only; EOS/EOT preserved."""
    def __init__(self,picker,penalty):
        if not math.isfinite(penalty)or not 1<=penalty<=2:raise ValueError('penalty1..2 required')
        self.picker,self.penalty=picker,penalty;self.seen=set();self.calls=0;self.modified_slots=0

    def __call__(self,logits,temperature,top_k):
        if logits.ndim!=2 or logits.shape[0]!=1:raise ValueError('diagnostic requires one reply at a time')
        work=logits
        ids=sorted(self.seen-{2,4})
        if self.penalty!=1 and ids:
            work=logits.clone();index=torch.tensor(ids,device=logits.device,dtype=torch.long)
            selected=work[:,index]
            work[:,index]=torch.where(selected<0,selected*self.penalty,selected/self.penalty)
            self.modified_slots+=len(ids)
        result=self.picker(work,temperature,top_k)
        if result.shape!=(1,1):raise ValueError('one picked token required')
        self.seen.add(int(result.item()));self.calls+=1
        return result


def emit(active,question,decoder,*,seed,max_new=64,history=()):
    """Only picker settings vary; role serialization/KV/EOT/answer owner reused."""
    if type(seed)is not int or seed<0:raise ValueError('explicit nonnegative seed required')
    torch.manual_seed(seed)
    pickers=[]
    def generation_tools(root):
        sample,capture,forward=manual.generation_tools(root)
        original=getattr(sample,'__wrapped__',None)
        if original is None or '_pick'not in original.__globals__:raise ValueError('known canonical sample loop required')
        picker=GeneratedTokenPenalty(original.__globals__['_pick'],decoder.repetition_penalty);pickers.append(picker)
        body=private_function(original,_pick=picker)
        def configured(*args,**kwargs):
            kwargs.update(temperature=decoder.temperature,top_k=decoder.top_k)
            return body(*args,**kwargs)
        return configured,capture,forward
    wrapped=private_function(manual.emit,generation_tools=generation_tools)
    answer,metadata=wrapped(active,question,max_new=max_new,history=history)
    if len(pickers)!=1:raise RuntimeError('one canonical generation loop required')
    metadata.update(temperature=decoder.temperature,top_k=decoder.top_k,
        repetition_penalty=decoder.repetition_penalty,penalty_scope='GENERATED_REPLY_ONLY_EXCLUDING_EOS2_EOT4',
        picker_calls=pickers[0].calls,modified_logit_slots=pickers[0].modified_slots,seed=seed,
        diagnostic_decoder=asdict(decoder),product_sample_loop_unchanged=True)
    return answer,metadata
