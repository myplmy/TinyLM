"""Pin the completed last author group and one source-supported grammar fix."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
assignment = json.loads((AUDIT / "profile_assignments_v1.json").read_text())["legacy_review"]
other = BASE / "agents/legacy_review/profile_resolution_v1"
directory = BASE / "agents/context_hangul/counter_profile_v1"
directory.mkdir()
lines = ["# 마지막 유형 정제본의 독립 대조와 작은 자기 교정", "",
         "역할은 정확 입력 판독과 새 txt/md 작성이다. 원문/타 작성자 수정 금지. 코드·시험·코퍼스 통계·해시 계산·모델·GPU·Git·웹·설치·삭제·목록 밖 접근 금지.", "",
         "먼저 자기45277의 v4를 원문과 다시 읽고 작은 v5를 만든다. 총괄이 원문 그래프 문단을 직접 읽었다. `From the discrete perspective ...`와 `We build this graph ...`라는 완결된 그래프 구성 설명이 이미 본문에 남아 있으므로, 다음 원문 `The nodes (and sometimes the edges) of are decorated with assorted data, especially the population associated to each vertex, which is crucial for plan validity.`에서 값 없는 `of`만 제거해 문법적으로 완결한 원문 문장을 복원할 수 있다. 새 graph/변수명을 넣지 않는다. 이 한 문장을 앞의 실제 graph construction과 뒤의 `Other attributes ...` 사이 원래 위치에 두면 Other의 선행사도 생긴다. 소실된 partition/cardinality/labeling-map/spanning-tree/cut-edge 형식 정의는 v4처럼 계속 분리한다. 원문은 `/home/uranus/tinyLM/data_cache/p106b_hold_recovery_v1_20261026_goalc/proposals_v1/review_packets/expanded_train_45277_original.txt`; 자기 manual_residual_v1의45277_v4 txt/hold/review_v4만 추가 입력 허용. 새45277_v5.txt/45277_v5_hold.md/review_v5.md를 그 디렉터리에 작성한다.", "",
         "다음은 타 작성자 legacy_review의 추가23건이다. 실제 본문과 원문을 끝까지 대조하고, 빈 표제/UI/기호 소실 및 분리한 구간을 지시하는 고아 참조, 원문 순서·주체·부정·조건·인용 손실, 없는 값/정의 생성이 남았는지 확인한다. 동일 줄번호 이동을 누락으로 오인하지 않으며 지적할 때 실제 양쪽 문구를 재확인한다. 이 디렉터리 새 counter.md에 ID/판정/실제 범위/정확 근거를 적고 작성자 파일은 수정하지 않는다.35650은 유해 물질 활용 세부를 새 파일에 재전사·요약하지 않고 독립 문화 서술 및 분리 경계/메모 범위만 대조한 제한을 보고한다.", "",
         "저자 검토표: `" + str(other / "review.md") + "`와 `" + str(other / "rules.md") + "`.", ""]
pins = []
for row in assignment["rows"]:
    prefix = row["id"].replace(":", "_")
    paths = [ROOT / row["path"]]
    paths += [p for p in [other / (prefix + ".txt"), other / (prefix + "_hold.md"), other / (prefix + "_exclude.md")] if p.exists()]
    lines += ["## " + row["id"], ""]
    for path in paths:
        lines.append("- `" + str(path) + "`")
        pins.append(dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper()))
    if len(paths) == 1:
        assert row["id"] == "expanded_train:248591"
        lines.append("- KEEP은 원문 그대로 사용하며 새 본문 없음.")
    lines.append("")
with (directory / "TASK.md").open("x", encoding="utf-8") as f:
    f.write(chr(10).join(lines))
with (AUDIT / "counter_profile_last_assignments_v1.json").open("x", encoding="utf-8") as f:
    json.dump(dict(role="context_hangul", ids=[r["id"] for r in assignment["rows"]], inputs=pins), f, ensure_ascii=False, indent=2)
    f.write(chr(10))
print(len(assignment["rows"]), "profile pairs pinned")
