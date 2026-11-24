"""Fork one unparented P109C prefix to compare the early course CE share."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import time
from unittest.mock import patch

from scripts import diag_p109c_evidence_flip as panel
from scripts import diag_p109c_v2_bilingual_native as probes
from tinylm.train import packed_document_training as saves


prep, mixed, native = probes.prep, probes.mixed, probes.native
state_tools = mixed.context_training_state
TAG = "p109c_early_course_share_chat32_v1_20261124"
EVAL_EVERY = 20
MIXED_UPDATES = 60
PHASE_KEY = "p109c_early_course_phase"
SHARES = {"flat": .25, "lowered": .10}


class SavedBoundary(Exception):
    """The native trainer saved the complete planned partial-run state."""


def admission():
    source = prep.read_json(probes.V2_ONLY_AUDIT)
    bundle = mixed.Bundle(probes.MANIFEST, source["manifest_sha256"])
    plan = dict(tag=TAG, shared_updates=bundle.warmup, mixed_updates=MIXED_UPDATES, share_by_arm=SHARES,
                eval_every=EVAL_EVERY, horizon=bundle.steps, manifest_sha256=bundle.digest)
    end = bundle.warmup + MIXED_UPDATES
    if not 0 < bundle.warmup < end < bundle.steps or bundle.warmup % EVAL_EVERY or end % EVAL_EVERY:
        raise ValueError("both partial endpoints must be native checkpoint boundaries")
    pins = probes.sources()
    for module in (panel, saves, state_tools):
        path = Path(module.__file__).resolve()
        pins[str(path.relative_to(prep.ROOT))] = prep.sha(path)
    own = Path(__file__).resolve()
    pins[str(own.relative_to(prep.ROOT))] = prep.sha(own)
    tokenizer = panel.completed.load_tokenizer()
    rows = panel.requests(tokenizer)
    plan["panel_sha256"] = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper()
    plan["sources"] = pins
    return plan, bundle, tokenizer, rows


def bind_pilot(plan, recipe, cache, device, *, make_binding, expected_share, declared):
    signature = dict(recipe["p109c_mixed_v2"])
    if signature.pop("sft_share") != expected_share or recipe["tag"] != TAG:
        raise ValueError("the trainer did not receive the declared arm share and pilot tag")
    # The shared raw-only prefix has the same binding for either declared continuation.
    signature["bounded_course_share_pilot"] = declared
    return make_binding(plan, dict(recipe, p109c_mixed_v2=signature), cache, device)


def phase_checkpoint(path, identity, torch):
    if path.resolve(strict=True) != path:
        raise ValueError("the phase checkpoint must be an unlinked native file")
    stamp = prep.sha(path)
    state = torch.load(path, map_location="cpu", mmap=True, weights_only=True)
    step = identity["end_update"]
    context = state[mixed.trainer.CONTEXT_STATE_KEY]
    cursor = context["cursor"]["cursor"]
    state_tools._validate_binding(context["binding"])
    if (step != state["step"] or state.get(PHASE_KEY) != identity
            or cursor["next_update"] != step or cursor["optimizer_updates"] != step
            or cursor["draw_tokens"] != step*prep.ACCUM*mixed.MICRO_TOKENS
            or context["control"]["n_skip"] != 0 or context["binding"]["plan"]["steps"] != identity["horizon"]
            or context["payload_sha256"] != state_tools._payload_sha(context)
            or state["tokenizer_sha256"].upper() != prep.TOKENIZER_SHA
            or not state["opt"]["state"] or not state["opt_muon"]["state"]):
        raise ValueError("the prefix does not contain the expected model, RNG, cursor and optimizer states")
    return stamp, state


def run_phase(bundle, record, cutoff, declared, profile_sha, phase, progress, torch, parent):
    shared = phase == "shared"
    share = SHARES["flat"] if shared else SHARES[phase]
    end = bundle.warmup if shared else bundle.warmup + MIXED_UPDATES
    start = 0 if shared else bundle.warmup
    resume = parent and (parent["checkpoint"], parent["sha256"])
    if shared != (resume is None):
        raise ValueError("only the raw prefix starts from random weights")
    if parent:
        parent_sha, parent_state = phase_checkpoint(resume[0], parent["identity"], torch)
        if (parent_sha != resume[1] or parent["identity"]["phase"] != "shared"
                or parent["identity"]["end_update"] != bundle.warmup
                or parent["identity"]["profile_sha256"] != profile_sha):
            raise ValueError("both continuations must read the same pre-mix prefix")
        del parent_state
    with patch.object(mixed, "SAVE_EVERY", EVAL_EVERY):
        _, display = mixed.native_commands(bundle, TAG, resume is not None)
    ck = record / "ckpt" / probes.training.checkpoint_name(display, TAG)
    identity = dict(phase=phase, end_update=end, horizon=bundle.steps, share=share, profile_sha256=profile_sha,
                    shared_checkpoint_sha256=resume[1] if resume else None)
    standard_binding, standard_save = state_tools.make_binding, saves.save_packed_checkpoint

    def binding(plan, recipe, cache, device):
        return bind_pilot(plan, recipe, cache, device, make_binding=standard_binding,
                          expected_share=share, declared=declared)

    def save_owned(path, state):
        step = state["step"]
        if not start < step <= end or path.parent != ck.parent:
            raise ValueError("checkpoint destination or planned phase changed")
        state[PHASE_KEY] = dict(identity, end_update=step)
        standard_save(path, state)
        if path == ck:
            print(json.dumps(dict(phase=phase, saved_update=step)), file=progress, flush=True)
            if step == end:
                raise SavedBoundary()

    record.mkdir()
    print(json.dumps(dict(phase=phase, start=start, stop=end)), file=progress, flush=True)
    started = time.monotonic()
    with (patch.object(mixed, "TAG", TAG), patch.object(mixed, "SAVE_EVERY", EVAL_EVERY),
          patch.object(state_tools, "make_binding", binding),
          patch.object(saves, "save_packed_checkpoint", save_owned)):
        try:
            mixed.train_bundle(bundle, record, cutoff, flash=True, sft_share=share, decimal_weight=.02, resume_from=resume)
        except SavedBoundary:
            pass
        else:
            raise RuntimeError("native training continued past the sealed partial boundary")
    stamp, state = phase_checkpoint(ck, identity, torch)
    validation = state[mixed.trainer.CONTEXT_STATE_KEY]["control"]["history"][-1]
    anneal = state["cfg"]["quant_anneal"]
    del state
    updates = [json.loads(row) for row in (record / "updates.jsonl").read_text().splitlines()]
    if ([row["index"] for row in updates] != list(range(start, end))
            or [row["source_update"] for row in updates] != list(range(start, end))):
        raise ValueError("the native input cursor did not apply every planned contiguous update")
    for row in updates:
        raw_mass = row["raw_targets"] * row["ce_weights"][0]
        if not math.isclose(raw_mass, 1. if shared else 1.-share, abs_tol=1e-12):
            raise ValueError("the observed raw CE mass differs from its arm")
    result = dict(identity=identity, checkpoint=str(ck), sha256=stamp, validation=validation,
                  quant_anneal=anneal, seconds=time.monotonic()-started, updates=len(updates))
    native.publish(record / "phase.json", result)
    return dict(result, checkpoint=ck), updates


def evaluate(finished, rows, tokenizer, record, cutoff, torch, progress, phase):
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer

    _, state = phase_checkpoint(finished["checkpoint"], finished["identity"], torch)
    cfg = TMTConfig(**state["cfg"])
    cfg.infer_repeat = 2.0
    model = TiedMLPTransformer(cfg)
    body = {key:value for key,value in state["model"].items() if not key.startswith("decimal_head.")}
    model.load_state_dict(body, strict=True)
    del body, state
    model = model.to(device="cuda", dtype=torch.float32).eval()
    model.set_anneal(finished["quant_anneal"])
    if len(model.visit_schedule()) != 28:
        raise ValueError("the partial-checkpoint evaluation must use both R2 visits")
    model.freeze_quant()

    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the permitted evaluation period elapsed")

    outputs = []
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for offset in range(0, len(rows), panel.BATCH):
            outputs.extend(panel.predict(model, tokenizer, rows[offset:offset+panel.BATCH], torch, check))
            print(json.dumps(dict(phase=phase, evaluation_prompts=len(outputs))), file=progress, flush=True)
    summary = panel.aggregate(outputs)
    native.publish(record / "evidence_flip.json", dict(summary=summary, quant_anneal=finished["quant_anneal"], rows=outputs))
    return summary


def worker(profile, sha, _resume, out, cutoff):
    import torch

    sealed = json.loads(native.manifest_bytes(profile, sha))
    declared, bundle, tokenizer, rows = admission()
    if sealed != declared or torch.cuda.device_count() != 1:
        raise ValueError("the declared early-share pilot or GPU assignment changed")
    free,total = torch.cuda.mem_get_info()
    allowance = (native.CARD_LIMIT_MIB-384)*2**20-(total-free)
    if not 0 < allowance <= total:
        raise ValueError("no GPU budget for the native pilot")
    torch.cuda.set_per_process_memory_fraction(allowance/total)
    torch.set_num_threads(2)
    with ((out / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress,
          (out / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        releases = {}
        inputs = None
        parent = None
        for phase in ("shared", *SHARES):
            record = out / phase
            finished, updates = run_phase(bundle, record, cutoff, declared, native.digest(sha), phase, progress, torch, parent)
            releases[phase] = dict(finished, checkpoint=str(finished["checkpoint"]))
            if phase == "shared":
                parent = finished
            else:
                exposure = [{k:v for k,v in row.items() if k not in ("ce_weights", "decimal_correct")} for row in updates]
                if inputs is not None and exposure != inputs:
                    raise ValueError("the two CE coefficients received different input exposure")
                inputs = exposure
        for phase in SHARES:
            finished = dict(releases[phase], checkpoint=Path(releases[phase]["checkpoint"]))
            releases[phase]["evidence_flip_summary"] = evaluate(finished, rows, tokenizer, out/phase,
                                                                 cutoff, torch, progress, phase)
        bundle.unchanged()
        if any(prep.sha(prep.ROOT / name) != digest for name,digest in sealed["sources"].items()):
            raise ValueError("a sealed training or scoring source changed")
        native.publish(out / "report.json", dict(status="MATCHED_PARTIAL_TRAINING_COMPLETE", profile=sealed,
                       phases=releases, peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        declared, _, _, _ = admission()
        native.publish(args.profile, declared)
        print(prep.sha(args.profile), flush=True)
        return 0
    if (args.profile_sha256 is None or args.stop_by is None or args.stop_by.tzinfo is None
            or args.stop_by > probes.AUTHORIZATION_END or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"):
        parser.error("the exact profile, cutoff within the authorized window and CUDA device 0 are required")
    return probes.supervisor.supervise(worker, args.profile, args.profile_sha256, prep.EVIDENCE / TAG, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
