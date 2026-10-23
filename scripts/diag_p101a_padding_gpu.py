#!/usr/bin/env python3
"""Opt-in actual-parent padding diagnostic; import/check-only opens source only.

One FP32 MATH update per policy checks all CPU-canonical gradients and updated
parameters. BF16 eager timing uses four fresh ABBA blocks, each with the same
two warmup and four measured updates. No CP is saved and no quality is claimed.
Execution belongs to the explicitly authorized root, never the author agent.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager, nullcontext
import copy
from datetime import datetime, timezone
import gc
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import weakref

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "P101A_PADDING_GPU_DIAGNOSTIC_V1"
TAG = "p101a_padding_gpu_v1_s1337"
WORKSPACE_TAG = TAG + "_workspace_v2"
SCRIPT = "scripts/diag_p101a_padding_gpu.py"
TEST = "scripts/test_p101a_padding_gpu.py"
CORPUS = "HF/sft_ready/p101a_sft_mtp_cleanbilingual_v3_s1337/corpus"
CORPUS_SHA = "7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20"
PARENT = "runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt"
PARENT_SHA = "12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950"
TOKENIZER = "data_cache/tok-ko-en-32768-chat32.json"
TOKENIZER_SHA = "9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E"
HARD_STOP = datetime(2026, 10, 23, 7, 30, tzinfo=timezone.utc)  # 16:30 KST.
POLICIES = ("fixed1024", "crop128")
ABBA = ("fixed1024", "crop128", "crop128", "fixed1024")
MICRO, ACCUM, FIXED, QUANTUM = 8, 16, 1024, 128
WARMUP, MEASURED, SEED = 2, 4, 1337
MAX_BYTES = 19_999_999
SOURCES = (
    SCRIPT, TEST, "scripts/diag_p101a_sft_mtp.py", "scripts/diag_p101a_clean_bilingual.py",
    "scripts/p101a_sft_mtp_data.py", "scripts/p106b_shards.py",
    "scripts/train_sft_p090.py",
    "scripts/test_p101a_padding_crop.py", "scripts/test_p101a_sft_mtp.py",
    "scripts/test_p070b_cla_routes.py", "scripts/p070b_cla_routes.py",
    "tinylm/__init__.py", "tinylm/paths.py", "tinylm/config.py",
    "tinylm/model/__init__.py", "tinylm/model/transformer.py", "tinylm/model/modules.py",
    "tinylm/model/ternary.py", "tinylm/model/ternary_kernel.py",
    "tinylm/data/__init__.py", "tinylm/data/prepare.py", "tinylm/data/sft.py",
    "tinylm/chat/__init__.py", "tinylm/chat/canonical.py", "tinylm/chat/serialize.py",
    "tinylm/chat/tokens.py", "tinylm/train/__init__.py", "tinylm/train/trainer.py",
    "tinylm/train/mtp_sft.py", "tinylm/train/muon.py", "tinylm/train/optimizer_audit.py",
    "tinylm/audit_io.py",
)


def utc_now():
    return datetime.now(timezone.utc)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def identity(value):
    return hashlib.sha256(canonical(value)).hexdigest().upper()


def safe_path(relative, root=ROOT):
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts or not value.parts or value.parts[:2] == ("datasets", "TinyDataset"):
        raise ValueError("explicit repository-relative nonsymlink path required")
    current = Path(root)
    for part in value.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("linked path refused: " + str(relative))
    return current


def digest(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("regular file required: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def source_manifest(root=ROOT):
    """Never import the original engine or inspect model/data directories."""
    source = safe_path("scripts/diag_p101a_sft_mtp.py", root)
    tree = ast.parse(source.read_text(encoding="utf-8"))
    declarations = [node.value for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "CODE" for t in node.targets)]
    if len(declarations) != 1:
        raise ValueError("original engine CODE must be one literal tuple")
    original = ast.literal_eval(declarations[0])
    if not isinstance(original, tuple) or any(not isinstance(p, str) or not p.endswith(".py") for p in original):
        raise ValueError("literal Python-only engine CODE required")
    pending = list(dict.fromkeys((*SOURCES, *original)))
    result = {}
    while pending:
        name = pending.pop(0)
        if name in result:
            continue
        if Path(name).parts[0] not in ("scripts", "tinylm") or not name.endswith(".py"):
            raise ValueError("source manifest cannot read assets")
        path = safe_path(name, root)
        result[name] = digest(path)
        parsed = ast.parse(path.read_text(encoding="utf-8"))
        package = list(Path(name).parts[:-1])
        modules = []
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                modules.extend(alias.name.split(".") for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                prefix = package[:len(package) - node.level + 1] if node.level else []
                base = prefix + (node.module.split(".") if node.module else [])
                modules.append(base)
                modules.extend(base + alias.name.split(".") for alias in node.names if alias.name != "*")
        for module in modules:
            if not module or module[0] not in ("scripts", "tinylm"):
                continue
            for end in range(1, len(module) + 1):
                partial = Path(*module[:end])
                for candidate in (str(partial) + ".py", str(partial / "__init__.py")):
                    resolved = safe_path(candidate, root)
                    if resolved.is_file() and candidate not in result and candidate not in pending:
                        pending.append(candidate)
    return dict(sorted(result.items()))


def literal_tolerances(root=ROOT):
    """Read existing rules without importing CPU tests (which import torch)."""
    wanted = {
        "scripts/test_p070b_cla_routes.py": ("ATOL", "RTOL"),
        "scripts/test_p101a_padding_crop.py": ("ACCUM_ATOL", "ACCUM_RTOL"),
    }
    values = {}
    for name, keys in wanted.items():
        found = {}
        tree = ast.parse(safe_path(name, root).read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in keys:
                found[node.targets[0].id] = ast.literal_eval(node.value)
            elif len(node.targets) == 1 and isinstance(node.targets[0], ast.Tuple):
                ids = [n.id for n in node.targets[0].elts if isinstance(n, ast.Name)]
                if ids == list(keys):
                    found.update(zip(ids, ast.literal_eval(node.value)))
        if set(found) != set(keys) or any(not isinstance(v, (float, int)) or not 0 < v < 1 for v in found.values()):
            raise ValueError("existing numerical rule unavailable: " + name)
        values[name] = dict(atol=float(found[keys[0]]), rtol=float(found[keys[1]]))
    return dict(loss_and_norm=values["scripts/test_p070b_cla_routes.py"],
                gradients_and_update=values["scripts/test_p101a_padding_crop.py"],
                provenance=values, interpretation="Existing regression tolerances applied to FP32 GPU diagnostic; not GPU calibrated; never retuned from results")


def aware(value):
    if not isinstance(value, str):
        raise ValueError("aware ISO deadline required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("naive deadline refused")
    return result.astimezone(timezone.utc)


def validate_execution(args, now=None):
    now = utc_now() if now is None else now
    deadline = aware(args.deadline)
    if not now < deadline <= HARD_STOP or deadline.date() != HARD_STOP.date():
        raise ValueError("deadline must be current and no later than 2026-10-23 16:30 KST")
    if type(args.max_wall_sec) is not int or not 60 <= args.max_wall_sec <= 1200:
        raise ValueError("wall bound must be 60..1200 seconds")
    if (deadline - now).total_seconds() < args.max_wall_sec:
        raise ValueError("declared wall bound does not fit before deadline")
    if args.mode not in ("correctness", "timing"):
        raise ValueError("registered diagnostic mode required")
    return deadline


class Guard:
    def __init__(self, deadline, seconds):
        self.deadline, self.seconds = deadline, seconds
        self.started = time.perf_counter()

    def check(self, stage):
        if utc_now() >= self.deadline or time.perf_counter() - self.started >= self.seconds:
            raise TimeoutError("diagnostic deadline/wall bound reached at " + stage)


@contextmanager
def wall_limit(seconds):
    """Bound imports and all model work; an outer OS timeout is still required."""
    if type(seconds) is not int or not 60 <= seconds <= 1200:
        raise ValueError("registered wall bound must be60..1200 seconds")
    if signal.getitimer(signal.ITIMER_REAL)[0]:
        raise ValueError("refusing to replace another active process alarm")
    previous = signal.getsignal(signal.SIGALRM)
    def alarm(*_args):
        raise TimeoutError("internal wall limit reached; partial evidence retained")
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def gpu_admission(torch=None, runner=subprocess.run):
    """No foreign compute process; after a block allow only this empty context."""
    apps = runner(["nvidia-smi", "--query-compute-apps=pid,process_name", "--format=csv,noheader,nounits"],
                  capture_output=True, text=True, timeout=5, check=False)
    memory = runner(["nvidia-smi", "--query-gpu=memory.used,memory.free", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5, check=False)
    if apps.returncode or memory.returncode:
        raise ValueError("cannot inspect GPU admission")
    rows = [line.strip() for line in apps.stdout.splitlines() if line.strip() and "No running processes" not in line]
    allowed_pid = str(os.getpid()) if torch is not None and torch.cuda.is_initialized() else None
    if any(row.split(",", 1)[0].strip() != allowed_pid for row in rows):
        raise ValueError("foreign GPU compute process present; model not started")
    memory_rows = [line for line in memory.stdout.splitlines() if line.strip()]
    if len(memory_rows) != 1:
        raise ValueError("single-GPU diagnostic required")
    cells = memory_rows[0].split(",")
    if len(cells) != 2 or any(not cell.strip().isdigit() for cell in cells) or int(cells[1]) < 14000:
        raise ValueError("GPU free memory must be at least14000MiB")
    if allowed_pid is not None and torch.cuda.memory_allocated():
        raise ValueError("previous GPU model/tensor still allocated; no co-residency permitted")
    return dict(processes=rows, self_context_allowed=allowed_pid is not None,
                used_mib=int(cells[0]), free_mib=int(cells[1]))


def output_path(value, mode, root=ROOT, *, release_workspace=False):
    expected = Path("test_result/evidence") / (WORKSPACE_TAG if release_workspace else TAG) / mode
    given = Path(value)
    if given.is_absolute():
        try:
            given = given.relative_to(root)
        except ValueError as exc:
            raise ValueError("output outside exact evidence namespace") from exc
    if given != expected:
        raise ValueError("output must be exactly " + str(expected))
    path = safe_path(str(expected), root)
    if path.exists() or path.is_symlink():
        raise FileExistsError("prior diagnostic output preserved: " + str(path))
    return path


def write_new(path, value):
    raw = canonical(value) + b"\n"
    if len(raw) > MAX_BYTES:
        raise ValueError("20MB evidence guard")
    with path.open("xb") as stream:
        stream.write(raw)


def clear_runtime_workspace(torch):
    """Opt-in diagnostic cleanup; never increase the zero-allocation threshold.

    PyTorch's own CUDA leak checker clears this handle/stream workspace before
    counting remaining live allocations. Unsupported runtimes still fail.
    """
    torch.cuda.synchronize()
    before = torch.cuda.memory_allocated()
    clear = getattr(torch._C, "_cuda_clearCublasWorkspaces", None)
    if not callable(clear):
        raise RuntimeError("explicit cuBLAS workspace cleanup API unsupported")
    clear()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    after = torch.cuda.memory_allocated()
    return dict(before_workspace_clear_bytes=before, after_workspace_clear_bytes=after,
                api="torch._C._cuda_clearCublasWorkspaces", remaining_zero=after == 0)


class Journal:
    def __init__(self, path):
        self.stream = path.open("xb")
        self.bytes = self.rows = 0

    def append(self, value):
        raw = canonical(value) + b"\n"
        if self.bytes + len(raw) > MAX_BYTES:
            raise ValueError("20MB cumulative event guard")
        self.stream.write(raw)
        self.stream.flush()
        self.bytes += len(raw)
        self.rows += 1

    def close(self):
        self.stream.close()


def record_value(record):
    x, y, segments = list(record.x), list(record.y), list(record.segments)
    if not 1 <= len(x) <= FIXED or not len(x) == len(y) == len(segments):
        raise ValueError("aligned full record within context required")
    if any(type(v) is not int or not 0 <= v < 32768 for v in x):
        raise ValueError("input token outside exact chat32 vocabulary")
    if any(type(v) is not int or v < 0 for v in segments):
        raise ValueError("nonnegative assistant owners required")
    for label, owner in zip(y, segments):
        if type(label) is not int or (label != -100 and not 0 <= label < 32768):
            raise ValueError("target outside exact chat32 vocabulary")
        if (label != -100) != (owner > 0):
            raise ValueError("supervision/assistant owner mismatch")
    if not any(label != -100 for label in y):
        raise ValueError("real records must have assistant targets")
    return [x, y, segments]


def width_for(micro, policy):
    if policy not in POLICIES or len(micro) != MICRO:
        raise ValueError("registered policy and exact eight-slot micro required")
    longest = max(len(record.x) for record in micro)
    if not 1 <= longest <= FIXED:
        raise ValueError("no real-token truncation permitted")
    return FIXED if policy == POLICIES[0] else QUANTUM * ((longest + QUANTUM - 1) // QUANTUM)


def update_plan(groups):
    if len(groups) != ACCUM or any(len(micro) != MICRO for micro in groups):
        raise ValueError("exact original16 micros x8 records required; no sample reduction")
    values = [[record_value(record) for record in micro] for micro in groups]
    targets = sum(sum(label != -100 for label in value[1]) for micro in values for value in micro)
    actual_x = sum(len(value[0]) for micro in values for value in micro)
    return dict(ordered_records_sha256=identity(values), rows=MICRO * ACCUM,
                assistant_targets=targets, actual_x_tokens=actual_x,
                micro_order_sha256=[identity(micro) for micro in values],
                widths={policy: [width_for(micro, policy) for micro in groups] for policy in POLICIES},
                padded_slots={policy: MICRO * sum(width_for(micro, policy) for micro in groups) for policy in POLICIES})


def block_schedule():
    return [dict(block=i, policy=policy, updates=[dict(index=j, phase="warmup" if j < WARMUP else "measured")
            for j in range(WARMUP + MEASURED)]) for i, policy in enumerate(ABBA)]


def scalar_difference(left, right, tolerance):
    if not all(math.isfinite(v) for v in (left, right)):
        return dict(close=False, left=left if math.isfinite(left) else None,
                    right=right if math.isfinite(right) else None, nonfinite=True)
    error = abs(left - right)
    relative = error / max(abs(left), sys.float_info.min)
    return dict(close=error <= tolerance["atol"] + tolerance["rtol"] * abs(left),
                left=left, right=right, max_abs=error,
                relative_to_reference=relative if math.isfinite(relative) else None)


def tensor_table(torch, reference, candidate, tolerance):
    if set(reference) != set(candidate):
        raise ValueError("all-parameter/optimizer-state key sets differ")
    rows = []
    for name in sorted(reference):
        left, right = reference[name], candidate[name]
        if left is None or right is None:
            rows.append(dict(name=name, close=left is None and right is None, none_reference=left is None, none_candidate=right is None))
            continue
        if left.device.type != "cpu" or right.device.type != "cpu" or left.shape != right.shape or left.dtype != right.dtype:
            raise ValueError("canonical CPU tensor shape/dtype differs: " + name)
        a, b = left.double(), right.double()
        error = (a - b).abs()
        finite = bool(torch.isfinite(a).all()) and bool(torch.isfinite(b).all())
        bad = error > tolerance["atol"] + tolerance["rtol"] * a.abs()
        tiny = torch.finfo(left.dtype).tiny if left.is_floating_point() else 1.0
        def tensor_sha(value):
            raw = value.contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
            return hashlib.sha256(raw).hexdigest().upper()
        rows.append(dict(name=name, close=finite and not bool(bad.any()), shape=list(left.shape), dtype=str(left.dtype),
            reference_sha256=tensor_sha(left), candidate_sha256=tensor_sha(right), finite=finite,
            elements=left.numel(), mismatch_elements=int(bad.sum()), max_abs=float(error.max()) if error.numel() and finite else None,
            max_relative=float((error / a.abs().clamp_min(tiny)).max()) if error.numel() and finite else None,
            reference_l2=float(a.norm()) if finite else None, candidate_l2=float(b.norm()) if finite else None,
            reference_max_abs=float(a.abs().max()) if a.numel() and finite else None))
    return dict(close=all(row["close"] for row in rows), tensors=len(rows), per_parameter=rows,
                statistics_dtype="CPU FP64 for statistics only; model/gradient operands are FP32; inherited FP32 tolerance unchanged")


def asset_manifest(engine, report):
    names = [PARENT, TOKENIZER, CORPUS + "/report.json"]
    for split in ("train", "val"):
        manifest = report["manifests"][split]
        for shard in manifest["shards"]:
            child = Path(shard["path"])
            if child.is_absolute() or ".." in child.parts:
                raise ValueError("corpus shard escape refused")
            names.append(CORPUS + "/" + str(child))
        manifest_name = CORPUS + "/" + split + "_shards_manifest.json"
        if safe_path(manifest_name).is_file():
            names.append(manifest_name)
    values = {name: digest(safe_path(name)) for name in dict.fromkeys(names)}
    if values[PARENT] != PARENT_SHA or values[TOKENIZER] != TOKENIZER_SHA or values[CORPUS + "/report.json"] != CORPUS_SHA:
        raise ValueError("pinned CP/tokenizer/V3 corpus identity differs")
    if engine.PARENT.resolve() != safe_path(PARENT).resolve() or engine.data.TOKENIZER.resolve() != safe_path(TOKENIZER).resolve():
        raise ValueError("original runtime resolved another parent/tokenizer")
    return values


def cpu_copy(values):
    return {name: value.detach().cpu().clone() for name, value in values.items()}


def optimizer_snapshot(torch, model, optimizers):
    names = {id(parameter): name for name, parameter in model.named_parameters()}
    result = {}
    for opt_name, optimizer in zip(("adamw", "muon"), optimizers):
        for parameter, state in optimizer.state.items():
            name = names[id(parameter)]
            for slot, value in state.items():
                result[opt_name + ":" + name + ":" + slot] = (value.detach().cpu().clone()
                    if torch.is_tensor(value) else torch.tensor(value, dtype=torch.float64))
    return result


def rng_identity(torch):
    return dict(cpu=hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest().upper(),
                cuda=hashlib.sha256(torch.cuda.get_rng_state().cpu().numpy().tobytes()).hexdigest().upper())


def one_update(torch, core, model, optimizers, groups, plan, policy, precision, guard, journal, block, index, phase, capture=False):
    guard.check("before update")
    if update_plan(groups) != plan:
        raise ValueError("ordered raw records/whole-update denominator changed")
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    for optimizer in optimizers:
        optimizer.zero_grad(set_to_none=True)
    zero_seconds = time.perf_counter() - started
    observed = 0
    nll = 0.0
    events = []
    pad_seconds = 0.0
    from torch.nn.attention import sdpa_kernel, SDPBackend
    for micro_index, micro in enumerate(groups):
        guard.check("before micro")
        micro_started_at = utc_now().isoformat()
        journal.append(dict(event="micro_start", block=block, update=index, phase=phase, policy=policy,
            micro=micro_index, at=micro_started_at, deadline=guard.deadline.isoformat()))
        tick = time.perf_counter()
        width = plan["widths"][policy][micro_index]
        x, y, segments = core.pad_records(micro, model._padding_pad_id, "cuda", fixed_width=width, batch_size=MICRO)
        this_pad_seconds = time.perf_counter() - tick
        pad_seconds += this_pad_seconds
        if list(x.shape) != [MICRO, width] or y.shape != x.shape or segments.shape != x.shape:
            raise ValueError("original pad_records execution shape differs")
        stamps = [torch.cuda.Event(enable_timing=True) for _ in range(4)]
        forward_started = time.perf_counter()
        with (sdpa_kernel(SDPBackend.MATH) if precision == "fp32_math" else nullcontext()):
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=precision == "bf16_eager"):
                stamps[0].record()
                hidden = model(x, return_hidden=True)
                stamps[1].record()
                sums, counts = core.components(model, hidden, y, segments, horizons=())
                loss = core.normalized_loss(sums, {1: plan["assistant_targets"]}, {})
                stamps[2].record()
            if not bool(torch.isfinite(loss)):
                raise ValueError("nonfinite assistant loss")
            backward_started = time.perf_counter()
            loss.backward()
            stamps[3].record()
        observed += counts[1]
        nll += float(sums[1].detach())
        events.append(stamps)
        journal.append(dict(event="micro_complete", block=block, update=index, phase=phase, policy=policy,
            micro=micro_index, width=width, actual_x_tokens=sum(len(r.x) for r in micro), assistant_targets=counts[1],
            whole_update_denominator=plan["assistant_targets"], host_micro_seconds=time.perf_counter() - tick,
            host_pad_h2d_seconds=this_pad_seconds,
            host_forward_finite_seconds=backward_started - forward_started,
            host_backward_and_loss_sync_seconds=time.perf_counter() - backward_started,
            started_at=micro_started_at,
            completed_at=utc_now().isoformat()))
        del x, y, segments, hidden, sums, loss
        guard.check("after micro")
    if observed != plan["assistant_targets"]:
        raise ValueError("actual16-micro target count differs from whole-update denominator")
    stats_started = time.perf_counter()
    parameters = dict(model.named_parameters())
    grads = [p.grad for p in parameters.values() if p.grad is not None]
    if not grads or not all(bool(torch.isfinite(g).all()) for g in grads):
        raise ValueError("missing/nonfinite gradient set")
    capture_started = time.perf_counter()
    canonical_gradients = ({name: None if p.grad is None else p.grad.detach().cpu().clone() for name, p in parameters.items()}
                           if capture else None)
    capture_seconds = time.perf_counter() - capture_started if capture else 0.0
    gradient_max = max(float(g.abs().max()) for g in grads)
    validation_stats_seconds = time.perf_counter() - stats_started - capture_seconds
    optimizer_events = [torch.cuda.Event(enable_timing=True) for _ in range(3)]
    clip_started = time.perf_counter()
    optimizer_events[0].record()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer_events[1].record()
    if not bool(torch.isfinite(norm)):
        raise ValueError("nonfinite preclip norm")
    guard.check("before optimizer")
    for optimizer in optimizers:
        optimizer.step()
    optimizer_events[2].record()
    torch.cuda.synchronize()
    seconds = time.perf_counter() - started
    spans = [dict(backbone_forward_ms=s[0].elapsed_time(s[1]), head_forward_ms=s[1].elapsed_time(s[2]),
                  backward_ms=s[2].elapsed_time(s[3])) for s in events]
    result = dict(block=block, update=index, phase=phase, policy=policy, precision=precision,
        whole_update_seconds=seconds, correctness_cpu_gradient_capture_seconds=capture_seconds,
        host_phase_seconds=dict(zero_grad=zero_seconds, pad_h2d_total=pad_seconds,
            gradient_validation_and_statistics=validation_stats_seconds, clip_and_optimizer_including_sync=time.perf_counter() - clip_started),
        gradient_clip_gpu_ms=optimizer_events[0].elapsed_time(optimizer_events[1]),
        optimizer_gpu_ms=optimizer_events[1].elapsed_time(optimizer_events[2]),
        event_timing_scope="forward backbone/head and backward; backward includes checkpoint recomputation; host journaling included in whole-update wall",
        micro_gpu_events=spans, actual_x_tokens=plan["actual_x_tokens"], assistant_targets=observed,
        padded_slots=plan["padded_slots"][policy], pad_slots=plan["padded_slots"][policy] - plan["actual_x_tokens"],
        denominator=plan["assistant_targets"], ordered_records_sha256=plan["ordered_records_sha256"],
        widths=plan["widths"][policy], loss=nll / observed, preclip_norm=float(norm), gradient_max=gradient_max,
        all_parameter_count=len(parameters), non_none_gradient_count=len(grads),
        none_gradient_names=[name for name, parameter in parameters.items() if parameter.grad is None],
        peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
        peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
    journal.append(dict(event="update_complete", **result))
    guard.check("after optimizer")
    if update_plan(groups) != plan:
        raise ValueError("original records were mutated")
    return result, canonical_gradients


def execute(args, sources, tolerances):
    deadline = validate_execution(args)
    release_workspace = getattr(args, "release_cublas_workspace", False)
    target = output_path(args.output, args.mode, release_workspace=release_workspace)
    if args.source_sha256 != identity(sources):
        raise ValueError("--source-sha256 must match current source-only receipt")
    for key, expected in (("TINYLM_DIR", str(ROOT)), ("TINYLM_HF", str(ROOT / "HF"))):
        if key in os.environ and os.environ[key] != expected:
            raise ValueError("unexpected runtime environment: " + key)
    target.mkdir(parents=True, exist_ok=False)
    journal = Journal(target / "events.jsonl")
    began = time.perf_counter()
    guard = Guard(deadline, args.max_wall_sec)
    result = dict(schema=SCHEMA, mode=args.mode, tag=WORKSPACE_TAG if release_workspace else TAG,
        release_cublas_workspace=release_workspace, gpu_release_audits=[], sources=sources, source_sha256=identity(sources),
        tolerances=tolerances, deadline=deadline.isoformat(), max_wall_sec=args.max_wall_sec,
        seed=SEED, parent_sha256=PARENT_SHA, tokenizer_sha256=TOKENIZER_SHA, corpus_report_sha256=CORPUS_SHA,
        corpus=CORPUS, corpus_quality="KNOWN_V3_SUPERVISION_DEFECTS; NOISY_CONTROL_FOR_NUMERICS_AND_PERFORMANCE_ONLY; NOT_ADMITTED",
        preserved_known_defects=["192 first assistant turn", "198 first assistant turn", "669 second assistant turn"],
        checkpoint_writes=0, production_adopted=False, quality_claim=False, compile=False, mtp=False,
        started_at=utc_now().isoformat(), diagnostic_precision="FP32_MATH" if args.mode == "correctness" else "BF16_EAGER",
        status="STARTED", returncode=9, updates=[], blocks=[], stages={})
    write_new(target / "admission.json", result)
    assets = None
    torch = template = model = optimizers = initial_state = records = None
    try:
        with wall_limit(args.max_wall_sec):
            tick = time.perf_counter()
            # paths.py calls mkdir(exist_ok=True); refuse missing/linked cache
            # directories so importing it cannot create a public/cache tree.
            for name in ("HF", "HF/hub", "data_cache", "runs", "runs/ckpt", "runs/logs"):
                if not safe_path(name).is_dir():
                    raise ValueError("existing runtime directory required before imports: " + name)
            import tinylm  # noqa:F401  # Cache redirection precedes third-party imports.
            from scripts import diag_p101a_sft_mtp as engine
            from scripts import diag_p101a_clean_bilingual as clean
            from tinylm.train import mtp_sft as core
            result["stages"]["runtime_import_seconds"] = time.perf_counter() - tick
            guard.check("before metadata")
            tick = time.perf_counter()
            if digest(safe_path(CORPUS + "/report.json")) != CORPUS_SHA:
                raise ValueError("pinned V3 corpus report differs before shard verification")
            report = engine.corpus_report(safe_path(CORPUS))
            assets = asset_manifest(engine, report)
            result["assets_before"] = assets
            result["stages"]["metadata_and_hash_seconds"] = time.perf_counter() - tick
            result["gpu_admission_before_parent"] = gpu_admission()
            guard.check("before CPU parent")
            tick = time.perf_counter()
            torch, template, cfg, tok, initial_sha = engine.load_runtime("parent_ntp")
            if cfg.cla_group != 2 or not cfg.grad_checkpoint or cfg.mtp_aux or cfg.train_repeat != 1.0:
                raise ValueError("exact parent CLA2/checkpointON/R1/MTPoff required")
            if any(isinstance(module, torch.nn.Dropout) and module.p for module in template.modules()):
                raise ValueError("dropout0 diagnostic contract required")
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            result["runtime"] = dict(python=sys.version, torch=torch.__version__, cuda=torch.version.cuda,
                cuda_launch_blocking=os.environ.get("CUDA_LAUNCH_BLOCKING"),
                allocator=os.environ.get("PYTORCH_CUDA_ALLOC_CONF"),
                deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
                flash_sdp=torch.backends.cuda.flash_sdp_enabled(),
                memory_efficient_sdp=torch.backends.cuda.mem_efficient_sdp_enabled(),
                math_sdp=torch.backends.cuda.math_sdp_enabled())
            records = clean.encoded(safe_path(CORPUS), report, tok)
            if len(records["train"]) != 22528 or len(records["val"]) != 512:
                raise ValueError("complete original V3 corpus rows required")
            available = list(itertools.islice(engine.batches(records["train"], 0), WARMUP + MEASURED))
            if len(available) != WARMUP + MEASURED:
                raise ValueError("all six predetermined updates required")
            plans = [update_plan(groups) for groups in available]
            if sum(r.targets for r in records["train"]) != 552609 or sum(r.x_tokens for r in records["train"]) != 5405444:
                raise ValueError("original V3 actual input/supervision mass differs")
            initial_state = cpu_copy(template.state_dict())
            model_class = type(template)
            pad = tok.token_to_id("<|pad|>")
            if pad is None:
                pad = tok.token_to_id("<pad>")
            if type(pad) is not int or not 0 <= pad < 32768:
                raise ValueError("exact valid PAD identity required")
            result.update(initial_core_sha256=initial_sha, student_cfg=copy.deepcopy(cfg.__dict__),
                plans=plans, timing_schedule=block_schedule(), actual_parent_loads=1,
                initial_state_scope="one CPU-only original checkpoint state; each GPU arm rebuilt strictly from these CPU tensors",
                optimizer=dict(factory="scripts.diag_p101a_sft_mtp.optimizers", adam_lr=5e-5, muon_lr=2e-4,
                    clip=1.0, state="fresh for each correctness arm/ABBA block", resets_within_block=0),
                parameter_dtype="FP32", tf32=False, dropout=0)
            result["stages"]["parent_encoding_cpu_snapshot_seconds"] = time.perf_counter() - tick
            del template
            template = None

            def fresh_model(block):
                guard.check("before GPU model")
                admission = gpu_admission(torch)
                torch.manual_seed(SEED)
                candidate = model_class(copy.deepcopy(cfg))
                candidate.load_state_dict(initial_state, strict=True)
                candidate.set_anneal(1.0)
                if engine.state_fingerprint(candidate) != initial_sha:
                    raise ValueError("fresh CPU model differs from original initial core")
                candidate._padding_pad_id = pad
                candidate.train()
                candidate = candidate.cuda()
                opts = engine.optimizers(candidate)
                for group in opts[0].param_groups:
                    group["lr"] = 5e-5
                for group in opts[1].param_groups:
                    group["lr"] = 2e-4
                owned = [id(p) for opt in opts for group in opt.param_groups for p in group["params"]]
                if len(owned) != len(set(owned)) or set(owned) != {id(p) for p in candidate.parameters() if p.requires_grad}:
                    raise ValueError("optimizer ownership must be complete and nonduplicated")
                torch.manual_seed(SEED)
                torch.cuda.synchronize()
                rng = rng_identity(torch)
                if result["blocks"] and rng != result["blocks"][0]["initial_rng_sha256"]:
                    raise ValueError("block RNG initial state differs")
                result["blocks"].append(dict(block=block, initial_core_sha256=initial_sha,
                    initial_rng_sha256=rng, gpu_admission=admission, fresh_optimizer=True,
                    model_compile=False, checkpoint=True, cla_group=2,
                    device=torch.cuda.get_device_name(), device_capability=list(torch.cuda.get_device_capability()),
                    normalization="RMSNorm has no trainable parameters; preclip global gradient norm and every trainable tensor are recorded"))
                return candidate, opts

            def release_gpu():
                nonlocal model, optimizers
                torch.cuda.synchronize()
                model_reference = weakref.ref(model)
                parameter_references = [weakref.ref(p) for p in model.parameters()]
                if model is not None:
                    model.clear_quant()
                optimizers = model = None
                gc.collect()
                audit = dict(model_still_alive=model_reference() is not None,
                    parameters_still_alive=sum(reference() is not None for reference in parameter_references),
                    explicit_workspace_cleanup=release_workspace)
                result["gpu_release_audits"].append(audit)
                if audit["model_still_alive"] or audit["parameters_still_alive"]:
                    raise RuntimeError("previous model/parameter object still alive after release")
                if release_workspace:
                    audit.update(clear_runtime_workspace(torch))
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                audit["final_allocated_bytes"] = torch.cuda.memory_allocated()
                journal.append(dict(event="gpu_release", **audit))
                if release_workspace and audit["final_allocated_bytes"] != 0:
                    raise RuntimeError("live CUDA allocation remains after explicit workspace cleanup")

            if args.mode == "correctness":
                snapshots = []
                for block, policy in enumerate(POLICIES):
                    tick = time.perf_counter()
                    model, optimizers = fresh_model(block)
                    result["stages"]["rebuild_block_" + str(block)] = time.perf_counter() - tick
                    update, gradients = one_update(torch, core, model, optimizers, available[0], plans[0], policy,
                        "fp32_math", guard, journal, block, 0, "correctness", capture=True)
                    result["updates"].append(update)
                    snapshots.append(dict(gradients=gradients, parameters=cpu_copy(dict(model.named_parameters())),
                                          optimizer=optimizer_snapshot(torch, model, optimizers)))
                    result["blocks"][-1]["final_rng_sha256"] = rng_identity(torch)
                    release_gpu()
                guard.check("before complete CPU comparison")
                tick = time.perf_counter()
                comparisons = {
                    "loss": scalar_difference(result["updates"][0]["loss"], result["updates"][1]["loss"], tolerances["loss_and_norm"]),
                    "preclip_norm": scalar_difference(result["updates"][0]["preclip_norm"], result["updates"][1]["preclip_norm"], tolerances["loss_and_norm"]),
                    "gradients": tensor_table(torch, snapshots[0]["gradients"], snapshots[1]["gradients"], tolerances["gradients_and_update"]),
                    "updated_parameters": tensor_table(torch, snapshots[0]["parameters"], snapshots[1]["parameters"], tolerances["gradients_and_update"]),
                    "optimizer_state": tensor_table(torch, snapshots[0]["optimizer"], snapshots[1]["optimizer"], tolerances["gradients_and_update"]),
                }
                result.update(comparisons=comparisons, correctness_pass=all(v["close"] for v in comparisons.values()),
                    tied_gradient_scope="emb.weight and emb_up.weight included among all parameters; full graph sums their input and output paths before clipping",
                    status="CORRECTNESS_COMPLETE" if all(v["close"] for v in comparisons.values()) else "NUMERICAL_DIAGNOSTIC_NEGATIVE")
                result["shared_input_output_gradients"] = {
                    row["name"]: row for row in comparisons["gradients"]["per_parameter"]
                    if row["name"] in ("emb.weight", "emb_up.weight")}
                if set(result["shared_input_output_gradients"]) != {"emb.weight", "emb_up.weight"}:
                    raise ValueError("required tied embedding/up-projection gradient summaries absent")
                result["stages"]["cpu_all_parameter_comparison_seconds"] = time.perf_counter() - tick
                result["returncode"] = 0 if result["correctness_pass"] else 9
                write_new(target / "comparisons.json", comparisons)
                del snapshots
            else:
                for block in block_schedule():
                    tick = time.perf_counter()
                    model, optimizers = fresh_model(block["block"])
                    result["stages"]["rebuild_block_" + str(block["block"])] = time.perf_counter() - tick
                    for step in block["updates"]:
                        index = step["index"]
                        update, _ = one_update(torch, core, model, optimizers, available[index], plans[index], block["policy"],
                            "bf16_eager", guard, journal, block["block"], index, step["phase"])
                        result["updates"].append(update)
                    result["blocks"][-1]["final_rng_sha256"] = rng_identity(torch)
                    release_gpu()
                measured = [u for u in result["updates"] if u["phase"] == "measured"]
                warmup = [u for u in result["updates"] if u["phase"] == "warmup"]
                result.update(status="TIMING_ABBA_COMPLETE", returncode=0,
                    timing_summary={policy: dict(measured_updates=sum(u["policy"] == policy for u in measured),
                        whole_update_seconds=sum(u["whole_update_seconds"] for u in measured if u["policy"] == policy),
                        warmup_update_seconds=sum(u["whole_update_seconds"] for u in warmup if u["policy"] == policy),
                        measured_actual_x_tokens=sum(u["actual_x_tokens"] for u in measured if u["policy"] == policy),
                        measured_targets=sum(u["assistant_targets"] for u in measured if u["policy"] == policy),
                        measured_padded_slots=sum(u["padded_slots"] for u in measured if u["policy"] == policy)) for policy in POLICIES},
                    correctness_status="SEPARATE_REPORT_REQUIRED; timing completion is not numerical equivalence or adoption",
                    timing_scope="single-seed sequential ABBA, BF16 eager,2 warmup+4 measured per fresh block; no compile/time-to-quality claim")
            guard.check("after diagnostics")
    except BaseException as error:
        result.update(status="INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "EXECUTION_ERROR", returncode=130 if isinstance(error, KeyboardInterrupt) else 9,
                      error=dict(type=type(error).__name__, message=str(error)[:2000]))
        try:
            journal.append(dict(event="error", error=result["error"], at=utc_now().isoformat()))
        except Exception as journal_error:
            result["journal_error"] = str(journal_error)[:1000]
    finally:
        if torch is not None:
            try:
                if model is not None:
                    model.clear_quant()
                optimizers = model = template = None
                gc.collect()
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            except Exception as error:
                result.update(cleanup_error=str(error)[:1000], status="GPU_CLEANUP_ERROR", returncode=9)
        tick = time.perf_counter()
        try:
            after_sources = source_manifest()
            result["sources_unchanged"] = after_sources == sources
            if assets is not None:
                after_assets = {name: digest(safe_path(name)) for name in assets}
                result["assets_after"] = after_assets
                result["assets_unchanged"] = after_assets == assets
            if not result["sources_unchanged"] or (assets is not None and not result["assets_unchanged"]):
                result.update(status="INPUT_IDENTITY_CHANGED", returncode=9)
        except Exception as error:
            result.update(status="FINAL_IDENTITY_AUDIT_ERROR", returncode=9, final_audit_error=str(error)[:1000])
        result["stages"]["final_hash_audit_seconds"] = time.perf_counter() - tick
        result.update(ended_at=utc_now().isoformat(), whole_worker_seconds=time.perf_counter() - began,
                      event_rows=journal.rows, event_bytes=journal.bytes, complete=result["returncode"] == 0)
        journal.close()
        write_new(target / "report.json", result)
        print("[PADDING_DIAGNOSTIC] " + json.dumps({k: result[k] for k in ("status", "returncode", "complete", "whole_worker_seconds", "checkpoint_writes", "production_adopted")}, ensure_ascii=False), flush=True)
    return result["returncode"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--mode", choices=("correctness", "timing"), default="correctness")
    parser.add_argument("--deadline", help="aware ISO timestamp, no later than2026-10-23 16:30KST")
    parser.add_argument("--max-wall-sec", type=int, default=1200)
    parser.add_argument("--output", help="exact fresh test_result/evidence/p101a_padding_gpu_v1_s1337/{mode}")
    parser.add_argument("--source-sha256", help="aggregate source SHA from --check-only")
    parser.add_argument("--release-cublas-workspace", action="store_true",
                        help="opt-in diagnostic runtime-workspace cleanup in separate workspace_v2 namespace")
    args = parser.parse_args(argv)
    sources = source_manifest()
    tolerances = literal_tolerances()
    if args.check_only:
        print(json.dumps(dict(schema=SCHEMA, status="SOURCE_ONLY_READY", source_sha256=identity(sources), sources=sources,
            tolerances=tolerances, execution_plan=block_schedule(), model_loads=0, asset_reads=0, gpu_calls=0,
            checkpoint_writes=0, claim="source contract only; runtime/numeric/speed NOT_RUN"), ensure_ascii=False, sort_keys=True))
        return 0
    if not args.output or not args.deadline or not args.source_sha256:
        parser.error("execute needs exact --output, --deadline and --source-sha256")
    return execute(args, sources, tolerances)


if __name__ == "__main__":
    raise SystemExit(main())
