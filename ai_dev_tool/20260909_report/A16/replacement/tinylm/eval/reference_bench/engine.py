"""TinyLM transport for reference harnesses; task prompts/scorers live upstream."""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path

from .artifacts import sha256_file, source_tree


class ContextOverflow(ValueError):
    pass


def trim_at_stop(text, stops):
    ends = [text.find(stop) for stop in stops if stop and stop in text]
    return text[:min(ends)] if ends else text


class TinyLMEngine:
    def __init__(self, checkpoint, data="ko-en", device="cpu", dtype="float32",
                 max_length=None, overflow="error", tokenizer=None, seed=99):
        if data == "synthetic":
            raise ValueError("Synthetic tokenizer cannot produce benchmark scores.")
        if overflow not in {"error", "left"}:
            raise ValueError("overflow must be error or left")
        if dtype not in {"float32", "bfloat16"}:
            raise ValueError("dtype must be float32 or bfloat16")
        import torch
        from tinylm.infer.generate import load_model
        from tinylm.data import load_tokenizer, tokenizer_path

        self.torch = torch
        self.device = torch.device(device)
        self.dtype_name = dtype
        self.seed = int(seed)
        torch.manual_seed(self.seed)
        checkpoint = Path(checkpoint).resolve(strict=True)
        self.model, self.cfg, _ = load_model(ckpt_path=str(checkpoint), device=str(self.device))
        # load_model owns anneal/freeze/eval; do not override recursive visit schedules.
        if tokenizer is None:
            tok_path = tokenizer_path(data, self.cfg.vocab_size)
            self.tokenizer = load_tokenizer(data, self.cfg.vocab_size)
        else:
            from tokenizers import Tokenizer
            tok_path = Path(tokenizer).resolve(strict=True)
            self.tokenizer = Tokenizer.from_file(str(tok_path))
        if self.tokenizer.get_vocab_size() != self.cfg.vocab_size:
            raise ValueError("Tokenizer vocabulary size differs from checkpoint cfg.")
        # Prevent a saved tokenizer's truncation/padding from silently changing requests.
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        self.eos_id = self.tokenizer.token_to_id("<eos>")
        if self.eos_id is None:
            raise ValueError("Explicit <eos> is required; no arbitrary newline fallback.")
        self.prefix_id = self.eos_id
        self.max_length = int(self.cfg.max_seq_len if max_length is None else max_length)
        if not 2 <= self.max_length <= self.cfg.max_seq_len:
            raise ValueError("max_length must be within checkpoint max_seq_len; no RoPE extension.")
        self.overflow = overflow
        self.stats = {"likelihood_requests": 0, "generation_requests": 0,
                      "truncated_requests": 0, "removed_context_tokens": 0,
                      "max_input_tokens": 0, "generated_tokens": 0}
        self.identity = {
            "checkpoint": str(checkpoint), "checkpoint_sha256": sha256_file(checkpoint),
            "tokenizer": str(Path(tok_path).resolve()), "tokenizer_sha256": sha256_file(tok_path),
            "config": asdict(self.cfg), "visit_schedule": self.model.visit_schedule(),
            "tinylm_source": source_tree(Path(__file__).resolve().parents[2]),
            "max_length": self.max_length, "overflow": overflow,
            "device": str(self.device), "dtype": dtype, "seed": self.seed,
            "add_special_tokens": False, "empty_context_prefix_id": self.prefix_id,
            "generation_eos_id": self.eos_id,
            "weight_path": "load_model: anneal=1, freeze_quant; latent checkpoint representation",
            "deployment_memory_test": False,
        }

    def autocast(self):
        if self.dtype_name == "bfloat16":
            return self.torch.autocast(self.device.type, dtype=self.torch.bfloat16)
        return nullcontext()

    def encode(self, text):
        return self.tokenizer.encode(text, add_special_tokens=False).ids

    def decode(self, ids):
        return self.tokenizer.decode(list(ids), skip_special_tokens=True)

    def _context(self, context, budget):
        if budget < 1:
            raise ContextOverflow(f"No space for context: budget={budget}.")
        if len(context) <= budget:
            return context
        if self.overflow == "error":
            raise ContextOverflow(
                f"Context {len(context)} > budget {budget}; no rows were silently skipped. "
                "Use overflow=left only for an explicitly truncated protocol.")
        self.stats["truncated_requests"] += 1
        self.stats["removed_context_tokens"] += len(context) - budget
        return context[-budget:]

    def loglikelihood_tokens(self, context, continuation):
        """Sum natural log probability and teacher-forced all-token greedy correctness."""
        t = self.torch
        continuation = list(continuation)
        context = list(context) or [self.prefix_id]
        if not continuation:
            raise ValueError("Empty continuation cannot be scored as a successful answer.")
        if len(continuation) > self.max_length:
            raise ContextOverflow("Continuation itself exceeds the model context window.")
        # The final target is not an input: one additional target token fits.
        context = self._context(context, self.max_length + 1 - len(continuation))
        tokens = context + continuation
        self.stats["likelihood_requests"] += 1
        self.stats["max_input_tokens"] = max(self.stats["max_input_tokens"], len(tokens) - 1)
        x = t.tensor([tokens[:-1]], dtype=t.long, device=self.device)
        with t.inference_mode(), self.autocast():
            logits = self.model(x)[0, -len(continuation):, :]
        # Only answer logits become FP32; avoid allocating FP32 logits for the prompt.
        target = t.tensor(continuation, dtype=t.long, device=self.device)
        total, correct = 0.0, True
        with t.inference_mode():
            for begin in range(0, len(continuation), 128):
                part = logits[begin:begin + 128].float()
                gold = target[begin:begin + 128]
                total -= float(t.nn.functional.cross_entropy(part, gold, reduction="sum"))
                correct = correct and bool(t.equal(part.argmax(-1), gold))
        return total, correct

    def generate(self, prompt, max_new, stops=(), temperature=0.0, top_p=1.0,
                 top_k=0, use_cache=False):
        """No-cache reference by default; cache is an explicit separate numerical arm."""
        t = self.torch
        max_new = int(max_new)
        if not 1 <= max_new < self.max_length:
            raise ContextOverflow("Generation budget must be positive and smaller than max_length.")
        if not 0 <= temperature or not 0 < top_p <= 1 or top_k < 0:
            raise ValueError("Invalid sampling parameters.")
        stops = [stops] if isinstance(stops, str) else list(stops)
        if any(not isinstance(s, str) or not s for s in stops):
            raise ValueError("Stop strings must be nonempty strings.")
        context = self.encode(prompt) or [self.prefix_id]
        # Match the harness convention: reserve the full requested generation budget.
        context = self._context(context, self.max_length - max_new)
        self.stats["generation_requests"] += 1
        self.stats["max_input_tokens"] = max(self.stats["max_input_tokens"], len(context))
        initial_count = len(context)
        generated, past, reason = [], None, "length"
        with t.inference_mode():
            for _ in range(max_new):
                ids = context if not use_cache or past is None else context[-1:]
                x = t.tensor([ids], dtype=t.long, device=self.device)
                with self.autocast():
                    if use_cache:
                        logits, past = self.model(x, past_kv=past, use_cache=True)
                    else:
                        logits = self.model(x)
                scores = logits[0, -1].float()
                if temperature == 0:
                    nxt = int(scores.argmax())
                else:
                    scores = scores / temperature
                    if top_k:
                        cutoff = t.topk(scores, min(int(top_k), scores.numel())).values[-1]
                        scores = scores.masked_fill(scores < cutoff, -t.inf)
                    if top_p < 1:
                        sorted_scores, order = scores.sort(descending=True)
                        remove = sorted_scores.softmax(-1).cumsum(-1) > top_p
                        remove[1:] = remove[:-1].clone()
                        remove[0] = False
                        scores[order[remove]] = -t.inf
                    nxt = int(t.multinomial(scores.softmax(-1), 1))
                generated.append(nxt)
                self.stats["generated_tokens"] += 1
                if nxt == self.eos_id:
                    reason = "eos"
                    break
                context.append(nxt)
                text = self.decode(generated)
                if any(stop in text for stop in stops):
                    reason = "stop_string"
                    break
        text = trim_at_stop(self.decode(generated), stops)
        return {"text": text, "finish_reason": reason, "prompt_tokens": initial_count,
                "completion_tokens": len(generated), "token_ids": generated}
