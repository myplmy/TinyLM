"""Hold exact P109C CPU training inputs fixed while varying worker placement."""

from argparse import ArgumentParser
from datetime import datetime
from hashlib import sha256
import os
from pathlib import Path
from random import Random
import resource
from statistics import median
import subprocess
import sys
from time import monotonic

from scripts import diag_p109c_v3_rule_flip as reference
from scripts import eval_p109c_completed as completed
from scripts import prepare_p109c_v2 as prep
from scripts import run_p109c_scratch330 as native


TAG = "p109c_cpu_affinity_training_20261125_retry1"
PROFILE = reference.EVIDENCE / f"{TAG}_profile.json"
RECORD = reference.EVIDENCE / TAG
STARTS = completed.ROOT / "data_cache/p109c_mixed_v2_v11_course_20261122_v1/raw_starts.npy"
STARTS_SHA = "003C3C205D8AF678C3815B19585CD42B655AB7E11E6876999BEE006ACE434AD8"
END = datetime.fromisoformat("2026-11-25T13:00:00+09:00")
WIDE = tuple(range(14))
PRIMARY = tuple(range(0, 14, 2))
STEPS, MICRO, ACCUM, WIDTH = 7, 2, 2, 256
ARMS = {"wide7": (WIDE, 7), "core7": (PRIMARY, 7), "smt14": (WIDE, 14)}
ORDER = ("wide7", "core7", "smt14", "smt14", "core7", "wide7")
SOURCES = (
    "scripts/diag_p109c_cpu_affinity_training.py", "scripts/diag_p109c_v3_rule_flip.py",
    "scripts/eval_p109c_completed.py", "scripts/diag_p102a_g4_full_delta_train.py",
    "tinylm/config.py", "tinylm/model/transformer.py", "tinylm/model/modules.py",
    "tinylm/model/ternary.py", "tinylm/train/recomputed_ce.py", "tinylm/train/muon.py",
)


def check(cutoff, cpus):
    if not datetime.now().astimezone() < cutoff <= END or os.sched_getaffinity(0) != set(cpus):
        raise ValueError("the authorized CPU affinity or deadline differs")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("this training diagnostic must not see the card")


def windows():
    import numpy as np

    if reference.file_sha(STARTS) != STARTS_SHA:
        raise ValueError("the admitted raw window locations differ")
    index = np.load(STARTS, mmap_mode="r", allow_pickle=False)
    draws = Random(13371125).sample(range(len(index)), STEPS * ACCUM)
    train = np.memmap(completed.regular_file(prep.CACHE / "train.bin"), dtype="<u2", mode="r")
    val = np.memmap(completed.regular_file(prep.CACHE / "val.bin"), dtype="<u2", mode="r")
    if len(train) != 1_183_367_026:
        raise ValueError("the selected v1.1 TRAIN differs")
    starts = [int(start) for start in index[draws, :MICRO].flat]
    ordered = sorted(starts)
    if any(b - a < WIDTH + 1 for a, b in zip(ordered, ordered[1:])):
        raise ValueError("the fixed probes must use disjoint raw training windows")
    batches = np.stack([train[start:start + WIDTH + 1] for start in starts])
    values = Random(13371126).sample(range(len(val) - WIDTH - 1), 8)
    val_batches = np.stack([val[start:start + WIDTH + 1] for start in values])
    return batches.reshape(STEPS, ACCUM, MICRO, WIDTH + 1), val_batches


def topology():
    records = {}
    for cpu in WIDE:
        path = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list")
        records[str(cpu)] = path.read_text().strip()
    if len({records[str(cpu)] for cpu in PRIMARY}) != 7 or len(set(records.values())) != 7:
        raise ValueError("the two affinity sets no longer cover the same seven physical cores")
    return records


def profile(train, val):
    return dict(tag=TAG, train_sha256=sha256(train).hexdigest(), val_sha256=sha256(val).hexdigest(),
                sources={name: reference.file_sha(completed.ROOT / name) for name in SOURCES},
                order=ORDER, arms=ARMS, physical_siblings=topology(), stages=STEPS,
                draws=STEPS * MICRO * ACCUM * WIDTH, warmup_excluded_from_timing=1,
                checkpoint_sha256=reference.CHECKPOINT_SHA256, raw_starts_sha256=STARTS_SHA,
                purpose="CPU update speed, exact model and optimizer state, fixed raw validation.")


def admit(stamp, cutoff, cpus):
    import json

    check(cutoff, cpus)
    train, val = windows()
    expected = profile(train, val)
    if reference.file_sha(PROFILE) != stamp.upper() or json.loads(json.dumps(expected)) != completed.read_json(PROFILE):
        raise ValueError("the frozen affinity, data or source profile differs")
    return train, val


def worker(arm, trial, stamp, cutoff):
    import torch
    from torch.nn import functional as F
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from scripts.diag_p102a_g4_full_delta_train import state_sha
    from tinylm.train.muon import Muon, split_params
    from tinylm.train.recomputed_ce import target_nll

    cpus, threads = ARMS[arm]
    train, val = admit(stamp, cutoff, cpus)
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(1337)
    torch.use_deterministic_algorithms(True)
    begin = monotonic()
    model = completed.load_model(reference.checkpoint(), 2942, "cpu")
    model.clear_quant()
    model.cfg.infer_repeat = 1.
    model.train()
    if len(model.visit_schedule()) != 28:
        raise ValueError("the CPU run must use the original 28-visit G4 route")
    matrices, other = split_params(model)
    adam = torch.optim.AdamW(other, lr=2e-5, betas=(0.9, 0.95), foreach=False)
    muon = Muon(matrices, lr=8e-5, scale_mode="rms")
    setup_seconds = monotonic() - begin
    updates = []
    with sdpa_kernel(SDPBackend.MATH):
        for step, group in enumerate(train):
            check(cutoff, cpus)
            start = monotonic()
            for optimizer in (adam, muon):
                optimizer.zero_grad(set_to_none=True)
            model.begin_quant_update_cache()
            losses = []
            try:
                for micro in group:
                    values = torch.tensor(micro.astype("int64"))
                    hidden = model(values[:, :-1], return_hidden=True)
                    nll, valid = target_nll(model, hidden, values[:, 1:], rows=512)
                    count = int(valid.sum())
                    if count != MICRO * WIDTH:
                        raise ValueError("the fixed raw batch has missing targets")
                    loss = nll.sum()
                    (loss / (ACCUM * count)).backward()
                    losses.append(float(loss.detach()) / count)
                model.finish_quant_update_cache()
            except BaseException:
                model.abort_quant_update_cache()
                raise
            compute = monotonic() - start
            grad_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True))
            adam.step()
            muon.step()
            updates.append(dict(step=step + 1, compute_seconds=compute, elapsed_seconds=monotonic() - start,
                                train_nll=sum(losses) / ACCUM, grad_norm=grad_norm))
        started_eval = monotonic()
        model.eval()
        model.cfg.infer_repeat = 2.
        with torch.inference_mode():
            model.freeze_quant()
            validation = []
            for batch in val.reshape(-1, MICRO, WIDTH + 1):
                check(cutoff, cpus)
                values = torch.tensor(batch.astype("int64"))
                logits = model(values[:, :-1])
                validation.append(float(F.cross_entropy(logits.transpose(1, 2).float(), values[:, 1:])))
        eval_seconds = monotonic() - started_eval
    states = dict(model=state_sha(model.state_dict()), adamw=state_sha(adam.state_dict()), muon=state_sha(muon.state_dict()))
    report = dict(arm=arm, trial=trial, cpus=cpus, threads=threads, setup_seconds=setup_seconds,
                  eval_seconds=eval_seconds, evaluation_nll=sum(validation) / len(validation),
                  evaluation_batches=validation, updates=updates, exact_states=states,
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  applied_targets=STEPS * MICRO * ACCUM * WIDTH, profile_sha256=stamp)
    native.publish(RECORD / f"{trial}_{arm}.json", report)
    print(f"{arm} repeat {trial} median {median(r['elapsed_seconds'] for r in updates[1:]):.4f}s "
          f"validation {report['evaluation_nll']:.8f}", flush=True)


def run(stamp, cutoff):
    admit(stamp, cutoff, WIDE)
    RECORD.mkdir()
    reports = []
    for trial, arm in enumerate(ORDER, 1):
        check(cutoff, WIDE)
        cpus, threads = ARMS[arm]
        environment = dict(os.environ, OMP_NUM_THREADS=str(threads), MKL_NUM_THREADS=str(threads),
                           OPENBLAS_NUM_THREADS="1")
        command = ["/usr/bin/taskset", "-c", ",".join(map(str, cpus)), sys.executable, "-B", "-u",
                   "-m", "scripts.diag_p109c_cpu_affinity_training", "worker", "--arm", arm,
                   "--trial", str(trial), "--profile-sha256", stamp, "--stop-by", cutoff.isoformat()]
        subprocess.run(command, env=environment, timeout=(cutoff - datetime.now().astimezone()).total_seconds(), check=True)
        reports.append(completed.read_json(RECORD / f"{trial}_{arm}.json"))
    reference_run = reports[0]
    equivalent = {}
    for report in reports:
        equivalent[str(report["trial"])] = dict(
            arm=report["arm"],
            exact_states={key: value == reference_run["exact_states"][key]
                          for key, value in report["exact_states"].items()},
            validation_delta=report["evaluation_nll"] - reference_run["evaluation_nll"],
            median_steady_seconds=median(row["elapsed_seconds"] for row in report["updates"][1:]),
        )
    native.publish(RECORD / "report.json", dict(profile_sha256=stamp, conditions=ARMS, trials=equivalent))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "run", "worker"))
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--trial", type=int)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if args.action == "seal":
        check(args.stop_by, WIDE)
        native.publish(PROFILE, profile(*windows()))
        print(reference.file_sha(PROFILE), flush=True)
    elif not args.profile_sha256:
        parser.error("run and worker need the exact profile hash")
    elif args.action == "run":
        run(args.profile_sha256, args.stop_by)
    elif not args.arm or args.trial not in range(1, len(ORDER) + 1) or ORDER[args.trial - 1] != args.arm:
        parser.error("worker needs one position from the sealed run order")
    else:
        worker(args.arm, args.trial, args.profile_sha256, args.stop_by)


if __name__ == "__main__":
    main()
