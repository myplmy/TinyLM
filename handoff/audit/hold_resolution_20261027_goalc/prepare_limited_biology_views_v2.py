"""Expose only the previously read non-pathogen portions of two mixed pages.

The complete parents remain metadata references. This tool neither opens the
excluded line range nor generates biological protocols or missing facts.
"""
from itertools import islice
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = BASE / "limited_biology_views_v2"
inv.require(not OUT.exists(), "new immutable limited view namespace required")
old = inv.cache.read(BASE / "exclusion_second_review_v1/manifest.json")
sources = {row["id"]: row for row in old["rows"]}
limits = [("expanded_train:15695", 139, "context_latin"), ("expanded_train:20624", 72, "context_controls")]
OUT.mkdir()
rows, assignments = [], {}
for ident, end, role in limits:
    source_row = sources[ident]
    parent = source_row["original"]
    with (ROOT / parent["path"]).open("r", encoding="utf-8", newline="") as stream:
        lines = list(islice(stream, end))
    inv.require(len(lines) == end, "limited source prefix is shorter than the recorded range")
    raw = "".join(lines)
    view_path = OUT / (ident.replace(":", "_") + "_view.txt")
    with view_path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(raw)
    view = dict(path=str(view_path.relative_to(ROOT)), sha256=inv.file_sha(view_path))
    row = dict(id=ident, original=view, candidate=view, restricted_parent_metadata_only=parent,
               restricted_parent_read_only_included_prefix=True, excluded_parent_content_not_opened_or_copied=True, source_line_range=[1, end],
               excluded_parent_line_range=[end + 1, "EOF"], role=role, root_approved=False)
    rows.append(row)
    assignments[role] = [ident]
    directory = BASE / "agents" / role / OUT.name
    inv.require(not directory.exists(), "new role limited review directory required")
    directory.mkdir()
    task = f'''# 혼합 문서의 지정 제한 view 독립 판독

현재 배정 TASK 한 묶음을 끝낸 뒤 이 한 view를 판독하고 이전 잔여 TASK를 계속한다.
허용 입력은 이 TASK와 아래 view 하나뿐이며, 전체 parent/제외한 뒤쪽 행/다른 버전은 열지 않는다.
text-only: cat/sed/nl, 같은 exact view의 diff -u 읽기, 자기 새 TXT/MD만 허용한다. 코드·시험·계산·해시·모델·GPU·Git·웹·설치·미지정 자료·덮기·삭제는 금지한다.
이 view는 기존 판독자가 읽은 앞부분에서 일반 생태·효모·세포 연구의 초록/관련 기사 목록이 관측된 구간이다. 주제만으로 보류하지 않으며, 병원체 유전조작/감염·침입/제조 실행법을 복원하거나 추론·전사하지 않는다. 실제 그러한 구간을 발견하면 해당 범위만 root에 알려 주고 상세 재전사하지 않는다.
view 전체를 EOF까지 읽되 이 끝이 전체 parent EOF라고 주장하지 않는다. 실제 제목·기관·완결 초록/고찰이 독립적으로 연결되는 부분만 원문 순서로 보존한다. 서로 다른 논문은 제목/기관 등 실제 출처 경계로 구분하고 한 연구로 합치지 않는다. 관련 기사 개수·UI·검색 태그와 끊긴 전환부는 본문에서 분리하되 주제나 실험이라는 단어만으로 완결 독립 설명을 지우지 않는다.
없는 제목·인용자·값·조건·실험/배양/감염법은 채우지 않는다. 과학적 사실·규격을 외부 검증하거나 최신이라고 주장하지 않는다. 부분 보존이 불명확하면 NEEDS_ROOT로 기록하고 미판독/범위를 명시한다.
새 review.md 표는 ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거. ACCEPT_CANDIDATE / REVISE_TEXT / EXCLUDE / NEEDS_ROOT 중 하나로 쓰고, 수정은 실제 expanded_train_{ident.rsplit(':', 1)[1]}_v2.txt 및 별도 _v2_hold.md를 새로 저장한다. 검수 메모는 TXT에 넣지 않는다. parent의 제외 범위는 메타데이터로만 기록한다.

## {ident}

view original/candidate: `{ROOT / view['path']}`

view SHA: `{view['sha256']}`

원문에서 포함한 행: 1–{end}. 그 뒤부터 전체 parent EOF까지는 이 작업에서 미판독/비채택이며 열거나 사본을 만들지 않는다.

root가 최종 선택하며 캐시 검산·전량 사실검증·학습 승인이 아니다.
'''
    with (directory / "TASK.md").open("x", encoding="utf-8") as stream:
        stream.write(task)
pins = [BASE / "exclusion_second_review_v1/manifest.json", Path(__file__)]
inv.write_json(OUT / "manifest.json", dict(status="LIMITED_NONPATHOGEN_SOURCE_VIEW_REVIEW_NOT_ADMISSION",
    rows=rows, assignments=assignments, input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in pins},
    full_parent_hashes_not_recomputed=True, excluded_parent_content_not_opened_or_copied=True,
    root_adopted=0, goal_complete=False, training_authorized=False))
print(json.dumps(dict(rows=len(rows), ranges={row["id"]:row["source_line_range"] for row in rows}), ensure_ascii=False))
