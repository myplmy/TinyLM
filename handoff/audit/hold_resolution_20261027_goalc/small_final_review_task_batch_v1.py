"""Return complete final+all-change views for up to five small own edited TXTs."""
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

MAX_FINAL_BYTES=4000
MAX_PACKET_BYTES=8000
MAX_BODY_BYTES=12000
MAX_OUTPUT_BYTES=18000


def collect(root,role,cohort,items,core,scope,read_metadata,contract,read_payload=None):
    core.require(1<=len(items)<=5 and len({x[0] for x in items})==len(items),'one to five distinct own final TXTs required')
    planned=[]
    for ident,name,sha in items:
        context=core.resolve_assignment(root,scope,role,cohort,ident,read_metadata)
        review.transport.guard.require_payload_context(context,contract)
        path,pin=review.target(root,context,name,sha,core)
        review.transport.guard.require_payload_context(dict(context,candidate=pin),contract)
        planned.append((context,path,pin))
    packets=[];deferred=[];used=0;loaded=[]
    for context,path,pin in planned:
        ident=context['source_id']
        if path.stat().st_size>MAX_FINAL_BYTES:
            deferred.append(dict(source_id=ident,reason='LARGE_FINAL_USE_EXISTING_SINGLE_READER_FROM_PART1',payload_pair_loaded=False))
            continue
        actual,final_pin,original,final=review.load_final(root,role,cohort,ident,path.name,pin['sha256'],
            core,scope,read_metadata,contract,read_payload)
        core.require(actual==context and final_pin==pin,'assignment changed during final batch')
        loaded.append(ident)
        source,body=original.decode('utf-8'),final.decode('utf-8')
        changes=review.exact_changes(source,body,core)
        views=dict(final=body,changes=review.changes_view(source,changes))
        width=sum(len(v.encode('utf-8')) for v in views.values())
        if width>MAX_PACKET_BYTES or used+width>MAX_BODY_BYTES:
            deferred.append(dict(source_id=ident,reason='WHOLE_PACKET_BUDGET_USE_EXISTING_SINGLE_READER_FROM_PART1',payload_pair_loaded=True))
            continue
        packets.append(dict(source_id=ident,original=context['original'],final=pin,views=views,
            exact_changes=len(changes),exact_final_byte_reconstruction=True))
        used+=width
    return packets,dict(requested_ids=[x[0] for x in items],deferred=deferred,payload_pairs_loaded=loaded,
        body_bytes=used,source_payload_copies_written=0,first_read_credit=0)


def render(role,cohort,packets,result,guard_pin):
    remaining=list(packets);deferred=list(result['deferred'])
    while True:
        completed=[p['source_id'] for p in remaining]
        common=dict(protocol='SMALL_ASSIGNED_FINAL_AND_ALL_CHANGES_TASK_BATCH_V1',role=role,cohort=cohort,
            guard=guard_pin,requested_ids=result['requested_ids'],first_read_credit=0,
            body_copies_written=0,semantic_review_complete=False,root_or_cache_admission=False)
        output=['TRUSTED_SMALL_FINAL_BATCH_CONTEXT '+json.dumps(common,ensure_ascii=False,separators=(',',':'))+chr(10)]
        for packet in remaining:
            header={k:v for k,v in packet.items() if k!='views'}
            output.append('TRUSTED_SMALL_FINAL_SOURCE '+json.dumps(header,ensure_ascii=False,separators=(',',':'))+chr(10))
            for view,text in packet['views'].items():
                info=dict(source_id=packet['source_id'],view=view,part=1,parts=1,end_of_view=True,next_part=None,
                    bytes=len(text.encode('utf-8')))
                output.extend(['TRUSTED_SMALL_FINAL_VIEW '+json.dumps(info,separators=(',',':'))+chr(10),
                    'SOURCE_DATA_VIEW_BEGIN'+chr(10),text,chr(10)+'SOURCE_DATA_VIEW_EOF'+chr(10)])
        end=dict(completed_final_and_all_changes_ids=completed,deferred=deferred,
            not_returned_ids=[i for i in result['requested_ids'] if i not in completed],
            payload_pairs_loaded=result['payload_pairs_loaded'],
            prepared_but_not_returned_ids=[i for i in result['payload_pairs_loaded'] if i not in completed],
            body_bytes=sum(len(v.encode('utf-8')) for p in remaining for v in p['views'].values()),
            semantic_review_complete=False,first_read_credit=0)
        output.append('TRUSTED_SMALL_FINAL_BATCH_END '+json.dumps(end,separators=(',',':'))+chr(10))
        value=''.join(output)
        if len(value.encode('utf-8'))<=MAX_OUTPUT_BYTES:return value
        if not remaining:raise ValueError('metadata output exceeded cap; nothing printed')
        packet=remaining.pop()
        deferred.append(dict(source_id=packet['source_id'],reason='OUTPUT_CAP_USE_EXISTING_SINGLE_READER_FROM_PART1',payload_pair_loaded=True))


def cli(root,role):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page',type=int)
    parser.add_argument('id_name_sha',nargs='+')
    args=parser.parse_args()
    if args.page<1 or len(args.id_name_sha)%3 or not 3<=len(args.id_name_sha)<=15:
        parser.error('PAGE followed by one to five ID FINAL_BASENAME FINAL_SHA256 triples required')
    items=[('expanded_train:'+ident if ident.isdigit() else ident,name,sha)
        for ident,name,sha in zip(args.id_name_sha[::3],args.id_name_sha[1::3],args.id_name_sha[2::3])]
    review.transport.guard.activate();contract=review.transport.guard.checked_contract()
    if {i for i,_,_ in items}&(set(contract['restricted_ids'])|set(contract['trusted_metadata'])):
        raise ValueError('restricted requested source identity; no payload read')
    old=review.transport.frozen_batch();metadata,scope,core=old.setup(root,old.frozen_entry())
    cohort='remaining_field_title_page_'+format(args.page,'03d')+'_counter_v1'
    packets,result=collect(root,role,cohort,items,core,scope,review.transport.cached_reader(metadata.pinned),contract)
    value=render(role,cohort,packets,result,dict(path=str(review.transport.guard.CONTRACT.relative_to(root)),
        sha256=review.transport.guard.EXPECTED))
    review.transport.guard.assert_no_protected_opens()
    print(value,end='')
