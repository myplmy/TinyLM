"""Recover a real GPU telemetry sample after brief NVML failures."""

import json
import subprocess
import time


QUERY = ["nvidia-smi", "--query-gpu=memory.total,memory.used,utilization.gpu", "--format=csv,noheader,nounits"]
GRACE_SECONDS = 22


def gpu_status(record):
    deadline = time.monotonic() + GRACE_SECONDS
    attempt = 0
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            raise RuntimeError(f"no valid NVML card sample within {GRACE_SECONDS} seconds")
        try:
            reply = subprocess.run(QUERY, capture_output=True, text=True, timeout=min(3., left), check=False)
        except subprocess.TimeoutExpired:
            detail = dict(reason="TIMEOUT")
        else:
            if reply.returncode == 0:
                total, used, utilization = map(int, reply.stdout.strip().split(","))
                if not 0 <= used <= total or not 0 <= utilization <= 100:
                    raise ValueError("the GPU resource sample has invalid limits")
                return total, used, utilization
            if reply.returncode != 255:
                raise subprocess.CalledProcessError(reply.returncode, QUERY, output=reply.stdout, stderr=reply.stderr)
            detail = dict(reason="NVML_EXIT_255", diagnostic=(reply.stderr.strip() or reply.stdout.strip())[:600])
        attempt += 1
        with (record / "telemetry_retries.jsonl").open("a", encoding="utf-8") as stream:
            print(json.dumps(dict(unix_seconds=time.time(), attempt=attempt, **detail)), file=stream)
        time.sleep(min(1., max(0., deadline - time.monotonic())))
