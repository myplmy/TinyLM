"""Verify and read sealed native-scale answers without loading any model."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from scripts.p108_readback import load_rows, paired_family_interval, write_small


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'test_result/evidence/p108_native_v1_20261105/new595-broad-q'
PROFILE_SHA = '77263DFCDDE3B7233491F69F23B282A743B993550EF243520DC5731CDAB09E65'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    if digest(BASE / 'profile.json') != PROFILE_SHA:
        raise ValueError('frozen profile differs')
    report = json.loads((BASE / 'confirm/report.json').read_text(encoding='utf-8'))
    if (report['profile_sha256'] != PROFILE_SHA
            or not report['final_source_and_original_bindings_unchanged']
            or report['optimizer_updates'] or report['training_tokens']
            or report['original_checkpoint_writes']
            or report['final_cuda_cleanup']['allocated_bytes']
            or report['final_cuda_cleanup']['reserved_bytes']):
        raise ValueError('run integrity or final cleanup is incomplete')
    grouped = defaultdict(dict)
    for row in load_rows(BASE / 'confirm'):
        if row['id'] in grouped[row['variant']]:
            raise ValueError('duplicate variant/item')
        grouped[row['variant']][row['id']] = row
    expected_names = {'original_test', 'requant_common_g1_test', 'targeted_test',
                      'native_random_17_test', 'native_random_29_test',
                      'native_random_43_test'}
    if set(grouped) != expected_names:
        raise ValueError('declared variants differ')
    original = grouped['original_test']
    if len(original) != 288:
        raise ValueError('original item count differs')
    output = dict(schema='P108_NATIVE_READBACK_V1', status='GATE_NEGATIVE',
        profile_sha256=PROFILE_SHA, run_report_sha256=digest(BASE / 'confirm/report.json'),
        paired_scope='FROZEN_PRACTICE_NOT_OFFICIAL_BENCHMARK',
        selection_changed=False, model_loading=False, variants={})
    for name, values in grouped.items():
        if set(values) != set(original):
            raise ValueError('paired IDs differ')
        changed_answers, changed_ids, changed_finishes = [], [], []
        for key, row in values.items():
            base = original[key]
            for field in ('question', 'expected', 'family', 'language', 'split',
                          'source_group', 'protected', 'rule'):
                if (field in row) != (field in base) or row.get(field) != base.get(field):
                    raise ValueError('paired content differs: ' + field)
            if row['answer'] != base['answer']:
                changed_answers.append(key)
            if row['generation']['generated_ids'] != base['generation']['generated_ids']:
                changed_ids.append(key)
            if row['generation']['finish_reason'] != base['generation']['finish_reason']:
                changed_finishes.append(key)
        scored = [r for r in values.values() if r['expected'] is not None]
        family = {}
        for kind in sorted({r['family'] for r in scored}):
            items = [r for r in scored if r['family'] == kind]
            family[kind] = dict(items=len(items), exact=sum(r['exact'] for r in items),
                loop_indicators=sum(r['diagnostics']['loop_indicator'] for r in items))
        output['variants'][name] = dict(items=len(values), scored=len(scored),
            exact=sum(r['exact'] for r in scored), by_family=family,
            changed_answers=changed_answers, changed_generated_ids=changed_ids,
            changed_finish_reasons=changed_finishes,
            open_seen=sum(r['split'] == 'open_seen' for r in values.values()),
            open_fresh=sum(r['split'] == 'open_fresh' for r in values.values()),
            answers_frequency=Counter(r['answer'] for r in scored).most_common(10),
            paired=None if name == 'original_test'
            else paired_family_interval(original, values))
    text = ['# 원본과 동결 삼진 편집의 실제 질문·답 전체', '',
        '새 규칙 test256, 이전 일상16, 새 일상16을 구분한다. '
        '공식 벤치마크가 아니며 이 원답으로 편집 후보를 다시 고르지 않았다.', '']
    for key, base in original.items():
        target = grouped['targeted_test'][key]
        expected = base['expected'] if base['expected'] is not None else '자동 정답 미지정'
        text.extend([f'## {key}', '', f'구분: {base["split"]} / {base["family"]}', '',
            f'질문: {base["question"]}', '', f'기대답: {expected}', '',
            '원본 답:', '', *['    ' + s for s in base['answer'].splitlines()], '',
            '삼진 편집 답:', '', *['    ' + s for s in target['answer'].splitlines()], '',
            f'종료: {base["generation"]["finish_reason"]} -> '
            f'{target["generation"]["finish_reason"]}', ''])
    write_small(BASE / 'readback/summary.json',
                json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + chr(10))
    write_small(BASE / 'readback/original_target_pairs.md', chr(10).join(text) + chr(10))
    print(json.dumps({name: {k: v[k] for k in ('exact', 'changed_answers',
          'changed_generated_ids', 'changed_finish_reasons', 'paired')}
          for name, v in output['variants'].items()}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
