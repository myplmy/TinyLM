"""Require an independent actual source review of the three retracted rows."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = BASE / "retracted_review_counter_v1"
inv.require(not OUT.exists(), "new independent retraction counter namespace required")
input_path = BASE / "root_selected_signal_counter_v1/manifest.json"
retraction_path = AUDIT / "AUTHOR_REVIEW_RETRACTIONS_V1.json"
source_rows = {row["id"]: row for row in inv.cache.read(input_path)["rows"]}
retractions = inv.cache.read(retraction_path)
ids = [row["id"] for row in retractions["rows"]]
inv.require(len(ids) == len(set(ids)) == 3, "exact retracted source scope differs")
role = "legacy_review"
directory = BASE / "agents" / role / OUT.name
inv.require(not directory.exists(), "independent role folder must be new")
directory.mkdir()
rows = []
parts = ["# 실제 판독 전 기재된 세 행의 별도 독립 대조",
         "현재 진행중인 root_selected_signal_counter_v1 TASK 한 개를 마친 뒤 이3쌍을 먼저 읽고, 그 뒤 원래 미완 TASK를 계속한다. 다른 완료 단계는 다시 열지 않는다.",
         "앞선 잘못된 검토표/그 저자의 출력은 이 역할의 근거로 사용하지 않는다. 아래 정확 원문과 당시 실제 선택본문만 각각 EOF까지 읽고 전체 diff를 직접 대조한다.",
         "유일한 새 출력 폴더: `" + str(directory) + "`.",
         "허용은 이TASK/지정쌍 text읽기·exact diff 및 자기새TXT/MD뿐이다. 코드·계산·계수·통계·해시·시험·웹·모델·GPU·Git·설치·타폴더쓰기·덮기삭제는 금지한다.",
         "후보가 삭제한 채워진 자녀/인명/역사/표/서지 등 독립 정보는 원문대로 복구한다. 실제 위키 추출 포장은 값·관계·순서를 보존해 정리한다. 숫자/날짜/조건/부정/인용 주체와 불확실성을 유지하고 누락값을 만들지 않는다.",
         "실제동일인날짜충돌은 두정확문맥만root에묻는다. 단순히서로다른연도가등장한다는이유로확정하거나한값을고르지않는다.",
         "review.md 표: ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거. 실제 새 본문은 expanded_train_ID_v2.txt 및 필요한 hold.md로 저장한다. 각 쌍을 실제 읽기 전 결론을 기재하지 않는다."]
for ident in ids:
    source = source_rows[ident]
    inv.require(source["role"] != role, "independent counter cannot use the same role")
    for pin in [source["original"], source["candidate"]]:
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "independent exact pair changed")
    rows.append(dict(source, role=role, root_approved=False))
    parts += ["## " + ident, "original: `" + str(ROOT / source["original"]["path"]) + "`",
              "original SHA: `" + source["original"]["sha256"] + "`",
              "candidate: `" + str(ROOT / source["candidate"]["path"]) + "`",
              "candidate SHA: `" + source["candidate"]["sha256"] + "`"]
with (directory / "TASK.md").open("x", encoding="utf-8") as stream:
    stream.write((chr(10) * 2).join(parts) + chr(10))
OUT.mkdir()
result = dict(status="INDEPENDENT_COUNTER_OF_RETRACTED_PREWRITTEN_ROWS_NOT_ADMISSION", rows=rows,
              assignments={role:ids}, pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [input_path, retraction_path, Path(__file__)]},
              cache_admitted=0, goal_complete=False, training_authorized=False)
inv.write_json(OUT / "manifest.json", result)
print(json.dumps(dict(rows=len(rows), assignments=result["assignments"], source_characters=sum(row["source_characters"] for row in rows)),ensure_ascii=False))
