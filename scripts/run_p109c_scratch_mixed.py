"""Train the sealed P109C v2 mixed corpus with the native G4 optimizer and recovery boundary."""

from __future__ import annotations

import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import datetime
from functools import partial
import json
import math
from pathlib import Path
import shutil
import time
from unittest.mock import patch

import numpy as np
import torch
import torch.nn.functional as F

from scripts import p109_gpu_supervisor as telemetry
from scripts import p109_mix_masked_course as prior
from scripts import p109_train_visit_policy as routed
from scripts import prepare_p109c_v2 as prep
from scripts import run_p109c_scratch330 as native
from scripts.diag_p109b_ste_exact_micro import UpdateQuantizationReuse
from tinylm.train import context_training_state, muon, trainer
from tinylm.train.context_micro_tokens import MicroTokensCursor
from tinylm.train.recomputed_ce import target_nll


TAG = "p109c_scratch_mixed_v2_v11_chat32_s1337"
PROBE_TAG = "p109c_v2_packed_contract_chat32_v1_20261122"
KIND_WEIGHTS = (0.30, 0.60, 0.10)
PACK_SHAPE = (prep.BATCH, 3, prep.WIDTH)
MICRO_TOKENS = prep.BATCH * prep.WIDTH
SAVE_EVERY = 64


def check_relation(array, description):
    for batch, aux in zip(array, description, strict=True):
        x, y = batch[:, 0], batch[:, 1]
        valid = y != prep.IGNORE
        starts = valid.argmax(axis=1)
        answers = [tuple(row[keep]) for row, keep in zip(y, valid, strict=True)]
        if (not 0 <= aux["gold"] < prep.BATCH or aux["decimal"] or not valid.any(axis=1).all()
                or not (starts == starts[0]).all()
                or not np.all(x[:, : starts[0] + 1] == x[0, : starts[0] + 1])
                or len(set(answers)) != prep.BATCH
                or any(len(answer) < 2 or answer[-1] != prep.END or prep.END in answer[:-1] for answer in answers)):
            raise ValueError("every relation batch must compare four distinct answers to one exact prompt")


class Bundle:
    def __init__(self, path, expected):
        self.path = path
        self.digest = native.digest(expected)
        self.manifest = json.loads(native.manifest_bytes(path, expected))
        self.stamps = {path: native.file_stamp(path)}
        if (self.manifest["schema"] != prep.SCHEMA or self.manifest["tokenizer_sha256"] != prep.TOKENIZER_SHA
                or self.manifest["raw_tokens"] != prep.RAW_TOKENS or self.manifest["code_sources"] != prep.source_pins()):
            raise ValueError("the previously verified P109C v2 source and exact compiler are required")
        self.meta = prep.read_json(prep.CACHE / "meta.json")
        self.cache = context_training_state.cache_identity(prep.CACHE)
        if self.cache != self.manifest["cache"] or prep.sha(prep.TOKENIZER) != prep.TOKENIZER_SHA:
            raise ValueError("the admitted raw cache or tokenizer differs")
        for name in native.CACHE_FILES:
            target = prep.CACHE / name
            self.stamps[target] = native.file_stamp(target)
        self.stamps[prep.TOKENIZER] = native.file_stamp(prep.TOKENIZER)
        self.schedule = self.array("schedule.npy", self.manifest["schedule_sha256"])
        self.starts = self.array("raw_starts.npy", self.manifest["raw_starts_sha256"])
        self.steps = self.manifest["steps"]
        self.warmup = self.manifest["warmup"]
        self.raw = np.memmap(prep.CACHE / "train.bin", dtype="<u2", mode="r")
        self.data, self.aux = [], []
        lens = []
        for lane in self.manifest["lanes"]:
            path = self.pin(lane["array"]["file"], lane["array"]["sha256"])
            description = self.pin(lane["metadata"]["file"], lane["metadata"]["sha256"])
            count = lane["micros"]
            width = prep.DTYPE.itemsize * math.prod(PACK_SHAPE)
            if path.stat().st_size != count * width:
                raise ValueError("a sealed curriculum lane has the wrong physical size")
            self.data.append(np.memmap(path, dtype=prep.DTYPE, mode="r", shape=(count, *PACK_SHAPE)))
            with description.open(encoding="utf-8") as file:
                self.aux.append([json.loads(line) for line in file])
            if len(self.aux[-1]) != count:
                raise ValueError("course labels do not cover every declared microbatch")
            if lane["kind"] == "relation":
                check_relation(self.data[-1], self.aux[-1])
            lens.append(count)
        self.validate_order(lens)

    def pin(self, name, expected):
        path = native.bundle_path(self.path.parent, name)
        if prep.sha(path) != native.digest(expected):
            raise ValueError(f"the sealed packed source changed: {name}")
        self.stamps[path] = native.file_stamp(path)
        return path

    def array(self, name, expected):
        return np.load(self.pin(name, expected), mmap_mode="r", allow_pickle=False)

    def validate_order(self, lens):
        schedule = self.schedule
        raw = prep.RAW_TOKENS // MICRO_TOKENS
        physical = self.steps * prep.ACCUM * MICRO_TOKENS
        if (schedule.dtype != np.dtype("<i4") or schedule.shape != (self.steps, prep.ACCUM, 2)
                or schedule[:, :, 0].min() < -2 or schedule[:, :, 0].max() >= len(lens)
                or len(self.raw) != self.meta["train"] or len(self.raw) < 2 * physical
                or self.starts.shape != (raw, prep.BATCH) or self.starts.min() < 0
                or self.starts.max() + prep.WIDTH >= len(self.raw)
                or not (schedule[:self.warmup, :, 0] == -1).all()
                or not np.array_equal(schedule[schedule[:, :, 0] == -1, 1], np.arange(raw))):
            raise ValueError("the raw exposure and packed physical schedule disagree")
        for key, count in enumerate(lens):
            order = schedule[schedule[:, :, 0] == key, 1]
            if not np.array_equal(np.sort(order), np.arange(count)):
                raise ValueError("each admitted packed microbatch must be consumed exactly once")
        lanes = schedule[self.warmup:, :, 0]
        if np.any(~(lanes >= 0).any(axis=1)) or np.any(~(lanes == -1).any(axis=1)):
            raise ValueError("the mixed phase must contain raw and supervised data in every update")

    def unchanged(self):
        if any(native.file_stamp(path) != stamp for path, stamp in self.stamps.items()):
            raise ValueError("a sealed v2 training input changed")

    def prepare(self, name, count, *, exact, doc_filter, doc_min_chars, hf_tok, chat32, existing_only=False):
        if name != "ko-en" or count != self.meta["tokens"] or not exact or doc_filter or hf_tok or not chat32:
            raise ValueError("only the existing exact admitted v1.1 cache can feed this experiment")
        self.unchanged()
        return dict(self.meta, dir=str(prep.CACHE))

    def raw_batch(self, indices):
        return self.raw[self.starts[indices, :, None] + np.arange(prep.WIDTH + 1)].astype(np.int64)


def label_kinds(y, segments):
    """0 means no positive CE, 1 first content, 2 remaining content, 3 EOT."""
    valid = y != prep.IGNORE
    kinds = np.zeros(y.shape, dtype=np.int8)
    kinds[valid] = 2
    kinds[:, 0] = np.where(valid[:, 0], 1, 0)
    first = valid[:, 1:] & (~valid[:, :-1] | (segments[:, 1:] != segments[:, :-1]))
    kinds[:, 1:][first] = 1
    kinds[y == prep.END] = 3
    return kinds


def masked_hidden(model, x, segments, *, flash):
    ss = torch.as_tensor(segments.astype(np.int64), device=x.device)
    compatible = ss[:, :, None].eq(ss[:, None, :])
    allowed = (compatible & torch.ones((x.shape[1], x.shape[1]), dtype=torch.bool, device=x.device).tril()).unsqueeze(1)
    # The existing explicit-visibility route ends at the head. Collect its hidden tensor at that boundary.
    with ExitStack() as stack:
        stack.enter_context(patch.object(model, "_head_logits", lambda hidden: hidden))
        if flash and x.is_cuda:
            from scripts.diag_p107_v11_full_packed_attention import packed_route
            from scripts.diag_p107_v11_packed_optimizer import mask_layout

            offsets, longest, causal = mask_layout(allowed)
            stack.enter_context(patch.object(model.cfg, "sdpa_gqa", True))
            stack.enter_context(patch.object(F, "scaled_dot_product_attention",
                                             packed_route(allowed, offsets, longest, causal)))
        return model(x, attention_mask=allowed, allow_fixed_g4_r2=True)


class MixedG4(prior.DecimalG4):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.mixed_quantization = None

    def refresh_quant(self):
        if not self.training:
            return super().refresh_quant()
        if self.training_route is None:
            raise RuntimeError("the shared weights need one committed training route")
        if self.mixed_quantization is None:
            self.mixed_quantization = UpdateQuantizationReuse(self)
        self.mixed_quantization.refresh()

    def clear_quant(self):
        super().clear_quant()
        self.mixed_quantization = None


def native_commands(bundle, tag, resume):
    with patch.object(native, "STEPS", bundle.steps), patch.object(native, "EVAL_EVERY", SAVE_EVERY):
        args = native.native_args(bundle.meta["tokens"], resume)
    display = f"{math.ceil(bundle.steps * prep.ACCUM * MICRO_TOKENS / 1e6)}M"
    for flag, value in (("--tag", tag), ("--tokens", display)):
        args[args.index(flag) + 1] = value
    return args, display


class ProbeComplete(Exception):
    """The planned short technical updates completed without publishing a training checkpoint."""


def probe_updates(bundle):
    cases = {}
    for index in range(bundle.warmup, bundle.steps):
        for lane, micro in bundle.schedule[index]:
            if lane < 0:
                continue
            aux = bundle.aux[lane][micro]
            if aux["gold"] >= 0:
                cases.setdefault("contrast", index)
            if aux["decimal"]:
                cases.setdefault("decimal", index)
        if len(cases) == 2:
            return tuple(dict.fromkeys((0, bundle.warmup, *cases.values())))
    raise ValueError("a usable integration probe needs both supervised auxiliary paths")


def train_bundle(bundle, record, cutoff, *, flash, sft_share, decimal_weight, resume_from=None, probe=False):
    bind_native = context_training_state.make_binding
    standard_eval = trainer._ce_recomputed
    standard_split = muon.split_params
    signature = dict(manifest_sha256=bundle.digest, source_sha256=prep.sha(Path(__file__)),
                     packed_attention="FLASH" if flash else "MATH", sft_share=sft_share,
                     positive_kind_weights=KIND_WEIGHTS, decimal_weight=decimal_weight,
                     relation_weight=prior.role_loss.WEIGHTS["ALL_AXES"], per_micro_ste=True)
    pending, metrics = {}, []
    current = None
    selected = probe_updates(bundle) if probe else None

    def bind(plan, recipe, cache, device):
        if (plan.steps != bundle.steps or plan.tokens_per_update != prep.ACCUM * MICRO_TOKENS
                or cache != bundle.cache or recipe["ce_recompute_rows"] != 1024
                or recipe.get("ste_update_cache") or recipe.get("packed_document_profile")):
            raise ValueError("the sealed mix needs the unchanged native raw and optimizer setup")
        bundle.unchanged()
        return bind_native(plan, dict(recipe, p109c_mixed_v2=signature), cache, device)

    def split(model):
        matrices, others = standard_split(model)
        head = model.decimal_head.weight
        return [weight for weight in matrices if weight is not head], [*others, head]

    class Cursor(MicroTokensCursor):
        def prepare(self):
            nonlocal current
            if pending or time.time() >= cutoff:
                raise RuntimeError("mixed update was left pending or the authorized window elapsed")
            if probe and self.next_update == len(selected):
                raise ProbeComplete()
            update = super().prepare()
            address = selected[update.update] if probe else update.update
            source = bundle.schedule[address]
            ids = source[source[:, 0] == -1, 1]
            raw = iter(bundle.raw_batch(ids))
            batches = []
            global_counts = np.zeros(4, dtype=np.int64)
            input_tokens = decimal_events = contrasts = 0
            course_weight = sft_share if address >= bundle.warmup else 0.
            for (lane, index), (x_template, y_template) in zip(source, update.batches, strict=True):
                gold, events, segments, kinds, positions = -1, [], None, None, None
                if lane == -1:
                    combined = next(raw)
                    x, y = combined[:, :-1], combined[:, 1:]
                    count = np.asarray([MICRO_TOKENS, 0, 0, 0])
                elif lane == -2:
                    x = np.zeros((prep.BATCH, prep.WIDTH), dtype=np.int16)
                    y = np.full_like(x, prep.IGNORE)
                    count = np.zeros(4, dtype=np.int64)
                else:
                    x, y, segments = bundle.data[lane][index].transpose(1, 0, 2)
                    info = bundle.aux[lane][index]
                    gold, events = info["gold"], info["decimal"]
                    kinds = label_kinds(y, segments)
                    positions = np.flatnonzero(y.ravel() != prep.IGNORE)
                    if any(kinds[row, column] != 1 or label < 1000 for row, column, label in events):
                        raise ValueError("the decimal event must point to its own first answer token")
                    if gold >= 0:
                        kinds[np.arange(prep.BATCH) != gold] = 0
                        contrasts += 1
                    decimal_events += len(events)
                    input_tokens += int(np.count_nonzero(segments))
                    count = np.bincount(kinds.ravel(), minlength=4)
                    count[0] = 0
                global_counts += count
                tx = x_template.new_tensor(x.astype(np.int64))
                ty = y_template.new_tensor(y.astype(np.int64))
                pending[id(ty)] = (int(lane), segments, kinds, positions, gold, events)
                batches.append((tx, ty))
            raw_targets = int(global_counts[0])
            if not raw_targets or (course_weight and sum(global_counts[1:]) == 0):
                raise ValueError("a mixed optimizer update needs raw and positive curriculum targets")
            active = sum(weight for weight, count in zip(KIND_WEIGHTS, global_counts[1:], strict=True) if count)
            weights = [float((1. - course_weight) / raw_targets)]
            weights += [float(course_weight * w / (active * n)) if n else 0.
                        for w, n in zip(KIND_WEIGHTS, global_counts[1:], strict=True)]
            current = dict(source_update=address, ce_weights=weights, raw_targets=raw_targets, course_tokens=input_tokens,
                           answer_start_targets=int(global_counts[1]), answer_body_targets=int(global_counts[2]),
                           answer_eot_targets=int(global_counts[3]), decimal_targets=decimal_events,
                           decimal_correct=0, contrast_questions=contrasts, n_valid=int(global_counts.sum()))
            self._pending = replace(update, batches=tuple(batches))
            return self._pending

        def finish(self, *, optimizer_applied):
            if pending or not optimizer_applied:
                raise RuntimeError("a sealed P109C v2 update was skipped or not fully consumed")
            result = super().finish(optimizer_applied=optimizer_applied)
            row = dict(index=result["update"], **current)
            metrics.append(row)
            update_log.write(json.dumps(row, allow_nan=False) + "\n")
            return result

    def ce(model, x, y, rows):
        if not model.training:
            return standard_eval(model, x, y, rows)
        lane, segments, kinds, positions, gold, events = pending.pop(id(y))
        if lane == -2:
            return model(x, return_hidden=True).sum() * 0.
        if lane == -1:
            nll, _ = target_nll(model, model(x, return_hidden=True), y, rows=rows)
            total = nll.sum()
            objective = total * current["ce_weights"][0]
        else:
            hidden = masked_hidden(model, x, segments, flash=flash)
            coordinates = torch.as_tensor(positions, device=y.device)
            nll, valid = prior.course_target_nll(model, hidden, y, rows * 2, coordinates)
            kind = torch.as_tensor(kinds, device=y.device)
            total = nll.masked_select(kind.ne(0)).sum()
            objective = sum(nll.masked_select(kind.eq(key)).sum() * current["ce_weights"][key]
                            for key in range(1, 4))
            if gold >= 0:
                content = valid & y.ne(prep.END)
                scores = -(nll * content).sum(1) / content.sum(1)
                objective = objective + prior.contrast_row(scores, gold) * (
                    prior.role_loss.WEIGHTS["ALL_AXES"] / current["contrast_questions"])
            if events:
                rows_index, cols = torch.as_tensor([event[:2] for event in events], device=x.device).T
                labels = [event[2] for event in events]
                predictions = hidden[rows_index, cols, None]
                shifted = y[rows_index, cols, None]
                # Each packed event is one independent known first-position predictor.
                aux, count, correct, _ = prior.joint_decimal.objective(
                    model.decimal_head, predictions, shifted, labels, [[0]] * len(events))
                if count != len(events):
                    raise RuntimeError("the existing decimal objective lost an admitted event")
                current["decimal_correct"] += correct
                objective = objective + aux * (decimal_weight / current["decimal_targets"])
        # The native meter reports positive next-token CE. Its backward receives the explicit update-wide objective.
        return (total.detach() / current["n_valid"] + (objective - objective.detach())) * prep.ACCUM

    tag = PROBE_TAG if probe else TAG
    commands, display = native_commands(bundle, tag, resume_from is not None)
    checkpoints, logs = record / "ckpt", record / "native_logs"
    checkpoints.mkdir()
    logs.mkdir()
    checkpoint = checkpoints / f"{native.PRESET}_ko-en_{display}_{tag}.pt"
    if resume_from is not None:
        original, expected_sha = resume_from
        if prep.sha(original) != expected_sha or checkpoint.exists():
            raise ValueError("the original v2 checkpoint differs or the new destination is occupied")
        shutil.copyfile(original, checkpoint)
        if prep.sha(checkpoint) != expected_sha:
            raise ValueError("the owned resume copy differs")
    with (patch.object(native, "STEPS", bundle.steps),
          patch.object(trainer, "prepare", bundle.prepare),
          patch.object(trainer, "LOGS", logs), patch.object(trainer, "CKPT", checkpoints),
          patch.object(routed, "MicroTokensCursor", Cursor),
          patch.object(context_training_state, "make_binding", bind),
          patch.object(muon, "split_params", split),
          patch.object(trainer, "_ce_recomputed", ce),
          (record / "updates.jsonl").open("x", encoding="utf-8", buffering=1) as update_log):
        try:
            result = routed.run_native("uniform_r2", commands, build_model=MixedG4)
        except ProbeComplete:
            if (not probe or len(metrics) != len(selected)
                    or not sum(r["decimal_targets"] for r in metrics)
                    or not sum(r["contrast_questions"] for r in metrics)):
                raise RuntimeError("the technical probe did not apply every planned objective")
            bundle.unchanged()
            native.publish(record / "report.json", dict(status="TECHNICAL_PROBE_COMPLETE", tag=tag,
                input_manifest_sha256=bundle.digest, loss_contract=signature, exposure=metrics,
                evaluated_quality=False, peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20))
            return
        native.export_for_evaluation(checkpoint, record / "evaluation.pt")
    bundle.unchanged()
    if [row["index"] for row in metrics] != [row["index"] for row in result["updates"]]:
        raise RuntimeError("the recorded mixed exposures disagree with applied updates")
    result.update(input_manifest_sha256=bundle.digest, loss_contract=signature, exposure=metrics,
                  peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                  peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                  evaluation_sha256=prep.sha(record / "evaluation.pt"))
    native.publish(record / "training.json", result)
    native.publish(record / "report.json", dict(status="FULL_SCRATCH_MIXED_COMPLETE", tag=tag,
        steps=bundle.steps, input_manifest_sha256=bundle.digest, evaluation_sha256=result["evaluation_sha256"],
        raw_tokens=prep.RAW_TOKENS, course_tokens=bundle.manifest["course_tokens"]))


def export_completed(bundle, original, checksum, record):
    """Recover the evaluation body from a final owned native save without an optimizer update."""
    if prep.sha(original) != checksum or original.is_symlink():
        raise ValueError("the exact owned final checkpoint is required")
    state = torch.load(original, weights_only=True, map_location="cpu", mmap=True)
    context = state[trainer.CONTEXT_STATE_KEY]
    binding = context["binding"]
    context_training_state._validate_binding(binding)
    cursors = context["cursor"]["cursor"]
    contract = binding["recipe"]["p109c_mixed_v2"]
    if (state["step"] != bundle.steps or cursors["optimizer_updates"] != bundle.steps
            or contract["manifest_sha256"] != bundle.digest or binding["cache"] != bundle.cache
            or state["tokenizer_sha256"] != prep.TOKENIZER_SHA
            or context["payload_sha256"] != context_training_state._payload_sha(context)
            or not {"opt", "opt_muon"} <= state.keys()
            or context["control"]["n_skip"] != 0):
        raise ValueError("the completed optimizer, corpus and checkpoint evidence do not agree")
    context_training_state.validate_trainer_control(context["control"], bundle.steps, bundle.steps)
    del state
    record.mkdir(exist_ok=False)
    output = record / "evaluation.pt"
    with patch.object(native, "STEPS", bundle.steps):
        native.export_for_evaluation(original, output)
    if prep.sha(original) != checksum:
        raise ValueError("the completed source checkpoint changed during export")
    native.publish(record / "report.json", dict(status="FULL_UPDATES_EXPORT_RECOVERED", steps=bundle.steps,
        input_manifest_sha256=bundle.digest, checkpoint_sha256=checksum, evaluation_sha256=prep.sha(output),
        additional_optimizer_updates=0))


def worker(flash, course_share, decimal_weight, resume, probe, code_sha, path, expected, _resume, record, cutoff):
    with (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
        if prep.sha(Path(__file__)) != code_sha:
            raise ValueError("the admitted v2 training code changed")
        bundle = Bundle(path, expected)
        if time.time() >= cutoff or torch.cuda.device_count() != 1:
            raise RuntimeError("the authorized single GPU and time window are required")
        free, total = torch.cuda.mem_get_info()
        allowed = (native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
        if not 0 < allowed <= total:
            raise RuntimeError("the approved device envelope has no training capacity")
        torch.cuda.set_per_process_memory_fraction(allowed / total)
        native.publish(record / "input.json", dict(manifest_sha256=bundle.digest, steps=bundle.steps,
            allocator_budget_bytes=allowed, raw_tokens=prep.RAW_TOKENS, course_tokens=bundle.manifest["course_tokens"]))
        train_bundle(bundle, record, cutoff, flash=flash, sft_share=course_share,
                     decimal_weight=decimal_weight, resume_from=resume, probe=probe)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "probe", "run", "export"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--source-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    parser.add_argument("--math-attention", action="store_true")
    parser.add_argument("--course-share", type=float, default=.25)
    parser.add_argument("--decimal-weight", type=float, default=.02)
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--resume-sha256")
    args = parser.parse_args()
    path, expected = args.manifest.absolute(), args.manifest_sha256
    if not 0 < args.course_share < 1 or not 0 < args.decimal_weight <= 1:
        parser.error("the course share or arithmetic auxiliary weight is outside its range")
    if args.mode == "check":
        bundle = Bundle(path, expected)
        print(json.dumps(dict(status="P109C_V2_INPUT_VERIFIED", steps=bundle.steps, tag=TAG,
                              course_tokens=bundle.manifest["course_tokens"], raw_tokens=prep.RAW_TOKENS)))
        return 0
    if args.mode == "export":
        if not args.record or not args.resume_from or not args.resume_sha256:
            parser.error("export requires the owned checkpoint, its checksum and a fresh output path")
        export_completed(Bundle(path, expected), args.resume_from.absolute(),
                         native.digest(args.resume_sha256), args.record.absolute())
        return 0
    if not args.record or not args.stop_by or args.stop_by.tzinfo is None:
        parser.error("execution requires a fresh output path and an authorized deadline with UTC offset")
    if bool(args.resume_from) != bool(args.resume_sha256):
        parser.error("a protected recovery source requires its digest")
    resume = (args.resume_from.absolute(), native.digest(args.resume_sha256)) if args.resume_from else None
    if args.mode == "probe" and resume:
        parser.error("the technical probe starts from its own random initialization")
    code_sha = native.digest(args.source_sha256)
    if code_sha != prep.sha(Path(__file__)):
        parser.error("the admitted v2 training code changed")
    record = args.record.absolute()
    with (patch.object(native, "gpu_worker", partial(worker, not args.math_attention, args.course_share,
                                                    args.decimal_weight, resume, args.mode == "probe", code_sha)),
          patch.object(native, "gpu_status", partial(telemetry.gpu_status, record))):
        return native.supervise(path, expected, bool(resume), record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
