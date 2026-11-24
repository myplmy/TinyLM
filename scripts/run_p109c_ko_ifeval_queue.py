"""Run the sealed Korean reply benchmark and record actual decoding progress."""

import argparse
from datetime import datetime
from functools import partial
import json
from pathlib import Path
import time
from unittest.mock import patch

from scripts import eval_p109c_ko_ifeval_replies as korean
from scripts import p109_eval_resilient_supervisor as supervisor
from scripts import wait_p109_cuda_return as returned


def worker(previous, profile, checksum, resume, record, cutoff):
    original = korean.replies
    groups = tokens = 0
    last = time.monotonic()
    with (record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as output:
        def update():
            print(json.dumps(dict(unix_seconds=time.time(), groups=groups,
                                  generation_iterations_completed=tokens)), file=output)

        def replies(model, tokenizer, cases, check):
            nonlocal groups
            checkpoints = 0

            def check_progress():
                nonlocal tokens, last, checkpoints
                check()
                if checkpoints:
                    tokens += 16
                checkpoints += 1
                now = time.monotonic()
                if checkpoints > 1 and now - last >= 2:
                    update()
                    last = now

            rows = original(model, tokenizer, cases, check_progress)
            groups += 1
            update()
            return rows

        update()
        with patch.object(korean, "replies", replies):
            korean.worker(previous, profile, checksum, resume, record, cutoff)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    options = parser.parse_args()
    record = options.record.absolute()
    source = options.after.absolute()
    if (options.stop_by.tzinfo is None or record.exists() or source == record
            or any(path.parent != returned.EVIDENCE for path in (source, record))):
        parser.error("the queue requires fresh owned records and an authorized cutoff")
    checksum = korean.native.digest(options.profile_sha256)
    profile = options.profile.absolute()
    pinned = json.loads(korean.native.manifest_bytes(profile, checksum))
    if pinned["sources"] != korean.source_pins():
        raise ValueError("the benchmark sources differ from the frozen profile")
    terminal = source / "supervisor.json"
    while not terminal.is_file() and time.time() < options.stop_by.timestamp() - 1200:
        time.sleep(2.)
    if time.time() >= options.stop_by.timestamp() - 1200:
        raise TimeoutError("the queue no longer has a useful evaluation window")
    previous = None
    if options.previous is not None:
        previous = options.previous.absolute()
        if previous.parent != returned.EVIDENCE or previous == record:
            raise ValueError("the copied replies must come from a distinct owned record")
    owner = json.loads(terminal.read_bytes())
    returned.wait_for_return(terminal, owner["pid"], options.stop_by)
    return supervisor.supervise(partial(worker, previous), profile, checksum, record, options.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
