"""Freeze completed-cohort choices for a partial technical cache, not final quality."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from guarded_reviewed_cache_v3 import hold_cases

names=['ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json','EXACT_SELECTION_RUNTIME_GUARDS_V10.json',
    'ROOT11_NUMERIC_CONTEXT_DIAGNOSTICS_V2.json','ROOT11_NUMERIC_CONTEXT_CLEARANCES_V1.json',
    'ROOT11_QUANTITY_AND_QUALIFIED_DATE_CONTEXTS_V1.json','ROOT_RUNTIME_PAIR_APPROVALS_V1.json',
    'ROOT11_COMPLETED_COHORT_CHECK_PROCESS_EXITS_V1.json']
preview,guards,numeric,cleared,quantities,exceptions,exits=[inv.cache.read(AUDIT/n) for n in names]
assert len(exits['rows'])==5 and all(r['process_exit_code']==0 for r in exits['rows'])
assert guards['counts']['sources']==7857 and guards['counts']['runtime_guard_failure']==0
assert guards['counts']['memo_flag']==0 and guards['counts'].get('invalid_utf8_bodies',0)==0
assert cleared['counts']['unresolved_numeric_flags']==0 and quantities['counts']['unresolved_context_flags']==0
for document in [preview,guards,numeric,cleared,quantities]:
    for name,sha in document.get('input_pins',{}).items():assert inv.file_sha(ROOT/name)==sha,name
checks={r['id']:r for r in guards['records']}
style={r['id']:r for r in exceptions['style_cases']}
numeric_pending={(r['id'],r['original']['sha256'],r['body']['sha256']):r for r in numeric['rows'] if r['unresolved_flags']}
assert set(numeric_pending)=={(r['id'],r['original']['sha256'],r['body']['sha256']) for r in cleared['rows']}
for r in cleared['rows']:
    pair=(r['id'],r['original']['sha256'],r['body']['sha256'])
    assert numeric_pending[pair]['unresolved_flags']==r['approved_exact_flags']
for r in quantities['rows']:
    assert r['root_context_approved'] is True
    for field in ['original','body','review']:
        pin=r[field];assert inv.file_sha(ROOT/pin['path'])==pin['sha256']
cases=hold_cases();rows=[]
closure_path=AUDIT/'ROOT11_COMPLETED_COHORT_BODY_CLOSURE_V1.json'
closure=dict(status='PARTIAL_CACHE_BODY_CHOICES_CLOSED_WITH_EXPLICIT_SEMANTIC_LIMITS',
    runtime_sources=7857,checked_bodies=7771,runtime_failures=0,memo_flags=0,
    reviewed_nonadmissions=38,exact_style_exceptions=14,
    numeric_counts=numeric['counts'],root_individual_numeric_flags=18,
    quantity_source_contexts=15,qualified_date_false_positive=1,
    ordered_character_deletion_flags=guards['counts']['ordered_flag'],
    independent_full_repeat_reviews=732,birth_full_author_reviews=2743,
    birth_independent_whole_second_reading='NOT_COMPLETED',
    whole_corpus_semantic_completion=False,whole_corpus_cleanup_complete=False,
    limits='A strict character-subsequence flag is not automatically an error or waived semantic proof. These are selected partial technical-cache choices; further independent review and all deferred types remain active.',
    input_pins={str((AUDIT/n).relative_to(ROOT)):inv.file_sha(AUDIT/n) for n in names},
    goal_complete=False,training_authorized=False)
assert not closure_path.exists()
inv.write_json(closure_path,closure)
closure_pin=dict(path=str(closure_path.relative_to(ROOT)),sha256=inv.file_sha(closure_path))
style_count=0
for source in preview['rows']:
    row=dict(source);choice=dict(source['selected']);check=checks[source['id']]
    assert check['original_text_sha256']==source['original_text_sha256']
    assert check.get('clean_text_sha256')==choice.get('clean_text_sha256')
    if choice['decision']=='HOLD':
        case=cases[source['original_text_sha256']]
        assert case['id']==source['id'] and choice['hold_review_evidence']==case['authority_pin']
        assert choice['content_reviewed'] is True and not choice.get('body') and not choice.get('clean_text_sha256')
    elif choice['decision']!='EXCLUDE':
        assert check['runtime_code_and_unicode_pass'] and not check['editor_memo_present']
        if check['semantic_style_pass'] is False:
            proof=style[source['id']]
            assert proof['root_approved'] is True and proof['original_text_sha256']==source['original_text_sha256']
            assert proof['clean_text_sha256']==choice['clean_text_sha256'] and proof['review']==choice['review']
            style_count+=1
    choice['root_approved']=True
    row.pop('prior_guard_closure',None)
    row.update(selected=choice,root_approved=True,
        status='ROOT_EXACT_PARTIAL_CACHE_CHOICE_CLOSED_NOT_WHOLE_SEMANTIC_COMPLETION',
        guard_closure_id='ROOT11_COMPLETED_COHORT_BODY_CLOSURE_V1',cache_admitted=False)
    rows.append(row)
assert len(rows)==len({r['id'] for r in rows})==len({r['original_text_sha256'] for r in rows})==7857
assert style_count==14
assert {r['id'] for r in rows if r['selected']['decision']=='HOLD'}=={r['id'] for r in cases.values()}
paths=[AUDIT/n for n in names]+[closure_path,Path(__file__),
    AUDIT/'ROOT11_COMPLETED_COHORT_ADMISSION_SCOPE_V1.md',AUDIT/'ROOT11_QUANTITY_AND_QUALIFIED_DATE_REVIEW_V1.md']
result=dict(status='ROOT_AUTHOR_BODY_SELECTIONS_NOT_CACHE_ADMISSION',rows=rows,
    source_ids=len(rows),selected_sources=len(rows),unresolved_sources=0,unresolved=[],
    unresolved_sources_meaning='ZERO_ONLY_WITHIN_SELECTED_ID_SET_NOT_WHOLE_CORPUS',
    selection_scope=preview['selection_scope'],deferred_literal_sources=1792,
    deferred_literal_ids=[r['id'] for r in preview['unresolved']],
    official_cache_v2_unprocessed_unique_before_this_selection=73668,
    counts=dict(Counter(r['selected']['decision'] for r in rows)),root_guard_closure_required=False,
    exact_style_exceptions=style_count,closure=closure_pin,
    independent_semantic_review_limits=closure['limits'],
    restricted_parent_full_bodies_opened=False,
    input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in paths},
    cache_admitted=0,whole_corpus_semantic_completion=False,goal_complete=False,training_authorized=False)
out=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json'
payload=(json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode()
assert len(payload)<20_000_000
with out.open('xb') as f:f.write(payload)
print(json.dumps(dict(sources=len(rows),counts=result['counts'],deferred_literal=1792,bytes=len(payload),cache_admitted=0)))
