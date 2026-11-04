"""Exact P107/P108 current static input binding; no ledger mutation."""
import argparse
import json
from pathlib import Path
from scripts.validation_scope import sha256

BASE = Path('handoff/audit/nov04_p107_cli')
SOURCE = Path('handoff/audit/nov04_weight_space/OWNED_INPUTS_v9.json')
EXTRA = (
    'tinylm/train/document_input.py', 'scripts/train_p107_documents.py',
    'scripts/diag_p107_document_cli.py', 'scripts/test_p107_document_input.py',
    'scripts/test_p107_document_cli.py',
    'test_plan/P107_문서가시성과-shift를-분리한-causal-MNTP-계약.md',
    'test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md',
    'docs/research/20261104_P107_명시입력과_CLI_연결설계.md',
    'docs/methods/05_training_speed.md',
    'handoff/202611042233_HANDOFF.md',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', type=int)
    args = parser.parse_args()
    if not 1 <= args.version <= 9:
        raise ValueError('fresh explicit revision required')
    output = BASE/('STATIC_INPUTS_v'+str(args.version)+'.json')
    if output.exists():
        raise FileExistsError(output)
    value = json.loads(SOURCE.read_text(encoding='utf-8'))
    paths = {r['path']:r['role'] for r in value['inputs'] if Path(r['path']).is_file()}
    own = [Path(name) for name in EXTRA]
    own += list(BASE.glob('*.py'))
    own += list(Path('handoff/audit/nov04_weight_space').glob('*.py'))
    own += list(Path('.').glob('run_P107_Stage8*.sh'))
    for path in own:
        paths[path.as_posix()] = 'owned'
    paths['handoff/audit/nov01_afternoon/prepare_owned_commit_v3.py'] = 'shared'
    value['inputs'] = [dict(path=name, role=role, sha256=sha256(Path(name))) for name,role in sorted(paths.items())]
    with output.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
    print(json.dumps(dict(path=str(output),sha256=sha256(output),inputs=len(paths))))


if __name__ == '__main__':
    main()
