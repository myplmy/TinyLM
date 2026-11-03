"""Extend the frozen strict collector to one explicitly bounded new cohort."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from exact_review_header_alias_v2 import wrap_review_entries


def run(version):
    frozen = AUDIT / 'collect_exact_cohort_reviews_v5.py'
    environment = {'__file__': __file__, '__name__': 'strict_birth_second_collector'}
    exec(compile(frozen.read_text(encoding='utf-8'), str(frozen), 'exec'), environment)
    original_load = environment['load_reused']

    def load(path, scope):
        result = original_load(path, scope)
        result['review_entries'] = wrap_review_entries(result['review_entries'])
        for name in ('collect_exact_cohort_reviews_v5.py', 'exact_review_header_alias_v1.py',
                     'exact_review_header_alias_v2.py', 'collect_birth_root11_independent_v1.py'):
            pin = AUDIT / name
            result['input_pins'][str(pin.relative_to(ROOT))] = inv.file_sha(pin)
        return result

    environment['load_reused'] = load
    environment['ALLOWED'] = {'birth_root11_independent_v1': 2707}
    return environment['collect']('birth_root11_independent_v1', version)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    run(parser.parse_args().version)
