"""Build one explicit owned/shared source manifest, never scan scripts globally."""
from pathlib import Path
import ast
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from validation_scope import SCHEMA, MODE, _relative


def main():
    old = json.loads((ROOT / 'handoff/audit/nov01_afternoon/SCOPE_v2.json').read_text())
    owned = {name for name in old['paths'] if name.endswith('.py')
             and name.startswith(('scripts/', 'tinylm/')) and (ROOT / name).is_file()}
    changed = {
        'scripts/validation_scope.py', 'scripts/test_validation_scope.py',
        'scripts/check_static_all.py', 'scripts/check_flag_whitelist.py',
        'scripts/smoke_execution_contract.py', 'scripts/codex_smoke.py',
    }
    names = set(owned) | changed | {
        'scripts/check_attrs.py', 'scripts/check_call_kwargs.py',
        'scripts/check_imports.py', 'scripts/check_flag_used.py', 'scripts/check_links.py',
        'scripts/flag_whitelist.tsv', 'handoff/WIP_20261022_작업원장.md',
        'docs/research/20261101_A_검사입력범위_구현계약.md',
        'docs/research/20261101_자율주도_연구_최종보고.md',
        'docs/research/20261101_오후_독립연구_결과보고.md',
        'handoff/202611011123_HANDOFF.md',
        'ai_dev_tool/Codex/06_Codex용_프로젝트지침과_메모리.md',
        'ai_dev_tool/Codex/08_AI-미보고-내역-자백원장.md',
        'proposal/20261101_정제세션-격리와-공용검사-범위-명시-제안서-approved-on-going.md',
    }
    # Only the shared model source directory is enumerated, before running any
    # checker. scripts/, audit/, protected data and foreign roots are not scanned.
    names.update(path.relative_to(ROOT).as_posix()
                 for path in (ROOT / 'tinylm').rglob('*.py') if path.is_file())
    forbidden_scripts = ('scripts/p106b_hold_resolution',)
    pending = [name for name in names if name.endswith('.py')]
    done = set()
    while pending:
        name = pending.pop()
        if name in done:
            continue
        done.add(name)
        _relative(name)
        if name.startswith(forbidden_scripts):
            raise ValueError('foreign source dependency requires separate handling')
        tree = ast.parse((ROOT / name).read_text())
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and not node.level and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
        for module in modules:
            parts = module.split('.')
            candidates = []
            if parts[0] in ('scripts', 'tinylm'):
                base = '/'.join(parts)
                candidates = [base + '.py', base + '/__init__.py']
            elif len(parts) == 1:
                candidates = ['scripts/' + parts[0] + '.py']
            for candidate in candidates:
                if candidate.startswith(forbidden_scripts):
                    raise ValueError('foreign source dependency is not automatically admitted')
                if (ROOT / candidate).is_file() and candidate not in names:
                    _relative(candidate)
                    names.add(candidate)
                    pending.append(candidate)
    checks = ['check_attrs', 'check_call_kwargs', 'check_imports',
              'check_flag_used', 'check_flag_whitelist', 'check_links']
    inputs = [dict(path=name, role='owned' if name in owned | changed else 'shared',
                   sha256=hashlib.sha256((ROOT / name).read_bytes()).hexdigest().upper())
              for name in sorted(names)]
    version = sys.argv[1] if len(sys.argv) == 2 else 'v1'
    if re.fullmatch('v[1-9][0-9]*', version) is None:
        raise ValueError('one explicit receipt version required')
    output = ROOT / ('handoff/audit/nov01_scope_a/OWNED_INPUTS_' + version + '.json')
    payload = dict(schema=SCHEMA, mode=MODE, repository=str(ROOT),
                   exclusions=['datasets/TinyDataset', '.claude',
                       'handoff/audit/hold_resolution_20261027_goalc',
                       'handoff/audit/hold_recovery_20261026_goalc',
                       'handoff/audit/source_cleanup_20261026_goalc',
                       'scripts/p106b_hold_resolution*'],
                   inputs=inputs, commands=[dict(name=name, argv=['scripts/'+name+'.py'])
                                            for name in checks], child_commands=[])
    with output.open('x', encoding='utf-8') as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
    print(json.dumps(dict(manifest=output.relative_to(ROOT).as_posix(), inputs=len(inputs),
                         checks=len(checks), sha256=hashlib.sha256(output.read_bytes()).hexdigest().upper())))


if __name__ == '__main__':
    main()
