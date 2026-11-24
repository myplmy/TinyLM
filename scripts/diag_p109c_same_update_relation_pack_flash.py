"""Compare three layouts of the same real relation questions with BF16 Flash."""

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

from scripts import diag_p109c_same_update_relation_pack_cpu as comparison
from scripts import p109_eval_resilient_supervisor as supervisor


TAG = "p109c_same_update_relation_pack_flash_v1_20261123"
mixed, readback = comparison.mixed, comparison.readback
ORDER = ("dedicated", "packed_fixed", "packed_trimmed", "packed_trimmed", "packed_fixed", "dedicated")


def layouts(bundle):
    rows, counts, groups, _ = readback.update_data(bundle, readback.UPDATE)
    relations = [row for row in rows if row[4] >= 0]
    if len(relations) != groups or any(row[5] for row in relations):
        raise ValueError("the actual update does not match the relation-only comparison")
    cropped = comparison.pack(relations)
    width_left = mixed.prep.WIDTH - cropped[0].shape[1]
    fixed = tuple(np.pad(array, ((0, 0), (0, width_left)), constant_values=value)
                  for array, value in zip(cropped, (0, mixed.prep.IGNORE, 0), strict=True))
    gold = [row[4] for row in relations]
    for group, (x, y, old_segments, _, _, _) in enumerate(relations, 1):
        for lane in range(mixed.prep.BATCH):
            active = cropped[2][lane] == group
            if not (np.array_equal(cropped[0][lane, active], x[lane, old_segments[lane] != 0])
                    and np.array_equal(cropped[1][lane, active], y[lane, old_segments[lane] != 0])):
                raise ValueError("packing changed an input ID or supervised position")
    return {"dedicated": [(row[0], row[1], row[2], [row[4]]) for row in relations],
            "packed_fixed": [(*fixed, gold)], "packed_trimmed": [(*cropped, gold)]}, counts


def worker(training, sources, path, sha, _unused, record, cutoff):
    if any(mixed.prep.sha(item) != key for item, key in sources.items()) or torch.cuda.device_count() != 1:
        raise ValueError("the pinned comparison sources and one authorized GPU are required")
    with (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        free, total = torch.cuda.mem_get_info()
        cap = (mixed.native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
        if not 0 < cap <= total:
            raise RuntimeError("the approved card envelope leaves no allocation budget")
        torch.cuda.set_per_process_memory_fraction(cap / total)
        bundle = mixed.Bundle(path, sha)
        batches, counts = layouts(bundle)
        model, checkpoint, export_sha, step = readback.load_checkpoint(training, bundle.digest)
        original_sha = mixed.prep.sha(checkpoint)
        model.to("cuda")
        readings, reference = {key: [] for key in batches}, None
        with (record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress:
            for index, name in enumerate((*batches, *ORDER)):
                warmed = index >= len(batches)
                print(json.dumps(dict(index=index, arm=name, timed=warmed)), file=progress, flush=True)
                torch.cuda.reset_peak_memory_stats()
                cache = mixed.UpdateQuantizationReuse(model)
                with patch.object(model, "refresh_quant", cache.refresh):
                    result, gradient = comparison.measure(model, batches[name], counts, cutoff,
                                                           device="cuda", flash=True)
                result["peak_allocated_mib"] = torch.cuda.max_memory_allocated() / 2**20
                model.clear_quant()
                del cache
                if not warmed:
                    del gradient
                    continue
                gradient = [None if value is None else value.cpu() for value in gradient]
                if reference is None:
                    reference = (result, gradient)
                before, expected = reference
                if any((a is None) != (b is None) for a, b in zip(expected, gradient, strict=True)):
                    raise ValueError("the packed comparison changed the parameters with gradients")
                drift = [a - b if a is not None else None for a, b in zip(expected, gradient, strict=True)]
                dot = readback.gradients.inner
                score_delta = np.asarray(before["scores"]) - np.asarray(result["scores"])
                if not np.isfinite(score_delta).all() or not math.isfinite(result["loss"]):
                    raise ValueError("the packed comparison produced a nonfinite objective or choice score")
                result.update(gradient_relative_l2=math.sqrt(dot(drift, drift)/dot(expected, expected)),
                              max_choice_logp_delta=float(np.max(np.abs(score_delta))),
                              same_selected_choices=bool(np.array_equal(np.argmax(before["scores"], axis=1),
                                                                         np.argmax(result["scores"], axis=1))))
                result["physical_slots"] = sum(x.size for x, _, _, _ in batches[name])
                readings[name].append(result)
                print(name, result["seconds"], result["gradient_relative_l2"], flush=True)
        bundle.unchanged()
        if (mixed.prep.sha(checkpoint) != original_sha
                or any(mixed.prep.sha(item) != key for item, key in sources.items())):
            raise ValueError("the completed model or comparison sources changed")
        mixed.native.publish(record / "report.json", dict(status="RELATION_LAYOUTS_FLASH_MEASURED", tag=TAG,
            checkpoint_sha256=original_sha, export_sha256=export_sha, training_step=step,
            source_update=readback.UPDATE+1, profile_sha256=sha, targets=counts, precision="CUDA_BF16_FLASH",
            sources={str(item): key for item, key in sources.items()}, optimizer_updates=0,
            median_seconds={name: median(row["seconds"] for row in trials) for name, trials in readings.items()},
            trials=readings))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "probe"))
    for name in ("training", "manifest", "record"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("manifest-sha256", "source-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    manifest, record = args.manifest.absolute(), args.record.absolute()
    paths = [Path(module.__file__).resolve() for module in (comparison, mixed, readback)]
    own = Path(__file__).resolve()
    pins = {path: mixed.prep.sha(path) for path in (own, *paths)}
    if (pins[own] != mixed.native.digest(args.source_sha256) or record.exists() or record.is_symlink()
            or (args.mode == "probe" and (not args.stop_by or args.stop_by.tzinfo is None))):
        parser.error("the exact comparison source, a fresh record and authorized cutoff are required")
    if args.mode == "check":
        batches, counts = layouts(mixed.Bundle(manifest, args.manifest_sha256))
        print(json.dumps(dict(status="RELATION_INPUTS_EXACT", tag=TAG, targets=counts,
            physical_slots={arm: sum(x.size for x, _, _, _ in rows) for arm, rows in batches.items()},
            sources={str(path): key for path, key in pins.items()})))
        return 0
    return supervisor.supervise(partial(worker, args.training.absolute(), pins), manifest,
                                args.manifest_sha256, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
