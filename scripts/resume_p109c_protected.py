"""Resume P109C with a guarded allocator and rolling native recovery checkpoints."""

import argparse
from copy import deepcopy
from datetime import datetime
from functools import partial
import inspect
from pathlib import Path
import sys
from unittest.mock import patch

from scripts import p109_gpu_supervisor as telemetry
from scripts import resume_p109c_scratch330 as recovery
from scripts import run_p109c_scratch330 as entry
from tinylm.train import context_training_state, packed_document_training, trainer
from tinylm.train.context_micro_tokens import MicroTokensCursor


SAVE_EVERY = 64
NATIVE_VALIDATE = context_training_state.validate_trainer_control


def validate_recovery_control(control, step, optimizer_updates):
    history = control.get("history")
    if not history or history[-1].get("step") == step:
        return NATIVE_VALIDATE(control, step, optimizer_updates)
    last_eval = history[-1]["step"]
    totals = control["loss_accumulators"]
    if (step % SAVE_EVERY or last_eval != (step // entry.EVAL_EVERY) * entry.EVAL_EVERY
            or control["completed_updates"] != step or optimizer_updates != step
            or control["n_skip"] != 0 or totals["no_n"] != step):
        raise ValueError("the rolling optimizer commit and last real evaluation differ")
    # The native validator expects the evaluation and commit counters to end together.
    # Validate the original evaluation history at its real end before returning the newer commit.
    validation_view = dict(control, completed_updates=last_eval,
                           loss_accumulators=dict(totals, no_n=last_eval))
    NATIVE_VALIDATE(validation_view, last_eval, last_eval)
    return deepcopy(control)


def save_rolling_checkpoint(frame, record, step):
    state = frame.f_locals
    ctx = state["_context_cursor"]
    if (not state["chat32_tokenizer"] or state["_packed_inputs"] is not None or state["shadow"] is not None
            or state["_experimental_route"] is not None or state["p101a_m0"] or state["ce_vocab_tile"]
            or state["ce_recompute_rows"] != 1024 or not state["opt_muon"] or ctx.next_update != step):
        raise ValueError("the recovery capture requires the admitted native P109C update contract")
    control = validate_recovery_control(dict(completed_updates=step,
        best_val=state["best_val"], best_step=state["best_step"], since_improve=state["since_improve"],
        history=state["hist"], n_skip=state["n_skip"], gmax=state["gmax"], gpeak=state["gpeak"],
        loss_accumulators=state["_acc"]), step, ctx.optimizer_updates)
    payload = context_training_state.capture_training_state(ctx, state["va"], state["_context_binding"], control)
    blob = dict(model=state["model"].state_dict(), opt=state["opt"].state_dict(), opt_muon=state["opt_muon"].state_dict(),
                step=step, cfg=state["cfg"].__dict__, ce_recompute_rows=state["ce_recompute_rows"],
                tokenizer_lineage="chat32", tokenizer_sha256=state["meta"]["tokenizer_sha256"],
                **{trainer.CONTEXT_STATE_KEY: payload})
    folder = record / "rolling_checkpoints"
    folder.mkdir(exist_ok=True)
    path = folder / f"resume_{(step // SAVE_EVERY) % 2}.pt"
    packed_document_training.save_packed_checkpoint(path, blob)
    entry.publish(folder / f"step_{step}.json", dict(checkpoint=str(path), step=step,
        optimizer_updates=ctx.optimizer_updates, sha256=entry.file_sha(path).upper(),
        context_state_sha256=payload["payload_sha256"], bytes=path.stat().st_size))
    print("P109C_ROLLING_CHECKPOINT", step, flush=True)


def checkpoint_hook(record):
    native = trainer.train
    lines, begin = inspect.getsourcelines(native)
    targets = [index for index, line in enumerate(lines, begin)
               if line.strip() == "if s % 10 == 0 or s == steps - 1:"]
    if len(targets) != 1:
        raise ValueError("the stable native post-update checkpoint position differs")
    target = targets[0]
    original = MicroTokensCursor.finish
    enabled = True

    def capture_failure(step, error):
        nonlocal enabled
        enabled = False
        print("P109C_ROLLING_CHECKPOINT_DISABLED", step, type(error).__name__, str(error), flush=True)

    def finish(cursor, *, optimizer_applied):
        result = original(cursor, optimizer_applied=optimizer_applied)
        step = cursor.next_update
        if not enabled or not optimizer_applied or step % SAVE_EVERY or step % entry.EVAL_EVERY == 0 or step >= entry.STEPS:
            return result
        frame = sys._getframe(1)
        while frame is not None and frame.f_code is not native.__code__:
            frame = frame.f_back
        if frame is None or frame.f_locals["s"] + 1 != step or sys.gettrace() is not None:
            capture_failure(step, RuntimeError("the native committed update could not be tracked"))
            return result

        def capture_once(active, event, _arg):
            if event == "return":
                sys.settrace(None)
            elif event == "line" and active.f_lineno == target:
                sys.settrace(None)
                try:
                    save_rolling_checkpoint(active, record, step)
                except Exception as error:
                    capture_failure(step, error)
            return capture_once

        # Trace only the already-active native frame until its accumulated loss is committed.
        sys.settrace(lambda _frame, _event, _arg: None)
        frame.f_trace = capture_once
        return result

    return patch.object(MicroTokensCursor, "finish", finish)


def worker(original, checksum, step, prior, path, sha256, resume, record, cutoff, *, reuse_quantization):
    import torch

    free, total = torch.cuda.mem_get_info()
    mib = 2**20
    allowed = (entry.CARD_LIMIT_MIB - 384) * mib - (total - free)
    if not 0 < allowed <= total:
        raise RuntimeError("the approved GPU cap leaves no allocator budget")
    torch.cuda.set_per_process_memory_fraction(allowed / total)
    entry.publish(record / "allocator_limit.json", dict(free_at_context_bytes=free, total_bytes=total,
                  allocator_budget_bytes=allowed, card_cap_mib=entry.CARD_LIMIT_MIB))
    with (checkpoint_hook(record),
          patch.object(context_training_state, "validate_trainer_control", validate_recovery_control)):
        recovery.worker(original, checksum, step, prior, path, sha256, resume, record, cutoff,
                        reuse_quantization=reuse_quantization)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--prior-record", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    original = args.checkpoint.absolute()
    if original.name != f"{entry.PRESET}_ko-en_330M_{entry.TAG}.pt":
        raise ValueError("the checkpoint filename is outside the original native run")
    target = partial(worker, original, entry.digest(args.checkpoint_sha256), args.step, args.prior_record.absolute())
    record = args.record.absolute()
    with (patch.object(entry, "gpu_worker", target),
          patch.object(entry, "gpu_status", partial(telemetry.gpu_status, record))):
        return entry.supervise(args.manifest.absolute(), args.manifest_sha256, True, record, args.stop_by,
                               reuse_quantization=True)


if __name__ == "__main__":
    raise SystemExit(main())
