# TinyLM Stage 1 Function Validation v01~v03 최종 생성·감사 보고서

- 감사 기준일: 2026-08-31
- 대상 영역: Stage 1 (3) 기능·용도·목적
- 대상 split: validation
- 최종 상태: **3 files / 450 records 확정**
- 정본 감사 JSON: `TinyLM_Stage1_Function_Validation_v01_v03_Audit_2026-08-31.json`

## 1. 생성 결과와 누적

요청한 450개를 150개씩 세 파일로 분리했다. Function train 4,050개 대비 record 수 비율은 `450 / 4,050 = 11.11%`다. 약 36K tokens는 450 packet의 설계 환산량이며 실제 학습 tokenizer의 token 수로 단정하지 않는다. 최종 `text`는 총 32,352자이고 `[0-9A-Za-z가-힣]+` 기준 공백·문장부호 분리 단위는 7,967개다.

| 파일 | ID 범위 | records | 새 concept family | unseen | `text` 문자 | 분리 단위 | SHA-256 |
|---|---|---:|---|---:|---:|---:|---|
| `stage1_(3)function_high_density_val_v01.json` | S1-FNV-0001~0150 | 150 | 천문·기상·지리 현장 관측과 야외 방향·시간 판독 도구의 기능 | 18 | 11,677 | 2,840 | `122a086c06c223a8d9a64dbdc5bf44d35b86a45d54fc51bb6b9ef92e071a607c` |
| `stage1_(3)function_high_density_val_v02.json` | S1-FNV-0151~0300 | 150 | 스포츠 경기 운영·판정·훈련·기록·안전 장비의 기능 | 18 | 10,486 | 2,618 | `f7d5bd99a13c708c781777f7c53714d2a409288decf927c2fbc6edda8b582754` |
| `stage1_(3)function_high_density_val_v03.json` | S1-FNV-0301~0450 | 150 | 악기 연주·조율·공명·음색 형성과 공연 보조 구성품의 기능 | 18 | 10,189 | 2,509 | `c832caf3afd8bfb43896b7eb250129801996bc88a7808fc93cd0953841b4a86a` |
| **합계** | S1-FNV-0001~0450 | **450** | **3개 새 family** | **54** | **32,352** | **7,967** |  |

원고는 `tools/function_validation_sources/v01.tsv`~`v03.tsv`에 concept, relations, unseen flag, 편집용 `other` 유형, 직접 작성 `text`를 분리 보관했다. 자동화는 ID·metadata·JSON 포장과 읽기 전용 감사에만 사용했다.

## 2. Validation 분리 규칙 결과

Function train v01~v27을 실제로 읽은 결과 `other`만 train에서 한 번도 나오지 않았고 나머지 12개 통제 relation은 관측됐다. 이에 따라 통제 어휘 밖 이름을 만들지 않으면서 다음처럼 V1~V3를 적용했다.

| 구분 | 전체 | 비율 | 파일별 | 판정 |
|---|---:|---:|---:|---|
| `unseen_relation: false` | 396 | 88.00% | 132/150 | relation 이름과 정렬된 relation-set이 모두 train 관측 |
| `unseen_relation: true` | 54 | **12.00%** | 18/150 | train 미관측 통제 relation `other` 포함, relation-set도 train 미관측 |

- 요청 범위 10~15% 충족: 예
- true 고유 미관측 relation-set: 9종
- false 고유 train 관측 relation-set: 13종
- true relation-set이 모두 train 미관측: 예
- false relation-set이 모두 train 관측: 예
- false record의 개별 relation 이름이 모두 train 관측: 예
- true record에서 실제 train 미관측 relation 이름: `other` 54회
- 모든 record의 `function` 포함: 450/450

## 3. Relations 분포

13개 통제 어휘 외 이름은 0건이며 record당 2~5개, record 내부 중복 0을 확인했다. `is_a`, `subclass_of`, `contrast`가 0인 것은 새 Function 문장의 실제 의미에 맞지 않는 라벨을 수량 맞추기용으로 붙이지 않았기 때문이다.

| relation | v01 | v02 | v03 | 전체 |
|---|---:|---:|---:|---:|
| `is_a` | 0 | 0 | 0 | 0 |
| `subclass_of` | 0 | 0 | 0 | 0 |
| `part_of` | 8 | 14 | 51 | 73 |
| `classification` | 9 | 4 | 5 | 18 |
| `boundary` | 12 | 28 | 7 | 47 |
| `contrast` | 0 | 0 | 0 | 0 |
| `comparison` | 25 | 11 | 8 | 44 |
| `function` | 150 | 150 | 150 | 450 |
| `role` | 20 | 37 | 32 | 89 |
| `process` | 35 | 18 | 21 | 74 |
| `state` | 21 | 25 | 36 | 82 |
| `attribute` | 24 | 23 | 37 | 84 |
| `other` | 18 | 18 | 18 | 54 |

## 4. `other` 편집 분류 상위 5유형

아래 유형명은 감사용 편집 분류이며 JSON의 relation 이름이 아니다. 실제 record에는 통제 relation `other`만 들어간다.

| 순위 | 자주 나온 개념 유형 | 수량 | 대표 concept |
|---:|---|---:|---|
| 1 | 환경·장소·규정 의존 (`context_dependency`) | 11 | 회전별자리판, 천문박명계산표, 산악기상경계판, 경기장기상중단판 |
| 2 | 기호·단위·표기 관례 해석 (`convention_interpretation`) | 11 | 별밝기비교성도, 국제기상기호관측표, 국제경기장선규격표, 관현악이조악기표 |
| 3 | 참여자·장비 시점 조율 신호 (`coordination_cue`) | 11 | 오토가이더카메라, 관측소시간동기화수신기, 팀훈련호흡신호등, 지휘자큐수신진동기 |
| 4 | 원본·수리·부품·기록 출처 추적 (`provenance_traceability`) | 11 | 천체사진촬영시각기록기, 경기영상원본봉인함, 악기수리이력꼬리표, 악기부품출처관리표 |
| 5 | 사용자 신체·감각·선호 맞춤 (`preference_adaptation`) | 10 | 접안렌즈배율세트, 관중맞춤득점안내판, 휠체어선수맞춤라켓그립표, 연주자맞춤리드강도표 |

## 5. 구조·중복·누출 감사

| 감사 항목 | 결과 |
|---|---:|
| JSON parse / UTF-8 오류 | 0 |
| 한글 `\uXXXX` escape 파일 | 0 |
| top-level metadata 오류 | 0 |
| record key / `function_packet` / `split: val` 오류 | 0 |
| ID 형식·전역 연속·범위 오류 | 0 |
| record 수 오류 | 0 |
| relation 통제·개수·중복·`function` 필수 오류 | 0 |
| unseen flag·relation-set 규칙 오류 | 0 |
| ID 중복 | 0 |
| primary concept 중복 | 0 |
| exact `text` 중복 | 0 |
| train–val exact primary concept 교집합 | 0 |
| train–val exact `text` 교집합 | 0 |
| train–val 객체–relation-set 조합 교집합 | 0 |
| validation 내부 반복 5어절 | 0 |
| train–val 공통 반복 5어절 | 0 |
| 반복 4어절 도입부 | 0 |

## 6. 유사도·보일러플레이트·한국어 품질

- 측정법: train과 validation을 함께 벡터화한 문자 3~5-gram TF-IDF cosine
- validation 내부 최대: `0.349621` — 테니스네트/배드민턴네트의 실제 유사 기능 문장으로, 복제 문장은 아님
- train–val 최대: `0.206182` — 총일사계/일사량계의 관련 기능 문장으로, exact·5어절 복제는 없음
- 내부 반복 5어절과 반복 도입부가 모두 0이고 최대 유사도도 낮아 대량 보일러플레이트 징후 없음
- primary concept 직후 `은/는·이/가·을/를·과/와·(으)로` 기계 검사 오류 0
- 문장 전체 조사 말음 후보 59건을 직접 확인함. `꺾는`, `있는`, `효과`, `사이`처럼 동사 관형형 또는 단어 자체의 끝음절을 조사로 오인한 후보였고 실제 조사 불량은 0
- 최종 문장 길이: 최소 52자, 중앙값 70자, 평균 71.893자, 최대 100자

첫 패키징 뒤 직접 검토에서 다음을 교정하고 전 파일을 다시 빌드·감사했다.

1. Function train과 겹친 `증발접시`를 새 primary concept `기상관측용증발팬`과 새 문장으로 교체했다.
2. 핸드볼골대/수구골대 사이 반복 5어절 1건을 수구골대의 실제 구조·계류 기능 문장으로 다시 썼다.
3. 오픈워터수영부표의 금지 수역 안내 방향을 바로잡았다.
4. 트럼펫워터키의 응축수 잡음, 호른스톱뮤트의 저항·음색·음정 보정, 탬버린징글의 금속성 잔울림, 마림바말렛의 경도별 반응을 더 정확하게 다시 서술했다.

교정 후 같은 전체 감사를 재실행했고 위 표의 모든 오류·중복·누출·반복 수가 0임을 확인했다.

## 7. 보호 파일 무결성

작업 시작 시점과 종료 시점에 다음 107개 정본의 SHA-256을 대조했다.

| 보호 범위 | 파일 수 | 변경 | 누락 |
|---|---:|---:|---:|
| Identity train v01~v41 | 41 | 0 | 0 |
| Identity validation v01~v04 | 4 | 0 | 0 |
| Attribute train v01~v31 | 31 | 0 | 0 |
| Attribute validation v01~v04 | 4 | 0 | 0 |
| Function train v01~v27 | 27 | 0 | 0 |
| **합계** | **107** | **0** | **0** |

Identity 계열을 포함한 보호 파일은 열람·해시·train 분리 감사 외에 수정하지 않았다. 작업 전 존재하던 범위 밖 smoketest/test-result 로그도 정리하거나 변경하지 않았다.

## 8. 산출물과 재현 명령

```text
val/stage1_(3)function_high_density_val_v01.json
val/stage1_(3)function_high_density_val_v02.json
val/stage1_(3)function_high_density_val_v03.json
tools/function_validation_sources/v01.tsv
tools/function_validation_sources/v02.tsv
tools/function_validation_sources/v03.tsv
tools/build_function_validation.py
tools/audit_function_validation.py
TinyLM_Stage1_Function_Validation_v01_v03_Audit_2026-08-31.json
TinyLM_Stage1_Function_Validation_v01_v03_Final_Report_2026-08-31.md
TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md
```

```powershell
$env:PYTHONIOENCODING='utf-8'
python stage1_highdensity_dataset\tools\build_function_validation.py stage1_highdensity_dataset
python stage1_highdensity_dataset\tools\audit_function_validation.py stage1_highdensity_dataset --output stage1_highdensity_dataset\TinyLM_Stage1_Function_Validation_v01_v03_Audit_2026-08-31.json --similarity-limit 150
```

작업지침서에는 Function validation의 파일명·ID·세 개 확정 family·12% unseen 해석·relations 분포·`other` 5유형·감사 기준·재현 명령·수정 금지 상태를 추가했다.
