"""Read-only scoring of sealed P108 artifacts; writes fresh small summaries.

No model imports or execution. Selection is never changed by this readback.
"""
from collections import defaultdict
import json
from pathlib import Path
import random

from scripts.p106b_shards import verify

BASE = Path('test_result/evidence/p108w_v2_20261104/new595-broad-q')


def load_rows(directory):
    manifest = json.loads((directory / 'answers_shards_manifest.json').read_text(encoding='utf-8'))
    verify(directory, manifest)
    rows = []
    for shard in manifest['shards']:
        rows.extend(json.loads(line) for line in (directory / shard['path']).read_text(encoding='utf-8').splitlines())
    return rows


def paired_family_interval(original, candidate, repeats=5000, seed=1337):
    if set(original) != set(candidate):
        raise ValueError('paired IDs differ')
    groups = defaultdict(list)
    wins = losses = 0
    for key, base in original.items():
        row = candidate[key]
        if row['expected'] is None:
            continue
        if (row['question'], row['expected'], row['family']) != (base['question'], base['expected'], base['family']):
            raise ValueError('paired question/expected/family differs')
        a, b = int(base['exact']), int(row['exact'])
        groups[base['family']].append(b-a)
        wins += b > a
        losses += a > b
    rng = random.Random(seed)
    names = sorted(groups)
    samples = []
    for _ in range(repeats):
        selected = [groups[rng.choice(names)] for _ in names]
        samples.append(sum(sum(group) for group in selected) / sum(len(group) for group in selected))
    samples.sort()
    return dict(family_groups=len(groups), resamples=repeats, seed=seed, unit='TASK_FAMILY',
                corrected=wins, regressed=losses,
                delta_accuracy=(wins-losses)/sum(map(len,groups.values())),
                percentile_95=[samples[int(.025*(repeats-1))], samples[int(.975*(repeats-1))]],
                inferential_scope='EXPLORATORY_FROZEN_PRACTICE_NOT_GENERAL_INTELLIGENCE')


def write_small(path, text):
    data = text.encode('utf-8')
    if len(data) >= 3_000_000:
        raise ValueError('readback must stay below 3MB')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model',choices=('q','f','j'),nargs='?',default='q')
    chosen=parser.parse_args().model
    base_dir = {'q': BASE,
        'f': Path('test_result/evidence/p108w_v3_20261104/new595-broad-f'),
        'j': Path('test_result/evidence/p108j_v1_20261104/new595-broad-q')}[chosen]
    rows = load_rows(base_dir / ('confirm_fixed_support' if chosen=='q' else 'confirm'))
    variants = defaultdict(dict)
    for row in rows:
        if row['id'] in variants[row['variant']]:
            raise ValueError('duplicate variant/item')
        variants[row['variant']][row['id']] = row
    original = variants['original_test']
    output = dict(schema='P108_READBACK_V1', status='GATE_NEGATIVE',
        primary_comparison=paired_family_interval(original,variants['targeted_test']), variants={})
    for name, values in sorted(variants.items()):
        scored = [r for r in values.values() if r['expected'] is not None]
        by_family = {}
        for family in sorted({r['family'] for r in scored}):
            group = [r for r in scored if r['family']==family]
            by_family[family] = dict(items=len(group), exact=sum(r['exact'] for r in group),
                                     verbatim_exact=sum(r['answer'].strip()==r['expected'] for r in group))
        output['variants'][name] = dict(items=len(values),scored=len(scored),by_family=by_family,
            normalized_positive_not_verbatim=[r['id'] for r in scored if r['exact'] and r['answer'].strip()!=r['expected']],
            paired=None if name=='original_test' else paired_family_interval(original,values))
    split = ('새 균형 test256과 이미 본 일상16 회귀' if chosen == 'j'
             else '새 규칙형 test128과 별도 일상16')
    text = ['# P108 원본과 동결 수리의 실제 질문·답', '',
            split+'의 전체 대응 원답이다. 공식 벤치마크가 아니며 test 정답표는 보정 선택에 사용하지 않았다.', '']
    for key, base in original.items():
        target = variants['targeted_test'][key]
        text.extend([f'## {key}', '', f'질문: {base["question"]}', '',
            '기대답: ' + ('자동 정답 미지정; 총괄 판독 대상' if base['expected'] is None else base['expected']), '',
            '원본 답:', '', *['    '+line for line in base['answer'].splitlines()], '',
            '수리 답:', '', *['    '+line for line in target['answer'].splitlines()], '',
            f'종료: {base["generation"]["finish_reason"]} → {target["generation"]["finish_reason"]}', ''])
    write_small(base_dir/'readback'/'original_target_pairs.md', chr(10).join(text)+chr(10))
    write_small(base_dir/'readback'/'summary.json',json.dumps(output,ensure_ascii=False,sort_keys=True,indent=2)+chr(10))
    print(json.dumps(dict(primary=output['primary_comparison'],
        normalized_positive_not_verbatim={name:r['normalized_positive_not_verbatim'] for name,r in output['variants'].items()}),ensure_ascii=False))


if __name__=='__main__':
    main()
