"""Measure owned short G4 updates against the v1.1 TRAIN speed budget."""

from argparse import ArgumentParser
from contextlib import ExitStack, nullcontext
from dataclasses import asdict, dataclass
from datetime import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from unittest.mock import patch

from scripts.p109_gpu_supervisor import QUERY
from scripts.run_p109b_scratch_pair_20261120 import idle_gpu, publish
from scripts.run_p109c_scratch330 import observe_card_return


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data_cache/ko-en_p109c_adopted_v11_20261121_chat32"
EVIDENCE = ROOT / "test_result/evidence"
AUTH_END = datetime.fromisoformat("2026-11-24T18:00:00+09:00").timestamp()
CARD_MIB = 6144
ALLOCATOR_MARGIN_MIB = 896
TELEMETRY_FAILURE_LIMIT = 5
TOKENS_PER_STEP = 131072
WIDTH = 1024
TRAIN_TOKENS = 1183367026
VAL_TOKENS = 2988635
VOCAB = 32768
SEED = 1337


@dataclass(frozen=True)
class Arm:
    batch: int
    checkpoint_visits: int = 0
    seq: int = WIDTH
    repeat: int = 2
    native_gqa: bool = True
    direct_ce: bool = False
    row_head: bool = False
    bf16_weights: bool = False
    ste_update: bool = False
    fused: bool = False
    sample_gradients: bool = False
    certify: bool = False
    pair_gates: bool = False
    mixed: bool = False
    r2_from: float = 0
    r2_ckpt: int = 12
    course_ckpt: int = 21


ARMS = {
    "r2_b2_ref": Arm(2, native_gqa=False),
    "r2_b2_gqa": Arm(2),
    "r2_b1_gqa": Arm(1),
    "r2_b2_ck14": Arm(2, 14),
    "r2_b4_ck14": Arm(4, 14),
    "r2_b4_ck21": Arm(4, 21),
    "r2_b4_ck28": Arm(4, 28),
    "r2_b8_ck28": Arm(8, 28),
    "r2_b2_direct": Arm(2, direct_ce=True),
    "r2_b4_ck14_direct": Arm(4, 14, direct_ce=True),
    "r2_b4_s512": Arm(4, seq=512, direct_ce=True),
    "r2_b8_s512_ck14": Arm(8, 14, seq=512, direct_ce=True),
    "r1_b4_s512": Arm(4, seq=512, repeat=1, direct_ce=True),
    "r1_b4_direct": Arm(4, repeat=1, direct_ce=True),
    "r1_b8_ck8": Arm(8, 8, repeat=1, direct_ce=True),
    "r1_b16_s256": Arm(16, seq=256, repeat=1, direct_ce=True),
    "r2_b4_ck21_row": Arm(4, 21, row_head=True),
    "r2_b4_ck21_bf16": Arm(4, 21, bf16_weights=True),
    "r2_b2_row_bf16": Arm(2, row_head=True, bf16_weights=True),
    "r2_b2_ck7_row_bf16_ste": Arm(2, 7, row_head=True, bf16_weights=True, ste_update=True),
    "r2_b4_ck14_row_bf16": Arm(4, 14, row_head=True, bf16_weights=True),
    "r2_b4_ck17_row_bf16": Arm(4, 17, row_head=True, bf16_weights=True),
    "r2_b4_ck17_row_ste": Arm(4, 17, row_head=True, ste_update=True),
    "r2_b4_ck17_row_bf16_ste": Arm(4, 17, row_head=True, bf16_weights=True, ste_update=True),
    "r2_b8_ck24_row_bf16": Arm(8, 24, row_head=True, bf16_weights=True),
    "r2_b8_ck19_s512_row_bf16": Arm(8, 19, 512, row_head=True, bf16_weights=True),
    "r1_b4_ck4_row_bf16": Arm(4, 4, repeat=1, row_head=True, bf16_weights=True),
    "r1_b8_ck8_s512_row_bf16": Arm(8, 8, 512, repeat=1, row_head=True, bf16_weights=True),
    "r1_b8_ck8_s512_row_bf16_ste": Arm(8, 8, 512, repeat=1, row_head=True, bf16_weights=True, ste_update=True),
    "r2_b4_ck17_fused": Arm(4, 17, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r2_b4_ck12_fused": Arm(4, 12, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r2_b8_ck24_fused": Arm(8, 24, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r2_b8_ck19_s512_fused": Arm(8, 19, 512, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r1_b4_ck4_row_bf16_ste": Arm(4, 4, repeat=1, row_head=True, bf16_weights=True, ste_update=True),
    "r1_b4_ck4_fused": Arm(4, 4, repeat=1, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r1_b4_fused": Arm(4, repeat=1, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r1_b8_ck8_s512_fused": Arm(8, 8, 512, repeat=1, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r1_b8_ck4_s512_fused": Arm(8, 4, 512, repeat=1, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r1_b8_s256_fused": Arm(8, 0, 256, repeat=1, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r1_b8_ck12_fused": Arm(8, 12, repeat=1, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r2_b4_ck8_fused_check": Arm(4, 8, row_head=True, bf16_weights=True, ste_update=True, fused=True, certify=True),
    "r2_b4_ck8_fused": Arm(4, 8, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r2_b4_ck4_fused": Arm(4, 4, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r2_b4_fused": Arm(4, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r2_b4_ck12_pair_gates": Arm(4, 12, row_head=True, bf16_weights=True, ste_update=True, fused=True, pair_gates=True),
    "r2_b4_fused_sample": Arm(4, row_head=True, bf16_weights=True, ste_update=True, fused=True, sample_gradients=True),
    "r2_b2_fused": Arm(2, row_head=True, bf16_weights=True, ste_update=True, fused=True),
    "r2_b2_fused_sample": Arm(2, row_head=True, bf16_weights=True, ste_update=True, fused=True, sample_gradients=True),
    "r2_b8_s512_fused_sample": Arm(8, seq=512, row_head=True, bf16_weights=True, ste_update=True,
                                  fused=True, sample_gradients=True),
    "mix_r1_to_r2": Arm(4, repeat=1, row_head=True, bf16_weights=True, ste_update=True, fused=True,
                        mixed=True, r2_from=.60),
    "mix_r1_to_r2_70": Arm(4, repeat=1, row_head=True, bf16_weights=True, ste_update=True, fused=True,
                           mixed=True, r2_from=.70),
    "mix_r2": Arm(4, 12, row_head=True, bf16_weights=True, ste_update=True, fused=True, mixed=True),
    "mix_r1_to_r2_ck8": Arm(4, repeat=1, row_head=True, bf16_weights=True, ste_update=True, fused=True,
                            mixed=True, r2_from=.60, r2_ckpt=8),
    "mix_r2_ck8": Arm(4, 8, row_head=True, bf16_weights=True, ste_update=True, fused=True, mixed=True),
}

EXPERIMENT_SOURCES = tuple(ROOT / "scripts" / name for name in (
    "p109_training_head.py", "p109_training_elementwise.py", "p109_training_gradient_sample.py",
    "p109_training_primitive_check.py", "p109_training_mixed.py", "p109_training_paired_gate.py"))


def pin_inputs():
    meta = (CACHE / "meta.json").read_bytes()
    info = json.loads(meta)
    if (info["train"], info["val"], info["vocab"], info["token_dtype"], info["tokenizer_sha256"]) != (
        TRAIN_TOKENS, VAL_TOKENS, VOCAB, "uint16", "9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E"
    ):
        raise ValueError("this diagnostic requires the exact v1.1 chat32 cache")
    sources = (Path(__file__), *EXPERIMENT_SOURCES,
               ROOT / "tinylm/config.py", ROOT / "tinylm/model/transformer.py",
               ROOT / "tinylm/model/modules.py", ROOT / "tinylm/model/ternary.py",
               ROOT / "tinylm/train/recomputed_ce.py", ROOT / "tinylm/train/muon.py")
    pins = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    pins[str((CACHE / "meta.json").relative_to(ROOT))] = hashlib.sha256(meta).hexdigest()
    for split, count in (("train", TRAIN_TOKENS), ("val", VAL_TOKENS)):
        path = CACHE / f"{split}.bin"
        stat = path.stat()
        if stat.st_size != count * 2:
            raise ValueError(f"unexpected {split} byte count")
        pins[str(path.relative_to(ROOT))] = dict(size=stat.st_size, mtime_ns=stat.st_mtime_ns, inode=stat.st_ino)
    return pins


def worker(args):
    import numpy as np
    import torch
    from torch.nn import functional as F
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from tinylm.config import build_config
    from tinylm.model import transformer
    from tinylm.train.muon import Muon, split_params
    from tinylm.train.recomputed_ce import target_nll

    directory = args.record
    profile = json.loads((directory.parent / "profile.json").read_bytes())
    if pin_inputs() != profile["pins"] or os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("source pin or authorized CUDA device changed")
    arm = ARMS[args.worker]
    if arm.mixed:
        from scripts.p109_training_mixed import mixed_worker

        return mixed_worker(args, arm, CACHE, publish, TOKENS_PER_STEP, WIDTH, SEED, CARD_MIB)
    torch.set_num_threads(1)
    torch.manual_seed(SEED)
    torch.cuda.set_per_process_memory_fraction(args.fraction, 0)
    torch.cuda.reset_peak_memory_stats()
    torch.backends.cuda.matmul.allow_tf32 = True
    if arm.certify:
        from scripts.p109_training_primitive_check import run as check_primitives

        publish(directory / "primitive_check.json", check_primitives())
        torch.cuda.empty_cache()
    cfg = build_config("m100s12_g4", "tied", WIDTH, ckpt=bool(arm.checkpoint_visits))
    cfg.vocab_size = VOCAB
    cfg.train_repeat = float(arm.repeat)
    cfg.sdpa_gqa = arm.native_gqa
    if arm.bf16_weights:
        cfg.wq_dtype = "bf16"
    if arm.row_head:
        from scripts.p109_training_head import target_nll as row_target_nll

    model = transformer.TiedMLPTransformer(cfg).cuda()
    model.set_anneal(1.0)
    matrices, _ = split_params(model)
    matrix_ids = {id(param) for param in matrices}
    groups = []
    for group in model.param_groups(0.001):
        params = [param for param in group["params"] if id(param) not in matrix_ids]
        if params:
            groups.append(dict(group, params=params))
    adamw = torch.optim.AdamW(groups, betas=(0.9, 0.95), eps=1e-8)
    muon = Muon(matrices, lr=0.004, scale_mode="rms", weight_decay=0.0)
    train = np.memmap(CACHE / "train.bin", dtype="<u2", mode="r")
    val = np.memmap(CACHE / "val.bin", dtype="<u2", mode="r")
    rng = np.random.default_rng(SEED)
    val_rng = np.random.default_rng(SEED + 1)
    val_starts = val_rng.integers(0, len(val) - WIDTH, size=8)
    starts = rng.integers(0, len(train) - WIDTH, size=(args.steps, TOKENS_PER_STEP // WIDTH))
    visits = 28 if arm.repeat == 2 else 16
    checkpoint = transformer.checkpoint
    visit = 0

    def keep_some_checkpoints(function, activation, **kwargs):
        nonlocal visit
        tag = visit % visits
        visit += 1
        if (tag + 1) * arm.checkpoint_visits // visits != tag * arm.checkpoint_visits // visits:
            return checkpoint(function, activation, **kwargs)
        return function(activation)

    def to_cuda(corpus, offsets, seq):
        rows = np.stack([corpus[start : start + WIDTH + 1] for start in offsets]).astype(np.int64)
        x = torch.from_numpy(rows[:, :-1].copy()).reshape(-1, seq).pin_memory()
        y = torch.from_numpy(rows[:, 1:].copy()).reshape(-1, seq).pin_memory()
        return x.to("cuda", non_blocking=True), y.to("cuda", non_blocking=True)

    def loss_for(x, y, training=False):
        with torch.autocast("cuda", dtype=torch.bfloat16):
            if training and arm.direct_ce:
                logits = model(x).flatten(0, 1)
                with torch.autocast("cuda", enabled=False):
                    selected = F.log_softmax(logits, dim=1).gather(1, y.view(-1, 1))
                    return -selected.float().mean()
            hidden = model(x, return_hidden=True)
            if training and arm.row_head:
                nll, valid = row_target_nll(model, hidden, y)
            else:
                nll, valid = target_nll(model, hidden, y, rows=1024)
            return nll.sum() / valid.sum()

    @torch.no_grad()
    def validate(repeat):
        model.eval()
        cfg.train_repeat = float(repeat)
        try:
            x, y = to_cuda(val, val_starts, WIDTH)
            return torch.stack([loss_for(a, b) for a, b in zip(x.split(1), y.split(1))]).mean().item()
        finally:
            model.train()
            cfg.train_repeat = float(arm.repeat)

    records = []
    with (sdpa_kernel(SDPBackend.FLASH_ATTENTION), patch.object(transformer, "checkpoint", keep_some_checkpoints),
          ExitStack() as kernels):
        if arm.fused:
            from scripts.p109_training_elementwise import fused_operations

            kernels.enter_context(fused_operations())
        if arm.pair_gates:
            from scripts.p109_training_paired_gate import PairedGates

            kernels.enter_context(PairedGates(model).patches())
        sampling = None
        if arm.sample_gradients:
            from scripts.p109_training_gradient_sample import RepeatedWeightSampling

            sampling = RepeatedWeightSampling(model)
            x, _ = to_cuda(train, starts[0, :1], WIDTH)
            sampling.inventory(model, x[:, :32])
            publish(directory / "gradient_sampling.json", dict(module_calls=sorted(sampling.counts.values()),
                    repeated_modules=sum(n > 1 for n in sampling.counts.values()), scale=2,
                    sample="alternating complementary halves across microbatches"))
        initial_val = validate(arm.repeat)
        initial_val_r2 = initial_val if arm.repeat == 2 else validate(2)
        with (directory / "steps.jsonl").open("x", encoding="utf-8", buffering=1) as stream:
            for index, offsets in enumerate(starts):
                tick = time.perf_counter()
                x, y = to_cuda(train, offsets, arm.seq)
                torch.cuda.synchronize()
                staged = time.perf_counter()
                adamw.zero_grad(set_to_none=True)
                muon.zero_grad(set_to_none=True)
                total_loss = torch.zeros((), device="cuda")
                micros = x.size(0) // arm.batch
                visit = 0
                if arm.ste_update:
                    model.begin_quant_update_cache()
                try:
                    for micro, (inputs, targets) in enumerate(zip(x.split(arm.batch), y.split(arm.batch), strict=True)):
                        phase = sampling.microbatch((index+micro)%2) if sampling is not None else nullcontext()
                        with phase:
                            loss = loss_for(inputs, targets, training=True)
                            (loss / micros).backward()
                            total_loss += loss.detach() / micros
                    if arm.ste_update:
                        model.finish_quant_update_cache()
                finally:
                    if arm.ste_update:
                        model.abort_quant_update_cache()
                if arm.checkpoint_visits and visit != visits * micros:
                    raise ValueError(f"unexpected number of layer visits {visit}")
                torch.cuda.synchronize()
                trained = time.perf_counter()
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                adamw.step()
                muon.step()
                torch.cuda.synchronize()
                ended = time.perf_counter()
                row = dict(step=index, sec=ended-tick, input_sec=staged-tick, model_sec=trained-staged,
                           optimizer_sec=ended-trained, train_nll=total_loss.item(), grad_norm=norm.item(),
                           targets=y.numel(), micros=micros, allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                           reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                if not (row["targets"] == TOKENS_PER_STEP and math.isfinite(row["train_nll"])
                        and math.isfinite(row["grad_norm"])):
                    raise ValueError("invalid update loss, norm, or target count")
                print(json.dumps(row), file=stream)
                records.append(row)
            final_val = validate(arm.repeat)
            final_val_r2 = final_val if arm.repeat == 2 else validate(2)
    steady = records[1:]
    publish(directory / "worker.json", dict(arm=asdict(arm), torch=torch.__version__, seed=SEED,
            torch_cuda=torch.version.cuda, param_count=sum(p.numel() for p in model.parameters()),
            initial_val=initial_val, final_val=final_val, val_targets=len(val_starts)*WIDTH,
            initial_val_r2=initial_val_r2, final_val_r2=final_val_r2,
            offsets_sha256=hashlib.sha256(starts.astype("<i8").tobytes()).hexdigest(),
            tokens_per_s=sum(row["targets"] for row in steady)/sum(row["sec"] for row in steady),
            update_seconds=sum(row["sec"] for row in records), updates=len(records)))


def card_sample():
    reply = subprocess.run(QUERY, capture_output=True, check=True, text=True, timeout=1.5)
    total, used, utilization = map(int, reply.stdout.strip().split(","))
    if not (CARD_MIB <= total and 0 <= used <= total and 0 <= utilization <= 100):
        raise ValueError("invalid card memory or utilization reading")
    return total, used, utilization


def run_arm(args, directory, label, deadline):
    total, background = idle_gpu()
    allocator_mib = CARD_MIB - background - args.allocator_margin
    if allocator_mib <= 0:
        raise RuntimeError("insufficient card headroom")
    directory.mkdir()
    command = [sys.executable, "-B", "-u", "-m", "scripts.diag_p109_full_train_throughput",
               "--worker", label, "--record", str(directory), "--steps", str(args.steps),
               "--fraction", str(allocator_mib/total)]
    start = time.time()
    peak = background
    missed = 0
    samples = 0
    reason = None
    with (directory / "worker.log").open("x", encoding="utf-8") as log, \
            (directory / "gpu.csv").open("x", encoding="utf-8", buffering=1) as gpu:
        print("unix_seconds,card_used_mib,gpu_util_percent", file=gpu)
        proc = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        consecutive_misses = 0
        print(f"START {label} pid={proc.pid} background={background} cap={allocator_mib}", flush=True)
        try:
            while proc.poll() is None:
                if time.time() >= deadline or (directory.parent / "STOP").exists():
                    reason = "TIME_OR_STOP"
                    break
                try:
                    _, used, util = card_sample()
                except (ValueError, subprocess.SubprocessError) as error:
                    missed += 1
                    consecutive_misses += 1
                    print(f"NVML {label} {type(error).__name__}", flush=True)
                    journal = directory / "steps.jsonl"
                    step_is_live = (ARMS[label].mixed and journal.is_file() and journal.stat().st_size > 0
                                    and time.time()-journal.stat().st_mtime < 8)
                    if consecutive_misses >= TELEMETRY_FAILURE_LIMIT and not step_is_live:
                        reason = "TELEMETRY_LOST"
                        break
                else:
                    consecutive_misses = 0
                    peak = max(peak, used)
                    samples += 1
                    print(f"{time.time():.3f},{used},{util}", file=gpu)
                    if used >= CARD_MIB - 64:
                        reason = "CARD_GUARD"
                        break
                time.sleep(0.40)
        except BaseException as error:
            reason = type(error).__name__
            raise
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            report = dict(arm=label, pid=proc.pid, command=command, returncode=proc.returncode,
                          start=start, end=time.time(), stop_reason=reason, starting_card_mib=background,
                          allocator_mib=allocator_mib, peak_card_mib=peak, samples=samples, missed=missed,
                          card_after_exit=observe_card_return())
            publish(directory / "supervisor.json", report)
            print(f"END {label} exit={proc.returncode} card_peak={peak} reason={reason}", flush=True)
    return reason


def main():
    cpus = os.sched_getaffinity(0)
    if os.cpu_count() == 16 and 15 in cpus:
        cpus.remove(15)
        if not cpus:
            raise RuntimeError("the WSL diagnostic requires a CPU other than reserved logical CPU 15")
        os.sched_setaffinity(0, cpus)
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--name")
    parser.add_argument("--arms", nargs="+", choices=ARMS)
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--allocator-margin", type=int, default=ALLOCATOR_MARGIN_MIB)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    parser.add_argument("--worker", choices=ARMS)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--fraction", type=float)
    args = parser.parse_args()
    if not 3 <= args.steps <= 128:
        parser.error("steps must include warm-up and at least two measured updates")
    if not 640 <= args.allocator_margin <= 1536:
        parser.error("allow at least 640 MiB beyond the desktop baseline for device runtime and drift")
    if args.worker:
        if args.record is None or not (0 < (args.fraction or 0) < 0.31):
            parser.error("worker requires the owned guard's path and allocator bound")
        return worker(args)
    if (args.arms is None or args.stop_by is None or args.stop_by.tzinfo is None or not args.name
            or not args.name.isascii() or not args.name.replace("_", "").isalnum()):
        parser.error("an ASCII run name, arm queue, and time with UTC offset are required")
    deadline = args.stop_by.timestamp() - 20
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or time.time()+30 >= deadline or deadline >= AUTH_END-20.0:
        parser.error("requires one owned card and a future stop inside the authorization window")
    output = EVIDENCE / f"p109_full_train_6gib_20261124_{args.name}"
    lock = os.open(ROOT / "runs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        idle_gpu()
        output.mkdir()
        for name in (Path(__file__), *EXPERIMENT_SOURCES):
            with (output / name.name).open("xb") as snapshot:
                snapshot.write(name.read_bytes())
        publish(output / "profile.json", dict(pins=pin_inputs(), steps=args.steps,
                arms=[(label, asdict(ARMS[label])) for label in args.arms], cutoff=deadline,
                card_ceiling_mib=CARD_MIB, fixed_allocator_margin_mib=args.allocator_margin,
                telemetry_failure_limit=TELEMETRY_FAILURE_LIMIT, cpu_affinity=sorted(cpus)))

        def stop(signum, _frame):
            raise KeyboardInterrupt(signal.Signals(signum).name)

        signal.signal(signal.SIGTERM, stop)
        for index, label in enumerate(args.arms):
            if time.time()+30 >= deadline or (output / "STOP").exists():
                break
            reason = run_arm(args, output / f"{index:02d}_{label}", label, deadline)
            if reason == "TIME_OR_STOP":
                break
    finally:
        os.close(lock)


if __name__ == "__main__":
    sys.exit(main())
