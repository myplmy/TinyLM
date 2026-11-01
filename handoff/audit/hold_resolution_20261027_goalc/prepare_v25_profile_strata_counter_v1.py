"""Reuse the exact-source exporter for all new full-census representative strata."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'prepare_v23_structural_counter_v1.py').read_text(encoding='utf-8')
changes = [
 ('from scripts import p106b_hold_resolution_policy_v23 as policy',
  'from scripts import p106b_hold_resolution_policy_v25 as policy'),
 ('from scripts import p106b_hold_resolution_revision_v23 as revision',
  'from scripts import p106b_hold_resolution_revision_v25 as revision'),
 ('structural_candidate_profile_v22_v1', 'remaining_unreviewed_candidate_profile_v25_v1'),
 ('policy_v23_structural_counter_v1', 'profile_strata_source_counter_v25_v1'),
 ('inv.verify(PROFILE / "matches", profile["matches_manifest"])\nselected = list(inv.cache.rows(PROFILE / "matches", profile["matches_manifest"]))\ninv.require(len(selected) == 33 and len({r["original_text_sha256"] for r in selected}) == 33, "whole-census matches differ")',
  '''packet_path = PROFILE / "review_packets/manifest.json"
packet_manifest = inv.cache.read(packet_path)
ordinal_path = BASE / "ordinal_metadata_counter_v26_v1/manifest.json"
ordinal = inv.cache.read(ordinal_path)
ordinal_ids = {row["id"] for row in ordinal["rows"]}
selected = [row for row in packet_manifest["rows"] if row["id"] not in ordinal_ids]
inv.require(len(packet_manifest["rows"]) == 238 and len(selected) == 237
            and len({r["original_text_sha256"] for r in selected}) == 237,
            "whole-profile representative membership differs")'''),
 ('roles = ["context_controls", "context_hangul", "context_latin"]',
  'roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "structure_counter"]'),
 ('        clean = value.get("candidate", value["text"])',
  '''        clean = value.get("candidate", value["text"])
        inv.require(inv.file_sha(ROOT / source["candidate"]["path"]) == source["candidate"]["sha256"]
                    and value["decision"] == "PENDING"
                    and inv.sha(clean) == source["candidate"]["sha256"],
                    "fresh exact original failed to reproduce the v25 diagnostic")'''),
 ('                         candidate_reasons=value["reasons"], root_approved=False))',
  '''                         candidate_reasons=value["reasons"], raw_original_not_redecoded=False,
                         fresh_exact_original_readback=True, original_native_v25_proposal_reproduced=True,
                         root_approved=False))'''),
 ('"전체 계수 유형: " + ", ".join(row["proof_kinds"])',
  '"전량 유형분석에서 이 원문이 대표하는 층: " + ", ".join(row["profile_kinds"])'),
 ('ALL_33_STRUCTURE_CENSUS_MATCHES_HAVE_EXACT_SOURCE_PAIRS_NOT_ADMISSION',
  'ALL_237_NEW_FULL_CENSUS_STRATA_HAVE_EXACT_SOURCE_PAIRS_NOT_ADMISSION'),
 ('이 33쌍은 전체 v21 미결의 구조 후보 전수계수 결과 전부다.',
  '이237쌍은 전체v25미결에서 새 유형별로 고른 원문이며 같은ordinal27의중복1개는제외했다.'),
 ('prepare_v23_structural_views_v1.py', 'prepare_v25_profile_strata_views_v1.py'),
 ('    input_pins={str(profile_path.relative_to(ROOT)): inv.file_sha(profile_path),',
  '''    input_pins={str(profile_path.relative_to(ROOT)): inv.file_sha(profile_path),
        str(packet_path.relative_to(ROOT)): inv.file_sha(packet_path),
        str(ordinal_path.relative_to(ROOT)): inv.file_sha(ordinal_path),''')
]
for before, after in changes:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
anchor = '    for number, row in enumerate(owned, 1):'
assert source.count(anchor) == 1
source = source.replace(anchor, '''    instructions += [
        "기존579및ordinal27의배정과정정부터마친뒤이새묶음을진행한다.",
        "대표237건이전체해소나작업량상한은아니다. 반복·빈값·분류각위험의실제문맥을판독한다.",
        "같은줄반복을일괄삭제하지않고, 유효한연도별/항목별/인용별반복과실제추출중복을구분한다.",
        "영어/한국어등원문언어와원래학술용어·이름·조건을유지하고번역이나동의어개작을하지않는다.",
        "새본문을전문작성한뒤raw마지막행과candidate전체diff를확인한다. wc-l과논리EOF를혼동하지않는다.",
        "임의로통계/코드/해시를실행하지않는다. 새txt/md편집과nl/sed/diff/tail의좁은읽기만허용한다."]
''' + anchor)
destination = AUDIT / 'materialize_v25_profile_strata_counter_v1.py'
compile(source, str(destination), 'exec')
with destination.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared exact237 source-pair exporter; no new policy or admission.')
