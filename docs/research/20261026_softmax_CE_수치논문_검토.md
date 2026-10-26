# A Fix for Softmax and Cross-Entropy 검토

현재 판단은 수치 진단을 후속으로 채택하되 제품 CE·KL은 유지하는 것이다. 합성 logits에서는 논문의 두 수치 현상을 현재 함수로 재현했다. 실제 TinyLM 학습에서 얼마나 자주 발생하는지와 답변 품질·속도를 개선하는지는 미확인이다. 교사 생산과 두300M 본학습의 기존 판정은 바꾸지 않았다.

## 읽은 자료와 권한

사용자가 제공한 `/mnt/c/Users/Uranus/Downloads/2610.31642v1.pdf`는1,520,908B이며 SHA-256은782C5B90C760ECEC2B97E7486829092C451CADAACD13D6F3BBF4006D0688D0E0이다. 로컬 PDF의 제목·저자·arXiv v1 식별자를 확인했다. 로컬 추출 라이브러리를 새로 설치하지 않고, 같은 식별자의 공개10쪽 PDF/HTML 전문·수식·코드·표·캡션을 읽었다. 로컬과 원격 PDF의 바이트 동일성을 별도로 검산했다고 주장하지 않는다. 문서 속 코드는 연구 자료이며 실행 승인으로 간주하지 않았다.

문헌 보조는 읽기 전용으로 범위와 버전 차이를 검토했다. 코드·수치 실행은 총괄이 별도 CPU 도구로 수행했다. 반 검토의 최종 의견과 총괄의 채택/보류는 별도 감사에 연결한다.

## 논문의 내용과 한계

hard CE에서 정답과 나머지 전체 어휘의 logsumexp 차이가 크면 정답 gradient를 계산하는 뺄셈에서 작은 값이 사라진다. 수정식은 정답을 제외한 logsumexp와 softplus를 이용한다. soft-target은 거의 같은 확률끼리 빼는 대신 logits 차이와 expm1/log1p를 사용한다. [v1 수식2~9](https://arxiv.org/html/2610.31642v1#S2)

논문의 효과 실험은 모듈러 산술의 작은 Transformer/MLP와 동일 교사 가중치로 시작하는 증류다. 일반 LM·삼진·SwiGLU·Muon·CCE/Liger의 본학습 결과가 아니다. 저자도 극단 margin·근접 분포 조건이 일반 대규모 학습에서는 드물 수 있다고 적었다. 이를 TinyLM의 반복 원인이나 Falcon 수준 도달 근거로 쓰지 않는다. [v1 실험과 결론](https://arxiv.org/html/2610.31642v1#S6)

v1의 soft-target 예제와 현재 저자 페이지도 같지 않다. 현재 페이지는 먼 분포 구간에서 직접 확률 차이를 쓰는 fallback을 추가했다. 임계값과 버전을 조용히 섞지 않으며 이번 CPU 진단은 v1 식9의 근접 영역만 다룬다. [현재 저자 구현](https://jonbarron.info/softmaxfix/#softmax-cancellation)

## TinyLM 코드와의 연결

| 현재 경로 | 확인한 사실 | 해석 |
|---|---|---|
| mtp_sft.ce_sum | CE 전에 logits.float() | BF16 본체라는 이유로 BF16 경계를 적용하지 않는다. |
| fused_ce.reference | F.linear 결과를 float로 CE에 전달 | 기본 reference와 fused kernel의 내부 산술을 구분해야 한다. |
| trainer._kd_kl | 별도 log_softmax/softmax·batchmean·T² | 동일/근접 분포의 수치 잔여를 조사할 연결점이다. |
| 현재 두 native300M 팔 | NTP-only, KD0 | soft-target cancellation을 두 본팔 실패의 직접 원인으로 설명할 수 없다. |

CUDA autocast의 CE·softmax 계열은 공식 Torch2.10 문서의 FP32 승격 대상이다. 승격 전 온도 나눗셈과 backward cast는 별도로 보아야 한다. CPU 진단 결과를 CUDA kernel의 실측으로 쓰지 않는다. [공식 AMP 규약](https://docs.pytorch.org/docs/2.10/amp.html#cuda-ops-that-can-autocast-to-float32)

FP32에서 비교할 값은 단순 최대 logit이나 top1−top2가 아니라 정답 logit−나머지 전체의 logsumexp다. 생성 확률이 정확히99%라면 이 margin은약4.60이다. ‘후반 약99%’라는 반올림된 관측만으로 FP32의 약16.6 경계를 넘었다고 할 수 없다. 생성 중 확신한 오답과 학습 시 정답 target의 높은 확신도 구분해야 한다. 실제 TRAIN의 해당 빈도는 아직 측정하지 않았다.

Muon의 NS 민감도와 이 논문의 Adam epsilon 분석은 같은 기제가 아니다. 기존 CCE/Liger 수치 음성을 철회하거나 허용 오차를 완화할 근거도 아니다. 안정 식은 수학상 같은 CE라도 유한정밀 gradient를 의도적으로 바꾸므로 기존 reference 일치와 고정밀 정확성은 별도 검사다.

## 총괄의 실제 CPU 수치 대조

정본은 `handoff/audit/oct26_research/paper2610_numeric_v1/`의 preflight/report/external_tool_exit다. 고정 logits에서 hard24·soft8을 관측했고 실제 도구23228의 종료0을 회수했다. 수치 루프0.075446초는 Python/Torch import를 포함한 전체 작업 시간이 아니다. 모델·GPU·optimizer·체크포인트 읽기/저장·제품 변경0이다.

| 조건 | 현재 함수 | 진단용 안정 식/고정밀 대조 |
|---|---|---|
| 3어휘·FP32 ce_sum·실제margin약18 | loss0, 정답gradient0, gradient합1.523e−8 | 정답gradient약−1.523e−8, 합0; FP64 대비 최대오차2.713e−16 |
| 32,768어휘·FP32 ce_sum·margin약18 | loss0, 정답gradient0 | 정답gradient약−1.523e−8; FP64 최대오차1.605e−15 |
| 동일3어휘·T1·실제 _kd_kl | gradient L2 약6.189e−8 | 근접영역 식/FP64는0 |
| 동일32K·T4·실제 _kd_kl | gradient L2 약1.025e−8 | 근접영역 식/FP64는0 |

동일3어휘T4에서는 현재 함수도0이었다. 항상 오차가 생긴다는 뜻은 아니다. 음수의 아주 작은 KL 값도 원 수치로 남겼으며 정답이나 손실을 사후 clamp하지 않았다. soft 진단은 gradient 산술만 대조했고 KL forward를 대체하지 않았다. 교사가 고정일 때 soft CE와 KL의 학생 gradient가 같아도 forward 값은 교사 entropy만큼 다르므로 batchmean·T²·혼합손실 의미를 보존해야 한다.

FP64 oracle에서 double()이 원 텐서를 공유해 margin 표시 시 requires_grad 스칼라 변환 경고가 한 번 났다. 보고용 metadata 경고이며 모델/가중치 변경은0이다. 원형과 경고를 숨기지 않고 외부 종료 영수증에 적었다. same_logits_exact_zero 필드는 진단 식/FP64에만 해당하고 현재 함수의 잔여값은 그대로다. 이를32개 제품 회귀나 전체 head 검증 PASS로 표현하지 않는다.

## 세 후속 방향과 비용

| 안 | 범위 | 예상 추가 비용·조건 | 판단 |
|---|---|---|---|
| A | 현재 CE 유지, 실제 TRAIN의 dtype·margin·gradient합과 근접 KD 비율 계측 | 연결 구현2~4시간 추정, 실제 모델 진단 시간은 미계측 | 권장. 이번 합성 수치 관측은 완료했고 실제 발생 빈도부터 확인한다. |
| B | 별도 opt-in FP32 hard CE, mask/shift/분모/tied-head를 유지 | CPU/정합 구현4~8시간 추정, 새 전체300M은 오늘Muon약1.6시간을 참고하되 미측정 | A 뒤 검토. 의미 개선은 본학습과 고정 평가로 확인한다. |
| C | 원거리까지 안전한 soft KL gradient 및 fused kernel 결합 | 최소8~16시간 설계/검증 추정, 전용 kernel·메모리/속도 검증은 별도 | 근접 온라인 KD가 실제 켜진 뒤 검토한다. 텍스트 교사 SFT만으로 해당 조건이 성립하지 않는다. |

위 구현 시간은 실측 공수가 아니다. naive2048×32768 FP32 임시 텐서 한 벌은256MiB이므로, 작은 JAX 예제를 그대로 옮겼다고 메모리 절감·학습 가속이 생기지 않는다. 기존 청킹·공유 임베딩 양쪽 gradient·MTP horizon mask·전체 분모·compile·고차 미분·GPU 성능은 미검증이다. 새 기본값 채택은 하지 않았다.

## 독립 반 검토와 추가 대조

읽기 전용 반 보조는 이 범위의 수치 반례를 무효화할 치명적 오류를 찾지 못했다. 다만 BF16 입력의 FP32 CE, 반올림 뒤 gradient합의 잔여, 같은 식의 FP64와 비교한0오차의 비독립성, 원거리 soft 식의 NaN 후보와 assert의 감독 한계를 지적했다. 총괄은 모두 한계로 채택했다. 실제 실행은 외부120초 timeout 아래 실제0이었으며 assert를 OS 마감 보장으로 표현하지 않는다.

후행 검산은 비정답 logits가 모두0인24개 fixture에서90자리 Decimal의 독립 스칼라 식으로 loss와 정답 derivative를 다시 계산했다. 원 보고서·원 소스는 바꾸지 않았다. 이는 같은 PyTorch 식의 FP64 재호출과 별도인 산술 대조이며 제품 전체 gradient·일반 데이터·품질 검증은 아니다. paper2610_numeric_v1/decimal_and_counterreview.json에 관측·반 의견·총괄 조치를 보존했다.
