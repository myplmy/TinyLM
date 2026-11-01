"""Assign every newly terminal purpose pair to an independent text-only role."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v22 as policy

AUDIT, BASE = Path(__file__).resolve().parent, inv.BASE
new_path = AUDIT / "policy_v22_purpose_probe_v1.json"
new = inv.cache.read(new_path)
for name, key in new["source_code_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == key, "purpose code changed before independent assignment")
output = BASE / "policy_v22_literal_counter_v1"
inv.require(not output.exists(), "new assignment namespace required")
output.mkdir()
directory = BASE / "agents/historical_review/policy_v22_literal_counter_v1"
directory.mkdir(parents=True, exist_ok=False)
rows = []
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:15695", "expanded_train:1216576",
              "expanded_train:1250821", "expanded_train:20624", "expanded_train:6030"}
for row in new["rows"]:
    if row["previous_decision"] != "PENDING" or row["decision"] not in {"KEEP", "EDIT"}:
        continue
    inv.require(row["id"] not in restricted, "restricted sources cannot enter general counter views")
    pin = row["source"]
    path = ROOT / pin["path"]
    inv.require(inv.file_sha(path) == pin["sha256"], "source pin changed")
    raw = path.read_bytes().decode("utf-8")
    prior_value = policy.previous.propose(dict(id=row["id"], text=raw, complete_eos=True, valid_utf8=True))
    inv.require(prior_value["decision"] == row["previous_decision"], "actual baseline regeneration differs")
    value = policy.propose(dict(id=row["id"], text=raw, complete_eos=True, valid_utf8=True))
    clean = value.get("candidate", value["text"])
    inv.require(value["decision"] == row["decision"] and inv.sha(clean) == row["clean_text_sha256"], "purpose regeneration changed")
    candidate = output / (row["id"].replace(":", "_") + "_candidate.txt")
    payload = clean.encode("utf-8")
    inv.require(0 < len(payload) < 20_000_000, "candidate artifact size differs")
    with candidate.open("xb") as stream:
        stream.write(payload)
    record = dict(id=row["id"], original=pin,
                  candidate=dict(path=str(candidate.relative_to(ROOT)), sha256=inv.sha(clean)),
                  prior_reasons=prior_value["reasons"], candidate_decision=value["decision"], root_approved=False)
    rows.append(record)
    task = directory / ("TASK_" + str(len(rows)).zfill(3) + ".md")
    lines = ["# " + row["id"], "", "정확 입력 두 파일을 전문 EOF/전체 diff로 판독한다. 추론 내용으로 식·값·코드를 채우지 않는다.",
             "", "original: `" + str(path) + "`", "original SHA256: " + pin["sha256"],
             "candidate: `" + str(candidate) + "`", "candidate SHA256: " + inv.sha(clean),
             "", "종전 신호: " + ", ".join(prior_value["reasons"]),
             "", "새 TXT/hold/표형 review_" + str(len(rows)).zfill(3) + ".md만 자신의 지정 폴더에 저장한다.",
             "표: | ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거 |", "판정: ACCEPT_CANDIDATE / REVISE_TEXT / KEEP_SOURCE / EXCLUDE / NEEDS_ROOT",
             "원문·후보 전체를 실제 읽기 전 ACCEPT 금지. 기존 파일은 자기 파일도 덮기/삭제/이동하지 않는다."]
    with task.open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(lines) + chr(10))
manifest = dict(status="ALL_NEWLY_TERMINAL_PURPOSE_PAIRS_ASSIGNED_NOT_ADMISSION", rows=rows,
                assignments={"historical_review": [row["id"] for row in rows]},
                input_pins={str(new_path.relative_to(ROOT)): inv.file_sha(new_path)},
                producer_sha256=inv.file_sha(Path(__file__)), cache_admitted=0, goal_complete=False, training_authorized=False)
inv.write_json(output / "manifest.json", manifest)
instructions = ["# historical_review 제한 역할", "", "역할: gpt-6-luna max 1개, 지정 원문/후보 판독과 새 txt/md 정제·제외 사유만.",
                "허용 읽기: 이 폴더의 START_HERE/TASK 및 manifest가 지정한 original/candidate, 자신이 새로 저장한 txt/md.",
                "허용 쓰기: " + str(directory) + " 안의 새 txt/md만. 새 버전 파일명을 사용하고 존재 확인 후 배타적으로 생성한다.",
                "금지: 다른 원문/역할/세션 자료, 코드·시험·모델·GPU·Git·규약·공유 원장 수정, 설치/다운로드, /tmp 포함 다른 경로 쓰기, 파일 덮기/삭제/개명.",
                "완전한 코드는 프로그램으로 실행하지 않는다. read/diff는 판독 보조이며, 잘린 출력으로 EOF를 주장하지 않는다.",
                "각 TASK가 완료되면 즉시 표형 review_NNN.md를 새로 저장하고 다음 TASK로 간다. 수정했으면 전체 후보를 편집 기반으로 사용하고 실제 새 TXT EOF/전체 diff를 확인한다.",
                "본문은 원문 내용만. hold/근거/행수/검토 메모는 md에만 둔다. 숫자/부정/조건/명칭/귀속/불확실성/참고·분류/실제 함수괄호/실제 강조값 보호.",
                "독립적인 완결 문장을 잃지 않으며, 판단 불명확하면 범위와 질문을 root에 보내고 다른 TASK를 진행한다.",
                "제한된 불법 제조 지침이 실제 나타나면 그 기술 내용을 복제하지 않고 ID/이유만 보고하여 root 판단을 받는다.",
                "", "이번 대상은 목적 탐색955 중 새로 종결된 모든 " + str(len(rows)) + "쌍이다. 전량 코퍼스 판독/사실검증이나 cache 채택이 아니다."]
with (directory / "START_HERE.md").open("x", encoding="utf-8") as stream:
    stream.write(chr(10).join(instructions) + chr(10))
print(json.dumps(dict(pairs=len(rows), role="historical_review", source_characters=sum(len((ROOT / r['original']['path']).read_text()) for r in rows), cache_admitted=0), ensure_ascii=False))
