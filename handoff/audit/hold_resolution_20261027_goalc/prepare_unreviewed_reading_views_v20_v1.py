"""Make ordered full reading views; these are not independent training docs."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
OUT = BASE / "remaining_unreviewed_context_v20_v1"
source_path = OUT / "manifest.json"
manifest = json.loads(source_path.read_text())
directory = OUT / "reading_views_v1"
directory.mkdir(exist_ok=False)
rows = []


def sha(payload):
    return hashlib.sha256(payload).hexdigest().upper()


def parts(ident, kind, payload):
    text = payload.decode("utf-8")
    result, reconstructed = [], []
    for offset in range(0, len(text), 6000):
        fragment = text[offset:offset + 6000]
        path = directory / (ident.replace(":", "_") + "_" + kind + "_" + str(offset // 6000 + 1).zfill(4) + ".txt")
        value = fragment.encode("utf-8")
        with path.open("xb") as stream:
            stream.write(value)
        reconstructed.append(value)
        result.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(value),
                           source_characters=[offset, offset + len(fragment)]))
    assert b"".join(reconstructed) == payload
    return result


for row in manifest["rows"]:
    values = {}
    for kind in ["original", "candidate"]:
        pin = row[kind]
        payload = (ROOT / pin["path"]).read_bytes()
        assert sha(payload) == pin["sha256"]
        values[kind] = payload
    delta = "".join(difflib.unified_diff(values["original"].decode("utf-8").splitlines(keepends=True),
        values["candidate"].decode("utf-8").splitlines(keepends=True), fromfile=row["original"]["path"],
        tofile=row["candidate"]["path"])).encode("utf-8")
    rows.append(dict(id=row["id"], role=row["role"],
        views={kind: parts(row["id"], kind, payload) for kind, payload in [*values.items(), ("diagnostic_diff", delta)]},
        diagnostic_diff_method="PYTHON_DIFFLIB_UNIFIED_DIFF_NOT_A_GNU_DIFF_EXIT_CLAIM",
        original_candidate_sha_pinned=True, ordered_view_bytes_reconstruct_inputs=True))
for role, ids in manifest["assignments"].items():
    destination = BASE / "agents" / role / OUT.name
    lines = ["# 전체 순서 판독 뷰", "이 파일과 지정 TASK의 정확 입력 및 아래 뷰만 추가 허용한다.",
        "뷰는 원문/후보를6000문자 단위로 잘랐으며 모든 뷰 바이트를 순서대로 합치면 지정 파일과 정확히 같다. 새 학습 문서가 아니다.",
        "diagnostic_diff는 Python difflib의 전체 unified diff이며 GNU diff 실행 결과가 아니다. diff뷰가 없는 쌍은 원문/후보가 바이트 동일하다.",
        "각 TASK의 전문/EOF·전체 차이를 실제로 읽는다. 출력 잘림을 완료로 세지 않는다. 인접 뷰의 경계를 연결하고 미판독은 정확히 기록한다.",
        "각 TASK를 마치면 표형 review_NNN.md를 새로 저장해 실제 근거를 보존한 뒤 다음 TASK로 간다. 기존 자기파일도 덮거나 지우지 않는다."]
    for row in rows:
        if row["role"] != role:
            continue
        lines.append("## " + row["id"])
        for kind, views in row["views"].items():
            lines.append(kind + (" (차이 없음)" if not views and kind == "diagnostic_diff" else ""))
            lines.extend("- `" + str(ROOT / view["path"]) + "` chars " + str(view["source_characters"])
                         for view in views)
    with (destination / "READING_VIEWS.md").open("x", encoding="utf-8") as stream:
        stream.write(chr(10).join(lines) + chr(10))
report = dict(status="FULL_ORDERED_SOURCE_CANDIDATE_AND_DIAGNOSTIC_DIFF_VIEWS_NOT_TRAINING_DOCS",
    source_manifest=dict(path=str(source_path.relative_to(ROOT)), sha256=sha(source_path.read_bytes())),
    producer_sha256=sha(Path(__file__).read_bytes()), rows=rows, cache_admitted=0, goal_complete=False,
    training_authorized=False)
with (OUT / "reading_views_manifest_v1.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(source_pairs=len(rows), exact_reconstruction_verified=True,
                      view_files=sum(len(parts) for row in rows for parts in row["views"].values()))))
