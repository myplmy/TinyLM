"""Delegate the original hybrid canary to a fixed body without mutating its LM."""
from types import SimpleNamespace
from scripts import p106b_qwen35_fixedshape as fixed


class FixedForwardView:
    def __init__(self,body,*,width,pad_id,check,stats):
        self._body=body;self.config=body.config
        self.width=width;self.pad_id=pad_id;self.check=check;self.stats=stats

    def __call__(self,*,input_ids,use_cache=False,past_key_values=None,logits_to_keep=0):
        if use_cache is not False or past_key_values is not None or logits_to_keep!=0:
            raise ValueError('original stateless full-head call contract required')
        value=fixed.logits(self._body,input_ids,width=self.width,pad_id=self.pad_id,
            vocab=self.config.vocab_size,check=self.check,stats=self.stats)
        return SimpleNamespace(logits=value,past_key_values=None)


class LegacyLMView:
    def __init__(self,lm,*,width=1024,pad_id=248044,check=lambda:None,stats=None):
        self._lm=lm
        self.model=FixedForwardView(lm.model,width=width,pad_id=pad_id,check=check,stats=stats)

    def __getattr__(self,name):
        return getattr(self._lm,name)


def exact_legacy_canary(lm,torch,*,width=1024,pad_id=248044,check=lambda:None):
    from scripts import diag_p106b_qwen35_text_core6 as q
    direct_stats={};adapter_stats={};original_body=lm.model
    with fixed.fixed_calls(lm,width=width,pad_id=pad_id,check=check,stats=adapter_stats):
        view=LegacyLMView(lm,width=width,pad_id=pad_id,check=check,stats=direct_stats)
        result=q.hybrid_canary(view,torch,check=check)
    if lm.model is not original_body:
        raise RuntimeError('original model reference changed')
    return dict(original_function=q.hybrid_canary.__module__+'.'+q.hybrid_canary.__name__,
        original_bytecode_unchanged=True,legacy_result=result,
        direct_body_stats=direct_stats,likelihood_adapter_stats=adapter_stats,
        actual_body_width=width,original_model_reference_unchanged=True,quality_claim=False)
