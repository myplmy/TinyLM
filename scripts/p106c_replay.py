#!/usr/bin/env python3
"""P106C user-owned real AdamW/Muon paired-replay research gate.

No model is loaded without --execute. Each phase has immutable outputs and
requires prior observed gates. This is fresh-state adaptation, not historical
pretraining replay. Code-generated gold is confined to a closed-world task.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106c_data as data
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_mixed_scale import digest, safe_repo_path
from scripts.p106b_education_followup import ARMS

BASE = ROOT / "HF/sft_ready/p106c_replay_v1"
MODES = ("prepare", "calibrate", "overfit", "replay", "policy")
CONTEXT, MICRO, ACCUM, MAX_UPDATES = 256, 8, 4, 568


def write_json(path, value):
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path):
    digest(path)
    return json.loads(path.read_text(encoding="utf-8"))


def code_contract():
    return {p: digest(ROOT / p) for p in (
        "scripts/p106c_data.py", "scripts/p106c_replay.py", "tinylm/model/ternary.py",
        "tinylm/train/muon.py", "scripts/p106b_education_followup.py", "tinylm/data/sft.py",
        "scripts/train_sft_p090.py", "scripts/p106b_shards.py", "tinylm/model/transformer.py",
        "tinylm/model/modules.py", "tinylm/config.py", "tinylm/infer/generate.py",
        "tinylm/train/optimizer_audit.py")}


def check(mode, budget):
    if not 1800 <= budget <= 21600:
        raise ValueError("session wall budget must be1800..21600 seconds")
    target = BASE / mode
    safe_repo_path(target)
    if shutil.disk_usage(ROOT).free < 8 * 2**30:
        raise ValueError("need8GiB free for new state/data artifacts; no automatic cleanup")
    if target.exists() or target.is_symlink():
        raise FileExistsError("preserve completed/partial phase; retry requires a new experiment version")
    if mode != "prepare":
        prepared = read_json(BASE / "prepare/report.json")
        if prepared.get("status") != "CPU_DATA_READY" or prepared["code"] != code_contract():
            raise ValueError("current prepared source/code contract is required")
    for previous, status in {"overfit": [("calibrate", "COST_REPLAY_READY")],
                             "replay": [("calibrate", "COST_REPLAY_READY"), ("overfit", "TINY_OVERFIT_PASSED")],
                             "policy": [("calibrate", "COST_REPLAY_READY"), ("overfit", "TINY_OVERFIT_PASSED"),
                                        ("replay", "REPLAY_SIGNAL_PASSED")]}.get(mode, []):
        report = read_json(BASE / previous / "report.json")
        if report.get("status") != status or report["code"] != code_contract() or report["budget_sec"] != budget:
            raise ValueError(f"prerequisite/code/budget not passed: {previous}")
    if mode != "prepare":
        for key, sha in (("parent", "sha"), ("tokenizer", "tok_sha")):
            if digest(ROOT / ARMS["b"][key]) != ARMS["b"][sha]:
                raise ValueError("pinned B parent/tokenizer differs")
    return target


def load_role(role):
    directory = BASE / "prepare"
    manifest = read_json(directory / f"{role}_shards_manifest.json")
    verify(directory, manifest)
    rows = [json.loads(line) for s in manifest["shards"]
            for line in (directory / s["path"]).read_text(encoding="utf-8").splitlines()]
    return rows


def prepare(target, budget):
    from tokenizers import Tokenizer
    from scripts.train_sft_p090 import encode_records
    spec = ARMS["b"]
    if digest(ROOT / spec["tokenizer"]) != spec["tok_sha"]:
        raise ValueError("chat32 tokenizer differs")
    tok = Tokenizer.from_file(str(ROOT / spec["tokenizer"]))
    groups = {name: data.make_role(name) for name in data.ROLES}
    data.validate_roles(groups)
    groups["controls"] = data.positive_controls()
    summaries = {}
    target.mkdir(parents=True, exist_ok=False)
    for role, examples in groups.items():
        encoded = encode_records([data.canonical(r) for r in examples], tok, CONTEXT, 32768)
        writer = ShardWriter(target, role)
        for example in examples:
            writer.append(example)
        spec = writer.close(lineage={"role": role, "gold": "CODE_CONSTRUCTED_CLOSED_WORLD", "code": code_contract()})
        verify(target, spec)
        summaries[role] = {"rows": len(examples), "tokens": sum(len(x) for x, _, _ in encoded),
                           "targets": sum(n for _, _, n in encoded), "sha256": spec["concat_sha256"]}
    tr = encode_records([data.canonical(r) for r in groups["train"]], tok, CONTEXT, 32768)
    rh = encode_records([data.canonical(r) for r in groups["rehearsal"]], tok, CONTEXT, 32768)
    plan = data.policy_plan(tr, rh, range(4), languages=[r["language"] for r in groups["train"]])
    return {"status": "CPU_DATA_READY", "datasets": summaries, "matched_plan_fixture_max_exposures": plan["max_exposures"],
            "micro": MICRO, "accum": ACCUM, "context": CONTEXT,
            "repeat_exception": "32-example memorization <=128 updates only; normal P106B four-epoch contract unchanged",
            "student_training": "NOT_RUN", "sealed_role_usage": "policy endpoints only, not selectors or prompt correction"}


def cpu_tree(value):
    import torch
    if torch.is_tensor(value):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {k: cpu_tree(v) for k, v in value.items()}
    if isinstance(value, list):
        return [cpu_tree(v) for v in value]
    if isinstance(value, tuple):
        return tuple(cpu_tree(v) for v in value)
    return copy.deepcopy(value)


def tree_hash(value):
    import torch
    h = hashlib.sha256()
    def walk(v):
        if torch.is_tensor(v):
            tensor = v.detach().cpu().contiguous()
            h.update(str((tensor.dtype, tuple(tensor.shape))).encode())
            h.update(tensor.reshape(-1).view(torch.uint8).numpy().tobytes())
        elif isinstance(v, dict):
            for k in sorted(v, key=str):
                h.update(repr(k).encode()); walk(v[k])
        elif isinstance(v, (list, tuple)):
            for item in v:
                walk(item)
        else:
            h.update(repr(v).encode())
    walk(value)
    return h.hexdigest().upper()


def ownership(base, optimizers):
    aliases = {}
    for name, parameter in base.named_parameters(remove_duplicate=False):
        aliases.setdefault(id(parameter), []).append(name)
    seen, groups = set(), []
    for opt in optimizers:
        for group in opt.param_groups:
            names = []
            for parameter in group["params"]:
                if id(parameter) in seen or id(parameter) not in aliases:
                    raise ValueError("optimizer ownership is duplicated or unknown")
                seen.add(id(parameter)); names.append(aliases[id(parameter)][0])
            groups.append({"optimizer": type(opt).__name__, "names": names,
                           "lr": group["lr"], "weight_decay": group.get("weight_decay", 0)})
    if seen != set(aliases):
        raise ValueError("some trainable parameters have no optimizer")
    return {"groups": groups, "aliases": sorted(aliases.values())}


def snapshot(base, optimizers):
    import torch
    if getattr(base, "_p102a_quant_update", None) is not None:
        raise ValueError("snapshot requires an update boundary, no active quant graph")
    if hasattr(base, "clear_quant"):
        base.clear_quant()
    if getattr(base, "_arena_v", 0) or getattr(base, "_int8_store", False) or getattr(base, "_lut_store", False):
        raise ValueError("only pinned training representation supported")
    return {"model": cpu_tree(base.state_dict()), "buffers": cpu_tree(dict(base.named_buffers())),
            "optimizers": [cpu_tree(o.state_dict()) for o in optimizers],
            "modes": {n: m.training for n, m in base.named_modules()},
            "rng_cpu": torch.get_rng_state(), "rng_cuda": cpu_tree(torch.cuda.get_rng_state_all()) if torch.cuda.is_initialized() else [],
            "python_rng": random.getstate(), "ownership": ownership(base, optimizers),
            "config": copy.deepcopy(getattr(base, "cfg", None).__dict__) if hasattr(base, "cfg") else None,
            "runtime": {"quant_cache": "CLEARED_REBUILD_EACH_FORWARD", "accumulation_position": 0,
                        "scaler": None, "schedule": "FIXED_LR", "materialized_input_rng": "per-step fixed seeds",
                        "math_backend": math_backend()}}


def math_backend():
    import torch
    return {"float32_matmul_precision": torch.get_float32_matmul_precision(),
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "cuda_tf32": torch.backends.cuda.matmul.allow_tf32,
            "cudnn_tf32": torch.backends.cudnn.allow_tf32,
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "cudnn_deterministic": torch.backends.cudnn.deterministic}


def restore(base, optimizers, state):
    import torch
    if ownership(base, optimizers) != state["ownership"]:
        raise ValueError("physical aliases/optimizer recipe changed")
    if math_backend() != state["runtime"]["math_backend"]:
        raise ValueError("math backend changed; cannot silently replay a different runtime")
    if state["config"] is not None and base.cfg.__dict__ != state["config"]:
        raise ValueError("model configuration changed")
    if hasattr(base, "clear_quant"):
        base.clear_quant()
    base.load_state_dict(state["model"], strict=True)
    buffers = dict(base.named_buffers())
    if set(buffers) != set(state["buffers"]):
        raise ValueError("runtime buffer set changed")
    with torch.no_grad():
        for name, value in state["buffers"].items():
            buffers[name].copy_(value.to(buffers[name].device))
    for opt, saved in zip(optimizers, state["optimizers"]):
        opt.load_state_dict(cpu_tree(saved)); opt.zero_grad(set_to_none=True)
    for name, module in base.named_modules():
        module.training = state["modes"][name]
    torch.set_rng_state(state["rng_cpu"])
    if state["rng_cuda"]:
        torch.cuda.set_rng_state_all(state["rng_cuda"])
    random.setstate(state["python_rng"])


def weighted_ce(logits, targets, weights, denominator):
    import torch
    import torch.nn.functional as F
    if denominator <= 0 or len(weights) != targets.shape[0]:
        raise ValueError("fixed target denominator/row weights invalid")
    losses = F.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), targets.reshape(-1),
                             ignore_index=-100, reduction="none").reshape(targets.shape)
    w = torch.as_tensor(weights, device=logits.device, dtype=losses.dtype)
    return (losses * w[:, None]).sum() / denominator


def loop_observed(tokens):
    for size in range(1, min(8, len(tokens)//3)+1):
        for i in range(len(tokens)-3*size+1):
            if tokens[i:i+size] == tokens[i+size:i+2*size] == tokens[i+2*size:i+3*size]:
                return True
    return False


def paired_interval(left, right, repeats=2000):
    if set(left) != set(right) or not left:
        raise ValueError("paired confidence interval needs identical nonempty question pairs")
    values = [int(right[k])-int(left[k]) for k in sorted(left)]
    rng = random.Random(20261002)
    samples = sorted(sum(rng.choice(values) for _ in values)/len(values) for _ in range(repeats))
    return {"delta": statistics.mean(values), "low": samples[int(.025*repeats)],
            "high": samples[min(repeats-1, math.ceil(.975*repeats)-1)], "pairs": len(values),
            "unit": "question pair; does not include training-seed uncertainty"}


def parameter_delta(base, plus, zero):
    """Count physical parameters once; selected whole-group quantization is descriptive."""
    import torch
    from tinylm.model.ternary import TLinear, ternary
    latent_square, latent_max, changed = 0.0, 0.0, 0
    for name, parameter in base.named_parameters():
        delta = plus[name].float() - zero[name].float()
        latent_square += float(delta.double().square().sum())
        latent_max = max(latent_max, float(delta.abs().max()))
        changed += int(torch.count_nonzero(delta))
    quant = []
    # Fixed first three physical TLinear modules, not chosen by observed effect.
    for name, module in base.named_modules():
        if not isinstance(module, TLinear):
            continue
        if getattr(module.cfg, "center_weights", False) or module.connectivity_mask is not None or module.use_mode:
            raise ValueError("quant delta requires the pinned uncentered, unmasked, single-mode parent")
        key = name + ".weight"
        if key not in plus:
            continue
        wp, wz = plus[key].float(), zero[key].float()
        qp, qz = ternary(wp, module.cfg), ternary(wz, module.cfg)
        group = module.in_f if not module.cfg.micro_group else module.cfg.micro_group
        ap = qp.abs().reshape(module.out_f, -1, group).amax(dim=-1)
        az = qz.abs().reshape(module.out_f, -1, group).amax(dim=-1)
        quant.append({"module": name, "effective_q_l2": float((qp-qz).double().square().sum().sqrt()),
                      "code_flips": int((qp.sign()!=qz.sign()).sum()), "scale_delta_max": float((ap-az).abs().max())})
        if len(quant) == 3:
            break
    return {"latent_l2": math.sqrt(latent_square), "latent_absmax": latent_max,
            "changed_physical_elements": changed, "fixed_first_three_tlinear_groups": quant,
            "interpretation": "descriptive finite delta, not an additive causal decomposition"}


class Runner:
    def __init__(self):
        import torch
        torch.manual_seed(1337)
        random.seed(1337)
        from scripts.p106b_education_followup import load_student
        from scripts.train_sft_p090 import encode_records
        self.torch, self.model, self.base, self.cfg, self.tok, self.adam, self.muon = load_student("b", training=True)
        self.optimizers = (self.adam, self.muon)
        self.pad = self.tok.token_to_id("<pad>")
        self.end = self.tok.token_to_id("<|im_end|>")
        if self.pad is None or self.end is None:
            raise ValueError("chat32 special-token contract missing")
        self.examples = {r: load_role(r) for r in ("train", "rehearsal", "select", "dev", "retention")}
        self.encoded = {role: encode_records([data.canonical(r) for r in values], self.tok, CONTEXT, 32768)
                        for role, values in self.examples.items()}
        self.s0 = snapshot(self.base, self.optimizers)
        self.s0_sha256 = tree_hash(self.s0)
        self.restore_times, self.step_times = [], []
        self.updates, self.processed_tokens, self.target_tokens = 0, 0, 0

    def native(self):
        from scripts.paired_eval import full_val_losses
        before = time.perf_counter()
        loss, tokens = full_val_losses(self.base, self.cfg, ROOT / ARMS["b"]["cache"], 1024, 4, "cuda")
        if not loss or not all(math.isfinite(v) for v in loss):
            raise ValueError("native validation empty/nonfinite")
        return {"ce": statistics.mean(loss), "tokens": tokens, "crops": len(loss), "wall_sec": time.perf_counter()-before}

    def reset(self):
        t0 = time.perf_counter()
        restore(self.base, self.optimizers, self.s0)
        self.torch.cuda.synchronize()
        self.restore_times.append(time.perf_counter() - t0)

    def step(self, records, weights, seed):
        torch = self.torch
        if len(records) != MICRO * ACCUM or len(weights) != len(records):
            raise ValueError("one update must contain exactly32 materialized rows")
        torch.manual_seed(seed)
        denominator = sum(r[2] for r in records)
        for opt in self.optimizers:
            opt.zero_grad(set_to_none=True)
        self.model.train()
        t0, total = time.perf_counter(), 0.0
        for start in range(0, 32, MICRO):
            micro = records[start:start + MICRO]
            x = torch.tensor([r[0] + [self.pad] * (CONTEXT-len(r[0])) for r in micro], device="cuda")
            y = torch.tensor([r[1] + [-100] * (CONTEXT-len(r[1])) for r in micro], device="cuda")
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logits = self.model(x)
            loss = weighted_ce(logits, y, weights[start:start + MICRO], denominator)
            if not torch.isfinite(loss):
                raise ValueError("nonfinite weighted CE")
            loss.backward(); total += float(loss.detach())
        grad = torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        if not torch.isfinite(grad):
            raise ValueError("nonfinite gradient")
        for opt in self.optimizers:
            opt.step()
        self.torch.cuda.synchronize()
        wall = time.perf_counter()-t0
        self.step_times.append(wall); self.updates += 1
        self.processed_tokens += sum(len(r[0]) for r in records)
        self.target_tokens += denominator
        return {"wall_sec": wall, "loss": total, "grad_norm_preclip": float(grad),
                "fixed_target_denominator": denominator, "weight_sum": sum(weights)}

    def block(self, number, step):
        train = self.encoded["train"][number*32 + step*16:number*32 + (step+1)*16]
        rehearsal = self.encoded["rehearsal"][step*16:(step+1)*16]
        return train + rehearsal

    def scores(self, role):
        from scripts.train_sft_p090 import encode_records
        import torch.nn.functional as F
        torch = self.torch
        rng, cuda = torch.get_rng_state(), torch.cuda.get_rng_state_all()
        self.base.eval(); self.base.freeze_quant()
        t0, cs, zs, es, losses = time.perf_counter(), [], [], [], []
        try:
            with torch.no_grad():
                for row in self.examples[role]:
                    vals = []
                    for j, answer in enumerate([row["gold"], *row["negatives"]]):
                        candidate = dict(row, gold=answer)
                        x, y, _ = encode_records([data.canonical(candidate)], self.tok, CONTEXT, 32768)[0]
                        with torch.autocast("cuda", dtype=torch.bfloat16):
                            logits = self.base(torch.tensor([x], device="cuda"))[0].float()
                        indices = [i for i, target in enumerate(y) if target != -100 and target != self.end]
                        values = [F.log_softmax(logits[i], dim=-1)[y[i]] for i in indices]
                        if not values:
                            raise ValueError("no answer content tokens")
                        vals.append(float(torch.stack(values).mean()))
                        if j == 0:
                            end_index = next(i for i, target in enumerate(y) if target == self.end)
                            end_logits = F.log_softmax(logits[end_index], dim=-1)
                            first_logits = F.log_softmax(logits[indices[0]], dim=-1)
                            zs.append(float(end_logits[self.end] - end_logits[y[indices[0]]]))
                            es.append(float(first_logits[y[indices[0]]] - first_logits[self.end]))
                            labels = torch.tensor(y, device="cuda")
                            losses.append((float(F.cross_entropy(logits, labels, ignore_index=-100, reduction="sum")),
                                           int((labels!=-100).sum())))
                    cs.append(vals[0] - statistics.mean(vals[1:]))
        finally:
            self.base.clear_quant(); self.model.train()
            torch.set_rng_state(rng); torch.cuda.set_rng_state_all(cuda)
        return {"contrast": statistics.mean(cs), "end_margin": statistics.mean(zs),
                "early_end_margin": statistics.mean(es), "nll": sum(v for v,n in losses)/sum(n for v,n in losses),
                "nll_target_tokens": sum(n for v,n in losses),
                "questions": len(cs), "wall_sec": time.perf_counter()-t0}

    def answers(self, examples, directory, stem):
        from tinylm.chat.serialize import serialize
        from tinylm.infer.generate import sample
        from tinylm.chat.canonical import normalize
        writer = ShardWriter(directory, stem)
        passed, stops, pairs, metrics = 0, Counter(), {}, Counter()
        rng, cuda = self.torch.get_rng_state(), self.torch.cuda.get_rng_state_all()
        self.base.eval(); self.base.freeze_quant()
        began = time.perf_counter()
        try:
            for row in examples:
                prompt = serialize(normalize({"messages": [{"role": "user", "content": row["question"]}]}),
                                   "chatml", add_generation_prompt=True)
                decoded, meta = sample(self.base, self.cfg, self.tok, prompt, max_new=32,
                    temperature=0, top_k=1, device="cuda", logits_last_only=True,
                    stop_token_sequences=[[self.end]], return_metadata=True)
                prefix = self.tok.decode(self.tok.encode(prompt).ids)
                if not decoded.startswith(prefix):
                    raise ValueError("generation prefix extraction mismatch")
                answer = decoded[len(prefix):].split("<|im_end|>", 1)[0].strip()
                stopped = meta["finish_reason"] in {"EOS", "STOP_SEQUENCE"}
                ok = answer == row["gold"] and stopped
                loop = loop_observed(self.tok.encode(answer).ids) and not row["repeat_expected"]
                metrics["unwanted_loop"] += loop
                metrics["empty_answer"] += not bool(answer)
                metrics[row["task"]+"_count"] += 1
                metrics[row["task"]+"_pass"] += ok
                passed += ok; stops[meta["finish_reason"]] += 1
                if row.get("pair_id"):
                    pairs.setdefault(row["pair_id"], []).append(ok)
                writer.append({"id": row["id"], "question": row["question"], "gold": row["gold"],
                               "answer": answer, "generation": meta, "exact_and_stopped": ok,
                               "task": row["task"], "repeat_expected": row["repeat_expected"],
                               "loop_observation": loop})
        finally:
            self.base.clear_quant(); self.model.train()
            self.torch.set_rng_state(rng); self.torch.cuda.set_rng_state_all(cuda)
        spec = writer.close(lineage={"examples_sha256": data.data_hash(examples), "assessment": "CODE_GOLD_AND_STOP_ONLY"})
        verify(directory, spec)
        return {"questions": len(examples), "exact_and_stopped": int(passed),
                "pair_count": len(pairs), "pair_pass": sum(len(v)==2 and all(v) for v in pairs.values()),
                "pair_results": {k: len(v)==2 and all(v) for k,v in pairs.items()},
                "observations": dict(metrics),
                "finish_counts": dict(stops), "wall_sec": time.perf_counter()-began,
                "raw_sha256": spec["concat_sha256"]}


def calibrate(runner, target, budget):
    warm = []
    for i in range(20):
        warm.append(runner.step(runner.block(i % 16, i % 2), [1]*32, 20261002+i)["wall_sec"])
    timed = []
    for i in range(16):
        timed.append(runner.step(runner.block(i, 0), [1]*32, 20261042+i)["wall_sec"])
    aa = []
    for pair in range(2):
        hashes, scores = [], []
        for _ in range(2):
            runner.reset()
            runner.step(runner.block(pair, 0), [1]*32, 991+pair)
            state = snapshot(runner.base, runner.optimizers)
            hashes.append(tree_hash({"model": state["model"], "optimizers": state["optimizers"], "buffers": state["buffers"]}))
            scores.append(runner.scores("select"))
        aa.append({"parameter_moment_buffer_hash_equal": hashes[0] == hashes[1],
                   "hashes": hashes, "contrast_delta": scores[0]["contrast"]-scores[1]["contrast"],
                   "score_wall_sec": statistics.mean(s["wall_sec"] for s in scores)})
    runner.reset()
    probe = runner.answers(runner.examples["select"][:8], target, "calibration_answers")
    retention_probe, dev_probe = runner.scores("retention"), runner.scores("dev")
    native = runner.native()
    delta_start = time.perf_counter()
    parameter_delta(runner.base, runner.s0["model"], runner.s0["model"])
    delta_sec = time.perf_counter()-delta_start
    costs = cost_estimate(statistics.median(timed), statistics.median(runner.restore_times),
        statistics.mean(a["score_wall_sec"] for a in aa), retention_probe["wall_sec"], dev_probe["wall_sec"],
        probe["wall_sec"]/8, native["wall_sec"], max(0, sum(warm)-20*statistics.median(timed)), delta_sec)
    predicted = sum(costs.values())
    okay = all(a["parameter_moment_buffer_hash_equal"] for a in aa) and predicted <= budget
    return {"status": "COST_REPLAY_READY" if okay else "CALIBRATION_GATE_NEGATIVE",
            "success_updates": 40, "timed_update_median_sec": statistics.median(timed),
            "restore_median_sec": statistics.median(runner.restore_times), "aa": aa,
            "aa_noise_margin": max(1e-6, 3*max(abs(a["contrast_delta"]) for a in aa)),
            "estimated_total_sec": predicted, "cost_components_sec": costs,
            "estimate_scope": "568 updates,50 restores,role-specific scoring,904 decodes,4 phase compiles,17 CPU deltas; estimate not guarantee",
            "calibration_decode": probe, "native_parent": native,
            "permission": "budget fit is not quality PASS"}


def cost_estimate(step, restore_sec, select_sec, retention_sec, dev_sec, decode_one, native_sec, warm_extra, delta_sec):
    values = (step, restore_sec, select_sec, retention_sec, dev_sec, decode_one, native_sec, warm_extra, delta_sec)
    if not all(math.isfinite(v) and v >= 0 for v in values):
        raise ValueError("nonfinite or negative cost estimate")
    return {"updates": MAX_UPDATES*step, "restores": 50*restore_sec,
            "select_scores": 36*select_sec, "retention_scores": 35*retention_sec,
            "dev_scores": 11*dev_sec, "greedy_answers": 904*decode_one,
            "native_validation": 3*native_sec, "four_compile_warmups": 4*warm_extra,
            "physical_delta_cpu": 17*delta_sec, "loading_io_allowance": 300.0}


def overfit(runner, target, budget):
    runner.reset()
    examples = runner.examples["train"][:32]
    records = runner.encoded["train"][:32]
    observations = []
    for step in range(1, 129):
        runner.step(records, [1]*32, 7000+step)
        if step % 8 == 0:
            assessment = runner.answers(examples, target, f"memorization_{step:03d}")
            observations.append({"step": step, **assessment})
            if assessment["exact_and_stopped"] >= 29:
                return {"status": "TINY_OVERFIT_PASSED", "success_updates": step,
                        "memorization": observations, "generalization": "NOT_TESTED"}
    return {"status": "TINY_OVERFIT_GATE_NEGATIVE", "success_updates": 128,
            "memorization": observations, "generalization": "NOT_TESTED"}


def replay(runner, target, budget):
    calibration = read_json(BASE / "calibrate/report.json")
    points = []
    for block in range(16):
        endpoints, states = [], []
        for weight in (1, 0):
            runner.reset()
            for step in range(2):
                runner.step(runner.block(block, step), [weight]*16+[1]*16, 8000+block*2+step)
            endpoints.append({"score": runner.scores("select"), "retention": runner.scores("retention")})
            states.append(cpu_tree(runner.base.state_dict()))
        plus, zero = endpoints
        delta = plus["score"]["contrast"] - zero["score"]["contrast"]
        retain = plus["retention"]["nll"] - zero["retention"]["nll"]
        early = plus["score"]["early_end_margin"] - zero["score"]["early_end_margin"]
        eligible = delta > calibration["aa_noise_margin"] and retain <= .01 and early >= -.02
        delta_state = parameter_delta(runner.base, states[0], states[1])
        del states
        points.append({"block": block, "plus": plus, "zero": zero, "delta_contrast": delta,
                       "physical_weight_delta": delta_state,
                       "retention_delta": retain, "early_end_delta": early, "eligible": eligible})
        write_json(target/f"block_{block:02d}.json", points[-1])
    ranked = sorted(points, key=lambda p: (-p["delta_contrast"], p["block"]))
    selected = [p["block"] for p in ranked if p["eligible"]][:4]
    candidates = [ranked[0]["block"], ranked[len(ranked)//2]["block"], ranked[-1]["block"]]
    random_block = random.Random(20261002).choice([i for i in range(16) if i not in candidates])
    tails = []
    for block in [*candidates, random_block]:
        endpoints = []
        for weight in (1, 0):
            runner.reset()
            for step in range(2):
                runner.step(runner.block(block, step), [weight]*16+[1]*16, 8000+block*2+step)
            for step in range(8):
                runner.step(runner.block(step, 0), [1]*32, 9000+step)
            endpoints.append(runner.scores("dev"))
        tails.append({"block": block, "plus": endpoints[0], "zero": endpoints[1],
                      "delta_contrast": endpoints[0]["contrast"]-endpoints[1]["contrast"]})
    signal = bool(selected) and tails[0]["delta_contrast"] > calibration["aa_noise_margin"]
    return {"status": "REPLAY_SIGNAL_PASSED" if signal else "REPLAY_GATE_NEGATIVE", "success_updates": 144,
            "points": points, "eligible_blocks": selected, "tails": tails,
            "limit": "local two-step fixed-denominator occurrence suppression; not historical deletion or general intelligence"}


def policies(runner, target, budget):
    prior = read_json(BASE / "replay/report.json")
    plan = data.policy_plan(runner.encoded["train"], runner.encoded["rehearsal"], prior["eligible_blocks"],
                            languages=[r["language"] for r in runner.examples["train"]])
    write_json(target/"batch_plan.json", plan)
    arm_reports = []
    # Sealed content is opened only here, after ranking and policy are frozen.
    sealed, controls = load_role("sealed"), load_role("controls")
    for arm in ("baseline", "selected"):
        runner.reset()
        count, tokens, targets = runner.updates, runner.processed_tokens, runner.target_tokens
        trace = []
        for step, spec in enumerate(plan[arm]):
            records = [runner.encoded["train"][i] for i in spec["candidate"]] + [runner.encoded["rehearsal"][i] for i in spec["rehearsal"]]
            trace.append(runner.step(records, [1]*32, 11000+step))
        assessment = runner.answers(sealed, target, arm+"_sealed")
        extras = runner.answers(controls, target, arm+"_controls")
        native = runner.native()
        arm_reports.append({"arm": arm, "success_updates": runner.updates-count,
                            "processed_tokens": runner.processed_tokens-tokens, "target_tokens": runner.target_tokens-targets,
                            "training": trace, "sealed": assessment, "controls": extras,
                            "retention": runner.scores("retention"), "dev": runner.scores("dev"), "native_after": native})
        state = {"model": cpu_tree(runner.base.state_dict()), "cfg": runner.cfg.__dict__,
                 "sft": {"arm": arm, "updates": 128, "parent_sha256": ARMS["b"]["sha"],
                         "code": code_contract(), "claim_scope": "P106C_CLOSED_WORLD"}}
        # Separate new endpoints for later inspection; no parent or previous output is overwritten.
        with (target/(arm+"_student.pt")).open("xb") as stream:
            runner.torch.save(state, stream)
        write_json(target/(arm+"_report.json"), arm_reports[-1])
    left, right = arm_reports
    if left["processed_tokens"] != right["processed_tokens"] or left["target_tokens"] != right["target_tokens"]:
        raise ValueError("main arm token budgets differ")
    delta = right["sealed"]["pair_pass"]/64-left["sealed"]["pair_pass"]/64
    interval = paired_interval(left["sealed"]["pair_results"], right["sealed"]["pair_results"])
    screens = {"sealed_pair_delta_at_least_10pp": delta >= .10,
               "retention_delta_at_most_0p01": right["retention"]["nll"]-left["retention"]["nll"] <= .01,
               "native_delta_at_most_0p03": right["native_after"]["ce"]-left["native_after"]["ce"] <= .03,
               "no_increase_empty": right["sealed"]["observations"].get("empty_answer", 0) <= left["sealed"]["observations"].get("empty_answer", 0),
               "no_increase_loop": right["sealed"]["observations"].get("unwanted_loop", 0) <= left["sealed"]["observations"].get("unwanted_loop", 0),
               "legitimate_repeat_not_worse": right["controls"]["observations"].get("legitimate_repetition_pass", 0) >= left["controls"]["observations"].get("legitimate_repetition_pass", 0)}
    return {"status": "POLICY_COMPARISON_COMPLETE", "success_updates": 256, "arms": arm_reports,
            "initialization_seeds": 1, "policy_order": ["baseline", "selected"],
            "pair_accuracy_delta": delta, "candidate_signal": all(screens.values()), "preregistered_screens": screens,
            "paired_bootstrap": interval,
            "retention_nll_delta": right["retention"]["nll"]-left["retention"]["nll"],
            "adoption": "NOT_DECIDED_REQUIRES_RAW_ANSWERS_RETENTION_AND_TOTAL_COST_REVIEW",
            "exposure_caps": plan["max_exposures"], "same_total_cost_comparison": "NOT_RUN"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check-only", action="store_true")
    g.add_argument("--execute", action="store_true")
    p.add_argument("--mode", choices=MODES, required=True)
    p.add_argument("--max-wall-sec", type=int, default=14400)
    args = p.parse_args()
    try:
        target = check(args.mode, args.max_wall_sec)
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        print(f"[HOLD] {exc}", file=sys.stderr)
        return 8
    if args.check_only:
        print(json.dumps({"mode": args.mode, "output": str(target.relative_to(ROOT)), "code": code_contract(),
                          "budget_sec": args.max_wall_sec, "micro": MICRO, "accum": ACCUM,
                          "context": CONTEXT, "runtime": "NOT_RUN"}))
        return 0
    began, runner = time.perf_counter(), None
    if args.mode == "prepare":
        report = prepare(target, args.max_wall_sec)
    else:
        from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit, disposition
        spent = sum(read_json(BASE/name/"report.json").get("whole_wall_sec", 0)
                    for name in MODES[1:MODES.index(args.mode)] if (BASE/name/"report.json").exists())
        remaining = args.max_wall_sec - spent
        if remaining < 60:
            print("[HOLD] cumulative session wall budget exhausted")
            return 8
        idle_before_gpu()
        target.mkdir(parents=True, exist_ok=False)
        try:
            with wall_limit(int(remaining)):
                runner = Runner()
                if args.mode != "calibrate" and runner.s0_sha256 != read_json(BASE / "calibrate/report.json")["s0_sha256"]:
                    raise ValueError("fresh S0 differs from calibrated model/optimizer/RNG state")
                report = {"calibrate": calibrate, "overfit": overfit, "replay": replay, "policy": policies}[args.mode](runner, target, args.max_wall_sec)
        except (Exception, KeyboardInterrupt) as exc:
            status, rc = disposition(exc)
            report = {"status": status, "exit_code": rc, "reason": f"{type(exc).__name__}: {exc}",
                      "success_updates": runner.updates if runner else 0}
    report.update(schema="P106C_REPLAY_RESEARCH_V1", mode=args.mode, code=code_contract(),
                  budget_sec=args.max_wall_sec, whole_wall_sec=time.perf_counter()-began,
                  parent_sha256=ARMS["b"]["sha"], tokenizer_sha256=ARMS["b"]["tok_sha"],
                  claim_scope="CLOSED_WORLD_FRESH_STATE_ADAPTATION", teacher_generation=0)
    if runner is not None:
        report.update(actual_success_updates=runner.updates, processed_conversation_tokens=runner.processed_tokens,
                      processed_assistant_targets=runner.target_tokens,
                      peak_allocated_mib=runner.torch.cuda.max_memory_allocated()/2**20,
                      peak_reserved_mib=runner.torch.cuda.max_memory_reserved()/2**20,
                      optimizer_ownership=runner.s0["ownership"], s0_sha256=runner.s0_sha256)
        if args.mode != "calibrate":
            initial = read_json(BASE / "calibrate/report.json")["s0_sha256"]
            if initial != runner.s0_sha256:
                report.update(status="S0_IDENTITY_MISMATCH", exit_code=9)
    okay = report["status"] in {"CPU_DATA_READY", "COST_REPLAY_READY", "TINY_OVERFIT_PASSED", "REPLAY_SIGNAL_PASSED", "POLICY_COMPARISON_COMPLETE"}
    rc = report.setdefault("exit_code", 0 if okay else 8)
    write_json(target/"report.json", report)
    print("[P106C_SUMMARY] " + json.dumps(report, ensure_ascii=False), flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
