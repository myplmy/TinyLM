"""Use the same bounded exact frames in a pinned, explicitly assigned supplement."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import active_guard_v6_preflight_v1 as guard
from batched_lossless_review_entry_v2 import frozen_batch


def cli(root,role,cohort,scope_pin):
    parser=argparse.ArgumentParser()
    parser.add_argument('source_id')
    parser.add_argument('first_part',type=int)
    parser.add_argument('count',type=int,nargs='?',default=3)
    args=parser.parse_args()
    if args.first_part<1 or not 1<=args.count<=3:
        parser.error('positive part and count1..3 required')
    guard.activate()
    old=frozen_batch()
    entry=old.frozen_entry()
    metadata=entry.load_module(AUDIT/'field_scoped_packet_entry_v1.py',
        '53C408863DCF2474BD9825DE23EA15D765DCC0F6EDC356CD5767E5C59A18F8CE','supplement_metadata')
    scope=json.loads(metadata.pinned(root,scope_pin))
    if scope['contract']['sha256']!=guard.EXPECTED:
        raise ValueError('supplement needs current cumulative guard6')
    pin=scope['core']
    core=entry.load_module(root/pin['path'],pin['sha256'],'supplement_exact_core3')
    ident='expanded_train:'+args.source_id if args.source_id.isdigit() else args.source_id
    context=core.resolve_assignment(root,scope,role,cohort,ident,metadata.pinned)
    guard.require_payload_context(context)
    context,views,pieces=old.batch(core,root,scope,role,cohort,ident,args.first_part,args.count,metadata.pinned)
    old.emit(root,context,views,pieces)
    guard.assert_no_protected_opens()
