"""Measure the cost of executing the empty slots of one sealed P109C update."""

import argparse
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from functools import partial
import json
from pathlib import Path
from statistics import median
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p109c_relation_pack_optimizer_cuda as comparison
from scripts import run_p109c_bilingual_mixed as combined


TAG = "p109c_padding_zero_backward_cuda_v1_20261124"
UPDATE = 152
ORDER = ("full_padding", "zero_backward", "zero_backward", "full_padding")
AUTHORITY = datetime.fromisoformat("2026-11-25T17:00:00+09:00")
mixed, prep, native = combined.mixed, combined.prep, combined.native


def prepare(manifest, manifest_sha, layout, layout_sha):
    bundle = mixed.Bundle(manifest, manifest_sha)
    original_padding = bundle.schedule[:, :, 0] == -2
    packed = combined.attach(bundle, layout, layout_sha)
    schedule = bundle.schedule[UPDATE]
    raw = iter(bundle.raw_batch(schedule[schedule[:, 0] == -1, 1]))
    shape = (prep.BATCH, prep.WIDTH)
    padding = (np.zeros(shape, dtype=np.int16), np.full(shape, prep.IGNORE, dtype=np.int16),
               None, None, (), (), False)
    rows = []
    counts = np.zeros(4, dtype=np.int64)
    relation_count = decimal_count = 0
    for lane, index in schedule:
        if lane == -1:
            tokens = next(raw)
            rows.append((tokens[:, :-1], tokens[:, 1:], None, None, (), (), False))
            counts[0] += mixed.MICRO_TOKENS
        elif lane == -2:
            rows.append(padding)
        else:
            x, y, segments = bundle.data[lane][index].transpose(1, 0, 2)
            aux = bundle.aux[lane][index]
            groups = combined.relation_objective.relation_groups_for(aux, prep.BATCH)
            kinds = mixed.label_kinds(y, segments)
            combined.relation_objective.keep_relation_winners(kinds, segments, groups)
            counts[1:] += np.bincount(kinds.ravel(), minlength=4)[1:]
            events = aux["decimal"]
            relation_count += len(groups)
            decimal_count += len(events)
            rows.append((x, y, segments, kinds, tuple(gold for _, gold in groups), events, len(groups) > 1))
    padding_count = sum(row is padding for row in rows)
    if (len(rows) != prep.ACCUM or not padding_count or not all(counts) or not decimal_count
            or relation_count < 2 or sum(r[0].size for r in rows) != prep.ACCUM * mixed.MICRO_TOKENS):
        raise ValueError("the exact mixed update must exercise original supervision and empty slots")
    packed_padding = bundle.schedule[:, :, 0] == -2
    padding_by_update = Counter(np.count_nonzero(packed_padding, axis=1).tolist())
    padding_total = int(np.count_nonzero(packed_padding))
    receipt = dict(source_update=UPDATE+1, raw_and_positive_counts=counts.tolist(), relations=relation_count,
                   decimal_targets=decimal_count, update_padding=padding_count,
                   padding_by_update=dict(sorted(padding_by_update.items())),
                   original_padding_microbatches=int(np.count_nonzero(original_padding)),
                   additional_padding_microbatches=int(np.count_nonzero(packed_padding & ~original_padding)),
                   padding_microbatches=padding_total, padding_slots=padding_total * mixed.MICRO_TOKENS,
                   admitted_inputs=packed)
    return bundle, rows, padding, receipt


def padding_objective(ordinary, padding, zero_backward, calls):
    def compute(model, row, *counts):
        if row is not padding:
            return ordinary(model, row, *counts)
        calls["padding"] += 1
        if zero_backward:
            return torch.zeros((), dtype=torch.float32, device="cuda", requires_grad=True)
        calls["padding_model"] += 1
        tokens = torch.as_tensor(row[0], dtype=torch.long, device="cuda")
        return model(tokens, return_hidden=True).sum() * 0.
    return compute


def worker(training, layout, layout_sha, sources, manifest, manifest_sha, _resume, record, cutoff):
    with (record/"stdout.txt").open("x", encoding="utf-8", buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
        if any(prep.sha(Path(path)) != sha for path, sha in sources.items()) or torch.cuda.device_count() != 1:
            raise ValueError("the comparison requires all pinned files and one CUDA device")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        free, total = torch.cuda.mem_get_info()
        allowed = (native.CARD_LIMIT_MIB-384)*2**20-(total-free)
        if not 0 < allowed <= total:
            raise ValueError("the current GPU envelope leaves no allocation budget")
        torch.cuda.set_per_process_memory_fraction(allowed/total)
        bundle, rows, padding, receipt = prepare(manifest, manifest_sha, layout, layout_sha)
        model, checkpoint, export_sha, step = comparison.readback.load_checkpoint(training, bundle.digest)
        native_sha = prep.sha(checkpoint)
        model.to("cuda")
        counts = receipt["raw_and_positive_counts"], receipt["relations"], receipt["decimal_targets"]
        scored = {arm: [] for arm in ("full_padding", "zero_backward")}
        deltas = {arm: [] for arm in scored}
        ordinary = comparison.objective
        clip = torch.nn.utils.clip_grad_norm_
        covered = []

        def observe_clip(iterable, *args, **kwargs):
            parameters = tuple(iterable)
            covered.append(tuple(parameter.grad is not None for parameter in parameters))
            return clip(parameters, *args, **kwargs)

        with (record/"progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress:
            for index, arm in enumerate((*scored, *ORDER)):
                timed = index >= len(scored)
                calls = Counter()
                zero = arm == "zero_backward"
                objective = padding_objective(ordinary, padding, zero, calls)
                print(json.dumps(dict(arm=arm, timed=timed)), file=progress, flush=True)
                with (patch.object(comparison, "objective", objective),
                      patch.object(torch.nn.utils, "clip_grad_norm_", observe_clip)):
                    stats, delta = comparison.update(model, checkpoint, rows, *counts, timed, cutoff)
                if (calls["padding"] != receipt["update_padding"]
                        or calls["padding_model"] != (0 if zero else receipt["update_padding"])):
                    raise ValueError("the number of calls for the padded slots changed")
                stats["scheduled_microbatches"] = stats.pop("training_forwards")
                stats.update(padding_backwards=calls["padding"], padding_model_forwards=calls["padding_model"])
                if timed:
                    scored[arm].append(stats)
                    deltas[arm].append(delta)
                print(arm, stats, flush=True)
        if not all(mask == covered[0] for mask in covered) or prep.sha(checkpoint) != native_sha:
            raise ValueError("parameter gradient coverage or starting checkpoint changed")
        within = {arm: comparison.compare_changes(*changes) for arm, changes in deltas.items()}
        across = [comparison.compare_changes(a, b) for a in deltas["full_padding"] for b in deltas["zero_backward"]]
        bundle.unchanged()
        native.publish(record/"report.json", dict(status="PADDING_ABBA_MEASURED", tag=TAG,
            training_record=str(training), starting_checkpoint_sha256=native_sha, export_sha256=export_sha,
            stored_step=step, preparation=receipt, order=ORDER, warmups=2, actual_optimizer_updates=len(covered),
            saved_new_model=False, arms=scored, gradient_presence_equal=True,
            parameters_with_gradient=sum(covered[0]), within_arm=within, across_arms=across,
            median_seconds={key:median(sample["seconds"] for sample in arm) for key, arm in scored.items()},
            sources=sources))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("training", "manifest", "layout", "record"):
        parser.add_argument("--"+option, required=True, type=Path)
    for option in ("manifest-sha256", "layout-sha256", "source-sha256"):
        parser.add_argument("--"+option, required=True)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    paths = list(combined.sources()) + [str(Path(module.__file__).resolve().relative_to(prep.ROOT))
            for module in (comparison, comparison.readback, comparison.optimizer_reference, comparison.supervisor)]
    own = str(Path(__file__).resolve().relative_to(prep.ROOT))
    sources = {str(prep.ROOT / path):prep.sha(prep.ROOT / path) for path in (own, *paths)}
    record = args.record.absolute()
    if (args.stop_by.tzinfo is None or args.stop_by > AUTHORITY or not record.is_relative_to(prep.EVIDENCE)
            or record.exists() or record.is_symlink()
            or sources[str(prep.ROOT / own)] != native.digest(args.source_sha256)):
        parser.error("the comparison requires an approved cutoff, fresh evidence path and exact new source")
    target = partial(worker,args.training.absolute(),args.layout.absolute(),args.layout_sha256,sources)
    return comparison.supervisor.supervise(target,args.manifest.absolute(),args.manifest_sha256,record,args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
