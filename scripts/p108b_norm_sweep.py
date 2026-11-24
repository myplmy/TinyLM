"""Scale the frozen protected interpolation without changing its solver."""
from datetime import datetime, timezone
import math
import time
import torch
from scripts import p108_nullspace_write as owner

AUTHORITY_END = datetime(2026, 11, 16, 8, tzinfo=timezone.utc)
CLEANUP_SECONDS = 1200


class Budget:
    def __init__(self, seconds=1800):
        if not isinstance(seconds, (float, int)) or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError('positive finite run duration required')
        self.seconds = seconds
        self.started = time.monotonic()

    def check(self, *, now=None, elapsed=None):
        now = datetime.now(timezone.utc) if now is None else now
        elapsed = time.monotonic() - self.started if elapsed is None else elapsed
        if now.tzinfo is None or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError('aware time and nonnegative finite elapsed duration required')
        if elapsed >= self.seconds or (AUTHORITY_END - now).total_seconds() <= CLEANUP_SECONDS:
            raise TimeoutError('afternoon run limit or Nov16 16:40KST cleanup boundary reached')


def full_solution(keys, values, protected, *, protect=True, rank_rtol=1e-8):
    if type(protect) is not bool or keys.ndim != 2 or values.ndim != 2 or protected.ndim != 2:
        raise ValueError('explicit protection and native two-dimensional columns required')
    selected = protected if protect else torch.zeros(1, keys.shape[0], dtype=torch.float64)
    factors, stats = owner.constrained_factors(keys.T, values.T, selected, rank_rtol=rank_rtol)
    full = factors['left'] @ factors['right']
    if not bool(torch.isfinite(full).all()) or float(full.norm()) <= 0:
        raise ValueError('finite nonzero interpolation required')
    return full, stats


def at_signal(full, signal):
    if (full.ndim != 2 or full.device.type != 'cpu' or full.requires_grad or
            not bool(torch.isfinite(full).all()) or not float(full.norm()) or
            not isinstance(signal, (float, int)) or not math.isfinite(signal) or signal <= 0):
        raise ValueError('finite detached CPU interpolation and positive signal required')
    return (full.double() * signal).float()


def delivery(delta, keys, values, protected, signal):
    if (delta.ndim != 2 or keys.ndim != 2 or values.ndim != 2 or protected.ndim != 2 or
            delta.shape[1] != keys.shape[0] or delta.shape[0] != values.shape[0] or
            keys.shape[1] != values.shape[1] or protected.shape[1] != delta.shape[1] or
            any(not bool(torch.isfinite(x).all()) for x in (delta, keys, values, protected)) or
            not isinstance(signal, (float, int)) or not math.isfinite(signal) or signal <= 0):
        raise ValueError('finite native delivery shapes and positive signal required')
    observed = delta.double() @ keys.double()
    target = values.double() * signal
    denominator = max(float(target.norm()), 1e-30)
    energy = max(float(values.double().square().sum()), 1e-30)
    return dict(target_relative_residual=float((observed - target).norm()) / denominator,
                target_signal_projection=float((observed * values.double()).sum()) / energy,
                protected_output_l2=float((delta.double() @ protected.double().T).norm()),
                norm=float(delta.double().norm()))


def selection_key(record):
    dev = record['dev']
    return (len(record['lost_original_protected_ids']),
            -(dev['target_exact'] + dev['other_exact']), dev['empty'],
            dev['unwanted_loops'], dev['question_echoes'], record['physical']['net_norm'], record['name'])
