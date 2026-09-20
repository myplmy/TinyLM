#!/usr/bin/env python3
"""Shared measurement helpers for synthetic GPU attribution diagnostics.

The helpers deliberately keep four quantities separate:

* ``wall_sync_ms``: Python dispatch + GPU work + a synchronize per call.
* ``event_batch_ms``: CUDA-stream elapsed time across consecutive calls.
* ``host_enqueue_us``: host-side Python/dispatcher enqueue time before a final sync.
* profiler rows: individual operator/kernel attribution for a small sample.

CUDA Event time is *not* labelled kernel-only because it can include padding,
casts, reductions, allocations and every other GPU operation launched by the
callable.  The profiler output is the narrower evidence for individual ops.
"""
from __future__ import annotations

import statistics
import time
from collections.abc import Callable, Mapping


def parse_int_csv(raw: str, *, minimum: int = 1) -> list[int]:
    values: list[int] = []
    for item in raw.split(","):
        value = int(item.strip())
        if value < minimum:
            raise ValueError(f"values must be >= {minimum}: {value}")
        if value not in values:
            values.append(value)
    if not values:
        raise ValueError("at least one integer is required")
    return values


def median_mad(values: list[float]) -> tuple[float, float]:
    if not values:
        raise ValueError("cannot summarize an empty sample")
    center = statistics.median(values)
    mad = statistics.median(abs(value - center) for value in values)
    return center, mad


def tensor_mib(tensor) -> float:
    return tensor.numel() * tensor.element_size() / 2**20


def wall_sync_ms(torch, fn: Callable[[], object], *, warmup: int, iters: int) -> float:
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    samples = []
    for _ in range(iters):
        started = time.perf_counter()
        fn()
        torch.cuda.synchronize()
        samples.append((time.perf_counter() - started) * 1e3)
    return statistics.median(samples)


def event_batch_ms(torch, fn: Callable[[], object], *, warmup: int, iters: int) -> float:
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(iters):
        fn()
    end.record()
    end.synchronize()
    return float(start.elapsed_time(end)) / iters


def host_enqueue_us(torch, fn: Callable[[], object], *, warmup: int, iters: int) -> float:
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    started = time.perf_counter()
    for _ in range(iters):
        fn()
    elapsed = time.perf_counter() - started
    # Do not include the final drain in the host enqueue metric.  It remains
    # necessary before returning so later variants do not inherit queued work.
    torch.cuda.synchronize()
    return elapsed * 1e6 / iters


def peak_delta_mib(torch, fn: Callable[[], object]) -> float:
    torch.cuda.synchronize()
    baseline = torch.cuda.memory_allocated()
    torch.cuda.reset_peak_memory_stats()
    output = fn()
    torch.cuda.synchronize()
    peak = torch.cuda.max_memory_allocated()
    del output
    return max(0, peak - baseline) / 2**20


def measure_variants(
    torch,
    variants: Mapping[str, Callable[[], object]],
    *,
    rounds: int,
    warmup: int,
    iters: int,
) -> dict[str, dict[str, float]]:
    """Measure variants in alternating order and return median plus MAD.

    Even rounds use declaration order and odd rounds reverse it.  This does not
    eliminate clock/temperature drift, but prevents a fixed dense-then-candidate
    order from being the only evidence.
    """
    samples = {
        name: {"wall": [], "event": [], "host": [], "peak": []}
        for name in variants
    }
    names = list(variants)
    for round_index in range(rounds):
        order = names if round_index % 2 == 0 else list(reversed(names))
        for name in order:
            fn = variants[name]
            samples[name]["wall"].append(
                wall_sync_ms(torch, fn, warmup=warmup, iters=iters)
            )
            samples[name]["event"].append(
                event_batch_ms(torch, fn, warmup=warmup, iters=iters)
            )
            samples[name]["host"].append(
                host_enqueue_us(torch, fn, warmup=warmup, iters=iters)
            )
            samples[name]["peak"].append(peak_delta_mib(torch, fn))

    result: dict[str, dict[str, float]] = {}
    for name, by_metric in samples.items():
        row: dict[str, float] = {}
        for metric, values in by_metric.items():
            median, mad = median_mad(values)
            row[metric] = median
            row[f"{metric}_mad"] = mad
        result[name] = row
    return result


def profiler_rows(torch, fn: Callable[[], object], *, iters: int, limit: int = 8):
    """Return top profiler rows without writing a trace file."""
    activities = [torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA]
    with torch.profiler.profile(
        activities=activities,
        record_shapes=False,
        profile_memory=True,
        with_stack=False,
    ) as profile:
        for _ in range(iters):
            fn()
        torch.cuda.synchronize()

    rows = []
    for event in profile.key_averages():
        device_total = float(
            getattr(event, "self_device_time_total", 0.0)
            or getattr(event, "self_cuda_time_total", 0.0)
            or 0.0
        )
        cpu_total = float(getattr(event, "self_cpu_time_total", 0.0) or 0.0)
        device_memory = float(
            getattr(event, "self_device_memory_usage", 0.0)
            or getattr(event, "self_cuda_memory_usage", 0.0)
            or 0.0
        )
        if device_total <= 0.0 and cpu_total <= 0.0:
            continue
        rows.append(
            {
                "key": str(event.key),
                "calls": int(event.count),
                "device_us": device_total,
                "cpu_us": cpu_total,
                "device_memory_mib": device_memory / 2**20,
            }
        )
    rows.sort(key=lambda row: (row["device_us"], row["cpu_us"]), reverse=True)
    return rows[:limit]
