# 2026-10-24 본학습·추가 공식 평가의 준비 상태

이번 CPU/GPU 위임은09:00 KST까지다. 기술진단의 작은 실행으로 새 모델의 지능을 판정하지
않는다. 이 파일은 읽기 검토이며 새 자료·설치·모델 본학습의 완료 영수증이 아니다.

## 본학습

| 후보 | 현재 확인 | 이번 판단 |
|---|---|---|
| 새 QA·명시적 대화75M×4 |생산 후보 누계29,221,731·산술 부족45,778,269. 이 누계는 공개후보29,022,176과 미채택 교사674묶음/199,555입력의 합 |미채택 교사량을 정식 가용 train에 다시 가산하거나29M을75M이라 바꿔 시작하지 않음 |
| 옛 Oct6 refill75M×4 + MTP |기존 NTP15752회/300,003,268입력/19,952.25초는 완료. 요약·변환 편중·의미미검토 자료이며 새 능력 교과와 다름 |기존 full NTP를 중복하지 않음. 새 MTP 이식과 원 배치/주손실/업데이트 경로 대조가 필요 |
| 현 P101A 실행기로75M NTP/MTP |8M 실측을 업데이트수만 비례한 외삽은 약8.61h+9.31h. 자료/연산량 차이가 있어 보장 아님 |두 팔 전체와 준비·평가가 이번 창에 안 들어옴. 부분 학습을 본학습 성과로 대체하지 않음 |
| Native595에 MTP 새 한 팔 |기존 NTP4543회/595,460,096targets가 완료, 기존 return_hidden 접점은 있음 |EOS별 segment/보조 분모/optimizer소유권/비용 및 새 실행기 필요. 현재 미정제 원문으로 새 학습을 강행하지 않음 |
| 교사8h 생산 재개 |기존 두 창31.8227입력/초. 단순8h 외삽916,494입력은 현재 부족분 약2% |75M 완성일 약속이나 본학습 대신이 아님. 원천 품질·후행 판독 선결은 그대로 |

권장은 정제·의미 판독/채택 계약을 먼저 닫고, 같은 정제 풀에서 전체 NTP/MTP를 비교하는 것이다.
다른 선택지는 옛 자료의 알려진 한계를 명시한 새 MTP 통제 연구, 또는 생산량 확보 우선이다.
두 대안 모두 자료 준비가 끝났다는 증거를 만들지 않는다. 이미 완료한 작은 MTP704/풀이128/
방문정책704/ALM32를 다시 학습하지 않는다.

원천 근거: 결과101§54~55/§436/§473, 결과092§19~24,
HF/sft_ready/p106b_mixed_student_v3_en_refill/report.json,
data_cache/p106b_native_format_v2_full_20261022/report.json,
scripts/diag_p106b_native_weight_route.py와tinylm/train/trainer.py의현MTP제한.
정제 형식파생1,441,175문서는 NOT_ADMITTED/FORMAT_DERIVATIVE_ONLY_NOT_TRAIN_READY이며
전량 의미 판독 완료가 아니다. 해당 후보를 이번 밤 새 학습에 넣지 않는다.

여기서 전량 의미 판독이 아직 없다는 관측은 모든 문장을 사람이 전수 검수해야 한다는
새 학습 필수조건을 뜻하지 않는다. 이번 판단은 실제 채택 영수증이 없는 후보 상태,
새 목표의45,778,269토큰 부족, 해당 전체 비교의 실행 경로와 남은 시간에 근거한다.
타세션의 후보 작성과 실제 적용·채택은 분리한다. 체크리스트가 선언한 두 사례 보완을
영어2,821행 전체의 새 검수 의무로 확대하지 않으며, 이것으로 원장 전체 정제를 완료했다고도
하지 않는다. 보유한 옛75M 자료와 이미 끝난300M 학습은 존재하며 새 능력 교과와 다르다.

양의 구분을 더 명확히 한다.29,221,731은 생산 보고의 기술적 누계이며 정식 품질승인
train 토큰 수가 아니다.199,555를 그 누계에 다시 더하면 이중계상이다. 미채택 교사
후보를 제외하고 공개 후보29,022,176만 기준으로 삼으면75M까지 산술 부족은45,977,824다.
이 공개 후보도 전체 품질 승인으로 확대하지 않는다. 아래8h 외삽은 생산 누계의 부족을
기준으로 한 단순 계산이며 정식 train 편입이나 완성일 보장이 아니다.

## Belebele·KoBEST

다음 표는 초기 문헌/가용성 담당의 읽기 전용 검토 시점이다. 이후 Belebele의 실제 준비
완료는 아래 추가 절과 결과101§490이 소유한다. KoBEST 설치와 모델 실행은 여전히 미실행이다.

| 대상 | 로컬/공식 정의 | 미충족 선결 |
|---|---|---|
| Belebele KO/EN |pinned harness에 kor_Hang/eng_Latn test4보기·acc/acc_norm 정의 있음 |조회한 정확 HF namespace와 Core6 manifest에 데이터 없음.900개씩의 revision/원형은 아직 미확인 |
| KoBEST boolq |고정 snapshot test JSONL1404행 |아래 공식 F1 의존성과별도 로컬 task binding |
| KoBEST copa |1000행 |정답이 문자열이라 Core6의 정수 target 전용 audit를 그대로 복사하면 안 됨 |
| KoBEST hellaswag |500행 |acc/acc_norm/macro-F1 계약 |
| KoBEST sentineg |397행 |acc/macro-F1 계약 |
| KoBEST wic |1260행 |acc/macro-F1 계약 |

KoBEST snapshot은 HF/datasets--skt--kobest_v1/snapshots/a5ea15e3ac77ed694b79f6204eb31889a2ba989f,
총4561행이다. pinned lm_eval commit은 d6de81643928d653435c431bae19945d41d32520이다.
평가 venv와 base 설치 metadata에 evaluate/scikit-learn/scipy가 없고 F1 metric cache도 없다.
공식 YAML의hf_evaluate/공식macro-F1를 쓰기 위한 최소 설치와 metric 확보를 먼저 승인받아야 한다.
Core6 전량 결과를 한국어 평가나 이 두 suite의 완료로 세지 않는다. 임의 대체 metric으로
공식 평가가 끝난 것처럼 보고하지 않는다. 향후 승인이 있으면 기존 loader/HFLM과 TinyLM
likelihood adapter를 재사용하고 중복 모델/평가기를 만들지 않는다.

## 공식 fused head 선결의 추가 읽기 확인

정 역할 담당이 실제 package metadata와 지정 cache/표준 source 경로를 읽었다. base는
Torch2.10.0+cu130·Triton3.6.0이고 평가 venv는 base를 상속한다. 확인한 경로에서 공식
cut_cross_entropy나 Liger package·wheel·source를 찾지 못했다. 전체 디스크에 전혀 없다고
증명한 것은 아니다. 모델/GPU·추가 설치·다운로드는 이 조사에서0이다.

현재 trainer의 compile은 모델을 감싸고 CE는 그 밖에서 계산한다. 이를 fused linear+CE라고
부르지 않는다. loss-first 경로는 chat32/compile/KD를 거부하고 기존 Triton은 ternary matmul
전용이다. 기존 target gather/checkpoint/CE와 gradient85개 재생은 재사용할 정합 기준이지
공식 CCE/Liger 접합의 구현 완료가 아니다. 실제 NS 반사실은 제품 Muon 기본값 변경을
승인하거나 본학습 수렴·지능 개선을 입증하지 않는다.

| 경로 | 장점 | 남은 비용·권한 |
|---|---|---|
| 기존 reference/compile 접점 정리 | 새 설치 없이 계약 준비 | fused head 자체와 가속 실측은 미완 |
| 공식 CCE/Liger source 고정 후 어댑터 | 검증된 kernel과 기존 진단 재사용 | source 취득/필요 의존성의 별도 범위와 실제 GPU 정합 필요 |
| 자체 Triton CE | 이미 있는 compiler 활용 | 새 커널·gradient·tied head 검증 부담, 공식 CCE와 다른 방법 |

권장은 두 번째 경로의 최소 의존성/라이선스/정확 버전을 먼저 확인하는 것이다. 이 문서는
설치·방법 채택이나 원 데이터 학습 편입 승인이 아니다. 새75M의 부족과 정제 후보 미편입을
가속으로 해결했다고 보고하지 않는다.

## 정확 fused head 후보의 최소 설치와 연결 계약

읽기 담당의 공식 소스·배포 메타 검토를 회수했고 총괄도 고정 소스의 의존성·exact preset·
Liger loss API를 웹으로 재대조했다. 현재 Python3.10.19/Torch2.10.0+cu130/Triton3.6.0/
packaging26.3은 선언 최소범위에 있지만 실제 커널·기울기·wallclock 호환은 미검증이다.

| 후보 | 최소 추가 범위 | 현재 상태 |
|---|---|---|
| 기존 FP32 reference |없음|대조군 재사용, 전량 logits/청크·재계산 비용 유지|
| Liger0.8.5 |기본 wheel1개, 기존 Torch/Triton 재사용|미설치, 추가 설치 허가 전 실행하지 않음|
| Apple CCE exact |고정 source와 필요한 build 보조만|미취득/미설치, setuptools-scm도 현재 없음|

[Liger 고정0.8.5](https://github.com/linkedin/Liger-Kernel/blob/1ab779ff0990d205e6003fa34c7618f0e8c50337/pyproject.toml)의
CuTe/cuTile·Transformers/개발 extras는 이번 CE 연결에 불필요하다. 기본 wheel 사용 시
source build 도구도 일괄 설치하지 않는다. BSD-2-Clause 고지와 정확 wheel hash를 보존해야 한다.
[공식 loss API](https://github.com/linkedin/Liger-Kernel/blob/1ab779ff0990d205e6003fa34c7618f0e8c50337/src/liger_kernel/transformers/fused_linear_cross_entropy.py)는
sum/FP32 accumulation, ignore_index=-100을 지정하고 label smoothing/z-loss/token scaling은
현재 원형대로 끈다. 공식 API 확인만으로 TinyLM 가속은 입증되지 않는다.

[CCE 고정 commit](https://github.com/apple/ml-cross-entropy/blob/3de376c106a1916bc5e1b619f9c77c87a461ee1c/pyproject.toml)의
기본 의존성은 Torch와Triton이며 source build는 setuptools-scm을 요구한다. Transformers
extra는4.48.2를 고정하므로 현재5.14.1 환경에 추가하지 않는다. 기본 auto 필터 대신
[cce_exact preset](https://github.com/apple/ml-cross-entropy/blob/3de376c106a1916bc5e1b619f9c77c87a461ee1c/cut_cross_entropy/cce_utils.py)의
filter_eps=None과 양쪽FP32 누적을 사용해야 원형 정합 비교에 적합하다. Apple 자체
[LICENSE](https://github.com/apple/ml-cross-entropy/blob/3de376c106a1916bc5e1b619f9c77c87a461ee1c/LICENSE)를
MIT/BSD라고 바꾸어 설명하지 않는다. exact도 비트 동일 보장은 아니다.

현재 factorized tied head의 hidden→256 projection과 같은 emb.weight를 그대로 전달해야
입력/출력 embedding gradient가 합쳐진다. 복제·detach·자동 추가 shift는 금지하며 이미
이동된 label, EOS/turn-end, assistant-only 마스크, 각MTP projection/마스크와 전체 update
분모를 유지한다. 초기 검산은 FP32/autocastOFF/TF32OFF이며 실제157gradient/85NS·update
재생과 같은 원형 검사를 통과해야 한다. CE만 연결한 것을 full KL·ALM 확률 경로의 fused
구현이라고 주장하지 않는다. 권장은 가장 작은 Liger 기본 wheel의 별도 설치 범위를 먼저
정하는 것이고, 이번 조사에서 설치·새 커널 실행·기본값 변경은0이다.

## 지명 Qwen3.5 HF와 Bonsai2B의 구체적인 미완 이유

읽기 담당이 평가 Python과 base의 실제 Transformers5.14.1 경로 및 관련7파일 SHA를
대조했다. 모델 모듈 import/forward 없이 동일 정의임을 확인했다. Qwen3.5 HF는 공식
AutoModelForCausalLM에 text class·nested config·prefix conversion이 실제로 있다.
따라서 지원 class가 없어서 영원히 불가능하다고 설명하지 않는다.

정확 safetensors header488키는 언어320/vision153/MTP15다. 공식 text class의
ignored-unexpected 목록은168키를, conditional class도MTP15키를 loading_info에서
걸러낸다. 빈 loading_info만 보고 전 가중치를 strict 소비했다고 주장할 수 없다.
원 파일·바이트는 보존하고 다음 모델 범위를 명시한 독립 runtime을 준비해야 한다.

| 방법 | 실제 의미 | 장점·한계 |
|---|---|---|
| text class |언어320키 전부를 검산하고 vision153/MTP15 미사용을 기록|텍스트 벤치에 가장 직접적이나 체크포인트 전체소비와 다름|
| conditional class |언어+vision473키를 로드하고 MTP15 미사용을 기록|원 구조를 더 보유하지만 텍스트 forward에서는 vision 미사용·비용 증가|
| 현 HOLD |제외/모델범위 선택을 확정하기 전 실행하지 않음|과대 strict 주장을 피하지만 전량 비교가 남음|

text-only 비교가 확정되면 기존 HFLM/task는 재사용하고 언어 body/head·실제 ID·FP32/eager/
cacheOFF, full CE·batch1/2·prefix/future·A/B/A 상태격리와 자산불변을 먼저 검사한다.
새 fast kernel 없이 공식 PyTorch fallback이 있으므로 미설치를 정답성 실패로 취급하지
않는다. 속도는 실제 cost 전 미측정이다. 이 준비는488키 무단 삭제나 v3 HOLD 해제가 아니다.

Bonsai 지명 파일은 `HF/benchmark_20261023/bonsai2_2b_ptq1/manifest.json`의
429,183,456B/revision683f7be2629342a50987627b40881e54761a2430이다. header는
qwen35/24층/320텐서, F32타입169개와 PTQ타입143의151개다. b11396의 고정 enum
GGML_TYPE_COUNT43에는 이 타입이 없어 같은 worker에 이름만 추가할 수 없다.
기존 Prism `llama-prism-b10743-adfffbe`의 server/base/core SHA는 고정 profile과 일치하고
PTQ 처리·raw logits·memory-clear 심볼은 있다. 그러나 full40 commit과 정확 header/ABI는
아직 닫히지 않았다.27B 성공을2B 로드 성공으로 대신하지 않고 TQ1_0/Q1_0도PTQ1_0와
동일시하지 않는다. 실제2B 로드·수치·우도·전체 점수는 모두 미실행이다.

## 03:18 이후 실제로 달라진 평가 준비

기존 평가자료 취득 승인 안에서 Belebele 공식 원 JSONL 두 파일만 새 경로에 취득했다.
고정 revision과 원 Git blob·bytes·로컬 SHA256을 확인했고 KO/EN 각900개와 대응키900,
link488·정답차0을 검산했다. source2BB7BC8D의 CPU prepare가 실제 종료0으로 닫혔으며
모델0·순전파0·GPU호출0이다. 사전7모델의 토큰 경계를 결과 전에 동결했고 공통 무절단
보조분모는898개다. prepare의 종결영수증과 원형은 결과101§490을 따른다. 이 추가로
앞의 초기 가용성 표를 실제 미취득 상태인 것처럼 읽지 않는다. 모델별 전량과 CI는 별도다.

03:18 당시에는 Falcon 문법59875/5218쌍과 외부3종의 Core6가 완료됐고 GPT2는 진행
중이었다. 이후04:36 실제 부모와 worker 종료0 및 종결·원형 재계수·소유 정리가 닫혀
GPT2 전량도 결과101절492에 기록했다. 현재 Core6는 Tiny3와 외부5의 총8모델이다.
고정7모델의 Belebele 한영 각900개와 LAMBADA5153개 전량도 결과493/496에서
완료했다. 이 후속은 앞의 초기 가용성 상태를 대체하지만 다른 미실행 suite를 채우지 않는다.

Qwen3.5 HF는 실제 생성자 복구 뒤 수치와정리 veto로 전량 미실행이다. 별도 관찰은
원 canary 통과를 대신하지 않는다. 정확 Qwen IQ2의 전량외삽15313.504초는 원7200초와
별도10800초 창을 모두 넘었고 점수가 없다. Bonsai2B는 exact Prism ABI가 남았으며
KoBEST 추가 설치, 다른 공식 suite와 전체 생성 자원행렬 및 새 본학습 자료 채택도 미완이다.

## 사용자 후속 순서 C 다음 A와 B의 필수 여부

사용자가 다음 회차는 C 다음 A로 지정했다. C는 정확 Qwen35 HF/IQ2/Bonsai2B와 남은
공식 평가의 연결, A는 정제·번역 후보의 실제 편입과 부족 원천/교사 증분생산 준비다.
B는 설명을 요청한 가속 후보이지 두 작업을 시작하기 위한 새 필수 게이트가 아니다.
이 선택 자체가 새 GPU 시간이나 설치 승인은 아니다. 이번 확인은 코드/메타데이터 읽기와
공식 고정 소스 조회이며 새 모델·패키지 설치·학습은0이다.

### B는 무엇을 줄이려는가

기존 출력층은 hidden을rank256으로 투영하고 어휘 수만큼 점수를 만든 뒤 CE를 계산한다.
낮은rank가 전체 토큰×어휘 점수 배열을 없애지는 않는다.8192개 위치를 전부 계산하는
FP32 logits 한 개만 가정하면 micro8×길이1024×어휘32768은1GiB,어휘248320은
7.578125GiB,262144는8GiB다. 이는 계산상 배열 크기이며 현재 실행의 peak 측정이 아니다.
CE를 chunk로 계산하더라도 model이 이미 반환한 전체 logits가 자동으로 없어지지는 않는다.

[CCE의 고정 공식 설명](https://raw.githubusercontent.com/apple/ml-cross-entropy/3de376c106a1916bc5e1b619f9c77c87a461ee1c/README.md)은
어휘 점수 전체를 전역메모리에 만들지 않고 정답 점수와 log-sum-exp를 계산하는 방법이다.
Liger fused linear+CE도 이 출력 계산과 손실의 결합을 위한 후보다. 목표는 같은 학습을
더 적은 메모리/전체시간으로 수행하는 것이고 직접적인 새 지식·정답 지도법은 아니다.

### 무엇이 추가로 필요한가

| 요소 | 현재 상태 | 필요한 이유와 최소 범위 |
|---|---|---|
|기존 실행 기반|Python3.10,Torch2.10.0+cu130,Triton3.6.0,packaging26.3 있음|재사용,재설치/버전변경하지 않음|
|가속 kernel|Liger/CCE 둘다 미설치|선택한1종만 별도 가속 실험 환경에 준비,둘을 한번에 설치할 이유 없음|
|TinyLM 연결|공식 fused adapter 미완|hidden→rank256 뒤 기존 같은 embedding을 넘겨 입력/출력 공유 gradient와 target/분모를 보존|
|기술 검증|기존157gradient/85Muon 재생 근거 있음|그 회귀를 재사용해 CE·마스크·gradient·update·MTP 및 메모리/시간을 검산|
|본학습 시간 평가|미실행|head 커널 하나의 시간이 아니라 같은 자료/노출/optimizer의 전체 wall과 메모리를 비교|

우선 검토 후보는 Liger0.8.5 기본 wheel1개다. 고정
[setup.py](https://raw.githubusercontent.com/linkedin/Liger-Kernel/1ab779ff0990d205e6003fa34c7618f0e8c50337/setup.py)는
CUDA 기본 의존성을Torch>=2.1.2와Triton>=2.3.1로 선언한다. 현재 버전은 이 하한을
만족하지만 실제 GPU/gradient 호환 보장은 아니다. CuTe/cuTile/개발 extras를 함께
넣지 않는다. 이는 기존 lm_eval+6종 평가 패키지와 다른 학습 가속 패키지여서 별도 승인
전 설치하지 않는다. 공식 wheel의 실제 배포 메타와 해시는 설치 전 다시 확인한다.

대안 CCE는 기본Torch>=2.4/Triton>=3.0와 source build의setuptools-scm을 확인한다.
현재Transformers5.14.1에 고정4.48.2를 요구하는 Transformers extra를 섞지 않는다.
초기 정합은 필터 없는exact/FP32누적을 기준으로 하고 자동 shift를 중복하지 않는다.
full KL·top-k·ALM 확률과 마스크 경로가 scalar CE 하나로 대체되는 것은 아니다.

설치만으로 TinyLM에 자동 적용되지 않는다. 현재 model._head_logits와 trainer의 CE는
별도이고 기존 loss_first는 재계산형 FP32 참조 구현이지만 chat32/compile/KD/기존커널/
resume을 거부한다. 따라서 기존 함수를 재사용할 수 있는 접점부터 검토하되 지원하지 않는
경로를 플래그 하나로 실행 가능하다고 안내하지 않는다. 이전 실제FP32 NS가 느렸던 결과도
Liger/CCE 자체의 속도 결과가 아니다. 가속 배수와 구현 시간은 아직 확정하지 않는다.

### 필수인가

- C의 평가와 A의 정제·번역·교사 생산에는 필요 없다. 현재 순서 C 다음 A를 유지한다.
- 기존32k 경로의 본학습도 B 없이 가능하며 실제300M/595M 학습 기록이 있다.
- 큰 어휘나 더 큰 배치에서 메모리가 부족하면 fused CE,청크/재계산,배치 조정 등 어떤
  메모리 절약책은 필요할 수 있으나 Liger라는 특정 패키지가 필수라는 뜻은 아니다.
- 기본값 채택은 실제 정합과 전체시간 이득 뒤에만 판단한다. 작은 학습 점수를 지능
  성과로 채택하거나 B 미설치를 이유로 자료 준비/연구를 중단하지 않는다.
