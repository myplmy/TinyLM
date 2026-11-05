"""Guard5 before reusing collector8 in an exact disjoint field/other cohort."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
sys.path.insert(0,str(AUDIT));sys.path.insert(0,str(ROOT))
from active_guard_v5_preflight_v1 import activate,checked_contract,assert_no_protected_opens,EXPECTED,CONTRACT
from scripts import p106b_hold_resolution_inventory as inv
activate();guard=checked_contract()
parser=argparse.ArgumentParser();choice=parser.add_mutually_exclusive_group(required=True)
choice.add_argument('--cohort');choice.add_argument('--phase',choices=['field','other'])
parser.add_argument('--page',type=int);parser.add_argument('--version',required=True)
args=parser.parse_args()
if args.cohort:
    import re
    assert re.fullmatch(r'(?:remaining_[a-z_]+|root12_independent_admission_counter)_v1',args.cohort)
    manifest_path=inv.BASE/args.cohort/'manifest.json'
else:
    group={'field':'remaining_field_title_readers_v1','other':'remaining_other_types_readers_v1'}[args.phase]
    index_path=inv.BASE/group/'complete.json';index=inv.cache.read(index_path)
    page,=[r for r in index['pages'] if r['page']==args.page]
    manifest_path=ROOT/page['path'];assert inv.file_sha(manifest_path)==page['sha256']
sources=inv.cache.read(manifest_path)['rows']
new_ids={r['id'] for r in guard['newly_quarantined_entries']}
new_hashes={r[label]['sha256'] for r in guard['newly_quarantined_entries'] for label in ['original','derived_candidate']}
assert not any(r['id'] in new_ids or any(r[label]['sha256'] in new_hashes
    for label in ['original','candidate']) for r in sources), 'new quarantine needs exact metadata-only collector; no payload read'
frozen=AUDIT/'collect_exact_reviews_guarded_v8.py';raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='FAB264CA899755A5BFCA3DCCB812B7B4460231A46D30A8A2DFEDA564D480556C'
exec(compile(raw,str(frozen),'exec'),dict(__name__='__main__',__file__=str(Path(__file__))))
assert_no_protected_opens()
if args.phase:
    receipt=AUDIT/f'EXACT_PAGE_REVIEW_{args.phase.upper()}_{args.page:03d}_{args.version.upper()}.json'
    p=AUDIT/f'GUARD5_{args.phase.upper()}_{args.page:03d}_{args.version.upper()}_PREFLIGHT_BINDING_V1.json'
    assert not p.exists()
    inv.write_json(p,dict(status='GUARD5_EXACT_DISJOINT_SCOPE_WITH_ZERO_PROTECTED_PAYLOAD_ATTEMPTS',
        guard_sha256=EXPECTED,manifest=dict(path=str(manifest_path.relative_to(ROOT)),sha256=inv.file_sha(manifest_path)),
        snapshot_receipt=dict(path=str(receipt.relative_to(ROOT)),sha256=inv.file_sha(receipt)),
        input_pins={str(q.relative_to(ROOT)):inv.file_sha(q) for q in [CONTRACT,Path(__file__),frozen,AUDIT/'active_guard_v5_preflight_v1.py']},
        protected_payload_open_attempts=0,goal_complete=False,training_authorized=False))
