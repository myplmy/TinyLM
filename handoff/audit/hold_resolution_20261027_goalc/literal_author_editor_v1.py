"""Fixed-target text editing with literal data only, never source commands."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path[:0]=[str(AUDIT),str(ROOT)]
import active_guard_v6_preflight_v1 as guard


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def edit(raw,request):
    if set(request)!={'expected_sha256','edits'} or request['expected_sha256']!=digest(raw):
        raise ValueError('current final SHA differs; no write')
    if not isinstance(request['edits'],list) or not 1<=len(request['edits'])<=32:
        raise ValueError('one to32 literal edits required')
    text=raw.decode('utf-8')
    hunks=[]
    for item in request['edits']:
        if set(item)!={'old','new'} or not all(isinstance(item[k],str) for k in ['old','new']):
            raise ValueError('each edit must contain only literal old/new strings')
        old,new=item['old'],item['new']
        if not old or len(old)>8000 or len(new)>8000 or text.count(old)!=1:
            raise ValueError('old must match exactly once within bounded literal data; no write')
        start=text.index(old)
        text=text[:start]+new+text[start+len(old):]
        hunks.append(dict(start_character_before_this_edit=start,old=old,new=new))
    after=text.encode('utf-8')
    if not text.strip() or len(after)>=20_000_000 or chr(0) in text:
        raise ValueError('invalid final body; no write')
    if len(json.dumps(hunks,ensure_ascii=False).encode())>24000:
        raise ValueError('edit batch report too large; use a smaller batch; no write')
    return after,hunks


def core():
    path=AUDIT/'lossless_review_packet_v3.py'
    if guard.inv.file_sha(path)!='1B88CE9E7D39983CB6558276F6BA0E5A1952492AB47679BB49DDDBA78CAF6978':
        raise ValueError('fixed byte frame core changed')
    spec=importlib.util.spec_from_file_location('literal_editor_frame_core3',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cli(root,role,scope_pin):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_id')
    choice=parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--check',action='store_true')
    choice.add_argument('--find')
    choice.add_argument('--apply',action='store_true')
    choice.add_argument('--final',type=int)
    choice.add_argument('--diff',type=int)
    parser.add_argument('--count',type=int,default=3)
    args=parser.parse_args()
    guard.activate()
    path=root/scope_pin['path']
    assert not path.is_symlink() and guard.inv.file_sha(path)==scope_pin['sha256']
    scope=json.loads(path.read_bytes())
    ident='expanded_train:'+args.source_id if args.source_id.isdigit() else args.source_id
    if ident!=scope['id'] or role!=scope['role'] or not scope['unfinished_final_only']:
        raise ValueError('outside exact unfinished final assignment; no payload read')
    guard.require_payload_context(scope)
    target=root/scope['target']
    assert target.parent==root/scope['author_directory'] and not target.is_symlink()
    assert target!=root/scope['original']['path'] and target!=root/scope['candidate']['path']
    raw=target.read_bytes()
    assert len(raw)<20_000_000
    text=raw.decode('utf-8')
    header=dict(id=ident,role=role,path=scope['target'],current_sha256=digest(raw),bytes=len(raw),
        original_sha256=scope['original']['sha256'],root_or_cache_admission=False,
        semantic_review_complete=False,payload_copies_written=0)
    if args.check:
        print(json.dumps(dict(header,status='UNFINISHED_FINAL_CHECK_ONLY'),ensure_ascii=False))
    elif args.find is not None:
        if not 1<=len(args.find)<=200:
            raise ValueError('bounded literal locator query required')
        indexes=[]
        start=0
        while len(indexes)<8:
            start=text.find(args.find,start)
            if start<0:
                break
            indexes.append(start)
            start+=len(args.find)
        print(json.dumps(dict(header,status='LITERAL_LOCATOR_NOT_NEW_FULL_READ',matches=[
            dict(character=i,context_start=max(0,i-120),text=text[max(0,i-120):i+len(args.find)+450])
            for i in indexes],truncated_match_list=text.count(args.find)>8),ensure_ascii=False))
    elif args.apply:
        payload=sys.stdin.buffer.read(262145)
        if len(payload)>262144:
            raise ValueError('literal request too large; no write')
        after,hunks=edit(raw,json.loads(payload))
        if target.read_bytes()!=raw:
            raise ValueError('final changed during preparation; no write')
        if after!=raw:
            # The transient file belongs to this single atomic transaction.
            with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.literal-edit-',suffix='.tmp',delete=False) as stream:
                temporary=Path(stream.name)
                stream.write(after)
                stream.flush()
                os.fsync(stream.fileno())
            if target.read_bytes()!=raw:
                temporary.unlink()
                raise ValueError('concurrent final change; target preserved')
            os.replace(temporary,target)
        print(json.dumps(dict(header,status='LITERAL_BATCH_APPLIED_UNFINISHED_NOT_ADMITTED',
            final_sha256=digest(after),final_bytes=len(after),hunks=hunks,temporary_files_remaining=0),ensure_ascii=False))
    else:
        first=args.final if args.final is not None else args.diff
        if first<1 or not 1<=args.count<=3:
            raise ValueError('positive part and count1..3 required')
        frame_core=core()
        value=text
        if args.diff is not None:
            source=root/scope['original']['path']
            assert not source.is_symlink()
            original=source.read_bytes()
            assert digest(original)==scope['original']['sha256']
            views=frame_core.prepare_views(original,raw)
            old=original.decode('utf-8')
            records=[]
            for number,item in enumerate(views['changes'],1):
                lo,hi=item['source_range']
                records.append('CHANGE '+str(number)+' '+json.dumps(item['source_range'])+'\nOLD\n'+old[lo:hi]+'\nNEW\n'+item['after']+'\nEND_CHANGE\n')
            value=''.join(records) if records else 'NO_CHANGES_FROM_ORIGINAL\n'
        view={'full_candidate':value}
        piece=frame_core.view_part(view,'full_candidate',first)
        last=min(piece['parts'],first+args.count-1)
        print('TRUSTED_LITERAL_EDITOR_CONTEXT_V1 '+json.dumps(dict(header,mode='final' if args.final is not None else 'full_old_new_diff'),ensure_ascii=False))
        for part in range(first,last+1):
            row=frame_core.view_part(view,'full_candidate',part)
            print('TRUSTED_LITERAL_EDITOR_FRAME_V1 '+json.dumps({k:v for k,v in row.items() if k!='text'},ensure_ascii=False))
            print('SOURCE_DATA_VIEW_BEGIN')
            print(row['text'],end='')
            print('\nSOURCE_DATA_VIEW_'+('EOF' if row['end_of_view'] else 'MORE_PARTS_REMAIN'))
    guard.assert_no_protected_opens()
