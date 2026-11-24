"""Check the bilingual auxiliary losses on identical native examples before and after packing."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from functools import partial
import json
import math
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from scripts import diag_p109c_relation_pack_optimizer_cuda as compare
from scripts import run_p109c_bilingual_mixed as combined
from scripts import run_p109c_bilingual_value_transfer as original


TAG = "p109c_bilingual_aux_packed_native_v1_20261124"
UPDATE = 157
AUTHORITY = datetime.fromisoformat("2026-11-25T17:00:00+09:00")
prep, native, mixed = combined.prep, combined.native, combined.mixed


def selections(tokens, sites, context, answers, rows, offsets, lengths):
    columns = np.arange(context.shape[1])[None, :]
    present = columns < lengths[:, None]
    context_row, context_pos = np.nonzero(context != prep.IGNORE)
    answer_row, answer_pos = np.nonzero(answers != prep.IGNORE)
    if (not np.all(present[context_row, context_pos]) or not np.all(present[answer_row, answer_pos])
            or np.any((context != prep.IGNORE) & (answers != prep.IGNORE))
            or np.any(sites[:, :5] >= lengths[:, None]) or np.any(sites[:, :5] < 0)
            or not np.array_equal(tokens[context_row, context_pos+1], context[context_row, context_pos])):
        raise ValueError("the auxiliary targets must stay in their original causal example")
    return dict(rows=rows, sites=sites[:, :5]+offsets[:, None], value_classes=sites[:, 5],
                context_rows=rows[context_row], context_pos=context_pos+offsets[context_row],
                context_targets=context[context_row, context_pos],
                answer_rows=rows[answer_row], answer_pos=answer_pos+offsets[answer_row],
                answer_targets=answers[answer_row, answer_pos])


def prepare(layout, layout_sha):
    profile = json.loads(native.manifest_bytes(layout, layout_sha))
    placement = profile["placements"][UPDATE-101]
    pair_source = combined.placement.PAIR_SOURCE
    if placement["update"] != UPDATE or prep.sha(pair_source) != profile["pair_archive_sha256"]:
        raise ValueError("the approved bilingual source and absolute placement differ")
    with np.load(pair_source, allow_pickle=False) as archive:
        tokens, labels = archive["tokens"], archive["labels"]
        lengths = np.where((tokens!=0) | (labels!=prep.IGNORE), np.arange(tokens.shape[1])+1, 0).max(1)
        packed = np.zeros(mixed.PACK_SHAPE, dtype=prep.DTYPE)
        packed[:, 1] = prep.IGNORE
        seen = set()
        combined.packed_pairs(packed, placement, tokens, labels, lengths, seen)
        pair, first_row, ko_offset, en_offset = np.asarray(placement["pairs"], dtype=np.int64).T
        index = (pair[:, None]*2 + np.arange(2)).ravel()
        n = int(lengths[index].max())
        x, y, ctx, sites = (tokens[index, :n], labels[index, :n], archive["context"][index, :n], archive["sites"][index])
        size = lengths[index]
        choices, unique = archive["options"][pair], archive["unique"][pair]
        target = archive["targets"][pair].astype(np.int64)
        gold = choices[np.arange(len(pair)), target]
        if (not np.array_equal(y[np.arange(len(index)), sites[:, 0]], np.repeat(gold, 2))
                or not unique[np.arange(len(pair)), target].all() or len(seen) != len(pair)):
            raise ValueError("the position and first token targets lost their separate original classes")
    px, py, seg = packed.transpose(1, 0, 2)
    kept = int(max(placement["row_widths"]))
    rows = (first_row[:, None]+np.arange(2)).ravel()
    offsets = np.column_stack((ko_offset, en_offset)).ravel()
    src = selections(x, sites, ctx, y, np.arange(len(index)), np.zeros(len(index), dtype=np.int64), size)
    dst = selections(x, sites, ctx, y, rows, offsets, size)
    if (not np.array_equal(py[dst["answer_rows"], dst["answer_pos"]], dst["answer_targets"])
            or not np.array_equal(px[dst["context_rows"], dst["context_pos"]+1], dst["context_targets"])
            or not np.array_equal(seg[rows[:, None], dst["sites"]], np.repeat(np.arange(1,len(pair)+1),2)[:,None]+np.zeros((1,5)))):
        raise ValueError("a packed target crossed into another example")
    different_target_class = int(np.count_nonzero(sites[::2, 5] != target))
    if different_target_class == 0:
        raise ValueError("the comparison must exercise nonidentical position and token target classes")
    source_segments = (np.arange(n)[None, :] < size[:, None]).astype(np.int16)
    return (x, source_segments, src), (px[:, :kept], seg[:, :kept], dst), dict(
        pairs=len(pair), context_targets=len(dst["context_targets"]), answer_targets=len(dst["answer_targets"]),
        position_targets=len(index), different_target_class=different_target_class,
        packed_shape=px[:, :kept].shape, independent_shape=x.shape, choices=choices, unique=unique, gold=gold)


def measure(model, selector, case, metadata, local=True):
    input_ids, segments, selection = case
    x = torch.tensor(input_ids, dtype=torch.long, device="cuda")
    order = {key:torch.tensor(value, dtype=torch.long, device=x.device) for key,value in selection.items()}
    vocab = model.cfg.vocab_size
    choices = torch.as_tensor(metadata["choices"], device=x.device, dtype=torch.long)
    unique = torch.as_tensor(metadata["unique"], device=x.device, dtype=torch.bool)
    gold = torch.as_tensor(metadata["gold"], device=x.device, dtype=torch.long)
    model.clear_quant()
    with torch.autocast("cuda", dtype=torch.bfloat16):
        hidden = (combined.relative.relative_hidden(model, x, segments, flash=True, hidden=mixed.masked_hidden)
                  if local else mixed.masked_hidden(model, x, segments, flash=True))
        features = hidden[order["rows"][:, None], order["sites"]]
        sites = torch.arange(5, device=x.device).expand(len(features), 5)
        location = selector(features, sites).float()
        position = F.cross_entropy(location, order["value_classes"], reduction="mean")
        first = model._head_logits(features[:, :1]).squeeze(1).float()
        if first.shape != (len(features), vocab):
            raise ValueError("the first-token gate requires the full vocabulary logits")
        transfer, n_transfers = original.selected_transfer(first, choices, unique, gold,
                                                            location.detach().argmax(1)==order["value_classes"])
        losses = []
        for name in ("answer", "context"):
            values = hidden[order[name+"_rows"], order[name+"_pos"]].unsqueeze(0)
            targets = order[name+"_targets"].unsqueeze(0)
            nll, _ = mixed.target_nll(model, values, targets, rows=512)
            losses.append(nll.mean())
        objective = losses[0]+losses[1]*.01+position*.02+transfer*.1/len(gold)
    parameters = tuple(p for p in (*model.parameters(), *selector.parameters()) if p.requires_grad)
    gradients = torch.autograd.grad(objective, parameters, allow_unused=True)
    report = dict(answer_nll=float(losses[0].detach()), context_nll=float(losses[1].detach()),
                  value_link_ce=float(position.detach()), transfer_pairs=int(n_transfers),
                  predicted_first=first.detach().argmax(1).tolist(), predicted_position=location.detach().argmax(1).tolist(),
                  backward_only=True)
    return report, location.detach().cpu(), [g.detach().cpu() if g is not None else None for g in gradients]


def worker(training, layout, layout_sha, pins, manifest, manifest_sha, _resume, record, cutoff):
    with (record/"stdout.txt").open("x", encoding="utf-8", buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
        if any(prep.sha(Path(p)) != expected for p,expected in pins.items()) or torch.cuda.device_count()!=1:
            raise ValueError("one approved GPU and pinned code are required")
        torch.set_num_threads(2)
        free,total = torch.cuda.mem_get_info()
        budget = (native.CARD_LIMIT_MIB-384)*2**20-(total-free)
        if not 0 < budget <= total:
            raise ValueError("no CUDA budget for the actual packed diagnostic")
        torch.cuda.set_per_process_memory_fraction(budget/total)
        independent, packed, metadata = prepare(layout, layout_sha)
        model, checkpoint, export_sha, step = compare.readback.load_checkpoint(training, manifest_sha)
        checkpoint_sha = prep.sha(checkpoint)
        model.to("cuda")
        torch.manual_seed(109157)
        selector = original.baseline.ValueLink(model.cfg.dim).to("cuda")
        original.verify_loss()
        results = {}
        reference_vectors = reference_gradients = None
        with (record/"progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress:
            order = (("independent_local", independent, True), ("packed_global", packed, False),
                     ("packed_local", packed, True), ("packed_local_repeat", packed, True))
            kept_gradients = None
            for name, case, local in order:
                if datetime.now().timestamp() >= cutoff:
                    raise TimeoutError("the declared CUDA experiment window elapsed")
                print(json.dumps({"arm":name}), file=progress, flush=True)
                torch.cuda.reset_peak_memory_stats()
                stats, vectors, gradients = measure(model, selector, case, metadata, local=local)
                stats["peak_allocated_mib"] = torch.cuda.max_memory_allocated()/2**20
                if name == "independent_local":
                    reference_vectors, reference_gradients = vectors, gradients
                else:
                    if any((a is None)!=(b is None) for a,b in zip(reference_gradients,gradients,strict=True)):
                        raise ValueError("packing changed which parameters the auxiliary losses supervise")
                    inner = compare.readback.gradients.inner
                    delta = [a-b if a is not None else None for a,b in zip(reference_gradients,gradients,strict=True)]
                    stats.update(max_position_logit_delta=float((reference_vectors-vectors).abs().max()),
                                 gradient_relative_l2=math.sqrt(inner(delta,delta)/inner(reference_gradients,reference_gradients)),
                                 same_first=stats["predicted_first"]==results["independent_local"]["predicted_first"],
                                 same_positions=stats["predicted_position"]==results["independent_local"]["predicted_position"])
                if name == "packed_local":
                    kept_gradients = gradients
                if name == "packed_local_repeat":
                    difference = [a-b if a is not None else None for a,b in zip(kept_gradients,gradients,strict=True)]
                    stats["within_local_gradient_relative_l2"] = math.sqrt(inner(difference,difference)/inner(kept_gradients,kept_gradients))
                results[name] = stats
        if prep.sha(checkpoint) != checkpoint_sha:
            raise ValueError("the original checkpoint changed")
        native.publish(record/"report.json",dict(status="ACTUAL_BILINGUAL_PACKED_AUXILIARY_BACKWARD_MEASURED",
            source_update=UPDATE, source_checkpoint_sha256=checkpoint_sha, source_export_sha256=export_sha,
            source_step=step, selector_init_seed=109157, optimizer_updates=0, sources=pins,
            counts={k:v for k,v in metadata.items() if k not in ("choices","unique","gold")}, arms=results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("training","layout","manifest","record"):
        parser.add_argument("--"+name, type=Path, required=True)
    for name in ("layout-sha256","manifest-sha256","source-sha256"):
        parser.add_argument("--"+name, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    own = Path(__file__).resolve()
    modules = (compare,compare.readback,compare.supervisor,combined,combined.relative,mixed,original,original.baseline)
    paths = {own, *(Path(module.__file__).resolve() for module in modules)}
    pins = {str(path):prep.sha(path) for path in sorted(paths)}
    record = args.record.absolute()
    if (args.stop_by.tzinfo is None or args.stop_by>AUTHORITY or not record.is_relative_to(prep.EVIDENCE)
            or record.exists() or record.is_symlink() or pins[str(own)]!=native.digest(args.source_sha256)):
        parser.error("the planned source, cutoff and fresh output must match")
    task = partial(worker,args.training.absolute(),args.layout.absolute(),args.layout_sha256,pins)
    return compare.supervisor.supervise(task,args.manifest.absolute(),args.manifest_sha256,record,args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
