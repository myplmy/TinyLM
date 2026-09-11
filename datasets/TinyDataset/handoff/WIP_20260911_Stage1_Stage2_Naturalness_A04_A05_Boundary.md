# WIP 작업원장 — 2026-09-11 Stage1/Stage2 자연성·병렬 경계

- **세션 시작**: 2026-09-11
- **직전 핸드오프**: 별도 handoff 파일 없음. 기존 중앙 원장: `stage1_highdensity_dataset/TinyLM_Stage2_Stage10_Actual3M_Expansion_Work_Ledger_2026-09-02.md`
- **사용자 지시**: 14건 (아래 표가 정본)

## 진행 상황판

| # | 지시 | 상태 | 산출물 | 이어받을 지점 |
|---|---|---|---|---|
| 1 | Stage1 highdensity 감사보고서에 primary+은/는 추가 감사와 Stage1 v2 추후 검토 사항을 기입 | ✅완료 | `audit_reports/Stage1_HighDensity_Retrospective_Naturalness_Audit_2026-09-11.md`, index, v2 설계서·v2 원장 | v2 범위·수치 gate·재작성 권한의 사용자 승인 전까지 `PREPARATION_ONLY` 유지 |
| 2 | 이 세션은 A04를 담당하고, A05는 Luna Max 별도 에이전트가 담당하는 영역분할 병렬 계획 | ✅완료 | 본 원장의 A04/A05 소유권 표 | A04 실제 수정 시작 전 source hash·중단 지점 재확인 |
| 3 | reviewer-assist 감사기를 특정 학습영역군(A04 등) 선택 검사하도록 구현 | ✅완료 | `stage2_highdensity_dataset/tools/audit_stage2_primary_reviewer_assist.js` | A04 실제 전체 감사는 A04 수정 범위 확정 뒤 `--area A04`로 실행 |
| 4 | A04 감사 수행 및 수정사항 보고 | ✅완료 (수정 범위 보고, source 미변경) | A04 read-only 전수 감사 결과·수정 필요성 판정 | 후속 재서술은 §7.15의 좁힌 범위와 사용자 승인 뒤에만 수행 |
| 5 | A04 수정 후 전수 재감사, 용어 적합성 사용자 검토표 제공 | ✅완료 (69/69 사용자 `Y` 반영) | A04 source 직접 수정·재감사 결과·Y/N 검토 TSV | 대시·문형 자연성은 별도 HOLD로 관리; A05·package·manifest 미변경 |
| 6 | C관련 요청: 감사기에 hard 대신 금지 표현 항목 추가해서 AI가 생성하는 어색한 표현 목록에 대해 별도로 경고/통계 수집 하도록 할 순 없는지? | ✅완료 | warning rules JSON, A04 source·독립 감사기·reviewer-assist 경고/통계 | 금지 표현은 구조 verdict와 분리된 `ADVISORY_WARNING_ONLY` packet으로 유지 |
| 7 | C관련 회신: review 를 포함한 다른 감사기 기능 추가는 승인 | ✅완료 | 대시 주어 복사·core fan-out 통계, syntax/self-test, Stage2 설계 규약 | 기존 hard schema·ID gate는 보존하고 자연성 경고를 별도 분리 |
| 8 | D정도면 굉장히 자연스러운데, 대부분의 문장이 매우 어색한 상태로 작성되어있는 것으로 보이는데 감사 및 재작성 제대로 수행한 것 맞는지? | ✅확인 | A04 감사보고서 §7.17의 범위·한계·최종 HOLD 근거 | 기존 구조·중복 감사는 실행됐으나 전수 한국어 자연성 검증으로는 불충분했음을 명시 |
| 9 | 권장 다음 순서에 따라 작업 착수 후 대시 primary 건 자연성 검토 수행바람. | ✅1차 완료 | 69행 재서술 → 전수 재감사 → 대시 1,263→1,233행 분류·고신뢰 29행과 불투명 text 5행 직접 재서술 | 잔여 1,233 대시는 family별 재설계 승인 전 일괄 치환 금지·`HOLD_SOURCE_PACKAGING` 유지 |
| 10 | 현재 감사 절차를 다른 에이전트에게도 전달하기 위한 프롬프트 제안 | ✅완료 | 전달용 감사 절차 프롬프트 | source-only·reader·자연성 warning·재감사·보고 경계를 포함해 최종 보고 |
| 11 | A06 `(13)temporal_order` v01 `.source.psv`와 v02 `.source.jsonl` 형식 검토 및 v01 수정 필요성 판단 | ✅완료 (읽기 전용) | legacy PSV/canonical JSONL 대조 수치·전환 권고 | v01은 유효 legacy PSV, v02는 유효 canonical JSONL; suffix-only rename 금지, 표준화는 별도 승인 필요 |
| 12 | 다른 에이전트가 자연스러운 문장으로 감사 후 재작성하도록 하는 프롬프트 제안 | ✅완료 | 전달용 자연성 재서술 프롬프트 | A04 대시·절단어근·불투명 기록행위의 실측 교훈과 human-review 경계를 포함 |
| 13 | A04 용어 적합성 사용자 검토 TSV의 반영 여부 확인, 미반영 시 수정 및 `-done` 완료 표기 | ✅완료 (source 변경 불필요) | 69 locator 전수 반영 대조 | 69/69 `Y`가 primary 또는 text에 반영, relations 0 변경; 조건부 수정·`-done` rename 미실행 |
| 14 | A04 전체 source를 자연스러운 명사구·의미 문장 규약에 따라 수정하고 전체 재감사 | 🔄진행 | A04 source 직접 재서술·A04 전수 audit·통합 감사보고서 갱신 | 대시형 primary 1,233행을 명확한 금지 형태로 판정; 수정 전 baseline을 재측정한 뒤 파일·행 단위로 직접 재서술 |

## 확보한 수치

측정 정의: `text`가 정확히 primary(패키지 JSON은 `concepts[0]`)로 시작하고 즉시 `은` 또는 `는`이 붙는 행.

| 범위 | 해당 / 전체 | 비율 |
|---|---:|---:|
| Stage1 train | 26,066 / 34,000 | 76.6647% |
| Stage1 val | 3,584 / 4,200 | 85.3333% |
| Stage1 전체 | 29,650 / 38,200 | 77.6178% |
| Stage2 현재 package train | 23,303 / 36,450 | 63.9314% |
| Stage2 현재 package val (A01 v01 1개) | 1 / 150 | 0.6667% |
| Stage2 현재 source train | 29,083 / 46,500 | 62.5441% |
| Stage2 A04 source | 5,784 / 10,350 | 55.8841% |
| Stage2 A05 v01 source | 2 / 150 | 1.3333% |

### A04 수정 전 기준점 (2026-09-11)

| 항목 | 값 |
|---|---:|
| 독립 structure source-set SHA-256 | `cd580a44f4648fa14af2365754a9a839a11e95bad9ad10c0d827c86d50046ba1` |
| 비-`text` projection SHA-256 | `60a4f5ead036871bbd111b04622054df023b4adf845f25a69d961d3b768e84bb` |
| structure verdict / 오류 합계 | PASS / 0 |
| 직접 수정 예정 | 명확한 primary 5행, 반복 5어절·Jaccard·길이 gate 대상 text |

### A04 수정 후 최종 기준점 (2026-09-11)

| 항목 | 값 |
|---|---:|
| 독립 structure source-set SHA-256 | `691c7e563bd7ea39a9f03c884eb1fd0d84b3f09cdaa90311253b44f63ebd7d7e` |
| 비-`text` projection SHA-256 | `8e4d404db49289cbf070494a004f5ccabee5ba39e7f60ce536a1296ae83371f6` |
| structure verdict / 오류 합계 | PASS / 0 |
| tokenizer tokens(+EOS) / 평균 | 454,462 / 43.909371981 |
| 파일 평균 목표 통과 / 범위 | 69/69 / 38.960000000~45.780000000 |
| 반복 5어절 / 4어절 도입부 | 0 / 0 |
| 독립 TF-IDF >=0.72 / Jaccard >=0.60 | 0 / 0 |
| 조사 hard·인접 중복·primary 후보 | 0 / 0 / 0 |
| 직접 수정 고유 행 / primary·text 동시 정정 행 | 142 / 6 |
| 사용자 검토 TSV | 69행·33 용어, 마지막 열 `user_decision_Y_or_N` |
| 남은 정책 신호 | primary+은/는 55.8550725%, 39 파일 diversity HOLD; Y/N 용어 검토 대기 |

### A04 advisory 자연성 경고 기준점 (69행 재서술 전)

| 항목 | 값 |
|---|---:|
| warning records / assignments | 1,336 / 1,408 |
| `primary_dash_qualifier` | 1,325 / 10,350 (12.8019324%) |
| exact 금지표현 warning | 23행 (초기 단순 substring 집계의 24는 일반 text 내 `가 판정` 1건을 오인한 값) |
| prefix·절단어근 warning | 33행 |
| `중간확정`·`차량통행` 합성어 warning | 13행 |
| 불투명 기록행위 text warning | 9행 / 14 assignments |
| 현재 reviewer hard 오류 | 0 (이 자연성 warning과 별도) |

### A04 69행 재서술 후 전수 재감사 기준점

| 항목 | 값 |
|---|---:|
| 사용자 `Y` target primary/text 변경 | 69 / 69, relations 변경 0 |
| independent structure | PASS, 오류 합계 0 |
| source-set / non-text projection SHA-256 | `25d0708aeef5f06588d5c752fe67e1bf84b4991f6ffe905cd6cb86181ae3a3cd` / `f310abf8fa81dfd03a9fbad4bb54ab72c3a7d4613d09b9b7c807fe1e1192555f` |
| tokens(+EOS) / 평균 / 파일 gate | 454,183 / 43.882415459 / 69/69 (38.96~45.76) |
| 반복 5어절 / 4어절 도입부 | 0 / 0 |
| TF-IDF >= 0.72 / Jaccard >= 0.60 | 0 / 0 (최대 0.665708883 / 0.590909091) |
| 조사 hard·인접중복·primary 후보 | 0 / 0 / 0 |
| advisory warning records / assignments | 1,267 / 1,268 |
| remaining dash primary | 1,263 |
| exact·prefix·constructed warning | 0 / 0 / 0 |
| opaque record-keeping text warning | 5 |

### A04 남은 대시 primary 자연성 read-only 분류

| 항목 | 값 |
|---|---:|
| 대시 primary | 1,263행 / 21 source files |
| preliminary direct rewrite candidate | 0 (기존 exact/prefix 목록 기준) |
| semantic text review candidate | 1 |
| DASH_DELIMITER_REVIEW | 1,262 |
| 여러 qualifier를 공유하는 core group | 347개 / 1,260행 |
| qualifier shape | 2 token 972, 3 token 이상 291 |

### 2026-09-11 A06 source 형식·A04 TSV 반영 read-only 대조

| 항목 | 결과 |
|---|---|
| `(13)temporal_order` v01 legacy PSV | BOM 없음, header 1 + data 150행, legacy reader 계약과 13개 relations·2~5 cardinality·중복 0 충족 |
| `(13)temporal_order` v02 canonical JSONL | BOM 없음, 150행/150 records, key `primary/text/relations`, 13개 relations·2~5 cardinality·primary/text 중복 0 |
| reader의 동시 형식 규칙 | 같은 reservation version에 `.source.jsonl`과 `.source.psv`가 함께 있으면 FAIL; 현재 v01/v02는 서로 다른 version이므로 충돌 없음 |
| A04 user-review TSV | 69 rows, malformed 0, `Y` 69, missing locator 0, primary 또는 text 변경 69/69, relations 변경 0 |

## A04/A05 소유권 및 금지 경계

| 담당 | 허용 경로 | 금지 경로 |
|---|---|---|
| 이 세션 (A04) | `stage2_highdensity_dataset/sources/train/stage2_(14)state_transition_high_density_train_v*.source.jsonl`, A04 전용 감사보고서·기계 결과·A04 전용 도구 | A05 `(15)` source, 중앙 원장·설계서, `PREPARATION_MANIFEST.json`, checkpoint, `train/`, `val/`, 공용 reviewer-assist 코드의 동시 수정 |
| Luna Max 별도 에이전트 (A05 예정) | `(15)modality_possibility` source·A05 전용 registry/감사 결과 | A04 `(14)` source·결과, 중앙 원장·설계서, manifest, checkpoint, `train/`, `val/`, 공용 reviewer-assist 코드 |

- 공용 reviewer-assist 실행은 반드시 영역 한정 selector 또는 `--match`를 사용한다. 기본 전체 source 스캔을 병렬 중 실행하지 않는다.
- 중앙 원장·manifest·checkpoint·패키징은 영역 source 감사가 끝난 뒤 이 세션이 단일 작성자로 순차 통합한다.
- A05는 아직 이 세션에서 배정·생성하지 않았다.

## 작업 로그 (append-only)

- 2026-09-11 착수. Stage1/Stage2 primary+은/는 전수 통계를 read-only로 확보했다.
- 2026-09-11 영향도 분석: A04/A05 source filename glob은 분리되어 파일 단위 충돌은 낮다. 그러나 공용 reviewer-assist의 기본 `--match`는 전체 Stage2 source이고 중앙 원장은 수정 상태이므로, 영역 selector 구현과 단일 문서 작성자 규칙이 선행되어야 한다.
- 2026-09-11 `--area` selector를 기존 reviewer-assist에 추가했다. `A01~A06`, source slot `11~16`, slug를 허용하며 `--match`와 교집합으로 파일명을 제한한다. `node --check`, `--self-test`, A04 v01(1 file·150 records) smoke와 A05 v01(1 file·150 records) smoke를 통과했다. source·package data는 수정하지 않았다.
- 2026-09-11 Stage1 retrospective 보고서·index와 Stage1 v2 설계/원장에 전수 수치, v1 비소급 보호, v2의 사람 검토·보정 전 수치 자동 gate 금지 원칙을 기록했다.
- 2026-09-11 중앙 Stage2~10 작업원장에도 A04/A05 역할 분할, 공용 경로 단일 작성자, `--area` 사용 규약, A05 미착수 상태를 기록했다.
- 2026-09-11 A04 감사 요청을 접수했다. A04는 자연성·출처 우려로 `PAUSED_PENDING_USER_DIRECTION` 상태였으므로, 우선 read-only 전수 감사와 기존 수정 이력·현재 source 대조를 수행하고 직접 재서술 대상은 결함 근거별로 분리한다.
- 2026-09-11 A04 현재 source를 read-only 전수 재감사했다. 독립 구조 감사는 69파일·10,350행에서 모든 오류 0(PASS), 조사 후보도 0이었다. 그러나 token 평균 상한 초과 6파일(합계 최소 1,484 tokens 압축 필요), 반복 5어절 25종·51 assignments(18행 greedy 재서술 후보), 독립 Jaccard 1쌍, `primary+은/는` 55.884058%(잠정 다양성 HOLD), 자연성 재검토 primary `찾 인계` 3행·`살피 포화` 2행·`중간확정` family 9행을 확인했다. source 수정 없이 A04 감사보고서 §7.15에 근거·수정 순서·보류 조건을 기록했다.
- 2026-09-11 사용자가 A04 수정과 전수 재감사를 승인했다. 수정 직전 독립 structure 기준점은 source-set `cd580a44f...50046ba1`, 비-`text` projection `60a4f5ea...768e84bb`, 69파일·10,350행·오류 0(PASS)이다. 명확한 용어 5행은 primary와 text를 함께, 나머지는 text 중심으로 수정하며, 검토가 필요한 용어는 마지막 열에 `Y`/`N`을 입력하는 TSV로 분리한다.
- 2026-09-11 A04 직접 보정을 완료했다. 142개 고유 행을 record별로 재서술했고, `찾 인계`·`살피 포화`·중복 수질 primary를 포함한 6개 primary를 text와 함께 정정했다. 최종 독립 구조 PASS(69파일·10,350행·오류 0), file-token 69/69, repeat5·repeat4 도입부 0/0, 독립 TF-IDF/Jaccard 임계 초과 0/0, 조사 후보 0/0/0을 확인했다. A04 audit §7.16과 69행 Y/N TSV·README를 작성했다. A05, package train/val, manifest, identity·저밀도·Stage1 확정 데이터는 수정하지 않았다.
- 2026-09-11 후속 재개점: 사용자 검토 TSV의 마지막 열에서 `Y`로 결정된 행만 현재 locator·primary·text를 재대조해 record별 patch를 만들고 전수 재감사한다. `N`과 `PENDING` 행에는 자동 변경을 하지 않는다. primary+은/는 55.8550725%의 문형 다양성 정책 신호는 family-level 승인 없이는 일괄 수정하지 않는다.
- 2026-09-11 사용자 검토표의 69행이 모두 `Y`임을 read-only로 확인했다. 이 중 62행은 ` — ` qualifier 형식이며, A04 전체 primary 중 같은 형식은 1,325/10,350행(12.8%)이다. 사용자 지정 확정 비문 13표현은 qualifier exact 비교로 23행이다(초기 단순 substring 24는 일반 text 내 `가 판정` 1건을 오인했다). 현 reviewer-assist의 hard 오류 0은 숫자 접미사·schema 중심 기계 규칙의 결과이며, 이 자연성 문제를 통과시킨다는 뜻이 아니다.
- 2026-09-11 사용자 승인: 금지 표현은 hard 실패가 아니라 별도 warning·통계·review queue로 추가한다. 수행 순서는 69개 `Y` 행의 primary/text 직접 재서술, A04 전수 재감사, 잔여 대시 primary의 read-only 자연성 분류다. ID·행순서·relations는 기본 보존하며, 재서술 후 text와 relations의 의미 불일치 후보는 자동 변경하지 않고 별도 보고한다.
- 2026-09-11 `primary_naturalness_warning_rules_v1.json`과 reviewer-assist의 warning-only 수집을 추가했다. Node syntax와 in-memory self-test를 통과했고, A04 10,350행 read-only 기준점은 warning records/assignments 1,336/1,408, 대시 primary 1,325행, exact 23행, prefix 33행, 합성어 13행, 불투명 기록행위 text 9행이다. warning은 direct rewrite target·구조 verdict에 영향을 주지 않는다.
- 2026-09-11 사용자 `Y` 69행의 primary와 text를 모두 record별로 직접 재서술했다. relations·행순서·파일 수·ID는 보존했다. 1차 재감사에서 새 반복 5어절 5종·10 assignments를 발견해 7행을 추가로 의미 재서술한 뒤 0/0으로 해소했다. 최종 구조·token·반복·독립 TF-IDF/Jaccard·조사 gate는 모두 PASS이며, 새 warning 통계는 대시 1,263행과 불투명 기록행위 text 5행만 남는다.
- 2026-09-11 새 `audit_a04_dash_primary_naturalness.js` read-only audit을 만들고 syntax/in-memory self-test를 통과했다. 남은 대시 1,263행은 347개 재사용 core group에 1,260행이 속하며, known exact/prefix fragment는 0이지만 `사 차단`·`사 계산`·`내리 재처리` 같은 목록 밖 절단 표현을 표본에서 발견했다. 따라서 대시 자체를 오류 확정으로 삼지 않고, warning 목록 확장 및 family별 AI 자연성 분류를 이어 간다.

### A04 warning 확장·대시 naturalness 재검토 최종 기준점 (2026-09-11)

| 항목 | 값 |
|---|---:|
| independent structure source-set SHA-256 | `554a3adf2e1b1cc9cc5ee2150db4cbebe91ecb8587477827f3c88f66739b7378` |
| 비-text projection SHA-256 | `a21ac53d8bbcc3fd731211dc25e06978d89f0c0e0174b0f09d9c8a3eccd3f84a` |
| structure verdict / 오류 합계 | PASS / 0 |
| tokenizer tokens(+EOS) / 평균 / 파일 gate | 454,150 / 43.879227053 / 69/69 (38.96~45.76) |
| 반복 5어절 / 4어절 도입부 | 0 / 0 |
| TF-IDF >=0.72 / Jaccard >=0.60 | 0 / 0 (최대 0.666119893 / 0.590909091) |
| 조사 hard·인접중복·primary 후보 | 0 / 0 / 0 |
| warning records / assignments | 1,233 / 1,233 |
| 잔여 대시 primary / high-confidence direct candidate | 1,233 / 0 |
| 대시가 조사와 함께 text 첫머리에 복사 | 1,116 / 1,233 (90.5109%) |
| 대시 core group / 재사용 group / 해당 records | 350 / 341 / 1,224 |
| `primary+은/는` / 전체 | 5,760 / 10,350 (55.6522%, 39 files diversity HOLD) |

- 2026-09-11 warning rule revision `2026-09-11-a04-fragment-expansion`을 추가했다. user 지정 13표현과 A04 대시 표본에서 확인한 절단·연결어 조각을 exact warning으로 보강했다. warning은 `HARD`가 아니며 source 자동 변경·구조 FAIL을 유발하지 않는다.
- 2026-09-11 high-confidence 29행을 primary와 text 함께 직접 재서술했다: v52 2행, v55 4행, v57 1행, v62 1행, v64 3행, v65 3행, v66 5행, v67 3행, v68 4행, v69 3행. v57:63에서 새 반복 5어절 1종을 확인해 같은 행의 text를 한 번 더 의미 보존형으로 수정했고 최종 0/0이다. relations·행 순서·파일 수는 보존했다.
- 2026-09-11 불투명 기록행위 warning 5행(v49:131, v52:101, v55:46·150, v56:106)도 개별 의미를 다시 읽어 text를 재서술했고, v52:101은 `터널 배수 상태 기록 대조`로 primary도 함께 정정했다. 최종 불투명 text warning은 0, direct rewrite candidate는 0이다.
- 2026-09-11 source/structure/similarity 감사기에 `--out`을 추가했다. sandbox가 Node 내부의 child-process 실행을 `EPERM`으로 막은 것을 우회하기 위한 audit artifact 출력 경로이며, 감사 정의나 source data는 바꾸지 않았다.
- 2026-09-11 A04 자연성 최종 판정은 `HOLD_SOURCE_PACKAGING`이다. 구조·중복·유사도·조사·token gate PASS는 자연스러운 한국어 전수 PASS가 아니다. 남은 대시 label과 문형 집중은 family-level 개념명·문장 재설계 승인 뒤 record별 직접 재서술로 다룬다. A05, package `train/val`, manifest/checkpoint, identity·저밀도·Stage1 확정 데이터는 수정하지 않았다.
- 2026-09-11 신규 4건을 접수했다. A06 temporal-order source 형식은 읽기 전용으로 live reader·generation guide·source schema를 대조한다. A04 user-review TSV는 locator별 source 반영을 전수 검증한 뒤, 미반영분만 record별로 수정하고 final audit 및 `-done` 표기를 수행한다. 다른 에이전트용 감사·자연성 재서술 프롬프트는 위 실제 audit 절차와 source-only 경계를 반영해 제안한다.
- 2026-09-11 A06 `(13)temporal_order` v01 PSV와 v02 JSONL을 read-only로 대조했다. v01은 legacy parser의 정확한 train header/150행 계약을, v02는 canonical JSONL 150행·schema·relation 계약을 충족한다. 서로 다른 version의 파일이므로 reader 충돌은 없으며, v01을 표준화할 경우에는 suffix만 바꾸지 말고 JSONL로 변환한 뒤 legacy 파일을 교체해야 한다.
- 2026-09-11 A04 user-review TSV를 locator별로 현재 source와 대조했다. 69 rows 모두 `Y`, 누락 locator·malformed rows 0, primary 또는 text 변경 69/69, relations 변경 0이다. 이미 반영되어 source 수정과 conditional `-done` rename은 수행하지 않았다.
- 2026-09-11 사용자 승인으로 A04 자연성 재서술을 재개했다. 이번 범위는 A04 `(14)state_transition` train source의 남은 대시형 primary와 그 text이며, `primary/text`만 record별로 수정한다. 행 순서·150행 파일 계약·relations·A05·package·manifest·checkpoint·중앙 원장은 보존한다. 전역 치환·템플릿 대량치환·source 전체 재직렬화는 금지하고 `apply_patch`의 파일·행 hunk만 사용한다.
- 2026-09-11 v49·v50·v51·v52의 대시형 primary 92행을 record별로 재서술했다. 네 파일은 각각 150행, 대시 primary 0, primary literal 누락 0, primary/text exact duplicate 0, relations 계약 오류 0을 확인했다. v52의 수정 후 SHA-256은 `a7a601a035c346cd5ecafde7f980bd503473d0ec0be9509eff7592c9266f5d8a`이다. 잔여 대시형 primary는 1,141행이며 v53부터 이어 간다.
- 2026-09-11 v53·v54의 대시형 primary 40행도 같은 방식으로 재서술했다. v49~v54 여섯 파일(900행)을 묶어 재검사한 결과 대시 primary·primary literal 누락·relations 계약 오류는 모두 0이다. v54의 수정 후 SHA-256은 `dfef1c7da8837beefb68957f4b537d66cdb5d42d549f540a5871be0c2523790e`이다. 누적 직접 재서술은 132/1,233행, 잔여는 1,101행이다.
- 2026-09-11 v55의 대시형 primary 52행을 모두 재서술했다. 중간 검사에서 새 primary 중복 1건(원래의 비대시 행과 같은 `열공급 열교환기 우회 운전`)을 발견해 `열공급 열교환기 성능 저하 우회 운전`으로 즉시 분리했다. v55는 150행, 대시 primary·literal 누락·primary/text exact duplicate·relations 계약 오류 0이며 수정 후 SHA-256은 `eb20e287f957a56d2a5a900bb253768c4f60e870e61f04ca7adb309c0012f0cf`이다. 누적 직접 재서술은 184/1,233행, 잔여는 1,049행이다.
- 2026-09-11 v56의 대시형 primary 16행과 v57의 13행도 재서술했다. 각 파일은 150행, 대시 primary·literal 누락·primary/text exact duplicate·relations 계약 오류 0이다. 수정 후 SHA-256은 v56 `98a73390f25a819ecc9377993f9d905c6febf2331f35227abcd9edd1802887b0`, v57 `3f009f32a2952162903ed7aad347e1410184656ba6b24d4f5cf437f09b6b0ae3`이다. 누적 직접 재서술은 213/1,233행, 잔여는 1,020행이다.
- 2026-09-11 v58의 대시형 primary 150행을 모두 record별로 재서술했다. 파일 단위 검사에서 새 primary 중복 1건(동일 파일 내 `산림 계곡 유량 안정 취수 제한 완화`)을 찾아 뒤 행을 `산림 계곡 유량 안정 수질 점검`으로 구분한 뒤 재검사했다. v58은 150행, 대시 primary·literal 누락·primary/text exact duplicate·relations 계약 오류 0이며 수정 후 SHA-256은 `d57329004c787652e5d83f815c4acaf6b91b2f51f9b7d8db92459f8169a36c97`이다. 누적 직접 재서술은 363/1,233행, 잔여는 870행이다.
- 2026-09-11 v59·v60·v61의 대시형 primary 32행을 재서술했다. 세 파일 모두 150행, 대시 primary·literal 누락·primary/text exact duplicate·relations 계약 오류 0이며 수정 후 SHA-256은 각각 v59 `fae2260b809bd3222046decf1c90beaa6463c857a8df9b08d2f2a8f1369dd40a`, v60 `4413ddea9cf392b0f936349dea6b057476ea3b93597006f26aebb2692cbf4db5`, v61 `a11c20b03dc0edbe3805aafe09eacdbba35e49c4617ce205cb0ef841a1c3064e`이다. 누적 직접 재서술은 395/1,233행, 잔여는 838행이다.
- 2026-09-11 v62의 대시형 primary 79행을 모두 재서술했다. 중간 처리에서 앞 30행을 이미 제거한 상태로 남은 목록에 다시 `skip 30`을 적용해 중간 30행이 남았고, 파일 단위 감사가 이를 정확히 31건(중복 포함)으로 검출했다. 남은 locator만 다시 읽어 직접 수정했으며, 새 primary 중복 1건은 `항만 위험물 검사 합격 후 격리 축소`로 구분했다. v62 최종은 150행, 대시 primary·literal 누락·primary/text exact duplicate·relations 계약 오류 0이고 SHA-256은 `d2feeb7d11b5a497b342135fc20cb8015b26913bb5fdffc32f95480d2a1c50f5`이다. 누적 직접 재서술은 474/1,233행, 잔여는 759행이다.
- 2026-09-11 v63의 대시형 primary 44행을 모두 record별로 재서술했다. 파일 단위 검사에서 150행, 대시 primary·primary literal 누락·primary/text exact duplicate·relations 계약 오류 모두 0을 확인했다. 수정 후 SHA-256은 `7a125b2e8c4d0c5798e579bca5821b63cf1e2fc7265d2b7c4a4792913c2d97b4`이다. 누적 직접 재서술은 518/1,233행, 잔여는 715행이며 v64부터 이어 간다.
- 2026-09-11 v64의 대시형 primary 67행을 모두 record별로 재서술했다. 파일 단위 검사에서 150행, 대시 primary·primary literal 누락·primary/text exact duplicate·relations 계약 오류 모두 0을 확인했다. 수정 후 SHA-256은 `15476ffce4dedec955186ee3b6aa841488f926efce58ad07036608d28f56c879`이다. 누적 직접 재서술은 585/1,233행, 잔여는 648행이며 v65부터 이어 간다.
- 2026-09-11 v65의 대시형 primary 115행을 모두 record별로 재서술했다. 파일 단위 검사에서 150행, 대시 primary·primary literal 누락·primary/text exact duplicate·relations 계약 오류 모두 0을 확인했다. 수정 후 SHA-256은 `84b8579ae4b27a3daf83c6a795ccbe19f1e535ca5dc70d2bf3fa7406acedb9ce`이다. 누적 직접 재서술은 700/1,233행, 잔여는 533행이며 v66부터 이어 간다.
- 2026-09-11 v66의 대시형 primary 130행을 모두 record별로 재서술했다. 반도체 공정군에서 절단 어근과 불투명한 상태 제목을 함께 해소하고, 각 행이 측정 대상·판정 조건·보류 또는 재개 행동을 드러내도록 text를 다시 썼다. 파일 단위 검사에서 150행, 대시 primary·primary literal 누락·primary/text exact duplicate·relations 계약 오류 모두 0을 확인했다. 수정 후 SHA-256은 `71738607f41f256a9eceace23b18a6ec106bb56b32d84a9a3580bdcb4752c973`이다. 누적 직접 재서술은 830/1,233행, 잔여는 403행이며 v67부터 이어 간다.
- 2026-09-11 v67의 대시형 primary 133행을 모두 record별로 재서술했다. 도시 열공급 운영군의 계측·압력·열원·공급 제한·운영회의 문장을 자연스러운 명사구와 조건-조치 문장으로 정리했다. 파일 단위 검사에서 150행, 대시 primary·primary literal 누락·primary/text exact duplicate·relations 계약 오류 모두 0을 확인했다. 수정 후 SHA-256은 `c0ad2e35b103bea42aa572e3dfb9ea457e3ceb7eb58a2e13eebb1c7b1143d9e1`이다. 누적 직접 재서술은 963/1,233행, 잔여는 270행이며 v68부터 이어 간다.
- 2026-09-11 v68의 대시형 primary 139행을 모두 record별로 재서술했다. 해양 부표의 수질·해양 상태·통신·경보·회수·재배치 운영군에서 관측 대상, 기준 비교, 조치와 재개 조건이 문장에 드러나도록 primary와 text를 함께 고쳤다. 파일 단위 검사에서 150행, 대시 primary·primary literal 누락·primary/text exact duplicate·relations 계약 오류 모두 0을 확인했다. 수정 후 SHA-256은 `a880fc5172715c8e35c91fbcecfb4467710303d60bba8c1eb402562847650ef3`이다. 누적 직접 재서술은 1,102/1,233행, 잔여는 131행이며 v69부터 이어 간다.
- 2026-09-11 v69의 대시형 primary 131행을 모두 record별로 재서술했다. 수술실 감염통제의 환자 확인·무균 관리·공조·수술 진행·회복·검체·보고·투약·퇴실 구간에서 실제 확인 조건과 안전 조치가 읽히도록 primary와 text를 함께 고쳤다. 파일 단위 검사에서 150행, 대시 primary·primary literal 누락·primary/text exact duplicate·relations 계약 오류 모두 0을 확인했다. 수정 후 SHA-256은 `f042eab4eae84797a26d576f7513eeff149844566c4c03521c12a335e4a718f8`이다. 누적 직접 재서술은 1,233/1,233행이며 다음 단계는 A04 69파일 전수 구조·유사도·조사·token·reviewer-assist 재감사다.
