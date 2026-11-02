"""Reuse full-pair reader assignment framing for all 23 actual runtime flags."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT/'prepare_post_semantic_independent_v1.py').read_text(encoding='utf-8')
source = source.replace("'post_semantic_independent_v1'", "'runtime_guard_counter_v1'")
source = source.replace("roles = ['context_controls', 'context_hangul']",
                        "roles = ['context_latin', 'historical_review', 'legacy_review']")
before = '''selected = sorted([r for r in snapshot['records'] if r['cohort'] in
                  {'post_body_guard_counter_v1', 'semantic_field_counter_v1'}],
                 key=lambda r: (r['role'] not in roles, r['id']))
inv.require(len(selected) == 26, 'all26 exact new reviews required')'''
after = '''preview_path = AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW4.json'
guard_path = AUDIT/'EXACT_SELECTION_RUNTIME_GUARDS_V1.json'
preview = inv.cache.read(preview_path)
guard = inv.cache.read(guard_path)
choices = {row['id']:row for row in preview['rows']}
selected = []
notes = out/'decision_notes'
notes.mkdir()
for flag in guard['records']:
    if flag.get('runtime_code_and_unicode_pass') is not False and flag.get('semantic_style_pass') is not False:
        continue
    previous = choices[flag['id']]
    choice = previous['selected']
    note_path = notes/(flag['id'].replace(':','_')+'.md')
    rationale = choice.get('reason','')
    text = '# 정확 본문 선택과 가드 경고' + chr(10)*2 + rationale + chr(10)*2
    text += '실제 캐시 코드 가드: ' + str(flag['runtime_code_and_unicode_pass']) + chr(10)
    text += '자동 서식 보존 검사: ' + str(flag['semantic_style_pass']) + chr(10)
    text += '경고는 오삭제 확정이 아니다. 실제 프로그램·인용·스타일 의미와 추출 잔재를 원문별로 구별한다.' + chr(10)
    text += '새 사실/코드/값은 생성하지 않는다. 누락 전제에 직접 매인 손상 부분은 원형 보류한다.' + chr(10)
    with note_path.open('x',encoding='utf-8') as stream:
        stream.write(text)
    selected.append(dict(id=flag['id'],role=choice.get('role','root'),
        original=dict(path=flag['original_comparison_source'],sha256=flag['original_text_sha256']),
        body=flag['body'],clean_text_sha256=flag['clean_text_sha256'],
        review=dict(path=str(note_path.relative_to(ROOT)),sha256=inv.file_sha(note_path)),
        review_text=text,status='MATERIALIZED_BODY_NOT_ROOT_ADMISSION'))
selected.sort(key=lambda row:row['id'])
inv.require(len(selected)==23,'all runtime9 and style14 exact flags required')'''
assert source.count(before) == 1
source = source.replace(before,after,1)
source = source.replace('counts[role] < 13','counts[role] < 8')
source = source.replace("input_pins={str(snapshot_path.relative_to(ROOT)):inv.file_sha(snapshot_path)},",
                        "input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in [snapshot_path,preview_path,guard_path]},")
source = source.replace('Issue all 26 exact original/final pairs to different-role independent readers.',
                        'Issue all23 runtime and style flagged source/body pairs for explicit review.')
with (AUDIT/'materialize_runtime_guard_counter_v1.py').open('x',encoding='utf-8') as stream:
    stream.write(source)
print('ALL23_RUNTIME_FLAG_FULL_CONTEXT_ASSIGNMENTS_PREPARED')
