# 실험계획 P013 (S2) — seq-length warmup 초기 스텝 절감 (소규모)

> 2026-10-27 현재 상태: 아래 옛 소규모 품질 판정 제안은 현재 실행 기준이 아니다. 사용자는 본학습 전 작은 학습으로 지능/벤치 성과를 판단하지 않도록 정정했고, 데이터 정제가 끝나기 전 추가300M 학습을 금지했다. 현재 후속은 독립 회계·수치·비용 선결만이다. 종전의16배는 고정시퀀스수에서attention의L제곱항 비율이며, 같은token/update나전체시간의16배 가속이 아니다.

## 목적
어텐션 O(L²) — 초반 seq를 짧게(256→1024) 성장시키면 **초기 스텝이 얼마나 싸지는지** 소규모로 측정.
절대 학습시간 절감 여부와 최종 품질 영향을 본다.

## 방법
- seq 스케줄: 전체의 0~20% 구간 256, 20~40% 512, 이후 1024(예). Loader/train에 seq 스케줄 추가(구현 필요).

## 조건 (소규모)
- m100 짧은 런(예: --steps 400) 또는 tiny 에서 **seq-warmup on/off**의 (a) 초기 구간 ms/step, (b) 전체 wall time, (c) 최종 val 비교.

## 판정
- 초기 스텝 시간 절감%(이론상 (1024/256)²=16배 싼 구간이나 다른 오버헤드로 실제는 작을 수 있음).
- 커리큘럼이라 **결과가 바뀌므로** 최종 val 영향도 확인. 이득이 초기 구간에 한정되는지.

## 비고
- 소규모 검증 후 이득이 유의하면 본 실행 옵션으로 승격. 아니면 폐기.

## Stage0W/Stage1W — 같은 full-window의 문맥 분할 선결

### 목적과 가설

원장57의 미구현 일정을 준비한다. 같은full1024 window를분할하면입력/정답위치를보존하면서문맥길이를바꿀수있고attention비용은줄수있다. 그러나micro호출/삼진화·head·재계산·optimizer비용때문에전체속도는개선되지않을수있다. 짧은문맥의함수/gradient는고정1024와다르며동률을가정하지않는다. [문헌·정 검토와세대안](../docs/research/20261027_문맥일정과_MNTP_접점.md)에선택근거를남겼다.

### 비교조건과 독립변수

기존Loader를고치지않고매update동일16개의(8,1024)x/y를얻는다. x/y를함께4×256/2×512로분할하고micro8로재배치하여accum64/32/16과131072 input/target을맞춘다. 순서·원y마지막위치·같은sampler16호출을유지한다. 짧은블록의context/position reset은의도한변수이고PADcrop·packing·새randomdraw와구분한다. 최초NTP-only/eager/R1·KD/MTPoff다. SFT/ignore mask·부분tail·틀린shift는거부한다.

2289update는300023808 draw이지정확300000000·고유token·순방문이아니다. 예시정수일정458:256/916:512/2289:1024는회계fixture이며실제본학습프로필채택이아니다. 모델최대/validation1024를유지하는제품통합과최종품질은후속미완이다.

### Stage0W CPU 계약

새 `tinylm/train/context_curriculum.py`는기존sampler를호출하는별도모듈이며기본trainer/CLI를변경하지않는다. source SHA·계획schema/hash·다음global update·소비draw/target/source-call·optimizer적용횟수·PCG64를완전한update경계에서저장한다. 중간micro/원천오류/불일치계획의재개는거부한다. source RNG/회계재개만이며모델·optimizer·Torch/validation RNG까지포함한전체학습정확재개가아니다.

실제원천을읽지않고가상window로원target위치별정확1회소비·분모·단계전환·JSON왕복재개를검산한다. 독립token별CE모델의gradient대조는분모검증이며실제causal모델의문맥동률주장이아니다. 반검토의scratch재사용반례는draw직후독립snapshot으로수리하고복사비용도포함한다. 종전11회귀12349/0·분모추가12회귀95641/0·snapshot13회귀77144/0의서로다른범위를보존한다.

### Stage1W 실제 모델의 기술 비용 후보

Stage0의전체가상위치계약/명시정적/소스봉인뒤,기존완료Native595-Q의동일가중치로256/512/1024의forward+backward비용만측정할수있다. 같은3개가상full-update의모든입력/target를재사용하고순서1024/256/512/512/256/1024에서블록당warm1·실측2로고정한다. micro8/원scale·anneal1·checkpointON·BF16 eager를유지하고각길이의full target합계로정규화한다. source생성/입장/체크포인트로드·준비와H2D/분할/forward/backward시간을구분한다. optimizer/교사/새학습자료/체크포인트저장/새품질평가는0이다. 이비용이optimizer·compile·validation·저장을포함한본학습wall을대신하지않는다.

### 권한·선결·실패·비용

사용자96/97의27일17시까지CPU/GPU·가용VRAM내허용을따른다. 다른정제전용자료/코드/원장·보호TinyDataset·원CP덮기/삭제·추가300M·설치/외부취득/Git은0이다. Stage0 CPU상한120초, Stage1 GPU상한900초와종결180초를고정하고다른GPU프로세스유휴/원CP·소스불변·gradient정리/모델해제/소유CUDA0을요구한다. GPU전체가안맞으면미실행으로남긴다. 새profile/새namespace만쓰며예산미완8·오류9·기술완결0을구분한다. 결과/원로그의파일별20MB상한을지킨다.

2026-10-27 Stage0/1의 기술 실행은 [결과106](../test_result/106_20261027123926_P013-같은토큰의-짧은문맥은-메모리를-줄였지만-느렸다.md)으로 완료했다. 전체786432위치/96호출 계약30298/0과 실제모델 F+B79138/0·98.952초를 회수했다. 같은131072토큰의 중앙값1024/512/256은3.563/3.993/7.974초로 짧은문맥이 느려 기본가속으로 비채택이다. allocated peak는4815.092/3108.076/2254.568MiB로 줄었지만 reserved는 앞블록 cache가 섞인다. 제품통합·optimizer/compile포함wall·본학습최종1024품질은 아직NOT_RUN이며 정제본채택·추가300M을 승인하지 않는다.

예측대조: 위치·분모·RNG보존은 실제검산됐다. attention 절감이 전체 F+B 가속으로 이어질 수 있다는 긍정 예측은 현 micro8 분할에서 기각됐고, micro호출/GEMM 등 비용으로 느려질 수 있다는 부정 예측과 부합한다. 원인별 비용분해를 수행한 것은 아니다. 기존 P021B의 micro-token 유지 이력은 재실행 전에 따로 대조해야 한다. 완료 두 SH는 전체명령/SHA를 결과에 보존하고 -done으로 개명했으며 삭제0이다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
