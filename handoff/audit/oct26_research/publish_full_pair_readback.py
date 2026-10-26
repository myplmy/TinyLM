"""닫힌 두 본학습의 표와 실제 답변을 모델 로딩 없이 읽기 좋게 기록한다."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "handoff/audit/oct26_research"
EVIDENCE = ROOT / "test_result/evidence"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def publish(path, text):
    encoded = text.encode("utf-8")
    if len(encoded) >= 20_000_000:
        raise ValueError("result file limit")
    if path.exists():
        if path.read_bytes() != encoded:
            raise ValueError("existing publication differs")
        return
    with path.open("xb") as out:
        out.write(encoded)


stats_path = EVIDENCE / "p106b_native_format_pair_stats_v1_20261026_json_recovery_v3/report.json"
stats = read(stats_path)
closed = read(stats_path.with_name("root_closed_ref.json"))
if closed["actual_cpu_exit"] != 0 or closed["sha256"] != sha(stats_path):
    raise ValueError("statistics closure")
tasks = ["piqa", "arc_easy", "arc_challenge", "hellaswag", "winogrande", "boolq"]
if len(stats["exact_tests"]) != 30 or stats["holm_family"]["size"] != 30:
    raise ValueError("predeclared family")

manual = {
    "muon": {
        "user_01": ["계산 대신 같은 식 반복", "정답 대신 다음 계산 질문 나열"],
        "user_02": ["무관한 위키 각주·분류", "질문 반복"],
        "user_03": ["무관한 위키 각주·분류", "B를 사과로 바꾸며 반복"],
        "user_04": ["무관한 위키 분류 반복", "영희의 값을 3개로 바꾸며 반복"],
        "user_05": ["무관한 가수 분류 반복", "무관한 음악 그룹 분류 반복"],
        "user_06": ["무관한 종교 분류 반복", "무관한 만화 분류 반복"],
        "general_01": ["파리 대신 위키 분류 반복", "질문 반복"],
        "general_02": ["건물 확인 없이 무관한 분류", "건축물 분류만 쓰고 정보 확인 안 함"],
        "general_03": ["답 대신 다른 질문 반복", "입력 질문 반복"],
        "general_04": ["B=carrot은 맞게 시작하지만 과도한 반복·미종료", "대상을 A로 바꾸고 무의미한 설명 반복"],
        "general_05": ["사과를 나무와 동일시하며 반복", "A. 반복"],
        "general_06": ["구기 규칙 없이 일반 game 문장 반복", "A. 반복"],
    },
    "normuon": {
        "user_01": ["무관한 라오스 분류 반복", "질문과 문자열 반복"],
        "user_02": ["무관한 공원 분류 반복", "질문과 문자열 반복"],
        "user_03": ["B를 사과로 바꾸며 반복", "B를 사과로 바꾸며 반복"],
        "user_04": ["무관한 요리사 분류 반복", "무관한 요리사 분류 반복"],
        "user_05": ["무관한 여자 모델 분류 반복", "무관한 교수 분류 반복"],
        "user_06": ["무관한 영화 분류", "질문과 문자열 반복"],
        "general_01": ["무관한 선거구 분류", "파리 대신 도시 분류 반복"],
        "general_02": ["건물 확인 없이 무관한 분류", "건축물 분류만 쓰고 정보 확인 안 함"],
        "general_03": ["계산 답 없이 1+1 문장 반복", "1+1+1 반복"],
        "general_04": ["당근을 과일로 설명하고 tree 반복", "B=carrot은 맞게 시작하지만 반복·무관 문자열·미종료"],
        "general_05": ["과일·단맛은 관련되지만 같은 문장 반복·미종료", "질문 형태로 바꿔 반복"],
        "general_06": ["농구의 구체적 규칙 없이 game 문장 반복", "농구라는 동어반복과 같은 문장 반복"],
    },
}

lines = [
    "# 2026-10-26 전체300M 두 모델의 실제 48답 판독",
    "",
    "총괄 GPT가 12질문 × plain/ChatML × 두 모델의 원답 48개를 모두 읽었다. 다음 평은 후행 수동 판독이다. 자동 오류문구 검사나 새 학습 자료 편입이 아니다.",
    "",
    "이 문서는 읽기용 표시본으로 각 답변의 행 끝 공백과 탭만 생략한다. 원답 JSONL·토큰·SHA는 그대로 보존했다. 최초 표시 원형도 handoff/audit/oct26_research/dialogue_display_original_v1.md.txt에 남겼다.",
    "",
    "모델별 학습은 NTP300,023,808토큰이며 교사75M SFT×4epoch가 아니다. FP32/MATH·greedy·최대128토큰·MTP OFF·과거 대화 없이 첫 답만 생성했다. 실제 멀티턴 대화 능력을 시험한 결과로 해석하지 않는다.",
    "",
    "영어에서 관련 단어 또는 정답으로 시작한 예는 있지만 정상적인 답변 완결과 종료를 확인하지 못했다. 한국어도 반복·질문 재출력·위키 분류로 이탈했다. 답변 품질 개선이나 대화 가능 수준을 주장하지 않는다.",
    "",
]
review_rows = []
for arm in ["muon", "normuon"]:
    base = EVIDENCE / ("p106b_native_format_dialogue_v1_20261026_format_" + arm + "_json_recovery_v3")
    worker = read(base / "worker.json")
    root_ref = read(base / "root_closed_ref.json")
    if root_ref["actual_supervisor_exit"] != 0 or worker["requests"] != 24:
        raise ValueError("dialogue closure")
    manifest = worker["answers_manifest"]
    rows = []
    for shard in manifest["shards"]:
        path = base / "answers" / shard["path"]
        if sha(path) != shard["sha256"] or path.stat().st_size != shard["bytes"]:
            raise ValueError("answer shard changed")
        rows += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if len(rows) != 24 or len({(r["case_id"], r["mode"]) for r in rows}) != 24:
        raise ValueError("answer count")
    lines += ["## " + arm, "", f"원답 `{base.relative_to(ROOT)}/answers/` · SHA `{manifest['concat_sha256']}`.", ""]
    for r in rows:
        note = manual[arm][r["case_id"]][["plain", "chatml"].index(r["mode"])]
        trace = r["trace"]
        lines += [
            f"### {r['case_id']} / {r['mode']}", "",
            "질문: " + r["question"], "", "실제 답변:", "", "```text",
            "\n".join(line.rstrip(" \t") for line in r["display_answer"].split("\n")), "```", "",
            f"종료: {trace['finish_reason']} · 생성 {trace['generated_tokens']}토큰 · 원답 SHA {r['answer_sha256']}", "",
            "총괄 판독: " + note + ".", "",
        ]
        review_rows.append({"arm": arm, "case_id": r["case_id"], "mode": r["mode"], "answer_sha256": r["answer_sha256"], "note": note, "finish_reason": trace["finish_reason"], "generated_tokens": trace["generated_tokens"], "admitted_to_train": False})
    caps = sum(r["max_new_reached"] for r in rows)
    eos = sum(r["generated_ids"][-1] == 2 for r in rows)
    lines += [f"이 모델의 길이상한 종료 {caps}/24, EOS 종료 {eos}/24. EOS 도달은 내용 정답성·적절한 답변 완료가 아니다.", ""]

lines += [
    "## 원인 해석의 한계", "",
    "두 모델은 tie_mlp=false, train_repeat=infer_repeat=1, repeat_block=0, mtp_aux=false다. 따라서 공유 MLP·재귀 방문·MTP가 있어야만 반복이 생긴다는 설명은 이번 반례와 맞지 않는다. CLA2와 삼진 경로는 사용하므로 모든 아키텍처 영향을 배제한 실험은 아니다.",
    "",
    "format 처리는 기존 원문에서 일부 빈 제목·줄바꿈을 정리했을 뿐 위키 분류·참조목록 전체의 의미 정제나 QA 지도까지 완료한 것이 아니다. 원자료 잔재와 이어쓰기 학습 목표는 관측과 부합하는 설명 후보다. raw+Muon 전체 본팔은 NOT_RUN이므로 정제의 인과 효과나 반복의 단일 원인을 확정하지 않는다.",
    "",
    "같은 평가 답안을 다시 가르치지 않는다. 후속은 별도 TRAIN 원문·다른 질문으로 자료 정제 및 QA/종료 지도를 설계하고, 고정 평가와 원문 능력 보존을 분리해야 한다.", "",
]
report = ROOT / "docs/research/20261026_전체300M_두모델_실제48답_판독.md"
publish(report, "\n".join(lines))
receipt = {
    "schema": "TINYLM_ROOT_FULL_PAIR_READBACK_V2",
    "stats_report": str(stats_path.relative_to(ROOT)), "stats_sha256": sha(stats_path),
    "review_report": str(report.relative_to(ROOT)), "review_sha256": sha(report),
    "root_read_all_answers": 48, "models_loaded": 0, "gpu_calls": 0,
    "manual_notes": review_rows, "adoption_decision": False,
    "automatic_quality_gate": False, "benchmark_answers_added_to_train": 0,
    "display_transform": "TRAILING_SPACE_TAB_ONLY; raw answers and token IDs unchanged",
    "original_display": "handoff/audit/oct26_research/dialogue_display_original_v1.md.txt",
    "original_display_sha256": sha(AUDIT / "dialogue_display_original_v1.md.txt"),
}
publish(AUDIT / "full_pair_manual_readback_v2.json", json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
print("PUBLISHED", len(review_rows), "answers", report.relative_to(ROOT), "bytes", report.stat().st_size)
