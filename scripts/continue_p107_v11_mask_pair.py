"""Continue both arms from the measured matched P107 boundary when time permits."""

import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime
from functools import partial
import gc
import json
import math
from pathlib import Path
import time
import traceback
from unittest.mock import patch

import numpy as np
import torch

from scripts import run_p107_v11_mask_pair as pair


def read_pair(previous, expected):
    terminal = pair.evaluation.read_json(previous / "supervisor.json")
    report = pair.evaluation.read_json(previous / "report.json")
    if (terminal["returncode"] or terminal["stop_reason"] is not None
            or terminal["card_after_exit"].get("compute_pids") != [] or report["profile_sha256"] != expected):
        raise ValueError("the prior matched pair needs a successful close and device return")
    if report["status"] == "FULL_300M_PAIR":
        return None
    if report["status"] == "MATCHED_PARTIAL_BUDGET_PAIR":
        arms = report["arms"]
    elif report["status"] == "PROBE_COMPLETE_TIME_HOLD":
        arms = report["probe"]
    else:
        raise ValueError("the prior report does not contain a matched saved boundary")
    reference, candidate = (arms[name] for name in pair.ARMS)
    if any(reference[key] != candidate[key] for key in ("start", "end", "initial_sha256", "source_end_rng",
                                                        "causal_targets")):
        raise ValueError("resuming requires identical prior exposure and initialized state")
    start = reference["end"]
    for name, row in arms.items():
        boundary = row["final"]
        target = previous / name / f"step_{start}.pt"
        if Path(boundary["path"]) != target or boundary["updates"] != start or boundary["slots"] != start * pair.SLOTS:
            raise ValueError("the paired training checkpoints do not close the prior exposure")
        pair.evaluation.regular_file(target)
    return arms


def read_flash_probe(receipt, arms, profile_sha):
    path, expected = receipt
    probe = json.loads(pair.supervisor.manifest_bytes(path, expected))
    terminal = pair.evaluation.read_json(path.with_name("supervisor.json"))
    reference = arms[pair.ARMS[0]]
    if (probe["status"] != "COMPLETE" or probe["profile_sha256"] != profile_sha
            or probe["starting_checkpoint_sha256"] != reference["final"]["sha256"]
            or terminal["returncode"] != 0 or terminal["stop_reason"] is not None
            or terminal["card_after_exit"]["compute_pids"] != []):
        raise ValueError("the packed-Flash probe must match the resumed reference and have returned the GPU")
    for source, sha in probe["sources"].items():
        if pair.evaluation.core6.digest(Path(source)) != sha:
            raise ValueError("the verified packed-Flash source has changed")
    math_arm, packed = (probe["arms"][key] for key in ("math", "packed"))
    controls = ("start", "end", "initial_sha256", "source_end_rng", "causal_targets", "masked_targets")
    if (packed["start"] != reference["end"] or packed["end"] - packed["start"] != probe["update_count"]
            or any(math_arm[key] != packed[key] for key in controls)):
        raise ValueError("the Flash timing probe did not use matched exposure")
    times = [value["seconds"][2:] for value in (math_arm, packed)]
    if any(not lane or any(not math.isfinite(v) or v <= 0 for v in lane) for lane in times):
        raise ValueError("the Flash timing probe needs measured positive update durations")
    return float(np.percentile(times[1], 90) / np.percentile(times[0], 90))


def budget_end(arms, cutoff, flash_ratio=None):
    start = arms[pair.ARMS[0]]["end"]
    costs = {}
    for name, row in arms.items():
        recent = row["seconds"][4:][-48:]
        if not recent or any(not math.isfinite(value) or value <= 0 for value in recent):
            raise ValueError("both previous arms need positive measured update durations")
        costs[name] = float(np.percentile(recent, 90))
        if flash_ratio is not None:
            # The probe measured the uniform arm. Retain margin for the adaptive arm and long execution.
            costs[name] *= min(1., flash_ratio * 1.25)
    available = cutoff - time.time() - 300
    possible = start + math.floor(available / (1.12 * sum(costs.values())))
    end = pair.STEPS if possible >= pair.STEPS else 128 * (possible // 128)
    if end < 512 or end - start < min(128, pair.STEPS - start):
        end = start
    return dict(start=start, end=end, p90_seconds=costs, available_after_reserve_seconds=available)


def worker(previous, path, sha256, _resume, record, cutoff, *, flash_probe=None):
    profile = json.loads(pair.supervisor.manifest_bytes(path, sha256))
    if profile["sources"] != pair.source_pins() or profile["device"] != "cuda":
        raise ValueError("the original exact preparation contract is required")
    arms = read_pair(previous, pair.supervisor.digest(sha256))
    flash_ratio = read_flash_probe(flash_probe, arms, pair.supervisor.digest(sha256)) if flash_probe else None
    budget = budget_end(arms, cutoff, flash_ratio)
    corpus = pair.load_index(Path(profile["index"]), profile["index_sha256"])["splits"]
    total, used, _ = pair.telemetry.gpu_status(record)
    allocator = pair.supervisor.CARD_LIMIT_MIB - used - 384
    if allocator <= 0 or torch.cuda.device_count() != 1:
        raise RuntimeError("the approved single GPU has no reserved budget for this pair")
    torch.cuda.set_per_process_memory_fraction(allocator / total)
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    result = dict(status="STARTED", previous_record=str(previous), profile_sha256=pair.supervisor.digest(sha256),
                  previous_report_sha256=pair.evaluation.core6.digest(previous / "report.json"),
                  allocator_budget_mib=allocator, budget=budget, arms={},
                  training_attention="DOCUMENT_PACKED_FLASH" if flash_probe else "MATH",
                  continuation_sha256=pair.evaluation.core6.digest(Path(__file__)))
    if flash_probe:
        result["flash_probe"] = dict(path=str(flash_probe[0]), sha256=flash_probe[1], p90_ratio=flash_ratio)
    with ((record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        try:
            if budget["end"] == budget["start"]:
                result["status"] = "PRIOR_MATCHED_BOUNDARY_PRESERVED"
                return
            with ExitStack() as stack:
                if flash_probe:
                    from torch.nn import functional as F
                    from scripts.diag_p107_v11_packed_optimizer import dispatch

                    original_session = pair.make_session

                    def make_flash_session(*args, **kwargs):
                        session = original_session(*args, **kwargs)
                        session.trainer.model.cfg.sdpa_gqa = True
                        return session

                    stack.enter_context(patch.object(pair, "make_session", make_flash_session))
                    stack.enter_context(patch.object(F, "scaled_dot_product_attention",
                                                     dispatch(F.scaled_dot_product_attention)))
                for name in pair.ARMS:
                    result["arms"][name] = pair.train_arm(profile, corpus, name, budget["end"], record, cutoff,
                                                          resume=arms[name]["final"])
                    gc.collect()
                    torch.cuda.empty_cache()
            reference, candidate = (result["arms"][name] for name in pair.ARMS)
            if (any(reference[key] != candidate[key] for key in ("start", "end", "initial_sha256", "source_end_rng",
                                                               "causal_targets"))
                    or profile["sources"] != pair.source_pins()):
                raise ValueError("the continued run did not preserve matched controls")
            result["status"] = "FULL_300M_PAIR" if reference["end"] == pair.STEPS else "MATCHED_PARTIAL_BUDGET_PAIR"
        except BaseException as error:
            traceback.print_exc()
            result.update(status="ERROR", error_type=type(error).__name__, error=str(error))
            raise
        finally:
            result["peak_allocated_mib"] = torch.cuda.max_memory_allocated() / 2**20
            result["peak_reserved_mib"] = torch.cuda.max_memory_reserved() / 2**20
            pair.supervisor.publish(record / "report.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--after-pair", type=Path, required=True)
    parser.add_argument("--flash-probe", type=Path)
    parser.add_argument("--flash-probe-sha256")
    parser.add_argument("--check", action="store_true", help="read the manifests and print the budget without CUDA")
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None:
        parser.error("--stop-by needs a UTC offset")
    if bool(args.flash_probe) != bool(args.flash_probe_sha256):
        parser.error("--flash-probe and --flash-probe-sha256 must be used together")
    flash_probe = (args.flash_probe.absolute(), args.flash_probe_sha256) if args.flash_probe else None
    cutoff = args.stop_by.timestamp() - 35
    previous, record = args.after_pair.absolute(), args.record.absolute()
    profile = json.loads(pair.supervisor.manifest_bytes(args.profile.absolute(), args.profile_sha256))
    if profile["sources"] != pair.source_pins() or profile["device"] != "cuda":
        raise ValueError("the original exact preparation contract is required")
    terminal = previous / "supervisor.json"
    print("P107_V11_WAIT_FOR_MATCHED_BOUNDARY", previous, flush=True)
    while time.time() < cutoff - 300:
        if terminal.is_file():
            try:
                arms = read_pair(previous, pair.supervisor.digest(args.profile_sha256))
                break
            except json.JSONDecodeError:
                pass
        if args.check:
            raise ValueError("the previous pair has no completed terminal receipt")
        time.sleep(5.)
    else:
        print("P107_V11_NO_TIME_TO_CONTINUE", flush=True)
        return 0
    if arms is None:
        print("P107_V11_ALREADY_FULL", flush=True)
        return 0
    flash_ratio = read_flash_probe(flash_probe, arms, pair.supervisor.digest(args.profile_sha256)) if flash_probe else None
    budget = budget_end(arms, cutoff, flash_ratio)
    print("P107_V11_CONTINUATION_BUDGET", budget, flush=True)
    if args.check or budget["end"] == budget["start"]:
        return 0
    with (patch.object(pair.supervisor, "gpu_worker", partial(worker, previous, flash_probe=flash_probe)),
          patch.object(pair.supervisor, "gpu_status", partial(pair.telemetry.gpu_status, record))):
        return pair.supervisor.supervise(args.profile.absolute(), args.profile_sha256, True, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
