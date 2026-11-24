"""Opt-in feature-gated replay of an existing edit, never a gold-answer gate."""
from contextlib import contextmanager
import hashlib
import numpy as np
import torch
from torch.nn.attention import sdpa_kernel, SDPBackend

from scripts import p108c_scope as scope
from scripts import p108_wsp_attention as intervention
from scripts import interactive_research_infer as manual


def question_indices(text, question, offsets):
    if not isinstance(question, str) or not question.strip():
        raise ValueError("nonempty current question required")
    start = text.rfind(question)
    if start < 0:
        raise ValueError("serialized current question span is absent")
    end = start + len(question)
    result = [i for i, (a, b) in enumerate(offsets) if a < end and b > start]
    if not result:
        raise ValueError("tokenizer did not expose current-question offsets")
    covered = {p for i in result for p in range(max(start, offsets[i][0]),
                                               min(end, offsets[i][1]))}
    if any(start+i not in covered for i, c in enumerate(question) if not c.isspace()):
        raise ValueError("token offsets do not cover current question characters")
    return result


def capture_features(layers, modules, ids, positions, forward):
    if (set(layers) != set(modules) or not layers or
            len({id(m) for m in modules.values()}) != len(modules) or
            not ids or not positions or min(positions) < 0 or max(positions) >= len(ids)):
        raise ValueError("unique native layers, full input, and valid question positions required")
    saved = {}; handles = []
    def store(index, family, tensor):
        if (index, family) in saved or tensor.ndim != 3 or tensor.shape[:2] != (1, len(ids)):
            raise ValueError("one complete native B1 layer visit required")
        chosen = torch.tensor(positions, device=tensor.device, dtype=torch.long)
        saved[(index, family)] = (tensor[0, -1].detach().float().cpu().numpy().copy(),
            tensor[0].index_select(0, chosen).mean(0).detach().float().cpu().numpy().copy())
    try:
        for index in sorted(layers):
            def down(_module, args, _out, index=index):
                store(index, "key", args[0])
            def residual(_module, _args, out, index=index):
                store(index, "residual", out)
            handles.append(modules[index].register_forward_hook(down))
            handles.append(layers[index].register_forward_hook(residual))
        with torch.no_grad():
            result = forward()
        del result
    finally:
        for handle in reversed(handles):
            handle.remove()
    if len(saved) != 2*len(layers):
        raise RuntimeError("incomplete native layer feature capture")
    return {family+"_"+position:np.stack([saved[(i, family)][column] for i in sorted(layers)])
        for family in ("key", "residual") for column, position in enumerate(("last", "question_mean"))}


class RoutedEdit:
    def __init__(self, active, router, threshold, packet, budget,
                 *, feature_view="key_last", feature_layer=13):
        self.active = active; self.budget = budget; self.router = router
        self.threshold = threshold; self.feature_view = feature_view; self.feature_layer = feature_layer
        self.model = active["model"]
        if (active["route"].mode != "float" or self.model.training or
                self.model.visit_schedule() != list(range(14)) or feature_layer not in range(14) or
                feature_view not in ("key_last", "key_question_mean", "residual_last", "residual_question_mean")):
            raise ValueError("admitted completed float14/R1 feature path required")
        self.modules = {int(key.split(":")[1]):m for key,m in intervention.outputs(self.model).items()
                        if key.startswith("mlp:")}
        if sorted(self.modules) != list(range(14)):
            raise ValueError("all14 native down projections required")
        self.original = self.modules[13].weight.detach().cpu().clone()
        self.requested = torch.as_tensor(packet["requested"]).float().cpu().clone()
        self.after = torch.as_tensor(packet["after"]).float().cpu().clone()
        if not torch.equal(self.original + self.requested, self.after):
            raise ValueError("same original plus stored requested delta must reproduce after bits")
        self.delta_gpu = self.requested.to(self.modules[13].weight)
        self.counts = dict(original_prefills=0, generated_replies=0, branch_on=0, branch_off=0)

    def prompt(self, question, history, max_new):
        from tinylm.chat.serialize import serialize
        messages = manual.prompt_messages(question, history)
        text = serialize(dict(messages=messages), "chatml", add_generation_prompt=True)
        encoding = self.active["tokenizer"].encode(text)
        ids = list(encoding.ids)
        if type(max_new) is not int or max_new < 1 or len(ids)+max_new > self.active["cfg"].max_seq_len:
            raise ValueError("explicit context and output limit required; no truncation")
        positions = question_indices(text, question, encoding.offsets)
        return text, ids, positions

    def capture(self, question, *, history=(), max_new=64):
        self.budget.check(); self.active["route"].assert_active()
        text, ids, positions = self.prompt(question, history, max_new)
        model = self.model
        def forward():
            return model(torch.tensor([ids], device=self.delta_gpu.device), logits_last_only=True)
        with sdpa_kernel(SDPBackend.MATH):
            features = capture_features(dict(enumerate(model.layers)), self.modules, ids, positions, forward)
        self.counts["original_prefills"] += 1
        self.active["route"].assert_active()
        return dict(features=features, ids=ids,
                    prompt_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest().upper(),
                    question_positions=positions, current_question=question, history=list(history))

    def decide(self, observation):
        x = observation["features"][self.feature_view][self.feature_layer][None]
        score = float(scope.score(self.router, x)[0])
        return bool(score >= self.threshold), score

    @contextmanager
    def branch(self, enabled):
        self.budget.check()
        if type(enabled) is not bool:
            raise ValueError("one input-only frozen boolean branch decision required")
        if enabled:
            with intervention.edit(self.model, self.active["route"], [("mlp:13", self.delta_gpu)]) as receipt:
                if not torch.equal(self.modules[13].weight.detach().cpu(), self.after):
                    raise RuntimeError("native branch differs from closed edited matrix")
                yield receipt
        else:
            if not torch.equal(self.modules[13].weight.detach().cpu(), self.original):
                raise RuntimeError("OFF branch is not the original matrix")
            yield []
        if not torch.equal(self.modules[13].weight.detach().cpu(), self.original):
            raise RuntimeError("branch did not restore original matrix")

    def emit(self, question, *, history=(), max_new=64, observation=None, forced=None):
        observation = (self.capture(question, history=history, max_new=max_new)
                       if observation is None else observation)
        text, ids, _ = self.prompt(question, history, max_new)
        if (observation["ids"] != ids or observation["prompt_sha256"] !=
                hashlib.sha256(text.encode("utf-8")).hexdigest().upper()):
            raise ValueError("cached original feature belongs to another actual prompt/history")
        enabled, score = self.decide(observation)
        if forced is not None:
            if type(forced) is not bool:
                raise ValueError("diagnostic forced branch must be explicit boolean")
            enabled = forced
        with self.branch(enabled):
            answer, generated = manual.emit(self.active, question, max_new=max_new, history=history)
        self.counts["generated_replies"] += 1
        self.counts["branch_on" if enabled else "branch_off"] += 1
        return answer, generated, dict(enabled=enabled, score=score, threshold=self.threshold,
            forced_diagnostic=forced is not None, feature_view=self.feature_view,
            feature_layer=self.feature_layer, original_prompt_sha256=observation["prompt_sha256"],
            branch_fixed_for_entire_reply=True, question_feature_from_original=True)

    def close(self):
        self.modules.clear()
        self.active = self.model = self.router = self.original = self.requested = self.after = self.delta_gpu = None
