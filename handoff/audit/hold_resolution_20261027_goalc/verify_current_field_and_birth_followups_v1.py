"""Check four root-read author outputs against explicit bounded source edits."""
from pathlib import Path
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'

reused = AUDIT / 'verify_current_birth_followups_v1.py'
tree = ast.parse(reused.read_text(encoding='utf-8'))
names = {'sha', 'read', 'pin', 'verify', 'replace_once'}
definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
assert len(definitions) == len(names) and all(not n.decorator_list for n in definitions)
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(reused), 'exec'), globals())
NL = chr(10)
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract = read(contract_path)
birth_manifest_path = BASE / 'birth_root11_independent_v1/manifest.json'
field_manifest_path = BASE / 'remaining_field_title_page_004_counter_v1/manifest.json'
birth_snapshot_path = BASE / 'birth_root11_independent_v1_snapshots/v20/complete.json'
field_snapshot_path = BASE / 'remaining_field_title_page_004_counter_v1_snapshots/v10/complete.json'
sources = {}
records = {}
for manifest_path, snapshot_path in ((birth_manifest_path, birth_snapshot_path),
                                     (field_manifest_path, field_snapshot_path)):
    manifest, snapshot = read(manifest_path), read(snapshot_path)
    assert not snapshot['errors']
    sources.update({row['id']: row for row in manifest['rows']})
    for shard in snapshot['shards']:
        data = (ROOT / shard['path']).read_bytes()
        assert sha(data) == shard['sha256']
        records.update({row['id']: row for row in json.loads(data)})

changes = {
    'expanded_train:35700': [
        ('1870년 ~ 1938년 10월 10일', '1870년 출생, 10월 10일 사망'),
        ('1938년 10월 일제가', '10월 일제가'),
        ('독살당하였다..', '독살당하였다.'),
        ('1938년 사망' + NL, '')],
    'expanded_train:292732': [
        ('덴쇼 13년 음력 11월 17일(1586년 1월 6일)', '음력 11월 17일'),
        ('1585년, 히토토리바시 전투에서는', '히토토리바시 전투에서는'),
        ('1586년 사망' + NL, '')],
    'expanded_train:47644': [
        ('3 태양질량()까지이다.', '3 태양질량까지이다.'),
        (' 관측된 것 중 가장 무거운 것은 2.01 이다.', ''),
        ('일반적으로 1.39 (찬드라세카르 한계)보다 작은 밀집성은 백색왜성이다. 그와 3 (톨만-오펜하이머-볼코프 한계) 사이에 있는 밀집성은 중성자별이 된다. 관측된 것 중 가장 무거운 중성자별의 질량은 약 2 이다. 10 보다 더 무거운 밀집성은 중성자 축퇴압이 밀집성을 지지하지 못하게 되어 밀집성은 보통 중력붕괴로 블랙홀을 형성하게 된다. 관측된 것 중 가장 작은 블랙홀의 질량은 약 5 이다. 두 밀집성 사이에는 ', ''),
        ('가설상의 중간질량 천체가', '가설상의 천체가'),
        ('정확히 알려져 있지 않다. ' + NL, '정확히 알려져 있지 않다.' + NL),
        ('초기 질량이 약 8  이상인 모든 주계열성은 중성자별이 될 가능성이 있다. ', ''),
        (' 만약 중성자별의 질량이 5 보다 더 크다면, 별은 더욱 붕괴하여 블랙홀이 된다.', ''),
        ('중성자별의 반지름이 이거나 그보다 작다면, 광자는 궤도를 돌게 될 수 있다. 그래서 중성자별의 표면 전체가 보이게 된다. ', ''),
        (' BE를 관측된 중성자별의 중력질량 M(kg), 반지름 R(m)의 비와 동일한 중력 속박 에너지 질량비라고 하면,', ''),
        (NL + '현재 주어진 값', ''),
        ('그러면 중성자별에 관한 상대론적 비(比) 속박에너지는' + NL*2 + '2 인 중성자별은 반지름이 10,970 미터(AP4)보다 더 작아지지 않는다. 그러면 별의 질량비 중력 속박 에너지는 0.187, -18.7%(발열)가 된다. 이는 0.6/2 = 0.3, -30%에 가깝지 아니하다.', ''),
        (' 예를 들면, 1.5 인 중성자별은 반지름이 10.7, 11.1, 12.1, 15.1 km(각각 EOS FPS, UU, APR, L 모형)이다.', ''),
        (' 측정된 질량은 1.97±0.004 이다. 이는 이전에 측정된 중성자별의 질량(1.67 , PSR J1903+0327 참고)보다 상당히 크며, 중성자별의 내부 조성에 관한 강한 제한요인으로 자리잡는다.', ''),
        ('2013년, 존 안토니아디스와 그의 동료들은 백색왜성 분광을 이용하여 PSR J0348+0432의 질량을 2.01±0.04 으로 측정하였다. 이는 그러한 무거운 별의 존재를 다른 방법을 이용하여 검증되었다. 나아가서, 이는 최초로 무거운 중성자별을 이용하여 일반상대성이론을 검증하게 만든 사례이다.',
         '2013년, 존 안토니아디스와 그의 동료들은 백색왜성 분광을 이용하여 PSR J0348+0432의 질량을 측정하였다.'),
        ('PSR J0348+0432 - 2.01±0.04 으로, 발견된 것 중 가장 무거운 중성자별', 'PSR J0348+0432'),
        (NL + '갤러리', '')],
    'expanded_train:48362': [
        ('Next step will consist in assessing a 0.05 probability of tsetse absence to ascertain a provisional eradication status. ', ''),
        (' (see details in )', ','),
        ('. From upper left to lower right are shown epicutaneous treatment using insecticide (pour on) on pigs, deltamethrin impregnated fences around pig pens, a deltamethrin impregnated black/blue/black target in a palm tree plantation, and cyfluthrin groundspraying using a Swinfog SN50.',
         ': epicutaneous treatment using insecticide (pour on) on pigs; deltamethrin impregnated fences around pig pens; a deltamethrin impregnated black/blue/black target in a palm tree plantation; and cyfluthrin groundspraying using a Swinfog SN50.'),
        (', and Figure 2', ''),
        ('Figure 2. Combination and GPS location of control techniques applied on Loos islands. This map shows exact GPS locations of places where the different control techniques (see legend) were implemented on each of the three islands, together with the location of monitoring traps.' + NL, ''),
        ('as described by , ', ''),
        (' (, or see also )', ''),
        (' In this model, the probability of observing a sequence of zero catches if in fact there are insects in the sampled area is given by:', ''),
        ('where S is the number of traps deployed in the total area, t the number of days for which each trap is operated, σ the trap efficiency and λ the population density (number of insects/area of suitable habitat). ',
         'S is the number of traps deployed in the total area; t is the number of days for which each trap is operated; σ is the trap efficiency; λ is the population density (number of insects/area of suitable habitat).' + NL),
        (', according to estimates obtained for G. palpalis gambiensis by ', ''),
        (' - i.e. when the probability of tsetse presence will be below 0.05 after which control operations will stop', ''),
        ('Format: DOC Size: 116KB Download file' + NL, ''),
        ('Format: DOC Size: 103KB Download file' + NL, '')]
}
sidecar_names = {
    'expanded_train:35700': 'hold_35700_v1.md',
    'expanded_train:292732': 'hold_292732_task124_v2.md',
    'expanded_train:47644': 'hold_47644_task018_v4.md',
    'expanded_train:48362': 'hold_48362_missing_formula_targets_and_thresholds_20261104_v3.md'
}
expected_outputs = {
    'expanded_train:35700': 'expanded_train_35700_reviewed_v2.txt',
    'expanded_train:292732': 'reviewed_292732_task124_v2.txt',
    'expanded_train:47644': 'expanded_train_47644_revised_task018_v3.txt',
    'expanded_train:48362': 'expanded_train_48362_historical_review_20261104_v3.txt'
}
read_scopes = {
    'expanded_train:35700': ('원문 전문; 선택v1 전문; v1→v2의 구두점 한 곳; sidecar 전문', ['4c55fe', 'd7f11a']),
    'expanded_train:292732': ('원문/후보/선택 전문; 전체 diff; sidecar 전문', ['202fec', 'df8524', '22201e']),
    'expanded_train:47644': ('원문 전문; 후보→선택v2 전체18변경 및 문맥/EOF; v2→v3 전체변경/EOF; 최종sidecar 전문', ['29ed5f', '77e227', 'd7c211', 'e01b67', '288e4d']),
    'expanded_train:48362': ('원문 첫9500자 및 모델·임계/그림 문맥; 후보→v2 전체23변경/문맥; v2→v3 전체변경/EOF; 최종sidecar 전문. 원문 참고문헌 꼬리의 전량 재판독 주장은 하지 않음', ['e9d5c2', '33444a', 'dd55da', 'd472e6', 'ad9018', '898a0b'])
}
results = []
for ident, replacements in changes.items():
    source, row = sources[ident], records[ident]
    assert ident not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    original, candidate = verify(source['original']), verify(source['candidate'])
    assert row['decision'] == 'EDIT_TEXT' and row['status'] == 'MATERIALIZED_BODY_NOT_ROOT_ADMISSION'
    assert Path(row['author_output']['path']).name == expected_outputs[ident]
    selected_pin = dict(path=row['body'], sha256=row['clean_text_sha256'])
    selected = verify(selected_pin)
    expected = candidate
    for old, new in replacements:
        expected = replace_once(expected, old, new)
    repeated_edits = []
    if ident == 'expanded_train:48362':
        for old, count in [(' (see Figure 2)', 2),
                           ('This file can be viewed with: Microsoft Word Viewer' + NL, 2)]:
            assert expected.count(old) == count
            expected = expected.replace(old, '')
            repeated_edits.append(dict(old=old, replacement='', exact_occurrences=count))
    if ident in {'expanded_train:35700', 'expanded_train:48362'}:
        expected = expected.rstrip(NL) + NL
        eof_rule = 'exactly one final LF'
    elif ident == 'expanded_train:292732':
        expected = expected.rstrip(NL)
        eof_rule = 'no final LF, matching the actual selected output'
    else:
        eof_rule = 'unchanged candidate EOF'
    assert expected == selected, 'bytes changed outside the bounded root-reviewed source edits: ' + ident
    directory = ROOT / Path(row['author_output']['path']).parent
    sidecar_pin = pin(directory / sidecar_names[ident])
    verify(sidecar_pin)
    review_data = (ROOT / row['review']['archive']).read_bytes()
    assert sha(review_data) == row['review']['sha256']
    actual_scope, chunks = read_scopes[ident]
    results.append(dict(id=ident, original=source['original'], candidate=source['candidate'],
                        author_output=row['author_output'], selected_body=selected_pin,
                        review=row['review'], sidecar=sidecar_pin,
                        allowed_exact_replacements=[dict(old=old, new=new) for old, new in replacements],
                        repeated_exact_edits=repeated_edits, eof_rule=eof_rule,
                        unchanged_bytes_outside_allowed_edits_verified=True,
                        root_actual_read_scope=actual_scope, root_read_chunks=chunks,
                        decision='KNOWN_FOLLOWUP_SCOPE_SATISFIED_NOT_ROOT_OR_CACHE_ADOPTED'))
paths = [reused, contract_path, birth_manifest_path, field_manifest_path,
         birth_snapshot_path, field_snapshot_path, Path(__file__).resolve()]
result = dict(status='FOUR_NEW_ROOT_READ_AUTHOR_FOLLOWUPS_AND_BOUNDED_BYTES_VERIFIED', rows=results,
              known_followups_in_this_scope=4, pending_known_in_this_scope=0,
              prior_three_scope_record='CURRENT_BIRTH_FOLLOWUP_SOURCE_ADJUDICATION_V1.json',
              prior_five_scope_record='ADDITIONAL_BIRTH_FOLLOWUP_SOURCE_ADJUDICATION_V1.json',
              these_ids_disjoint_from_prior_eight=True,
              root_authored_training_bodies=0, root_or_cache_adoptions=0,
              protected_body_reads=0, whole_semantic_review_complete=False, goal_complete=False,
              input_pins={entry['path']: entry['sha256'] for entry in map(pin, paths)})
target = AUDIT / 'CURRENT_FIELD_AND_BIRTH_FOLLOWUP_ADJUDICATIONS_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(NL)
print(json.dumps(dict(status=result['status'], known_followups=4, pending_in_this_scope=0,
                     root_or_cache_adoptions=0), ensure_ascii=False))
