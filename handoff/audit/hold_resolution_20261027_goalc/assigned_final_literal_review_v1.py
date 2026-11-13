"""Read an assigned final TXT and exact character changes without whole-line diffs."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import re
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
FROZEN_TRANSPORT=AUDIT/'multi_source_lossless_review_entry_v1.py'
assert not FROZEN_TRANSPORT.is_symlink() and hashlib.sha256(FROZEN_TRANSPORT.read_bytes()).hexdigest().upper()==\
    '4F30167E8DC5F00655CE32BA8AF4BFE96C15FBEFF5CBD38AFDF655DADE1E5433'
import multi_source_lossless_review_entry_v1 as transport

MAX_MATCH_CHARACTERS=2_000_000
MAX_TOKENS=200_000
SMALL_GAP=6000
CONTEXT=64


def exact_changes(source,final,core):
    """Unique token anchors bound matching; every range reconstructs final bytes."""
    changes=[]

    def add(a,b,c,d):
        if a==b and c==d:return
        changes.append(dict(op='insert' if a==b else 'delete' if c==d else 'replace',
            source_range=[a,b],candidate_range=[c,d],after=final[c:d]))

    def gap(a,b,c,d):
        while a<b and c<d and source[a]==final[c]:a+=1;c+=1
        while a<b and c<d and source[b-1]==final[d-1]:b-=1;d-=1
        if a==b or c==d:
            add(a,b,c,d);return
        if b-a+d-c<=SMALL_GAP:
            for tag,i,j,k,l in difflib.SequenceMatcher(None,source[a:b],final[c:d],autojunk=True).get_opcodes():
                if tag!='equal':add(a+i,a+j,c+k,c+l)
        else:add(a,b,c,d)

    if source==final:return []
    if len(source)+len(final)<=MAX_MATCH_CHARACTERS:
        old=re.findall(r'\w+|\s+|[^\w\s]',source)
        new=re.findall(r'\w+|\s+|[^\w\s]',final)
        if max(len(old),len(new))<=MAX_TOKENS:
            old_offsets,new_offsets=core.base._offsets(old),core.base._offsets(new)
            a=c=0
            for i,j in core.ordered_anchors(old,new):
                b,d=old_offsets[i],new_offsets[j]
                gap(a,b,c,d)
                core.require(old[i]==new[j],'word anchor changed')
                a,c=old_offsets[i+1],new_offsets[j+1]
            gap(a,len(source),c,len(final))
        else:gap(0,len(source),0,len(final))
    else:gap(0,len(source),0,len(final))
    core.require(core.base.reconstruct(source,changes).encode('utf-8')==final.encode('utf-8'),
        'all final bytes were not reconstructed')
    return changes


def target(root,context,basename,sha,core):
    ident=context['source_id'];ordinal=ident.rsplit(':',1)[1]
    core.require(re.fullmatch(r'expanded_train_'+ordinal+r'_[A-Za-z0-9_-]+\.txt',basename) is not None,
        'final filename must belong to the exact assigned source')
    core.require(re.fullmatch(r'[0-9A-F]{64}',sha) is not None,'final SHA must be exact uppercase SHA256')
    name=core.base.DATA_ROOT+'/agents/'+context['role']+'/'+context['cohort']+'/'+basename
    path=core.base.data_path(root,name)
    return path,dict(path=name,sha256=sha)


def load_final(root,role,cohort,ident,basename,sha,core,scope,read_metadata,contract,read_payload=None):
    context=core.resolve_assignment(root,scope,role,cohort,ident,read_metadata)
    transport.guard.require_payload_context(context,contract)
    _path,final_pin=target(root,context,basename,sha,core)
    transport.guard.require_payload_context(dict(context,candidate=final_pin),contract)
    read_payload=read_payload or core.base.bounded_payload
    values=[]
    for pin in [context['original'],final_pin]:
        raw=read_payload(root,pin)
        core.require(len(raw)<core.base.LIMIT_BYTES and core.base.digest(raw)==pin['sha256'],
            'source or final bytes differ from the exact SHA or size bound')
        values.append(raw)
    return context,final_pin,*values


def changes_view(source,changes):
    parts=['ALL_EXACT_CHARACTER_CHANGES '+str(len(changes))+chr(10)]
    for number,item in enumerate(changes,1):
        a,b=item['source_range'];c,d=item['candidate_range']
        metadata=dict(number=number,operation=item['op'],source_range=[a,b],final_range=[c,d],
            range_unit='UNICODE_CODEPOINTS',source_before_context=source[max(0,a-CONTEXT):a],
            source_after_context=source[b:b+CONTEXT])
        parts.extend(['EXACT_CHANGE '+json.dumps(metadata,ensure_ascii=False,separators=(',',':'))+chr(10),
            'SOURCE_CHANGED_TEXT_BEGIN'+chr(10),source[a:b],chr(10)+'SOURCE_CHANGED_TEXT_END'+chr(10),
            'FINAL_CHANGED_TEXT_BEGIN'+chr(10),item['after'],chr(10)+'FINAL_CHANGED_TEXT_END'+chr(10)])
    parts.append('ALL_EXACT_CHARACTER_CHANGES_END'+chr(10))
    return ''.join(parts)


def cli(root,role):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page',type=int)
    parser.add_argument('source_id')
    parser.add_argument('final_basename')
    parser.add_argument('final_sha256')
    parser.add_argument('view',choices=['final','changes'])
    parser.add_argument('first_part',type=int,nargs='?',default=1)
    parser.add_argument('count',type=int,nargs='?',default=3)
    args=parser.parse_args()
    if args.page<1 or args.first_part<1 or not 1<=args.count<=3:parser.error('positive page/part and count1..3 required')
    ident='expanded_train:'+args.source_id if args.source_id.isdigit() else args.source_id
    transport.guard.activate();contract=transport.guard.checked_contract()
    if ident in set(contract['restricted_ids'])|set(contract['trusted_metadata']):
        raise ValueError('restricted source identity; no payload read')
    old=transport.frozen_batch();metadata,scope,core=old.setup(root,old.frozen_entry())
    cohort='remaining_field_title_page_'+format(args.page,'03d')+'_counter_v1'
    context,pin,raw,final_raw=load_final(root,role,cohort,ident,args.final_basename,args.final_sha256,
        core,scope,transport.cached_reader(metadata.pinned),contract)
    source,final=raw.decode('utf-8'),final_raw.decode('utf-8')
    changes=exact_changes(source,final,core)
    view=final if args.view=='final' else changes_view(source,changes)
    frames={'candidate':view}
    first=core.view_part(frames,'candidate',args.first_part)
    pieces=[first]+[core.view_part(frames,'candidate',n) for n in
        range(args.first_part+1,min(args.first_part+args.count,first['parts']+1))]
    header=dict(protocol='ASSIGNED_FINAL_EXACT_CHARACTER_REVIEW_V1',source_id=ident,role=role,cohort=cohort,
        original=context['original'],final=pin,view=args.view,exact_changes=len(changes),
        exact_final_byte_reconstruction=True,original_candidate_body_opened=False,
        guard=dict(path=str(transport.guard.CONTRACT.relative_to(root)),sha256=transport.guard.EXPECTED),
        body_copies_written=0,first_read_credit=0,semantic_review_complete=False,root_or_cache_admission=False)
    output=['TRUSTED_FINAL_CONTEXT '+json.dumps(header,ensure_ascii=False,separators=(',',':'))+chr(10)]
    for piece in pieces:
        output.extend(['TRUSTED_FINAL_FRAME '+json.dumps({k:v for k,v in piece.items() if k!='text'},
            separators=(',',':'))+chr(10),'SOURCE_DATA_VIEW_BEGIN'+chr(10),piece['text'],
            chr(10)+'SOURCE_DATA_VIEW_'+('EOF' if piece['end_of_view'] else 'MORE_PARTS_REMAIN')+chr(10)])
    output.append('TRUSTED_FINAL_BATCH_END '+json.dumps(dict(view=args.view,source_id=ident,
        final_sha256=args.final_sha256,last_part=pieces[-1]['part'],parts=pieces[-1]['parts'],
        next_part=pieces[-1]['next_part'],end_of_view=pieces[-1]['end_of_view']),separators=(',',':'))+chr(10))
    value=''.join(output)
    core.require(len(value.encode('utf-8'))<=18000,'final review output exceeded its cap; nothing printed')
    transport.guard.assert_no_protected_opens()
    print(value,end='')
