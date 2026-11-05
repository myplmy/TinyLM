"""Fixed-role V4 reader: full original plus independently reconstructible candidate."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json

AUDIT = Path(__file__).resolve().parent
CONTRACT = ('handoff/audit/hold_resolution_20261027_goalc/GUARDED_SOURCE_METADATA_CONTRACT_V4.json',
            '59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D')


def load_module(path, expected, name):
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest().upper()!=expected:
        raise ValueError('fixed reader code bytes changed')
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def cli(root, role, config_pin):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort',required=True);parser.add_argument('--source-id',required=True)
    parser.add_argument('--view',choices=['pair','original','candidate','full_candidate'],required=True)
    parser.add_argument('--part',type=int,default=1);parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    metadata=load_module(AUDIT/'field_scoped_packet_entry_v1.py',
        '53C408863DCF2474BD9825DE23EA15D765DCC0F6EDC356CD5767E5C59A18F8CE','unchanged_v2_metadata_reader')
    scope=json.loads(metadata.pinned(root,config_pin))
    if (scope['contract']['path'],scope['contract']['sha256'])!=CONTRACT:
        raise ValueError('current V4 guard is mandatory before payload access')
    if scope.get('transport_protocol')!='FULL_ORIGINAL_AND_LOSSLESS_CANDIDATE_V2':
        raise ValueError('unexpected transport contract')
    pin=scope['core']
    if pin['path']!='handoff/audit/hold_resolution_20261027_goalc/lossless_review_packet_v2.py':
        raise ValueError('unexpected lossless core path')
    metadata.pinned(root,pin)
    core=load_module(root/pin['path'],pin['sha256'],'pinned_lossless_review_v2')
    if args.check_only:
        context=core.resolve_assignment(root,scope,role,args.cohort,args.source_id,metadata.pinned)
        print(json.dumps(dict(status='LOSSLESS_V2_METADATA_ONLY_PREFLIGHT_PASS',**context,
            payload_opens=0,output_writes=0),ensure_ascii=False));return
    context,original,candidate=core.load_pair(root,scope,role,args.cohort,args.source_id,metadata.pinned)
    views=core.prepare_views(original,candidate);piece=core.view_part(views,args.view,args.part)
    info={key:value for key,value in views.items() if key not in
        {'original','candidate','full_candidate','pair','changes'}}
    info.update(context);info.update({key:value for key,value in piece.items() if key!='text'})
    info.update(accept_output_absolute=str(root/context['candidate']['path']),
        required_views=['pair'] if args.view=='pair' else ['original','candidate_or_full_candidate'],
        changes=len(views['changes']),root_or_cache_admission=False,semantic_review_complete=False,
        code_or_model_execution=False,output_writes=0)
    print('TRUSTED_LOSSLESS_VIEW_V2 '+json.dumps(info,ensure_ascii=False,separators=(',',':')))
    print('SOURCE_DATA_VIEW_BEGIN');print(piece['text'],end='')
    print('\nSOURCE_DATA_VIEW_'+('EOF' if piece['end_of_view'] else 'MORE_PARTS_REMAIN'))
