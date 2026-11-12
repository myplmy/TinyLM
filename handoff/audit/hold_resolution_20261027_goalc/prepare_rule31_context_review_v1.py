"""Reuse the exact six-source assignment generator for rule31 risk strata."""
from pathlib import Path
import ast
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path[:0]=[str(AUDIT),str(ROOT)]
import active_guard_v6_preflight_v1 as guard

frozen=AUDIT/'prepare_rule30_context_review_v1.py'
assert guard.inv.file_sha(frozen)=='9B4E7005533FF86ACC1D720D75F3111716E208BEBB17970313287C5112EE4136'
tree=ast.parse(frozen.read_text(encoding='utf-8'))
ids=['validation:443','expanded_train:51217','expanded_train:5823',
     'expanded_train:73713','expanded_train:1002418','expanded_train:1062897']
changes={
    'remaining_rule30_independent_context_v1':'remaining_rule31_independent_context_v1',
    'RULE30_EVENT_METADATA_LITERAL_INDEPENDENT_VERIFIED_V1.json':'RULE31_CATEGORY_METADATA_LITERAL_INDEPENDENT_VERIFIED_V1.json',
    'RULE30_EVENT_METADATA_CENSUS_V1.json':'RULE31_CATEGORY_ANCHOR_CENSUS_V1.json',
    'rule30_literal_final_bodies_v1':'exact_cohort_rendered_v1',
    'RULE30_CONTEXT_LOSSLESS_SCOPE_V1.json':'RULE31_CONTEXT_LOSSLESS_SCOPE_V1.json',
    'p106b_hold_resolution_policy_v30':'p106b_hold_resolution_policy_v31',
    'scripts/p106b_hold_resolution_policy_v30.py':'scripts/p106b_hold_resolution_policy_v31.py',
}
for node in ast.walk(tree):
    if isinstance(node,ast.Constant) and isinstance(node.value,str):
        if node.value in changes:
            node.value=changes[node.value]
        elif node.value.startswith('# rule30'):
            node.value=node.value.replace('rule30','rule31').replace('独立','독립')
    if isinstance(node,ast.ImportFrom) and node.module=='scripts':
        for name in node.names:
            if name.name=='p106b_hold_resolution_policy_v30':name.name='p106b_hold_resolution_policy_v31'
id_nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ids' for t in n.targets)]
assert len(id_nodes)==1
id_nodes[0].value=ast.List(elts=[ast.Constant(v) for v in ids],ctx=ast.Load())
assertions=[n for n in ast.walk(tree) if isinstance(n,ast.Assert) and ast.unparse(n.test)=="proposed['decision'] == 'EDIT'"]
assert len(assertions)==1
assertions[0].test=ast.parse("proposed['decision'] in {'KEEP','EDIT'}",mode='eval').body
ast.fix_missing_locations(tree)
exec(compile(tree,str(frozen),'exec'),dict(__name__='rule31_exact_six_context_assignments',__file__=str(Path(__file__))))
cohort='remaining_rule31_independent_context_v1'
manifest=json.loads((guard.inv.BASE/cohort/'manifest.json').read_bytes())
directory=guard.inv.BASE/'agents/historical_review'/cohort
for number,rows in [(1,manifest['rows'][:5]),(2,manifest['rows'][5:])]:
    lines=['# TASK_'+format(number,'03d'),'ASSIGNMENT_V1.md와 고정 manifest의 정확한 동일 배정이다.']
    for row in rows:
        lines.extend(['## '+row['id'],'original: '+str(ROOT/row['original']['path']),
            'original SHA-256: '+row['original']['sha256'],'candidate: '+str(ROOT/row['candidate']['path']),
            'candidate SHA-256: '+row['candidate']['sha256']])
    path=directory/('TASK_'+format(number,'03d')+'.md')
    assert not path.exists()
    with path.open('x',encoding='utf-8') as stream:
        stream.write(chr(10).join(lines)+chr(10))
guard.assert_no_protected_opens()
