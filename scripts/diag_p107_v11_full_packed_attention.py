"""Measure document-local Flash attention in the real P107 training forward/backward."""

import argparse
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from datetime import datetime
from functools import partial
import gc
import json
import math
from pathlib import Path
import sys
from time import perf_counter, sleep, time
from unittest.mock import patch

import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p107_v11_packed_attention as packed
from scripts import eval_p107_v11_causal_groups_cpu as causal
from tinylm.train.anneal_schedule import quant_anneal_factor, resolve_quant_start
from tinylm.train.hybrid_mntp import causal_batch, mntp_batch, uniform_mntp_selection


PAIR = causal.pair
MODES = ("math", "packed", "packed_without_checkpoint")


def fixed_batches(index):
    source = PAIR.documents.BinaryDocumentSource(index["splits"]["train"], batch=PAIR.BATCH,
                                                 micros=PAIR.MICROS, length=PAIR.LENGTH, seed=PAIR.SEED)
    sequence = source.next_update()
    x, d = sequence[0]
    causal_input = causal_batch(x, d, vocab_size=PAIR.supervisor.VOCAB)
    x_masked, docs_masked = sequence[PAIR.MICROS // 2]
    selected = uniform_mntp_selection(x_masked, docs_masked, vocab_size=PAIR.supervisor.VOCAB,
                                      probability=.15, generator=torch.Generator().manual_seed(PAIR.SEED))
    masked_input = mntp_batch(x_masked, docs_masked, selected, vocab_size=PAIR.supervisor.VOCAB)
    return ((causal_input, packed.offsets_for(d[:, :-1]), True),
            (masked_input, packed.offsets_for(docs_masked[:, :-1]), False))


def packed_route(mask, offsets, maximum, window_causal):
    from torch.nn.attention.varlen import varlen_attn

    admitted = None

    def attention(q, k, v, *, attn_mask, is_causal=False, enable_gqa=False):
        nonlocal admitted
        if is_causal or not enable_gqa or q.shape[1] != 12 or k.shape[1] != 3 or k.shape != v.shape:
            raise ValueError("the full-window GQA projection differs")
        if admitted is None:
            if not torch.equal(attn_mask, mask):
                raise ValueError("the model attention visibility differs from the packed input")
            admitted = attn_mask
        if attn_mask is not admitted:
            raise ValueError("a different mask reached the same forward/backward")
        batch, heads, width, depth = q.shape
        tensors = tuple(value.transpose(1, 2).reshape(batch * width, value.shape[1], depth)
                        .to(torch.bfloat16).contiguous() for value in (q, k, v))
        out = varlen_attn(*tensors, offsets, offsets, maximum, maximum, is_causal=window_causal)
        return out.reshape(batch, width, heads, depth).transpose(1, 2)

    return attention


def run_batch(model, batch, offsets, positions, maximum, causal_path, mode, capture):
    device = next(model.parameters()).device
    inputs, targets, mask = (item.to(device) for item in (batch.inputs, batch.targets, batch.attention_mask))
    model.cfg.sdpa_gqa = mode != "math"
    model.cfg.grad_checkpoint = mode != "packed_without_checkpoint"
    model.zero_grad(set_to_none=True)
    route = (nullcontext() if mode == "math" else patch.object(
        F, "scaled_dot_product_attention", packed_route(mask, positions, maximum, causal_path)))
    with route:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        begin = perf_counter()
        with torch.autocast("cuda", dtype=torch.bfloat16), patch.object(model, "_head_logits", PAIR.HiddenForCE):
            hidden = model(inputs, attention_mask=mask, allow_fixed_g4_r2=True).hidden
            loss, count, ids = PAIR.target_head.objective(model, hidden, targets, rows=PAIR.CE_ROWS,
                                                         collect_ids=not causal_path)
        loss.backward()
        torch.cuda.synchronize()
        seconds = perf_counter() - begin
    if count != batch.target_count or not torch.isfinite(loss):
        raise ValueError("the set of supervised positions or the loss differs")
    row = dict(causal=causal_path, seconds=seconds, loss=float(loss.detach()), targets=count,
               peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
               peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
               document_spans=offsets.diff().tolist())
    if not capture:
        return row, None
    gradients = {name: value.grad.detach().cpu() for name, value in model.named_parameters() if value.grad is not None}
    selected = ids[targets.ne(-100)].detach().cpu() if ids is not None else None
    return row, (gradients, selected)


def compare(reference, candidate):
    gold_grad, gold_ids = reference
    gradients, ids = candidate
    if gradients.keys() != gold_grad.keys() or (ids is None) != (gold_ids is None):
        raise ValueError("the compared gradient or observed ID domain differs")
    original_sq = sum(float(v.square().sum()) for v in gold_grad.values())
    delta_sq = sum(float((value - gold_grad[name]).square().sum()) for name, value in gradients.items())
    if not math.isfinite(original_sq + delta_sq) or original_sq <= 0:
        raise ValueError("the measured parameter gradients are not finite")
    return dict(relative_gradient_l2=math.sqrt(delta_sq/original_sq),
                observed_id_matches=(int(ids.eq(gold_ids).sum()) if ids is not None else None),
                observed_id_count=(len(ids) if ids is not None else None))


def worker(arm_path, arm_sha256, pins, profile_path, profile_sha256, _resume, record, cutoff):
    with (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
        profile = json.loads(PAIR.supervisor.manifest_bytes(profile_path, profile_sha256))
        if (profile["sources"] != PAIR.source_pins()
                or any(PAIR.evaluation.core6.digest(Path(path)) != digest for path, digest in pins.items())
                or torch.cuda.device_count() != 1):
            raise ValueError("the original sources and one assigned device are required")
        arm = json.loads(PAIR.supervisor.manifest_bytes(arm_path, arm_sha256))
        if arm["arm"] != "observe" or arm["end"] != 896:
            raise ValueError("the fixed 896-update uniform reference is required")
        total, used, _ = PAIR.telemetry.gpu_status(record)
        allowance = PAIR.supervisor.CARD_LIMIT_MIB - used - 384
        if allowance <= 0:
            raise RuntimeError("the device cap leaves no room for the trial")
        torch.cuda.set_per_process_memory_fraction(allowance / total)
        torch.set_num_threads(2)
        torch.backends.cuda.matmul.allow_tf32 = False
        index = PAIR.load_index(Path(profile["index"]), profile["index_sha256"])
        batches = [(batch, counts, counts.to("cuda"), int(counts.diff().max()), direction)
                    for batch, counts, direction in fixed_batches(index)]
        model = causal.checkpoint_model(arm, arm["end"])
        model.clear_quant()
        model.cuda().train()
        anneal_start = resolve_quant_start(PAIR.WARMUP, PAIR.STEPS)
        anneal = quant_anneal_factor(arm["end"] - 1, PAIR.STEPS, "wsd", "linear", anneal_start, .60)
        model.set_anneal(anneal)
        baseline = {}
        runs, errors = [], {}
        order = MODES + MODES + tuple(reversed(MODES))
        for visit, mode in enumerate(order):
            if mode in errors:
                continue
            if time() >= cutoff:
                raise TimeoutError("the authorized CUDA trial ended")
            capture = visit < len(MODES)
            try:
                torch.cuda.empty_cache()
                with sdpa_kernel(SDPBackend.MATH):
                    for batch, offsets, positions, maximum, direction in batches:
                        row, proof = run_batch(model, batch, offsets, positions, maximum, direction, mode, capture)
                        if capture and mode == "math":
                            baseline[direction] = proof
                        elif capture:
                            row.update(compare(baseline[direction], proof))
                        runs.append(dict(row, mode=mode, warmup=capture))
                        print("P107_FULL_PACKED_ATTENTION_BATCH", mode, direction, row["seconds"], flush=True)
            except (torch.OutOfMemoryError, RuntimeError) as error:
                if mode == "math":
                    raise
                errors[mode] = dict(error_type=type(error).__name__, message=str(error))
                print("P107_FULL_PACKED_ATTENTION_ERROR", mode, errors[mode], flush=True)
            finally:
                model.zero_grad(set_to_none=True)
                model.clear_quant()
                gc.collect()
        if any(PAIR.evaluation.core6.digest(Path(path)) != digest for path, digest in pins.items()):
            raise ValueError("a benchmark source changed")
        PAIR.supervisor.publish(record / "report.json", dict(status="COMPLETE" if not errors else "PARTIAL", runs=runs,
            errors=errors, checkpoint_sha256=arm["final"]["sha256"], profile_sha256=profile_sha256,
            arm_receipt_sha256=arm_sha256, sources=pins, anneal=anneal, allocator_mib=allowance))


def wait_for_return(previous, stop_by):
    terminal = previous / "supervisor.json"
    while time() < stop_by.timestamp() - 120:
        if terminal.is_file():
            try:
                receipt = PAIR.evaluation.read_json(terminal)
            except json.JSONDecodeError:
                pass
            else:
                if (receipt["returncode"] or receipt["stop_reason"] is not None
                        or receipt["card_after_exit"].get("compute_pids") != []):
                    raise ValueError("the preceding supervised job did not return the GPU cleanly")
                return True
        sleep(2.)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--arm-receipt", type=Path, required=True)
    parser.add_argument("--arm-receipt-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    parser.add_argument("--after-run", type=Path)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None:
        parser.error("the trial needs an explicit cutoff timezone")
    files = (Path(__file__), Path(packed.__file__), Path(causal.__file__))
    pins = {str(path.resolve()): PAIR.evaluation.core6.digest(path) for path in files}
    if pins[str(Path(__file__).resolve())] != PAIR.supervisor.digest(args.source_sha256):
        parser.error("the sealed benchmark script differs")
    if args.after_run is not None and not wait_for_return(args.after_run, args.stop_by):
        print("P107_FULL_PACKED_ATTENTION_NO_TIME_AFTER_PREVIOUS", flush=True)
        return 0
    with (patch.object(PAIR.supervisor, "gpu_worker", partial(worker, args.arm_receipt.absolute(),
                                                             args.arm_receipt_sha256, pins)),
          patch.object(PAIR.supervisor, "gpu_status", partial(PAIR.telemetry.gpu_status, args.record.absolute()))):
        return PAIR.supervisor.supervise(args.profile.absolute(), args.profile_sha256, False,
                                        args.record.absolute(), args.stop_by)


if __name__ == "__main__":
    sys.exit(main())
