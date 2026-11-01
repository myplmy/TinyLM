"""Pin the observed Search UI case without a general backtick exception."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
readback = json.loads((AUDIT / "root_selected_body_literals_v2.json").read_text())
row = next(row for row in readback["records"] if row["id"] == "expanded_train:6773")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


source = ROOT / row["compare_source"]["path"]
body = ROOT / row["body"]
assert sha(source) == row["compare_source"]["sha256"]
assert sha(body) == row["clean_text_sha256"]
raw, clean = source.read_text(encoding="utf-8"), body.read_text(encoding="utf-8")
before, after = [Counter(re.findall(r"`[^`\n]+`", text)) for text in [raw, clean]]
assert before - after == Counter({"`Search`": 1}) and not after - before
assert "Typ a word and hit `Search`." in raw and "Typ a word and hit `Search`." not in clean
evidence_path = AUDIT / "NONPROGRAM_SEARCH_UI_EVIDENCE_V1.md"
evidence = """# 6773 검색 UI의 실제 비프로그램 backtick 분리

총괄은 원문 Search 전후 검색 지시/검색 결과 목록과 현재 정제 본문 꼬리를 직접 읽었다. 원문의 검색어 입력 후 Search를 누르라는 문장은 독립 검색 UI이며 프로그램 예제가 아니다. 현재 정제 본문은 별도 사전 정의와 식물 설명을 유지한다. 원문/본문 inline 리터럴 Counter 차이는 Search 한 개이며 다른 리터럴의 추가/소실은 없다. 기존 전문 대조 review_008의 정확 SHA와 source/body를 연결한다.

이 판단은 해당 원문/본문 쌍에만 유효하다. 실제 프로그램이나 다른 버전의 backtick을 일반적으로 삭제하도록 허용하지 않는다. 원문 전체의 사실검증이나 모델 품질 승인이 아니다.
"""
with evidence_path.open("x", encoding="utf-8") as stream:
    stream.write(evidence)
record = dict(id=row["id"], kind="EXACT_REVIEWED_NONPROGRAM_DELIMITER_PAIR",
    original=str(source.relative_to(ROOT)), original_text_sha256=sha(source),
    body=row["body"], clean_text_sha256=sha(body),
    required_literal_segments=sorted(set(before) & set(after)),
    evidence=dict(path=str(evidence_path.relative_to(ROOT)), sha256=sha(evidence_path)),
    review_inputs=[dict(path=row["review"]["path"], sha256=row["review"]["sha256"])],
    removed_nonprogram_literal="`Search`", root_approved=True)
out = AUDIT / "NONPROGRAM_SEARCH_UI_APPROVAL_V1.json"
document = dict(schema="P106B_EXACT_LITERAL_GUARD_APPROVALS_V1",
    status="ROOT_REVIEWED_EXACT_SOURCE_BODY_PAIRS", global_code_guard_waiver=False, rows=[record])
with out.open("x", encoding="utf-8") as stream:
    json.dump(document, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(id=row["id"], registry_sha256=sha(out),
                      removed_nonprogram_literals=dict(before - after)), ensure_ascii=False))
