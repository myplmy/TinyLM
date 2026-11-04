"""Read-only owned WIP hashing; writes only a fresh static-scope JSON.

Kept as a named helper so the WIP mutation hook can distinguish the audit
output from an attempted direct ledger rewrite. The official wip.py remains
the only ledger writer.
"""
import json
from pathlib import Path
from scripts import validation_scope as scope

BASE = Path('handoff/audit/nov04_weight_space')
old = json.loads((BASE / 'OWNED_INPUTS_v1.json').read_text(encoding='utf-8'))
extra = ['handoff/WIP_20261022_작업원장.md', 'scripts/p108_signed_control.py',
         'scripts/test_p108_signed_control.py', 'scripts/diag_p108_fixed_support.py',
         'run_P108_Stage0eW_fixed_support_contract.sh', 'run_P108_Stage3cW_fixed_support_confirm.sh',
         'scripts/test_p106b_weight_route.py']
inputs = {row['path']: row['role'] for row in old['inputs']}
for name in extra:
    inputs[name] = 'owned'
old['inputs'] = [dict(path=name, role=role, sha256=scope.sha256(Path(name)))
                 for name, role in sorted(inputs.items())]
path = BASE / 'OWNED_INPUTS_v3.json'
with path.open('x', encoding='utf-8') as stream:
    json.dump(old, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(inputs=len(old['inputs']), sha256=scope.sha256(path))))
