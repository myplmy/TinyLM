"""lm-evaluation-harness TemplateLM adapter. Task-level scores are never recomputed here."""
from __future__ import annotations

from lm_eval.api.model import TemplateLM
from lm_eval import utils


class TinyLMHarness(TemplateLM):
    backend = "causal"

    def __init__(self, engine, max_gen_toks=256, use_cache=False):
        super().__init__()
        self.engine = engine
        # Upstream loggers expect the HF metadata interface. Model requests still use
        # engine.encode/decode, preserving the native tokenizer and its boundaries.
        from transformers import PreTrainedTokenizerFast
        self.tokenizer = PreTrainedTokenizerFast(
            tokenizer_object=engine.tokenizer, eos_token="<eos>",
            model_max_length=engine.max_length, clean_up_tokenization_spaces=False)
        self._device = engine.device
        self._max_gen_toks = int(max_gen_toks)
        self.use_kv_cache = bool(use_cache)
        self.batch_size = 1
        self.batch_sizes = {}
        self.truncation = engine.overflow
        self.logits_cache = False

    @property
    def eot_token_id(self):
        return self.engine.eos_id

    @property
    def prefix_token_id(self):
        return self.engine.prefix_id

    @property
    def max_length(self):
        return self.engine.max_length

    @property
    def max_gen_toks(self):
        return self._max_gen_toks

    @property
    def tokenizer_name(self):
        return "tinylm-" + self.engine.identity["tokenizer_sha256"]

    def tok_encode(self, string, add_special_tokens=None, **kwargs):
        if add_special_tokens:
            raise ValueError("A16 causal benchmark protocol does not insert special tokens.")
        if kwargs:
            raise ValueError(f"Unsupported tokenization options: {sorted(kwargs)}")
        return self.engine.encode(string)

    def tok_decode(self, tokens, **kwargs):
        if kwargs:
            raise ValueError(f"Unsupported decoding options: {sorted(kwargs)}")
        return self.engine.decode(tokens)

    def _loglikelihood_tokens(self, requests, disable_tqdm=False, **kwargs):
        results = []
        for cache_key, context, continuation in requests:
            result = self.engine.loglikelihood_tokens(context, continuation)
            results.append(result)
            if cache_key is not None:
                self.cache_hook.add_partial("loglikelihood", cache_key, result)
        return results

    def loglikelihood_rolling(self, requests, disable_tqdm=False):
        values = []
        for request in requests:
            (text,) = request.args
            windows = utils.get_rolling_token_windows(
                token_list=self.tok_encode(text), prefix_token=self.prefix_token_id,
                max_seq_len=self.max_length, context_len=1)
            total = 0.0
            for window in windows:
                context, continuation = utils.make_disjoint_window(window)
                total += self.engine.loglikelihood_tokens(context, continuation)[0]
            values.append(total)
            self.cache_hook.add_partial("loglikelihood_rolling", request.args, total)
        return values

    def generate_until(self, requests, disable_tqdm=False):
        outputs = []
        for request in requests:
            prompt, supplied = request.args
            kw = dict(supplied)
            until = kw.pop("until", [])
            max_new = kw.pop("max_gen_toks", kw.pop("max_new_tokens", self.max_gen_toks))
            do_sample = bool(kw.pop("do_sample", False))
            temperature = float(kw.pop("temperature", 0.0))
            top_p = float(kw.pop("top_p", 1.0))
            top_k = int(kw.pop("top_k", 0))
            # Evaluation defaults occasionally serialize these harmless options.
            if kw.pop("num_beams", 1) != 1 or kw.pop("num_return_sequences", 1) != 1:
                raise ValueError("Beam search / multiple sequences not supported by this adapter.")
            if kw:
                raise ValueError(f"Unsupported generation options; not ignored: {sorted(kw)}")
            if not do_sample:
                temperature, top_p, top_k = 0.0, 1.0, 0
            elif temperature <= 0:
                raise ValueError("Sampling requires a positive temperature.")
            result = self.engine.generate(prompt, max_new, until, temperature, top_p,
                                          top_k, use_cache=self.use_kv_cache)
            outputs.append(result["text"])
            self.cache_hook.add_partial("generate_until", request.args, result["text"])
        return outputs

    def apply_chat_template(self, chat_history, add_generation_prompt=True):
        raise ValueError("No inferred chat template. Use the raw benchmark prompt profile.")

    def chat_template(self, chat_template=False):
        if chat_template:
            raise ValueError("A16 TinyLM adapter has no implicit chat template.")
        return None
