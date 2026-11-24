"""Verify the public CE option against the recorded masked G4 control."""

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from statistics import median
import sys
from unittest.mock import patch

import torch

from scripts import diag_p102a_g4_recompute_shapes as shapes


BASE = shapes.BASE
ROOT = shapes.ROOT
TAG = "p102a_g4_native_recomputed_ce_v1_20261119"
OUT = shapes.OUT.with_name(TAG)
DIGEST = shapes.LOSS.DIGEST
CPU_LOG = ROOT / "test_result/093_log_20261119_P102A_Stage2inWb0_recomputed_ce_native_CPU.txt"


def read(path):
    return json.loads(path.read_bytes())


def identity():
    paths = (
        Path(__file__).resolve(), ROOT / "tinylm/train/recomputed_ce.py",
        ROOT / "tinylm/train/context_training_state.py", ROOT / "scripts/test_p102a_recomputed_ce.py",
        CPU_LOG, shapes.OUT / "profile.json", shapes.OUT / "masked_reference/report.json",
        shapes.OUT / "report.json", shapes.OUT / "terminal_readback.json",
    )
    return shapes.identity() | {str(path.relative_to(ROOT)): DIGEST(path) for path in paths}


def check_call(args, kwargs):
    shapes.check_call("masked_reference", args, kwargs)
    assert kwargs["ce_recompute_rows"] == shapes.ROWS and kwargs["tag"] == TAG


def prepare():
    from tinylm import cli
    import tinylm.train as train_package

    prior = read(shapes.OUT / "report.json")
    receipt = read(shapes.OUT / "terminal_readback.json")
    source = read(shapes.OUT / "profile.json")
    assert receipt["report_sha256"] == DIGEST(shapes.OUT / "report.json")
    assert receipt["profile_sha256"] == DIGEST(shapes.OUT / "profile.json")
    assert receipt["native_json"]["masked_reference"]["measurement_sha256"] == DIGEST(
        shapes.OUT / "masked_reference/report.json")
    assert prior["pairs"]["masked"]["numerical_pass"]
    assert "Ran 38 tests" in CPU_LOG.read_text() and "[runlog] 종료코드 0" in CPU_LOG.read_text()
    args = source["commands"]["masked_reference"].copy()
    args[args.index("--tag") + 1] = TAG
    args += ["--ce-recompute-rows", str(shapes.ROWS)]
    with patch.object(sys, "argv", args), patch.object(train_package, "train") as target:
        cli.main()
    target.assert_called_once()
    check_call(*target.call_args)
    assert not torch.cuda.is_initialized()
    BASE.write_new(OUT / "profile.json", dict(tag=TAG, source=source["tag"],
        identity=identity(), args=args, data=source["data"], targets=source["targets"],
        supervised=source["masked_micro_supervised"], sampler_start=source["sampler_start"],
        sampler_end=source["sampler_end"]))
    print("P102A_NATIVE_RECOMPUTE_READY", shapes.ROWS, sum(source["masked_micro_supervised"]), flush=True)


def actual():
    from tinylm import cli
    from tinylm.train import muon, recomputed_ce, trainer
    import tinylm.train as train_package

    profile = read(OUT / "profile.json")
    assert profile["identity"] == identity() and shapes.idle()
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * (1 << 30)
    assert os.environ["CUBLAS_WORKSPACE_CONFIG"] == shapes.LOSS.STRICT.WORKSPACE
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.set_float32_matmul_precision("high")
    reference = read(shapes.OUT / "masked_reference/report.json")
    ckpt, logs = OUT / "ckpt", OUT / "logs"
    train = train_package.train
    model, loader_type, evaluate = trainer.TiedMLPTransformer, trainer.Loader, trainer.evaluate
    step, stats = muon.Muon.step, trainer._step_stats
    nll = recomputed_ce.target_nll
    seen, peaks, times, hashes = [], [], [], {}
    train_loader = initial = None
    nll_calls = 0

    class MaskedLoader(loader_type):
        def __call__(self):
            x, y = super().__call__()
            masked = shapes.add_mask(y)
            seen.append(int(masked.ne(shapes.IGNORE).sum()))
            return x, masked

    def loader(split, *args, **kwargs):
        nonlocal train_loader
        if split == "train":
            train_loader = MaskedLoader(split, *args, **kwargs)
            assert train_loader.rng.bit_generator.state == profile["sampler_start"]
            return train_loader
        return loader_type(split, *args, **kwargs)

    def make_model(cfg):
        nonlocal initial
        result = model(cfg)
        assert (cfg.mlp_group, cfg.cla_group, len(result.visit_schedule())) == (4, 2, 28)
        initial = shapes.previous.state_sha(result.state_dict())
        return result

    def prepare_cache(data, tokens, *, exact, doc_filter, hf_tok, chat32, **_):
        assert data == "synthetic" and tokens == BASE.POOL and exact and not (doc_filter or hf_tok or chat32)
        return dict(profile["data"])

    def observed_nll(*args, rows):
        nonlocal nll_calls
        assert rows == shapes.ROWS
        nll_calls += 1
        return nll(*args, rows=rows)

    def short_eval(model, source, iters, device, **kwargs):
        value = evaluate(model, source, 2, device, **kwargs)
        torch.cuda.reset_peak_memory_stats()
        return value

    def observed_step(opt, *args, **kwargs):
        value = step(opt, *args, **kwargs)
        torch.cuda.synchronize()
        peaks.append((torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved()))
        return value

    def save(blob, path):
        assert path.parent == ckpt and not path.exists()
        assert blob["ce_recompute_rows"] == shapes.ROWS and "ce_vocab_tile" not in blob
        index = str(blob["step"])
        if index not in hashes:
            hashes[index] = {key: shapes.previous.state_sha(blob[key]) for key in ("model", "opt", "opt_muon")}

    def watched_stats(values):
        times.extend(values)
        return stats(values)

    def checked_train(*args, **kwargs):
        check_call(args, kwargs)
        return train(*args, **kwargs)

    BASE.write_new(OUT / "active.json", dict(tag=TAG, pid=os.getpid()))
    print("P102A_NATIVE_RECOMPUTE_ACTIVE", os.getpid(), flush=True)
    with (patch.object(sys, "argv", profile["args"]), patch.object(train_package, "train", checked_train),
          patch.object(trainer, "CKPT", ckpt), patch.object(trainer, "LOGS", logs),
          patch.object(trainer, "prepare", prepare_cache), patch.object(trainer, "Loader", loader),
          patch.object(trainer, "TiedMLPTransformer", make_model), patch.object(trainer, "evaluate", short_eval),
          patch.object(trainer, "_step_stats", watched_stats), patch.object(muon.Muon, "step", observed_step),
          patch.object(recomputed_ce, "target_nll", observed_nll), patch.object(torch, "save", save)):
        cli.main()
    (native,) = logs.glob("*.json")
    result = read(native)
    assert nll_calls == len(seen) == 12 and len(peaks) == len(times) == len(hashes) == BASE.STEPS
    assert initial == reference["initial"] and seen == profile["supervised"]
    assert train_loader.rng.bit_generator.state == profile["sampler_end"]
    assert result["ce_recompute_rows"] == shapes.ROWS and "ce_vocab_tile" not in result
    assert result["n_skip"] == 0 and result["tokens"] == profile["targets"] and not any(ckpt.iterdir())
    train_ce = [row["train_ce"] for row in result["history"]]
    val = result["final"]["val_loss"]
    variations = {index: [key for key, value in item.items() if reference["states"][index][key] != value]
                  for index, item in hashes.items()}
    passed = not any(variations.values()) and train_ce == reference["train_ce"] and val == reference["val_ce"]
    assert profile["identity"] == identity()
    BASE.write_new(OUT / "report.json", dict(tag=TAG, native_json=str(native.relative_to(ROOT)),
        profile_sha256=DIGEST(OUT / "profile.json"), initial=initial, supervised=seen, updates=BASE.STEPS,
        nll_calls=nll_calls, state_hashes=hashes, state_differences=variations, numerical_pass=passed,
        train_ce=train_ce, val_ce=val, allocated=max(p[0] for p in peaks), reserved=max(p[1] for p in peaks),
        step_times_ms=times, median_after_first_ms=median(times[1:]), checkpoint_writes=0))
    print("P102A_NATIVE_RECOMPUTE_RESULT", passed, variations, flush=True)
    return 0 if passed else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "actual"))
    args = parser.parse_args()
    assert datetime.now(BASE.CUTOFF.tzinfo) + timedelta(minutes=3) < BASE.CUTOFF
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if args.phase == "prepare" else "0")
    if args.phase == "prepare":
        OUT.mkdir(exist_ok=False)
    else:
        assert not (OUT / "active.json").exists() and not (OUT / "report.json").exists()
    os.environ.update(TINYLM_DIR=str(OUT / "scratch"), TINYLM_HF=str(OUT / "scratch" / "HF"))
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    return prepare() if args.phase == "prepare" else actual()


if __name__ == "__main__":
    sys.exit(main())
