"""Native mixed training with a sealed schedule containing grouped relation questions."""

from contextlib import contextmanager
from dataclasses import replace
import fcntl
from hashlib import sha256
import json
import os
import shutil
import time
from unittest.mock import patch

import numpy as np
import torch

from scripts import p109c_packed_relation_objective as relation
from scripts import run_p109c_scratch_mixed as base
from tinylm.train import packed_document_training


prep, native, trainee = base.prep, base.native, base.trainer
EXPOSURE_KEY = "p109c_bilingual_exposure"
EXPOSURE_SCHEMA = "P109C_BILINGUAL_EXPOSURE_V1"
EXPOSURE_TOTALS = ("raw_targets", "course_tokens", "contrast_questions", "answer_start_targets",
                   "answer_body_targets", "answer_eot_targets")


@contextmanager
def locked_record(record):
    if record.resolve(strict=True) != record:
        raise ValueError("the training record directory may not be linked")
    descriptor = os.open(record, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def loss_signature(bundle, pins, layout_sha):
    return dict(manifest_sha256=bundle.digest, layout_sha256=layout_sha, sources=pins, sft_share=.25,
                positive_kind_weights=list(base.KIND_WEIGHTS), decimal_weight=.02,
                relation_weight=base.prior.role_loss.WEIGHTS["ALL_AXES"], per_micro_ste=True)


def checkpoint_name(display, tag):
    return f"{native.PRESET}_ko-en_{display}_{tag}.pt"


def exposure_seal(step, digest):
    return dict(schema=EXPOSURE_SCHEMA, completed_updates=step, sha256=digest.hexdigest().upper())


def inspect_resume(bundle, resume, tag, signature, proof, *, destination=None):
    """Read the exact committed prefix while the source training record is idle."""
    checkpoint, expected = resume
    original = checkpoint.parent.parent
    _, display = base.native_commands(bundle, tag, True)
    if (not original.is_relative_to(prep.EVIDENCE) or checkpoint.parent.name != "ckpt"
            or checkpoint.name != checkpoint_name(display, tag)):
        raise ValueError("resume requires the same bilingual experiment's full checkpoint under evidence")
    extension, journal = original / "extension.json", original / "updates.jsonl"
    with locked_record(original):
        for source in (checkpoint, extension, journal):
            if source.resolve(strict=True) != source or not source.is_file():
                raise ValueError("resume requires original unlinked training files")
        if ((original / "training.json").exists() or (original / "evaluation.pt").exists()
                or prep.read_json(extension) != proof or prep.sha(checkpoint) != expected):
            raise ValueError("resume requires the unchanged, incomplete record using the sealed layout")
        state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
        step = state["step"]
        context = state[trainee.CONTEXT_STATE_KEY]
        binding = context["binding"]
        cursor = context["cursor"]["cursor"]
        state_tools = base.context_training_state
        state_tools._validate_binding(binding)
        state_tools.validate_trainer_control(context["control"], step, cursor["optimizer_updates"])
        state_tools._rng_tensor(context["cpu_rng"])
        state_tools._rng_tensor(context["cuda_rng"])
        if (type(step) is not int or not 0 < step < bundle.steps
                or binding["plan"]["steps"] != bundle.steps or binding["cache"] != bundle.cache
                or binding["recipe"].get("p109c_bilingual_mixed") != signature
                or torch.device(binding["runtime"]["device"]).type != "cuda"
                or context["payload_sha256"] != state_tools._payload_sha(context)
                or cursor["next_update"] != step or cursor["optimizer_updates"] != step
                or cursor["draw_tokens"] != step * prep.ACCUM * base.MICRO_TOKENS
                or context["control"]["n_skip"] or state["ce_recompute_rows"] != 1024
                or state.get("tokenizer_lineage") != "chat32"
                or state.get("tokenizer_sha256") != bundle.meta["tokenizer_sha256"]
                or not state["model"] or not state["opt"]["state"] or not state["opt_muon"]["state"]):
            raise ValueError("resume requires the identical complete model, optimizer, cursor and RNG state")

        rows, raw_prefix, digest = [], bytearray(), sha256()
        with journal.open("rb") as stream:
            for index in range(step):
                raw = stream.readline()
                if not raw.endswith(b"\n"):
                    raise ValueError("the exposure journal ends before the checkpoint")
                row = json.loads(raw)
                if (row["index"] != index or row["source_update"] != index
                        or any(type(row[key]) is not int or row[key] < 0 for key in EXPOSURE_TOTALS)):
                    raise ValueError("the exposure journal lost its absolute update sequence")
                rows.append(row)
                raw_prefix.extend(raw)
                digest.update(raw)
        seal = exposure_seal(step, digest)
        if state.get(EXPOSURE_KEY) != seal:
            raise ValueError("the exposure journal does not match its checkpoint seal")
        if destination is not None:
            with checkpoint.open("rb") as source, destination.open("xb") as target:
                shutil.copyfileobj(source, target, length=4 * 1024**2)
                target.flush()
                os.fsync(target.fileno())
            if prep.sha(destination) != expected:
                raise ValueError("the isolated checkpoint copy differs")
        return dict(**seal, prior_record=str(original), checkpoint_sha256=expected,
                    binding_sha256=binding["binding_sha256"]), rows, bytes(raw_prefix)


def run(bundle, record, cutoff, tag, pins, layout_sha, *, proof=None, resume=None,
        probe_updates=(), device="cuda"):
    binding = base.context_training_state.make_binding
    ordinary_eval = trainee._ce_recomputed
    ordinary_split = base.muon.split_params
    ordinary_save = packed_document_training.save_packed_checkpoint
    optimizer_steps = []
    exposure_digest = sha256()
    pending = {}
    current = None
    probe = bool(probe_updates)
    if (probe and resume) or (not probe and proof is None):
        raise ValueError("probes start fresh and full training requires its sealed exposure counts")
    signature = loss_signature(bundle, pins, layout_sha)

    def bind(plan, recipe, cache, device):
        if (plan.steps != bundle.steps or plan.tokens_per_update != prep.ACCUM * base.MICRO_TOKENS
                or cache != bundle.cache or recipe["ce_recompute_rows"] != 1024
                or recipe.get("ste_update_cache") or recipe.get("packed_document_profile")):
            raise ValueError("the combined course uses the sealed native optimizer geometry")
        bundle.unchanged()
        return binding(plan, dict(recipe, p109c_bilingual_mixed=signature), cache, device)

    def split(model):
        matrices, others = ordinary_split(model)
        head = model.decimal_head.weight
        return [weight for weight in matrices if weight is not head], [*others, head]

    class Cursor(base.MicroTokensCursor):
        def prepare(self):
            nonlocal current
            if pending or time.time() >= cutoff:
                raise RuntimeError("a training update was left pending or exceeded the user window")
            if probe and self.next_update == len(probe_updates):
                raise base.ProbeComplete()
            update = super().prepare()
            address = probe_updates[update.update] if probe else update.update
            schedule = bundle.schedule[address]
            raw = iter(bundle.raw_batch(schedule[schedule[:, 0] == -1, 1]))
            n_raw = int(np.count_nonzero(schedule[:, 0] == -1)) * base.MICRO_TOKENS
            counts = np.zeros(4, dtype=np.int64)
            prepared = []
            course = relation_count = decimal_count = 0
            for (lane, index), (template_x, template_y) in zip(schedule, update.batches, strict=True):
                if lane == -1:
                    batch = next(raw)
                    x, y = (template_x.new_tensor(batch[:, :-1]), template_y.new_tensor(batch[:, 1:]))
                    data = None
                elif lane == -2:
                    x = template_x.new_zeros(template_x.shape)
                    y = template_y.new_full(template_y.shape, prep.IGNORE)
                    data = None
                else:
                    inputs, labels, segments = bundle.data[lane][index].transpose(1, 0, 2)
                    x, y = template_x.new_tensor(inputs.astype(np.int64)), template_y.new_tensor(labels.astype(np.int64))
                    aux = bundle.aux[lane][index]
                    groups = relation.relation_groups_for(aux, prep.BATCH)
                    targets = np.flatnonzero(labels.ravel() != prep.IGNORE)
                    kinds = base.label_kinds(labels, segments)
                    relation.keep_relation_winners(kinds, segments, groups)
                    events = aux["decimal"]
                    if any(kinds[row, column] != 1 or value < 1000 for row, column, value in events):
                        raise ValueError("the decimal target lost its first-answer supervision")
                    counts += np.bincount(kinds.ravel(), minlength=4)
                    course += int(np.count_nonzero(segments))
                    relation_count += len(groups)
                    decimal_count += len(events)
                    data = (segments, targets, kinds, groups, events)
                prepared.append((x, y))
                pending[id(y)] = (int(lane), data)
            course_weight = .25 if address >= bundle.warmup else 0.
            active = sum(weight for weight, total in zip(base.KIND_WEIGHTS, counts[1:], strict=True) if total)
            if not n_raw or course_weight and active <= 0:
                raise ValueError("each sealed mixed update must contain raw and positive course supervision")
            ce_weights = [(1. - course_weight) / n_raw]
            ce_weights.extend(float(course_weight * w / (active * n)) if n else 0.
                              for w, n in zip(base.KIND_WEIGHTS, counts[1:], strict=True))
            current = dict(source_update=address, ce_weights=ce_weights, raw_targets=n_raw, course_tokens=course,
                           answer_start_targets=int(counts[1]), answer_body_targets=int(counts[2]),
                           answer_eot_targets=int(counts[3]), decimal_targets=decimal_count,
                           decimal_correct=0, contrast_questions=relation_count, n_valid=n_raw+int(counts[1:].sum()))
            self._pending = replace(update, batches=tuple(prepared))
            return self._pending

        def finish(self, *, optimizer_applied):
            if pending or not optimizer_applied:
                raise RuntimeError("a sealed bilingual optimizer update was skipped or not consumed")
            result = super().finish(optimizer_applied=optimizer_applied)
            row = dict(index=result["update"], **current)
            optimizer_steps.append(row)
            line = json.dumps(row, allow_nan=False) + "\n"
            updates.write(line)
            exposure_digest.update(line.encode("utf-8"))
            return result

    def ce(model, x, y, rows):
        if not model.training:
            return ordinary_eval(model, x, y, rows)
        lane, data = pending.pop(id(y))
        if lane == -2:
            # The established native route accounts for one forward per slot.
            return model(x, return_hidden=True).sum() * 0.
        if lane == -1:
            nll, _ = base.target_nll(model, model(x, return_hidden=True), y, rows=rows)
            total = nll.sum()
            loss = total * current["ce_weights"][0]
        else:
            segments, targets, kinds, groups, events = data
            if len(groups) > 1:
                hidden = bundle.packed_hidden(model, x, segments, flash=True, hidden=base.masked_hidden)
            else:
                hidden = base.masked_hidden(model, x, segments, flash=True)
            nll, valid = base.prior.course_target_nll(
                model, hidden, y, rows * 2, torch.as_tensor(targets, device=y.device))
            kind = torch.as_tensor(kinds, device=y.device)
            total = nll.masked_select(kind.ne(0)).sum()
            loss = sum(nll.masked_select(kind.eq(i)).sum() * current["ce_weights"][i] for i in range(1, 4))
            if groups:
                share = signature["relation_weight"] / current["contrast_questions"]
                for scores, gold in relation.relation_scores(nll, valid, y, segments, groups, prep.END):
                    loss = loss + share * base.prior.contrast_row(scores, gold)
            if events:
                r, c = torch.as_tensor([event[:2] for event in events], device=x.device).T
                labels = [event[2] for event in events]
                auxiliary, count, correct, _ = base.prior.joint_decimal.objective(
                    model.decimal_head, hidden[r, c, None], y[r, c, None], labels, [[0]] * len(events))
                if count != len(events):
                    raise RuntimeError("the decimal task lost an admitted target")
                current["decimal_correct"] += correct
                loss = loss + auxiliary * (signature["decimal_weight"] / current["decimal_targets"])
        return (total.detach() / current["n_valid"] + (loss - loss.detach())) * prep.ACCUM

    def save_checkpoint(path, state):
        if state["step"] != len(optimizer_steps):
            raise RuntimeError("the native checkpoint and committed exposure length disagree")
        updates.flush()
        os.fsync(updates.fileno())
        state[EXPOSURE_KEY] = exposure_seal(state["step"], exposure_digest)
        ordinary_save(path, state)

    commands, display = base.native_commands(bundle, tag, resume is not None)
    checkpoints, logs = record / "ckpt", record / "native_logs"
    checkpoints.mkdir()
    logs.mkdir()
    checkpoint = checkpoints / checkpoint_name(display, tag)
    prefix = None
    prefix_bytes = b""
    if resume is not None:
        prefix, optimizer_steps, prefix_bytes = inspect_resume(bundle, resume, tag, signature, proof,
                                                               destination=checkpoint)
        native.publish(record / "resume_prefix.json", prefix)
    start = len(optimizer_steps)
    with (patch.object(native, "STEPS", bundle.steps),
          patch.object(trainee, "prepare", bundle.prepare),
          patch.object(trainee, "LOGS", logs), patch.object(trainee, "CKPT", checkpoints),
          patch.object(base.routed, "MicroTokensCursor", Cursor),
          patch.object(base.context_training_state, "make_binding", bind),
          patch.object(base.muon, "split_params", split), patch.object(trainee, "_ce_recomputed", ce),
          patch.object(packed_document_training, "save_packed_checkpoint", save_checkpoint),
          (record / "updates.jsonl").open("x", encoding="utf-8", newline="\n", buffering=1) as updates):
        if prefix_bytes:
            updates.write(prefix_bytes.decode("utf-8"))
            exposure_digest.update(prefix_bytes)
        try:
            result = base.routed.run_native("uniform_r2", commands, build_model=base.MixedG4)
        except base.ProbeComplete:
            if (not probe or len(optimizer_steps) != len(probe_updates)
                    or not all(sum(row[key] for row in optimizer_steps)
                               for key in ("decimal_targets", "contrast_questions", "course_tokens"))):
                raise RuntimeError("the grouped diagnostic must apply every objective")
            bundle.unchanged()
            native.publish(record / "report.json", dict(status="TECHNICAL_PROBE_COMPLETE", tag=tag,
                input_manifest_sha256=bundle.digest, loss_contract=signature, exposure=optimizer_steps,
                device=device, evaluated_quality=False,
                peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20 if device == "cuda" else None))
            return
    bundle.unchanged()
    if ([row["index"] for row in result["updates"]] != list(range(start, bundle.steps))
            or [row["index"] for row in optimizer_steps] != list(range(bundle.steps))):
        raise RuntimeError("recorded bilingual input did not match the actual optimizer updates")
    raw, course, questions, *answers = (sum(row[key] for row in optimizer_steps) for key in EXPOSURE_TOTALS)
    if (raw, course, questions, sum(answers)) != (proof["raw_tokens"], proof["course_tokens"],
                                                  proof["relations"], proof["answer_targets"]):
        raise ValueError("the actual training changed the sealed raw, course, relation or answer exposure")
    with patch.object(native, "STEPS", bundle.steps):
        native.export_for_evaluation(checkpoint, record / "evaluation.pt")
    digest = prep.sha(record / "evaluation.pt")
    result.update(input_manifest_sha256=bundle.digest, loss_contract=signature, exposure=optimizer_steps,
                  peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                  peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20, evaluation_sha256=digest)
    if prefix is not None:
        result["resume_prefix"] = prefix
    native.publish(record / "training.json", result)
    native.publish(record / "report.json", dict(status="FULL_SCRATCH_MIXED_COMPLETE", tag=tag,
        steps=bundle.steps, input_manifest_sha256=bundle.digest, evaluation_sha256=digest,
        raw_tokens=prep.RAW_TOKENS, course_tokens=bundle.manifest["course_tokens"]))
