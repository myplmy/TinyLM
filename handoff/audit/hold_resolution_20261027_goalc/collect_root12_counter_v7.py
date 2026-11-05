"""Reuse guard4 collection with first-cell declaration checks and old logs intact."""
from pathlib import Path
import hashlib
import sys
from unittest.mock import patch

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_review_safeguards_v3 as old_safeguards
from scripts import p106b_hold_resolution_review_safeguards_v4 as safeguards

frozen = AUDIT/'collect_root12_counter_v6.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'CC1BC862BCE892FE8BE53AD2456742B2B553ABE8EC087552F96C253A17CC6569'
original_read = Path.read_text
core = AUDIT/'collect_root12_counter_v1.py'


def bind_current_safeguards(path, *args, **kwargs):
    code = original_read(path, *args, **kwargs)
    if path.resolve() == core:
        anchor = 'summary=dict(status='
        assert code.count(anchor) == 1
        extra = """for current_input in [ROOT/'scripts/p106b_hold_resolution_review_safeguards_v4.py',
    AUDIT/'collect_root12_counter_v6.py',AUDIT/'collect_root12_counter_v7.py']:
    env['input_pins'][str(current_input.relative_to(ROOT))]=inv.file_sha(current_input)
"""
        code = code.replace(anchor, extra + anchor)
    return code


with patch.object(Path, 'read_text', bind_current_safeguards), patch.object(
    old_safeguards, 'unparsed_declared_review_ids', safeguards.unparsed_declared_review_ids):
    exec(compile(raw, str(frozen), 'exec'), dict(__name__='guard4_counter7_actual_run',
        __file__=str(Path(__file__))))
