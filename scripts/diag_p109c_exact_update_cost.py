"""Measure same-math CE retention and logging changes on real P109C update inputs."""

from argparse import ArgumentParser
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from datetime import datetime
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from statistics import median
from time import perf_counter, time
from unittest.mock import patch

import torch
from torch.autograd.function import once_differentiable
from torch.nn import functional as F

from scripts import diag_p109c_v3_rule_flip as reference
from scripts import p109c_supervised_eval_export as export
from scripts import run_p109c_integrated_scratch as integrated
from tinylm.config import TMTConfig
from tinylm.train import recomputed_ce
from tinylm.train.anneal_schedule import lr_factor, quant_anneal_factor, resolve_quant_start
from tinylm.train.muon import Muon, split_params


TAG = "p109c_exact_update_cost_cuda_20261126"
PROFILE = reference.EVIDENCE / f"{TAG}_profile_v3.json"
OUT = reference.EVIDENCE / TAG
ROOT = reference.completed.ROOT
ADDRESSES = (31, 977, 1914, 2631)
CPUS = set(range(8))
END = datetime.fromisoformat("2026-11-26T11:30:00+09:00")
ARMS = ("baseline", "logp", "deferred", "both")
ROWS = 1024


class SavedLogpNLL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, projected, table, targets, rows):
        e = table.to(projected.dtype)
        valid = targets.ne(recomputed_ce.IGNORE_INDEX)
        labels = targets.masked_fill(~valid, 0)
        nll = projected.new_empty((len(labels),), dtype=torch.float32)
        blocks = []
        with torch.autocast(projected.device.type, enabled=False):
            for start in range(0, len(labels), rows):
                part = slice(start, start + rows)
                logp = F.log_softmax(F.linear(projected[part], e), dim=1)
                nll[part] = -logp.gather(1, labels[part, None]).flatten().float()
                blocks.append(logp)
        ctx.save_for_backward(projected, e, labels, valid, *blocks)
        ctx.rows, ctx.table_dtype = rows, table.dtype
        return nll.masked_fill_(~valid, 0)

    @staticmethod
    @once_differentiable
    def backward(ctx, upstream):
        projected, table, labels, valid, *blocks = ctx.saved_tensors
        delta = projected.new_empty((len(labels), len(table)))
        upstream = upstream.to(projected.dtype).masked_fill(~valid, 0)
        with torch.autocast(projected.device.type, enabled=False):
            for start, logp in zip(range(0, len(labels), ctx.rows), blocks, strict=True):
                part = slice(start, start + ctx.rows)
                dlogp = torch.zeros_like(logp)
                dlogp.scatter_(1, labels[part, None], -upstream[part, None])
                block = torch.ops.aten._log_softmax_backward_data.default(dlogp, logp, 1, logp.dtype)
                delta[part].copy_(block.masked_fill_(~valid[part, None], 0))
            dp = delta @ table if ctx.needs_input_grad[0] else None
            de = (delta.T @ projected).to(ctx.table_dtype) if ctx.needs_input_grad[1] else None
        return dp, de, None, None


def input_batches(bundle, slots, address):
    order = bundle.schedule[address]
    raw = iter(bundle.raw_batch(order[order[:, 0] == -1, 1]))
    batches = []
    for lane, index in order:
        if lane == -1:
            wire = next(raw)
            x, y, course = wire[:, :-1], wire[:, 1:], None
        elif lane >= 0:
            x, y, course = integrated.supervised.course_microbatch(bundle, slots, address, lane, index)
        else:
            x, y, course = None, None, None
        batches.append((int(lane), x, y, course))
    return batches


def prepare():
    original, bundle, slots, policy = integrated.prepare("original", "capped", "proportional", 0., True)
    evaluation = reference.checkpoint()
    archived_extension = reference.TRAINING / "extension.json"
    archived_signature = reference.completed.read_json(archived_extension)["signature"]
    current = original["signature"]
    integrated_path = str(Path(integrated.__file__).relative_to(ROOT))
    differences = {path for path in archived_signature["sources"] | current["sources"]
                   if archived_signature["sources"].get(path) != current["sources"].get(path)}
    if (differences != {integrated_path}
            or {key: value for key, value in archived_signature.items() if key != "sources"}
            != {key: value for key, value in current.items() if key != "sources"}):
        raise ValueError("the archived v3 and the current R2 replay do not share the verified input and loss signature")
    _, display = integrated.base.native_commands(bundle, original["tag"], False)
    parent = reference.completed.regular_file(reference.TRAINING / "ckpt" /
                                              integrated.journal.checkpoint_name(display, original["tag"]))
    panels = {}
    for address in ADDRESSES:
        batches = input_batches(bundle, slots, address)
        payload = sha256(bundle.schedule[address].tobytes())
        for _, x, y, _ in batches:
            if x is not None:
                payload.update(x.astype("<i8", copy=False).tobytes())
                payload.update(y.astype("<i8", copy=False).tobytes())
        counts = integrated.curriculum.read_targets(bundle, slots, address)
        weights = policy.weights(address, counts)
        anneal = quant_anneal_factor(address, bundle.steps, "wsd", "linear",
                                    resolve_quant_start(bundle.warmup, bundle.steps), .60)
        multiplier = lr_factor(address, bundle.warmup, bundle.steps, "wsd", .2)
        panels[str(address)] = dict(sha256=payload.hexdigest().upper(), counts=counts, weights=weights,
                                    anneal=anneal, lr_multiplier=multiplier)
    if (panels["31"]["counts"]["raw"] != integrated.prep.ACCUM * integrated.base.MICRO_TOKENS
            or any(panels[str(i)]["counts"]["course_inputs"] <= 0 for i in ADDRESSES[1:])
            or any(panels["1914"]["counts"][key] <= 0 for key in ("empty", "decimals"))):
        raise ValueError("the real raw-only and mixed addresses differ")
    sources = (Path(__file__), Path(recomputed_ce.__file__), Path(integrated.__file__),
               Path(integrated.trainer.__file__), Path(export.__file__))
    profile = dict(tag=TAG, parent=str(parent.relative_to(ROOT)), parent_sha256=reference.file_sha(parent),
                   inference_sha256=reference.CHECKPOINT_SHA256, steps=bundle.steps,
                   manifest_sha256=bundle.digest, integrated_training_signature=archived_signature,
                   replay_signature=current, archived_extension_sha256=reference.file_sha(archived_extension),
                   sources={str(path.relative_to(ROOT)): reference.file_sha(path) for path in sources},
                   addresses=list(ADDRESSES), panels=panels, arms=list(ARMS), rows=ROWS,
                   disposition="private in-memory optimizer steps restored independently from the same v3 training state",
                   cpu_affinity=sorted(CPUS), card_limit_mib=integrated.native.CARD_LIMIT_MIB,
                   speed_gate_pct=2.)
    bundle.unchanged()
    return json.loads(json.dumps(profile)), bundle, slots, parent, evaluation


def clone_scalar_state(value):
    # Noncapturable AdamW performs its step counter update on the CPU in place.
    return dict(value, state={key: {name: item.clone() if torch.is_tensor(item) and item.ndim == 0 else item
                                  for name, item in state.items()} for key, state in value["state"].items()})


def restore(model, state, context, address, panel, horizon):
    model.zero_grad(set_to_none=True)
    model.clear_quant()
    model.load_state_dict(state["model"], strict=True)
    model.set_anneal(panel["anneal"])
    model.training_route = integrated.supervised.routed.route_for(model.cfg, model.owner, "uniform_r2", 1337,
                                                                   address, horizon)
    model.training_forwards = 0
    aux = {id(value) for value in (model.decimal_head.weight, *model.value_link.parameters())}
    matrices, _ = split_params(model)
    matrices = [value for value in matrices if id(value) not in aux]
    ids = {id(value) for value in matrices}
    groups = [dict(group, params=[value for value in group["params"] if id(value) not in ids])
              for group in model.param_groups(1e-3)]
    adam = torch.optim.AdamW([group for group in groups if group["params"]], betas=(.9, .95), eps=1e-8)
    muon = Muon(matrices, lr=.004, scale_mode="rms", weight_decay=0.)
    for optimizer, key in ((adam, "opt"), (muon, "opt_muon")):
        base_rates = [group["lr"] for group in optimizer.param_groups]
        optimizer.load_state_dict(clone_scalar_state(state[key]))
        for group, base_rate in zip(optimizer.param_groups, base_rates, strict=True):
            group["lr"] = base_rate * panel["lr_multiplier"]
    torch.set_rng_state(context["cpu_rng"])
    if next(model.parameters()).is_cuda:
        torch.cuda.set_rng_state(context["cuda_rng"], device="cuda")
    return adam, muon


class Phases:
    def __init__(self):
        self.events = {}
        self.stack = []

    def start(self, name):
        start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
        start.record()
        self.stack.append((name, start, end))

    def end(self):
        name, start, end = self.stack.pop()
        end.record()
        self.events.setdefault(name, []).append((start, end))

    def summary(self):
        if self.stack:
            raise ValueError("an update phase was left open")
        return {name: sum(a.elapsed_time(b) for a, b in events) for name, events in self.events.items()}


def run_update(model, bundle, batches, panel, opts, arm, phases=None):
    counts = panel["counts"]
    scalars = dict(panel["weights"], context_targets=counts["context"], location_targets=counts["locations"],
                   relation_questions=counts["relations"], decimal_targets=counts["decimals"], decimal_correct=0)
    accum = integrated.prep.ACCUM
    adam, muon = opts
    retain = arm in ("logp", "both")
    defer = arm in ("deferred", "both")
    logged, detached = [], []
    old = recomputed_ce._RecomputedNLL
    raw_context = patch.object(recomputed_ce, "_RecomputedNLL", SavedLogpNLL) if retain else nullcontext()
    original_backward = old.backward

    def track_backward(ctx, upstream):
        if lane != -1:
            return original_backward(ctx, upstream)
        phases.start("raw_head_backward_cuda_ms")
        result = original_backward(ctx, upstream)
        phases.end()
        return result

    track = patch.object(old, "backward", staticmethod(track_backward)) if phases is not None else nullcontext()
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    started = perf_counter()
    with track, patch.object(integrated.supervised, "VALUE_WEIGHT", scalars["value_weight"]):
        for lane, x, y, course in batches:
            if phases is not None:
                phases.start("raw_forward_cuda_ms" if lane == -1 else "course_forward_cuda_ms" if lane >= 0 else "empty_cuda_ms")
            with torch.autocast("cuda", dtype=torch.bfloat16):
                if lane == -1:
                    hidden = model(x, return_hidden=True)
                    if phases is not None:
                        phases.end()
                        phases.start("raw_head_forward_cuda_ms")
                    with raw_context:
                        values, _ = recomputed_ce.target_nll(model, hidden, y, rows=ROWS)
                    plain = values.sum()
                    loss = plain * scalars["raw_context_weight"]
                    ce = (plain.detach() / scalars["valid_ce_targets"] + (loss - loss.detach())) * accum
                    del hidden, values, plain
                elif lane >= 0:
                    plain, loss = integrated.supervised.course_objective(model, bundle, x, y, ROWS, course, scalars)
                    ce = (plain.detach() / scalars["valid_ce_targets"] + (loss - loss.detach())) * accum
                    del plain
                else:
                    ce = torch.zeros((), dtype=torch.float32, device="cuda", requires_grad=True)
                loss = ce / accum
            if phases is not None:
                phases.end()
                phases.start("raw_backward_cuda_ms" if lane == -1 else "course_backward_cuda_ms" if lane >= 0 else "empty_cuda_ms")
            loss.backward()
            if phases is not None:
                phases.end()
            if defer:
                detached.extend((loss.detach(), ce.detach()))
            else:
                logged.append((loss.item(), ce.item()))
    if defer:
        copied = torch.stack(detached).cpu().tolist()
        logged = list(zip(copied[::2], copied[1::2], strict=True))
    total, total_ce = 0., 0.
    for loss, ce in logged:
        total += loss
        total_ce += ce / accum
    if phases is not None:
        phases.start("clip_and_optimizer_cuda_ms")
    norm_tensor = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
    if not torch.isfinite(norm_tensor):
        raise ValueError("the native gradient clip produced a nonfinite norm")
    norm = float(norm_tensor)
    adam.step()
    muon.step()
    if phases is not None:
        phases.end()
    torch.cuda.synchronize()
    seconds = perf_counter() - started
    if model.training_forwards != counts["reserved"] - counts["empty"] or len(model.training_route) != 28:
        raise ValueError("the real forward routes differ")
    if scalars.get("bilingual_pairs", 0) != counts["pairs"] or not math.isfinite(total + total_ce + norm):
        raise ValueError("supervision accounting or finite scalar check failed")
    timing = {} if phases is None else phases.summary()
    if phases is not None:
        timing["raw_backward_outside_head_cuda_ms"] = timing["raw_backward_cuda_ms"] - timing["raw_head_backward_cuda_ms"]
    return dict(seconds=seconds, allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                reserved_mib=torch.cuda.max_memory_reserved() / 2**20, ce=total_ce, total=total, grad_norm=norm,
                micro_scalars=[list(row) for row in logged], phase_events=timing)


def check_identity(actual, baseline):
    fields = ("ce", "total", "grad_norm", "micro_scalars", "gradients", "updated", "adam", "muon")
    return [field for field in fields if actual[field] != baseline[field]]


def probe(profile, bundle, slots, parent, evaluation, record, deadline):
    from scripts.diag_p102a_g4_full_delta_train import state_sha

    state = torch.load(parent, map_location="cpu", mmap=True, weights_only=True)
    context = export.check_training_state(state, bundle.steps)
    evaluated = torch.load(evaluation, map_location="cpu", mmap=True, weights_only=True)
    if (context["binding"]["recipe"]["p109c_bilingual_mixed"] != profile["integrated_training_signature"]
            or state_sha(export.evaluation_payload(state)) != state_sha(evaluated)):
        raise ValueError("the verified native state does not export the archived v3 evaluation body")
    del evaluated
    cfg = TMTConfig(**state["cfg"])
    if (cfg.emb_rank, cfg.vocab_size, cfg.max_seq_len) != (256, 32768, 1024) or cfg.grad_checkpoint:
        raise ValueError("the native model geometry differs from the comparison")
    model = integrated.supervised.SupervisedG4(cfg).to("cuda").train()
    paths = (record / "progress.jsonl", record / "updates.jsonl")
    with (paths[0].open("x", encoding="utf-8", buffering=1) as progress,
          paths[1].open("x", encoding="utf-8", buffering=1) as measurements):
        def trial(address, prepared, arm, *, warm=False, phase=False):
            if time() >= deadline:
                raise TimeoutError("the equivalence study reached its approved return time")
            panel = profile["panels"][str(address)]
            print(json.dumps(dict(address=address, arm=arm, started=True)), file=progress)
            opts = restore(model, state, context, address, panel, bundle.steps)
            stats = run_update(model, bundle, prepared, panel, opts, arm, Phases() if phase else None)
            if not warm and not phase:
                stats.update(gradients=state_sha({name: value.grad for name, value in model.named_parameters()}),
                             updated=state_sha(model.state_dict()), adam=state_sha(opts[0].state_dict()),
                             muon=state_sha(opts[1].state_dict()))
            row = dict(address=address, arm=arm, warm=warm, phase=phase, **stats)
            print(json.dumps(row), file=measurements)
            print(json.dumps(dict(address=address, arm=arm, seconds=row["seconds"],
                                  allocated_mib=row["allocated_mib"], completed=True)), file=progress)
            return row

        warm_batches = device_batches(bundle, slots, ADDRESSES[0])
        for arm in ARMS:
            trial(ADDRESSES[0], warm_batches, arm, warm=True)
        del warm_batches
        summaries, phase_rows = {}, {}
        variants = ARMS[1:]
        for index, address in enumerate(ADDRESSES):
            start = index % len(variants)
            order = (*variants[start:], *variants[:start])
            batches = device_batches(bundle, slots, address)
            trial(address, batches, "baseline", warm=True)
            baseline = trial(address, batches, "baseline")
            body = {arm: trial(address, batches, arm) for arm in order}
            again = trial(address, batches, "baseline")
            comparisons = {arm: check_identity(body[arm], baseline) for arm in ARMS[1:]}
            delay = (baseline["seconds"] + again["seconds"]) * .5
            summaries[str(address)] = dict(baseline_repeat_difference=check_identity(again, baseline),
                                            differences=comparisons, baseline_seconds=[baseline["seconds"], again["seconds"]],
                                            changes={arm: dict(seconds=body[arm]["seconds"],
                                                              speedup_pct=(1 - body[arm]["seconds"] / delay) * 100,
                                                              allocated_mib=body[arm]["allocated_mib"],
                                                              allocation_delta_mib=body[arm]["allocated_mib"] - baseline["allocated_mib"])
                                                     for arm in ARMS[1:]})
            if address in (31, 1914):
                phase = trial(address, batches, "baseline", phase=True)
                phase_rows[str(address)] = dict(seconds=phase["seconds"], events=phase["phase_events"])
            del batches
    bundle.unchanged()
    if reference.file_sha(parent) != profile["parent_sha256"]:
        raise ValueError("the read-only training checkpoint changed")
    summary = {arm: dict(exact=all(not row["baseline_repeat_difference"] and not row["differences"][arm]
                                  for row in summaries.values()),
                         median_speedup_pct=median(row["changes"][arm]["speedup_pct"] for row in summaries.values()),
                         slowest_address_speedup_pct=min(row["changes"][arm]["speedup_pct"] for row in summaries.values()))
               for arm in ARMS[1:]}
    integrated.native.publish(record / "report.json", dict(status="PROBE_COMPLETE", profile_sha256=reference.file_sha(PROFILE),
                              per_address=summaries, baseline_phase_probes=phase_rows, summary=summary,
                              update_journal_sha256=reference.file_sha(paths[1])))


def device_batches(bundle, slots, address):
    return [(lane, None if x is None else torch.tensor(x, dtype=torch.long, device="cuda"),
             None if y is None else torch.tensor(y, dtype=torch.long, device="cuda"), course)
            for lane, x, y, course in input_batches(bundle, slots, address)]


def worker(path, digest, _resume, record, deadline):
    with (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        profile, bundle, slots, parent, evaluation = prepare()
        if (profile != json.loads(integrated.native.manifest_bytes(path, digest)) or torch.cuda.device_count() != 1
                or not torch.cuda.is_bf16_supported()):
            raise ValueError("the input or target CUDA configuration differs from the seal")
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        torch.set_float32_matmul_precision("high")
        free, total = torch.cuda.mem_get_info()
        budget = (profile["card_limit_mib"] - 384) * 2**20 - (total - free)
        if not 0 < budget <= total:
            raise ValueError("insufficient CUDA allocator headroom")
        torch.cuda.set_per_process_memory_fraction(budget / total)
        torch.manual_seed(1337)
        probe(profile, bundle, slots, parent, evaluation, record, deadline)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "seal":
        if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.profile_sha256 or args.stop_by:
            parser.error("sealing only reads the approved CPU-side assets")
        profile, *_ = prepare()
        integrated.native.publish(PROFILE, profile)
        print(reference.file_sha(PROFILE), flush=True)
        return 0
    if (not args.profile_sha256 or args.stop_by is None or args.stop_by.tzinfo is None
            or not datetime.now().astimezone() < args.stop_by <= END or os.sched_getaffinity(0) != CPUS
            or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"):
        parser.error("use eight reserved logical CPUs and one CUDA device within the short experimental window")
    return integrated.supervisor.supervise(worker, PROFILE, args.profile_sha256, OUT, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
