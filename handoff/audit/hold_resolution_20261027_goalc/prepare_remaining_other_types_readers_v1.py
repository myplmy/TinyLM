"""Reuse the existing full-pair reader producer over all bounded field pages."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE = inv.BASE
source_path = BASE / 'remaining_other_types_native_proofs_v1/complete.json'
source = inv.cache.read(source_path)
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract = inv.cache.read(contract_path)
blocked_ids = set(contract['restricted_ids'])
blocked_hashes = set(contract['restricted_hashes'])
template_path = AUDIT / 'prepare_remaining_birth_readers_v1.py'
template = template_path.read_text(encoding='utf-8')
assert source['counts']['fresh_native_sources'] == 50162
assert source['counts']['fresh_regeneration_and_proof_match'] == 50162
assert len(source['pages']) == 98
output_path = BASE / 'remaining_other_types_readers_v1/complete.json'
assert not output_path.exists()
seen, pages = set(), []

extra = '''    start.extend([
        "다른 잔여 유형 전량의 일부 페이지다. 이 페이지나 TASK의 끝이 전체 정제 끝은 아니다.",
        "이름 없는 필드·셀·목록 항목의 주체와 관계를 원문 전체에서 확인한다. 빠진 제목·사람·값을 순서나 상식만으로 채우지 않는다.",
        "작품·선수·기록·참고문헌·코드·인용·교육과정의 실제 제목과 채워진 내용은 보존한다. 제목처럼 보인다는 이유로 지우지 않는다.",
        "빈 표제/탐색/광고 UI는 실제 역할을 확인해 원형 sidecar와 함께 분리하고 유효 본문 관계를 보존한다.",
        "없어진 그림·식·코드에 직접 의존하는 설명만 보류한다. 문장 자체에 대상·조건·값이 완결된 내용은 그림 부재만으로 버리지 않는다.",
        "숫자·날짜·단위·부정·조건·인용 주체·불확실성은 보존한다. 어느 이름이나 값도 원문에 없는 채로 만들지 않는다.",
        "후보와 원문 동일성은 내용 수용 근거가 아니다. 별도 검산 계획이 있으면 원문 전문 실제 판독과 최종diff를 확인하고 중복 후보만 생략한다.",
        "동일 입력 계획에서 생략한 candidate 중간 패킷의 앞뒤를 이어 새 후보로 해석하지 않는다. 원문 전문의 실제 END와 diff END는 각각 확인한다.",
        "controls는 별도 ROOT 고정 reader 허가 전에는 실제 원문을 읽지 않는다. 다른 역할은 자기 정확 지정 입력만 읽는다.",
        "같은 ID의 source/body/sidecar/review를 마감한 뒤 다음 ID를 편집한다. 새 TXT 전체와 전체diff를 읽고 출력이 실제 달라진 때만 REVISE로 기록한다.",
        "TASK 번호와 다섯 source ID를 정확히 맞춘다. 질문은 좁은 원문 문구로 보내고 다른 독립 TASK를 계속한다."])
'''

for page in source['pages']:
    native_path = ROOT / page['path']
    assert inv.file_sha(native_path) == page['sha256']
    native = inv.cache.read(native_path)
    ids = {row['id'] for row in native['rows']}
    assert len(ids) == page['sources'] and not (ids & seen)
    assert not (ids & blocked_ids)
    assert not ({row['original']['sha256'] for row in native['rows']} & blocked_hashes)
    seen.update(ids)
    group = 'remaining_other_types_page_' + str(page['page']).zfill(3) + '_counter_v1'
    text = template
    begin = text.index('    start.extend([')
    end = text.index('    save(directory / "START_HERE.md"', begin)
    text = text[:begin] + extra + text[end:]
    replacements = [
        ('remaining_birth_full_counter_v1', group),
        ('remaining_birth_native_proofs_v1/complete.json', str(native_path.relative_to(BASE))),
        ('len(source["rows"]) == 2743', 'len(source["rows"]) == ' + str(page['sources'])),
        ('source["counts"]["fresh_regeneration_and_proof_match"] == 2743',
         'source["counts"]["fresh_regeneration_and_proof_match"] == len(source["rows"])'),
        ('sources=2743', 'sources=len(source["rows"])'),
        ('6000', '2000'),
        ('출생연도 충돌의 전량 원문 판독', '다른 잔여 유형의 전량 문맥 판독'),
        ('BIRTH_YEAR_CONFLICT_REQUIRES_INDEPENDENT_SOURCE_READING',
         'OTHER_TYPES_REQUIRE_INDEPENDENT_SOURCE_READING'),
        ('ALL2743_NATIVE_SOURCE_CANDIDATE_FULL_READING_REQUIRED_NOT_ADMISSION',
         'EXACT_OTHER_TYPE_PAGE_FULL_READING_REQUIRED_NOT_ADMISSION'),
        ('이2743건은지정유형전량의판독후보이며판독의결론이아니다.',
         '이 페이지는 유형 전량의 일부이며 판독 준비를 판독 결과로 세지 않는다.'),
        ('row[label] = save(OUT / "inputs" / (stem + "_" + label + ".txt"), text)',
         'row[label] = item["row"][label]'),
        ('[source_path, Path(__file__)]', '[source_path, Path(__file__), template_path]'),
        ('inv.write_json(OUT / "manifest.json", manifest)',
         'save(OUT / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + chr(10))'),
    ]
    for before, after in replacements:
        assert before in text, before
        text = text.replace(before, after)
    text = text.replace('all2743', 'exact field page')
    assert '2743' not in text and 'BIRTH_YEAR' not in text
    scope = dict(__file__=str(Path(__file__)), __name__='field_reader_adapter', template_path=template_path)
    exec(compile(text, str(Path(__file__)) + ':' + group, 'exec'), scope)
    manifest_path = BASE / group / 'manifest.json'
    manifest = inv.cache.read(manifest_path)
    assert {row['id'] for row in manifest['rows']} == ids
    assert manifest_path.stat().st_size < 20_000_000
    pages.append(dict(page=page['page'], group=group, sources=len(ids),
        path=str(manifest_path.relative_to(ROOT)), sha256=inv.file_sha(manifest_path),
        assignments={role: len(assigned) for role, assigned in manifest['assignments'].items()}))
assert len(seen) == 50162 and sum(page['sources'] for page in pages) == 50162
output_path.parent.mkdir(exist_ok=False)
inv.write_json(output_path, dict(status='ALL_OTHER_TYPE_PAGES_PREPARED_NOT_CONTENT_REVIEWED',
    sources=len(seen), occurrences=77879, pages=pages,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path)
        for path in [source_path, contract_path, template_path, Path(__file__)]},
    cleaned_texts_authored_by_root=0, protected_parent_bodies_opened=0,
    goal_complete=False, training_authorized=False))
print(json.dumps(dict(all_other_type_sources=len(seen), pages=len(pages), cache_admitted=0)))
