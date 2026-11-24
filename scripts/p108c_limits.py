"""The new, explicit overnight authority; never extends old experiment guards."""
from datetime import datetime, timezone, timedelta
import math
import time

AUTHORITY_END = datetime(2026, 11, 16, 23, 0, tzinfo=timezone.utc)
CLEANUP_SECONDS = 1200


class Budget:
    def __init__(self, seconds=900):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("positive finite phase duration required")
        self.seconds = seconds
        self.started = time.monotonic()

    def check(self, *, now=None, elapsed=None, admission=False):
        now = datetime.now(timezone.utc) if now is None else now
        elapsed = time.monotonic() - self.started if elapsed is None else elapsed
        if now.tzinfo is None or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("aware clock and finite nonnegative elapsed duration required")
        remaining = (AUTHORITY_END - timedelta(seconds=CLEANUP_SECONDS) - now).total_seconds()
        if remaining <= 0 or elapsed >= self.seconds:
            raise TimeoutError("night phase or Nov17 07:40KST cleanup boundary reached")
        if admission and self.seconds > remaining:
            raise TimeoutError("complete declared phase no longer fits before cleanup")
        return remaining
