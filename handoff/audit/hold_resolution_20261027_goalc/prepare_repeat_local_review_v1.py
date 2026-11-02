"""Prepare all40 native-verified pairs for independent complete source reading."""
from collections import Counter
from pathlib import Path
import difflib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE = inv.BASE
GROUP = "repeat_local_context_counter_v1"
OUT = BASE / GROUP
source_path = BASE / "repeat_local_native_proofs_v1/complete.json"
source = inv.cache.read(source_path)
inv.require(not OUT.exists() and len(source["rows"]) == 40, "exact new all40 reading namespace required")
inv.require(source["counts"]["fresh_regeneration_and_proof_match"] == 40, "native regeneration must agree")
roles = ["context_controls", "context_hangul", "historical_review"]
assignments, sizes = {role: [] for role in roles}, Counter()
prepared = []
for row in source["rows"]:
    values = {}
    for label in ["original", "candidate"]:
        pin = row[label]
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "native input pair changed")
        values[label] = (ROOT / pin["path"]).read_text(encoding="utf-8")
    prepared.append(dict(row=row, values=values, cost=sum(map(len, values.values()))))
for item in sorted(prepared, key=lambda value: (-value["cost"], value["row"]["id"])):
    role = min(roles, key=lambda value: (sizes[value], len(assignments[value]), value))
    item["role"] = role
    assignments[role].append(item["row"]["id"])
    sizes[role] += item["cost"]
(OUT / "inputs").mkdir(parents=True)
(OUT / "reading_packets_v1").mkdir()


def save(path, value):
    payload = value.encode("utf-8")
    inv.require(0 < len(payload) < 20_000_000, "new artifact must be split")
    with path.open("xb") as stream:
        stream.write(payload)
    return dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path))


rows, by_id = [], {}
for item in prepared:
    row = dict(item["row"])
    ident, stem = row["id"], row["id"].replace(":", "_")
    for label, text in item["values"].items():
        row[label] = save(OUT / "inputs" / (stem + "_" + label + ".txt"), text)
    delta = "".join(difflib.unified_diff(item["values"]["original"].splitlines(keepends=True),
        item["values"]["candidate"].splitlines(keepends=True), fromfile="original", tofile="candidate"))
    sections = [*item["values"].items(), ("full_diff", delta or "비교한 전문의 줄 차이 없음")]
    framed = ""
    for kind, text in sections:
        framed += "=== BEGIN " + ident + " " + kind + " characters=" + str(len(text)) + " ===" + chr(10)
        framed += text + chr(10) + "=== END " + ident + " " + kind + " ===" + chr(10)
    parts, reconstructed = [], ""
    for offset in range(0, len(framed), 6000):
        fragment = framed[offset:offset + 6000]
        parts.append(dict(**save(OUT / "reading_packets_v1" / (stem + "_" + str(offset // 6000 + 1).zfill(4) + ".txt"), fragment),
                          characters=[offset, offset + len(fragment)]))
        reconstructed += fragment
    inv.require(reconstructed == framed, "ordered views must reconstruct every full section")
    row.update(role=item["role"], reading_parts=parts,
        candidate_reasons=["REPEATED_LINE_CONTEXT_REQUIRES_INDEPENDENT_SOURCE_READING", *row["remaining_reasons"]])
    rows.append(row)
    by_id[ident] = row
for role, ids in assignments.items():
    ids.sort()
    directory = BASE / "agents" / role / GROUP
    directory.mkdir(parents=True, exist_ok=False)
    start = ["# 반복 문맥의 독립 원문 판독", "",
        "입력은 이 START/TASK/READING_VIEWS 및 거기에 정확 지정한 새 그룹의 TXT/순서 패킷뿐이다.",
        "쓰기는 이 새 자기 폴더의 새 txt/md뿐이다. 기존 파일을 덮거나 삭제하지 않는다.",
        "코드·시험·통계·해시 계산·Python·Git·웹·모델·GPU·다른 역할·타 세션·보호자료 접근은 금지한다.",
        "모든 지정 원문·후보·전체 diff와 실제 EOF를 읽는다. 패킷은6000문자의 연속 조각이며 개별파일끝이 문장중간이어도 정상이다.",
        "한 ID의 모든 조각을 순서대로 읽어 마지막논리END를 확인한다. 도구출력잘림을 정상분할과 구별하고 부분출력을 전문판독으로 세지 않는다.",
        "반복 줄이 필요 없는 추출 중복인지, 서로 다른 실제 제목·작성자·문단의 정보인지 원문 전체로 판단한다.",
        "정상 반복은 지우지 않고 관계와 순서를 보존한다. 누락식/표·코드·인용·숫자·부정·조건·출처를 보호한다.",
        "현재후보가적절하면ACCEPT_CANDIDATE와정확candidate경로. 보류MD만추가할때도같은판정이며동일TXT를복제하지않는다.",
        "실제수정이필요하면새전체TXT와원형holdMD를쓰고REVISE_TEXT와정확자기TXT경로를표시한다.",
        "판단할수없는좁은경계는NEEDS_ROOT질문을보내되다른독립TASK를계속한다. 없는이름·값·수식은생성하지않는다.",
        "각TASK마다review_NNN.md를ID/판정/실제판독범위/정확출력/구체근거의5열표로저장한다. 한국어검수설명과원문언어를구분한다.",
        "해시문자열이입력에이미있으면메타데이터로읽을수있지만직접해시계산·검사는하지않는다. 코드실행/캐시채택/전체품질완료선언은금지한다.",
        "이40건은자동탐지의후보이며판독의결론이아니다. 다른결손이있으면그상태를무시하지말고남은본문독립성을검토한다."]
    save(directory / "START_HERE.md", chr(10).join(start) + chr(10))
    view_lines = ["# 지정 원문 전체 순서 목록"]
    for task, offset in enumerate(range(0, len(ids), 5), 1):
        lines = ["# TASK_" + str(task).zfill(3), "START_HERE와 지정 전문 입력을 따른다."]
        for ident in ids[offset:offset + 5]:
            row = by_id[ident]
            lines.extend(["## " + ident, "original: " + str(ROOT / row["original"]["path"]),
                          "candidate: " + str(ROOT / row["candidate"]["path"]), "전문 연속 패킷:"])
            lines.extend("- " + str(ROOT / pin["path"]) for pin in row["reading_parts"])
            view_lines.extend(["## " + ident, *["- " + str(ROOT / pin["path"]) for pin in row["reading_parts"]]])
        save(directory / ("TASK_" + str(task).zfill(3) + ".md"), chr(10).join(lines) + chr(10))
    save(directory / "READING_VIEWS.md", chr(10).join(view_lines) + chr(10))
manifest = dict(status="ALL40_NATIVE_SOURCE_CANDIDATE_FULL_READING_REQUIRED_NOT_ADMISSION", rows=rows,
    assignments=assignments, source_characters_by_role=dict(sizes),
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [source_path, Path(__file__)]},
    source_code_pins=source["source_code_pins"], cache_admitted=0, goal_complete=False, training_authorized=False)
inv.write_json(OUT / "manifest.json", manifest)
print(json.dumps(dict(sources=40, assignments={role: len(ids) for role,ids in assignments.items()},
    characters=dict(sizes), packet_parts=sum(len(row["reading_parts"]) for row in rows))))
