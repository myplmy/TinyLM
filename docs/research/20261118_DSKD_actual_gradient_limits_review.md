# 2026-11-18 DSKD 원실험의 미분 제약과 실제 연결 잔여

사용자161/원61의 후속 읽기 검토다. 소유 Codex가11월13일에 실제 종료0으로 닫힌 native 미분 보고서의 scalar만 대조했다. 새 모델·원feature·체크포인트를 읽거나 학습하지 않았다. [원결과101§604](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)와 [이번 계산 영수증](../../handoff/audit/research_20261118_01a1e647/DSKD_CLOSED_SCALAR_CONSTRAINT_REVIEW_v1.json)이 근거다.

## 1. 관측 정본

원actual session76967/exit0의 report SHA62CEFA43B5D08053AA4F62A4D67CA7CF8E0C0AA1B6089A6CF065613E874F4FFA를 ROOT 영수증과 대조했다. 원CE772/KD538·학생157파라미터 tensor·본체155와 공유embedding/head2를 유지한다. 원실험은 optimizer update0이고 품질 판정을 하지 않았다.

| 공간 | CE norm | 두 KL 합 norm /CE | CE와 두 KL 합 cosine |
|---|---:|---:|---:|
| 학생 전체157 tensor |3.401442|32.855795|−0.171101|
| 공유embedding/head 제외 본체155 |3.303458|33.314970|−0.161058|
| 공유embedding/head2 |0.810541|23.975086|−0.411857|

33.315배와−0.161은 **본체 공간**이다. 이를 전체157 tensor의32.856배/−0.171과 섞지 않는다. 별도 새 투영 Pt의 CE gradient norm50.633254도 이 학생 공간과 다른 변수다. 큰 신호가 새 투영에서만 생겼다는 해석은 원측정과 맞지 않는다.

## 2. 계산과 적용 범위

고정한 같은 지점에서 CE 미분을 g, 두 KL 합 미분을 k라 하면 g와 합성미분 g+beta*k의 내적은 g·g+beta*(g·k)다. 이는 그 한 점의 **무한소 음의 Euclidean 미분 방향**에 대한 계산이다. 실제 Muon/AdamW의 momentum·preconditioning·weight decay, clipping 이후 방향이나 유한 step의 CE/품질 변화는 이 식으로 보장하지 않는다.

| 공간 | beta=1일 때 내적 /CE norm 제곱 | 내적이 양수인 beta의 상한, 진단 계산 | beta=0.03의 KD norm /CE |
|---|---:|---:|---:|
| 학생 전체 |−4.621645|0.177884 미만|0.985674|
| 본체 |−4.365626|0.186372 미만|0.999449|
| 공유embedding/head |−8.874300|0.101273 미만|0.719253|

원계수1의 신호는 해당 고정 지점에서 CE 미분과 반대 내적을 만든다. 이 사실은 곧 실제 Muon의 CE 증가나 DSKD 전체 실패를 관측했다는 뜻이 아니다. 약0.03은 기존 결과의 동일 norm 환산과 연결되는 **진단값**이며 생산 계수를 선택하거나 새 학습으로 검증한 값이 아니다. 새 beta 실험·품질 판정·수치 문턱 변경은0이다.

## 3. 투영의 일부 개선과 일반화 미확인

[원결과101§605/608](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)는 작은 투영402학습위치를100% 맞춰도 보류 CE가6.754944→19.231279로 악화했음을 보존한다. 확장한3220학습/893dev의100회 보정에서는 dev top1이135→425/893, CE가6.959716→6.125227로 개선됐다. 그러나 같은 옛보류136의 CE는6.754944→7.372004로 나빠졌다.

따라서 투영 보정에 실질적인 국소 개선이 없었다고 말하지 않는다. 동시에 학생 본체 학습·일반 정답·대화 개선이나 생산 채택으로도 올리지 않는다. 두 실행의 학습위치 수와 노출예산이 달라 순수 다양성의 인과 효과를 분리한 비교가 아니며,25회 지점을 사후 최종 승자로 고르지 않는다.

## 4. provider 상태 검토에서 확인한 실제 잔여

확인한 원 scripts/diag_p106b_dskdv2_bridge.py:student_cost는 원래16개 microbatch×8행을 pad_records로 구성하고 그 안에서 모델을 직접 호출한다. 새 scripts/p106b_dskdv2_training.py의 CPU owner는 callback으로 원문항 한 행의 전체 StudentFrame을 받는다. 확인한 원진단·소비자·새학습기 사용부에는 실제 생산용 StudentFrame 연결부가 없다. 이 한정된 사용부 검토를 저장소 모든 경로의 부재 증명으로 확대하지 않는다.

새 CPU fixture의 한 행 호출은 native batch8 수치·속도·메모리를 검증하지 않았다. 실제 연결 시 원래 batch 구성/문서·shift·owner/분모, body graph 수명, padding과 모델의 cache/hybrid 상태를 명시해야 한다. Provider가 따로 가진 generator/cache·교사의 내부 상태는 model/source/세 전역RNG를 저장했다는 이유만으로 복구된 것이 아니다. 현재 형식은 이를 caller 소유·미인증으로 남긴다. 선언만 추가한 범용 상태 스키마를 실제 연결 완료로 계산하지 않는다.

Reader17/consumer40/producer21/multi-window19/CEKD24/별도LR10은 닫힌 CPU 구현 결과다. 실제 Native/corpus/provider/teacher 연결, 정식TRAIN 권리·분할·편입, BF16/CUDA/full비용·8h/75M과 학생 품질은 남는다. 자동승인 거절 뒤 새 모델/GPU 실행과 우회는0이며 원로그·원함수·기존 데이터/CP·타정제는 바꾸지 않았다.

## 5. 같은날 후속: 별도 microbatch 어댑터의 수치 연결

앞선§4의부재확인은그검토시점의사용부를말한다. 이후 [101§650](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-causal-microbatch-frame-adapter-cpu)에서별도 CausalMicrobatchFrames를신설했다. 원토큰단한번shift/pad·고정batch8과마지막real행까지의공유graph수명을새CPU8/전체55변수참조로검증했다. 기존행단위소비자/학습기25소스는보존했고자동연결·실제Native/BF16·전용RNG/전체재개·교사/정식TRAIN/75M·학생품질은여전히미완이다. 원미분/생산계수판정은바꾸지않는다.
