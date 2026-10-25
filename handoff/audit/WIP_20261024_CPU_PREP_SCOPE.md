# C 다음 A 다음 B의 CPU 전용 선결 준비

현재 사용자 승인: 원장1·2의 데이터셋 편입 작업 명시, 적절한 가속 패키지 비교와 필요한
최소 설치, 다음 주도적 실험의 C 다음 A 다음 B 선결 구현 및 CPU 테스트다.
GPU·체크포인트 실행·학습·전체 스모크는 이번에 실행하지 않는다.

## 파일별 영향과 권한

| 파일·경로 | 예정 동작 | 현재 권한 근거 | 제외 |
|---|---|---|---|
|handoff/WIP_20261022_작업원장.md|정상API로75~79 추가·현재 CPU 경계·원1/2 편입 잔여 갱신|원장 기입과 다음 GPU 작업 추가·중단 재개 지시|전체 원장 완료 아님|
|handoff/audit/WIP_20261024_CPU_PREP_SCOPE.md 및 준비 감사|신설|선결 준비의 영향·의존성·검증 기록|옛 감사 덮기 금지|
|docs/research/20261024_CAB_선결준비와_데이터편입.md|신설|패키지 비교와 실제 편입 절차 설명|모든 후보 채택이나 전량 정제 완료 선언 금지|
|docs/research/20261024_fused_ce_minimal_requirements.txt|고정 버전·wheel 해시 보존|필수 패키지 설치와 재현 준비|다른 빌드의 archive 바이트 동일성 보증 아님|
|data_cache/p102a_accel_runtime/ 아래 새 환경·고정 패키지·메타|필요 최소 패키지 설치와 출처/SHA 보존|필요한 패키지 설치 명시 승인|기존 tlm_torch·공식평가 환경 업그레이드/대형 모델 다운로드 금지|
|tinylm/train/fused_ce.py|기존 shared head의 선택형 외부 커널 연결 신설|B 선결 코드 구현 허가|기본값 교체·가중치 복제·묵시적 fallback 금지|
|tinylm/train/mtp_sft.py|기본 reference 보존·선택적 CE backend 접점|B 선결 코드 구현 허가|기존 loss/shift/mask/분모 변경 금지|
|scripts/test_p102a_fused_ce.py 및 scripts/diag_p102a_fused_ce.py|CPU 계약 회귀와 다음 GPU 정합 진입점|구현 테스트 CPU 허가·다음 주도적 실험 준비|이번 공식 GPU 커널 PASS·지능 성과 주장 금지|
|scripts/test_p102a_fused_ce_driver.py|미래 실제 업데이트 진입점의 합성 CPU 제어 회귀|B 선결 준비·중단 재개 승인|실제 모델·원배치·GPU 실행0|
|C 및 A의 최소 준비 도구/회귀|기존 도구 조사 후 빠진 접점만 개별 명시|C 다음 A 다음 B 선결 구현 허가|원 수치 문턱 완화·옛 veto 소급 변경·타세션 원형 편입 금지|
|scripts/p106b_native_iq2_window.py 및 scripts/test_p106b_native_iq2_window.py|새 시간창을 입력받는 독립 IQ2 전량 제어기와 합성 회귀|C 선결 구현 승인|원7200초/GPT2창/수치함수 변경0·실제모델0|
|scripts/p106b_admission.py 및 scripts/test_p106b_admission.py|검수 결정→root별 분할→토큰/manifest 연결과 합성 회귀|A 선결 구현 승인|실제 후보와 타세션 원형의 편입0·의미검사 자동 판정0|
|test_plan/P102A 및 P106B·계획목록·COMPASS·방법론05|현재 준비/다음 검증·제한 동기화|선결 구현과 다음 실험 준비|새 학습/벤치 수치 작성 금지|
|scripts/flag_whitelist.tsv|새 CLI9개를 실험용 등급으로 등록|새 선결 코드의 필수 메타데이터 동기화|검사기 완화·실제 커널 통과 등급으로 승격 금지|
|test_result/093_log_20261024_P102A_Stage2dW_cpu_fused_and_cab_contract.txt 및 새 정적 감사 원로그|실제 CPU 검증의 원문 로그 생성|구현 코드 CPU 테스트와 절차 검증|학습 로그나 GPU 결과가 아님|
|ai_dev_tool/Codex/08|실제 도구 오류 발생 시 원인/한계 추가|기존 절차 및 오류 기록 지시|환경 검사기·.agents·.codex 변경 금지|

## F3 패키지 경로 비교

| 안 | 장점 | 단점 | 비용·영향 |
|---|---|---|---|
|Liger만|기본 wheel이 작고 FP32 누적·sum API가 명시적|CCE의 어휘 전체 배열 회피 방식과 비교 불가|낮음·커널1종/접점1개|
|CCE만|큰 어휘의 head 메모리 절약을 직접 시험|배포 wheel과 최신 고정 source의 exact API가 달라 확인 필요|중간·출처와 exact 조건 동결|
|둘을 같은 어댑터로 별도 비교|TinyLM의 rank256·큰 V와 현재 dtype에서 실제 적합성을 구별|각 backend 수치/메모리/시간 회수가 필요|준비는 중간·다음 GPU 두 후보 대조|

이번 권장은 세 번째다. 기본 경로는 reference를 유지하고 Liger를 첫 연결 후보로 둔다.
큰 V 대비 작은 투영폭이 CCE에 유리할 가능성은 있지만 TinyLM에서 실측한 이득은 아니다.
GPU가 금지된 이번에는 설치·API/마스크·공유 gradient·기본값 보존 CPU 계약까지만 확인한다.
공식 커널의 실제 GPU 정합과 optimizer 민감도·전체 본학습 시간 전에는 기본 채택하지 않는다.

## F4 축별 점검

| 축 | 영향 | 경계 |
|---|---|---|
|코드|선택 CE 접점과 독립 진단|기존 p102a_contract 및 mtp_sft 마스크/분모 재사용·중복 수학 금지|
|데이터|편입 절차/명세 준비|원문·타세션 후보 불변,synthetic 테스트만 사용|
|테스트|현재 CPU 회귀 추가·기존 MTP 회귀 영향|공식 GPU 커널·전체 스모크는 다음 새 허가창|
|정본 문서|계획·속도 방법론·나침반·원장 연결|새 결과인 척하지 않고 STATIC_ONLY/NOT_RUN 표시|
|부채/우선순위|C 다음 A 다음 B의 선결을 분리|가속 미완을 데이터 준비의 필수 중단 사유로 삼지 않음|
|GPU/모델 권한|이번 불허|CUDA_VISIBLE_DEVICES를 비우고 CPU tensor 계약만 검증|
|소유권|보호 경로 및 타세션 원형 접근/변경 제외|기존 로그·가중치·게시본 삭제/덮기0|
|비교 유효성|다음 실험에서 자료·부모·배치·optimizer·노출 고정|같은 소규모 기술 검증을 지능 향상으로 판정하지 않음|
|증거 수준|설치·CPU·실제 GPU·본학습을 구분|패키지 import 성공은 커널 실행/가속 성공이 아님|

필수 의존성은 실제 배포 메타와 현재 설치를 먼저 대조한다. 기본 Torch/Triton/Transformers는
업그레이드하지 않으며, extras와 사용하지 않는 공식 평가 파이프라인을 일괄 설치하지 않는다.
파일별 결과는20,000,000B 미만으로 유지한다. 이번 Git 쓰기와 삭제는0이다.
