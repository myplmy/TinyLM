# P030B — WSL 현행 d14 RMS4 CPU 배포 속도·상주 재실측

> 계기: [P030 계획](P030_추론속도-KV캐시-CPU배포.md) Stage5/6/7b와 [결과014 §15~18](../test_result/014_20260731003000_P030-CPU추론실측-양자화오버헤드.md)은 **이미 Windows 사용자 실측 완료**다. 이전 C3의 “Stage5 미실행” 판단을 정정하고, 새 WSL·Muon RMS4 체크포인트·last-only 생성경로를 별도 suffix로 연다.

## 1. 왜

프로젝트 배포 바닥은 CPU 단일 코어 ≥15 tok/s다. 옛 Windows d14_cla2_norecur는 19.19 tok/s(결과014 §16)였지만 새 d14_cla2_norecur_rms4 checkpoint의 현재 WSL int8-store+unpack-cache 경로는 직접 잰 적이 없다. P030 Stage5의 d12/d16 승자 실측을 다시 돌리면 중복이다. WSL 새 함수를 그 값의 PASS로 승격하지 않는다.

## 2. 질문

| # | 질문 | 이유 |
|---|---|---|
| Q1 | 현 WSL d14 RMS4가 같은 실제 CPU 배포 경로에서 1코어 15 tok/s를 넘는가 | 현재 후보의 사용자 체감 바닥 |
| Q2 | 같은 d14 구조의 옛 optimizer checkpoint와 같은 세션에서 속도·외부 CPU 부하가 얼마나 다른가 | 날짜·환경 교락을 줄인 기술 대조 |
| Q3 | 속도에 사용한 int8-store/unpack-cache 상태의 실제 물리 RSS·KV는 얼마인가 | packed/runtime 식을 물리 상주로 오인 방지 |

## 3. 예측 — 성공·실패 모두

Windows 옛 d14 무재귀 19.19 tok/s라 현 RMS4도 15를 넘을 수 있지만 WSL CPU·현재 last-only 기본값·OS 부하가 달라 방향을 예측만으로 채택하지 않는다. optimizer 자체는 같은 구조의 inference 연산량을 줄이지 않지만 가중치 값·캐시·CPU 스택에 따른 시간 차이가 생길 수 있다. int8 unpack-cache는 packed 저장값만큼 작게 상주하지 않을 가능성이 높다.

## 4. 단계 설계

### Stage0W — 정확 두 체크포인트 같은 세션 CPU 게이트

SH `run_P030B_Stage0W_wsl_cpu_d14_rms4.sh`(완료 명령은 [결과100 §4](../test_result/100_20260926_P030B-1코어-바닥은-통과했지만-상주-목표는-미달이다.md)에 보존)는 m100s10/ko-en/300M의 d14_cla2_norecur와 d14_cla2_norecur_rms4 final 두 파일이 존재할 때만 시작한다. 기존 bench_infer.py에 둘을 **같은 명령**으로 전달해 CPU 1/4스레드, max_new128, reps3, KV cache on, drop-latent+int8-store+unpack-cache, logits_last_only, cache 정합과 psutil 외부부하·사전 idle10초를 기록한다. 같은 SH에서 mem_runtime.py가 **동일 저장·언팩·KV fp32 상태**의 실제 상주와 packed 식을 따로 적는다. Windows 역사 Stage5에는 full-logits였으므로 숫자를 직접 뺄셈하지 않는다.

### Stage1W — 조건부 품질·배포 판단

1코어 속도가 15 미만이거나 실제 상주가 40MiB 목표를 벗어나면 CPU 병목/상주 항목을 분해해 새 커널·KV/형상 대안을 판단한다. 속도와 상주가 모두 바닥을 넘더라도 언어 품질은 이 벤치가 재지 않으므로 기존 동일 tokenizer·full-val/한영 과제와 결합해야 한다.

## 5. 판정 기준

| 관측 | 기술 판정 |
|---|---|
| exact 두 checkpoint 없음, cache 정합 실패, 측정 0행 | 실행 실패; 속도 PASS 주장 금지 |
| 현 RMS4 1코어 median tok/s≥15, 외부부하 행이 서로 유사 | 이 WSL 세션의 CPU 속도 바닥 후보 |
| 실제 물리 RSS+KV가 40MiB 초과 | 40MiB 배포 동시 충족 아님; packed 값을 대신 쓰지 않음 |
| 4스레드만 ≥15 | 단일 코어 바닥 미달, 참고 출력 |
| 두 checkpoint 속도 차 | 같은 구조지만 학습 가중치/OS 실행 경로의 기술값; optimizer 인과·Windows 대비 향상 아님 |

## 6. 비용

| 단계 | 예상 | 자원 |
|---|---:|---|
| Stage0W 동일세션 두 checkpoint CPU decode+RSS | 0.6h 상한 | 사용자 WSL CPU 단독/감시, GPU0 |
| Stage1W 후속 | Stage0W 결과 뒤 산정 | 새 학습 없음 |

## 7. 실행

실물 `run_P030B_Stage0W_wsl_cpu_d14_rms4.sh`는 사용자 smoke PASS 뒤 실행을 완료했다([결과100](../test_result/100_20260926_P030B-1코어-바닥은-통과했지만-상주-목표는-미달이다.md)). 출력은 별도 P030B runlog이며 과거 P030 결과014를 덮지 않는다. 등록된 두 checkpoint 태그는 기존 자산이고 새 train tag/토큰/풀은 0이다.

## 8. 한계

WSL과 Windows의 다른 시점·스택을 직접 인과 비교하지 않는다. CPU 한 호스트/프롬프트/128 decode-token/두 checkpoint의 측정이며 다른 prompt 분포·저전력 엣지 기기 일반화가 아니다. bench_infer의 runtime_mb는 회계값이고 mem_runtime의 프로세스 RSS는 allocator·런타임에 오염될 수 있다. 모델 상주 목표는 최소 텐서+KV 회계와 별도 깨끗한 프로세스 측정을 구분한다. 모델 로딩·CPU 실행은 사용자 소유다.

## 9. 실행 이력

- 2026-09-26: P030 Stage5/6/7b 기실행을 결과014 §15~18에서 재확인해 중복 SH를 만들지 않았다. P030B는 새 WSL 현행 d14 RMS4 계보를 묻는 별도 계획. 기존 bench/mem 도구와 사용자 SH 준비, 정적 검사 전/사용자 모델 NOT_RUN.
- 2026-09-26 사용자 Stage0W: [결과100](../test_result/100_20260926_P030B-1코어-바닥은-통과했지만-상주-목표는-미달이다.md) — 속도/상주 두 도구 exit0, 1코어 두 팔 32.64/37.49 tok/s로 15 바닥 통과. int8 경로 텐서116.2+KV10.5=126.7 MiB로 40 상한 미달. 고정 측정 순서·체크포인트 가중치 차이가 있으므로 1.149× 원인 귀속 금지. 자동 문구의 동점 회계 판정·2× 상한 설명 오류는 원시 측정과 분리해 후속 교정한다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-09-27 Stage0W 두 훈련 JSON 직접 재검산

[결과100 §5](../test_result/100_20260926_P030B-1코어-바닥은-통과했지만-상주-목표는-미달이다.md)에서 정확 두 훈련 JSON을 직접 읽어 같은 m100s10 dense·300,023,808 draw·exact600M 풀·seed1337·dense 부모·CLA2·skip0을 확인했다. optimizer는 AdamW 대 Muon RMS4로 다르다. 따라서 §1의 예전 훈련 메타 미열람은 해소됐지만, 학습 가중치와 고정 실행 순서가 달라 1코어1.149×을 optimizer 순수 추론 효과라 할 수 없다. 상주126.7MiB 미달 판정은 유지한다.

## 10. 2026-09-27 Stage0Wb — CPU 모델 측정 순서와 RSS 독립 프로세스 게이트

직전 Stage0W의 d14 두 체크포인트 속도비1.149×은 **A→B 고정 순서**이고 현 int8 경로 텐서+KV가126.7MiB라 40MiB 목표는 이미 실패했다. 이번 후속은 구조·학습을 바꾸지 않고 고정 순서 편향 및 프로세스 RSS를 다시 잰다. `run_P030B_Stage0Wb_cpu_order_rss.sh`는 기존 두 final을 `paired_eval.py --check-inputs`의 공통 경로 resolver로 모델 로딩 전 확인한 뒤, 같은 한 문장·CPU 1스레드·128 decode·reps3·int8-store/unpack-cache·last-only·CPU watch로 **A→B→B→A 각 새 프로세스**를 실행하도록 준비했다. 각 팔 뒤 별도 `mem_runtime.py`도 같은 A/B/B/A 순서로 별도 프로세스에서 실행한다. 현재 지시상 Codex의 런처/모델 실행은 금지이므로 코드는 정적 상태이고 수치 `NOT_RUN`이다.

예측: 고정 순서가 주원인이면 A/B의 속도 차가 순서 반전에서 줄거나 부호가 바뀐다. 방향이 유지돼도 가중치 값이 다른 두 최종 모델이므로 optimizer가 순수하게 inference를 빠르게 했다고 말할 수 없다. RSS가 실제로 작아지더라도 물리 텐서+KV 126.7MiB와 양립하는지 먼저 확인한다. 40MiB 목표 미달을 속도 PASS로 상쇄하지 않는다. 외부 CPU 부하·시스템 cache·clock이 크게 다르면 기술 판정 보류다.

| 비용·선결 | 값 |
|---|---|
| 사용자 실행 | WSL CPU 단독, GPU0, 약1.0h 상한(8개 독립 프로세스·각 benchmark 10초 idle) |
| 자산 | 기존 두 final checkpoint와 legacy tokenizer, 새 학습·다운로드·저장0 |
| PASS 한계 | 입력 정합·ABBA 8행 출력·프로세스별 RSS, 속도비는 조건부 설명값 |
| 중단 | 한 팔 오류/외부 CPU 부하 편차·RSS/텐서 회계 모순이면 채택 주장 금지 |

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 11. 2026-09-27 Stage0Wb 사용자 실행·예측 대조

[결과100 §6](../test_result/100_20260926_P030B-1코어-바닥은-통과했지만-상주-목표는-미달이다.md)의 사용자 runlog에서 선검사1·1코어 decode4·별도 RSS4 호출은 모두 종료0이다. A(기존 d14) 34.27/33.51, B(RMS4) 35.68/32.15 tok/s였고 각 두 값 평균 B/A는 **1.0007×**다. 앞 A→B 쌍은 B 우세, 뒤 B→A 쌍은 B 열세로 뒤집혔다. 이전 Stage0W의 **1.149× 일방향 우위는 재현되지 않았다**는 점에서 고정 순서/시점 변동 후보가 지지되지만, 클럭·온도·내부 reps3 원시값이 없어 원인 확정은 아니다. 두 모델 모두 WSL CPU1 ≥15 tok/s는 유지한다.

새 프로세스의 시작 RSS는 각각562.6~562.8MiB였고, 변환 후 RSS는 A 2,096.9/2,071.9MiB, B 2,025.0/2,025.1MiB다. 이는 **파이썬/Torch 할당자까지 포함한 프로세스 RSS**로, 두 모델의 물리 가중치 차라고 귀속하지 않는다. 두 팔의 변환 후 텐서합산116.2MiB와 KV10.5MiB는 같고 **최소 회계126.7MiB > 40MiB 목표**도 그대로다. 별도 프로세스로 앞 단계의 이어받은 RSS 교락은 줄였지만 실제 packed 배포의 40MiB를 달성한 것은 아니다.

§3 예측 중 “고정 순서가 주원인이면 순서 반전에서 속도 차가 줄거나 부호가 바뀐다”는 이번 2+2 출력에서는 **방향상 일치**한다. 그러나 실험은 두 가중치·optimizer가 같이 다른 모델의 단일 프롬프트 시험이므로 `OPTIMIZER_CAUSAL_SPEED`는 `NOT_RUN`이다. 다음 실험 가치는 추가 반복 횟수보다 실제 packed 상주 경로 구현·그 형상에서의 품질/CPU 예산 검증에 있는지 frontier와 사용자 목표에 다시 대조한다. Stage0W/Stage0Wb는 기술 판독 완료, 전체 P030B 축은 40MiB 미달 원인·대안이 남아 진행 중이다.
