"""Opt-in, bounded timeout recovery for memory queries, never GPU error recovery.

The old reader and teacher lifecycle remain unchanged outside this adapter.
Missing observations are recorded; no peak/OOM safety is inferred across gaps.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import subprocess
import threading
import time

POLICY = "P106B_VRAM_TIMEOUT_RETRY_V1"
MAX_ATTEMPTS = 3  # First query included; each existing reader has a 5s timeout.
MAX_EVENTS = 128


class RetryingMemoryReader:
    def __init__(self, reader, *, emit=print, clock=time.monotonic,
                 pause=time.sleep, max_attempts=MAX_ATTEMPTS):
        if not 1 <= max_attempts <= MAX_ATTEMPTS:
            raise ValueError("memory query attempts must be 1..3")
        self.reader, self.emit, self.clock, self.pause = reader, emit, clock, pause
        self.max_attempts = max_attempts
        self.started = clock()
        self.lock = threading.RLock()
        self.calls = self.successes = self.timeouts = self.recovered = self.failed = 0
        self.events = []
        self.event_count = 0
        self.chain = hashlib.sha256()
        self.gap_seconds = 0.0
        self.peak = self.minimum_free = None

    def event(self, kind, **fields):
        packet = dict(kind=kind, utc=datetime.now(timezone.utc).isoformat(),
                      elapsed_sec=self.clock()-self.started, **fields)
        encoded = json.dumps(packet, sort_keys=True, ensure_ascii=False)
        self.chain.update((encoded+"\n").encode("utf-8"))
        self.event_count += 1
        if len(self.events) < MAX_EVENTS:
            self.events.append(packet)
            self.emit("[VRAM_QUERY_EVENT] "+encoded)
        elif self.event_count == MAX_EVENTS+1:
            self.emit("[VRAM_QUERY_EVENT_LIMIT] first128 retained; all counts and event-chain SHA retained")

    def __call__(self):
        # Serialize calls so baseline/worker queries cannot race the retry budget.
        with self.lock:
            self.calls += 1
            began = self.clock()
            had_timeout = False
            try:
                for attempt in range(1, self.max_attempts+1):
                    try:
                        value = self.reader()
                    except subprocess.TimeoutExpired:
                        had_timeout = True
                        self.timeouts += 1
                        self.event("TIMEOUT", attempt=attempt,
                                   total_attempts=self.max_attempts,
                                   query_timeout_sec=5)
                        if attempt == self.max_attempts:
                            raise
                        self.pause(.2)
                        continue
                    used, free = value
                    if (type(used) is not int or type(free) is not int
                            or used < 0 or free < 0):
                        raise ValueError("invalid memory observation")
                    self.successes += 1
                    self.peak = used if self.peak is None else max(self.peak, used)
                    self.minimum_free = free if self.minimum_free is None else min(self.minimum_free, free)
                    if had_timeout:
                        self.recovered += 1
                        gap = self.clock()-began
                        self.gap_seconds += gap
                        self.event("RECOVERED", attempts=attempt,
                                   unobserved_query_window_sec=gap)
                    return used, free  # Low-free guards are still owned by Session.
            except BaseException as exc:
                self.failed += 1
                gap = self.clock()-began
                self.gap_seconds += gap
                self.event("FATAL_QUERY", error_type=type(exc).__name__,
                           unobserved_query_window_sec=gap)
                raise  # Non-timeout errors are never retried or suppressed.

    def snapshot(self):
        with self.lock:
            gaps = bool(self.timeouts or self.failed)
            return dict(schema=POLICY, maximum_attempts=self.max_attempts,
                        per_query_timeout_sec=5, retry_delay_sec=.2,
                        calls=self.calls, successful_queries=self.successes,
                        timeout_attempts=self.timeouts, recovered_calls=self.recovered,
                        fatal_calls=self.failed,
                        unobserved_query_window_sec=self.gap_seconds,
                        events=list(self.events), event_count=self.event_count,
                        omitted_event_count=self.event_count-len(self.events),
                        event_chain_sha256=self.chain.hexdigest().upper(),
                        measurement_coverage="GAPPED" if gaps else "SAMPLED_ONLY",
                        observed_global_peak_mib=self.peak,
                        observed_min_free_mib=self.minimum_free,
                        continuous_peak_verified=False, oom_safety="NOT_ESTABLISHED",
                        scope="Only subprocess.TimeoutExpired retries; no GPU reset/model restart; gaps never interpolated")
