"""Reuse the coverage-only join for an explicitly versioned later snapshot."""
from pathlib import Path
import argparse
import re

AUDIT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--snapshot-version', required=True)
parser.add_argument('--report-version', required=True)
args = parser.parse_args()
assert re.fullmatch(r'v[1-9][0-9]*', args.snapshot_version)
assert re.fullmatch(r'v[2-9][0-9]*', args.report_version)
frozen = AUDIT / 'bridge_root_and_birth_review_coverage_v1.py'
code = frozen.read_text(encoding='utf-8')
edits = {
    'birth_root11_independent_v1_snapshots/v3/complete.json':
        'birth_root11_independent_v1_snapshots/' + args.snapshot_version + '/complete.json',
    'ROOT11_AND_BIRTH_SAVED_REVIEW_COVERAGE_BRIDGE_V1.json':
        'ROOT11_AND_BIRTH_SAVED_REVIEW_COVERAGE_BRIDGE_' + args.report_version.upper() + '.json',
    'inv.write_json(out, result)':
        "result['input_pins'][str(frozen.relative_to(ROOT))] = inv.file_sha(frozen)" + chr(10) + 'inv.write_json(out, result)',
}
for before, after in edits.items():
    assert code.count(before) == 1
    code = code.replace(before, after, 1)
exec(compile(code, str(frozen), 'exec'), {'__file__': __file__, '__name__': 'reused_saved_coverage', 'frozen': frozen})
