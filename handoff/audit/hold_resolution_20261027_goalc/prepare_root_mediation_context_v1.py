"""Assign four concrete root-mediated source boundaries to text-only authors."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = BASE / "root_mediation_context_v1"
inv.require(not OUT.exists(), "new root mediation namespace required")
context_path = BASE / "contextual_residual_v11_v1/manifest.json"
plan_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V2.json"
context = {row["id"]: row for row in inv.cache.read(context_path)["rows"]}
selected = {row["id"]: row for row in inv.cache.read(plan_path)["rows"]}
assign = {"expanded_train:229468": "historical_review", "expanded_train:277085": "context_hangul",
          "expanded_train:801462": "context_latin", "expanded_train:909808": "legacy_review"}
notes = {
    "expanded_train:229468": "root는 앞부분의 실제 원자/오비탈 정의, n/L/m 및 s/p/d/f 설명과 조건·전자성질·역사를 확인했다. 원문/후보 전문을 독립 판독해 실제 없는 식·기호/범위/표의 도입과 그 직접 의존 설명만 sidecar로 분리한다. 실제 제공된 Ĥψ=Eψ 등 식과 변수 설명/조건이 완결돼 있으면 그대로 보존한다. 불확정성 관계나 궤도 명명 값을 외워서 채우지 않는다. 같은 문단의 완결된 정성 설명과 독립 역사는 함께 지우지 않는다. '근본적으로, 원자 궤도는 전자 하나의 전자에...'처럼 원문 자체 문장 뜻이 소실된 구간은 추정 번역/교정하지 않고 보류한다. 모든 수치·역사인물·시점·조건을 보존하고 실제 보존 범위/홀 경계만 root에 보고한다.",
    "expanded_train:277085": "root가 처음62행의 경력/발성/더빙 설명과 뒤에 긴 크레딧이 존재함을 확인했다. 학창시절/소속·1981/1990/2017 등 완결 경력과 모든 TV/극장OVA/게임/외화의 채워진 연도·작품·역할·배우 대응은 보호한다. '[마이데]를 [무대로]를' 같은 실제 손상 문장, 중복된 끝맺음 없는 표현 단편만 정확 원문 sidecar로 분리하고 임의 자연어 재번역/동의어 교정은 하지 않는다. 1995년의 인용 도입 뒤 실제 발언이 없으면 그 도입과 직접 의존 평가만 보류한다. 2007년의 깨진 [[레지던트 이블2... 링크는 실제 보이는 작품명/내용이 있으면 유지하되 표적/표시 관계를 새로 추정하지 않는다. 판단이 불명확한 해당 한 링크/문장만 hold하고 전체 유효 크레딧 목록을 제외하지 않는다.",
    "expanded_train:801462": "root가4039자 원문 전문을 읽었다. 음이 아닌 정수라는 도메인과 반복 자릿수합 정의를 보존한다. 65536의 자릿수근7과 덧셈지속성2의 채워진 주장은 남기고 '왜냐하면 이고 이기 때문이다'만 분리할 수 있다. 체크섬/덧셈지속성 등 완결 정성 설명, 독립적으로 식별되는 숫자/조건/수열·같이보기·자료는 보존한다. 실제 빠진 바닥함수 정의, 표와 '이 표는' 의존, 공식적 정의/증명에서 변수·수식이 없는 구간은 추측해 채우지 않고 함께 보류한다. 원문에 자릿수근9인9의배수 설명과 무조건 '9로 나눈 나머지'라는 주장이 같이 있어 latter의 빠진 증명/조건 의존은 분리하며 올바른 공식으로 대체하지 않는다. 매개변수를 잃은 가중치/연산/계승·거듭제곱 서술은 직접 결손만 보류하고, 나머지 완결된 수열/예시의 외부 사실검증이나 새 계산은 하지 않는다. TXT에는 검수 메모를 넣지 않는다.",
    "expanded_train:909808": "root가 원문15행 전문을 읽었다. 첫행 '|현재 상태 = 운영 중'은 채워진 상태 값이므로 삭제하지 않고 '현재 상태 = 운영 중'으로 보존하며, 고립된 다음 '}}'만 추출 구문으로 sidecar에 분리한다. GrassBase/Grassworld 이름, 2015/2016.1,11369/64273,기관과 저자네명은 그대로 보존한다. '(:en:Botanical name)'의 실제 영어명은 유지하고 원시 언어 namespace ':en:'만 포장으로 정리할 수 있다. 실제 자료 없는 각주/외부링크 표제만 분리하고 '온라인 데이터베이스' 분류를 유지한다. 상태 값을 새 기관/날짜로 재귀속하거나 원문 없는 사실을 만들지 않는다.",
}
OUT.mkdir()
rows, assignments = [], {}
for ident, role in assign.items():
    if ident in context:
        paths = context[ident]["paths"]
    else:
        prior = selected[ident]
        paths = dict(original=dict(path=prior["original_paths"][0], sha256=prior["original_text_sha256"]),
                     candidate=dict(path=prior["selected"]["body"], sha256=prior["selected"]["clean_text_sha256"]))
    for pin in paths.values():
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "root mediation source/body changed")
    row = dict(id=ident, role=role, original=paths["original"], candidate=paths["candidate"],
               root_context=notes[ident], root_approved=False)
    rows.append(row)
    assignments[role] = [ident]
    directory = BASE / "agents" / role / OUT.name
    inv.require(not directory.exists(), "new exact role folder required")
    directory.mkdir()
    text = f"""# root 중재: {ident}

이번 허용은 이 TASK와 아래 exact original/candidate의 text 판독, 전체 diff, 자기 새 TXT/MD 저장뿐이다. 모든 이전 완료 TASK는 닫혔다.
원문·후보 각각 처음부터 EOF까지 읽고 출력이 잘리면 작은 행 범위로 이어 판독한다. 미판독을 전문 판독으로 표시하지 않는다.
코드·시험·계산·계수·통계·해시·웹·모델·GPU·Git·설치·원형/타폴더 변경·덮기/삭제는 금지한다.
정확 출력 폴더: `{directory}`.
original: `{ROOT / paths['original']['path']}`
original SHA: `{paths['original']['sha256']}`
candidate: `{ROOT / paths['candidate']['path']}`
candidate SHA: `{paths['candidate']['sha256']}`

## root 판단과 보존 경계

{notes[ident]}

실제 수정은 `{ident.replace(':','_')}_v2.txt`와 필요한 새 hold.md에 저장한다. 원문에 없는 이름/수식/값/조건/날짜를 생성하지 않는다. 학술용어·인명·수치·단위·부정·조건·추측과 인용 귀속은 보존한다.
review.md 표: ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거. ACCEPT_CANDIDATE / REVISE_TEXT / KEEP_SOURCE / EXCLUDE / NEEDS_ROOT 중 실제 상태와 정확 본문 파일명을 적는다. 메모는MD에만 쓴다.
이번 한 건 완료 후 정확 저장물·미판독·미확정 대표만 보고하고 final로 종료한다. 이는 root 최종 캐시 채택·전체 검증·학습 승인이 아니다.
"""
    with (directory / "TASK.md").open("x", encoding="utf-8") as stream:
        stream.write(text)
result = dict(status="ROOT_MEDIATED_FULL_SOURCE_TEXT_REVIEW_NOT_ADMISSION", rows=rows, assignments=assignments,
              pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [context_path, plan_path, Path(__file__)]},
              cache_admitted=0, goal_complete=False, training_authorized=False)
inv.write_json(OUT / "manifest.json", result)
print(json.dumps(dict(rows=len(rows), assignments=assignments),ensure_ascii=False))
