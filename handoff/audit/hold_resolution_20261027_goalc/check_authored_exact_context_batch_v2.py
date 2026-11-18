"""Extend unchanged literal checks to exact list reviews from L/G roles."""
from pathlib import Path
import argparse
import hashlib
import sys

AUDIT = Path(__file__).resolve().parent
sys.path[:0] = [str(AUDIT), str(AUDIT.parents[2])]
frozen = AUDIT / 'check_authored_exact_context_batch_v1.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper() == '74B4C0DA26EDB90F5A49CAD3133C7DD473CDA55DCB09CD41D9A59FD935381FF3'
import check_authored_exact_context_batch_v1 as previous

# Only source-specific unfinished-prose judgments are added. The complete
# literal, numeric, code, quote, delimiter and metadata guards remain unchanged.
previous.ALLOWED = dict(previous.ALLOWED,
    l_partial_deletions={previous.PROSE}, g_partial_context={previous.PROSE})
old_read = previous.read_metadata


def read_metadata(pin, pins):
    pins[str(Path(__file__).relative_to(previous.ROOT))] = previous.guard.inv.file_sha(Path(__file__))
    return old_read(pin, pins)


previous.read_metadata = read_metadata

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    previous.run(Path(parser.parse_args().config).resolve())
