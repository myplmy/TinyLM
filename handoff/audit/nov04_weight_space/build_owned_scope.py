"""Pin exact current P108 owned inputs plus existing shared dependencies.

The WIP is read only. The official ledger writer remains its sole mutator.
No other-session tree is enumerated, read or admitted as a fallback.
"""
import argparse
import json
from pathlib import Path

from scripts import validation_scope as scope

BASE = Path('handoff/audit/nov04_weight_space')
EXACT = (
    'handoff/WIP_20261022_작업원장.md',
    'docs/EXPERIMENT_BASELINES.md', 'docs/METHODS.md', 'handoff/COMPASS.md',
    'experiments.tsv',
    'docs/methods/03_knowledge_quality.md',
    'ai_dev_tool/Codex/08_AI-미보고-내역-자백원장.md',
    'test_plan/P108_직접가중치-방향수리와-학습개입.md',
    'test_plan/실험계획목록.md', 'test_result/실험목록.md',
    'test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True, type=int)
    args = parser.parse_args()
    if args.version < 4:
        raise ValueError('existing historical manifests are immutable')
    output = BASE/('OWNED_INPUTS_v'+str(args.version)+'.json')
    if output.exists():
        raise FileExistsError(output)
    old = json.loads((BASE/'OWNED_INPUTS_v3.json').read_text(encoding='utf-8'))
    paths = {row['path']: row['role'] for row in old['inputs'] if Path(row['path']).is_file()}
    own = [Path(name) for name in EXACT]
    own += list(Path('scripts').glob('*p108*.py'))
    own += list(Path('.').glob('run_P108_*.sh'))
    own += list(Path('docs/research').glob('20261104_P108_*.md'))
    own += list(BASE.glob('*.py'))
    for tag in ('p108w_v1_20261104', 'p108w_v2_20261104',
                'p108w_v3_20261104', 'p108j_v1_20261104'):
        # initial_plan.md is a byte-frozen source snapshot with links relative
        # to its original test_plan directory, not a relocated live document.
        # ARCHIVAL_PLAN_CONTEXT_v1 separately verifies its bytes and origin.
        own += list((Path('test_result/evidence')/tag).rglob('original_target_pairs.md'))
    for path in own:
        if not path.is_file():
            raise FileNotFoundError(path)
        paths[path.as_posix()] = 'owned'
    paths['scripts/sync_experiments_tsv.py'] = 'shared'
    old['inputs'] = [dict(path=name, role=role, sha256=scope.sha256(Path(name)))
                     for name, role in sorted(paths.items())]
    data = (json.dumps(old, ensure_ascii=False, indent=2)+chr(10)).encode('utf-8')
    with output.open('xb') as stream:
        stream.write(data)
    print(json.dumps(dict(path=str(output), inputs=len(paths), sha256=scope.sha256(output))))


if __name__ == '__main__':
    main()
