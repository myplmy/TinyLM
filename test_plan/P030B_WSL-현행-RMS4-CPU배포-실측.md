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

[SH](../run_P030B_Stage0W_wsl_cpu_d14_rms4.sh)는 m100s10/ko-en/300M의 d14_cla2_norecur와 d14_cla2_norecur_rms4 final 두 파일이 존재할 때만 시작한다. 기존 bench_infer.py에 둘을 **같은 명령**으로 전달해 CPU 1/4스레드, max_new128, reps3, KV cache on, drop-latent+int8-store+unpack-cache, logits_last_only, cache 정합과 psutil 외부부하·사전 idle10초를 기록한다. 같은 SH에서 mem_runtime.py가 **동일 저장·언팩·KV fp32 상태**의 실제 상주와 packed 식을 따로 적는다. Windows 역사 Stage5에는 full-logits였으므로 숫자를 직접 뺄셈하지 않는다.

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

실물 [run_P030B_Stage0W_wsl_cpu_d14_rms4.sh](../run_P030B_Stage0W_wsl_cpu_d14_rms4.sh). 사용자 새 smoke PASS 뒤 실행한다. 출력은 별도 P030B runlog이며 과거 P030 결과014를 덮지 않는다. 등록된 두 checkpoint 태그는 기존 자산이고 새 train tag/토큰/풀은 0이다.

## 8. 한계

WSL과 Windows의 다른 시점·스택을 직접 인과 비교하지 않는다. CPU 한 호스트/프롬프트/128 decode-token/두 checkpoint의 측정이며 다른 prompt 분포·저전력 엣지 기기 일반화가 아니다. bench_infer의 runtime_mb는 회계값이고 물리 RSS는 mem_runtime 별도 출력으로만 판정한다. 모델 로딩·CPU 실행은 사용자 소유다.

## 9. 실행 이력

- 2026-09-26: P030 Stage5/6/7b 기실행을 결과014 §15~18에서 재확인해 중복 SH를 만들지 않았다. P030B는 새 WSL 현행 d14 RMS4 계보를 묻는 별도 계획. 기존 bench/mem 도구와 사용자 SH 준비, 정적 검사 전/사용자 모델 NOT_RUN.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
