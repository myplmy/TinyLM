"""Add the exact missing handoff predecessor; no checker/criteria changes."""
import json
from pathlib import Path
from scripts.validation_scope import sha256

BASE = Path('handoff/audit/nov04_weight_space')


def main():
    old = json.loads((BASE/'SMOKE_INPUTS_v1.json').read_text(encoding='utf-8'))
    paths = {r['path']:r['role'] for r in old['inputs']}
    paths['handoff/202610271445_HANDOFF.md'] = 'shared'
    paths['handoff/audit/nov04_weight_space/build_smoke_scope_v2.py'] = 'owned'
    old['inputs'] = [dict(path=name, role=role, sha256=sha256(Path(name)))
                     for name,role in sorted(paths.items())]
    out = BASE/'SMOKE_INPUTS_v2.json'
    with out.open('x',encoding='utf-8') as stream:
        json.dump(old,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
    print(json.dumps(dict(path=str(out),sha256=sha256(out),inputs=len(paths),
                          session='nov04_p108_p107_v2',criteria_changed=False)))


if __name__ == '__main__':
    main()
