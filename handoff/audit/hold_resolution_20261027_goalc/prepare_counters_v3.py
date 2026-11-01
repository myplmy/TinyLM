"""Pin additional saved text inputs for the existing independent readers."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
assignments = json.loads((AUDIT / "profile_assignments_v1.json").read_text())
ready = {"context_controls": "context_latin", "historical_review": "context_controls",
         "context_latin": "historical_review", "legacy_review": "context_hangul"}
auto = json.loads((BASE / "draft_proposals_v3/review_packets/manifest.json").read_text())["rows"]
auto = [r for r in auto if r["decision"] in ["KEEP", "EDIT"]]
roles = list(ready)
loads = {role: 0 for role in roles}
auto_assigned = {role: [] for role in roles}
for row in sorted(auto, key=lambda r: -r["characters"]):
    role = min(roles, key=lambda r: (loads[r], r))
    loads[role] += row["characters"]
    auto_assigned[role].append(row)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def ver(path):
    match = re.search(r"_v([0-9]+)[.]", path.name)
    return int(match[1]) if match else 1


result = {}
for role, author in ready.items():
    directory = BASE / "agents" / role / "counter_profile_v1"
    directory.mkdir()
    other = BASE / "agents" / author / "profile_resolution_v1"
    reviews = sorted(other.glob("review*.md"), key=ver)
    decisions = {}
    for p in reviews:
        for line in p.read_text().splitlines():
            if line.startswith("|"):
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if cells and re.fullmatch(r"(?:expanded_train:)?[0-9]+", cells[0]):
                    ident = cells[0] if ":" in cells[0] else "expanded_train:" + cells[0]
                    decisions[ident] = cells[1]
    expected = {r["id"] for r in assignments[author]["rows"]}
    assert set(decisions) == expected, (author, expected-set(decisions))
    lines = ["# 추가 원문 정제본과 전량 v3 후보의 독립 대조", "",
             "역할은 정확 지정 원문/실제 저장물의 독립 텍스트 대조다. 원문/작성자 파일 수정 금지. 코드·시험·전처리·코퍼스 통계·해시 계산·모델·GPU·Git·웹·설치·삭제·목록 밖 접근 금지. 이 디렉터리 새 counter.md만 작성한다.", "",
             "동일 줄번호만 비교하지 않고 실제 문구와 원문 순서를 확인한다. 손실/추가 주장은 원문과 저장물에서 실제로 직접 재확인하고 근거 구절을 기록한다. 원문에 없는 값/정의 생성, 유효 조건·부정·주체·인용·불확실성 손실, 분리한 구간을 지시하는 고아 참조와 잔여 UI/빈 표제를 검토한다. URL이 추출되지 않았어도 실제 공식자료/사람/플랫폼 명칭은 유효 정보일 수 있다. 단순 탐지 일치나 문구 부재만으로 판단하지 않는다.", "",
             "counter.md는 ID | PASS/REVISE/NEEDS_ROOT | 실제 원문·본문 판독 범위 | 정확 보존·손실·잔존 근거를 기록한다. 앞 유형 정제본과 뒤 자동 v3 후보는 별도 행으로 구별한다. 전량 사실/모델 품질/최종 채택 PASS라고 표현하지 않는다.", "",
             "특수 읽기 경계:237405는 원문의 제목/학술지/첫 초록 단락과 정제본만 대조하고 상세 생물학 본문을 재전사·요약·검증하지 않는다.35650은 유해 물질의 사용 세부를 새 파일에 재전사·요약하지 않고 독립 문화 서술과 분리 경계/메모 범위만 검토한다. 이 제한도 실제 판독 범위에 적는다.", "", "## 저자 검토표", ""]
    input_pins = []
    for review in reviews + [other / "rules.md"]:
        lines += ["- `" + str(review) + "`"]
        input_pins.append(dict(path=str(review.relative_to(ROOT)), sha256=digest(review)))
    for row in assignments[author]["rows"]:
        prefix = row["id"].replace(":", "_")
        lines += ["", "## 유형 " + row["id"] + " / 저자 " + decisions[row["id"]], "",
                  "원문: `" + str(ROOT / row["path"]) + "`", "", "허용 실제 저장물:"]
        input_pins.append(dict(path=row["path"], sha256=digest(ROOT / row["path"])))
        pattern = re.compile(re.escape(prefix) + r"(?:_v[0-9]+)?(?:_hold|_exclude)?[.](?:txt|md)")
        bodies = [p for p in other.glob(prefix + "*") if pattern.fullmatch(p.name)]
        for suffix in [".txt", "_hold.md", "_exclude.md"]:
            current = [p for p in bodies if p.name.endswith(suffix)]
            if current:
                p = max(current, key=ver)
                lines.append("- `" + str(p) + "`")
                input_pins.append(dict(path=str(p.relative_to(ROOT)), sha256=digest(p)))
        if decisions[row["id"]] == "KEEP":
            lines.append("- KEEP은 별도 본문 없이 원문 그대로 유지한다.")
    for row in auto_assigned[role]:
        lines += ["", "## 전량 v3 자동 후보 " + row["id"] + " / " + row["decision"], ""]
        for kind in ["original", "candidate"]:
            p = ROOT / row["paths"][kind]["path"]
            assert digest(p) == row["paths"][kind]["sha256"]
            lines.append(kind + ": `" + str(p) + "`")
            input_pins.append(dict(path=str(p.relative_to(ROOT)), sha256=digest(p)))
    text = chr(10).join(lines)
    with (directory / "TASK.md").open("x", encoding="utf-8") as f:
        f.write(text)
    result[role] = dict(author=author, profile_ids=sorted(expected),
                        auto_ids=[r["id"] for r in auto_assigned[role]], input_pins=input_pins,
                        task=str((directory / "TASK.md").relative_to(ROOT)))
with (AUDIT / "counter_profile_assignments_v1.json").open("x", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write(chr(10))
print(json.dumps({r: dict(profile=len(v["profile_ids"]), auto=len(v["auto_ids"])) for r,v in result.items()}))
