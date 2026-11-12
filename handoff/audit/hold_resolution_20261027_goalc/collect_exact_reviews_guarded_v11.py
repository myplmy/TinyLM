"""Reuse collector10 with exact MD status/output spelling normalization only."""
from pathlib import Path
import hashlib
import json
import sys
from unittest.mock import patch

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path.insert(0,str(AUDIT))
sys.path.insert(0,str(ROOT))
for name,expected in [
    ('collect_exact_reviews_guarded_v10.py','956ED28A7F5AF7964965A849236A17E40DFAD42B4E6995187108FBC2AFE322B6'),
    ('exact_review_output_cell_alias_v1.py','496A39C064224251C5C5F2833979E926DDEE3AB96EE40FC168FF7001A57CF4AF'),
    ('exact_review_header_alias_v2.py','F8E33D9225F2799076839EB07B34B1698760B87140F801CDD0362EFD84AADB7F')]:
    path=AUDIT/name
    assert not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest().upper()==expected,name
import exact_review_header_alias_v2 as headers
import exact_review_output_cell_alias_v1 as aliases
from scripts import p106b_hold_resolution_inventory as inv

frozen=AUDIT/'collect_exact_reviews_guarded_v10.py'
with patch.object(headers,'wrap_review_entries',aliases.wrap_review_entries):
    exec(compile(frozen.read_bytes(),str(frozen),'exec'),
         dict(__name__='__main__',__file__=str(Path(__file__))))
args=sys.argv[1:]
if '--phase' in args:
    phase=args[args.index('--phase')+1]
    page=int(args[args.index('--page')+1])
    version=args[args.index('--version')+1]
    cohort=(f'remaining_field_title_page_{page:03d}_counter_v1' if phase=='field'
            else f'remaining_other_types_page_{page:03d}_counter_v1')
    summary=inv.BASE/(cohort+'_snapshots')/version/'complete.json'
    complete=json.loads(summary.read_bytes())
    receipt=dict(status='EXACT_STATUS_ALIAS_AND_SINGLE_TXT_LOCAL_MD_NOTE_BINDING_NO_GUARD_WAIVER',
        normalizations=list(aliases.NORMALIZATIONS.values()),
        snapshot=dict(path=str(summary.relative_to(ROOT)),sha256=inv.file_sha(summary)),
        errors=len(complete['errors']),
        input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in [Path(__file__),frozen,
            AUDIT/'exact_review_output_cell_alias_v1.py',AUDIT/'exact_review_header_alias_v2.py',
            AUDIT/'REVIEW_CELL_ALIAS_TESTS_V1.log',ROOT/'scripts/p106b_hold_resolution_author_output_bindings_v1.py']},
        author_MD_or_TXT_modified=False,original_or_candidate_modified=False,
        protected_payload_guard_changed=False,root_adopted=0,cache_admitted=0,
        goal_complete=False,training_authorized=False)
    inv.write_json(AUDIT/f'OUTPUT_CELL_ALIAS_{phase.upper()}_{page:03d}_{version.upper()}_V1.json',receipt)
    print(json.dumps(dict(status=receipt['status'],normalizations=len(receipt['normalizations']),
                          page=page,version=version,errors=receipt['errors']),ensure_ascii=False))
