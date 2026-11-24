"""Compare real MATH and packed-Flash P107 optimizer updates from one boundary."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from functools import partial
import gc
import json
from pathlib import Path
import sys
from unittest.mock import patch

import torch
from torch.nn import functional as F

from scripts import diag_p107_v11_full_packed_attention as diagnostic
from scripts.interactive_research_infer import state_fingerprint


PAIR = diagnostic.PAIR
PROBE_UPDATES = 16


def mask_layout(mask):
    allowed = mask[:, 0]
    batch, width, _ = allowed.shape
    starts = torch.ones((batch, width), dtype=torch.bool, device=mask.device)
    starts[:, 1:] = ~allowed.diagonal(-1, -2, -1)
    terminal = torch.tensor([batch*width], device=mask.device)
    offsets = torch.cat((starts.flatten().nonzero().flatten(), terminal)).to(torch.int32)
    causal = not bool(allowed.diagonal(1, -2, -1).any())
    return offsets, int(offsets.diff().max()), causal


def dispatch(native):
    last_mask = route = None

    def attention(q, k, v, *, attn_mask=None, is_causal=False, enable_gqa=False):
        nonlocal last_mask, route
        if not torch.is_grad_enabled():
            repeats = q.shape[1] // k.shape[1] if enable_gqa else 1
            if repeats != 1:
                k = k.repeat_interleave(repeats, dim=1)
                v = v.repeat_interleave(repeats, dim=1)
            return native(q, k, v, attn_mask=attn_mask, is_causal=is_causal)
        if attn_mask is None or not enable_gqa or is_causal:
            raise ValueError("the packed learning route needs explicit document GQA")
        if attn_mask is not last_mask:
            offsets, maximum, causal = mask_layout(attn_mask)
            last_mask = attn_mask
            route = diagnostic.packed_route(attn_mask, offsets, maximum, causal)
        return route(q, k, v, attn_mask=attn_mask, enable_gqa=True)

    return attention


def fingerprint_boundary(session, _profile, _initial, _directory):
    return dict(updates=session.cursor, slots=session.cursor*PAIR.SLOTS,
                model_sha256=state_fingerprint(session.trainer.model), checkpoint_written=False)


def worker(arm_path, arm_sha, pins, profile_path, profile_sha, _resume, record, cutoff):
    with (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
        profile = json.loads(PAIR.supervisor.manifest_bytes(profile_path, profile_sha))
        arm = json.loads(PAIR.supervisor.manifest_bytes(arm_path, arm_sha))
        if (profile["sources"] != PAIR.source_pins() or arm["end"] != 1152 or arm["arm"] != "observe"
                or torch.cuda.device_count() != 1 or any(PAIR.evaluation.core6.digest(Path(p)) != h for p,h in pins.items())):
            raise ValueError("the original learning sources, 1,152 checkpoint and assigned GPU are required")
        total, used, _ = PAIR.telemetry.gpu_status(record)
        allowance = PAIR.supervisor.CARD_LIMIT_MIB - used - 384
        if allowance <= 0:
            raise RuntimeError("the approved card cap leaves no allocation budget")
        torch.cuda.set_per_process_memory_fraction(allowance / total)
        torch.set_num_threads(2)
        torch.backends.cuda.matmul.allow_tf32 = False
        corpus = PAIR.load_index(Path(profile["index"]), profile["index_sha256"])["splits"]
        native_sdpa, native_session = F.scaled_dot_product_attention, PAIR.make_session
        results = {}
        for mode in ("math", "packed"):
            destination = record / mode
            destination.mkdir(exist_ok=False)

            def build(*args, **kwargs):
                session = native_session(*args, **kwargs)
                session.trainer.model.cfg.sdpa_gqa = mode == "packed"
                return session

            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
            with (patch.object(PAIR, "make_session", build),
                  patch.object(PAIR, "write_boundary", fingerprint_boundary),
                  patch.object(F, "scaled_dot_product_attention", dispatch(native_sdpa) if mode == "packed" else native_sdpa)):
                row = PAIR.train_arm(profile, corpus, "observe", arm["end"]+PROBE_UPDATES, destination,
                                     cutoff, resume=arm["final"])
            row.update(peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                       peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
            results[mode] = row
            gc.collect()
        a,b=results["math"],results["packed"]
        controls=("start","end","initial_sha256","source_end_rng","causal_targets","masked_targets")
        if any(a[k]!=b[k] for k in controls) or any(PAIR.evaluation.core6.digest(Path(p)) != h for p,h in pins.items()):
            raise ValueError("the input, common exposure or source identity differs")
        PAIR.supervisor.publish(record / "report.json", dict(status="COMPLETE", arms=results,
            update_count=PROBE_UPDATES, source_receipt_sha256=arm_sha, starting_checkpoint_sha256=arm["final"]["sha256"],
            profile_sha256=profile_sha, sources=pins, allocator_budget_mib=allowance, optimizer_checkpoints_written=0))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", type=Path, required=True)
    p.add_argument("--profile-sha256", required=True)
    p.add_argument("--arm-receipt", type=Path, required=True)
    p.add_argument("--arm-receipt-sha256", required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--record", type=Path, required=True)
    p.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = p.parse_args()
    files = (Path(__file__), Path(diagnostic.__file__), Path(diagnostic.packed.__file__))
    pins = {str(path.resolve()): PAIR.evaluation.core6.digest(path) for path in files}
    if pins[str(Path(__file__).resolve())] != PAIR.supervisor.digest(args.source_sha256):
        p.error("the sealed training diagnostic source differs")
    with (patch.object(PAIR.supervisor, "gpu_worker", partial(worker, args.arm_receipt.absolute(),
                                                             args.arm_receipt_sha256, pins)),
          patch.object(PAIR.supervisor, "gpu_status", partial(PAIR.telemetry.gpu_status, args.record.absolute()))):
        return PAIR.supervisor.supervise(args.profile.absolute(), args.profile_sha256, False,
                                        args.record.absolute(), args.stop_by)


if __name__ == "__main__":
    sys.exit(main())
