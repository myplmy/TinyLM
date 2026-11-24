"""Compare an entire real P109C update with dedicated and packed relation questions."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from functools import partial
import json
import math
from pathlib import Path
from statistics import median
import time
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p109b_ste_g4_cpu as optimizer_reference
from scripts import diag_p109c_relation_pack_segment_rope_flash as relative_rope
from scripts import diag_p109c_same_update_relation_pack_cpu as relation_pack
from scripts import p109_eval_resilient_supervisor as supervisor


TAG = "p109c_relation_pack_optimizer_cuda_v2_20261123"
mixed, readback = relation_pack.mixed, relation_pack.readback
ORDER = ("dedicated", "packed", "packed", "dedicated")


def make_batches(bundle):
    rows, counts, relation_count, decimal_count = readback.update_data(bundle, readback.UPDATE)
    relations = [row for row in rows if row[4] >= 0]
    if len(relations) != relation_count or any(row[5] for row in relations):
        raise ValueError("relation questions must preserve their membership and independent decimal events")
    x, y, segments = relation_pack.pack(relations)
    kinds = mixed.label_kinds(y, segments)
    winners = [row[4] for row in relations]
    for group, winner in enumerate(winners, 1):
        kinds[(segments == group) & (np.arange(x.shape[0])[:, None] != winner)] = 0
    combined = (x, y, segments, kinds, tuple(winners), (), True)
    dedicated, packed = [], []
    for x, y, segment, kind, gold, events in rows:
        baseline = (x, y, segment, kind, (gold,) if gold >= 0 else (), events, False)
        dedicated.append(baseline)
        if gold < 0:
            packed.append(baseline)
        elif not any(batch[-1] for batch in packed):
            packed.append(combined)
    for arm in (dedicated, packed):
        observed = [sum(int(np.count_nonzero(kind == i)) for _, _, _, kind, _, _, _ in arm if kind is not None)
                    for i in range(1, 4)]
        if observed != counts[1:] or sum(len(row[4]) for row in arm) != relation_count:
            raise ValueError("an optimizer arm changed the supervision weight denominators")
    return {"dedicated": dedicated, "packed": packed}, counts, relation_count, decimal_count


def objective(model, row, counts, relation_count, decimal_count):
    inputs, labels, segments, kinds, winners, events, packed = row
    x, y = (torch.as_tensor(values.astype(np.int64), device="cuda") for values in (inputs, labels))
    if segments is None:
        nll, _ = mixed.target_nll(model, model(x, return_hidden=True), y, rows=1024)
        return nll.sum() * (.75 / counts[0])
    if packed:
        hidden = relative_rope.relative_hidden(model, x, segments, flash=True, hidden=mixed.masked_hidden)
    else:
        hidden = mixed.masked_hidden(model, x, segments, flash=True)
    positions = torch.as_tensor(np.flatnonzero(labels.ravel() != mixed.prep.IGNORE), device="cuda")
    nll, valid = mixed.prior.course_target_nll(model, hidden, y, 2048, positions)
    kind = torch.as_tensor(kinds, device="cuda")
    value = sum(nll[kind == i].sum() * (.25 * weight / counts[i])
                for i, weight in enumerate(mixed.KIND_WEIGHTS, 1))
    if winners:
        segment_ids = torch.as_tensor(segments, device="cuda")
        for group, winner in enumerate(winners, 1):
            content = valid & y.ne(mixed.prep.END) & segment_ids.eq(group)
            score = -(nll * content).sum(1) / content.sum(1)
            value = value + mixed.prior.contrast_row(score, winner) * (
                mixed.prior.role_loss.WEIGHTS["ALL_AXES"] / relation_count)
    if events:
        r, c = torch.as_tensor([event[:2] for event in events], device="cuda").T
        aux, count, _, _ = mixed.prior.joint_decimal.objective(
            model.decimal_head, hidden[r, c, None], y[r, c, None], [event[2] for event in events], [[0]] * len(events))
        if count != len(events):
            raise ValueError("the full step lost decimal labels")
        value = value + aux * (.02 / decimal_count)
    return value


def update(model, checkpoint, batches, counts, relations, decimals, capture, cutoff):
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    model.load_state_dict(state["model"], strict=True)
    model.zero_grad(set_to_none=True)
    model.clear_quant()
    model.set_anneal(1.)
    split_original = optimizer_reference.split_params

    def split(model):
        matrices, rest = split_original(model)
        head = model.decimal_head.weight
        return [parameter for parameter in matrices if parameter is not head], [*rest, head]

    with patch.object(optimizer_reference, "split_params", split):
        adamw, muon, _ = optimizer_reference.optimizers(model)
    adamw.load_state_dict(state["opt"])
    muon.load_state_dict(state["opt_muon"])
    cache = mixed.UpdateQuantizationReuse(model)
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    objective_value = 0.
    forwards = 0
    with patch.object(model, "refresh_quant", cache.refresh):
        for row in batches:
            if time.time() >= cutoff:
                raise TimeoutError("the approved full-step comparison ended")
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss = objective(model, row, counts, relations, decimals)
            objective_value += float(loss.detach())
            loss.backward()
            forwards += 1
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
    adamw.step()
    muon.step()
    torch.cuda.synchronize()
    elapsed = time.perf_counter()-started
    if forwards != len(batches) or not math.isfinite(objective_value):
        raise ValueError("an actual training forward or finite loss was lost")
    stats = dict(seconds=elapsed, unclipped_norm=float(norm), mixed_objective=objective_value,
                 physical_slots=sum(row[0].size for row in batches), training_forwards=forwards,
                 peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20)
    changes = {name: value.detach().cpu() - state["model"][name] for name,value in model.named_parameters()} if capture else {}
    model.clear_quant()
    return stats, changes


def compare_changes(reference, other):
    if reference.keys() != other.keys():
        raise ValueError("optimizer step coverage changed")
    inner = readback.gradients.inner
    differences = [reference[name] - other[name] for name in reference]
    values = list(reference.values())
    return dict(relative_l2=math.sqrt(inner(differences, differences) / inner(values, values)),
                max_absolute=max(float(value.abs().max()) for value in differences))


def worker(training, sources, manifest, digest, _resume, record, cutoff):
    with (record/"stdout.txt").open("x", encoding="utf-8", buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
        if any(mixed.prep.sha(f)!=h for f,h in sources.items()) or torch.cuda.device_count()!=1:
            raise ValueError("the pinned source files and exactly one authorized GPU are required")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        free,total = torch.cuda.mem_get_info()
        allowed = (mixed.native.CARD_LIMIT_MIB-384)*2**20-(total-free)
        if not 0 < allowed <= total:
            raise ValueError("the active GPU envelope leaves no allocation budget")
        torch.cuda.set_per_process_memory_fraction(allowed/total)
        bundle = mixed.Bundle(manifest,digest)
        batches, counts, relations, decimals = make_batches(bundle)
        model, checkpoint, export_sha, step = readback.load_checkpoint(training,bundle.digest)
        native_sha = mixed.prep.sha(checkpoint)
        model.to("cuda")
        scored = {arm: [] for arm in batches}
        changes = {arm: [] for arm in batches}
        with (record/"progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress:
            for index,arm in enumerate((*batches,*ORDER)):
                timed = index >= len(batches)
                print(json.dumps(dict(arm=arm, timed=timed)),file=progress,flush=True)
                stats, delta = update(model, checkpoint, batches[arm], counts, relations, decimals, timed, cutoff)
                if timed:
                    scored[arm].append(stats)
                    changes[arm].append(delta)
                print(arm,stats,flush=True)
        before,after = changes["dedicated"],changes["packed"]
        within = {arm: compare_changes(*attempts) for arm, attempts in changes.items()}
        across = [dict(dedicated_try=i, packed_try=j, **compare_changes(left, right))
                  for i, left in enumerate(before, 1) for j, right in enumerate(after, 1)]
        if mixed.prep.sha(checkpoint) != native_sha:
            raise ValueError("the starting model changed")
        bundle.unchanged()
        mixed.native.publish(record/"report.json",dict(status="FULL_MIXED_OPTIMIZER_STEP_COMPARISON_COMPLETE",
            tag=TAG, checkpoint_sha256=native_sha, export_sha256=export_sha, stored_step=step,
            source_update=readback.UPDATE+1, input_manifest_sha256=bundle.digest, counts=counts,
            relation_questions=relations, decimal_targets=decimals, optimizer_updates=6, saved_new_model=False,
            arms=scored, seconds_median={k:median(r["seconds"] for r in arm) for k,arm in scored.items()},
            weight_update_rel_l2=across[0]["relative_l2"],
            max_abs_weight_update_difference=across[0]["max_absolute"],
            within_route=within, between_routes=across,
            sources={str(f):h for f,h in sources.items()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("training","manifest","record"):
        parser.add_argument("--"+option,required=True,type=Path)
    for option in ("manifest-sha256","source-sha256"):
        parser.add_argument("--"+option,required=True)
    parser.add_argument("--stop-by",required=True,type=datetime.fromisoformat)
    args=parser.parse_args()
    own=Path(__file__).resolve()
    files=[own]+[Path(module.__file__).resolve() for module in (optimizer_reference,relative_rope,relation_pack,mixed,readback)]
    sources={file:mixed.prep.sha(file) for file in files}
    record=args.record.absolute()
    if args.stop_by.tzinfo is None or sources[own]!=mixed.native.digest(args.source_sha256) or record.exists() or record.is_symlink():
        parser.error("the sealed comparison source, approved cutoff and fresh record are required")
    target=partial(worker,args.training.absolute(),sources)
    return supervisor.supervise(target,args.manifest.absolute(),args.manifest_sha256,record,args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
