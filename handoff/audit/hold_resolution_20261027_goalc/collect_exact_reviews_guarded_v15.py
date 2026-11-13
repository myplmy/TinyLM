"""Reuse guard6 collector13 with explicit relative Markdown output metadata."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import runpy
import sys

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path[:0]=[str(AUDIT),str(ROOT)]
import exact_review_output_cell_alias_v2 as previous
import exact_review_output_cell_alias_v3 as current

frozen=AUDIT/'collect_exact_reviews_guarded_v13.py'
assert not frozen.is_symlink() and hashlib.sha256(frozen.read_bytes()).hexdigest().upper()==\
    '33EB796A20851FC628B6B545623BA4CE32DAC9BF2B81317E7B6337012909688B'
arguments=sys.argv[1:]
assert '--phase' in arguments and '--cohort' not in arguments
phase=arguments[arguments.index('--phase')+1]
page=int(arguments[arguments.index('--page')+1])
version=arguments[arguments.index('--version')+1]
with patch.object(previous,'wrap_review_entries',current.wrap_review_entries):
    runpy.run_path(str(frozen),run_name='__main__')
import active_guard_v6_preflight_v1 as guard
guard.assert_no_protected_opens()
cohort=('remaining_field_title_page_' if phase=='field' else 'remaining_other_types_page_')+format(page,'03d')+'_counter_v1'
summary=guard.inv.BASE/(cohort+'_snapshots')/version/'complete.json'
complete=guard.inv.cache.read(summary)
assert not complete['errors']
receipt=dict(status='EXACT_MARKDOWN_TARGET_AND_OUTPUT_HEADER_BOUND_NO_CORPUS_GUARD_WAIVER',
    snapshot=dict(path=str(summary.relative_to(ROOT)),sha256=guard.inv.file_sha(summary)),
    normalizations=list(current.NORMALIZATIONS.values()),
    input_pins={str(path.relative_to(ROOT)):guard.inv.file_sha(path) for path in
        [Path(__file__),frozen,AUDIT/'exact_review_output_cell_alias_v3.py',
         AUDIT/'REVIEW_CELL_ALIAS_V3_TESTS_V1.log',guard.CONTRACT]},
    original_or_candidate_modified=False,author_MD_or_TXT_modified=False,
    protected_payload_open_attempts=0,root_adopted=0,cache_admitted=0,
    goal_complete=False,training_authorized=False)
out=AUDIT/('MARKDOWN_OUTPUT_BINDING_'+phase.upper()+'_'+format(page,'03d')+'_'+version.upper()+'_V1.json')
assert not out.exists()
guard.inv.write_json(out,receipt)
print(json.dumps(dict(status=receipt['status'],page=page,version=version,
    normalizations=len(receipt['normalizations']),errors=0)))
