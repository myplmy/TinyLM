"""Compare exact real frames and reconstruct every old metadata key in RAM."""
from pathlib import Path
import ast
import contextlib
import hashlib
import io
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path[:0]=[str(AUDIT),str(ROOT)]
import active_guard_v6_preflight_v1 as guard
import batched_lossless_review_entry_v3 as compact

old_parser_path=AUDIT/'verify_batched_reader_actual_v1.py'
nodes=[n for n in ast.parse(old_parser_path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='parse']
assert len(nodes)==1
namespace=dict(json=json)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(old_parser_path),'exec'),namespace)
parse_old=namespace['parse']


def parse_compact(raw):
    line,raw=raw.split(b'\n',1)
    marker=b'TRUSTED_LOSSLESS_CONTEXT_V3 '
    assert line.startswith(marker)
    common=json.loads(line[len(marker):])
    frames=[]
    while raw.startswith(b'TRUSTED_LOSSLESS_VIEW_V3 '):
        line,raw=raw.split(b'\n',1)
        piece=json.loads(line.split(b' ',1)[1])
        info=dict(common,**piece)
        begin=b'SOURCE_DATA_VIEW_BEGIN\n'
        assert raw.startswith(begin)
        raw=raw[len(begin):]
        count=piece['range'][1]-piece['range'][0]
        text,raw=raw[:count],raw[count:]
        text.decode('utf-8')
        end=b'\nSOURCE_DATA_VIEW_'+(b'EOF' if piece['end_of_view'] else b'MORE_PARTS_REMAIN')+b'\n'
        assert raw.startswith(end)
        raw=raw[len(end):]
        frames.append((info,text))
    return frames,raw


guard.activate()
old=compact.frozen_batch()
entry=old.frozen_entry()
metadata,scope,core=old.setup(ROOT,entry)
rows=[]
for role,page,ident in [('context_controls',12,'259740'),('context_latin',12,'263562'),
    ('context_hangul',16,'445464'),('historical_review',15,'392325'),('legacy_review',14,'335240')]:
    key='expanded_train:'+ident
    cohort='remaining_field_title_page_'+format(page,'03d')+'_counter_v1'
    context=core.resolve_assignment(ROOT,scope,role,cohort,key,metadata.pinned)
    guard.require_payload_context(context)
    context,views,pieces=old.batch(core,ROOT,scope,role,cohort,key,1,3,metadata.pinned)
    context['cumulative_guard']=dict(path=str(guard.CONTRACT.relative_to(ROOT)),sha256=guard.EXPECTED)
    a,b=io.StringIO(),io.StringIO()
    with contextlib.redirect_stdout(a):old.emit(ROOT,context,views,pieces)
    with contextlib.redirect_stdout(b):compact.emit(ROOT,context,views,pieces)
    old_raw,new_raw=a.getvalue().encode(),b.getvalue().encode()
    before,old_tail=parse_old(old_raw)
    after,new_tail=parse_compact(new_raw)
    assert before==after and old_tail==new_tail and len(after)==3
    body_bytes=sum(len(t) for _,t in after)
    rows.append(dict(role=role,id=key,frames=3,old_stdout_bytes=len(old_raw),new_stdout_bytes=len(new_raw),
        body_bytes=body_bytes,exact_body_and_reconstructed_metadata=True))
guard.assert_no_protected_opens()
old_total=sum(r['old_stdout_bytes'] for r in rows)
new_total=sum(r['new_stdout_bytes'] for r in rows)
body_total=sum(r['body_bytes'] for r in rows)
result=dict(status='ACTUAL_FIVE_ROLE_COMPACT_HEADERS_PRESERVE_ALL_15_FRAMES_AND_OLD_METADATA',
    rows=rows,frames=15,old_stdout_bytes=old_total,new_stdout_bytes=new_total,body_bytes=body_total,
    stdout_reduction_percent=100*(old_total-new_total)/old_total,
    repeated_metadata_reduction_percent=100*(old_total-new_total)/(old_total-body_total),
    protected_payload_open_attempts=0,payload_copies_written=0,new_human_first_read_credit=0,
    not_a_semantic_or_whole_job_speed_measurement=True,
    input_pins={str(p.relative_to(ROOT)):guard.inv.file_sha(p) for p in
        [Path(__file__),AUDIT/'batched_lossless_review_entry_v3.py',old_parser_path,guard.CONTRACT]},
    goal_complete=False,training_authorized=False)
out=AUDIT/'COMPACT_BATCH_HEADERS_FIVE_ROLE_ACTUAL_VERIFIED_V1.json'
assert not out.exists()
guard.inv.write_json(out,result)
print(json.dumps({k:v for k,v in result.items() if k not in {'rows','input_pins'}}))
