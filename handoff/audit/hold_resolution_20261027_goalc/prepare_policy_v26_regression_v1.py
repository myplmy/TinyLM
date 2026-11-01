"""Reuse the entire361-case v25 suite with v26 plus nine boundary challenges."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
source = (ROOT / 'scripts/test_p106b_hold_resolution_policy_v25.py').read_text(encoding='utf-8')
before = 'from scripts import p106b_hold_resolution_policy_v25 as policy'
assert source.count(before) == 1
source = source.replace(before, 'from scripts import p106b_hold_resolution_policy_v26 as policy' + chr(10)
                        + 'from scripts import test_p106b_hold_resolution_metadata_v2 as metadata_tests')
before = 'classes = [ObservedSourceHolesAndEmptyLeaves, AliasScopeAndEnglishRoles, EntireMissingContentAxis]'
assert source.count(before) == 1
source = source.replace(before, 'classes = [ObservedSourceHolesAndEmptyLeaves, AliasScopeAndEnglishRoles, EntireMissingContentAxis, metadata_tests.TypedOrdinalMetadata]')
output = ROOT / 'scripts/test_p106b_hold_resolution_policy_v26.py'
compile(source, str(output), 'exec')
with output.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared inherited v25 regression suite and new ordinal proof tests under v26.')
