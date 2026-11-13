"""Report up to five own generated TXT identities; never open a source payload."""
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


def collect(root,role,cohort,pairs,core,scope,read_metadata,contract,read_payload=None):
    core.require(1<=len(pairs)<=5 and len({p[0] for p in pairs})==len(pairs),
        'one to five distinct own generated files required')
    prepared=[]
    for ident,basename in pairs:
        context=core.resolve_assignment(root,scope,role,cohort,ident,read_metadata)
        review.transport.guard.require_payload_context(context,contract)
        _path,pin=review.target(root,context,basename,'0'*64,core)
        prepared.append((context,pin['path']))
    # All source assignments and original/candidate SHA restrictions were
    # checked before this separate identity stage opens an OWN generated TXT.
    # No original/candidate payload path is used here, and no body is printed.
    read_payload=read_payload or core.base.bounded_payload
    identities=[]
    for context,name in prepared:
        raw=read_payload(root,dict(path=name))
        core.require(len(raw)<core.base.LIMIT_BYTES,'generated TXT exceeds the fixed size bound')
        pin=dict(path=name,sha256=core.base.digest(raw),bytes=len(raw))
        review.transport.guard.require_payload_context(dict(context,candidate=pin),contract)
        identities.append(dict(source_id=context['source_id'],final=pin))
    return identities


def cli(root,role):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page',type=int)
    parser.add_argument('id_and_basename',nargs='+')
    args=parser.parse_args()
    if args.page<1 or len(args.id_and_basename)%2 or not 2<=len(args.id_and_basename)<=10:
        parser.error('PAGE followed by one to five ID FINAL_BASENAME pairs required')
    pairs=[('expanded_train:'+ident if ident.isdigit() else ident,name)
        for ident,name in zip(args.id_and_basename[::2],args.id_and_basename[1::2])]
    review.transport.guard.activate();contract=review.transport.guard.checked_contract()
    if {ident for ident,_ in pairs}&(set(contract['restricted_ids'])|set(contract['trusted_metadata'])):
        raise ValueError('restricted requested identity; no payload read')
    old=review.transport.frozen_batch();metadata,scope,core=old.setup(root,old.frozen_entry())
    cohort='remaining_field_title_page_'+format(args.page,'03d')+'_counter_v1'
    identities=collect(root,role,cohort,pairs,core,scope,review.transport.cached_reader(metadata.pinned),contract)
    review.transport.guard.assert_no_protected_opens()
    print('TRUSTED_OWN_FINAL_IDENTITIES '+json.dumps(dict(role=role,cohort=cohort,identities=identities,
        original_or_candidate_payload_opens=0,body_printed=False,body_written=False,
        final_UTF8_or_semantic_validation_performed=False,first_read_credit=0,root_or_cache_admission=False),
        ensure_ascii=False,separators=(',',':')))
