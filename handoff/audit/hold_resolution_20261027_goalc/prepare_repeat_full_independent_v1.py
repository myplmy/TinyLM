"""Reuse the complete-reader exporter for cross-role review of all732 bodies."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE=inv.BASE
group='repeat_named_full_independent_v1'
source_manifest_path=BASE/'repeat_named_roles_counter_v2/manifest.json'
source_manifest=inv.cache.read(source_manifest_path)
snapshot_path=BASE/'repeat_named_roles_counter_v2_snapshots/v3/complete.json'
snapshot=inv.cache.read(snapshot_path)
diagnostic_path=AUDIT/'EXACT_COHORT_BODY_DIAGNOSTICS_V2.json'
diagnostic=inv.cache.read(diagnostic_path)
guards={r['id']:r for r in diagnostic['rows'] if r['cohort']=='repeat_named_roles_counter_v2'}
contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
choices={}
for pin in snapshot['shards']:
    inv.require(inv.file_sha(ROOT/pin['path'])==pin['sha256'],'immutable selection shard changed')
    choices.update({r['id']:r for r in inv.cache.read(ROOT/pin['path'])})
inv.require(len(choices)==len(guards)==732,'every source needs a bound body and diagnostic')
rows=[]
for source in source_manifest['rows']:
    choice=choices[source['id']]
    guard=guards[source['id']]
    inv.require(choice.get('body') and not choice.get('error') and choice['decision'] in {'EDIT_TEXT','ADOPT_CANDIDATE','KEEP_SOURCE'},
                'unclosed source cannot enter independent body review')
    inv.require(source['id'] not in contract['restricted_ids'] and source['original']['sha256'] not in contract['restricted_hashes'],
                'restricted source must remain metadata-only')
    candidate=dict(path=choice['body'],sha256=choice['clean_text_sha256'])
    inv.require(candidate==guard['body'],'diagnostic belongs to another selected body')
    for pin in (source['original'],candidate):
        inv.require(inv.file_sha(ROOT/pin['path'])==pin['sha256'],'exact source/body changed')
    row={k:v for k,v in source.items() if k not in {'proof','native_proof_agrees','guards','candidate_decision','reading_parts','candidate'}}
    row.update(candidate=candidate,previous_editor_role=source['role'],
        previous_editor_review=choice['review'],source_native_original_verified=True,
        candidate_is_authored_body_not_native_v26_reproduction=True,
        named_review_strata=[*source['named_review_strata'],'ALL732_CROSS_ROLE_INDEPENDENT_MEANING_REVIEW'],
        guards=guard['guards'],root_approved=False,cache_admitted=False)
    rows.append(row)
source_path=BASE/'repeat_named_full_independent_source_v1.json'
inv.write_json(source_path,dict(rows=rows,counts=dict(pinned_source_body_pairs_verified=732),
    source_code_pins=source_manifest['source_code_pins'],
    source_manifest=dict(path=str(source_manifest_path.relative_to(ROOT)),sha256=inv.file_sha(source_manifest_path)),
    authored_snapshot=dict(path=str(snapshot_path.relative_to(ROOT)),sha256=inv.file_sha(snapshot_path)),
    body_diagnostic=dict(path=str(diagnostic_path.relative_to(ROOT)),sha256=inv.file_sha(diagnostic_path)),
    root_adopted=0,goal_complete=False,training_authorized=False))

template_path=AUDIT/'prepare_remaining_birth_readers_v1.py'
text=template_path.read_text(encoding='utf-8')
replacements={
 'all2743':'all732', '2743':'732',
 'GROUP = "remaining_birth_full_counter_v1"':'GROUP = "repeat_named_full_independent_v1"',
 'BASE / "remaining_birth_native_proofs_v1/complete.json"':'BASE / "repeat_named_full_independent_source_v1.json"',
 'fresh_regeneration_and_proof_match':'pinned_source_body_pairs_verified',
 'native regeneration must agree':'every source/body pin must agree',
 'native input pair changed':'source or selected authored body changed',
 '"ALL732_NATIVE_SOURCE_CANDIDATE_FULL_READING_REQUIRED_NOT_ADMISSION"':'"ALL732_CROSS_ROLE_COMPLETE_MEANING_REVIEW_REQUIRED_NOT_ADMISSION"',
 '"BIRTH_YEAR_CONFLICT_REQUIRES_INDEPENDENT_SOURCE_READING"':'"FULL_SOURCE_AUTHORED_BODY_REQUIRES_DIFFERENT_ROLE_MEANING_REVIEW"',
 '"# 출생연도 충돌의 전량 원문 판독"':'"# 반복732건 실제 수정본문의 전량 교차 검토"',
 'role = min(roles, key=lambda value:':'role = min([r for r in roles if r != item["row"]["previous_editor_role"]], key=lambda value:'}
for before,after in replacements.items():
    inv.require(before in text,'reader reuse anchor changed: '+before)
    text=text.replace(before,after)
lo=text.index('    start.extend([')
hi=text.index('    save(directory / "START_HERE.md"',lo)
replacement='''    start.extend([
        "이732건은기존편집자와다른역할로배정됐다.자기이전판정이나자동가드만으로ACCEPT하지않는다.",
        "원문전체와실제선택본문전체·전체차이를읽고고유명·수치·단위·날짜·부정·조건·불확실성·인용주체·표축·목록순서·문서경계를비교한다.",
        "정상제목/작품목록/작성자/인용/학술참고자료/코드/전사기호와문맥상필요한반복의오삭제를확인한다.",
        "남아있는페이지UI/고립범례/빈표제/미상주체/누락식/깨진관계와본문독립성도확인한다.표전체나수식주변설명을일괄삭제하지않는다.",
        "실제문맥상필요한반복/값/설명이빠졌으면원문의정확관계로복구한다.새이름·식·날짜·국가·추정관계는만들지않는다.",
        "원문과본문을먼저독립비교한뒤ROOT_READING_PROTOCOL_V1의정확근거문서만추가확인할수있다.기존편집자폴더/리뷰는입력범위가아니다.",
        "공유ROOT_READING_PROTOCOL_V1.md를읽고그안의정확지정ROOT근거MD도읽을수있다.웹방문은금지이며근거부족은NEEDS_ROOT로질문한다.",
        "모든새TXT/MD는set -C(noclobber)로생성한다.기존파일존재시덮지말고새이름을요청한다.부분정정review는수정행만새버전으로적을수있다.",
        "검수메모/보류설명/편집지시를학습본문에넣지않는다.이전원형과빠진구간사유는자기새sidecarMD로보존한다.",
        "입력은공유새그룹의정확경로이며agents/역할을접두어로붙이지않는다.출력은자기새그룹폴더만이다.",
        "대기시간경과는미결경계승인이아니다.총괄중재를기다리는동안독립TASK를계속하고전체배정종료로세지않는다.",
        "이전birthTASK는현재읽는것까지만마감하고이교차검토30TASK를모두처리한뒤미결birthTASK로돌아간다.전체goal진행은계속된다."])
'''
text=text[:lo]+replacement+text[hi:]
manifest_anchor='manifest = dict(status='
index=text.index(manifest_anchor)
protocol='''protocol = ["# 교차 검토의 정확 추가 근거", "",
    "먼저현재TASK원문/후보/전체차이로독립판독한다.그뒤아래공유근거MD만추가열람가능하다.다른역할의기존리뷰/출력폴더접근은금지한다.",
    "V3의명명지역/거리/순서·부분표원형보존원칙을적용한다.수학본문은실제조건/단위를보존하고원문에없는변수/식/표값을채우지않는다."]
for guide in sorted((BASE / "repeat_named_roles_counter_v2").glob("ROOT_*.md")):
    protocol.append(str(ROOT / guide.relative_to(ROOT)))
save(OUT / "ROOT_READING_PROTOCOL_V1.md", chr(10).join(protocol) + chr(10))
'''
text=text[:index]+protocol+text[index:]
target=AUDIT/'prepare_repeat_full_independent_readers_v1.py'
with target.open('x',encoding='utf-8') as stream:stream.write(text)
print(json.dumps(dict(source_pairs=732,producer=str(target.relative_to(ROOT)),
    source_manifest_sha256=inv.file_sha(source_path),independence='greedy balance excludes each original editor'),ensure_ascii=False))
