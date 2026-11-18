"""Add an explicit proof type for source-reviewed round-closure repairs."""
from pathlib import Path
import argparse
import sys

AUDIT = Path(__file__).resolve().parent
sys.path[:0] = [str(AUDIT), str(AUDIT.parents[2])]
import check_authored_exact_context_batch_v3 as wrapper
import authored_round_closure_preservation_v1 as closure

previous = wrapper.previous
previous.preservation = closure.preservation
old_read = previous.read_metadata


def read_metadata(pin, pins):
    for path in [Path(__file__), Path(wrapper.__file__), Path(closure.__file__),
                 AUDIT / 'test_authored_round_closure_preservation_v1.py']:
        pins[str(path.relative_to(previous.ROOT))] = previous.guard.inv.file_sha(path)
    return old_read(pin, pins)


previous.read_metadata = read_metadata

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    previous.run(Path(parser.parse_args().config).resolve())
