"""Prepare exact source/candidate text for the existing five text-only roles."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v9 as policy

AUDIT=Path(__file__).resolve().parent
BASE=inv.BASE
out=BASE/"policy_counter_review_v1"
inv.require(not out.exists(),"immutable review version required")
out.mkdir()
packets=out/"packets"
packets.mkdir()
inputs=[AUDIT/(f"policy_v{version}_purpose_probe_v1.json") for version in [7,8,9]]
rows={}
for path in inputs:
    for row in inv.cache.read(path)["rows"]:
        if row["decision"] in {"KEEP","EDIT"}:
            rows[row["id"]]=row
records=[]
for ident,row in sorted(rows.items()):
    info=row["source"]
    source=ROOT/info["path"]
    inv.require(inv.file_sha(source)==info["sha256"],"counter review source differs")
    text=source.read_bytes().decode("utf-8")
    value=policy.propose(dict(id=ident,text=text,complete_eos=True,valid_utf8=True))
    candidate=value.get("candidate",value["text"])
    payload=candidate.encode("utf-8")
    inv.require(len(payload)<20_000_000,"ordered review split required")
    target=packets/(ident.replace(":","_")+"_candidate.txt")
    with target.open("xb") as stream:
        stream.write(payload)
    records.append(dict(id=ident,original=info,candidate=dict(path=str(target.relative_to(ROOT)),sha256=inv.file_sha(target)),
                        decision=value["decision"],reasons=value["reasons"],changes=value["changes"],
                        characters=len(text),rules=policy.RULES,root_approved=False))
roles=["context_controls","context_hangul","context_latin","historical_review","legacy_review"]
assignments={role:[] for role in roles}
loads=Counter({role:0 for role in roles})
for row in sorted(records,key=lambda r:(-r["characters"],r["id"])):
    role=min(roles,key=lambda key:(loads[key],roles.index(key)))
    assignments[role].append(row)
    loads[role]+=row["characters"]
for role,assigned in assignments.items():
    directory=BASE/"agents"/role/"policy_counter_review_v1"
    directory.mkdir()
    lines=["# 기존 역할의 후속 독립 문맥 대조", "",
        "먼저 기존 TASK001–012와 기계 오류 보완을 마친 뒤 이 배정을 전부 수행한다. 별도 허가를 기다리거나 대표 몇 건에서 멈추지 않는다.",
        "읽기는 이 TASK, 아래 지정 original/candidate 두 본문과 자기 출력만 허용한다. 텍스트 판독과 새 txt/md만 작성한다. 코드/시험/계산/해시/통계/모델/GPU/Git/웹/다른 역할 자료 접근은 금지한다.",
        "정확한 두 입력의 읽기 전용 diff -u는 판독 도구로 허용한다. 명시적인 문자 차이와 실제 의미 손실을 분리한다.",
        "원문과 후보를 처음부터 끝까지 읽고, 조건·부정·수치·단위·날짜·주체·인용·불확실성·정상 코드/Unicode·실제 자료명을 대조한다. 빈 식의 흔적만 지운 뒤 그 식에 의존하는 설명을 남기지 않았는지, 반대로 독립 내용을 과잉 삭제했는지도 확인한다.",
        "원문 사실의 외부 진위나 코드 실행 성공은 판정하지 않는다. 새 이름/값/수식/표 열/출처/결론을 생성하지 않는다.",
        "출력은 이 디렉터리의 새 review.md와 필요한 expanded_train_ID_v2.txt/expanded_train_ID_hold.md다. 모든 검수 메모는 md에만 쓰고 학습 본문 txt에 넣지 않는다. 이미 있는 파일은 덮지 않고 새 vN으로 쓴다.",
        "review 표 열: ID | 판정 | 실제 판독 범위 | 출력 | 근거. 판정은 ACCEPT_CANDIDATE / REVISE_TEXT / EXCLUDE / NEEDS_ROOT 중 정확한 하나. 새 본문이 필요하면 REVISE_TEXT와 실제 파일을 함께 저장한다. 초안 통과는 root 최종 채택이 아니다.", ""]
    for row in sorted(assigned,key=lambda r:r["id"]):
        lines.extend(["## "+row["id"], "", "초안: "+row["decision"]+" / "+", ".join(row["reasons"]),
            "original: `"+str(ROOT/row["original"]["path"])+"`",
            "original SHA: `"+row["original"]["sha256"]+"`",
            "candidate: `"+str(ROOT/row["candidate"]["path"])+"`",
            "candidate SHA: `"+row["candidate"]["sha256"]+"`", ""])
    with (directory/"TASK.md").open("x",encoding="utf-8") as stream:
        stream.write(chr(10).join(lines)+chr(10))
inv.write_json(out/"manifest.json",dict(status="COUNTER_REVIEW_REQUIRED_NOT_CACHE_ADMISSION",rows=records,
    assignments={role:[r["id"] for r in assigned] for role,assigned in assignments.items()},
    loads_characters=dict(loads),input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in inputs},
    policy_sha256=inv.file_sha(ROOT/"scripts/p106b_hold_resolution_policy_v9.py"),producer_sha256=inv.file_sha(Path(__file__))))
print(json.dumps(dict(cases=len(records),assignments={role:len(values) for role,values in assignments.items()},characters=dict(loads)),ensure_ascii=False))
