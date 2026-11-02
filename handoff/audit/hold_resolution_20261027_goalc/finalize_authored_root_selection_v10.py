"""Close all exact source choices under actual guards and independent review pins."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

preview_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW6.json'
guards_path=AUDIT/'EXACT_SELECTION_RUNTIME_GUARDS_V3.json'
pairs_path=AUDIT/'ROOT_RUNTIME_PAIR_APPROVALS_V1.json'
rationale_path=AUDIT/'ROOT_INDEPENDENT49_MEDIATIONS_V1.md'
output=AUDIT/'ROOT_AUTHORED_SELECTIONS_V10.json'
inv.require(not output.exists(),'new immutable exact root selection required')
preview,guards,pairs=map(inv.cache.read,[preview_path,guards_path,pairs_path])
inv.require(guards['counts']['sources']==4381 and guards['counts']['runtime_guard_failure']==0 and
            guards['counts']['memo_flag']==0,'exact body runtime guard closure is incomplete')
for document in [preview,guards,pairs]:
    for name,expected in document['input_pins'].items():
        inv.require(inv.file_sha(ROOT/name)==expected,'exact reviewed input changed')
checked={row['id']:row for row in guards['records']}
style={row['id']:row for row in pairs['style_cases']}
rows=[]
for source in preview['rows']:
    ident=source['id']
    choice=dict(source['selected'])
    check=checked[ident]
    inv.require(check['original_text_sha256']==source['original_text_sha256'] and
                check.get('clean_text_sha256')==choice.get('clean_text_sha256'),'guard examined a different exact pair')
    if choice['decision']!='EXCLUDE':
        inv.require(check['runtime_code_and_unicode_pass'] and not check['editor_memo_present'],
                    'selected body failed a runtime guard')
        if check['semantic_style_pass'] is False:
            approved=style[ident]
            inv.require(approved['root_approved'] is True and approved['original_text_sha256']==source['original_text_sha256']
                        and approved['clean_text_sha256']==choice['clean_text_sha256'] and approved['review']==choice['review'],
                        'a style exception lacks the exact full-source review')
    choice['root_approved']=True
    rows.append(dict(source,selected=choice,root_approved=True,
        status='ROOT_EXACT_SOURCE_BODY_SELECTION_CLOSED_PENDING_NEW_CACHE',
        guard_closure=dict(path=str(guards_path.relative_to(ROOT)),sha256=inv.file_sha(guards_path)),
        cache_admitted=False,goal_complete=False,training_authorized=False))
inv.require(len(rows)==len({r['id'] for r in rows})==4381,'whole exact source conservation differs')
paths=[preview_path,guards_path,pairs_path,rationale_path,AUDIT/'ACTUAL_GUARDED_SOURCE_ROWS_V1.json',Path(__file__)]
result=dict(status='ROOT_AUTHOR_BODY_SELECTIONS_NOT_CACHE_ADMISSION',rows=rows,
    source_ids=len(rows),selected_sources=len(rows),unresolved_sources=0,unresolved=[],
    counts=dict(Counter(row['selected']['decision'] for row in rows)),root_guard_closure_required=False,
    exact_style_exceptions=len(style),restricted_parent_full_bodies_opened=False,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in paths},
    cache_admitted=0,goal_complete=False,training_authorized=False)
inv.require(len(json.dumps(result,ensure_ascii=False).encode())<20_000_000,'root selections need ordered shards')
inv.write_json(output,result)
print(json.dumps({key:result[key] for key in ['status','source_ids','counts','exact_style_exceptions']}))
