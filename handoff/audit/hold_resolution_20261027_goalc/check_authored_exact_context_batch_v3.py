"""Retain literal proofs; recognize width pairs and the actual H review role."""
from pathlib import Path
import argparse
import hashlib
import sys

AUDIT = Path(__file__).resolve().parent
sys.path[:0] = [str(AUDIT), str(AUDIT.parents[2])]
V1 = AUDIT / 'check_authored_exact_context_batch_v1.py'
assert hashlib.sha256(V1.read_bytes()).hexdigest().upper() == \
    '74B4C0DA26EDB90F5A49CAD3133C7DD473CDA55DCB09CD41D9A59FD935381FF3'
import check_authored_exact_context_batch_v1 as previous
import structural_delimiter_deferrals_v2 as brackets

previous.ALLOWED = dict(previous.ALLOWED,
    l_partial_deletions={previous.PROSE}, g_partial_context={previous.PROSE},
    h_small_word_changes={previous.PROSE})
previous.delimiter_deferrals = brackets.deferrals
old_read = previous.read_metadata


def read_metadata(pin, pins):
    for path in [Path(__file__), Path(brackets.__file__), V1]:
        pins[str(path.relative_to(previous.ROOT))] = previous.guard.inv.file_sha(path)
    return old_read(pin, pins)


previous.read_metadata = read_metadata

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    previous.run(Path(parser.parse_args().config).resolve())
