"""Verify category-tail edits and two source-preserving context followups."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
A = Path(__file__).resolve().parent
B = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
guard_raw = (A / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_bytes()
assert hashlib.sha256(guard_raw).hexdigest().upper() == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
guard = json.loads(guard_raw)

def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest().upper())

def snapshot_row(page, version, identity):
    complete_path = B / f'remaining_field_title_page_{page:03}_counter_v1_snapshots/{version}/complete.json'
    complete = json.loads(complete_path.read_text())
    assert not complete['errors']
    found = []
    for shard in complete['shards']:
        raw = (ROOT / shard['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest().upper() == shard['sha256']
        value = json.loads(raw)
        rows = value if isinstance(value, list) else value.get('rows', value.get('records'))
        found.extend(row for row in rows if row['id'] == identity)
    assert len(found) == 1
    return found[0], pin(complete_path)

def review_rows(path):
    return {m.group(1): line for line in path.read_text().splitlines()
            if (m := re.match(r'^\|\s*(expanded_train:[0-9]+)\s*\|', line))}

records = []
for number, page in [('114651', 8), ('114848', 8), ('168901', 9), ('169725', 9)]:
    identity = 'expanded_train:' + number
    source = next(row for row in json.loads((B / f'remaining_field_title_page_{page:03}_counter_v1/manifest.json').read_text())['rows'] if row['id'] == identity)
    assert identity not in guard['restricted_ids']
    assert source['original']['sha256'] not in guard['restricted_hashes']
    row, frozen = snapshot_row(page, 'v11' if page == 8 else 'v6', identity)
    assert row['original'] == source['original']
    new_path = ROOT / row['author_output']['path']
    new_raw = new_path.read_bytes()
    assert hashlib.sha256(new_raw).hexdigest().upper() == row['clean_text_sha256'] == row['author_output']['sha256']
    new = new_raw.decode()
    folder = new_path.parent
    old_review = None
    if page == 8:
        old_row, old_frozen = snapshot_row(8, 'v10', identity)
        old_path = ROOT / old_row['body']
        old_raw = old_path.read_bytes()
        assert hashlib.sha256(old_raw).hexdigest().upper() == old_row['clean_text_sha256']
        old = old_raw.decode()
        deleted = ('1993년 설립된 스포츠 리그' + chr(10) + '슬로바키아의 축구 리그' + chr(10) + '유럽의 축구 1부 리그' + chr(10)
                   if number == '114651' else '일본의 연호' + chr(10) + '헤이안 시대' + chr(10))
        assert old.endswith(deleted)
        assert old[:-len(deleted)] == new
        old_review = ROOT / old_row['review']['path']
        before, after = review_rows(old_review), review_rows(ROOT / row['review']['path'])
        targets = {'expanded_train:114651', 'expanded_train:114848'}
        assert len(before) == len(after) == 5 and set(before) == set(after)
        assert all(before[k] == after[k] for k in before if k not in targets)
        sidecar = folder / f'hold_{number}_category_tail_20261104_v1.md'
        details = dict(exact_deleted_tail=deleted, other_three_review_rows_unchanged=True,
                       original_narrative_outside_tail_unchanged=True)
    elif number == '168901':
        old_path = folder / 'expanded_train_168901_task014_v1.txt'
        old_raw = old_path.read_bytes()
        assert hashlib.sha256(old_raw).hexdigest().upper() == '53FE70ED53770A61DCD17DEE4318478087CC5CD918F844BC3973A455712C1961'
        old = old_raw.decode()
        definition = '만약 피적분 함수가 직접 적분하지 못하는 곳의 임의의 근방에서 무계 함수라면, 그 이상 적분을 특이 적분(特異積分)이라고 한다.'
        anchor = chr(10) + '무한대 적분'
        replacement = chr(10) + '특이 적분' + chr(10) + definition + chr(10)*2 + '무한대 적분'
        assert old.count(anchor) == 1 and old.replace(anchor, replacement, 1) == new
        original_raw = (ROOT / source['original']['path']).read_bytes()
        assert hashlib.sha256(original_raw).hexdigest().upper() == source['original']['sha256']
        original = original_raw.decode()
        assert definition.replace('(特異積分)', '(特異積分, )') in original
        convergence = '함수의 절댓값의 이상 적분의 수렴은 원래 이상 적분의 수렴보다 더 강한 조건이다. 절댓값의 이상 적분이 수렴한다면, 원래 이상 적분이 절대 수렴(絶對收斂)한다고 한다.'
        assert convergence in new and convergence in old
        old_review = folder / 'review_014_v5.md'
        before, after = review_rows(old_review), review_rows(ROOT / row['review']['path'])
        assert len(before) == len(after) == 5 and all(before[k] == after[k] for k in before if k != identity)
        sidecar = folder / 'hold_168901_task014_v3.md'
        details = dict(exact_restored_condition_definition=definition,
                       empty_foreign_slot_only_removed_from_definition=True,
                       absolute_value_convergence_sentences_preserved=True,
                       standalone_filled_term_적분학_preserved=new.rstrip().endswith('적분학'),
                       old_overheld_definition_output_preserved=True,
                       other_four_review_rows_unchanged=True,
                       original_to_first_version_broad_diff_read='98c8a8',
                       exact_followup_diff_read='1f7932')
    else:
        old_path = ROOT / source['candidate']['path']
        old_raw = old_path.read_bytes()
        assert hashlib.sha256(old_raw).hexdigest().upper() == source['candidate']['sha256']
        old = old_raw.decode()
        prefix = '카라( 등)는 다음 뜻으로 쓰인다.' + chr(10)*2
        assert old.startswith(prefix)
        expected = old[len(prefix):]
        assert expected.count('카라 (북유럽 신화)()') == 1
        expected = expected.replace('카라 (북유럽 신화)()', '카라 (북유럽 신화)', 1) + chr(10)
        assert expected == new
        sidecar = folder / 'hold_169725_task014_v1.md'
        details = dict(only_unbound_intro_and_empty_parentheses_removed=True,
                       all_filled_named_list_entries_preserved=True,
                       same_ambiguous_등_not_rewritten_as_known_subject=True,
                       final_LF_added_recorded=True, actual_full_diff_read='98c8a8')
    assert source['id'] == identity and sidecar.is_file()
    records.append(dict(id=identity, original=source['original'], old_body=pin(old_path),
                        new_body=pin(new_path), snapshot=frozen, review=row['review'],
                        old_review=pin(old_review) if old_review else None, sidecar=pin(sidecar),
                        details=details, UTF8_valid=True,
                        old_EOF_LF=old_raw.endswith(bytes([10])),
                        new_EOF_LF=new_raw.endswith(bytes([10])),
                        outside_specified_scope_unchanged=True,
                        root_authored_training_body=False))
target = A / 'ROOT_FOUR_FIELD_SCOPED_FOLLOWUPS_VERIFIED_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(dict(status='FOUR_NARROW_FIELD_FOLLOWUPS_EXACTLY_BOUND_NOT_ADMISSION',
                   records=records, new_first_review_unique_added_by_this_check=0,
                   root_or_cache_admissions=0, whole_goal_complete=False,
                   training_authorized=False), stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(path=str(target.relative_to(ROOT)), records=4,
                     sha256=hashlib.sha256(target.read_bytes()).hexdigest().upper()), ensure_ascii=False))
