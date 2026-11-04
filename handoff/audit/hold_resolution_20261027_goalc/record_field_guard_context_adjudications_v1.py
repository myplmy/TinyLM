"""Record four specific literal/style contexts; never change a corpus guard."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}


def read(path):
    payload = path.read_bytes()
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest().upper()
    return payload


guard_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
guard = json.loads(read(guard_path))
assert pins[str(guard_path.relative_to(ROOT))] == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
diagnostic_path = AUDIT / 'FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json'
diagnostic = json.loads(read(diagnostic_path))
assert pins[str(diagnostic_path.relative_to(ROOT))] == 'B8DB86B3F0F59887327E5935068095EE6AD0D71D101B323032A2415690F708F1'
records = []
for page, role, number, name, expected_sha in [
    (3, 'historical_review', '25945', 'expanded_train_25945_historical_review_20261103_v1.txt',
     '343FE9F230AF2A3F98575B2976EADA6BFAF93D58D1B2E429E4263855FB86AEAC'),
    (4, 'context_hangul', '46956', 'revise_46956_preserve_ghost_station_v1.txt',
     'A05B43376131BF3C38B27DD333D4ECD10B90728EE24DA3FC05F9E372D067DFBA'),
    (5, 'legacy_review', '60130', 'expanded_train_60130_revised_task011_v1.txt',
     '5EC0CBA9DC4973ABF4E72FB07E3608C624C261298799D823CBFFC1CFB1DB69F8'),
    (5, 'legacy_review', '62432', 'expanded_train_62432_revised_task012_v1.txt',
     '678E7047873948430564DFBFAF1A650C92E4F7B79928AEA78792CFBCEB6DCB6B'),
]:
    ident = 'expanded_train:' + number
    manifest_path = BASE / f'remaining_field_title_page_{page:03}_counter_v1/manifest.json'
    source = next(row for row in json.loads(read(manifest_path))['rows'] if row['id'] == ident)
    assert ident not in guard['restricted_ids'] and source['original']['sha256'] not in guard['restricted_hashes']
    original = read(ROOT / source['original']['path'])
    assert hashlib.sha256(original).hexdigest().upper() == source['original']['sha256']
    path = BASE / 'agents' / role / f'remaining_field_title_page_{page:03}_counter_v1' / name
    body = read(path)
    assert hashlib.sha256(body).hexdigest().upper() == expected_sha
    before, after = original.decode('utf-8'), body.decode('utf-8')
    if number == '25945':
        old = 'U+003F(?, 물음표)나 U+FFFD(, 유니코드 대치 문자)'
        new = 'U+003F(?, 물음표)나 U+FFFD(유니코드 대치 문자)'
        assert before.count(old) == after.count(new) == 1
        assert Counter(re.findall(r'U\+[0-9A-Fa-f]+', before)) == Counter(re.findall(r'U\+[0-9A-Fa-f]+', after))
        assert before.count('?, 물음표') == after.count('?, 물음표')
        details = dict(scope='Only the empty U+FFFD glyph slot separator; codepoint and name retained',
                       actual_question_mark_example_retained=True,
                       codepoint_multiset_unchanged=True,
                       missing_glyph_not_generated=True)
    elif number == '46956':
        spans = ['<span style="color:black;">', '<span style="color:silver;">']
        assert all(before.count(value) == 1 and value not in after for value in spans)
        assert "닉네임 '오랜지팩코'<span style=\"color:black;\">를 사용하는 청취자" in before
        assert "닉네임 '오랜지팩코'를 사용하는 청취자" in after
        assert 'SBS 라디오 팟캐스트 (현재 폐쇄)' in before and 'SBS 라디오 팟캐스트 (현재 폐쇄)' in after
        assert before.count('(현재 폐쇄)') == after.count('(현재 폐쇄)')
        details = dict(scope='Two presentation-only opening spans in the examined lines',
                       named_listener_and_closed_status_preserved=True,
                       semantic_colour_legend_not_present_in_these_contexts=True)
    elif number == '60130':
        pairs = [
            ("24. 땡땡과 알파아트(Tintin et l'Alph-art) (1986, 2004)", '에르제 사후에 미완성 유고작으로 출간됨'),
            ('25. 땡땡과 상어 호수 (Tintin et le lac aux requins) (1972)', '극장판 애니메이션을 원작으로 만들어짐'),
        ]
        for title, note in pairs:
            assert before.count(title + '<div style="text-align: center;">' + note) == 1
            assert after.count(title + '\n   ' + note) == 1
        assert '브느와 페터스 (1984) . Magic-Strip.' in before
        assert '브느와 페터스 (1984), Magic-Strip.' in after
        details = dict(scope='Two centred notes remain directly under their original named books and years',
                       title_year_note_relations_preserved=True,
                       separate_missing_bibliographic_title_followup_open=True,
                       missing_title_row_not_approved_by_style_adjudication=True)
    else:
        empty = before[before.index('{| class="wikitable sortable"'):before.index('\n국가 정보')]
        assert empty.endswith('| <div style="text-align: center;">\n')
        assert all(label in empty for label in ('! 지역', '! 회원국', '! 수반직책', '! 정부수반'))
        assert '{|' not in after and 'text-align' not in after
        assert '구성원\n\nG20의 구성원은' in after
        for empty_heading in ('지역 그룹', '참석 정부수반', '국가 정보', '정상회의\n'):
            assert empty_heading not in after
        assert '보건장관 회의\nG20 보건장관회의 - 2021년 9월 5일-6일, 이탈리아 로마' in after
        assert '이상 생략' not in after
        details = dict(scope='Style belongs to an empty wikitable with column labels but no member rows',
                       missing_table_not_reconstructed=True,
                       retained_members_heading_has_actual_prose=True,
                       dated_health_minister_meeting_preserved=True,
                       current_membership_or_source_factual_correctness_not_verified=True)
    records.append(dict(id=ident, original=source['original'],
                        body=dict(path=str(path.relative_to(ROOT)), sha256=expected_sha),
                        details=details, whole_body_semantic_pass=False))
read(Path(__file__).resolve())
result = dict(status='FOUR_SOURCE_SPECIFIC_UNICODE_AND_STYLE_CONTEXTS_ADJUDICATED',
              records=records, actual_scoped_context_reads=['ccf7ee', '299ad4', '454f85'],
              generic_guards_changed=False, automatic_waivers=0,
              unrelated_numeric_ordered_or_code_flags_closed=False,
              separate_60130_bibliographic_followup_pending=True,
              new_root_or_cache_admissions=0, input_pins=pins,
              whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'FIELD_FOUR_LITERAL_STYLE_CONTEXT_ADJUDICATIONS_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
observation = dict(status='RECORDED_PRIOR_ACTUAL_NARROW_LANGUAGE_SCREEN_OBSERVATION',
                   actual_command_result='97b3f2', frozen_body_pairs_checked=2220,
                   original_without_hangul_to_body_with_hangul=0,
                   diagnostic_complete=dict(path=str(diagnostic_path.relative_to(ROOT)),
                       sha256=pins[str(diagnostic_path.relative_to(ROOT))]),
                   versions=diagnostic['versions'],
                   body_pairs_reread_for_recording_this_observation=False,
                   post_freeze_47905_intermediate_v3_not_in_this_screen=True,
                   unrelated_languages_or_semantic_changes_checked=False,
                   corpus_wide_language_or_semantic_approval=False,
                   whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'FIELD_BOUND_HANGUL_ADDITION_SCREEN_OBSERVATION_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(observation, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(contexts=4, generic_guard_changes=0, unrelated_flags_closed=0,
                     missing_bibliographic_title_followup_open=1,
                     recorded_prior_hangul_screen_pairs=2220, new_hangul_in_that_screen=0)))
