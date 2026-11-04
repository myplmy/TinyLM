"""Bind two previously reported editing incidents to exact selected outputs."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
A = Path(__file__).resolve().parent
B = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
guard_path = A / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
guard_raw = guard_path.read_bytes()
assert hashlib.sha256(guard_raw).hexdigest().upper() == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
guard = json.loads(guard_raw)

def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest().upper())

specs = [
    dict(number='163020', page=9, role='context_hangul', task=9,
         name='expanded_train_163020_task009_v1.txt',
         note='note_163020_packet_context_mixup_v1.md',
         sidecar='hold_163020_task009_v1.md',
         sha='36F44A5B74A9616D6C82F2D6DC8B6EE56E471780E2ACAA48201CC046B071CE83',
         edits=[(25, 29, ', , ', ''),
                (7082, 7127, '이 책에서는 포그가 80일 만에 세계를 일주하는 것을 두고 리폼 클럽의 사다.' + chr(10) + ' ', ''),
                (7406, 7411, chr(10) * 2 + '각주 ', ''),
                (7777, 7777, '', chr(10))]),
    dict(number='96670', page=7, role='legacy_review', task=18,
         name='expanded_train_96670_revised_task018_v2.txt',
         note='incident_96670_task018_range_edit_v1.md',
         sidecar='hold_96670_task018_v2.md',
         sha='77D77A41F32DBF129B5B469C7F099E66504CE02B14A2F1D04ADCB66E93FC00FD',
         edits=[(137, 163, chr(10).join(['', '자동차 운전자의 주의의무', '', '긍정사례', '', '부정사례']), ''),
                (842, 886, chr(10).join(['', '부정사례', '', '공사감독자', '', '긍정사례', '', '부정사례', '', '교사 보호자', '', '긍정사례', '', '부정사례']), ''),
                (4016, 4021, '<ref>', ' '), (4042, 4047, '<ref>', ''),
                (5741, 5744, ' ()', ''), (5843, 5846, ' ()', ''),
                (5878, 5882, '각주 ' + chr(10), '')]),
]
records = []
for spec in specs:
    identity = 'expanded_train:' + spec['number']
    manifest_path = B / f"remaining_field_title_page_{spec['page']:03}_counter_v1/manifest.json"
    source = next(row for row in json.loads(manifest_path.read_text())['rows'] if row['id'] == identity)
    assert identity not in guard['restricted_ids']
    assert source['original']['sha256'] not in guard['restricted_hashes']
    original_path, candidate_path = ROOT / source['original']['path'], ROOT / source['candidate']['path']
    original_raw, candidate_raw = original_path.read_bytes(), candidate_path.read_bytes()
    assert hashlib.sha256(original_raw).hexdigest().upper() == source['original']['sha256']
    assert hashlib.sha256(candidate_raw).hexdigest().upper() == source['candidate']['sha256']
    assert original_raw == candidate_raw
    folder = B / 'agents' / spec['role'] / f"remaining_field_title_page_{spec['page']:03}_counter_v1"
    initial = folder / f"expanded_train_{spec['number']}_initial_candidate_v1.txt"
    assert initial.read_bytes() == candidate_raw
    old = candidate_raw.decode('utf-8')
    selected_path = folder / spec['name']
    selected_raw = selected_path.read_bytes()
    selected = selected_raw.decode('utf-8')
    assert hashlib.sha256(selected_raw).hexdigest().upper() == spec['sha']
    expected = old
    for start, end, before, after in reversed(spec['edits']):
        assert old[start:end] == before, (identity, start, end)
        expected = expected[:start] + after + expected[end:]
    assert expected == selected
    review_path = folder / f"review_{spec['task']:03}.md"
    lines = [line for line in review_path.read_text().splitlines() if re.match(r'^\|\s*' + re.escape(identity) + r'\s*\|', line)]
    assert len(lines) == 1 and spec['name'] in lines[0]
    row = dict(id=identity, original=source['original'], candidate=source['candidate'],
               initial=pin(initial), selected=pin(selected_path), review=pin(review_path),
               note=pin(folder / spec['note']), sidecar=pin(folder / spec['sidecar']),
               exact_edits=[dict(source_span=[s,e], before=x, after=y) for s,e,x,y in spec['edits']],
               outside_exact_edits_unchanged=True, UTF8_valid=True,
               source_EOF_LF=candidate_raw.endswith(bytes([10])),
               selected_EOF_LF=selected_raw.endswith(bytes([10])),
               actual_full_diff_and_note_read='d11c9b', exact_character_diff_read='356637',
               whole_document_fact_verification=False, root_authored_training_body=False)
    if spec['number'] == '163020':
        assert '구슬' not in old and len(old) == 7777
        row.update(incident='AUTHOR_REPORT_CONFUSED_WITH_161287_NOT_SOURCE_CORRUPTION',
                   note_records_its_creation_time_not_current_selection=True,
                   original_and_candidate_identical=True, added_final_LF_recorded=True)
    else:
        failed = folder / 'expanded_train_96670_revised_task018_v1.txt'
        failed_text = failed.read_text(encoding='utf-8')
        assert '미국' not in failed_text and len(failed_text) < len(selected)
        assert 'expanded_train_96670_revised_task018_v1.txt' not in lines[0]
        assert '2011. 9. 8. 2009도1395' in selected
        assert old[4047:] .replace(' ()', '').replace('각주 ' + chr(10), '') == selected[3968:]
        row.update(incident='SED_END_ANCHOR_TRAILING_SPACE_MISMATCH_LOST_TAIL_IN_UNSELECTED_V1',
                   failed_unselected_preserved=pin(failed), failed_v1_selected=False,
                   filled_case_citation_preserved=True, legal_narrative_and_tail_preserved=True,
                   legal_truth_or_current_law_verified=False)
    records.append(row)
target = A / 'ROOT_163020_AND_96670_SELECTED_RECOVERY_VERIFIED_V1.json'
result = dict(status='EXACT_SELECTED_OUTPUTS_AND_INCIDENT_NOTES_VERIFIED', records=records,
              root_or_cache_admissions=0, whole_goal_complete=False, training_authorized=False)
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(path=str(target.relative_to(ROOT)), sha256=pin(target)['sha256'], records=len(records))))
