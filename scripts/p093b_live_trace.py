"""Read-only native-sample observer; no model/private IO or quality gates."""
from __future__ import annotations
from contextlib import contextmanager
import math
import torch

VERSION = "P093B_LIVE_TRACE_V1"


def pair_change(a, b):
    a, b = a.detach().float().cpu(), b.detach().float().cpu()
    if a.shape != b.shape or not torch.isfinite(a).all() or not torch.isfinite(b).all():
        raise ValueError("aligned finite vectors required")
    delta = a - b
    den = float(b.square().mean().sqrt())
    norm_a, norm_b = float(a.norm()), float(b.norm())
    cosine = float(torch.dot(a.flatten(), b.flatten()) / (norm_a * norm_b)) if norm_a > 1e-12 and norm_b > 1e-12 else None
    return {"max_abs": float(delta.abs().max()),
            "rms": float(delta.square().mean().sqrt()),
            "relative_rms": float(delta.square().mean().sqrt()) / max(den, 1e-12),
            "cosine": cosine}


def loop_candidate(ids, max_period=24):
    """Operational exact-token loop only; never a semantic rejection."""
    for period in range(1, min(max_period, len(ids) // 3) + 1):
        blocks = [ids[-3 * period:-2 * period],
                  ids[-2 * period:-period], ids[-period:]]
        if blocks[0] == blocks[1] == blocks[2]:
            return {"period": period, "first_block_token": len(ids) - 3 * period + 1,
                    "onset_token": len(ids) - 2 * period + 1,
                    "confirmed_at_token": len(ids),
                    "block_ids": list(blocks[0]),
                    "decision": "OBSERVATION_ONLY; legitimate repeats possible"}
    return None


def logits_stats(logits, generated, prompt_ids, eos_id, decode):
    x = logits.detach().float().flatten().cpu()
    if x.numel() < 2 or not torch.isfinite(x).all():
        raise ValueError("finite native logits required")
    probs = torch.softmax(x, -1)
    top = torch.topk(x, min(10, x.numel()))
    nxt = int(torch.argmax(x))
    def mass(ids):
        selected = sorted({int(i) for i in ids if 0 <= int(i) < x.numel()})
        return float(probs[selected].sum()) if selected else 0.
    return {"argmax_id": nxt, "argmax_text": decode([nxt]),
            "top10": [{"id": int(i), "text": decode([int(i)]),
                       "logit": float(v), "probability": float(probs[int(i)])}
                      for i, v in zip(top.indices, top.values)],
            "top1_top2_logit_margin": float(top.values[0] - top.values[1]),
            "entropy_nats": float(-(probs * probs.clamp_min(1e-30).log()).sum()),
            "eos_id": eos_id, "eos_available": 0 <= eos_id < x.numel(),
            "eos_probability": float(probs[eos_id]) if 0 <= eos_id < x.numel() else None,
            "mass_on_prior_generated_token_types": mass(generated),
            "mass_on_prompt_token_types": mass(prompt_ids),
            "argmax_in_prior_generated": nxt in generated,
            "argmax_in_prompt": nxt in prompt_ids}


def kv_stats(current, previous, expected_length):
    if not isinstance(current, dict) or not current:
        raise ValueError("nonempty native owner KV dictionary required")
    rows, nbytes = [], 0
    previous = previous or {}
    for owner, pair in sorted(current.items()):
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ValueError("native KV must have K/V pairs")
        k, v = pair
        if k.ndim != 4 or v.shape != k.shape or k.shape[2] != expected_length:
            raise ValueError("native owner KV shape/length differs")
        if not torch.isfinite(k.float()).all() or not torch.isfinite(v.float()).all():
            raise ValueError("nonfinite KV")
        prefix_ok, differences = None, {}
        last_change = None
        if owner in previous:
            old_k, old_v = previous[owner]
            length = old_k.shape[2]
            if old_v.shape != old_k.shape or length >= expected_length:
                raise ValueError("previous KV length is invalid")
            prefix_ok = bool(torch.equal(k[:, :, :length], old_k)
                             and torch.equal(v[:, :, :length], old_v))
            last_change = {"k": pair_change(k[:, :, -1].flatten(), old_k[:, :, -1].flatten()),
                           "v": pair_change(v[:, :, -1].flatten(), old_v[:, :, -1].flatten())}
            differences = {}
            for label, now, before in (("k", k[:, :, :length], old_k), ("v", v[:, :, :length], old_v)):
                if torch.equal(now, before):
                    differences[label] = {"max_abs": 0., "rms": 0.}
                else:
                    delta = now.float() - before.float()
                    differences[label] = {"max_abs": float(delta.abs().max()),
                                          "rms": float(delta.square().mean().sqrt())}
        total = k.numel() * k.element_size() + v.numel() * v.element_size()
        nbytes += total
        rows.append({"owner": int(owner), "length": int(k.shape[2]),
                     "shape": list(k.shape), "k_dtype": str(k.dtype), "v_dtype": str(v.dtype),
                     "bytes": total, "prefix_unchanged": prefix_ok,
                     "prefix_difference": differences,
                     "last_vs_previous_token": last_change,
                     "last_k_rms": float(k[:, :, -1].float().square().mean().sqrt()),
                     "last_v_rms": float(v[:, :, -1].float().square().mean().sqrt())})
    if previous and set(previous) != set(current):
        raise ValueError("KV owner set changed")
    return {"owners": rows, "total_bytes": nbytes,
            "all_previous_prefixes_unchanged": all(r["prefix_unchanged"] is not False for r in rows)}


class LiveObserver:
    """Observe native greedy sample. Return no hook replacement tensors."""
    def __init__(self, model, tok, prompt_ids, *, subject, ident, emit,
                 max_new=96, shadow=True):
        self.model, self.tok, self.prompt_ids = model, tok, list(prompt_ids)
        self.subject, self.ident, self.emit = subject, ident, emit
        self.max_new, self.shadow = max_new, shadow
        self.generated, self.rows, self.handles = [], [], []
        self.phase = "primary"
        self.frame = None
        self.previous_layers = {}
        self.eos_id = tok.token_to_id("<eos>")
        if self.eos_id is None:
            self.eos_id = -1
        self.events = []
        self._seen_event_keys = set()
        self.owner_set = sorted(set(model.owner)) if hasattr(model, "owner") else None

    def __enter__(self):
        self.handles.append(self.model.register_forward_pre_hook(self._before, with_kwargs=True))
        self.handles.append(self.model.register_forward_hook(self._after, with_kwargs=True))
        for index, layer in enumerate(self.model.layers):
            self.handles.append(layer.register_forward_pre_hook(
                lambda module, args, index=index: self._layer_before(index, args)))
            self.handles.append(layer.ln2.register_forward_pre_hook(
                lambda module, args, index=index: self._after_attention(index, args)))
            self.handles.append(layer.register_forward_hook(
                lambda module, args, out, index=index: self._layer_after(index, out)))
        return self

    def __exit__(self, *_):
        for handle in self.handles:
            handle.remove()
        self.handles = []

    @staticmethod
    def _last(x):
        if isinstance(x, tuple):
            x = x[0]
        return x[0, -1].detach().float().clone()

    def _before(self, module, args, kwargs):
        if self.phase == "shadow":
            return None
        step = len(self.generated) + 1
        if step > self.max_new:
            raise ValueError("native sampling exceeded max_new")
        tokens = args[0]
        prefix = self.prompt_ids + self.generated
        got = tokens[0].detach().cpu().tolist()
        if got != (self.prompt_ids if step == 1 else self.generated[-1:]):
            raise ValueError("native cached sample input differs from recorded prefix")
        if not kwargs.get("use_cache") or not kwargs.get("logits_last_only"):
            raise ValueError("native cached last-logit route required")
        if len(prefix) > self.model.cfg.max_seq_len:
            raise ValueError("no silent context window reset in this gate")
        prior = kwargs.get("past_kv")
        snapshot = {key: (k.detach().clone(), v.detach().clone())
                    for key, (k, v) in (prior or {}).items()}
        self.frame = {"step": step, "prefix": prefix, "previous_kv": snapshot,
                      "layers": {}, "visited": []}

    def _layer_before(self, index, args):
        if self.phase == "primary":
            self.frame["visited"].append(index)
            self.frame["layers"][index] = {"before": self._last(args[0])}

    def _after_attention(self, index, args):
        if self.phase == "primary":
            self.frame["layers"][index]["after_attention"] = self._last(args[0])

    def _layer_after(self, index, out):
        value = self._last(out)
        if self.phase == "shadow":
            self.shadow_layers[index] = value
        else:
            self.frame["layers"][index]["output"] = value

    def _after(self, module, args, kwargs, output):
        if self.phase == "shadow":
            return None
        if not isinstance(output, tuple) or len(output) != 2:
            raise ValueError("native sample did not return logits and KV")
        logits, kv = output
        current = logits[0, -1].detach().float()
        prefix = self.frame["prefix"]
        stats = logits_stats(current, self.generated, self.prompt_ids, self.eos_id, self.tok.decode)
        nxt = stats["argmax_id"]
        if self.frame["visited"] != list(range(len(module.layers))):
            raise ValueError("this diagnostic requires exactly one ordered layer visit")
        kv_info = kv_stats(kv, self.frame["previous_kv"], len(prefix))
        if self.owner_set is not None and [x["owner"] for x in kv_info["owners"]] != self.owner_set:
            raise ValueError("observed KV owner set differs from model ownership")
        comparison = None
        self.shadow_layers = {}
        if self.shadow:
            try:
                self.phase = "shadow"
                full = torch.tensor([prefix], device=args[0].device, dtype=torch.long)
                reference = module(full, use_cache=False, logits_last_only=True)[0, -1].detach().float().cpu()
            finally:
                self.phase = "primary"
            comparison = pair_change(current, reference)
            comparison.update(argmax_match=nxt == int(reference.argmax()),
                              cache_off_argmax_id=int(reference.argmax()),
                              cache_off_eos_probability=float(torch.softmax(reference, -1)[self.eos_id])
                              if 0 <= self.eos_id < reference.numel() else None)
        vector_keys, vectors = [], []
        for index, entry in sorted(self.frame["layers"].items()):
            for name, value in entry.items():
                vector_keys.append(("primary", index, name)); vectors.append(value)
        for index, value in sorted(self.shadow_layers.items()):
            vector_keys.append(("shadow", index, "output")); vectors.append(value)
        coalesced = torch.stack(vectors).cpu()
        for (phase, index, name), value in zip(vector_keys, coalesced):
            if phase == "primary": self.frame["layers"][index][name] = value
            else: self.shadow_layers[index] = value
        layer_rows = []
        for index, entry in sorted(self.frame["layers"].items()):
            before, after, value = (entry[x] for x in ("before", "after_attention", "output"))
            layer_rows.append({"layer": index, "input_rms": float(before.square().mean().sqrt()),
                "output_rms": float(value.square().mean().sqrt()),
                "gated_attention_change": pair_change(after, before),
                "gated_mlp_change": pair_change(value, after),
                "output_vs_previous_token": pair_change(value, self.previous_layers[index])
                if index in self.previous_layers else None,
                "cached_vs_same_prefix_uncached": pair_change(value, self.shadow_layers[index])
                if index in self.shadow_layers else None})
            self.previous_layers[index] = value
        self.generated.append(nxt)
        candidate = loop_candidate(self.generated)
        if candidate:
            key = (candidate["period"], tuple(candidate["block_ids"]))
            if key not in self._seen_event_keys:
                self._seen_event_keys.add(key)
                candidate.update(subject=self.subject, id=self.ident,
                                 block_text=self.tok.decode(candidate["block_ids"]))
                self.events.append(candidate)
        row = {"subject": self.subject, "id": self.ident, "step": self.frame["step"],
               "prefix_token_count": len(prefix), "input_token_id": int(prefix[-1]),
               "next_token_id": nxt, "next_token_text": self.tok.decode([nxt]),
               "selection_scope": "greedy argmax prediction; confirmed by native next-input and completed decoded-ID equality",
               "hidden_position_scope": "last input token BEFORE selecting generated token at this step",
               "logits": stats, "kv": kv_info, "same_prefix_cache_comparison": comparison,
               "layers": layer_rows, "new_loop_candidate": candidate,
               "quality_decision": "NOT_REVIEWED; no rejection/regeneration/training"}
        self.rows.append(row)
        self.emit(row)
        self.frame = None
        return None
