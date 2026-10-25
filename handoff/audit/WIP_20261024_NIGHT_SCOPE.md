# 2026-10-23 야간 재개 범위와 착수 영향도

현재 사용자는 원장1·2 타세션 완료 검토와 2026-10-24 09:00 KST까지 CPU+GPU 주도적 학습을 허가했다. 세션은 `01a0b33b-d14e-7c40-ada8-229a1f97eabd`이며 같은 열린 WIP의72·73번이 현재 요청을 소유한다. 이 문서는 원장이나 사용자 승인 사본을 대신하지 않는 이번 변경 범위표다.

## 경로별 경계

| 경로 | 동작 | 현재 근거 | 제외 |
|---|---|---|---|
| `/tmp/tinylm_task12_checklist_20261023.md`, 지명 task12 후보·검토문·패킷 | 읽기 대조 | 원장1·2 완료 검토 | 타세션 원형·후보·게시·완료 영수증 수정0 |
| 현재 WIP와 `handoff/audit/WIP_20261024_*` | 정상 API 갱신과 독립 감사 | 재개 절차·현재 위임 | 다른 세션 WIP 및 과거 인계 변경0 |
| `scripts/diag_p102a_head_muon_trace.py`, `scripts/test_p102a_head_muon_trace.py` | 새 진단·CPU 회귀 | 선택된 수치 원인분리 후속 | 제품 Muon·기존 head 기본값 및 이전 진단 변경0 |
| `scripts/diag_p106b_external_core6.py`, `scripts/test_p106b_external_core6.py` | 기존 HF 자산의 공식 평가 연결·CPU 회귀 | 미완 외부 비교 회수와 현재 계산 위임 | 새 설치·다운로드·공식 prompt/metric 변경0 |
| P102A·P106B 계획과 결과093·101, 기준표·방법론·COMPASS·목록 | 현재 설계 및 실제 관측만 연쇄 반영 | 기존 실험 운영 절차 | 과거 음성·원로그·가중치 소급 수정0 |
| 새 단계 SH와 `experiments.tsv` | 실행 가능 선결 완료 뒤 등록 | 현재 독립 실험 수행 | 기실행 런처 복구·중복 학습0 |
| 새 evidence namespace와 새 raw log | 원답·기술 관측·자산 불변성 보존 | 현재 실험 | 파일별20MB 미만, 기존 출력 재사용/덮어쓰기0 |

## 영향도

- 코드: 기존 모델/optimizer/공식 task 계산은 재사용하고 새 orchestration만 분리한다. head는 실제 같은 초기값·gradient 재생으로 NS 정밀도 영향과 손실 경로 영향을 구분한다.
- 데이터: 알려진 V3 지도 결함 자료는 수치 진단에만 사용한다. 타세션 미채택 후보와 평가 정답은 train에 편입하지 않는다. 신규75M의 부족45.778269M은 작은 학습이나 반복 행으로 채우지 않는다.
- 테스트: CPU 합성 대조와 실제 backend oracle, 전체 스모크 신선도를 별개로 기록한다. 현재 기술 진단은 checkpoint 저장0·지능 판정0이다.
- 정본: 기존 외부4종 완료 표현은 총4모델(Tiny3+Falcon1)의 범위 오판이었다. 새 외부 모델별 완료/미실행을 실제 보고서와 연결한다.
- 우선순위: 이미 선택된 head 원인분리를 먼저 닫고, 독립 외부 기준선은 완료 모델의 공식 평가로 수행한다. 본학습이 불가능한 자료·구현 선결은 정확히 미완으로 남긴다.
- 자원: GPU 한 작업씩 실행한다. 일반 격리 NVML은 OS 차단됐고 허가된 비격리 읽기 조회에서4070TiS16GB/free14572MiB/계산PID0을 확인했다. 이 점조회가 장시간 안전을 보증하지 않는다. WSL `df`의561GiB는 가상 파일시스템 값이며 호스트 Z 여유로 보고하지 않는다.
- 시간: 새 실행은10/24 08:40 KST를 내부 마감으로 두고09:00까지 정리·보고 여유를 남긴다. 기존17시 만료 상수를 조용히 고치거나 옛 source hash를 새 실행에 사용하지 않는다.
- 보호: `datasets/TinyDataset/**`, 환경 지침·검사기, Git, 설치/다운로드, 기존 가중치·원로그 삭제는 현재 쓰기 범위 밖이다.

## 문헌·정반 역할

기존 사용자 허용의 sol6.1/max 역할 중 필요해진 두 담당만 호출했다. head 정 역할과 외부 평가 반 역할이 먼저 읽기 분석을 회수했고, root의 경로별 위임 뒤 각 새 diag/test 두 파일만 구현한다. Luna의 코드 수정이나 타세션 원천 작업은 없다. 총괄이 최종 계획·실제 실행·검증·기록을 소유한다.

## HF 실제 입장 오류 뒤 좁은 v2 보완

Stage8hWa는 tokenizer image special 범위와 loading_info set 직렬화에서 중단됐다.
기존2파일의 원형·SHA를 source_20261024_external_hf_v1에 정확 복사 보존했고, 실제 request의
ID 경계 검사와 실패 보고 회수 회귀만 같은 활성2파일에서 v2로 보완한다. 소스 수정 전에
P106B Stage8hWd/We/Wf로 사전등록했다. head source102와 제품·검사기는 변경0이다.
후속 SH/TSV의 단계와 source도 v2로 분리하며 어떤 미수행 v1을 실행 완료로 표기하지 않는다.

## Belebele 한국어·영어 공식 자료 준비 추가

원장23번의 평가자료 다운로드 허가와45번의 지명 평가를 연결한다. 공식 revision
`7899cdfa4e1e0d733fd77c848e2c273cb1d32be2`의 `data/kor_Hang.jsonl`1534047B와
`data/eng_Latn.jsonl`836071B만 독립 data_cache 경로에 취득한다. 공급자 Git blob OID와
실제 bytes 및 로컬 SHA256을 검산하고 CC-BY-SA-4.0과 출처를 기록한다. 모델·패키지·
환경 변경은 없다. 앞의 다운로드 제외는 이 명시된 기존 허가의 두 원자료에는 적용하지 않는다.

독립 `scripts/diag_p106b_belebele.py`와 `scripts/test_p106b_belebele.py`만 추가 허용한다.
고정 harness의 실제 YAML·ConfigurableTask·TemplateLM·metric과 동결된 HF/strict runtime을
재사용하며 기존 평가기와 전량 점수는 수정하지 않는다. 새 본문 저장은 root가 prepare로
수행하고 에이전트는 코드·합성 CPU 회귀만 소유한다. 질문·정답을 train이나 교사에 보내지 않는다.

세 방법을 비교했다. 전량만 집계하면 구현은 작지만 언어별 문맥 절단 차이가 남는다.
공통 무절단 문항만 실행하면 짧은 문항 편향과 공식900분모 누락이 생긴다. 따라서 공식
900×2 전량을 주 결과로 보존하고, 결과를 보기 전 고정7모델의 양 언어 모두 무절단인
문항 교집합을 보조집계로 분리하는 방식을 택한다. 교집합 분모는 사전 토큰화 전 미확인이다.
488개 link 묶음의 대응 bootstrap은 별도 구현·검증이 끝나기 전에는 수행했다고 주장하지 않는다.

영향은 공식 평가자료의 독립 로컬 취득과 새 평가 orchestration에 한정한다. 성능 개선 학습이나
새 지능 채택 문턱을 추가하지 않는다. canary→32문항씩 비용→조건부900문항씩 전량을
새 namespace에서 실행하며 한 GPU·08:40 내부 마감·20MB 미만 샤드·원형 보존을 유지한다.

v2 실제 cost32×6은 원형/독립재계수 뒤 writer의 정수label-key 제약에 걸렸다. 정상 키의
JSON 보존·충돌 거부만 v3로 수리하고 실제192raw의 전체 영수증 CPU 재생 검산을 추가했다.
원 v2소스/실패fallback은 보존한다. Stage9eW는 제품/공용검사기를 바꾸지 않고 기존
Codex전체스모크를 새 출력 namespace에서1200초 한도로 직접 실행해 source와 자산 불변을 확인한다.

## 지명 GPT2 Q4용 정확 빌드 헤더 취득과 독립 연결

현재 계산 위임만으로 다운로드를 새로 허용하지 않는다. 다만 이 대화의 별도 원지시
“벤치마크를 위해 필요한 자료 다운로드하여 벤치마크 및 평가도구 준비할 것”은 WIP23번에
보존돼 있으며 소스 취득과 패키지 설치를 구분한다. 이 기존 허가에 한해 공식 GitHub의
`b11396` 태그가 가리키는 commit `2e7c58c5477478c8cf6e199cfaa5dcd5a4319c81`의 필요한
헤더 include 폐쇄와 LICENSE만 새 data_cache 경로에 취득한다. 새 모델·패키지 설치0이다.
API 응답의 전체 commit은 설치된 common ELF의 build11396/commit2e7c58c54 및 과거
서버 실행 영수증과 일치한다. source header 일치가 수치 평가 정합의 증명은 아니다.

| 경로 | 동작 | 권한 근거 | 제외 |
|---|---|---|---|
| `data_cache/p106b_llama_eval_headers/2e7c58c5477478c8cf6e199cfaa5dcd5a4319c81/` | 공식 immutable source의 헤더와 LICENSE·취득 manifest 신설 | 위 평가 도구 다운로드 원지시 | package 설치, 원 실행 엔진 교체, 다른 commit 혼합0 |
| `scripts/p106b_native_llama_worker.cpp`, `scripts/p106b_native_core6.py`, `scripts/test_p106b_native_core6.py` | 독립 worker·공식 task adapter·CPU 회귀 신설 | 지명 GPT2 미완 회수와 현 계산 위임 | HFv3 동결 파일·제품·공용검사기 변경0 |
| 새 native namespace와 P106B 계획·결과·목록·WIP | 실행 전 설계 및 실제 근거만 반영 | 기존 연구 절차 | benchmark 정답 학습·타세션 쓰기0 |

코드는 기존 공식 task·TemplateLM의 토큰 경계와 독립 재계수를 재사용한다. 모델별 token ID와
Q4 실행 정밀도·KV/엔진 조건을 기록하고 HF FP32와 동일 계산 정밀도라고 주장하지 않는다.
새 데이터 schema와 배포 변경은 없고 benchmark 원답은 로컬 샤드로만 남긴다. head·HF와
실행 GPU를 공유하지 않으며 CPU 구조/shift/cache 회귀 뒤 root가 GPU canary·cost부터 연다.
일반 TensorFlow/HF 어휘 remap, 수동 ABI 구조 추측, 임의 모델 대체는 없다. 추가 패키지가
필수로 드러나면 그 경로는 보류한다. 구현 예상2~4시간과 수치 검산 비용은 아직 실측 전이다.

## 원장68의 같은 문항 CPU 대응 집계

추가 허용 파일은 `scripts/summarize_p106b_core6_pairs.py`와
`scripts/test_summarize_p106b_core6_pairs.py`, 새 결과 namespace뿐이다. 기존 사용자 지시의
paired95% CI·모델표와 현CPU 위임을 근거로 한다. 공식 task·metric·문항·정답·원 우도는
변경하지 않으며 새 임계값/모델 채택 규칙을 만들지 않는다. 원 raw는 읽기 전용이다.
닫힌 full과 exact correspondence를 검사하는 테스트, 무작위/최빈/길이 baseline 구분,
고정6과제 동일가중 case-paired bootstrap만 연결한다. 이전 임의 작은 표본과 다른 평가셋을
합치지 않는다. root가 GPU 작업을 계속 소유하고 이 집계는 CPU에서만 수행한다.

## 추가 공식 누락의 준비

scripts/diag_p106b_babylm_window.py와 scripts/test_p106b_babylm_window.py,
scripts/diag_p106b_lambada_default.py와 scripts/test_p106b_lambada_default.py만
추가 코드 허용한다. 원장20·47의 기존 평가 지시와 현 계산 위임이 근거다. 기존 공식AST/
model_runtime/TemplateLM/정식집계를 재사용하고 독립 제어·검산을 추가한다. 원 평가기나
마감globals를 runtime patch하지 않는다. Falcon 고정문법의 새cost/full, LAMBADAdefault의
모델별canary/cost/full만 새namespace에 작성한다. 보호TinyDataset/타세션/원로그는 제외다.
LAMBADA 공식default 원격LFS와 로컬en의SHA동일성을 실제 재계산해 새파일 취득은 필요없다.
패키지설치0이며 판단은 전체분모 뒤, GPU실행/SH/등록/결과는root만 소유한다.

## 새 평가 도구의 정적 오류 수리 범위

전수 정적 검사 Stage9fW에서 새 딕셔너리 `config.get/update`가 모델 TMTConfig로
분류된 이름 충돌, 통계 도구의 명시 `import tinylm` 누락, 새 CLI 두 항목의 등급표
미등록을 확인했다. 공용 검사기는 변경하지 않는다. 새 두 도구의 사전등록 소스를
각각 정확 보존하고 v2 namespace로 분리한 뒤 딕셔너리 이름·캐시 초기화·실패 종결만
보완한다. `scripts/flag_whitelist.tsv`에는 실제 파서가 소유한 `--output-stamp`와
`--read-only`의 읽기 및 독립 출력 경계만 추가한다. 점수·공식 방법·원자료·이미 완료된
v1 계산은 바꾸지 않는다. 보존 로그의 기존 C0 오류는 별도 미해결로 계속 공개한다.

## GPT2의 전량 시간 창만 분리

02:19 v2 GPT2의 실제 수치와cost는 통과했으나 전량 외삽8734.442초가 기술 상한7200초를
넘었다. 사용자의 승인 마감09시/내부08:40은 바뀌지 않는다. 다음 창으로 계속 미루는 안,
새 캐시 재사용 가속을 구현한 뒤 다시 수치부터 검증하는 안, 지금 같은 계산을 독립10800초
전량 창에서 수행하는 안을 비교했다. 새 가속은 더 많은 구현·검산이 필요하고 지명GPT2가
계속 미완으로 남으므로, 전체10800초가 남은 승인 창에 들어갈 때만 세 번째 안을 선택한다.

새 허용파일은 `scripts/p106b_native_window.py`와 `scripts/test_p106b_native_window.py`다.
동결된 native v2 source42713과 정확worker/원canary/cost를 읽기 전용으로 재사용한다.
공식 task·metric·숫자 문턱·singleton shape·캐시 계약은 변경0이다. 기존 execute의 검증이나
globals를 교체하지 않고 새로운 입장·소유수명·정리 orchestration만 추가한다. 새 출력과
보고서 source를 분리하며 내부shard lineage의 원 v2 tag는 출처로 그대로 보존한다.
예전 full HOLD와 원로그를 덮거나7200 통과로 소급하지 않는다. Qwen IQ2의15313초 외삽은
이10800 창에도 들어오지 않으므로 함께 실행하지 않는다. 총괄만 GPU를 실행한다.

## 새 시간 제어기 v1의 실행 전 반례 회수

root가121 CPU회귀를 통과한 뒤 독립 반 검토는 결과 저장 전에만 wall/deadline을 판정하는
반례를 찾았다. 디스크 저장이 경계 밖으로 지연돼도0으로 보일 수 있으므로 실제 모델에
사용하지 않는다. root가 정확 v1 두 소스와 source영수증을
`handoff/audit/source_20261024_native_window_v1/`에 보존하고 미실행SH를hold로 분리한다.
기존 두 활성파일의 새 v2만 최종 저장/재읽기 뒤 판정·실패 영수증과 지연회귀를 추가한다.
원 native v2·공식계산·원모델·원 canary/cost/HOLD는 변경0이다. 새source와단계는
별도로 고정하고 CPU와독립검토뒤에만실행한다. 이것은 실제 점수 음성이나 기실행 취소가 아니다.

반 검토의 두 번째 반례는 입장시 이미 쓴phase시간을forecast예산에서 빼지 않는 것이다.
새 v2 owner가 경과시간+원forecast+종결예비를 두 입장점에서 직접 검사한다. 원공유helper와
수치검사는변경0이며지연저장·wall만료·worker오류·표본누락회귀도새owner두파일에한정한다.

## Belebele v1의 같은 운영 경계 보완

원v1 과학계산과root85 CPU회귀는통과했으나독립검토가상속한finalize의시간감시누락을
확인했다. 후pin/가중치검증과idle조회·보고서저장이alarm밖이어서상한후에도0이될수있다.
실제자료취득과모델실행은0이며원소스두개와source영수증을
`handoff/audit/source_20261024_belebele_v1/`에보존한다. 같은활성두파일의v2만
잔여phase입장·종결전체유계화·최종종결영수증/실패veto·지연회귀를추가한다.
원공유LAMBADA/Falcon/HF source와공식계산을수정하지않는다. 외부상한과실제프로세스
종료시각도함께회수하고원자적파일시스템종료보장은주장하지않는다. 새source/namespace와
단계가고정되고CPU및반검토를회수하기전root도실제자료나GPU를열지않는다.

## GPT2 v2 실행의 실제 외부 소유 감시

추가 SH는 run_P106B_Stage8pWb_gpt2_verified_window10800.sh 하나이며 새 제어기5BA4870D를
고정한다. root128 CPU회귀0.766초와 독립 검토를 회수했다. worker가 별도 세션인 사실에
따라 부모 timeout10675+5초, 전체10800 중120초 정리 예비와 root의 실제 PID 소유 캡처를
병행한다. 환경변수는 무인 실행 방지일 뿐 실제 감독 증거가 아니다. root가 실제 소유
PID/시작 tick/실행파일을 새 audit에 보존하고 필요시 그 그룹만 종료할 수 있다. 이는 이번
GPU 실행 위임 안의 자원 정리이며 기존 모델·체크포인트·다른 세션 프로세스는 변경0이다.
실제 종결과 유휴 검증이 닫히지 않으면 원형 후보의0만으로 점수를 보고하지 않는다.

## Belebele 지문 단위 대응 통계의 추가 범위

원장68번이 요구한 공식 대응키·같은 지문 묶음의 CI를 별도로 회수한다. 추가 허용 코드는
scripts/summarize_p106b_belebele_pairs.py와 scripts/test_summarize_p106b_belebele_pairs.py
두 파일 및 독립 새 통계 출력뿐이다. 동결된 기존 평가기와 Core6 통계는 변경하지 않는다.
완결된 full 보고서·종결영수증·원raw만 읽고 실제 양언어 대응키900과 link488 및 사전
무절단898을 다시 확인한다. 문항 독립 CI를 지문 CI로 재명명하지 않는다. CPU 통계만
준비하고 모델·GPU·설치·자료취득·평가정답의 학습 편입은0이다.

## LAMBADA 원 소스의 외부 감독 실행

동결된 LAMBADA v2 helper는 Belebele의 준비 계보에도 포함되므로 수정하지 않는다.
기존 finalize의 단발 내부 timer 밖 후검사·저장 경계를 root가 실제 외부 cap·프로세스
종료·정리로 검산하는 별도 한 단계 SH만 추가한다. canary/cost/full 자동 연결은 하지
않고 root가 직전 실제 종료0과 원report·시간·소유 정리를 회수한 뒤 다음 단계를 호출한다.
추가 파일은 run_P106B_Stage8nWc_lambada_supervised_phase.sh와 명시 등록 및 원형이다.
원 sourceA400D971·공식5153행·metric·이전 준비는 변경0이다.

## 후속 SH의 독립 반례 반영

실제 GPU 실행 전 두 후속 SH를 독립 검토했다. 로그 준비 시간을 timeout 밖에서
소비하는 경로와 마지막 note 실패를 무시하는 경로가 있었다. 실제 CPU prepare만 완료한
Belebele Stage8oWb는 원소스와 명령을 done으로 보존하고 모델 실행은 새Stage8oWc SH로
분리한다. LAMBADA Stage8nWc는 아직 미실행이므로 같은 SH만 좁게 보완한다.
외부 timeout이 실행 runlog 전체를 감싸 로그 준비·실행·종결을 포함한다. note 호출도
유계화하고 실패하면9로 끝낸다. cap은 마지막 사전 note 뒤 계산하며 절대마감 예비는
120초로 둔다. root의 실제 시간·프로세스·소유 정리 검산은 계속 필요하고 원자적 종료는
보장하지 않는다. 모델 계산과 평가기 소스 및 기존 원로그는 변경0이다.

## 미실행 자동 런처의 보류와 감독 경계

사용하지 않은 LAMBADA Stage8nWb 자동 연속 SH는 `-hold.sh`로 보존하고 활성 등록을
해제한다. 실제 수행 이력이 없으므로 `-done`이나 실험 완료로 표시하지 않는다.
한 모델의 한 단계만 실행하는 Stage8nWc를 대신 사용하며 원 평가 소스는 변경하지 않는다.
새 두 감독 SH의 독립 합성 검토는 26개 경우를 통과했다. 실제 모델과 시간 제한 도구를
모두 모의한 검사이므로 GPU 실행이나 실제 강제 종료의 증거로 승격하지 않는다.

마감 직전 보류 안내 로그만 순회하면 안내가 08:40을 넘을 수 있는 경계가 남아 있다.
따라서 SH 전체가 그 시각에 원자적으로 끝난다고 주장하지 않는다. 총괄이 모델 실행의
08:40 마감과 실제 종료·정리를 직접 확인하며, 이후 09:00까지는 기록과 보고만 수행한다.
마감 직전 다수 모델의 새 순회를 시작하지 않는 운영 조건도 유지한다.

## 원장1·2 판독 범위의 독립 검토

반 역할 담당이 지정 체크리스트·읽기 감사·본학습 준비표·모델 종합표만 대조했다.
최근66건의 후보 작성은 이뤄졌지만 적용·채택이 미완이라는 결론이며,66건이 전부
미처리라고 해석하지 않는다. 번역의 두 사례 제안도 실제 성과이나 전체 코퍼스 완료가
아니다. 체크리스트의 범위를 새2,821행 검수 의무로 확대하지 않는다. 총괄이 이 구분을
받아들였고 원장 전체의 상태와 타세션 파일은 변경하지 않는다. 사람 전수 의미 검수를
새 보편 필수조건으로 만들지 않으며 구체적인 미채택·분량·구현·시간 선결로 보고한다.

## 닫힌 GPT2 원형의 대응 통계 연결

원장68의 대응 통계를 위해 새 파일 scripts/summarize_p106b_native_core6_pairs.py와
scripts/test_summarize_p106b_native_core6_pairs.py 두 개만 추가 허용한다. 기존 helper는
진행 중인 평가의 동결 소스이므로 수정하거나 복제하지 않는다. 새 얇은 연결기는 native의
원 report9와 terminal0 및 총괄 실제 종결 감사를 별도로 검증하고 원 객체를 그대로 기존
recount_model과 paired_intervals에 전달한다. 정상 HF 보고서처럼 바꿔 주입하지 않는다.
전체 문항·보기·정답·순서를 검산하고 기존7모델 각각과 GPT2의7쌍만 추가한다. 이미 본
점수의 사후 보조 분석이며 새로운 사전등록 품질 우위를 주장하지 않는다. 모델·GPU·설치·
학습은0이며 총괄이 새 소스 검토와 CPU 회귀 뒤 실제120초 이내 계산을 소유한다.

## Qwen3.5 HF 언어부의 별도 입장 검사

기존 보류를 해제했다고 가정하지 않고 새 두 파일에서 연결을 준비한다. 허용 파일은
scripts/diag_p106b_qwen35_text_core6.py와 scripts/test_p106b_qwen35_text_core6.py다.
기존 평가기와 원 가중치 및 설치 환경은 변경하지 않는다. 공식 text class의 언어320키를
일대일로 실제 값까지 검산하고 시각153키와 MTP15키의 명시 미사용을 기록한다. 전체488키를
소비했다고 주장하지 않는다. 토크나이저는 원 JSON의 실제 처리 부품과 원 config의 모든
추가 토큰·속성·이름을 함께 보존해야 한다. 잘못된 클래스의 재구성이나11개 선언 누락을
묵인하지 않는다. 정확 계약을 입증하지 못하면 모델 실행 전 보류한다.

먼저 총괄과 독립 반 검토가 새 소스 및 CPU 회귀를 확인한다. 실제 모델은 다른 GPU 작업
종료와 유휴 뒤 수치 canary 및 새 cost부터 실행하며 전량은08:40 안의 실측 예산이 있을
때만 진행한다. 모델 본학습·새 패키지·모델 다운로드·평가 정답의 학습 편입은0이다.

## 새 통계 연결기의 출력 연결 경계 반례

총괄54개 CPU 회귀 이후 독립 반 검토가 끊어진 출력 veto 심볼릭 링크를 exists만으로
놓치는 합성 반례를 찾았다. 실제8모델 통계는 아직0이다. 두 v1 소스와 정확 SHA 및
회귀 증거는 source_20261024_native_pairs_v1에 보존한다. 같은 활성 두 파일의 새v2에서
실패 표식의 exists와is_symlink를 함께 확인하고 실패 기록이 연결을 따라 쓰지 않도록
좁게 보완한다. 회귀와 namespace를 분리하고 원 수학 함수·기존 평가기·원 report는
변경하지 않는다. 수정 전 합성 통과를 실제 통계 완료로 소급하지 않는다.

## Qwen3.5 원본 BPE 직렬화의 좁은 후속

실제 CPU 토크나이저 검사에서 v1은 원 JSON과 공개 라이브러리의 직렬화 표현을 직접
비교하여 보류했다. 공식 Tokenizer 원본 roundtrip만으로 merges 문자열이 두 원소 배열이
되고 미기재 ignore_merges가 false로 명시되는 것을 총괄이 재현했다. 247587개 merge는
원순서와 내용을 모두 보존했고 다른 부품 차이는0이다. 이를 처리 규칙 변경과 혼동하지 않는다.

활성 두 파일을 수정하기 전에 정확 v1 파일과 SHA를
handoff/audit/source_20261024_qwen35_text_v1/에 복사 보존한다. v2의 기준은 공개 원본
roundtrip이며 원 JSON SHA·merge 원순서·모든 처리 부품과 config33·추가13·명명7은
별도로 검산한다. 모델 regex 변경이나 config 누락, 수치 문턱 완화는 허용하지 않는다.
새 합성 회귀·독립 검토·실제 토크나이저 검산 뒤에만 별도 GPU 입장을 판단한다.

v2 총괄84개 CPU0.275초와 독립84개0.310초 및 실제 tokenizer 검산을 회수했다.
새 Stage8sWb SH/TSV258은 한 단계만 실행하며 선행 실제 종료를 총괄이 확인하지 않으면
cost/full을 열지 않는다. flag_whitelist.tsv에는 새 파서의 prior-process-exit0 의미만 추가한다.
검사기 로직·사용자 기본값·원 모델과 공식 집계는 바꾸지 않는다. CLI stdout도 포함한
외부 timeout 및 실제 종료·종결·정리 검산을 계속 필수로 둔다.

## Qwen3.5 v2 실제 생성자 연결 오류의 최소 v3

실제 canary는 종료9이며 본체 생성자에 use_cache 키워드가 전달돼 실패했다. 명시 config를
준 공식 from_pretrained는 남은 kwargs를 생성자에 넘기고 해당 모델 생성자는 config만
받는다. config의 use_cache=False와 매 forward의 캐시 비활성은 이미 별도로 유지한다.

정확 v2 두파일은 source_20261024_qwen35_text_v2에 SHA로 보존했다. 같은 활성 두파일의
새 v3는 from_pretrained 중복 use_cache 키워드만 제거하며 엄격한 가짜 생성자와 AST
회귀를 추가한다. 실제 config 값·모든 forward·본체/토크나이저/우도/종결 문턱은 유지한다.
원 v2 실제 실패와 closure9 및 원로그를 보존하고 old SH는 해당 canary만 완료로 기록한다.
새 source·namespace·SH·등록에서 CPU와 독립 검토 후 다시 실제 canary부터 시작한다.

## Qwen3.5 수치 음성의 별도 관찰 범위

v3 실제 canary는 짧은 입력과 긴 입력의 공통 앞부분 수치 비교에서 실패했다. 이어진
정리 검사는 예외가 GPU 텐서를 보유했을 가능성이 있지만 현재 실제 점유량 자료는 없다.
원 v3 소스와 veto를 그대로 두며 전량 입장을 열지 않는다.

세 안을 비교했다. A는 현재 음성을 기록하고 끝내므로 비용은 작지만 형상과 미래 내용의
영향을 구분하지 못한다. B는 같은 길이의 미래 교체와 반복 입력, 원 길이 확장 및 층별·
우도 차이를 별도로 관찰한다. C는 새 커널이나 다른 정밀도로 바꿔 비교하므로 설치·조건
변경과 시간이 늘어난다. 이번에는 B를 택하며 문턱 완화나 모델 점수 채택은 하지 않는다.

새 허용 파일은 scripts/diag_p106b_qwen35_numeric_observer.py와
scripts/test_p106b_qwen35_numeric_observer.py뿐이다. 동결2B244C6B의 모델 runtime과
공식 로더·본체 값 검산을 재사용하고 새 관찰 namespace 및 SH/TSV만 추가한다. 기존
q.finalize나 model proof를 위장 통과시키거나 globals를 바꾸지 않는다. 수치 음성은
수치·위치·빈도로 먼저 보존하고 예상하지 못한 오류도 원 type/message를 남긴다.
전후 소스·자산·본체 및 소유 정리와 실제 부모 종료를 검산하며 전체600초 상한을 둔다.
관찰이 끝나도 기존 v3의 cost/full은 미실행이고 새 공식 점수·학습·교사 편입은0이다.

## 관찰 v1 정리 음성의 엔진 workspace 인과 관찰

관찰 v1은 예외 없이20행을 저장했지만 allocator 정리가 false여서 실제9로 종료했다.
PyTorch2.10 공식 CUDA 문서와 설치 header는 cuBLAS handle/stream workspace가
empty_cache와 별도로 유지되고 전용 clear로 해제됨을 명시한다. 이것을 실제 원인으로
확정하지 않고 증거가 필요한 후보로 둔다. 원 v1 두파일과 SHA는
source_20261024_qwen35_observer_v1에 정확 복사했고 이전 원형과 veto는 바꾸지 않는다.

A는 실패를 보존하고 끝내며 비용이 가장 작지만 원인을 남긴다. B는 등록 텐서와 Python
CUDA storage 메타 및 allocator를 측정하고,일반 GC/empty_cache 반복 대조 뒤 엔진
workspace clear 전후를 비교한다. C는 원 q.runtime의 cleanup 기준을 바로 바꾸고 전량을
여는 것으로 수치·입장 정책까지 바뀌므로 이번에 하지 않는다. root는 B를 선택한다.

기존 관찰기 두파일만 새 v2 TAG로 수정하고 원2B244C6B runtime은 계속 동결한다.
메타 계측은 값 복사·가중치 수정·새 출력 정답 판정 없이 수행하며 관찰 함수 자체가
CUDA storage 참조를 보유하지 않게 한다. workspace clear는 종료된 현재 프로세스의
캐시만 한 번 해제한다. 외부환경·다른 GPU 프로세스·패키지·제품 기본값은 바꾸지 않는다.
원 proof의 owned_cleanup_complete=false와 veto는 그대로이며 새 전후 통계에만 기록한다.
대조에서도 줄면 clear 효과로 귀속하지 않고 private API 부재는 보류한다. 이전 계약처럼
종결이 실패하면 그대로9를 남기며 원 canary/cost/full은 자동 개방하지 않는다.
추가 구현·합성 회귀는20~30분 추정, 실제GPU는 외부600/내부570초 상한과08:40 안이다.
