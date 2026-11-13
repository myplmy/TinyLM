# Soft-DTW GPU 부품 검증 — 모델 학습과 구분

원장62에서CPU8/경로열거/유한차분을닫은수학reference를기준으로미구현GPU DP를준비한다.
사용자115의17시까지CPU/GPU·코드구현위임범위이며설치/다운로드/새환경은0이다. 현재로컬의
torch2.10.0+cu130·triton3.6.0과CUDA libdevice exp/log가있음을읽기/CPUimport로확인했다.

| 안 | 방법 | 장점 | 한계·영향 |
|---|---|---|---|
| A, 선택 | anti-diagonal Triton forward/backward의FP64 단일cost prototype | Python셀별그래프없이같은DP수학을검사 | 한CTA라장치활용이낮을수있고생산batch/native연결은미완 |
| B | Torch anti-diagonal 벡터화 | 구현이비교적단순 | 길이마다다수커널호출/그래프부담 |
| C | 외부GPU Soft-DTW패키지설치 | 기존구현활용가능 | 새설치허가·버전/미분검증이필요해현재보류 |

새helper/driver/SH와소유계획/결과/원장만변경한다. 제품/공용checker/원CP/원cache/타정제/
TinyDataset/라이브러리소스/Git은변경하지않는다. 컴파일캐시는새data_cache태그로격리한다.
모델/학습/optimizer/CP저장은0이며전체DWA/일반지능/본학습가속성과로승격하지않는다.

## 수학과 수치 게이트

forward는각anti-diagonal의이전두줄을보관하고안정적softmin과세전이확률을계산한다.
backward는역방향DP로확률을전파한다. FP64의libdevice exp/log를사용하고최초에는2차미분을
지원하지않는다. 입력은유한·연속CUDA FP64 cost2D, 각변1~1024·최대1048576셀로한정한다.

같은CPU reference의작은8×12/16×24/32×48 및1×1/1×17/17×1에서loss와costgradient를
atol1e-9/rtol1e-8로대조한다. FP64 작은DP의누적roundoff를넘는공학허용치이며모델가족의
sigma를복사한것이아니다. 실패시문턱을늘리지않고source/원실패를보존한다. 큰256/512/1024
cost는전치loss/gradient,endpoint미분1·미분0~1·합max(N,M)~N+M−1의경로성질을검사한다.
긴CPU autograd참조를억지로실행하지않으며큰shape의완전독립일치는NOT_RUN으로남긴다.

최초컴파일포함wall과warm CUDA event/wall을분리한다. 각shape의메모리는이DP부품만이며
모델peak와같지않다. 모델/GPU전수스모크/전체학습0·원소스SHA불변과CUDA0/0·실제종료를닫는다.
예상GPU1~5분/상한20분·17시전15분정리여유다. 빠르지않거나수치음성이어도그대로기록한다.

근거: [Soft-DTW 저자원문](https://proceedings.mlr.press/v70/cuturi17a.html),
[Triton gather](https://triton-lang.org/main/python-api/generated/triton.language.gather.html).
이는DWA의CMA/두표현/native분모나self-band정책을완성한것이아니다.

## 실제v1실패와사전고정v2수리

actual44558 종료1·내부9이다. 1행/열3개는맞았으나8×12에서loss차5.520663/미분차.997039로
중단했다. 생성TTIR의loop-carried는prev하나뿐이고diag의gather는초기inf상수를읽었다.
Python벡터대각reference는원DP와같고, 대각을뺀DP+gamma log2는실패GPU값과맞았다.
동일tensor객체alias초기화작성에문제가있으므로새v2는두초기상태를독립tl.full로만든다.
역방향두next도같이분리하고line별대입으로명시한다. helper/driver/test와cache를새v2로분리해
원source/IR/보고서/실패는유지한다. 새EPS확대·정밀도/수학/shape변경0이며전체기준은같다.

## v2 실제 회수

actual33061 종료0/5.306073초다. 작은6개 CPU 참조의 손실·미분은 원오차 안이고 미분
최대차4.385381e-14다. 새 IR은 두 상태를 별도 loop-carried 값으로 유지한다. 큰3개는
전치·경로 성질만 검증했고 독립 큰 CPU 참조는 NOT_RUN이다. warm F/B 중앙값은
256×384 14.580ms,512×768 43.924ms,1024² 78.271ms이며 마지막 allocated40.001MiB다.
이는 부품 비용이며 전체 DWA 속도·모델 메모리·품질이나 학습 효율을 뜻하지 않는다.
첫 v1 actual44558/1과 원IR·문턱을 보존하고 명령을 archive_v19/20에 기록했다.
최종 소스 불변·CUDA0/0·모델/optimizer/CP0을 확인했다. 결과101§610이 수치 정본이다.

## 후속 독립 큰 손실 대조

같은 RNG 입력을 CPU에서 복원한 Stage7av actual27359/0에서 별도 행 단위 scalar DP로
큰3형상의 loss를 대조해 절대차0을 확인했다. source와 원GPU 값은 불변이다. 큰 gradient
대조는 여전히 NOT_RUN이며 이 추가 근거의 정본은 결과101§612다. GPU 재실행은0이다.
