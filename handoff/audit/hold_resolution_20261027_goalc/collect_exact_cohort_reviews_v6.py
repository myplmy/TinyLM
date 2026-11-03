"""Opt in to an exact output-heading alias; reuse all prior binding guards."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from exact_review_header_alias_v1 import wrap_review_entries


def run(cohort, version):
    source = AUDIT / 'collect_exact_cohort_reviews_v5.py'
    environment = {'__name__': 'exact_collector_v5_reused', '__file__': __file__}
    exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), environment)
    original_load = environment['load_reused']

    def load_with_exact_header(path, scope):
        scope = original_load(path, scope)
        scope['review_entries'] = wrap_review_entries(scope['review_entries'])
        for pin in (source, AUDIT / 'exact_review_header_alias_v1.py'):
            scope['input_pins'][str(pin.relative_to(ROOT))] = inv.file_sha(pin)
        return scope

    environment['load_reused'] = load_with_exact_header
    return environment['collect'](cohort, version)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    run(args.cohort, args.version)
