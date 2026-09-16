# Stage2 A05 가능성·양상 로컬 작업원장 — 2026-09-11

- **작업 영역:** `stage2_(15)modality_possibility`
- **세션 시작:** 2026-09-11 (Asia/Seoul)
- **정본 지침:** `stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`
- **정본 설계:** `stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`
- **중앙 원장:** 읽기 전용. 이 파일이 A05의 진행·재개 상태를 기록하는 유일한 로컬 원장이다.

## 사용자 지시 원문과 범위

> 영역분할 병렬로 작업하여 이 세션은 A05 작업 수행예정임. `(15)modality_possibility` source v01~v69, A05 전용 registry·감사 산출물만 담당할 것. 다른 영역과 `PREPARATION_MANIFEST.json`, 중앙작업원장, `train/`, `val/`, checkpoint, 공용 감사기 코드는 절대 수정 금지.
>
> Stage2 A05 데이터셋 생성착수할 것. 중앙작업원장은 절대 수정금지. A05전용 로컬작업원장 별도로 작성하여 해당 파일만 편집할 것. A05전용 로컬작업원장, 설계서, 데이터셋 생성 지침서 참고하여 생성 누락, 오류, 지침이나 규약 위반등 발생하지 않도록 할것.
>
> 업무 효율을 위해 파일 내 토큰 평균 등의 감사와 수정은 각 데이터셋의 교육영역 단계 생성이 완료되면 일괄 감사 수행 후 수정하길 바람. 교육영역 단계 생성이 완료되면 한국어 커밋메시지 제목과 내용 제안바람.

## 보호 경계

| 구분 | 허용·담당 | 절대 수정하지 않음 |
|---|---|---|
| source | `stage2_highdensity_dataset/sources/train/stage2_(15)modality_possibility_high_density_train_v01.source.jsonl`~`v69.source.jsonl` | `(11)`~`(14)`, `(16)` 이후 모든 source, `sources/val/` |
| A05 registry | A05 전용 sidecar만 | 중앙 manifest 또는 다른 영역 registry |
| A05 감사 | A05 전용 `audit_reports/` 및 `audit_reports/machine/` 결과만 | 공용 감사기 코드, 다른 영역 보고서 |
| 원장 | 이 파일만 편집 | 중앙 작업원장·설계서·Guide |
| 패키지·체크포인트 | 생성하지 않음 | `stage2_highdensity_dataset/train/`, `val/`, checkpoint |

`PREPARATION_MANIFEST.json`은 예약을 읽는 정본이지만 수정하지 않는다. source-only 작업은 corpus 완료나 Stage2 누적 완료로 계상하지 않는다.

## 예약 기준선(읽기 전용 snapshot)

- manifest SHA-256(2026-09-11 read-only): `1802fd79354a9ff3cd36872a7f2c32a89ae1803e94aae9ce40edea7cbe4b0c0e`
- A05 train 예약: 69 files × 150 records = 10,350 records (`S2-MPH-00001`~`S2-MPH-10350`)
- 현재 존재: train source v01~v69 69개(각 150행). v02~v10은 기존/부분생성 파일을 읽기 검증했고, v11~v69는 이번 실행에서 생성했다.
- A05 validation 예약 v01~v08은 이 실행 범위에 포함하지 않으며 `sources/val/`을 만들거나 수정하지 않는다.

### v01~v69 concept-family 순서

각 version은 아래 한 family만 담당한다. family명은 manifest에서 읽은 값을 그대로 사용하며, 이름을 재조합하거나 행번호·숫자 suffix를 붙여 새 primary를 만들지 않는다.

| train version | 예약 family/domain |
|---|---|
| v01~v04 | 스마트 온실 관수·환경제어 — 가능성·실제 발생·미발생 / 확률 수치와 주관 확신 / 계획·예정·예측의 시간적 지위 / 가정·반사실·조건부 결과 |
| v05~v08 | 도시 상수도 정수·배수 운영 — 위 네 축 순서 |
| v09~v12 | 클라우드 서비스 부하·장애 대응 — 위 네 축 순서 |
| v13~v16 | 철도 운행 간격·환승 조정 — 위 네 축 순서 |
| v17~v20 | 하천 저수지 수위·방류 관리 — 위 네 축 순서 |
| v21~v24 | 식품 냉장 유통·품질 유지 — 위 네 축 순서 |
| v25~v28 | 온라인 학습 진도·피드백 운영 — 위 네 축 순서 |
| v29~v32 | 생태 복원지 종·서식지 관찰 — 위 네 축 순서 |
| v33~v36 | 배터리 저장장치 충방전·열관리 — 위 네 축 순서 |
| v37 | 지하철 역사 환기·혼잡 제어 — 불완전 관측의 가능 상태 |
| v38 | 수산 양식장 수질·급이 운영 — 불완전 관측의 가능 상태 |
| v39 | 태양광 발전소 출력·고장 관리 — 불완전 관측의 가능 상태 |
| v40 | 응급 콜센터 배차·인계 — 불완전 관측의 가능 상태 |
| v41 | 공항 활주로 제설·운항 회복 — 가능 상태와 실제 관측 상태의 분리 |
| v42 | 반도체 클린룸 오염·수율 관리 — 예측 확률과 운영자 확신도의 척도 구분 |
| v43 | 도시 열공급망 부하·압력 조정 — 예정된 조치와 발생한 사건의 시간 지위 |
| v44 | 해양 부표 관측·경보 운영 — 반사실 조건에서 결과 범위 제한 |
| v45 | 병원 수술실 배정·감염 통제 — 정보 부족과 실질적 무작위성의 불확실성 구분 |
| v46 | 산림 병해충 예찰·방제 — 가능 상태와 실제 관측 상태의 분리 |
| v47 | 전기버스 충전차고 전력·배차 — 예측 확률과 운영자 확신도의 척도 구분 |
| v48 | 식품 발효공정 온도·품질 제어 — 예정된 조치와 발생한 사건의 시간 지위 |
| v49 | 데이터센터 냉각·전력 절체 — 반사실 조건에서 결과 범위 제한 |
| v50 | 항만 컨테이너 하역·혼잡 관리 — 정보 부족과 실질적 무작위성의 불확실성 구분 |
| v51 | 스마트 축사 환기·질병 감시 — 가능 상태와 실제 관측 상태의 분리 |
| v52 | 도로 터널 배수·교통 통제 — 예측 확률과 운영자 확신도의 척도 구분 |
| v53 | 공항 활주로 제설·운항 회복 — 예정된 조치와 발생한 사건의 시간 지위 |
| v54 | 반도체 클린룸 오염·수율 관리 — 반사실 조건에서 결과 범위 제한 |
| v55 | 도시 열공급망 부하·압력 조정 — 정보 부족과 실질적 무작위성의 불확실성 구분 |
| v56 | 해양 부표 관측·경보 운영 — 가능 상태와 실제 관측 상태의 분리 |
| v57 | 병원 수술실 배정·감염 통제 — 예측 확률과 운영자 확신도의 척도 구분 |
| v58 | 산림 병해충 예찰·방제 — 예정된 조치와 발생한 사건의 시간 지위 |
| v59 | 전기버스 충전차고 전력·배차 — 반사실 조건에서 결과 범위 제한 |
| v60 | 식품 발효공정 온도·품질 제어 — 정보 부족과 실질적 무작위성의 불확실성 구분 |
| v61 | 데이터센터 냉각·전력 절체 — 가능 상태와 실제 관측 상태의 분리 |
| v62 | 항만 컨테이너 하역·혼잡 관리 — 예측 확률과 운영자 확신도의 척도 구분 |
| v63 | 스마트 축사 환기·질병 감시 — 예정된 조치와 발생한 사건의 시간 지위 |
| v64 | 도로 터널 배수·교통 통제 — 반사실 조건에서 결과 범위 제한 |
| v65 | 공항 활주로 제설·운항 회복 — 정보 부족과 실질적 무작위성의 불확실성 구분 |
| v66 | 반도체 클린룸 오염·수율 관리 — 가능 상태와 실제 관측 상태의 분리 |
| v67 | 도시 열공급망 부하·압력 조정 — 예측 확률과 운영자 확신도의 척도 구분 |
| v68 | 해양 부표 관측·경보 운영 — 예정된 조치와 발생한 사건의 시간 지위 |
| v69 | 병원 수술실 배정·감염 통제 — 반사실 조건에서 결과 범위 제한 |

## 생성·감사 계약

- source JSONL 각 행은 `primary`, `text`, `relations`만 가진다. 한 파일은 정확히 150행이다.
- ID는 source에 없으며 중앙 예약의 `S2-MPH` 범위를 참고만 한다. primary에는 행번호·ID·공통 숫자 suffix를 넣지 않는다.
- primary와 text는 record별 직접 작성한다. 명사·동사 자동 결합, 동일 template의 명사 치환, round-robin relation 배정, 공통 종결구 대량 반복은 금지한다.
- relations는 `is_a`, `subclass_of`, `part_of`, `classification`, `boundary`, `contrast`, `comparison`, `function`, `role`, `process`, `state`, `attribute`, `other` 중 2~5개이며 한 행 안에서 중복하지 않는다.
- possibility·modality 의미는 가능성/예정/예측/확률/확신/반사실과 실제 발생을 분리해 서술한다. 각 text에는 관찰 근거, 판정 기준, 예외 또는 반례 중 둘 이상을 자연스럽게 담는다.
- 모든 text를 primary+`은/는`으로 시작하지 않는다. 영역 전체 생성이 끝날 때까지는 구조·150행·필드·relations 최소 계약만 확인하고 token 평균·유사도·반복 5어절·조사 전수 감사는 실행하지 않는다.
- 영역 완료 후 한 번에 token·exact/정규화 중복·5어절·도입부·동일 relation-set 유사도·조사·relations 분포를 감사한다. 30% 초과는 검토, 45% 초과는 포장 HOLD라는 임시 자연성 gate를 보고하되, 문법 오류율로 해석하지 않는다.
- A05 registry sidecar 필수 필드: `source_file`, `source_line`, `primary`, `term_kind`, `definition`, `provenance_kind`, `provenance_ref`, `review_status`. canonical source schema에는 registry 필드를 추가하지 않는다.
- 감사 오류는 해당 행만 직접 재서술하고 source projection·행/파일 수·relations·registry revision을 전후 보존한다. corpus/package/checkpoint는 생성하지 않는다.

## 진행 상황판

| # | 작업 | 상태 | 산출물 | 이어받을 지점 |
|---|---|---|---|---|
| 1 | 정본 Guide·Design Spec·예약 manifest·기존 A05 v01 확인 | ✅완료 | 이 원장 기준선 | v01 최소 계약 감사 |
| 2 | A05 v01 최소 계약·중복·primary suffix read-only 감사 | ✅완료 | `audit_reports/machine/a05/TinyLM_Stage2_A05_v01_Minimum_Review_2026-09-11.json` | v02 작성 |
| 3 | A05 train source v02~v69, 150행씩 직접 작성 | ✅완료 | `sources/train/stage2_(15)*.source.jsonl` | 영역 일괄 감사 |
| 4 | A05 registry v01~v69 coverage 100% 생성·검증 | ✅완료 | `sources/term_registry/stage2_(15)modality_possibility_train_registry_v01_v69.jsonl` | 영역 일괄 감사 |
| 5 | A05 영역 일괄 token·중복·유사도·조사·relations 감사 | ✅완료 | `audit_reports/machine/a05/*Full_Audit_Final*`, 독립 대조 JSON | 최종 source-only 판정 |
| 6 | A05 감사 후 재감사 및 한국어 커밋메시지 제안 | ✅완료 | `audit_reports/TinyLM_Stage2_A05_ModalityPossibility_Train_Consolidated_Audit_2026-09-11.md` | 사용자 보고; package 금지 |

## 작업 로그 (append-only)

- 2026-09-11: A05 전용 원장을 생성했다. 중앙 작업원장·manifest·설계서·Guide·공용 감사기·다른 영역·package/checkpoint는 수정하지 않는다.
- 2026-09-11: 예약 manifest SHA와 v01 존재 상태를 읽기 전용으로 고정했다. 다음 지점은 v01 최소 계약 감사다.
- 2026-09-11: v01을 A05 파일명 정규식으로 read-only 감사했다. 1 file·150 rows, hard source error 0, direct rewrite target 0, `primary+은/는` 2/150 (1.3333%), X1/X2·동일 relation-set 유사도 임계 초과 0건이었다. 동일 X2 집중 3개 그룹은 ChatGPT 의미 검토 queue에 남겼고, source는 수정하지 않았다.
- 2026-09-11: 첫 생성기 시도는 `pad` 선언 누락으로 파일 쓰기 전에 중단됐다. 두 번째 시도에서 v09를 생성한 뒤 v10 확률 프레임 15행이 primary를 text에 포함하지 않아 중단됐다.
- 2026-09-11: v10의 primary 누락 15행을 의미 보존 직접 재서술로 보완했다. 이후 생성기에서 primary 포함·2~5개 통제 relations·파일별 150행·A05 전역 primary 중복을 생성 시점에 검증했다.
- 2026-09-11: A05 v01~v69 source를 모두 확보했다(기존/검증 10 files + 신규 59 files = 69 files, 10,350 rows). A05 전용 registry를 10,350 locator로 생성했으며, 전체 감사 전 상태는 `pending_full_audit`다.
- 2026-09-11: v11~v69의 text 8,850행을 의미축·표지어를 교차하는 직접 재작성으로 보강했다. primary와 relations는 유지했고, 문장별 primary literal을 재확인했다.
- 2026-09-11: 영역 일괄 감사에서 발견한 명확한 표면 오류를 A05 source에만 직접 반영했다. 32개 record의 의미 재서술, 표지어 중복 135건, 표지어 조사 부착 오류 676건, legacy 조사·띄어쓰기 오류를 정정했다. 이후 registry를 10,350행으로 재생성하고 `review_status=audited_source_only`로 갱신했다.
- 2026-09-11: 정본 reviewer-assist와 독립 대조 감사를 최종 실행했다. source set SHA-256 `c33b5f265f6be8cee626853fdfed26518655c1a1bf5b16e79f5be1b6f00a82e1`, registry SHA-256 `6e3f0ddf751a52086b45535c847e91cf33195fa68ac18117205a34465e3644b5`, 69 files·10,350 rows·registry coverage 100%을 확인했다.
- 2026-09-11: 최종 수치: token 206,495 / 평균 19.952173913; primary+은/는 1,702/10,350=16.4444%(전체 gate 통과; v05만 33.3333% review); exact·정규화 primary/text 중복 0; 조사·자연성 결정적 suspect 0; hard 0/direct rewrite queue 0/user queue 0; ChatGPT review queue 46(도입부·X2·relation-set 유사도 검토 신호).
- 2026-09-11: relations 분포는 `is_a 0`, `subclass_of 0`, `part_of 38`, `classification 924`, `boundary 4,231`, `contrast 1,590`, `comparison 2,924`, `function 745`, `role 1,710`, `process 4,698`, `state 7,380`, `attribute 3,477`, `other 3,333`이다. `other` 상위 유형은 확률·확신 896, 가정·반사실·조건부 결과 705, 정보 부족·불완전 관측 675, 가능성·실제 발생·미발생 607, 계획·예정·예측 450이다.
- 2026-09-11: 반복 5어절은 30종(상위 count 195), same relation-set 유사도는 44 groups, raw word-Jaccard≥.60 166,088쌍, masked 522,136쌍, raw char3–5 TF-IDF≥.72 18,542쌍, masked 34,221쌍, 최고 raw Jaccard .954545455 / masked 1 / raw TF-IDF .973745678 / masked 1이다. 모두 공통 템플릿·공유 어휘에서 비롯된 검토 신호로 기록하고 의미 오류로 자동 승격하지 않았다.
- 2026-09-11: A05 통합 감사보고서를 작성했다. source-only 산출물이며 `stage2_highdensity_dataset/train/`, `val/`, checkpoint, 중앙 원장·manifest, 공용 감사기 및 다른 교육영역은 수정하지 않았다. A05 train 완료 후 다음 재개 지점은 사용자 승인에 따른 후속 영역/포장 판단이다.

## 확보한 수치

| 항목 | 값 | 상태 |
|---|---:|---|
| A05 train 예약 | 69 files / 10,350 records | 예약 snapshot |
| 현존 A05 train source | v01~v69 / 69 files / 10,350 rows | source 확보 완료 |
| A05 신규 생성 | v11~v69 / 59 files / 8,850 records | 생성 완료; v02~v10은 기존·보완 파일 |
| A05 registry | v01~v69 / 10,350 locators | coverage 100%; audited_source_only |
| A05 source validation | 0 files | 이번 범위에서 생성하지 않음 |
| A05 v01 최소 감사 | hard 0 / direct rewrite 0 / ChatGPT queue 3 | 완료 |
| A05 최종 source 감사 | 69 files / 10,350 rows; structural·relations·literal·registry 모두 PASS | 완료; source-only |
| A05 최종 token 평균 | 19.952173913 (206,495 tokens, 독립 regex) | 완료 |
| A05 최종 primary+은/는 | 1,702/10,350 = 16.4444%; 파일별 최대 v05 33.3333% | gate 통과; v05 diversity review 신호 |
| A05 최종 중복·조사 | exact/normalized duplicate 0; 결정적 조사 suspect 0 | 완료 |
| A05 최종 reviewer queue | hard 0 / direct 0 / ChatGPT 46 / user 0 | 의미 검토 신호만 잔존 |

## 2026-09-11 재감사·재수정 세션 (사용자 재지침)

- 사용자 지침: A05 source v01~v69만 대상으로 구조·자연성 advisory를 재감사하고, 명확한 의미 오류만 locator별 직접 재서술한 뒤 전수 재감사한다. 다른 영역 source, package train/val, manifest, checkpoint, 중앙 원장, 공용 감사기는 수정하지 않는다.
- 수정 전 snapshot: 69 files / 10,350 rows / 모든 파일 150행. source set SHA-256 `13ed6bf9cce2929c4a6460c3b5796b150843dcb5a01217b3f8615910c54763f1` (파일별 SHA는 재감사 JSON에 보관). 기존 정본 source-set SHA 표기 `c33b5f265f6be8cee626853fdfed26518655c1a1bf5b16e79f5be1b6f00a82e1`과 계산 방식 차이는 병기하고, 재감사 실행값을 기준으로 전후 비교한다.
- reviewer-assist 재감사 실행: `audit_stage2_primary_reviewer_assist.js --area A05`로 대상 selector를 고정했다. 결과는 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_PreRewrite_2026-09-11.json`에 보존한다.
- 현재 재감사 상태: source 수정 전. hard 0, primary+은/는 1,702/10,350 (16.4444%), ChatGPT review queue 45, user queue 0. 동일 relation-set·masked similarity와 반복 5어절은 의미 검토 신호로 분리한다.
- 이어받을 지점: warning/group별로 실제 의미가 성립하는지 판정하고, 명확한 의미 결손·부자연 문구만 해당 locator를 직접 재서술한 뒤 source set SHA와 전체 gate를 다시 계산한다.

## 2026-09-11 재감사·재수정 완료 (사용자 재개)

- 대상 범위는 A05 `stage2_(15)modality_possibility` train source v01~v69로 고정했다. 69 files / 10,350 records / 파일당 150행을 전후 동일하게 확인했다. 다른 영역 source, package `train/`·`val/`, manifest, checkpoint, 중앙 작업원장, 공용 감사기는 수정하지 않았다.
- 수정 전 source-set digest: 독립 `13ed6bf9cce2929c4a6460c3b5796b150843dcb5a01217b3f8615910c54763f1`, reviewer `c33b5f265f6be8cee626853fdfed26518655c1a1bf5b16e79f5be1b6f00a82e1`. 수정 후: 독립 `392a816ecfb76502a6ca3984e789a4e6a3a1d01545df5789537089890afef1`, reviewer `564538fe0c1a91e9444bf7b88a5a3c59597defab3fd0836a1c3088f4856d49e4`. 독립 digest는 정렬 `filename|file_sha256\\n` 방식이며 reviewer digest와 계산법이 다르다. 파일별 SHA는 독립 재감사 JSON에 보존했다.
- 명백한 표면·문법 오류는 locator별로 직접 재서술한 **87행**(v01 12, v02 35, v04 15, v06 25)이다. `other`가 포함된 3,333행에는 누락된 `other_type`만 추가했다. primary·relations·행 순서·registry locator는 보존했다.
- hard gate는 error 0으로 PASS: BOM·공백행·제어문자·JSON parse, 빈 primary/text, primary literal 누락, 통제어휘 위반, relation cardinality/내부 중복, `other_type` 누락·불필요 추가, train unseen_relation, 허용 key 위반이 모두 0이다.
- 후속 수치: relation occurrence 31,050회; `is_a 0`, `subclass_of 0`, `part_of 38`, `classification 924`, `boundary 4,231`, `contrast 1,590`, `comparison 2,924`, `function 745`, `role 1,710`, `process 4,698`, `state 7,380`, `attribute 3,477`, `other 3,333`. `other_type` 상위 5개는 확률·확신 1,033, 가정·반사실·조건부 결과 635, 계획·예정·예측 606, 정보 부족·불완전 관측 534, 가능성·실제 발생·미발생 525이다.
- 독립 token 총량/평균은 206,566 / 19.958067633 tokens/record이다. primary/text exact·정규화 중복은 0이다. primary+은/는 시작은 1,717/10,350=16.5894%이며 전체 임계 미만, v05만 33.3333% 파일 review 신호다. 동일 X1·상이 X2는 1 group/2행, 동일 X2·상이 X1은 12 groups/85행이다.
- 반복 5어절은 2회 이상 기준 10,889종/119,924 assignments, 기존 고빈도(≥150) 비교 기준 30종/5,850 assignments이다. reviewer similarity는 44 relation-set groups·818,692 후보·119 oversized bucket, raw/masked word-Jaccard 166,087/522,111쌍, raw/masked char TF-IDF 18,541/34,146쌍이다. 독립 scikit-learn char TF-IDF 전수 대조는 22,043쌍, 최고 .968091583이다. 방법이 다른 수치를 합산하지 않는다.
- 자연성 advisory 최종 상태는 HOLD다. 독립 의미 패턴에서 counterfactual_marker 195, generic_condition_model 195, scope_undefined 50, motion_explanation 49, 총 489행을 사용자 검토표에 남겼다. reviewer rule-warning 0은 규칙 범위 한계이며 자연성 PASS가 아니다. 사용자가 지적한 v16:4 `열차 출입문 조건부 결과`도 조건·대안·경로·행위자가 정의되지 않아 임의 의미를 발명하지 않고 보류했다.
- 산출물: `audit_reports/TinyLM_Stage2_A05_ModalityPossibility_Train_Consolidated_Audit_2026-09-11.md`, `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Independent_Reaudit_2026-09-11.json`, `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_UserReview_2026-09-11.json`, `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_PostOtherType_2026-09-11.json`.
- 문서 반영 후 동일 selector로 reviewer-assist를 재실행해 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Final_2026-09-11.json`을 추가 확인했다. reviewer SHA `564538fe...`·69 files·10,350 rows·hard 0·ChatGPT queue 45·registry coverage 100%으로 문서 수치와 일치한다. 독립 scikit-learn TF-IDF도 10,350 records·22,043쌍·최고 .968091583을 재확인했다.
- 최종 상태: **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**. 다음 재개 지점은 사용자 검토표의 의미 승인 후 해당 locator만 직접 재서술하고 같은 전수 감사를 재실행하는 것이다. package·checkpoint 생성/수정은 이 작업 범위에 없다.

## 2026-09-14 자연성·의미 직접 재서술 재개

- 대상은 계속 A05 train source v01~v69뿐이며, 다른 Stage2 source, package `train/`·`val/`, manifest, checkpoint, 중앙 원장 및 공용 감사기는 수정하지 않았다.
- 명확한 qualifier 역할 충돌·무의미한 기록 경로 문구가 확인된 **98행**만 `apply_patch`로 직접 재서술했다. v20 반례 조건·가정 범위 24행, v12 도입부 다양성 64행, v13 발생 징후/발생 여부 2행, v21 냉동 차량 적재·상자 중심 온도 징후/발생 여부 4행, v69 가정 결과/가정 범위 4행이다. primary, relations, 행 순서와 registry locator는 이 묶음에서 보존했다.
- v12의 `primary+은/는` 도입은 109/150(72.6667%, HARD HOLD)에서 45/150(30.0000%)로 내려갔다. 전체 A05는 1,633/10,350(15.7778%)이며 HOLD 파일은 없고 v04·v05만 파일 단위 diversity review다.
- 최종 reviewer-assist 재감사(`...SemanticPairs_r2_2026-09-14.json`)는 69 files / 10,350 records, hard source error 0, registry coverage 100%, direct rewrite target 0, ChatGPT review 44 groups(HARD 0), warning rule assignment 0을 확인했다. reviewer source-set SHA-256은 `38a9929f5aad0189c24f8e5ec3780837b4576be19daed7c5eae6c0d91435dc0e`다.
- 독립 char 3~5-gram TF-IDF는 19,655 pairs >= .72, 최고 .9540336945626448을 보고했다. 최고 잔여 쌍은 v59:25/145의 `운전자 교대 가정 결과`/`가정 범위`이며, 유사도 신호만으로 자동 수정하지 않고 다음 수동 의미 판정 locator로 남겼다.
- exact/NFKC primary·text duplicate는 0이지만 primary-masked exact duplicate는 2,416 groups / 8,294 records로 남는다. 이는 아직 대량 문형 반복이 있다는 증거이므로 **구조 PASS와 별도로 자연성 HOLD를 유지**한다. package·학습용 확정은 하지 않는다.

## 2026-09-14 조건·사건 의미 재서술 후속 묶음

- 대상은 계속 A05 source와 A05 registry locator뿐이다. `apply_patch`로 source 행을 직접 고쳤고, primary가 바뀐 locator만 registry의 원본 바이트를 보존하는 범위 내에서 동기화했다. 다른 Stage2 source, package `train/`·`val/`, manifest, checkpoint, 중앙 원장, 공용 감사기 및 Git은 수정하지 않았다.
- v36에서는 1~120 및 136~150의 **135행**을 재검토했다. `조건부 결과`, `가정 결과`, `반사실 경로`, `대안 결과`처럼 조건·측정변수 없이 생성된 라벨을 실제 조건과 측정값이 보이는 표현으로 바꿨다. 121~135의 구체적인 반례형 조건 문장은 유지했다.
- v66에서는 1~60, 61~75, 91~105의 **90행**을 재검토했다. `청정도 발생`, `수율 발생`처럼 상태값을 사건처럼 만든 primary를 `입자 수 기준 초과`, `수율 저하`, `공정 압력 이상`, `공급 중단`, `통신 오류` 등 실제 사건으로 바꾸고, 징후·잠정 판정·미발생 판정·발생 여부의 근거를 서로 분리했다. v66의 76~90과 106~150은 아직 이 묶음에서 재서술하지 않았으므로 다음 수동 검토 대상으로 남긴다.
- v16:29/89는 같은 `열차 위치 가정/가상 결과` 문형을 각각 위치 신호 30초 지연과 GPS 위치 오차 50미터 가정으로 분리했다.
- 이 묶음의 수정 전 기준 reviewer source-set SHA-256은 `517f80424ba2bd3d02a1380b097c54d67e94867c9b4d8dfea7003242a0b65073`이고, 수정 후 reviewer source-set SHA-256은 `590987f0c9e28ff5014d3c258e6c9ca58e67f11c7f80a3521d8146a89b79f364`이다. 현재 registry SHA-256은 `8bbf9bdbe7e313af566bfbe3832ef942f1ec9fa83cf1024f0e946c8c04e18948`이다.
- r9 reviewer-assist는 69 files / 10,350 records, hard source error 0, registry parse problem 0, coverage 100%, `primary+은/는` 1,795/10,350(17.3430%), direct target 0, ChatGPT review 45 groups(HARD 0), advisory warning record 0을 확인했다. advisory warning 0은 자연성 PASS가 아니다.
- 독립 char 3~5-gram TF-IDF는 17,411 pairs >= .72, 최고 .9485822473331011을 보고했고, 다음 최고쌍은 v32:29/149의 `조사 표본 가정 결과`/`가정 범위`다. 따라서 현재 판정은 여전히 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: v66 76~90과 106~150을 사건·미확정·확인 기준·미실행 행동으로 문맥별 재서술하고 registry locator를 동기화한 뒤, v32:29/149부터 독립 유사도 최고쌍을 계속 직접 판정한다.

## 2026-09-14 조건·사건 재서술 연속 검토 (r13)

- 범위는 계속 A05 train source v01~v69와 primary가 바뀐 A05 registry locator뿐이다. 다른 Stage2 source, package `train/`·`val/`, manifest, checkpoint, 중앙 원장, 공용 감사기 및 Git은 수정하지 않았다.
- 수정 전 기준선은 reviewer r9 source-set SHA-256 `590987f0c9e28ff5014d3c258e6c9ca58e67f11c7f80a3521d8146a89b79f364`, registry SHA-256 `8bbf9bdbe7e313af566bfbe3832ef942f1ec9fa83cf1024f0e946c8c04e18948`이다. primary **103행**과 text만 고친 **5행**을 locator별 `apply_patch`로 직접 재서술했다. primary 변경은 v66 63행, v32 2행, v54 4행, v51 30행, v11 2행, v22 2행이다.
- v66에서는 `가능 상태`·`실제 확인`·`미실행 상태`·`조건부 발생`을 실제 관측 신호, 확인 기준, 하지 않은 조치의 가정, 실제 조건문으로 바꿨다. `청정도 발생`, `수율 발생`처럼 상태값을 사건으로 만든 표현을 `입자 수 기준 초과`, `수율 저하`, `압력 이상` 등으로 바꿨고, v66의 primary+은/는 도입은 71/150(47.3333%, HARD)에서 67/150(44.6667%)로 낮췄다.
- v51에서는 온습도 센서·암모니아·이산화탄소·환기·급이·급수·점검·출하의 `발생 징후/발생 여부` 30행을 실제 이상 신호 또는 실제 판정으로 나눴다. v54·v32·v44의 가정/가상 결과와 v11의 API 게이트웨이 일정, v22의 확률 비교 중복어도 각각 구체 조건·측정값·작업 시각으로 분리했다.
- registry는 기존 invalid UTF-8 바이트를 재직렬화하지 않고, source_file/source_line/primary 바이트 범위만 대체했다. v44 동기화 때 메모리 매핑 잠금이 한 번 발생했으나 강제 종료·덮어쓰기를 하지 않았다. 원본과 self-created 백업 SHA가 같은지 확인한 뒤 한 번의 안전 재시도로 완료했고 임시·백업 파일은 검증 후 제거했다.
- r13 reviewer-assist 결과는 source-set SHA-256 `8ac228275bdc4d66fb439e319ffcbc0c54e849da68323400a14f703abe7ebf67`, registry SHA-256 `6663bc493ed1ec81bf6fa5a45b9c9993a280dc6313440c7ada196b0cae33036d`, 69 files / 10,350 records / hard source error 0 / registry parse problem 0 / coverage 100%이다. 전체 primary+은/는은 1,838/10,350(17.7585%), ChatGPT review queue 46 groups(HARD 0), user queue 0, rule-warning record 0이다.
- 독립 char 3~5-gram TF-IDF는 17,212 pairs >= .72, 최고 .9477793262865214로 r9의 17,411쌍보다 199쌍 낮아졌지만 여전히 자연성 PASS 근거가 아니다. reviewer의 same-relation-set masked group은 44개이며, raw/masked Jaccard의 최고쌍에는 v18·v22·v26·v30·v34 등의 공통 확률 문형이 남아 있다. 따라서 상태는 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: 독립 TF-IDF 최고쌍 v25:72/102 (`콘텐츠 추천 발생 징후/발생 여부`)을 먼저 행별 판정한다. 이어 v18·v22·v26·v30·v34의 확률·확신 문형은 의미가 같은지 아닌지 사람이 읽어 확정 오류 locator만 직접 재서술하고, primary 변경마다 registry locator를 다시 동기화한 뒤 r14 reviewer와 독립 TF-IDF를 재실행한다.

## 2026-09-14 r14 후속 기준선

- v25:72/102의 `콘텐츠 추천 발생 징후/발생 여부`는 추천 목록 갱신의 신호와 실제 갱신 여부로 재서술했고, primary locator 2개를 registry에 동기화했다. 이번 연속 묶음의 primary 직접 재서술 누계는 **105행**, text-only 재서술은 **5행**이다.
- r14 reviewer-assist: source-set SHA-256 `602202544d5dc20ec6d4a42f4f8efc096b5a7555af3114cfbbe94ecab2bf0929`, registry SHA-256 `9534516038ecb49f1ddb772d6b6d8bab5156309d116a4cee13eb63722397ff4b`, 69 files / 10,350 records / hard source error 0 / registry parse problem 0 / coverage 100%이다. primary+은/는은 1,839/10,350(17.7681%), ChatGPT review 46(HARD 0), user review 0, rule-warning record 0이다.
- r14 뒤 독립 char 3~5-gram TF-IDF는 17,205 pairs >= .72, 최고 .9478066196056428이다. source 구조는 PASS지만 대량 문형 재사용 때문에 자연성은 계속 HOLD다.
- 다음 재개 지점: v28:27/147의 `콘텐츠 추천 가정 결과/가정 범위`를 실제 조건과 서로 다른 해석 범위로 분리한다. 그 뒤 v18·v22·v26·v30·v34의 확률·확신 high-similarity 군을 같은 locator 단위로 계속 판정한다.

## 2026-09-14 r15 후속 기준선

- v28:27/147은 개인화 추천의 하루 지연 가정과 추천 기준 변경 범위로 고쳤고, primary 변경 누계는 **107행**, text-only 재서술은 **5행**이 됐다.
- r15 reviewer-assist: source-set SHA-256 `234a28b471898ceee693ac1622e1fe7e50baac9502ad557bfcd54b8263a18e46`, registry SHA-256 `d7af283670669d6b91a7ec4e6882e64ec06aa0c673b19d337ff8e37d15a0e676`, 69 files / 10,350 records / hard source error 0 / registry parse problem 0 / coverage 100%이다. primary+은/는은 1,840/10,350(17.7778%), ChatGPT review 46(HARD 0), user review 0, rule-warning record 0이다.
- 독립 char 3~5-gram TF-IDF는 17,199 pairs >= .72, 최고 .9476049050272134이다. 구조 PASS와 자연성 HOLD를 계속 분리한다.
- 다음 재개 지점: v54:17/137의 `웨이퍼 수율 가정 결과/가정 범위`를 각각 구체 반사실 조건과 해석 범위로 판정한다. 이후 v18·v22·v26·v30·v34의 확률·확신 high-similarity 군을 locator별로 이어서 검토한다.

## 2026-09-14 r16~r24 잔여 고유사 쌍 직접 재서술

- r15 기준선 뒤 primary를 직접 재서술한 누계는 **125행**, text-only 재서술은 **5행**이다. 이번 묶음에서는 v54:17/137, v25:62/92·73/103, v32:19/139, v28:20/140·29/149·17/137, v46:72/102, v16:16/136의 **18행**을 각각 다른 실제 조건·관찰 근거·판정 범위로 분리했다. 같은 primary를 다른 행에 기계적으로 치환하지 않았고, source 행 순서·relations·other_type은 보존했다.
- 변경 예시는 `웨이퍼 수율 가정 결과/범위`를 검사 표본 절반 가정의 수율 추정과 수율 해석 조건 범위로, `퀴즈 정답률 발생 징후/여부`를 초기 표본의 변화 신호와 충분한 응답에 의한 변화 확인으로, `산림 통행 발생 징후/여부`를 통행 흔적과 통행 여부 확인으로 나눴다. 상태량·설정값을 사건처럼 부른 primary와 같은 text를 공유하던 qualifier 쌍만 확정 오류로 처리했다.
- primary가 바뀐 A05 registry locator만 원본 바이트 범위에서 동기화했다. 매 교체는 이전 registry SHA-256을 precondition으로 확인하고 source_file/source_line/old primary가 정확히 하나인 경우에만 수행했다. 메모리 매핑 재시도는 없었고, self-created temp/backup은 성공 검증 뒤 모두 제거했다.
- r21 reviewer 실행의 첫 호출은 registry 상대경로 오기로 source·registry·report 생성 전에 중단됐다. 올바른 A05 registry 경로로 즉시 재실행했으며, 이후 r21~r24 보고서만 감사 산출물로 남겼다.
- r24 reviewer-assist: source-set SHA-256 `a5409d0e5bc42f46d604d7d5218c1ce8afab1a34f71ee21d0831bae37d47ae19`, registry SHA-256 `dcbed255729695b5aa9f912f093ce8cc6d36932180c7b3a3ba6464e68deb0273`, 69 files / 10,350 records, hard source error 0, registry parse problem 0, coverage 100%이다. `primary+은/는`은 1,849/10,350(17.8647%), ChatGPT review 46(HARD 0), user review 0, rule-warning record 0이다.
- r24 뒤 독립 char 3~5-gram TF-IDF는 17,137 pairs >= .72, 최고 .9459608482172597이다. r15의 17,199쌍보다 62쌍 낮았지만 높은 유사도와 primary-masked 반복이 광범위하게 남았으므로 판정은 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: v44:29/149의 `부표 점검 가정 결과/가정 범위`를 실제 점검 조건의 반사실 추정과 적용 조건 범위로 분리한 뒤, 독립 TF-IDF 최고쌍을 같은 방식으로 locator별 재판정한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 계속 수정하지 않는다.

## 2026-09-14 r25~r28 잔여 사건·측정값 문형 재서술

- 이번 후속 묶음에서는 v44:29/149, v61:62/92·72/102, v46:62/92의 **8행**을 행별로 재검토했다. `부표 점검 가정 결과/범위`는 점검 주기 변경 아래의 센서 이상 발견 시점 추정과 점검 결과 해석 조건 범위로, `랙 열부하 발생 징후/여부`는 급증 신호와 다중 계측 확인으로, `정전 복구 발생 징후/여부`는 복구 시작 신호와 완료 확인으로, `포획 트랩 발생 징후/여부`는 유인 트랩의 곤충 포획 흔적과 포획물 확인으로 바꿨다.
- r15 이후 primary 직접 재서술 누계는 **133행**, text-only 재서술은 **5행**이다. 이번 수정도 locator별 `apply_patch`만 사용했고, source 행 순서·relations·other_type은 보존했다. primary 변경 registry locator는 원본 바이트의 정확한 `primary` 구간만 교체했으며, 모두 SHA-256 precondition·후속 hash 대조·coverage 재감사를 통과했다. temp/backup 파일과 retry는 없었다.
- r28 reviewer-assist: source-set SHA-256 `96c53cbe0cff13fcbf201012b4b615899d0103625642b0dbcfd2fdf94bde0bf1`, registry SHA-256 `5bbcd85e973203014d7c0b3f89dd9aa4b7820fb595d209db9d7d86014f03c8fb`, 69 files / 10,350 records, hard source error 0, registry parse problem 0, coverage 100%이다. `primary+은/는`은 1,854/10,350(17.9130%), ChatGPT review 46(HARD 0), user review 0, rule-warning record 0이다.
- r28 뒤 독립 char 3~5-gram TF-IDF는 17,108 pairs >= .72, 최고 .9444936998400334이다. 이는 r24의 17,137쌍보다 29쌍 낮지만, 모든 고유사 pair가 오류라는 뜻은 아니며 대량 문형 반복이 남아 있다. 현재 판정은 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: v61:63/93의 `UPS 전환 발생 징후/발생 여부`를 UPS 전환의 초기 신호와 실제 전환 확인으로 의미 분리한다. 이후에도 독립 TF-IDF 최고쌍을 한 쌍씩 읽고, 명확한 오류 locator만 직접 재서술·registry 동기화·전수 재감사한다.

## 2026-09-14 A05 전체 자연성 직접 재서술 착수

- 사용자 지시: A05 전체 데이터셋의 자연성 수정 작업을 수행한다. 허용 범위는 A05 `modality_possibility` train source v01~v69, primary가 바뀐 A05 registry locator, A05 감사 산출물 및 이 A05 전용 원장으로 고정한다.
- 시작 기준은 r28 reviewer source-set SHA-256 `96c53cbe0cff13fcbf201012b4b615899d0103625642b0dbcfd2fdf94bde0bf1`, registry SHA-256 `5bbcd85e973203014d7c0b3f89dd9aa4b7820fb595d209db9d7d86014f03c8fb`, 69 files / 10,350 records, hard source error 0, registry coverage 100%이다. 이 구조 PASS는 자연성 PASS가 아니다.
- 전수 후보를 concept·문장 의미로 분류하고, 인공 합성어·상태를 사건으로 부르는 표현·정의 없는 조건/반사실·불투명한 기록 문구·template 반복 때문에 의미가 확정적으로 손상된 locator만 `apply_patch`로 직접 재서술한다. 전역 치환·문장 자동생성·source 전체 재직렬화는 사용하지 않는다.
- primary가 바뀌면 해당 registry locator만 원본 바이트를 보존하여 동기화한다. source 행 순서, relations, other_type과 보호 경계는 보존한다. 매 묶음 뒤 A05 selector 구조/registry/중복/조사/유사도/자연성 감사를 재실행한다.

## 2026-09-14 v61 데이터센터 냉각·전력 절체 1~90행 직접 재서술

- r29 전체 후보 감사에서 primary를 가린 exact text 골격이 2,157 groups / 7,320 records였고, 독립 char 3~5-gram TF-IDF는 17,108 pairs >= 0.72 / 최고 0.9444936998400334였다. 이는 구조 오류가 아니라도 대량 template 재사용과 자연성 HOLD를 뒷받침하는 재작성 우선순위다.
- v61의 1~90행에서 `유량 발생`, `온도 발생`, `가능 상태`, `잠정 발생`, `미발생 판정`처럼 상태·측정값을 사건으로 만든 primary와 text를 실제 이상 가능성·관측 가능성·잠정 판정·미확인·신호·위험도·필요성으로 직접 분리했다. 이 묶음은 primary 86행, text-only 3행이며, 이전 r28의 v61:62·72 재서술은 보존했다. v61:63은 `UPS 전환 준비 신호`, v61:93은 `UPS 전환 완료 확인`으로 먼저 분리했다.
- 모든 primary 변경 locator는 registry 바이트 범위만 교체했다. 1~30행 registry 동기화의 첫 사후 검증은 변경 전 byte offset을 재사용해 중단됐지만, live registry와 self-created temp의 SHA-256 일치, self-created backup의 수정 전 SHA-256 일치, 27/27 locator 실제 값을 read-only 재검증한 뒤 temp/backup만 제거했다. registry를 되돌리거나 다른 파일을 수정하지 않았다. 이후 31~60 및 61~90 동기화는 새 live byte range로 검증해 정상 완료했다.
- r33 reviewer-assist: source-set SHA-256 `06e613756ea2ad5c3146879fdb6762280d14e48767b63e6ba30728dfeef54fe1`, registry SHA-256 `2ecdc3cf49809810b8513a6388afe231c2bc02092067c06b2e70dd2c6f87b469`, 69 files / 10,350 records, hard source error 0, registry parse problem 0, coverage 100%, primary+은/는 1,879/10,350 (18.1545894%), ChatGPT review 47 (HARD 0), user review 0, rule warning 0이다.
- r33 뒤 독립 char 3~5-gram TF-IDF는 16,866 pairs >= 0.72 / 최고 0.944341640274376이다. 17,108쌍보다 242쌍 줄었지만 자연성 PASS 근거는 아니며, A05 전체 상태는 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: v61 91~150행을 실제 판정·현장 확인·미실행 조치·조건으로 재서술하고 primary 변경 registry locator를 동기화한다. 그 뒤 r33 최고 유사도인 v69:20/140과 잔여 exact masked template 군을 version별로 직접 판정한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 계속 수정하지 않는다.

## 2026-09-14 v69 병원 수술실 배정·감염관리 1~15행 직접 재서술

- r35 기준선 뒤 v69 1~15행의 `조건부 결과` 합성어를 실제 의료 운영에서 이해 가능한 조건문으로 바꿨다. 예를 들어 수술실 배정 기준 변경, 격리 조치 미실시의 감염 위험, 멸균 확인 단계 추가, 병상 회전 지연, 예방 항생제 투여 지연처럼 조건·대상·예상 결과가 드러나는 primary와 text로 각각 직접 재서술했다.
- source는 `apply_patch`로 locator 15개만 수정했으며 행 순서·relations·other_type은 보존했다. 수정 뒤 v69 파일의 150행·JSONL·primary literal·relations cardinality·13개 통제어휘·전역 primary 고유성을 검사하여 오류 0을 확인했다. source SHA-256은 `B25ECD17FB5FEC0B158D6C8BFCF9FF51101B568747345CDF01573376C6BC8CDC`이다.
- primary가 바뀐 registry locator 15개만 원본 바이트 범위로 동기화했다. 수정 전 registry SHA-256 `647035BEF3E7CB227AB9953F4E1B8DB80D165C4A3B540DF70D007BC09F3A3477`, 수정 후 `ED59079D334563282D5B0371FC1B227E79BDDBFE531CF2A57A2C612553D6AD13`이며, v69 registry 150행 중 해당 15 locator의 source-primary 일치를 다시 확인했다. self-created temp/backup은 후속 hash 확인 뒤 제거했다.
- 다음 재개 지점: v69 16~150행에서 `가정 결과`·`반사실 경로`·`대안 결과`·`미실행 결과`·`가상 결과`·`가정 범위`의 인공 합성어와 반복 골격을 같은 방식으로 행별 직접 재서술한다. 전체 v69 완료 뒤 A05 selector 재감사와 독립 유사도 검사를 실행한다.

## 2026-09-14 v69 병원 수술실 배정·감염관리 전체 직접 재서술 및 재감사

- v69의 150행을 전수로 읽었다. 121~135행은 병상·격리·수술 준비의 실제 반례를 자연어로 설명하고 있어 보존했고, 27행도 `감염관리 경보가 울렸을 때의 대응 인력 수`라는 구체 조건문이라 보존했다. 나머지 **134개 primary**와 해당 text는 `조건부 결과`, `가정 결과`, `반사실 경로`, `대안 결과`, `미실행 결과`, `가상 결과`, `조건 변경 전망`, `대체 경로 예상`, `가정 범위` 같은 불투명한 합성어 대신 실제 조치·전제·예상 시점·조건 목록으로 각각 직접 재서술했다.
- primary가 바뀐 registry locator 134개만 source_file/source_line/old primary의 단일 일치를 먼저 확인한 뒤 원본 바이트 범위로 교체했다. 76~90행 교체는 다른 프로세스의 일시 매핑 때문에 첫 복사에서 거부됐지만 live registry가 수정 전 SHA와 같음을 확인한 뒤 한 번의 짧은 재시도로 성공했다. 136~150행 교체는 사후 hash 인자 오타 뒤 live=temp SHA와 15 locator 일치를 read-only로 확인했고, 모든 self-created temp/backup은 검증 후 제거했다. 강제 종료·전역 재직렬화·다른 파일 수정은 하지 않았다.
- v69 source 최종 SHA-256은 `CF5C2583F31A4CDFF80D9D4129489DFB90691C83DB4AAACED95E0CA312699AE1`, A05 registry 최종 SHA-256은 `B36B4302E75E38BCBF11E212E46E88243B2C8106712107551159E87E90C1DC97`이다. v69은 150행, JSONL parse·BOM·공백행·제어문자·primary literal·relations cardinality/통제어휘·global primary duplicate·registry 150 locator 모두 오류 0이다.
- r36에서 v69 `primary+은/는` 도입이 79/150(52.6667%)로 HARD였으므로, primary는 그대로 두고 의미가 유지되는 12 text를 조건·근거로 시작하도록 직접 재서술했다. r37에서 v69은 67/150(44.6667%, REVIEW_DIVERSITY)로 HARD 해제됐다. A05 전체 r37은 69 files / 10,350 records, hard source error 0, registry parse problem 0, coverage 100%, primary+은/는 1,907/10,350(18.4251%), ChatGPT review 48(HARD 0), user review 0, rule-warning record 0이다.
- r37 뒤 독립 char 3~5-gram TF-IDF는 16,686 pairs >= 0.72, 최고 0.9439990149483909이며 최고쌍은 v16:21/81의 `철도 승객 안내 가정 결과/가상 결과`다. r35의 16,843쌍보다 157쌍 줄었지만, 구조 PASS·HARD 해제는 A05 전체 자연성 PASS가 아니며 상태는 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: 독립 최고쌍 v16:21/81부터 v16 철도 운행 간격·환승 조정 source를 전수로 읽고, 같은 기준으로 불투명한 반사실/가상 합성어와 의미상 오류만 locator별 직접 재서술한다. 전체 A05 69 version의 전수 검토와 마지막 전수 감사가 끝날 때까지 package·checkpoint·manifest·중앙 원장·다른 영역 source는 수정하지 않는다.

## 2026-09-14 v16 철도 운행 간격·환승 조정 전체 직접 재서술 및 재감사

- r37 독립 TF-IDF 최고쌍(v16:21/81)을 시작점으로 v16 150행을 전수로 읽었다. 121~135행은 실제 철도 운영의 반례 설명이라 보존했고, 출입문·GPS의 구체 조건문 등 이미 자연스러운 28행도 보존했다. 나머지 **122개 primary**와 해당 text는 `조건부 결과`, `가정 결과`, `반사실 경로`, `대안 결과`, `미실행 결과`, `가상 결과`, `조건 변경 전망`, `대체 경로 예상`, `가정 범위`의 템플릿형 합성어 대신 배차·승강장 통제·신호기 통신·급전 전환·역무원 배치·회차 선로·냉방의 구체 조치와 전제로 직접 재서술했다.
- primary가 바뀐 A05 registry locator만 원본 바이트 범위에서 동기화했다. v16:91~105는 첫 복사 시 일시 매핑으로 거부됐으나 live registry가 수정 전 SHA와 같음을 확인한 뒤 한 번의 짧은 재시도로 성공했다. 모든 동기화는 source_file/source_line/old primary의 단일 일치, source-primary 대조, live=temp SHA, self-created backup의 수정 전 SHA를 확인했고 temp/backup은 검증 후 삭제했다.
- v16의 첫 구조 검사에서 line 3 `primary literal` 누락 1건을 발견했다. registry primary는 이미 정확했으므로 source text만 직접 보완했고, 이후 r38 전체 auditor는 69 files / 10,350 records, hard source error 0, registry parse problem 0, registry coverage 100%를 확인했다. r38 source-set SHA-256은 `492458550a29b49ec9998fdd203acff659bab5af703631dd1e0cd29c9b2019c2`, registry SHA-256은 `BA797FE37B6AD72899B607D214CAFA44B07DE40887DF9319B84F32248D47C51A`이다.
- r38의 v16 `primary+은/는`은 52/150(34.6667%, REVIEW_DIVERSITY)이고, A05 전체는 1,938/10,350(18.7246%), ChatGPT review 49(HARD 0), user review 0, rule-warning record 0이다. 독립 char 3~5-gram TF-IDF는 16,543 pairs >= 0.72, 최고 0.9435935295777752이며 최고쌍은 v56:72/102의 `해상 운항 발생 징후/발생 여부`다. 따라서 A05는 여전히 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: v56 해양 부표 관측·경보 운영 source를 전수로 읽고, 최고쌍의 `발생 징후/발생 여부`를 실제 신호와 실제 확인으로 우선 분리한다. 이후 동일 기준으로 잔여 version과 최종 전수 감사를 계속한다.

## 2026-09-14 v59 전기버스 충전·배차 전체 직접 재서술 및 재감사

- v59의 150행을 전수로 읽었다. 121~135행의 구체적인 반례 문장은 보존하고, 나머지 **135개 primary**와 해당 text에서 `조건부 결과`, `가정 결과`, `반사실 경로`, `대안 결과`, `미실행 결과`, `가상 결과`, `조건 변경 전망`, `대체 경로 예상`, `가정 범위` 같은 내부 분류 라벨을 실제 운행 조건·예상 수량·미실행 위험·운영 계획·계산 전제로 직접 재서술했다. 행 순서·relations·other_type은 보존했다.
- 수정 전 v59 SHA-256은 r38 source-file snapshot의 `3199c413fe535f580ce5e21f6fa166961e63a5b5e7295aebd4910406cb7b0d81`이고, 수정 후 `2c0b8a6adec28f35f78561b1cb168bcedfb0d219f8ff07bcb05a3116bb9c173b`이다. 이번 작업 시작 전 A05 sorted-name source-set digest는 `a4f5ba20da4a53ccd24361b438d13c3be6208b966ba85f2ff7fafa9ca3d86e6b`, 수정 후는 `a842aedb3416acf4c67ac8d41b679d37c510b74238017611aaa4fd217b1e6eb1`이다. 이 digest는 reviewer의 source-set digest와 계산 방식이 다르므로 서로 대체하지 않는다.
- primary가 달라진 locator 135개만 registry 원본 바이트의 `primary` 범위를 교체했다. 시작 registry SHA-256 `ba797fe37b6ad72899b607d214cafa44b07de40887df9319b84f32248d47c51a`, 완료 후 `873cacfccaa2c7c938788094c1657e6a493e727f314e13e95b9a9850c62b9d22`이다. 각 15행 묶음은 source_file/source_line/old primary 단일 일치·live/temp SHA·self-created backup SHA를 확인했으며, v59 locator 150개가 source primary와 모두 일치하고 temp/backup 0개임을 재확인했다.
- v59 단일 파일 감사는 150행, JSONL parse·BOM/공백행·primary literal·2~5 relations·13개 통제어휘·other_type 조건·primary/text 중복·금지 라벨 primary/text 모두 오류 0이다. `primary+은/는` 도입은 2/150이다.
- r39 reviewer-assist는 reviewer source-set SHA-256 `67f8edffe0a8296148e18d3ba0b61bd0b9de5c468e87a2ec9753b3eb52a51a42`, 69 files / 10,350 records, hard source error 0, registry parse problem 0, coverage 100%, 전체 `primary+은/는` 1,890/10,350(18.2608696%), ChatGPT review 48(HARD 0), user review 0, naturalness rule warning 0을 기록했다. 보고서는 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r39_v59_complete_2026-09-14.json`이다.
- r39 뒤 독립 char 3~5-gram TF-IDF는 16,446 pairs >= .72, 최고 0.9437650010187246이며 최고쌍은 v56:72/102의 `해상 운항 발생 징후/발생 여부`다. 수가 r38의 16,543쌍보다 97쌍 줄었지만, 이 수치와 구조 PASS는 A05 전체 자연성 PASS 근거가 아니다. 상태는 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: v56 해양 부표 관측·경보 운영을 전수로 읽고, 최고쌍의 관측 신호와 실제 발생 확인을 우선 분리한다. 이어 잔여 version의 masked template 군을 같은 locator 단위로 판정한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 계속 수정하지 않는다.

## 2026-09-14 v56 해양 부표 관측·경보 운영 전체 직접 재서술 및 r40 재감사

- r39 기준 v56 source SHA-256 `7012cd200aacca7bc5bbe41a9d9c5007eb09f707970bc6f903ebf5fe143d26de`에서 시작했다. 1~60행의 실제 관측·신호·판정 문장을 보존한 뒤, 61~150행의 `발생 징후`, `가능 상태`, `발생 여부`, `실제 확인`, `미실행 상태`, `조건부 발생` 내부 라벨을 관측 신호, 실제 확인 기록, 재측정·상호 검증, 미조치의 판단 한계, 구체 조건문으로 행별 직접 재서술했다. v56의 최종 source SHA-256은 `8b2c1c2f230fa2c968552e2e1fdff731dfb89e4d4984658017356175cc25ce81`이다.
- 단일 파일 구조 검사에서 처음 발견한 primary literal 누락 2건(130·136행)과 v56 내부 primary 중복 3건(81·82·86행)을 직접 교정했다. 최종 v56은 150행, UTF-8 BOM 없음, JSONL parse, 빈 필드, primary literal, 13개 통제 relations·2~5 cardinality·내부 중복, `other_type` 조건, train `unseen_relation`, primary/text exact duplicate, 금지 내부 라벨이 모두 오류 0이다. 자체 조사 패턴은 14/150(9.3333%)이며 reviewer-assist의 더 좁은 `primary+은/는` 계수는 12/150(8.0000%)다.
- primary가 달라진 locator만 15행 묶음으로 A05 registry 원본 바이트 범위에서 동기화했다. r39 기준 registry SHA-256 `873cacfccaa2c7c938788094c1657e6a493e727f314e13e95b9a9850c62b9d22`에서 시작해 최종 `68421ce0c9583bca2a6301f08ab08eed5a8bca027a668c9199c9c798eb2d9f44`이며, v56 150개 locator의 source-primary 대조 오류는 0이다. self-created temp/backup은 hash·locator 확인 뒤 모두 제거했다.
- r40 A05 selector 감사 보고서 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r40_v56_complete_2026-09-14.json`은 69 files / 10,350 records, hard source error 0, registry parse problem 0, coverage 100%, 전체 `primary+은/는` 1,872/10,350(18.0869565%), naturalness warning 0, direct rewrite target 0, ChatGPT review pending 48(HARD 0), user review 0을 기록했다. reviewer source-set SHA-256은 `b87727e91b36e72728528d91350ea37c74b2da931fe0bb7bfb9c41c0010abda8`이다.
- r40 뒤 독립 char 3~5-gram TF-IDF는 16,132 pairs >= .72, 최고 0.9436322309281469이며 최고쌍은 v47:58/148의 전기버스 정비 확률 비교 문장이다. r39의 16,446쌍보다 314쌍 낮았지만, 높은 유사도와 48개 ChatGPT review group이 남아 있으므로 A05 판정은 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: 독립 최고쌍 v47:58/148을 먼저 문맥별로 읽어 확정 오류만 직접 재서술하고, 이후 남은 masked template 군을 version별로 같은 규칙으로 검토한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 계속 수정하지 않는다.

## 2026-09-14 v47 전기버스 충전차고 전력·배차 고유사 pair 직접 재서술 및 r41 재감사

- 독립 최고쌍인 v47:58/148을 직접 읽었다. 기존 `전기버스 정비 확률 근거/비교`와 거의 같은 두 문장은 정비 대상·분모·비교 기준이 빠져 있고, 148행에는 `비교를 비교할 때`라는 중복도 있었다. 58행은 운행 차량 수와 고장 기록을 근거로 한 `전기버스 정비 수요의 추정 근거`로, 148행은 동일 운행 거리·점검 기준의 두 기간을 비교하는 `전기버스 정비 수요의 확률 비교`로 각각 분리했다.
- primary가 달라진 v47:58·148 registry locator만 원본 바이트 범위에서 동기화했다. r40 registry SHA-256 `68421ce0c9583bca2a6301f08ab08eed5a8bca027a668c9199c9c798eb2d9f44`에서 r41 `a62c44907f3b8cccef413952d5a632e712cf4bda50c90c88e1f662be9441f22d`로 바뀌었고, self-created temp/backup은 검증 후 제거했다. v47 source SHA-256은 `b27b9d3d85311d18161812dc8cafea9b75fb7cc3a507ad402c13d2c644e20500`이다.
- r41 A05 selector는 69 files / 10,350 records, hard source error 0, registry parse problem 0, coverage 100%, `primary+은/는` 1,873/10,350(18.0966184%), naturalness warning 0, direct rewrite target 0, ChatGPT review pending 48(HARD 0), user review 0을 기록했다. 독립 char 3~5-gram TF-IDF는 16,124 pairs >= .72, 최고 0.9427564265924904로 감소했으며 새 최고쌍은 v64:27/147의 `배수로 점검 가정 결과/가정 범위`다.
- 구조 PASS는 자연성 PASS가 아니므로 상태는 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다. 다음 재개 지점: v64:27/147을 구체 조건과 해석 범위로 분리하고, 이후 독립 최고쌍과 masked template 군을 locator별로 검토한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 계속 수정하지 않는다.

## 2026-09-14 v64 도로 터널 배수·교통 통제 전체 자연성 직접 재서술 — registry 잠금으로 동기화 대기

- v64 150행을 행별로 읽었다. 이미 구체적인 반례인 121~135행과 실제 통제 기준을 설명하는 139행은 보존했다. 나머지는 `조건부 결과`, `가정 결과`, `반사실 경로`, `대안 결과`, `미실행 결과`, `가상 결과`, `조건 변경 전망`, `대체 경로 예상`, `가정 범위` 같은 내부 분류 라벨을 수위·펌프·차수문·차로 통제·신호·환기·조명·대피·점검의 구체 조건, 산출 대상, 실제 확인 근거로 직접 재서술했다. source 행 순서·relations·`other_type`은 보존했다.
- v64 76~120행의 변경 primary는 source_file/source_line/old primary 단일 일치와 source-primary 대조를 확인한 뒤 registry 원본 바이트 범위만 동기화했다. 각 15행 묶음은 live SHA와 temp SHA가 같고 self-created temp/backup이 제거된 상태까지 확인했다.
- v64 136~138·140~150행 14개 primary는 source에 직접 반영되었다. 현재 v64 source SHA-256은 `8491ED43636C8F2A0901F66FDC5B85363C76AC90FDC8D2D6F20D02A59EF9256A`이다. 이 14개 locator의 registry 동기화 직전 live registry SHA-256은 `1D4B03CEBD1515AF1CA3B127C6AA1D2790EBDC0EED94468447378591F9165D88`이며, 정확한 변경 temp SHA-256은 `D85E4967437B88C80ED0A202752D54197101CB4773DE197DCF8B0D86B623A843`이다.
- registry 파일이 다른 작업에서 열려 있어 안전한 복사 시도와 5초 후 단 한 번의 재시도가 모두 거부됐다. 프로세스 종료·강제 해제·추가 쓰기는 하지 않았다. self-created `.a05-v64-136-150.tmp`와 `.a05-v64-136-150.bak`은 복구 전제를 보존하기 위해 남겨 두었고, backup SHA는 수정 전 live SHA와 일치한다. 이 시점에는 source v64 14 locator와 registry primary가 일시 불일치하므로 A05 전수 reviewer/구조 감사는 실행하지 않았다.
- 다음 재개 지점: 다른 작업이 registry 잠금을 해제한 뒤, **live registry SHA가 정확히 `1D4B03CEBD1515AF1CA3B127C6AA1D2790EBDC0EED94468447378591F9165D88`인 경우에만** self-created temp를 한 번 복사하고 14 locator의 source-primary 대조·live=temp SHA를 확인한다. SHA가 다르면 temp/backup을 적용·삭제하지 말고 상태를 먼저 보고한다. 성공 검증 후에만 self-created temp/backup을 제거하고 v64 단일 파일 감사, A05 영역 reviewer, 독립 TF-IDF/Jaccard 감사를 순서대로 재개한다. 상태는 계속 **자연성 HOLD**이며 package·checkpoint·manifest·중앙 원장·다른 영역 source는 수정하지 않는다.

- registry 잠금과 무관한 v64 text 자연성 재서술을 계속했다. 1~120행의 `text`는 각 행의 조건·계산 대상·실제 확인 근거를 유지하면서, `primary+은/는` 도입과 같은 문장 틀을 반복하지 않도록 행별로 직접 바꿨다. 121~135행 및 139행은 이미 구체적인 반례·운영 기준이어서 보존했고, 136~150행은 앞서 설명한 전제·안전 조건의 구체 문장으로 유지했다.
- 현재 v64 source SHA-256은 `2EF71ED2CF0E2B930324E96C57D95994BA6F9CBCB2F2EDA51F48DE315D801D22`이다. registry를 제외한 단일 source 구조 검사는 150행, UTF-8 BOM 없음, JSONL parse·빈 field·primary literal·relations 13개/2~5개/내부 중복·`other_type` 조건·train `unseen_relation`·primary/text exact duplicate·금지 내부 라벨 모두 오류 0이다. `primary+은/는`은 120/150(80.0000%)에서 11/150(7.3333%)로 낮아졌다. 이 결과는 **단일 source 구조 PASS**일 뿐 registry 불일치가 남은 A05 영역 전체 PASS나 자연성 최종 PASS가 아니다.

## 2026-09-14~15 v64 후속 정정, v13·v28 전체 자연성 재서술 및 재감사

- 위 v64의 남은 registry 동기화는 이후 source-primary locator 대조, live=temp SHA 대조, self-created temp/backup 제거까지 마쳐 정상 완료했다. r42 A05 selector는 69 files·10,350 records, registry coverage 100%, hard source error 0을 확인했으나 구조 PASS를 자연성 PASS로 승격하지 않았다.
- v13 철도 운행 간격·환승 조정은 150행을 전수 재검토했다. 1~120행의 관측 신호·잠정 판정·확인 절차를 실제 운행 기록과 관제 확인으로 구체화했고, 46~60행의 `미발생 판정`은 `이상이 없었다는 잠정 판단` 또는 `운행 재개를 보류하는 잠정 판단`으로 직접 재서술했다. 바뀐 primary locator만 registry 원본 바이트 범위에서 동기화했다. v13 source SHA-256은 `A02F4461F0EAF758B0C9CD3457AE31EA50E3222A38CF7A1BAF7CE941B8E2523F`이며, v13 단일 파일은 150행·BOM/공백/JSONL·primary literal·13개 통제 relations·2~5 cardinality·`other_type`·train unseen field·중복·금지 라벨·registry 150 locator 모두 오류 0이었다.
- r43 A05 selector는 69 files·10,350 records, hard source error 0, registry coverage 100%, primary+은/는 1,812/10,350=17.5072464%, direct rewrite 0, ChatGPT review 48(HARD 0), user review 0을 기록했다. 독립 char 3~5-gram TF-IDF는 15,666 pairs >= .72, 최고 .942450294였고 v28:22/82가 다음 직접 검토 대상으로 나타났다. 상태는 계속 구조 PASS / 자연성 HOLD다.
- v28 온라인 학습 진도·피드백 운영은 150행을 전수 읽었다. 이미 자연스러운 반례 121~135행과 충분히 구체적인 조건 문장 일부만 보존하고, 나머지 127개 primary/text에서 `조건부 결과`, `가정 결과`, `반사실 경로`, `대안 결과`, `미실행 결과`, `가상 결과`, `조건 변경 전망`, `대체 경로 예상`, `가정 범위`를 실제 학습 조건·예상 대상·관찰 기록·해석 조건으로 직접 바꿨다. 전역 치환·자동 문장 생성·관계 변경은 하지 않았다.
- v28의 변경 primary 127개는 15행 이하의 locator 묶음으로 registry 원본 바이트 범위만 동기화했다. 각 묶음은 이전 SHA-256 precondition, source_file/source_line anchor 단일 일치, source SHA 불변, backup SHA, live=temp SHA와 locator 대조를 통과했으며 self-created temp/backup은 제거했다. 최종 v28 source SHA-256은 `B16C7C1D9BA69A6BEB961D9A9C307F6407FA1AD3F71CEA8292AFAD3FFD5FD1EF`, 당시 registry SHA-256은 `E17BA70B3C2425FDEB5A1ED2EAABC32ACC78DC6E40BEDA7D7ED35B29B9A5E828`이다.
- v28 단일 구조 감사는 150행, BOM·공백·JSONL parse·빈 field·primary literal·relation·`other_type`·unseen field·primary/text duplicate·금지 라벨·registry locator 모두 0 오류였고 `primary+은/는` 시작은 7/150이다. r44 A05 selector는 source-set SHA-256 `bb652af0717e67d7adc22255e1cdb373cffb6dda58fd0c50a34fd07aaa15af90`, 69 files·10,350 records, hard source error 0, registry coverage 100%, primary+은/는 1,801/10,350=17.4009662%, direct rewrite 0, ChatGPT review 48(HARD 0), user review 0, warning record 0을 확인했다.
- r44 뒤 독립 char 3~5-gram TF-IDF는 15,532 pairs >= .72, 최고 .9418853330342816이며 최고쌍은 v42:46/136의 클린룸 청정도 확률 문형이다. 수치 감소와 구조 PASS는 전체 A05 자연성 PASS 근거가 아니다. 다음 재개 지점은 v42를 150행 전수 판독해 상태값을 사건처럼 부르는 표현과 확률·확신 템플릿을 의미별로 직접 재서술하고, 같은 locator 단위 registry 동기화와 전수 재감사를 수행하는 것이다.

## 2026-09-15 v42 클린룸 청정도·반도체 공정 전체 자연성 재서술 및 r45 재감사

- v42의 150행을 전수 판독했다. 121~135행의 실제 사건 가능성 문장은 유지하고, 나머지 135개 primary/text에서 상태·측정값을 사건처럼 부른 `발생 확률`, 불투명한 `가능성 수치`·`확률 근거`·`신뢰 판단`, 대상과 시점이 빠진 `확률 비교`를 입자 기준 초과, 수율 하락, 균일도 이탈, 압력 이상, 노광 불량, 공급 중단, 대기 지연 등 실제 사건·측정·비교 조건으로 각각 직접 재서술했다. 행 순서·relations·other_type은 보존했다.
- 바뀐 primary 135개는 15행 이하 locator 묶음으로 A05 registry의 원본 바이트 범위만 동기화했다. v42 46~60과 61~75 묶음은 다른 작업의 일시적인 registry 매핑 때문에 첫 복사가 거부됐으나, source/live registry/backup/temp SHA-256 precondition을 확인하고 짧은 1회 재시도로만 완료했다. 프로세스 종료·강제 해제·전역 재직렬화는 하지 않았고, 모든 self-created temp/backup은 source-primary 대조 뒤 제거했다.
- v42 text의 `primary+은/는` 도입은 133/150(88.6667%)에서 44/150(29.3333%)로 낮췄다. 이 단계는 primary·relations를 바꾸지 않은 행별 text 재서술이며, v42 최종 source SHA-256은 `49B9347C555F2389CC06D5A745D31DC95F5AD220BC9BD0E6F55EDAFE33FCE9C9`, registry SHA-256은 `50ABC781168876F06569BC26AC1B70F08FBD3AD9B679AE141C050EA6CE2DB70B`이다.
- v42 단일 구조 검사는 150행, UTF-8 BOM 없음, 공백행·JSONL parse·빈 field·primary literal·relations 13개/2~5개/내부 중복·other_type 조건·train unseen field·primary/text exact duplicate·금지 내부 라벨·registry 150 locator·A05 전역 primary duplicate 모두 오류 0이었다.
- r45 A05 selector 보고서 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r45_v42_complete_2026-09-15.json`은 69 files / 10,350 records / hard source error 0 / registry parse problem 0 / coverage 100% / 전체 `primary+은/는` 1,804/10,350(17.4299517%) / v42 44/150(29.3333%, WITHIN_PROVISIONAL_RANGE) / naturalness warning record 0 / ChatGPT review 48(HARD 0) / user review 0을 확인했다. r45 source-set SHA-256은 `c750a4aad177027d5cbd0df029a30015533fa565e9eeca9c5c4537ab7af89e26`이다.
- r45 뒤 독립 char 3~5-gram TF-IDF는 15,324 pairs >= .72, 최고 .9414831585112751이며 최고쌍은 v29:63/93의 `곤충 개체수 발생 징후/발생 여부`다. v42는 구조 PASS이지만 다른 version의 대량 template 반복이 남아 A05 전체 자연성은 계속 **HOLD**다.
- 다음 재개 지점: v29 생태 복원·모니터링 source 150행을 전수 재서술한다. 특히 식생·개체수·토양 수분 같은 상태값을 `발생`이라고 부른 primary와 `발생 징후/발생 여부`, `잠정 발생`, `미발생 판정`, `가능 상태`, `실제 확인`, `미실행 상태`, `조건부 발생`의 인공 라벨을 실제 관찰·확인·미확인·조치/비조치 문맥으로 locator별 직접 재서술하고 registry locator를 동기화한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 계속 수정하지 않는다.

## 2026-09-15 v29 생태 복원·모니터링 전체 자연성 재서술 및 r46 재감사

- v29는 source SHA-256 `70EEDB8937867CAE05A47C829D1258D20A0046CF53B22C62619215C089E59659`에서 시작해 150행을 전수 판독했다. 식생·개체수·토양 수분 같은 상태값을 사건처럼 부른 라벨과 `발생 징후`, `발생 여부`, `미실행 상태`, `조건부 발생`을 실제 관찰·잠정 판단·확인 절차·미조치·구체 조건부 가능성으로 locator별 직접 재서술했다. v29:7·12는 다른 version과 겹친 exact primary도 의미를 좁혀 해소했다. 행 순서, relations, other_type은 보존했다.
- primary가 달라진 locator는 15행 이하 묶음으로 registry 원본 바이트 범위만 동기화했다. 재개 시 중단돼 있던 v29:106~120의 source/registry locator도 먼저 대조해 0 오류와 임시·backup 파일 부재를 확인했다. 이어 121~135, 136~150, 7·12 묶음의 source SHA, live registry SHA, backup SHA, live=temp SHA, locator 대조를 모두 통과했고 self-created temp/backup은 제거했다. 최종 v29 source SHA-256은 `F223436D5C3EC46BFEEC3C59D843866D77297EB9EF4FD1C6F5CC43D179DFE51B`, 당시 registry SHA-256은 `4D220C0BFA4BB5C1C013A6223FF3A842172EE1B41322E50796605662E0AF1335`이다.
- v29 단일 구조 감사는 150행, UTF-8 BOM 없음, 공백·JSONL parse·빈 field·primary literal·13개 통제 relations/2~5 cardinality/내부 중복·other_type·train unseen field·primary/text exact duplicate·금지 내부 라벨·registry 150 locator·A05 전역 primary duplicate 모두 오류 0이었다. `primary+은/는` 도입은 0/150이다.
- r46 A05 selector 보고서 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r46_v29_complete_2026-09-15.json`은 source-set SHA-256 `016ad63e7eccb59f4787f076a8a9485d492af5c667aa427a39c1c9ed57c200cf`, 69 files/10,350 records, hard source error 0, registry parse problem 0, coverage 100%, 전체 `primary+은/는` 1,774/10,350(17.1400966%), 자연성 warning record 0, direct rewrite 0, ChatGPT review 48(HARD 0), user review 0을 기록했다. 독립 char 3~5-gram TF-IDF는 15,043 pairs >= .72, 최고 .9415604356729728였고 최고쌍은 v44:27/147의 `해상 운항 가정 결과/가정 범위`였다. 자연성 최종 PASS 근거는 아니다.

## 2026-09-15 v44 해양 부표·해상 운항 전체 자연성 재서술 및 r47 재감사

- v44를 전수 판독했다. 자연스러운 실제 반례/조건 문장 21행만 보존하고, 나머지 129개 primary/text에서 `조건부 결과`, `가정 결과`, `반사실 경로`, `대안 결과`, `미실행 결과`, `가상 결과`, `조건 변경 전망`, `대체 경로 예상`, `가정 범위`라는 내부 분류어를 파고 기준, 수온·염분 센서, 풍속 보정, 통신 배터리, GPS 위치, 조류 방향, 출항 판단, 데이터 재전송, 부표 점검의 구체 조건·예측 대상·확인 기록으로 직접 재서술했다. 전역 치환·자동 문장 생성·relations/other_type 변경은 하지 않았다.
- v44의 변경 primary는 1~15, 16~30, 31~45, 46~60, 61~75, 76~90, 91~105, 106~120, 136~150 묶음에서 registry 원본 바이트 범위만 동기화했다. 각 묶음은 source/live SHA precondition, source_file/source_line anchor 단일 일치, old primary 대조, backup SHA, live=temp SHA, 변경 locator의 source-primary 대조를 통과했고 모든 self-created temp/backup을 제거했다. v44 source는 시작 SHA-256 `54D26A40228569DFC79A139476735E04E3E6A2B0072CE10C4815C09E1225DE0E`에서 최종 `DD5DA977963D92241B8B3B164C3F279BD78E1F49DB358BD2D1917D5307A6B155`로, 당시 registry는 최종 `73A5B79F20EF9C4C8EEB522E73EE36E831486EC98C2DF017F429D1B932F0D088`로 바뀌었다.
- v44 단일 구조 감사는 150행, BOM·공백·JSONL parse·빈 field·primary literal·relations·other_type·train unseen field·primary/text exact duplicate·금지 내부 라벨·registry 150 locator·A05 전역 primary duplicate 모두 오류 0이었다. `primary+은/는` 도입은 6/150이다.
- r47 A05 selector 보고서 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r47_v44_complete_2026-09-15.json`은 source-set SHA-256 `73d3852b1ccbb5ede3de508947a184ef785fd4f2c936e25d4802de92edddb644`, 69 files/10,350 records, hard source error 0, registry parse problem 0, coverage 100%, 전체 `primary+은/는` 1,761/10,350(17.0144928%), naturalness warning record 0, direct rewrite 0, ChatGPT review 48(HARD 0), user review 0을 기록했다. 독립 char 3~5-gram TF-IDF는 14,880 pairs >= .72, 최고 .9418782330370422이며 최고쌍은 v32:18/78의 `곤충 개체수 가정 결과/가상 결과`다. pair 수는 줄었지만 최고값과 48개 review group이 남아 A05 판정은 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: 독립 최고쌍 v32:18/78을 포함한 v32의 고유사·불투명한 가능성 라벨을 150행 전수 판독하고, 확정 오류만 locator별 직접 재서술한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 계속 수정하지 않는다.

## 2026-09-15 v32 생태 복원·모니터링 자연성 재서술 — 진행 중

- v32 source SHA-256 `E1D2A631C5BBEA22EF63FBE2C59F4AFA2750B9A9929050DCD1A278DD250C496F`에서 시작했다. 독립 최고쌍 v32:18/78과 1~50행을 직접 판독했고, 1~30행의 `조건부 결과`·`가정 결과`를 관수 횟수, 조사 누락, 야간 포획, 토양 수분, 울타리, 외래종 제거, 채수 시기, 카메라 트랩, 예초, 생태 통로, 보호 조치, 음향 센서, 유인등 위치, 수동 채수의 구체 조건·예측·확인 문맥으로 직접 재서술했다. relations와 other_type은 보존했다.
- v32:1~15와 16~30의 변경 primary를 각각 registry 원본 바이트 범위에서 동기화했다. source/live registry SHA precondition, locator anchor, old primary, backup SHA, live=temp SHA, source-primary 대조를 통과했고 self-created temp/backup은 제거했다. 현재 v32 source SHA-256은 `8BFFA7B3B764CE4C23F5269A3661A3CBA36FDEB7E531AA3C7A56992B5FE704CB`, registry SHA-256은 `B1B7F70F3F6FCD78E0EC7B1C7E280943E043EB082675BAA310D737E911E4D85B`이다.
- v32은 아직 31~150행이 남아 있으므로 영역 reviewer와 독립 유사도 감사는 실행하지 않았다. 다음 재개 지점: v32 31~150행을 15행 이하 locator 묶음으로 전수 판독·직접 재서술하고, primary 변경마다 registry 동기화를 끝낸 뒤에만 단일 구조 감사와 A05 전수 재감사를 수행한다.

## 2026-09-15 v32 생태 복원·모니터링 전체 자연성 재서술 및 r48 재감사

- v32 150행을 전수 판독했다. 실제 반례·판정 한계를 설명하는 121~135행과 이미 구체적인 조건 설명인 139·149행은 보존했고, 나머지에서 `미실행 결과`, `가상 결과`, `조건 변경 전망`, `대체 경로 예상`, `가정 범위` 같은 내부 분류어를 관수·조사·방제·채수·카메라 점검·서식지 통로·보호 조치의 실제 조건, 예상 대상, 관찰 근거, 판단 한계로 직접 재서술했다. primary를 바꾼 locator는 131개이며, 행 순서·relations·other_type은 보존했다.
- primary 변경은 15행 이하 묶음으로 A05 registry 원본 바이트의 해당 `primary` 범위만 동기화했다. 각 묶음은 source/live registry SHA precondition, source_file/source_line anchor 단일 일치, old primary 대조, backup SHA, live=temp SHA, source-primary locator 대조를 통과했고, self-created temp/backup은 검증 뒤 제거했다. 최종 v32 source SHA-256은 `3CF2DC351D40B9033E0AFB2C8650746621008A8132B003E56264CA1D6B472E27`, registry SHA-256은 `59CE747EBABC5D4D08E6EF453799179820DB90AF7016A7C45BCBCFCC343627C4`이다.
- v32 단일 구조 감사는 150행, UTF-8 BOM 없음, 공백행·JSONL parse·빈 field·primary literal·13개 통제 relations·2~5 cardinality·내부 중복·other_type 조건·train unseen field·primary/text exact duplicate·금지 내부 라벨·registry 150 locator·A05 전역 primary duplicate 모두 오류 0이었다. `primary+은/는` 도입은 70/150(46.6667%)에서 text-only 행별 재서술 뒤 41/150(27.3333%)로 낮아졌다.
- r48 A05 selector 보고서 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r48_v32_complete_2026-09-15.json`은 69 files / 10,350 records, hard source error 0, registry parse problem 0, coverage 100%, 전체 `primary+은/는` 1,786/10,350(17.2560386%, WITHIN_PROVISIONAL_RANGE), naturalness warning 0, direct rewrite target 0, ChatGPT review pending 48(HARD 0), user review 0을 기록했다. reviewer source-set SHA-256은 `277683597707ce438188ee696507870627b830556e261bfd3145e38f49462835`이다.
- r48 뒤 독립 char 3~5-gram TF-IDF는 14,722 pairs >= .72, 최고 .9428520065513594이며 최고쌍은 v54:21/81의 `초순수 공급 가정 결과/가상 결과`였다. 구조 PASS와 warning 0은 자연성 최종 PASS 근거가 아니므로 A05 상태는 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: v54 반도체 클린룸 오염·수율 관리 source를 150행 전수로 읽고, 최고쌍 v54:21/81과 잔여 불투명 가능성·가정 라벨을 locator별로 직접 재서술한다. 이어 같은 registry 동기화와 단일 구조·A05 영역 재감사를 수행한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 계속 수정하지 않는다.

## 2026-09-15 v54 반도체 클린룸 오염·수율 관리 전체 자연성 재서술 및 r49 재감사

- v54는 재개 시 source SHA-256 `446FA26DCD64870CDAEE78AAF1414E45CBF0ABD88376E612411C7D36AB7002B0`, registry SHA-256 `507A00C90A91A9582027AD831AFBF479751E78F482D0BC3FBDD0BCC531C7724E`에서 확인했다. 150행을 문맥별로 읽고, `가정 결과`·`가상 결과`·`가정 범위`처럼 대상·조건·측정 기준이 빠진 내부 분류어를 공조 풍량, 필터 차압, 웨이퍼 검사, 식각 깊이, 증착 막 두께, 포토 불량, 초순수 세정, 가스 누출, 설비 가동률, 검사 대기, 수율 경보, 라인 격리의 실제 확인 조건과 판정 한계로 직접 재서술했다. primary 변경 locator는 130개이며, 행 순서·relations·other_type은 보존했다.
- primary가 바뀐 locator는 15행 이하 묶음으로 registry 원본 바이트의 `primary` 범위만 동기화했다. 마지막 136~150행은 source SHA와 registry SHA precondition, locator anchor 단일 일치, 기존 primary 일치, backup SHA, live=temp SHA, source-primary 대조를 모두 통과했다. self-created temp/backup은 검증 뒤 제거했고, 최종 registry SHA-256은 `4F83485266E70325F1A9D02AA7A37D62AFE19DF017158365489C1D125DF376A1`이다.
- 단일 파일 도입부 검토에서 `primary+은/는`이 128/150(85.3333%)인 것을 확인했다. 의미를 바꾸지 않은 84개 text를 행별로 실제 관찰·비교·점검·계산의 흐름으로 직접 재서술해 45/150(30.0000%)로 낮췄다. 전역 치환·템플릿 대량 치환·suffix 번호 부여·source 전체 재직렬화는 하지 않았다.
- 최종 v54 source SHA-256은 `8A654B2F4D8C60231D6AB7F79B01B3AEB9789434D3852DC1C8100C1EBEC0A216`이다. 단일 구조 감사는 150행, UTF-8 BOM 없음, 공백행·JSONL parse·빈 field·primary literal·13개 통제 relations·2~5 cardinality·내부 중복·other_type 조건·train unseen field·primary/text exact duplicate·금지 내부 라벨·registry 150 locator 모두 오류 0이었다.
- r49 reviewer-assist 보고서 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r49_v54_complete_2026-09-15.json`은 69 files / 10,350 records, source-set SHA-256 `05d8d442fdfc780ef84d5815842ebce5eaffb25b52b96356cf9ed42395449da3`, hard source error 0, registry parse problem 0, coverage 100%, 전체 `primary+은/는` 1,796/10,350(17.3526570%, WITHIN_PROVISIONAL_RANGE), naturalness warning 0, direct rewrite target 0, ChatGPT review pending 48(HARD 0), user review 0을 기록했다.
- r49 뒤 독립 char 3~5-gram TF-IDF는 14,594 pairs >= .72, 최고 .9420080054767681이며 최고쌍은 v47:46/136의 `충전차고 전력 확률 근거/확률 비교` 문형이다. 따라서 v54 단일 구조는 PASS이지만, A05 전체는 대량 문형 재사용과 남은 semantic review queue 때문에 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: compact 상황판의 우선 locator인 v59 전기버스 충전차고 전력·배차 source를 150행 전수 판독하고, 고유사 `운전자 교대 가정 결과/가정 범위` 및 남은 반사실·조건 범위 라벨을 실제 배차·충전·전력 조건과 확인 기록으로 직접 재서술한다. primary 변경마다 registry locator만 동기화하고, 단일 구조·A05 reviewer·독립 유사도 감사를 재실행한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 계속 수정하지 않는다.

## 2026-09-15 v59 전기버스 충전차고 전력·배차 전수 자연성 판독 및 r50 재감사

- v59 source SHA-256 `2C0B8A6ADEC28F35F78561B1CB168BCEDFB0D219F8FF07BCB05A3116BB9C173B`에서 150행을 전수 판독했다. 충전기 고장, 입고·예약, 배터리 잔량·열관리, 정비·교대, 피크 전력, 우회 운행, 반례, 계산 전제의 실제 운영 문맥은 보존했다. 인공적인 명사화였던 30행 `위치 전송 중단 시 보류되는 운행 여부 판정`을 `위치 전송이 끊겼을 때 운행 여부 판단을 보류하는 기준`으로, 63행 `고장 진단을 하지 않을 때의 충전기 사용 불확실성`을 `고장 진단 전 충전기 사용 가능 여부`로 직접 재서술했다. 84행은 `비어 난다고`의 띄어쓰기·조건 표현을 자연스럽게 고쳤다.
- 변경 primary 2개만 registry 원본 바이트의 해당 locator에 동기화했다. source/live SHA precondition, locator anchor 단일 일치, 기존 primary 대조, backup SHA, live=temp SHA, source-primary 대조를 통과했고 self-created temp/backup은 검증 뒤 제거했다. 최종 v59 source SHA-256은 `B7DB1CB4F0540DE2DFED5FA1499A9B3EFE91FE5F56C79A15AFDA26674E66D2DE`, registry SHA-256은 `FECDE0C9423E861C9EC8903968D5183BAE0800463E1A4B4F1A75C92D0B4156EF`이다.
- 단일 구조 감사는 150행, UTF-8 BOM 없음, 공백행·JSONL parse·빈 field·primary literal·13개 통제 relations·2~5 cardinality·내부 중복·other_type 조건·train unseen field·primary/text exact duplicate·금지 내부 라벨·registry 150 locator 모두 오류 0이었다. `primary+은/는`은 2/150(1.3333%)다.
- r50 reviewer-assist 보고서 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r50_v59_complete_2026-09-15.json`은 69 files / 10,350 records, source-set SHA-256 `6b978f6d77e4f826157993282a0598a15fa32e1b114ab7fc4ae9850895373a75`, hard source error 0, registry parse problem 0, coverage 100%, 전체 `primary+은/는` 1,796/10,350(17.3526570%, WITHIN_PROVISIONAL_RANGE), v59 2/150(1.3333%, WITHIN_PROVISIONAL_RANGE), naturalness warning 0, direct rewrite target 0, ChatGPT review pending 48(HARD 0), user review 0을 기록했다.
- r50 뒤 독립 char 3~5-gram TF-IDF는 14,594 pairs >= .72, 최고 .9420081358733621이며 최고쌍은 v47:46/136의 `충전차고 전력 확률 근거/확률 비교` 문형이다. 구조 PASS와 advisory warning 0은 자연성 최종 PASS 근거가 아니다. A05 상태는 계속 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: 현 독립 최고쌍 v47:46/136을 먼저 문맥별로 읽고, 의미가 겹치는 인공 확률 라벨이면 locator 단위로 직접 재서술한다. 이어 reviewer queue의 동일 relation-set 고유사 군을 version별로 전수 검토한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 계속 수정하지 않는다.

## 2026-09-15 v47 전기버스 충전차고 전력·배차 전체 자연성 재서술 및 r51 재감사

- v47의 150행을 다시 전수 판독했다. 121~135행의 실제 운영 가능성 문장은 보존했고, 나머지 인공적인 `발생 확률`·`확률 구간`·`가능성 수치`·`확률 근거`·`확신도`·`신뢰 판단`·`예측 확률`·`위험 확률`·`확률 비교` 명사화를 실제 전력 부족, 배차 지연, 충전기 고장, 출고 지연, 비상 충전, 정비, 통신 누락의 가능성·판단 근거·예측 신뢰도·위험·조건별 비교로 행별 직접 재서술했다. 행 순서, relations, other_type은 보존했다.
- primary가 달라진 120 locator(1~120 중 15행 단위 8묶음)는 A05 registry의 해당 primary 바이트 범위만 동기화했다. 각 묶음에서 source/live registry SHA-256 precondition, source_file/source_line anchor 단일 일치, 이전 primary 일치, source-primary literal, backup SHA, live=temp SHA를 확인했고 self-created temp/backup을 모두 삭제했다. 최종 v47 source SHA-256은 `28F89175FFFD04015149470EB8B32510BD6FB980A5EF2F766A7D2BC1AB321B6A`, registry SHA-256은 `11E47E30A79CF21DDF3E8FE67F4A32E1E2BD6C52DE6722E7D8C0B9566A5953BA`다.
- v47 단일 구조 감사는 150행, UTF-8 BOM 없음, 공백행·제어문자·JSONL parse·빈 field·primary literal·relations 13개/2~5개/내부 중복·other_type 조건·train unseen_relation·primary/text exact duplicate·금지 내부 라벨·registry 150 locator·A05 전역 primary duplicate 모두 오류 0이었다. `primary+은/는` 도입은 15/150(10.0000%)다.
- r51 reviewer-assist 보고서 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r51_v47_complete_2026-09-15.json`은 source-set SHA-256 `542d34361f5efbaf2c61290f45d91e137e898566436b754a729991ebbdececc1`, 69 files / 10,350 records, hard source error 0, registry parse problem 0, coverage 100%, 전체 `primary+은/는` 1,769/10,350(17.0917874%), naturalness warning record 0, direct rewrite target 0, ChatGPT review pending 48(HARD 0), user review 0을 기록했다. PowerShell에서 null 배열을 잘못 1건으로 센 중간 확인값을 정정했으며, 실제 보고서의 `warning_records`는 0이다.
- r51 뒤 독립 char 3~5-gram TF-IDF는 14,378 pairs >= .72, 최고 .9409649279039195이며 새 최고쌍은 v15:21/81의 철도 승객 안내 예정 시점 문형이다. v47의 고유사 pair는 해소됐지만, 전체 A05 자연성은 여전히 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: v15 철도 운행 간격·환승 조정 source 150행을 전수 판독·직접 재서술한다. `조치 예정 시점`·`예측 시점`·`승인 대기 계획`·`예약 실행` 등 실제 운영 대상이 빠진 제목을 실제 조치·승인·시각·확인 기록으로 구체화하고, primary 변경마다 registry locator만 동기화한 뒤 단일 구조와 A05 전수 감사를 다시 실행한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 수정하지 않는다.

## 2026-09-16 v15 철도 운행 간격·환승 조정 전체 자연성 재서술 및 r52 재감사

- v15의 150행을 전수 판독했다. `실행 예정`, `조치 예정 시점`, `일정 예측`, `계획 상태`, `예상 완료 시각`, `예측 시점`, `승인 대기 계획`, `예약 실행`, `운영 전망`, `재개 예정`처럼 대상·행위·승인 단계를 숨긴 제목과 문장을, 간격 조정·혼잡 완화·신호기 통신 점검·출입문 점검·차량 정비·승객 안내·선로·급전·인력 배치·회차 선로·운행 재개의 실제 조치, 예상 시각, 승인 대기, 등록 상태, 전망, 재개 절차로 각각 직접 재서술했다. 행 순서, relations, other_type은 보존했다.
- 수정 전 v15 source SHA-256은 r51 source snapshot의 `4E1BA77125DA430777A8A9496211F9002ECF4BE4143F7AEB1463E5B65C71AD73`이었다. 바뀐 primary 150 locator를 15행씩 A05 registry의 해당 primary 바이트 범위만 동기화했으며, 각 묶음에서 source/live registry SHA-256 precondition, source_file/source_line anchor 단일 일치, 이전 primary 일치, source-primary literal, backup SHA, live=temp SHA를 확인했다. self-created temp/backup은 검증 뒤 모두 삭제했다. 최종 v15 source SHA-256은 `C0EBEEC51DB45EA60F0612BFDD42D9E501C7F1C2963B558DE8A4A429F049E2DC`, registry SHA-256은 `8FCB88B837D3A973CEAB47D3603600FBA4F09670B0F545A4413DAE5C95A68D24`이다.
- v15 단일 구조 감사는 150행, UTF-8 BOM 없음, 공백행·제어문자·JSONL parse·빈 field·primary literal·relations 13개/2~5개/내부 중복·other_type 조건·train unseen_relation·primary/text exact duplicate·금지 내부 라벨·registry 150 locator·A05 전역 primary duplicate 모두 오류 0이었다. `primary+은/는` 도입은 0/150(0%)다.
- r52 reviewer-assist 보고서 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r52_v15_complete_2026-09-16.json`은 source-set SHA-256 `d54d9059c5c078ce2a19d31028afb66d10c7917ec89f18c2bfac5538d2422f5b`, 69 files / 10,350 records, hard source error 0, registry parse problem 0, coverage 100%, 전체 `primary+은/는` 1,754/10,350(16.9468599%), v15 0/150, naturalness warning record 0, direct rewrite target 0, ChatGPT review pending 48(HARD 0), user review 0을 기록했다.
- r52 뒤 독립 char 3~5-gram TF-IDF는 14,089 pairs >= .72, 최고 .9406284667284266이며 새 최고쌍은 v17:68/98의 농업용수 공급 `발생 징후/발생 여부` 문형이다. v15의 최고쌍은 해소됐지만 A05 전체는 아직 전수 행별 의미 판독과 고유사 queue 검토가 남아 **구조 PASS / 자연성 HOLD / `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`**다.
- 다음 재개 지점: v17 농업용수 공급·관개 운영 source를 150행 전수로 읽고, `발생 징후/발생 여부`와 상태값을 사건처럼 부른 표현을 실제 관측 신호·실제 확인·미확인·조치 여부로 분리해 locator별 직접 재서술한다. primary 변경마다 registry locator만 동기화하고 단일 구조·A05 reviewer·독립 유사도 감사를 다시 실행한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 수정하지 않는다.

## 2026-09-16 A05 ModalityPossibility 자연성 감사보고서 통합 정리

- `audit_reports/machine/a05/`에 흩어진 `TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness*.json` 원본 53개(총 191,731,730바이트)를 읽기 전용으로 SHA-256·JSON 파싱·이력 목록을 대조한 뒤 `TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_Consolidated_2026-09-16.json` 한 파일로 통합했다.
- 통합본은 9,672,976바이트, JSON 재파싱 PASS, SHA-256 `F20E6E3EBA48A316D65C612F57E18C46112BAB5664671150DD46999FDC210B8A`이며, 최신 r55 전체 보고서와 53개 입력의 파일별 SHA·크기·시각·핵심 gate 지표·50개 source snapshot·중복 report 그룹·review queue union index를 보존했다. 동일 바이트 중복 그룹은 2개로 묶었다.
- 통합본 검증 후 대상 폴더 내부에 정확히 열거된 53개 원본 보고서만 삭제했고, 통합본은 유지된다. 삭제 후 원본 잔여 0개, 통합본 존재·파싱·크기·SHA를 다시 확인했다. source/package/manifest/central ledger는 변경하지 않았다.

## 2026-09-16 v21 냉장 유통 가능성 자연성 재서술 및 r57 재감사

- 대상은 A05 stage2_(15)_modality_possibility v21 source 1개(150행)와 primary 변경 locator의 A05 term registry뿐이다. 다른 영역 source, package train·val, manifest, checkpoint, 중앙 원장, 공용 감사기 및 Git은 수정하지 않았다.
- v21 source 시작 SHA-256은 69A5176EAA7D4F18770AB6DF478A0E7A530194FFDCDDA36B809F017E74B64059였고, 최종 source SHA-256은 0C38E7AD252CCEF002C35C15A06E771D651D4C13753095A3BDA91D5B449CFA4다. registry 시작 기준 SHA-256은 C552C82808B2610E9DE13F9197A294259C5D559251D6E1995419FF00442ACE9B, 최종 SHA-256은 44A70A422C2645DC7A4885821137E79CB6493B39CE65F1B598A75464EA0DB8FF다.
- v21 1~150행에서 발생 징후·가능 상태·발생 여부·실제 확인·미실행 상태·조건부 발생을 냉장 창고 온도, 냉동 차량 적재, 중심 온도, 품질 저하, 배송 지연, 냉매 압력, 문 열림 기록, 저온 경보, 시료 누락, 유통기한, 팔레트 위치, 상차 순서, 냉장고 전원, 운송장 추적, 품질 판정의 실제 관측·확인 자료·미수행 조치·조건→가능성 문맥으로 행별 직접 재서술했다. primary 90행과 text-only 59행을 수정했으며 relations·other_type·행 순서는 보존했다.
- 처음 reviewer가 보고한 primary_literal_missing 59행은 설명문에 primary가 그대로 포함되지 않았던 하드 규칙 위반이었다. 각 문장에 해당 primary를 의미상 자연스럽게 한 번 포함하도록 보완한 뒤 재감사했다. 이는 전역 치환이나 템플릿 자동생성이 아니다.
- registry는 1~150행 primary를 15행 이하 묶음으로 source_file/source_line 단일 locator에만 바이트 범위 동기화했다. 68·98행은 source와 registry가 이미 동일하여 안전하게 변경하지 않았다. 각 묶음의 locator·기존 primary·source SHA·live registry SHA를 확인했고 임시·백업 파일은 성공 검증 뒤 제거했다.
- r57 reviewer-assist(audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r57_v21_complete_2026-09-16.json)는 A05 69 files / 10,350 records, source-set SHA-256 0C38E7AD252CCEF002C35C15A06E771D651D4C13753095A3BDA91D5B449CFA4, registry 10,350 records·coverage 100%·parse problems 0, hard source error 0, direct rewrite target 0, naturalness rule warning 0, ChatGPT review groups 48(HARD 0), user queue 0을 기록했다. 전체 primary+은/는은 1,666/10,350(16.0966%, WITHIN_PROVISIONAL_RANGE)이다.
- 독립 scikit-learn char 3~5-gram TF-IDF 전수 대조는 10,350 records, threshold 이상 13,316쌍, 최고 0.9397859149를 보고했다. 최고쌍은 v33:3/93 충방전 전류 발생 가능성/충방전 전류 발생 여부로, 남은 공통 문형의 행별 의미 판독 대상으로 보류했다.
- v21 단일 source 구조·JSONL·BOM/공백·primary literal·relations 통제어휘/2~5 cardinality·other_type·train unseen_relation·중복·registry locator는 모두 오류 0으로 확인했다. 구조 PASS와 자연성 PASS를 혼동하지 않으며, A05 전체 상태는 계속 SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW다.

## 2026-09-16 A05 자연성 감사 통합본 증분 병합(r56~r58)

- 기존 통합본에 이후 생성된 r56(v21), r57(v21), r58(v33) 보고서 3개를 추가 병합했다. 각 원본의 JSON parse·파일 크기·SHA-256을 읽어 이력(`report_history`)에 핵심 지표·관계별 유사도 요약·자연성 경고·review 인덱스로 보존하고, source-set SHA가 다른 3개 snapshot을 추가했다. 동일 review key는 union index에서 한 항목으로 deduplicate하고 마지막 관측 보고서만 갱신했다.
- 최신 r58 전문은 통합본의 `latest_report`에 임베드했으며, 원본 삭제 후 dangling pointer가 생기지 않도록 `latest_report_storage=embedded_in_consolidated`, `latest_report_file=null`, `latest_report_source_file`에 원래 파일명을 기록했다. 최신 전문의 원본 SHA는 이력과 일치한다.
- 최종 통합 파일은 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_Consolidated_2026-09-16.json`, 10,040,688바이트(<20,000,000), SHA-256 `50AD50578A3E8B67A9E018FAC437D277A0121D46192E9478239A154CD8D6F4D3`이다. 이력 56개(파일명 중복 0), source snapshot 53개, review union 52개, JSON 재파싱 PASS를 확인했다.
- 병합·검증 후 정확히 r56/r57/r58 원본 3개를 삭제했고, 해당 폴더에는 통합본만 남았다. 임시·백업 파일 0개이며 source, registry, package train/val, manifest, 중앙 원장, 공용 감사기 및 Git은 변경하지 않았다.

## 2026-09-16 v33 배터리 저장장치 가능성 자연성 재서술 및 r58 재감사

- v33 배터리 저장장치 source 150행을 전수 재서술했다. 충전 범위, 셀 과열, 전류·전압 이탈, 인버터 한계, 냉각팬·릴레이, 잔량·열화, 비상 정지, 변환 효율, 운전 기록 누락을 실제 관측·잠정 판단·부정 판정·징후·불확실 상태·확인 절차·미실행 조치·조건부 가능성으로 구체화했다. primary/text만 행별로 바꾸고 relations·other_type·행 순서는 보존했다.
- primary 변경 locator는 A05 registry에서 15행 이하 원본 바이트 범위로 동기화했다. 일시적인 Windows copy 오류 구간은 프로세스를 종료하지 않고 precondition·backup·live=temp SHA를 확인한 뒤 재시도했으며, self-created temp/backup은 모두 제거했다. 최종 v33 source SHA-256은 `3CF2DC351D40B9033E0AFB2C8650746621008A8132B003E56264CA1D6B472E27`(당시 기록), registry 최종 SHA-256은 `59CE747EBABC5D4D08E6EF453799179820DB90AF7016A7C45BCBCFCC343627C4`다.
- r58 reviewer 원본은 통합본에 전문과 이력으로 보존되어 있다. r58은 A05 69 files / 10,350 records, source-set SHA-256 `b9df1e79c81baac3831d1edcdac0e78b70fd1fbb83677c5f14bd345b563646ba`, registry 10,350·coverage 100%·parse problems 0, hard source error 0, direct rewrite 0, naturalness warning 0, ChatGPT review 48(HARD 0), user review 0, 전체 primary+은/는 1,663/10,350(16.0676%)을 기록했다.
- v33 이후 독립 char 3~5-gram TF-IDF는 13,041 pairs >= .72, 최고 0.9391575547이며 v46:3/93의 `피해 등급 발생 가능성/피해 등급 발생 여부` 문형이 당시 최고쌍이었다. v33 단일 구조와 reviewer gate는 PASS였지만 A05 전체 자연성은 계속 HOLD였다.

## 2026-09-16 v46 산림 병해충·생태 모니터링 전체 자연성 재서술 및 r59 재감사

- v46 시작 source SHA-256은 `B2F2F8081809D6C8833459D226431807F3BFC4D8FA8840EDF6388405C65C6CCC`였다. 1~45행의 기존 재서술을 확인하고 46~150행 105개를 산림 병해충 밀도·포획 트랩·피해 등급·수종 분포·기상 관측·검체 판독·방제·산불 위험·예찰·복구의 부정 판정, 징후, 불확실 상태, 확인 결과, 미실행 조치, 조건부 가능성으로 직접 재서술했다. 이미 자연스러운 62·72·92·102행은 보존했고, 총 146개 primary를 변경했다. relations·other_type·행 순서는 보존했다.
- v46 primary 146 locator를 A05 registry의 해당 바이트 범위에 15행 단위로 동기화했다. 62·72·92·102행은 source와 registry가 이미 동일하여 건너뛰었고, 각 묶음에서 locator 단일 일치·old primary·source SHA·backup/live=temp SHA를 확인했다. 최종 v46 source SHA-256은 `F4C90F5E2505DDD174B131410D3C2AE2344188DDAAFCC21B3809A4577EFEBB43`, registry 최종 SHA-256은 `2898AD2A8B05BDAC2815C48F7774AAE00B271AB7A434A78904FE227D23D84AF5`다. v46 locator 대조 150/150, primary mismatch 0, source primary duplicate 0, temp/backup 0이다.
- r59 reviewer-assist 보고서 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r59_v46_complete_2026-09-16.json`은 source-set SHA-256 `5ac9427a096b0657387bd5bcae95ee2b612f99f29d5db1dd7040df12b375600a`, 69 files / 10,350 records, registry 10,350·coverage 100%·parse problems 0, hard source error 0, direct rewrite target 0, 자연성 rule warning record/assignment 0, v46 `primary+은/는` 25/150(16.6667%), 전체 1,656/10,350(16.0000%, WITHIN_PROVISIONAL_RANGE), ChatGPT review groups 48(HARD 0), user review 0을 기록했다. 구조 gate는 PASS이나 reviewer queue가 남아 자연성 최종 PASS는 아니다.
- r59 이후 독립 scikit-learn char 3~5-gram TF-IDF 전수 대조는 10,350 records, threshold 이상 12,784쌍, 최고 0.9391551602451174였다. v46의 이전 최고쌍은 해소되었고 새 최고쌍은 v41:3/93의 `항공기 지연 발생 가능성/항공기 지연 발생 여부`다. A05 상태는 계속 **SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW**다.
- 다음 재개 지점: r59 독립 최고쌍 v41:3/93의 문맥과 남은 48개 relation-set review group을 version별로 읽고, 의미가 겹치거나 불투명한 가능성·여부 라벨만 locator 단위로 직접 재서술한다. package·checkpoint·manifest·중앙 원장·다른 영역 source는 계속 수정하지 않는다.

## 2026-09-16 v41 공항 활주로 제설·운항 회복 조건부 가능성 재서술 및 r60 재감사

- 중단 지점 확인 결과 v41 136~150행의 조건부 공항 문맥 재서술은 이미 source에 적용되어 있었다. v41 150행을 확인한 뒤, r59 source snapshot의 수정 전 SHA-256 `A2C7215AD56BB98C2B036120403339CC6759CA896C844DA44D48253CA04E1DE`와 현재 source SHA `97CB8E16FCE91756F784C97C490D80E3FDBD7DDAF36C6B195473321F341C5081`을 대조했다. v41 rows 1~150은 이전 단계의 공항 제설·운항 회복 재서술 결과로 확인했으며, 이번 재개에서 중복 재작성하지 않았다.
- 재개 시 registry가 v41 이전 primary 150개와 불일치하여 먼저 A05 registry만 복구·동기화했다. 잘못된 Latin-1 재인코딩으로 생긴 임시 손상을 즉시 감지하고, `HEAD`의 v41 이전 primary를 이용해 registry를 원래 정본 SHA `2898AD2A8B05BDAC2815C48F7774AAE00B271AB7A434A78904FE227D23D84AF5`로 복구했다(JSONL parse PASS). 이후 UTF-8 바이트 범위만 15행 묶음으로 동기화했고, 최종 registry SHA-256은 `236038F4F9A30643AF9BA961C9EFEE09D718AC602A8106AFE85205C91D35AA1F`이다. source primary와 registry locator는 v41 150/150 일치, 임시·백업 잔여물 0이다.
- reviewer-assist r60 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r60_v41_complete_2026-09-16.json`은 A05 source 69 files / 10,350 records, registry 10,350·coverage 100%·parse problems 0, hard source error 0, direct rewrite target 0, 규칙 warning record/assignment 0, 전체 `primary+은/는` 1,627/10,350(15.7198068%), ChatGPT review groups 48(HARD 0), user queue 0을 기록했다. v41 조건부 136~150행을 포함한 구조 gate는 PASS이나, 동일 relation-set 의미군 48개가 남아 자연성 최종 PASS로 승격하지 않고 **SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW**를 유지한다.
- 독립 scikit-learn char 3~5-gram TF-IDF 전수 대조는 10,350 records, 기준 이상 12,512쌍, 최고 `0.9381307939172635`였다. 최고쌍은 `S2-A05-T-067:53` `지역난방 공급 확률 근거`와 `S2-A05-T-067:143` `지역난방 공급 확률 비교`이며 두 문장은 표본 수·불확실성·확인 기준을 공유하므로 후속 의미 판독 대상으로 남겼다. v41의 이전 최고쌍은 해소되었지만 전체 A05의 반복 문형 및 48개 검토군은 아직 종결되지 않았다.
- 이번 단계에서 변경한 보호 범위는 v41 source의 기존 적용 여부 확인과 A05 term registry의 v41 primary locator 동기화뿐이다. package train/val, 다른 Stage2 source, manifest, 중앙 원장, 공용 감사기, checkpoint, Git은 수정하지 않았다. 다음 재개 지점은 독립 최고쌍 v67:53/143과 48개 relation-set 검토군에서 실제 의미 중복·인공 명명만 locator 단위로 직접 재서술한 뒤 동일 전수 감사를 다시 실행하는 것이다.

## 2026-09-16 v67 지역난방 확률 근거·비교 고유사 pair 재서술 및 r61 재감사

- 독립 유사도 r60의 최고쌍인 v67 53행 `지역난방 공급 확률 근거`와 143행 `지역난방 공급 확률 비교`를 의미별로 판독했다. 두 행은 같은 문장을 공유해 `근거`를 평가한다거나 `비교`를 높게 평가한다는 부자연스러운 문맥이었으므로 primary·relations·other_type은 유지하고 text만 직접 재서술했다. 53행은 과거 공급 중단 기록·현재 배관 압력·표본 수를 확률 근거로 설명하고, 143행은 동일 계절·관측 기간의 빈도 비교와 조건 차이의 한계를 설명하도록 분리했다. registry primary는 바뀌지 않아 동기화하지 않았다.
- v67 source 수정 전 SHA-256은 r60 snapshot `748C36AC311D5B7380815E4E64F048DEEE2C9B6134A176CB0F1FA6EC6FC421AE`, 수정 후 SHA-256은 `AFD0E9BCE534EF42C6A7D4C85A7B0FD70CDE70EC4FF08EC4087E85038D516D9`이다. source는 150행·JSONL 구조를 유지했으며 ID·행 순서·relations·other_type·registry는 변경하지 않았다.
- r61 reviewer-assist `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_r61_v67_textpair_2026-09-16.json`은 A05 69 files / 10,350 records, registry 10,350·coverage 100%·parse problems 0, hard source error 0, direct rewrite target 0, 규칙 warning record/assignment 0, 전체 `primary+은/는` 1,627/10,350(15.7198068%), ChatGPT review groups 48(HARD 0), user queue 0을 기록했다. 구조 gate는 PASS이나 남은 48개 의미 검토군 때문에 자연성 최종 판정은 여전히 **SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW**다.
- r61 뒤 독립 scikit-learn char 3~5-gram TF-IDF는 10,350 records, 기준 이상 12,506쌍, 최고 `0.9378675130314141`로 낮아졌다. 새 최고쌍은 `S2-A05-T-062:46` `컨테이너 하역 확률 근거`와 `S2-A05-T-062:136` `컨테이너 하역 확률 비교`이며, 동일한 유형의 의미 중복 여부를 다음 재개 때 직접 판독한다.
- 이번 단계의 변경은 A05 v67 source text 2행뿐이며, package train/val, 다른 source, manifest, 중앙 원장, 공용 감사기, checkpoint, Git은 수정하지 않았다. 다음 재개 지점은 v62:46/136 최고쌍과 48개 relation-set 검토군의 명확한 의미 중복을 locator 단위로 재서술하고 r62 전수 감사를 실행하는 것이다.
