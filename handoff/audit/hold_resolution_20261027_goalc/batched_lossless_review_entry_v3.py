"""Same exact input and frames; print their common context only once per batch."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import active_guard_v6_preflight_v1 as guard

PREVIOUS=AUDIT/'batched_lossless_review_entry_v2.py'
assert not PREVIOUS.is_symlink()
assert hashlib.sha256(PREVIOUS.read_bytes()).hexdigest().upper()=='D2BDBB34ED21647E25AC460D6BCCBA70A3621DE8C189CC464677532E2537CECE'
from batched_lossless_review_entry_v2 import frozen_batch


def emit(root,context,views,pieces):
    common={key:value for key,value in views.items() if key not in
        {'original','candidate','full_candidate','pair','changes'}}
    common.update(context)
    common.update(keep_output_absolute=str(root/context['original']['path']),
        accept_output_absolute=str(root/context['candidate']['path']),required_views=['pair'],
        changes=len(views['changes']),root_or_cache_admission=False,semantic_review_complete=False,
        code_or_model_execution=False,output_writes=0)
    print('TRUSTED_LOSSLESS_CONTEXT_V3 '+json.dumps(common,ensure_ascii=False,separators=(',',':')))
    for piece in pieces:
        frame={key:value for key,value in piece.items() if key!='text'}
        print('TRUSTED_LOSSLESS_VIEW_V3 '+json.dumps(frame,ensure_ascii=False,separators=(',',':')))
        print('SOURCE_DATA_VIEW_BEGIN')
        print(piece['text'],end='')
        print('\nSOURCE_DATA_VIEW_'+('EOF' if piece['end_of_view'] else 'MORE_PARTS_REMAIN'))
    print('TRUSTED_LOSSLESS_BATCH_END '+json.dumps(dict(source_id=context['source_id'],role=context['role'],
        first_part=pieces[0]['part'],last_part=pieces[-1]['part'],parts=pieces[-1]['parts'],
        next_part=pieces[-1]['next_part'],pair_loads=1,returned_parts=len(pieces),
        payload_copies_written=0,semantic_review_complete=False),separators=(',',':')))


def cli(root,role):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page',type=int)
    parser.add_argument('source_id')
    parser.add_argument('first_part',type=int)
    parser.add_argument('count',type=int,nargs='?',default=3)
    args=parser.parse_args()
    if args.page<1 or args.first_part<1 or not 1<=args.count<=3:
        parser.error('positive page/part and count1..3 required')
    guard.activate()
    data=guard.checked_contract()
    ident='expanded_train:'+args.source_id if args.source_id.isdigit() else args.source_id
    if ident in set(data['restricted_ids'])|set(data['trusted_metadata']):
        raise ValueError('restricted source identity; no payload read')
    cohort='remaining_field_title_page_'+format(args.page,'03d')+'_counter_v1'
    old=frozen_batch()
    entry=old.frozen_entry()
    metadata,scope,core=old.setup(root,entry)
    context=core.resolve_assignment(root,scope,role,cohort,ident,metadata.pinned)
    guard.require_payload_context(context,data)
    context,views,pieces=old.batch(core,root,scope,role,cohort,ident,args.first_part,args.count,metadata.pinned)
    context['cumulative_guard']=dict(path=str(guard.CONTRACT.relative_to(root)),sha256=guard.EXPECTED)
    emit(root,context,views,pieces)
    guard.assert_no_protected_opens()
