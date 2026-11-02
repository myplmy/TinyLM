"""Freeze exact reviewed9 pairs and independently preserve five source code units."""
from pathlib import Path
import ast
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
import exact_runtime_pair_guard_v1 as exact

selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW6.json'
audit_path=AUDIT/'EXACT_SELECTION_RUNTIME_GUARDS_V2.json'
rationale_path=AUDIT/'ROOT_INDEPENDENT49_MEDIATIONS_V1.md'
snapshot_path=AUDIT/'supplemental_candidates_snapshot_v60.json'
selection,audit,snapshot=map(inv.cache.read,[selection_path,audit_path,snapshot_path])
choices={row['id']:row for row in selection['rows']}
flags={row['id']:row for row in audit['records'] if row.get('runtime_code_and_unicode_pass') is False}
inv.require(set(flags)==exact.EXPECTED,'the nine exact runtime flag sources differ')
for group,expected in [('post_semantic_independent_v1',26),('runtime_guard_counter_v1',23)]:
    coverage=snapshot['coverage'][group]
    inv.require(coverage['expected']==coverage['saved']==expected and coverage['awaiting_review']==0,
                'independent full-source coverage differs')
    inv.require(all(row.get('body') and row['status']!='MECHANICAL_REJECTION_NOT_APPLIED'
                    for row in snapshot['records'] if row['cohort']==group),'a fresh review still failed')
proof_old_path=AUDIT/'GUARD_RESTORATION_CODE_PROOF_V1.json'
proof_old=inv.cache.read(proof_old_path)
code_proof=[]
records=[]
for ident in sorted(flags):
    source=choices[ident]
    chosen=source['selected']
    original_path=ROOT/flags[ident]['original_comparison_source']
    body_path=ROOT/chosen['body']
    inv.require(inv.file_sha(original_path)==source['original_text_sha256'] and
                inv.file_sha(body_path)==chosen['clean_text_sha256'],'exact source/body changed')
    raw,clean=original_path.read_text(encoding='utf-8'),body_path.read_text(encoding='utf-8')
    units=[]
    if ident=='expanded_train:1254536':
        inv.require(source['original_text_sha256']==proof_old['source']['sha256'],'original program source changed')
        source_lines=raw.splitlines()
        blocks=re.findall(r'```(?:text|python)[ \t]*\n([\s\S]*?)\n```',clean)
        inv.require(len(blocks)==len(proof_old['code_blocks'])==5,'all five complete source code blocks required')
        for old,block in zip(proof_old['code_blocks'],blocks):
            original=source_lines[old['source_line']-1]
            unit=re.sub(r'\s+','',original)
            inv.require(inv.sha(unit)==old['nonwhitespace_sha256'] and
                        re.sub(r'\s+','',block)==unit,'source code gained or lost nonwhitespace tokens')
            ast.parse(block)
            units.append(unit)
            code_proof.append(dict(source_line=old['source_line'],nonwhitespace_sha256=inv.sha(unit),
                                   nonwhitespace_equal=True,ast_parse=True))
    elif ident=='expanded_train:689736':
        matches=re.findall(r"lastSeasonDF\s*=\s*nhlDF[.]xs\(20182019,\s*level='season'\)",raw)
        inv.require(len(matches)==1,'actual xs source unit must be unique')
        units.append(re.sub(r'\s+','',matches[0]))
    record=dict(id=ident,root_approved=True,
        original=dict(path=str(original_path.relative_to(ROOT)),sha256=source['original_text_sha256']),
        body=dict(path=str(body_path.relative_to(ROOT)),sha256=chosen['clean_text_sha256']),
        review=chosen['review'], evidence=dict(path=str(rationale_path.relative_to(ROOT)),sha256=inv.file_sha(rationale_path)),
        required_nonwhitespace_code_units=units,cache_admitted=0)
    inv.require(exact.exact_pair_preserved(raw,clean,ident,{ident:record}),
                'reviewed exact pair lost a nonempty Unicode example or source code unit')
    records.append(record)
style=[]
for flag in audit['records']:
    if flag.get('semantic_style_pass') is not False:
        continue
    row=choices[flag['id']]
    style.append(dict(id=row['id'],original_text_sha256=row['original_text_sha256'],
        clean_text_sha256=row['selected']['clean_text_sha256'],review=row['selected']['review'],
        root_approved=True,scope='EXACT_EMPTY_LAYOUT_OR_UNBOUND_LEGEND_SOURCE_CONTEXT_NOT_GLOBAL_STYLE_WAIVER'))
inv.require(len(style)==14,'all actual style flag cases must be explicitly reviewed')
proof_path=AUDIT/'GUARD_RESTORATION_CODE_PROOF_V2.json'
inv.require(not proof_path.exists() and not exact.REGISTRY.exists(),'new exact guard artifacts required')
inv.write_json(proof_path,dict(status='FIVE_SOURCE_CODE_UNITS_AND_AST_PRESERVED_IN_LATEST_AUTHORED_BODY',
    code_blocks=code_proof,source=proof_old['source'],body=next(r['body'] for r in records if r['id']=='expanded_train:1254536'),
    model_or_example_code_executed=False,cache_admitted=0,training_authorized=False))
result=dict(status='ROOT_REVIEWED_EXACT_RUNTIME_SOURCE_BODY_PAIRS',rows=records,style_cases=style,
    global_code_guard_waiver=False,baseline_exception_allowed=False,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in
                [selection_path,audit_path,rationale_path,snapshot_path,proof_old_path,proof_path,Path(__file__)]},
    cache_admitted=0,goal_complete=False,training_authorized=False)
inv.write_json(exact.REGISTRY,result)
exact.load_registry()
print(json.dumps(dict(exact_code_pairs=len(records),exact_style_cases=len(style),source_code_blocks=len(code_proof),
                      ast_parse=True,program_execution=False)))
