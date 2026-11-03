"""Check eight manually adjudicated author outputs; never write corpus TXT."""
from pathlib import Path
import ast
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import exact_entry, load_parser
from scripts import p106b_hold_resolution_author_output_bindings_v1 as binding

reused = AUDIT / 'verify_current_birth_followups_v1.py'
names = {'sha', 'read', 'pin', 'verify', 'replace_once'}
definitions = [node for node in ast.parse(reused.read_text(encoding='utf-8')).body
               if isinstance(node, ast.FunctionDef) and node.name in names]
assert len(definitions) == len(names) and all(not node.decorator_list for node in definitions)
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(reused), 'exec'), globals())

contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract = read(contract_path)
resolve, parse, parser_sha = load_parser()
birth = 'birth_root11_independent_v1'
field = 'remaining_field_title_page_006_counter_v1'
specs = {
    '625422': (birth, 'context_controls', 'expanded_train_625422_reviewed_v2.txt', 'review_187_v2.md', ['hold_625422_v2.md']),
    '56462': (birth, 'context_latin', 'reviewed_56462_task173_v2.txt', 'review_173_v2.md', ['hold_56462_task173_v2.md']),
    '511882': (birth, 'context_latin', 'reviewed_511882_task167_v1.txt', 'review_167_v2.md', ['hold_511882_task167_awards_birth_v2.md', 'hold_511882_task167_birth_and_table_v1.md']),
    '367209': (birth, 'context_latin', 'reviewed_367209_task142_v1.txt', 'review_142_v2.md', ['hold_367209_task142_v1.md']),
    '58381': (birth, 'context_latin', 'reviewed_58381_task177_v2.txt', 'review_177_v2.md', ['hold_58381_task177_v1.md']),
    '82044': (field, 'context_hangul', 'expanded_train_82044_task015_v2.txt', 'review_015.md', ['hold_82044_task015_v1.md']),
    '83431': (field, 'context_hangul', 'expanded_train_83431_task016_v1.txt', 'review_016.md', ['hold_83431_task016_v1.md']),
    '740452': (birth, 'context_controls', 'expanded_train_740452_reviewed_v1.txt', 'review_214_v2.md', ['hold_740452_v1.md', 'note_740452_input_equality_correction_v1.md']),
}
manifests = {cohort: read(BASE / cohort / 'manifest.json') for cohort in (birth, field)}
sources = {cohort: {row['id']: row for row in manifest['rows']} for cohort, manifest in manifests.items()}
pins = [pin(contract_path), pin(reused), pin(Path(__file__).resolve()),
        pin(AUDIT / 'exact_manifest_review_row_binding_v1.py'),
        pin(ROOT / 'scripts/p106b_hold_resolution_author_output_bindings_v1.py')]
pins += [pin(BASE / cohort / 'manifest.json') for cohort in manifests]
rows = []

for number, (cohort, role, filename, review_name, notes) in specs.items():
    ident = 'expanded_train:' + number
    source = sources[cohort][ident]
    assert source['role'] == role
    # Both metadata predicates precede any source, candidate, or author-body IO.
    assert ident not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    original, candidate = verify(source['original']), verify(source['candidate'])
    directory = BASE / 'agents' / role / cohort
    selected_pin = pin(directory / filename)
    selected = verify(selected_pin)
    review_path = directory / review_name
    entry = exact_entry(review_path.read_bytes(), ident, set(sources[cohort]), resolve, parse)
    assert entry['cells'][1] == 'REVISE_TEXT'
    absolute = {label: dict(source[label], path=str(ROOT / source[label]['path'])) for label in ('original', 'candidate')}
    assert binding.declared_txt_basename(entry['cells'][3], ident, directory, absolute, 'EDIT_TEXT') == filename
    base = 'original' if number in {'625422', '56462', '82044', '83431'} else 'candidate'
    expected = original if base == 'original' else candidate
    edits = []

    def change(old, new, count=1):
        global expected
        assert expected.count(old) == count, (ident, old, expected.count(old), count)
        expected = expected.replace(old, new)
        edits.append(dict(old=old, new=new, occurrences=count))

    if number == '625422':
        for old, new in [('(, 덴분', '(덴분'), ('사자()', '사자'),
                         ('(호리오 다지마, )', '(호리오 다지마)'),
                         ('(호리오 탄게, )', '(호리오 탄게)'),
                         ('(호리오 시게스케 4대, )', '(호리오 시게스케 4대)'),
                         ('나가오키.쵸젠의 남동생)을', '나가오키를'), ('호리오성()', '호리오성')]:
            change(old, new)
    elif number == '56462':
        change('1932년 김덕기에게 붙잡혀 사형 선고를 받고', '1932년 김덕기에게 붙잡혔다. 사형 선고를 받고')
        change('1995년{{', '1995년')
    elif number == '511882':
        change('수상 ' + chr(10) + ' 2× WKBL 기량발전상' + chr(10),
               '수상 ' + chr(10) + ' WKBL 베스트 5' + chr(10) + ' 2× WKBL 기량발전상' + chr(10) + ' WKBL 식스우먼상' + chr(10))
        change(chr(10) + ' ' + chr(10), chr(10)*2)
        table = original[original.index('기록 ' + chr(10)):original.index('수상 ' + chr(10))].rstrip(chr(10))
        assert table in (directory / notes[1]).read_text(encoding='utf-8')
    elif number == '367209':
        change('선조의 명을 받고의병의 지휘를', '선조의 명을 받았다. 의병의 지휘를')
        change('맡기고 길을 떠났다가 5월 21일', '맡기고 길을 떠났다. 5월 21일')
        change('그해 10월에 남양주에 안장되었다.', '10월에 남양주에 안장되었다.')
    elif number == '58381':
        change('8월 10일 ~ 2002년 1월 2일', '8월 10일 출생, 1월 2일 사망')
        v1 = (directory / 'reviewed_58381_task177_v1.txt').read_text(encoding='utf-8')
        assert selected == replace_once(v1, '8월 10일 ~ 1월 2일', '8월 10일 출생, 1월 2일 사망')
    elif number == '82044':
        change('()', '', 7)
        change('[]', '')
        change('는 도치기현 우쓰노미야시 출신 사이타마현에서', '치하라 미노리는 도치기현 우쓰노미야시 출신으로 사이타마현에서')
        change('음악' + chr(10)*2 + '싱글' + chr(10), '음악' + chr(10)*2)
        change('일등성（)（2010년 8월 7일）', '일등성 (2010년 8월 7일)')
        change('각주' + chr(10), '')
        assert '2013년 3월 31일자로 전속계약이 만료됨에 따라 4월부터는' in selected
        assert '가족 관계는 2녀 1남 중 차녀이다.' in selected
    elif number == '83431':
        change(' ()', '', 30)
        change('()', '', 12)
        for old, new in [('(보노)는', 'Buono! (보노)는'), ('연애라이더( (', '연애라이더 ('),
                         ('진검 승부로 가자!(（', '진검 승부로 가자!('), ('롯타라 롯타라(（', '롯타라 롯타라('),
                         (', 는 영화《고멘나사이》주제가', ''), ('각주' + chr(10), '')]:
            change(old, new)
        assert '양 A면 싱글. 커플링 곡은 없음.' in selected
    elif number == '740452':
        change('1078년 출생' + chr(10), '')
        copy_path = directory / 'expanded_train_740452_initial_candidate_v1.txt'
        assert copy_path.read_bytes() == candidate.encode('utf-8')
        payloads = [verify(part) for part in source['reading_parts']]
        assembled = ''.join(payloads)
        for label, text in [('original', original), ('candidate', candidate)]:
            marker = re.search('=== BEGIN ' + re.escape(ident) + ' ' + label + r' characters=(\d+) ===\n', assembled)
            assert marker and assembled[marker.end():marker.end()+int(marker.group(1))] == text
        assert candidate.count('그러나 알락산다르는 모레이') == selected.count('그러나 알락산다르는 모레이') == 1
        pins.append(pin(copy_path))

    final_lf_normalized = selected.endswith(chr(10))
    if final_lf_normalized:
        expected = expected.rstrip(chr(10)) + chr(10)
    assert selected == expected, 'unreviewed bytes outside allowed edits: ' + ident
    sidecars = [pin(directory / name) for name in notes]
    for note_pin in sidecars:
        verify(note_pin)
    scope = ('원문/선택 전문·모든 후보차이/EOF·sidecar 전문' if number in {'625422', '56462', '511882', '367209', '58381'}
             else '원문 전량과 선택전문·원문 대비 모든차이/EOF·sidecar 전문' if number == '82044'
             else '주체 명시 문맥·모든 원문 대비차이/EOF·sidecar 전문; 선택본문 일부 출력은 잘렸으므로 전량 판독 주장은 하지 않음' if number == '83431'
             else '원문 모레이 문맥·실제 full_diff 전문·선택의 모든차이/EOF·sidecar/정정리뷰 전문; 원문 전량 주장 없음')
    rows.append(dict(id=ident, role=role, cohort=cohort, original=source['original'], candidate=source['candidate'],
                     selected_body=selected_pin, review=pin(review_path), exact_review_row=entry['raw'],
                     sidecars=sidecars, verification_base=base, allowed_edits=edits,
                     final_LF_normalized=final_lf_normalized,
                     unchanged_bytes_outside_reviewed_edits_verified=True,
                     root_actual_read_scope=scope,
                     decision='KNOWN_FOLLOWUP_SCOPE_SATISFIED_NOT_ROOT_OR_CACHE_ADOPTED'))

previous_files = ['CURRENT_BIRTH_FOLLOWUP_SOURCE_ADJUDICATION_V1.json',
                  'ADDITIONAL_BIRTH_FOLLOWUP_SOURCE_ADJUDICATION_V1.json',
                  'CURRENT_FIELD_AND_BIRTH_FOLLOWUP_ADJUDICATIONS_V1.json']
previous_ids = {row['id'] for name in previous_files for row in read(AUDIT / name)['rows']}
previous_ids.add(read(AUDIT / 'DELIVERY_MISSING_449324_REPAIR_VERIFIED_V1.json')['id'])
assert len(previous_ids) == 13 and not (previous_ids & {row['id'] for row in rows})
result = dict(status='EIGHT_MORE_SOURCE_BOUND_FOLLOWUPS_AND_OUTSIDE_BYTES_VERIFIED', rows=rows,
              previous_explicit_followup_ids=sorted(previous_ids), previous_followups=13,
              new_disjoint_followups=8, combined_specific_followups=21,
              root_read_chunks=['d19bdd', '972a36', 'a62304', '8a6700', '4e622e', '479753', '8f0fe8', 'b15ed6'],
              large_85646_v1_separately_requires_revision=True,
              limits=['These 21 narrow followups are not all authored bodies or a whole-corpus semantic pass.',
                      'Input delivery is not inferred here; its separately frozen guard is required for adoption.',
                      '83431 root viewing was partial; all allowed edits and outside bytes were checked.'],
              input_pins=pins, reused_parser_sha256=parser_sha,
              root_authored_corpus_bodies=0, root_or_cache_adoptions=0,
              protected_body_reads=0, goal_complete=False, training_authorized=False)
target = AUDIT / 'EIGHT_MORE_FOLLOWUPS_BYTE_VERIFIED_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'], cases=8, combined_specific_followups=21,
                     pending_in_this_narrow_scope=0, root_or_cache_adoptions=0), ensure_ascii=False))
