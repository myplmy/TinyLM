"""Exit successfully only after a specific P109 supervisor returns its CUDA device."""

import argparse
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import time


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "test_result" / "evidence"


def wait_for_return(terminal, pid, deadline):
    lock = os.open(ROOT / "runs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        while time.time() < deadline.timestamp():
            if terminal.is_file():
                record = json.loads(terminal.read_text(encoding="utf-8"))
                returned = record.get("card_after_exit") or {}
                if (record.get("pid") != pid or record.get("returncode") != 0
                        or record.get("stop_reason") is not None or returned.get("compute_pids") != []
                        or not isinstance(record.get("ended"), (int, float))
                        or not isinstance(returned.get("sampled_at"), (int, float))
                        or returned["sampled_at"] < record["ended"]
                        or not isinstance(returned.get("free_mib"), int)
                        or not terminal.with_name("report.json").is_file()):
                    raise ValueError(f"P109 owner {pid} has no successful termination and return receipt")
                try:
                    fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
                except BlockingIOError:
                    pass
                else:
                    print(json.dumps(dict(predecessor=pid, returned_at=returned["sampled_at"],
                                          released_lock_at=time.time(), free_mib=returned["free_mib"])), flush=True)
                    return
            time.sleep(min(.5, max(0., deadline.timestamp() - time.time())))
        raise TimeoutError(f"P109 owner {pid} did not return before the queue cutoff")
    finally:
        os.close(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supervisor", type=Path, required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--until", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    terminal = args.supervisor.resolve()
    if (terminal.name != "supervisor.json" or terminal.parent.parent != EVIDENCE
            or not terminal.parent.name.startswith("p109") or args.pid <= 0 or not args.until.tzinfo):
        parser.error("requires one P109 evidence supervisor, its owned PID and a timezone-aware cutoff")
    wait_for_return(terminal, args.pid, args.until)


if __name__ == "__main__":
    main()
