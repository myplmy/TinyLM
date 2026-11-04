"""Bind unchanged canonical smoke plus four explicit source collectors.

This pins shared product code only, never other-session data/cleaning code.
The canonical dynamic actions and model arguments are not changed.
"""
import json
from pathlib import Path

from scripts.codex_smoke import build_plan
from scripts.smoke_execution_contract import execution_source_pins, SCOPED_COLLECTORS
from scripts.validation_scope import _python_target, sha256

BASE = Path('handoff/audit/nov04_weight_space')
SESSION = 'nov04_p108_p107_v1'


def main():
    output = BASE/'SMOKE_INPUTS_v1.json'
    if output.exists():
        raise FileExistsError(output)
    root = Path.cwd()
    old = json.loads((BASE/'OWNED_INPUTS_v6.json').read_text(encoding='utf-8'))
    paths = {row['path']:row['role'] for row in old['inputs'] if Path(row['path']).is_file()}
    paths.update({name:'shared' for name in execution_source_pins(root)})
    for name in ('tinylm/train/document_input.py', 'scripts/test_p107_document_input.py',
                 'test_plan/P107_문서가시성과-shift를-분리한-causal-MNTP-계약.md',
                 'docs/research/20261104_P107_명시입력과_CLI_연결설계.md',
                 'handoff/audit/nov04_weight_space/build_smoke_scope.py'):
        paths[name] = 'owned'
    paths['handoff/202611011123_HANDOFF.md'] = 'shared'
    _, actions, changed, _ = build_plan(root, SESSION)
    commands = list(old['commands'])
    for action in changed:
        if action.kind != 'run' or '--' not in action.argv:
            continue
        child = list(action.argv[action.argv.index('--')+1:])
        hits = [name for name in SCOPED_COLLECTORS if name in child]
        if not hits:
            continue
        if len(hits) != 1:
            raise ValueError('ambiguous collector')
        _, _, target = _python_target(child)
        commands.append(dict(name=SCOPED_COLLECTORS[hits[0]], argv=target))
    if len(commands) != 10 or len(actions) != 106:
        raise ValueError('canonical static/collector/action inventory differs')
    old['inputs'] = [dict(path=name, role=role, sha256=sha256(Path(name)))
                     for name,role in sorted(paths.items())]
    old['commands'] = commands
    with output.open('x', encoding='utf-8') as stream:
        json.dump(old, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(json.dumps(dict(path=str(output), sha256=sha256(output), inputs=len(paths),
                          commands=len(commands), actions=106, children=44, session=SESSION)))


if __name__ == '__main__':
    main()
