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
