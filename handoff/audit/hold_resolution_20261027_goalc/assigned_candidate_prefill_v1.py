"""Create only own missing final TXTs from exact assigned candidate bytes."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
FROZEN=AUDIT/'assigned_final_literal_review_v1.py'
assert not FROZEN.is_symlink() and hashlib.sha256(FROZEN.read_bytes()).hexdigest().upper()==\
    'E5EA73B8543BF79B22D8A01CC2B91D74922115AFBD96BEEB2B42F8674CC055E8'
import assigned_final_literal_review_v1 as review


def prefill(root,role,cohort,pairs,core,scope,read_metadata,contract,read_payload=None):
    core.require(1<=len(pairs)<=5 and len({p[0] for p in pairs})==len(pairs),
        'one to five distinct assigned IDs required')
    planned=[]
    for ident,basename in pairs:
        context=core.resolve_assignment(root,scope,role,cohort,ident,read_metadata)
        review.transport.guard.require_payload_context(context,contract)
        path,_=review.target(root,context,basename,context['candidate']['sha256'],core)
        core.require(path.parent.is_dir() and not path.exists(),'own output folder must exist and final TXT must be new')
        planned.append((context,path))
    read_payload=read_payload or core.base.bounded_payload
    prepared=[]
    for context,path in planned:
        raw=read_payload(root,context['candidate'])
        core.require(len(raw)<core.base.LIMIT_BYTES and core.base.digest(raw)==context['candidate']['sha256'],
            'candidate bytes changed; no output created')
        prepared.append((context,path,raw))
    result=[]
    for context,path,raw in prepared:
        with path.open('xb') as stream:stream.write(raw)
        result.append(dict(source_id=context['source_id'],final=dict(path=str(path.relative_to(root)),
            sha256=context['candidate']['sha256'],bytes=len(raw))))
    return result


def cli(root,role):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page',type=int)
    parser.add_argument('id_and_basename',nargs='+')
    args=parser.parse_args()
    if args.page<1 or len(args.id_and_basename)%2 or not 2<=len(args.id_and_basename)<=10:
        parser.error('PAGE and one to five ID FINAL_BASENAME pairs required')
    pairs=[('expanded_train:'+ident if ident.isdigit() else ident,name)
        for ident,name in zip(args.id_and_basename[::2],args.id_and_basename[1::2])]
    review.transport.guard.activate();contract=review.transport.guard.checked_contract()
    if {ident for ident,_ in pairs}&(set(contract['restricted_ids'])|set(contract['trusted_metadata'])):
        raise ValueError('restricted requested identity; no payload read')
    old=review.transport.frozen_batch();metadata,scope,core=old.setup(root,old.frozen_entry())
    cohort='remaining_field_title_page_'+format(args.page,'03d')+'_counter_v1'
    result=prefill(root,role,cohort,pairs,core,scope,review.transport.cached_reader(metadata.pinned),contract)
    review.transport.guard.assert_no_protected_opens()
    print('TRUSTED_OWN_CANDIDATE_PREFILL '+json.dumps(dict(role=role,cohort=cohort,outputs=result,
        original_payload_opens=0,exact_candidate_prefill_only=True,semantic_edit_performed=False,
        existing_file_overwrites=0,initial_candidate_extra_copy_created=False,first_read_credit=0,
        root_or_cache_admission=False),ensure_ascii=False,separators=(',',':')))
