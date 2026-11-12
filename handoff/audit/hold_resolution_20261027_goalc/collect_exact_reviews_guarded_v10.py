"""Retain collector9 guards with one pinned non-decision correction memo.

The physical V1 registry stays unchanged. This exact process-local metadata
binding supplies V2, preserves its inherited rows, and records both input pins.
It cannot ignore arbitrary review files or change any corpus decision/body.
"""
from pathlib import Path
import hashlib
import json
import sys
from unittest.mock import patch

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv

frozen=AUDIT/'collect_exact_reviews_guarded_v9.py';raw=frozen.read_bytes()
assert inv.file_sha(frozen)=='68759913392F8DECEE352861C5E8764D0CACCD19D14AE6F9985E52954D9752DE'
old=AUDIT/'EXACT_COHORT_AUXILIARY_REVIEW_DISPOSITIONS_V1.json'
new=AUDIT/'EXACT_COHORT_AUXILIARY_REVIEW_DISPOSITIONS_V2.json'
assert inv.file_sha(old)=='708CACD97F10A7F5DEEEDF16D5B0D3C8F955A926A6319AF33465D1C29F18B84A'
assert inv.file_sha(new)=='2E6EFC3EC3F0E30F3D9CE3BF8AA3480F77FC83EDB82F44C65661CCF3995CF8B0'
prior=json.loads(old.read_bytes());current=json.loads(new.read_bytes())
assert current['rows'][:len(prior['rows'])]==prior['rows'] and len(current['rows'])==len(prior['rows'])+1
extra=current['rows'][-1]
assert extra['path']=='data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/historical_review/remaining_field_title_page_015_counter_v1/review_011_v2_output_path_correction.md'
assert extra['canonical_review'].endswith('/review_011_v3.md')
note=(ROOT/extra['path']).read_text(encoding='utf-8')
assert not any(line.startswith('|') for line in note.splitlines())
for record in current['rows']:
    assert record['root_approved'] is True and record['original_auxiliary_preserved'] is True
    assert inv.file_sha(ROOT/record['path'])==record['sha256']
    assert inv.file_sha(ROOT/record['canonical_review'])==record['canonical_review_sha256']
read=inv.cache.read


def bound_auxiliary(path):
    return current if Path(path).resolve()==old else read(path)


with patch.object(inv.cache,'read',bound_auxiliary):
    exec(compile(raw,str(frozen),'exec'),dict(__name__='__main__',__file__=str(Path(__file__))))
args=sys.argv[1:]
if '--phase' in args:
    phase=args[args.index('--phase')+1];page=int(args[args.index('--page')+1]);version=args[args.index('--version')+1]
    summary=inv.BASE/(f'remaining_{phase}_title_page_{page:03d}_counter_v1_snapshots' if phase=='field'
        else f'remaining_other_types_page_{page:03d}_counter_v1_snapshots')/version/'complete.json'
    assert summary.is_file()
    receipt=dict(status='EXACT_NONDECISION_AUXILIARY_METADATA_BINDING_NO_CORPUS_GUARD_WAIVER',
        old_registry=dict(path=str(old.relative_to(ROOT)),sha256=inv.file_sha(old)),
        effective_registry=dict(path=str(new.relative_to(ROOT)),sha256=inv.file_sha(new)),
        actual_snapshot=dict(path=str(summary.relative_to(ROOT)),sha256=inv.file_sha(summary)),
        only_one_source_free_note_excluded=True,canonical_five_row_review_preserved=True,
        input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in [Path(__file__),frozen,old,new]},
        source_original_or_candidate_modified=False,root_adopted=0,cache_admitted=0,
        goal_complete=False,training_authorized=False)
    inv.write_json(AUDIT/f'AUXILIARY_BINDING_{phase.upper()}_{page:03d}_{version.upper()}_V1.json',receipt)
