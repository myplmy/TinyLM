"""Measure the first-token gate's necessary conditions before training a value head."""

import argparse
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import torch

from scripts import eval_p109c_mixed_v2 as v2
from scripts import p109c_bilingual_terms as terms
from scripts import run_p109c_early_course_share as early
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer


inputs, prep, mixed, native = terms.inputs, terms.prep, terms.mixed, terms.inputs.native
TAG = "p109c_early_bilingual_gate_v2_20261124"
TRAINED = v2.original.ROOT / "test_result/evidence/p109c_scratch_mixed_v2_v11_chat32_s1337_run1_20261123"
EARLY = prep.EVIDENCE / early.TAG
# Sample across the first 256 mixed addresses and leave the previous single-address test out.
ADDRESSES = tuple(range(101, 356, 8))


def prepare():
    bundle, proof = inputs.load_inputs()
    slots = terms.BilingualSlots(bundle, proof["layout_sha256"])
    candidates = [(address, slots.at(address)) for address in ADDRESSES]
    end = prep.read_json(EARLY / "supervisor.json")
    if (end["returncode"] or end["stop_reason"] is not None or end["card_after_exit"]["compute_pids"]):
        raise ValueError("the partial checkpoint trial did not close with a returned device")
    prior = prep.read_json(EARLY / "report.json")
    models = {phase: prior["phases"][phase] for phase in ("flat", "lowered")}
    if (prior["status"] != "MATCHED_PARTIAL_TRAINING_COMPLETE"
            or len({model["identity"]["shared_checkpoint_sha256"] for model in models.values()}) != 1):
        raise ValueError("the early arms must use one identical unparented prefix")
    with patch.object(native, "STEPS", bundle.steps):
        checkpoint, digest = v2.completed_v2(TRAINED, bundle.digest)
    models["v2"] = dict(checkpoint=str(checkpoint), sha256=digest, quant_anneal=1.)
    pinned = inputs.sources()
    files = tuple(Path(m.__file__).resolve() for m in (terms, terms.audited, early, v2)) + (Path(__file__).resolve(),)
    for path in files:
        pinned[str(path.relative_to(prep.ROOT))] = prep.sha(path)
    return (dict(tag=TAG, sources=pinned, inputs=proof, models=models, routes="LOCAL_SEGMENT_UNIFORM_R2_BF16",
                 addresses=[address+1 for address, _ in candidates], pairs=sum(len(row.gold) for _, row in candidates)),
            bundle, candidates)


def load_model(name, record):
    checkpoint = Path(record["checkpoint"])
    if name == "v2":
        digest = prep.sha(checkpoint)
        stored = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    else:
        digest, stored = early.phase_checkpoint(checkpoint, record["identity"], torch)
    if digest != record["sha256"]:
        raise ValueError("the declared model export changed")
    cfg = TMTConfig(**stored["cfg"])
    model = TiedMLPTransformer(cfg)
    model.load_state_dict({k:v for k,v in stored["model"].items() if not k.startswith("decimal_head.")}, strict=True)
    model = model.to("cuda").eval()
    model.set_anneal(record["quant_anneal"])
    model.freeze_quant()
    return model


def gate_rows(model, batches, bundle, cutoff):
    rows = []
    counts = Counter()
    route = list(mixed.routed.route_for(model.cfg, model.owner, "uniform_r2", 1337, 0, bundle.steps))
    with (patch.object(model, "visit_schedule", return_value=route), torch.inference_mode(),
          torch.autocast("cuda", dtype=torch.bfloat16)):
        for address, targets in batches:
            if time.time() >= cutoff:
                raise TimeoutError("the sealed gate measure reached its GPU limit")
            x, _, segments = bundle.data[-1][address-bundle.warmup].transpose(1, 0, 2)
            width = int(np.count_nonzero(segments, axis=1).max())
            ids = torch.as_tensor(x[:, :width].astype(np.int64), device="cuda")
            hidden = bundle.packed_hidden(model, ids, segments[:, :width], flash=True, hidden=mixed.masked_hidden)
            first = model._head_logits(targets.features(hidden)[:, 0]).float().reshape(len(targets.gold), 2, -1)
            choices, unique, gold = targets.candidates(first.device)
            if first.shape[2] != model.cfg.vocab_size or not bool(torch.isfinite(first).all()):
                raise ValueError("expected one finite full-vocabulary prediction per answer site")
            best = first.argmax(dim=2)
            allowed = first.gather(2, choices[:, None, :].expand(-1, 2, -1)).masked_fill(~unique[:, None, :], -torch.inf)
            constrained = choices.gather(1, allowed.argmax(dim=2))
            a, b = best.eq(gold[:, None]).T
            c, d = constrained.eq(gold[:, None]).T
            distinct = unique.sum(1) > 1
            totals = dict(pairs=len(gold), ko_full=int(a.sum()), en_full=int(b.sum()),
                          ko_choice=int(c.sum()), en_choice=int(d.sum()),
                          full_gate_upper=int((b & ~a & distinct).sum()),
                          choice_gate_upper=int((d & ~a & distinct).sum()),
                          choice_gate_wrong_EN=int((~d & ~a & distinct).sum()))
            rows.append(dict(source_update=address+1, counts=totals, gold=gold.tolist(),
                             full_argmax=best.tolist(), candidate_argmax=constrained.tolist()))
            counts.update(totals)
    return dict(counts), rows


def worker(path, expected, _resume, record, cutoff):
    sealed = json.loads(native.manifest_bytes(path, expected))
    actual, bundle, candidates = prepare()
    if actual != sealed or torch.cuda.device_count() != 1:
        raise ValueError("the declared gate evaluation changed")
    torch.set_num_threads(2)
    free, total = torch.cuda.mem_get_info()
    budget = (native.CARD_LIMIT_MIB-384)*2**20-(total-free)
    if not 0 < budget <= total:
        raise ValueError("no GPU budget for the frozen gate comparison")
    torch.cuda.set_per_process_memory_fraction(budget/total)
    results = {}
    with (record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as journal:
        for name, source in sealed["models"].items():
            model = load_model(name, source)
            counts, rows = gate_rows(model, candidates, bundle, cutoff)
            if counts["pairs"] != sealed["pairs"]:
                raise ValueError("the gate comparison lost a bilingual pair")
            native.publish(record / f"{name}.json", dict(counts=counts, rows=rows))
            results[name] = counts
            print(json.dumps(dict(model=name, pairs=counts["pairs"])), file=journal, flush=True)
            del model
    bundle.unchanged()
    native.publish(record / "report.json", dict(status="FIRST_TOKEN_GATE_UPPER_BOUND_MEASURED", input=sealed,
                   results=results, value_head=False, optimizer_updates=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        plan, _, _ = prepare()
        native.publish(args.profile, plan)
        print(prep.sha(args.profile), plan["pairs"], flush=True)
        return 0
    if (args.profile_sha256 is None or args.stop_by is None or args.stop_by.tzinfo is None
            or args.stop_by > inputs.AUTHORIZATION_END or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"):
        parser.error("the exact profile, approved cutoff and GPU 0 are required")
    return inputs.supervisor.supervise(worker, args.profile, args.profile_sha256, prep.EVIDENCE / TAG, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
