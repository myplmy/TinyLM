"""Train the admitted integrated P109C preset from random initialization."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import datetime
from functools import partial
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

import numpy as np
import torch

from scripts import p109_eval_resilient_supervisor as supervisor
from scripts import p109c_native_curriculum as curriculum
from scripts import p109c_supervised_eval_export as exporter
from tinylm import cli
from tinylm.train import context_micro_tokens


supervised, prep, inputs, base = curriculum.supervised, curriculum.prep, curriculum.inputs, curriculum.base
native, trainer, state_tools = supervised.native, supervised.trainer, supervised.state_tools
journal = inputs.training
TAG = "p109c_integrated_scratch_v3_v11_chat32_s1337"
PREFLIGHT = curriculum.AUDIT / "P109C_NATIVE_CURRICULUM_CPU_READBACK_20261124.json"
EXPORT_PROOF = curriculum.AUDIT / "P109C_SUPERVISED_EVAL_EXPORT_CPU_20261124.json"


def prepare(raw_mode, course_mode, value_mode, transfer_weight, skip_empty):
    proof, export = (prep.read_json(path) for path in (PREFLIGHT, EXPORT_PROOF))
    if (proof["status"] != "NATIVE_CURRICULUM_CPU_READBACK_VERIFIED"
            or proof["source_sha256"] != prep.sha(Path(curriculum.__file__))
            or export["status"] != "NATIVE_SUPERVISED_BODY_STRICT_EVAL_LOAD_VERIFIED"
            or export["source_sha256"] != prep.sha(Path(exporter.__file__))
            or type(skip_empty) is not bool or transfer_weight not in (0., .10)):
        raise ValueError("the admitted CPU readback, export route and explicit method choices are required")
    bundle, layout = inputs.load_inputs()
    if layout != proof["layout"]:
        raise ValueError("the assembled curriculum differs from the verified complete layout")
    raw = curriculum.select_raw_windows(bundle, raw_mode)
    if raw not in proof["raw_options"]:
        raise ValueError("the requested raw layout was not read back with this curriculum")
    weights = curriculum.load_loss_schedule(bundle, course_mode, value_mode)
    pins = inputs.sources()
    for path in (Path(__file__), Path(curriculum.__file__), Path(exporter.__file__),
                 Path(supervised.__file__), Path(supervised.terms.__file__), Path(journal.__file__),
                 Path(supervisor.__file__), Path(supervisor.telemetry.__file__), PREFLIGHT, EXPORT_PROOF):
        pins[str(path.resolve().relative_to(prep.ROOT))] = prep.sha(path)
    signature = dict(schema="P109C_INTEGRATED_NATIVE_V1", manifest_sha256=bundle.digest, layout=layout,
                     raw=raw, coefficients=weights.contract, transfer_weight=transfer_weight,
                     skip_empty=skip_empty, sources=pins)
    slots = supervised.terms.BilingualSlots(bundle, layout["layout_sha256"])
    profile = dict(tag=TAG, steps=bundle.steps, signature=signature, totals=proof["totals"])
    return profile, bundle, slots, weights


def tallies(bundle, slots, policy, totals, cutoff):
    rows = []
    for address in range(bundle.steps):
        if time.time() >= cutoff:
            raise TimeoutError("the admitted CPU batch inspection reached the cutoff")
        targets = curriculum.read_targets(bundle, slots, address)
        rows.append((targets, policy.weights(address, targets)))
    if any(sum(row[key] for row, _ in rows) != totals[key]
           for key in ("raw", "context", "locations", "pairs", "relations", "decimals", "course_inputs", "empty", "reserved")):
        raise ValueError("the current batches do not reproduce every admitted full-layout count")
    if [sum(row["answers"][kind] for row, _ in rows) for kind in range(3)] != totals["answers"]:
        raise ValueError("the current batches do not reproduce the admitted answer targets")
    return rows


def train(bundle, slots, profile, policy, record, cutoff, resume):
    signature = profile["signature"]
    tag = profile["tag"]
    visit_trial = signature.get("raw_visit_schedule")
    expected = tallies(bundle, slots, policy, profile["totals"], cutoff)
    if visit_trial is not None:
        boundary = visit_trial["boundary"]
        if (not 0 < boundary < bundle.steps or visit_trial["early_repeat"] not in (1, 2)
                or sum(row["raw"] for row, _ in expected[:boundary]) != visit_trial["prefix_raw_targets"]):
            raise ValueError("the raw visit transition differs from the sealed exposure")
    commands, display = base.native_commands(bundle, tag, resume is not None)
    (record / "ckpt").mkdir()
    (record / "native_logs").mkdir()
    checkpoint = record / "ckpt" / journal.checkpoint_name(display, tag)
    optimizer_rows, prefix_bytes = [], b""
    if resume:
        prefix, optimizer_rows, prefix_bytes = journal.inspect_resume(
            bundle, resume, tag, signature, profile, destination=checkpoint)
        native.publish(record / "resume_prefix.json", prefix)
        for i, row in enumerate(optimizer_rows):
            scalar = expected[i][1]
            if (row["course_share"] != scalar["course_share"] or row["value_weight"] != scalar["value_weight"]
                    or row["answer_weights"] != list(scalar["answer_weights"])):
                raise ValueError("the committed prior updates used a different absolute loss schedule")
    digest = sha256(prefix_bytes)
    pending, counts, stats, model = {}, None, None, None
    single_route, raw_route, raw_forward_visits = None, None, 0
    old_bind, old_save, old_ce = state_tools.make_binding, supervised.saves.save_packed_checkpoint, trainer._ce_recomputed
    old_split, real_aux = base.muon.split_params, supervised.terms.auxiliary

    def build(cfg):
        nonlocal model, single_route
        model = supervised.SupervisedG4(cfg)
        if visit_trial is not None and visit_trial["early_repeat"] == 1:
            single_route = tuple(supervised.routed.cla.schedule(cfg, model.owner, "uniform", 1))
            if len(single_route) != cfg.n_layers:
                raise ValueError("the raw R1 route must visit all physical layers once")
        return model

    def bind(plan, recipe, cache, device):
        if (plan.steps != bundle.steps or cache != bundle.cache or recipe["ce_recompute_rows"] != 1024
                or plan.tokens_per_update != prep.ACCUM * base.MICRO_TOKENS or recipe.get("init_from")
                or recipe.get("ste_update_cache") or recipe.get("packed_document_profile")):
            raise ValueError("the integrated preset must use its sealed unparented native optimizer path")
        bundle.unchanged()
        visit = dict(schema="P109_VISIT_POLICY_NTP_V1", policy="uniform_r2", seed=1337,
                     steps=bundle.steps, eval_route="uniform_r2", sources=supervised.routed.source_pins())
        if visit_trial is not None:
            visit["raw_visit_schedule"] = visit_trial
        fields = {"p109c_bilingual_mixed": signature, supervised.routed.RECIPE_KEY: visit}
        return old_bind(plan, dict(recipe, **fields), cache, device)

    def split(owner):
        matrices, others = old_split(owner)
        auxiliary = [owner.decimal_head.weight, *owner.value_link.parameters()]
        ids = {id(weight) for weight in auxiliary}
        return [weight for weight in matrices if id(weight) not in ids], [*others, *auxiliary]

    class Cursor(context_micro_tokens.MicroTokensCursor):
        def prepare(self):
            nonlocal counts, stats, raw_route, raw_forward_visits
            if pending or model.training_route is not None or time.time() >= cutoff:
                raise RuntimeError("incomplete prior batch or ended authorization")
            update = super().prepare()
            index = update.update
            counts, scalar = expected[index]
            schedule = bundle.schedule[index]
            raw = iter(bundle.raw_batch(schedule[schedule[:, 0] == -1, 1]))
            batches = []
            for (lane, slot), (x, y) in zip(schedule, update.batches, strict=True):
                course = None
                if lane == -1:
                    tokens = next(raw)
                    x, y = x.new_tensor(tokens[:, :-1]), y.new_tensor(tokens[:, 1:])
                elif lane >= 0:
                    a, b, course = supervised.course_microbatch(bundle, slots, index, lane, slot)
                    x, y = x.new_tensor(a.astype(np.int64)), y.new_tensor(b.astype(np.int64))
                pending[id(y)] = (int(lane), course)
                batches.append((x, y))
            stats = dict(scalar, context_targets=counts["context"], location_targets=counts["locations"],
                         relation_questions=counts["relations"], decimal_targets=counts["decimals"], decimal_correct=0)
            model.training_route = supervised.routed.route_for(model.cfg, model.owner, "uniform_r2", 1337, index, bundle.steps)
            model.training_forwards = 0
            raw_route = single_route if visit_trial is not None and index < visit_trial["boundary"] else None
            raw_forward_visits = 0
            self._pending = replace(update, batches=tuple(batches))
            return self._pending

        def finish(self, *, optimizer_applied):
            forwards = counts["reserved"] - (counts["empty"] if signature["skip_empty"] else 0)
            if (pending or not optimizer_applied or model.training_forwards != forwards
                    or stats.get("bilingual_pairs", 0) != counts["pairs"]):
                raise RuntimeError("the actual ordered forwards or supervised pairs differ from the admitted update")
            result = super().finish(optimizer_applied=True)
            index = result["update"]
            if index != len(optimizer_rows):
                raise ValueError("the native cursor diverged from the absolute exposure journal")
            visits = len(model.training_route)
            model.training_route = None
            start, body, eos = counts["answers"]
            row = dict(stats, index=index, source_update=index, optimizer_applied=True,
                       raw_targets=counts["raw"], course_tokens=counts["course_inputs"],
                       answer_start_targets=start, answer_body_targets=body, answer_eot_targets=eos,
                       contrast_questions=counts["relations"], empty_batches=counts["empty"],
                       reserved_batches=counts["reserved"], actual_forwards=forwards, route_visits=visits,
                       forward_layer_slots=forwards * base.MICRO_TOKENS * visits)
            if visit_trial is not None:
                raw_batches = counts["raw"] // base.MICRO_TOKENS
                raw_visits = len(raw_route) if raw_route is not None else visits
                if visits != 28 or raw_forward_visits != raw_batches * raw_visits:
                    raise ValueError("the actual raw and course visits diverged")
                raw_slots = raw_forward_visits * base.MICRO_TOKENS
                course_slots = (forwards - raw_batches) * visits * base.MICRO_TOKENS
                row.update(raw_route_visits=raw_visits, course_route_visits=visits,
                           raw_forward_layer_slots=raw_slots, course_forward_layer_slots=course_slots,
                           forward_layer_slots=raw_slots + course_slots)
            raw = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode()
            updates.write(raw)
            digest.update(raw)
            optimizer_rows.append(row)
            print(json.dumps(dict(completed_updates=index + 1)), file=progress, flush=True)
            return result

    def ce(owner, x, y, rows):
        nonlocal raw_forward_visits
        if not owner.training:
            return old_ce(owner, x, y, rows)
        lane, batch = pending.pop(id(y))
        if lane == -2:
            if signature["skip_empty"]:
                return torch.zeros((), dtype=torch.float32, device=x.device, requires_grad=True)
            return owner(x, return_hidden=True).sum() * 0.
        if lane == -1:
            if raw_route is None:
                hidden = owner(x, return_hidden=True)
                if visit_trial is not None:
                    raw_forward_visits += len(owner.training_route)
            else:
                full_route = owner.training_route
                owner.training_route = raw_route
                try:
                    hidden = owner(x, return_hidden=True)
                    raw_forward_visits += len(owner.training_route)
                finally:
                    owner.training_route = full_route
            values, _ = base.target_nll(owner, hidden, y, rows=rows)
            plain = values.sum()
            loss = plain * stats["raw_context_weight"]
        else:
            with patch.object(supervised, "VALUE_WEIGHT", stats["value_weight"]):
                plain, loss = supervised.course_objective(owner, bundle, x, y, rows, batch, stats)
        return (plain.detach() / stats["valid_ce_targets"] + (loss - loss.detach())) * prep.ACCUM

    def auxiliary(owner, hidden, target, transfer_weight):
        if transfer_weight != 0.:
            raise ValueError("only the sealed transfer coefficient may change")
        return real_aux(owner, hidden, target, transfer_weight=signature["transfer_weight"])

    def save(path, state):
        if state["step"] != len(optimizer_rows):
            raise ValueError("native checkpoint update differs from committed exposure")
        updates.flush()
        os.fsync(updates.fileno())
        state[journal.EXPOSURE_KEY] = journal.exposure_seal(state["step"], digest)
        old_save(path, state)

    with ((record / "updates.jsonl").open("xb", buffering=0) as updates,
          (record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress,
          patch.object(sys, "argv", ["tinylm", *commands]), patch.object(trainer, "prepare", bundle.prepare),
          patch.object(trainer, "CKPT", checkpoint.parent), patch.object(trainer, "LOGS", record / "native_logs"),
          patch.object(trainer, "TiedMLPTransformer", build), patch.object(trainer, "_ce_recomputed", ce),
          patch.object(context_micro_tokens, "MicroTokensCursor", Cursor),
          patch.object(state_tools, "make_binding", bind), patch.object(base.muon, "split_params", split),
          patch.object(supervised.terms, "auxiliary", auxiliary),
          patch.object(supervised.saves, "save_packed_checkpoint", save)):
        if prefix_bytes:
            updates.write(prefix_bytes)
        print(json.dumps(dict(verified_updates=bundle.steps, completed_updates=len(optimizer_rows))),
              file=progress, flush=True)
        cli.main()
    bundle.unchanged()
    if len(optimizer_rows) != bundle.steps:
        raise ValueError("every native optimizer update must finish before exporting")
    sums = {key: sum(row[key] for row in optimizer_rows) for key in journal.EXPOSURE_TOTALS}
    totals = profile["totals"]
    required = dict(zip(journal.EXPOSURE_TOTALS, (totals["raw"], totals["course_inputs"], totals["relations"],
                                                *totals["answers"]), strict=True))
    if sums != required:
        raise ValueError("the actual exposures did not close at the sealed denominators")
    digest = exporter.export_finished(checkpoint, prep.sha(checkpoint), bundle.steps, record / "evaluation.pt")
    native.publish(record / "training.json", dict(updates=optimizer_rows, input_manifest_sha256=bundle.digest,
                   evaluation_sha256=digest, peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                   peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20, exposure_sums=sums))
    native.publish(record / "report.json", dict(status="FULL_SCRATCH_MIXED_COMPLETE", tag=tag,
                   steps=bundle.steps, input_manifest_sha256=bundle.digest, evaluation_sha256=digest,
                   raw_tokens=totals["raw"], course_tokens=totals["course_inputs"], final_preset=signature))


def worker(resume, path, digest, _resuming, record, cutoff, *, make_profile=prepare):
    with (journal.locked_record(record), (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        sealed = json.loads(native.manifest_bytes(path, digest))
        signature = sealed["signature"]
        pair = signature["coefficients"]
        profile, bundle, slots, policy = make_profile(signature["raw"]["name"], pair["course"], pair["location"],
                                                       signature["transfer_weight"], signature["skip_empty"])
        if (profile != sealed or time.time() >= cutoff
                or torch.cuda.device_count() != 1 or not torch.cuda.is_bf16_supported()):
            raise ValueError("the sealed curriculum and approved CUDA device are required")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        free, total = torch.cuda.mem_get_info()
        budget = (native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
        if not 0 < budget <= total:
            raise ValueError("no usable allocation budget on the approved CUDA device")
        torch.cuda.set_per_process_memory_fraction(budget / total)
        native.publish(record / "extension.json", profile)
        native.publish(record / "input.json", dict(manifest_sha256=bundle.digest, steps=bundle.steps,
                       raw_tokens=profile["totals"]["raw"], course_tokens=profile["totals"]["course_inputs"]))
        train(bundle, slots, profile, policy, record, cutoff, resume)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--raw", choices=curriculum.ORIGINAL_CHOICES)
    parser.add_argument("--course", choices=("fixed", "capped"))
    parser.add_argument("--value", choices=("fixed", "proportional"))
    parser.add_argument("--transfer", type=float, choices=(0., .1))
    parser.add_argument("--padding", choices=("skip", "full"))
    parser.add_argument("--record", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    parser.add_argument("--resume-checkpoint", type=Path)
    parser.add_argument("--resume-sha256")
    args = parser.parse_args()
    if args.mode == "prepare":
        if any(getattr(args, key) is None for key in ("raw", "course", "value", "transfer", "padding")):
            parser.error("declare every selected experiment policy")
        profile, *_ = prepare(args.raw, args.course, args.value, args.transfer, args.padding == "skip")
        native.publish(args.profile, profile)
        print(prep.sha(args.profile), profile["steps"], flush=True)
        return 0
    if (any(getattr(args, key) is not None for key in ("raw", "course", "value", "transfer", "padding"))
            or not args.profile_sha256 or not args.stop_by or not args.stop_by.tzinfo or not args.record
            or args.stop_by > inputs.AUTHORIZATION_END or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"
            or bool(args.resume_checkpoint) != bool(args.resume_sha256)):
        parser.error("use one sealed profile, evidence directory and approved GPU interval")
    record = args.record.absolute()
    if record.parent != prep.EVIDENCE:
        parser.error("a fresh experiment directory under the evidence root is required")
    resume = (args.resume_checkpoint.absolute(), args.resume_sha256.upper()) if args.resume_checkpoint else None
    return supervisor.supervise(partial(worker, resume), args.profile.absolute(), args.profile_sha256,
                                record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
