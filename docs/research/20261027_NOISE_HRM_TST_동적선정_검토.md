# NOISE·HRM-Text·TST·동적 자료 선정·활성 기울기 제어 검토

사용자98의 조사 결과이며 사용자99의 임시 마감에 맞춰 회수한 근거와 남은 일을 구분한다. 새 방법을 구현하거나 학습에 채택한 문서가 아니다. 문헌·정·반 보조는 사전 명세의 웹/지정 코드 읽기만 수행했고, 총괄이 공개 일차자료와 현재 기술 경계를 대조했다. 구현·학습·설치·다운로드0이다. 기존 P107 GPU 비용은 이 조사와 별도 실행이다.

## 1. 확인 범위와 결론

| 대상 | 정확한 출처 | 이번 판정 |
|---|---|---|
| NOISE | [현재 규칙/30M 기록](https://github.com/qlabs-eng/noise), 품질 코드 `6f0c450ed52d52dd2fefd2a8ba485d92f2b37e92`, 속도 코드 `4586b02e7f77927683c1f5d28a981b3a0342b9ea` | 순전파만 쓰는 별도 credit engine. 전체 이식은 큰 변경이며 BP와의 혼합은 별도 연구 |
| HRM-Text | 사용자 지정 [논문2605.20613v1](https://arxiv.org/html/2605.20613v1), [공식 저장소](https://github.com/sapientinc/HRM-Text) | SwiGLU는 호환 부품. H/L 상태·정규화·역전파 horizon·cache는 새 구조 계약 필요 |
| Token Superposition Training | 사용자 지정 [논문2605.06546v2](https://arxiv.org/abs/2605.06546v2), [저자 설명](https://nousresearch.com/token-superposition) | 추론 구조를 유지하는 사전학습 가속 후보. 평균 임베딩·다음 bag·정상 NTP 복구가 한 묶음 |
| AC-ODM | 사용자 지정 [ICML2026/PMLR306](https://proceedings.mlr.press/v306/ma26i.html), [arXiv v2](https://arxiv.org/html/2505.23878v2) | 도메인 sampler 후보. 작은 모델에서 정책·reward 비용 재계측 필요 |
| LFR | [Learn, Focus, and Review, CoNLL2025](https://aclanthology.org/2025.conll-1.18/), [arXiv2409.06131v2](https://arxiv.org/html/2409.06131v2) | 문맥상 유력 동정. 사용자 링크 미지정·공식 코드 미확인이므로 약어 확정과 구현 재현은 미완 |
| MAI-Base-2 | 사용자 지정 [Microsoft 보고서?v=2](https://microsoft.ai/pdf/Frontier-Pre-training-at-Microsoft-AI.pdf?v=2) | 모델 전체의 효율 수치를 TinyLM에 이전하지 않음. 데이터 계보·반복노출 회계·최적화 검증 관점 차용 |
| Activation Gradient Clipping | 위 보고서 pp.10–11 | 활성의 기울기 이상치 관찰은 유용한 후보. 실제 clipping recipe는 지점/축/threshold가 공개되지 않아 재현 설계 미완 |

직접 차용하기 쉬운 것은 **비교 조건과 노출 회계, 안정성 관찰, 자료 추적**이다. 지능과 본학습 wall 개선은 이번에 측정하지 않았다. 과거의 작은 학습 결과나 이번의 가상 통계 통과를 본학습 성과로 승격하지 않는다.

## 2. NOISE에서 잘된 것은 무엇인가

NOISE는 backward·reverse/forward autodiff·수제 backward를 금지한다. Dust의 병렬성은 토큰별 활성 잡음과 여러 후보를 순전파에서 평가하는 것이다. 이후 코드의 통신/행렬 계산 overlap도 BP 동시 실행과 다르다. [규칙](https://github.com/qlabs-eng/noise#rules), [Dust 방법](https://qlabs.sh/research/dust).

아래는 현재37.7M 모델/BPE4096/FineWeb 약30M·최대1epoch/8×H100/seed0의 기록이다. 최종 NTP CE와 기록된 학습시간이며 컴파일·평가 제외다. [공식 기록](https://github.com/qlabs-eng/noise#records).

| 방법 | 최종 CE↓ | 시간 |
|---|---:|---:|
| Dust+Adam, population24k |3.767|5시간17분|
| Boost→Cut |3.409|1시간43분|
| true-path readout+ANVIL II 계열 |3.338|56분|
| identity-path→Cut-lite, 목표3.5 |3.499|8분20초|
| BP+Adam |3.419|미기재|
| BP+ANVIL II/Adam |3.340|미기재|

3.338 대3.340은 단일 seed의0.002차이다. 통계 우위나 BP 대비 시간 우위가 아니다. 옛10M/목표4.2의1.6초 및 구조 변경 트랙의3.211과 섞지 않는다. 이번은 새 실제 TinyLM 결과도 아니다.

품질 기록의 [고정 코드](https://github.com/qlabs-eng/noise/blob/6f0c450ed52d52dd2fefd2a8ba485d92f2b37e92/train/val/run.py)에서 보조는 중간 readout, own-query/선택 경로 재실행, 다른 토큰의 실제 경로 credit, 여러 EMA와 마지막 merge 탐색을 확인했다. 한 epoch가 forward 한 번을 뜻하지 않는다. ANVIL II는 행렬 momentum·직교화·방향별 정규화와 norm 복원 등을 조합하고 비행렬은 Adam 계열로 처리한다. 원장56의 AdaMuon과 같은 갱신법이 아니다. 여러 요소를 함께 바꾼 기록이므로 갱신법 하나의 기여로 분해할 근거는 없다.

현재 특화 코드는 power-of-two 폭·같은 Q/KV head 수·ReLU²를 가정한다. TinyLM의 GQA/SwiGLU·공유MLP·CLA·삼진 STE에 그대로 연결할 수 없다. 특히 잠재 가중치의 작은 교란이 삼진 문턱을 넘지 않으면 실제 순전파 차이는0일 수 있으나 STE는 비영 기울기를 줄 수 있다. 활성 교란도 방문별 신호 합산과 latent 변환을 별도로 정의해야 한다. 이는 [현재 ternary 구현](../../tinylm/model/ternary.py)에 근거한 이식 위험 추론이며 실제 새 오류 관측이 아니다.

## 3. 순전파 기반 갱신과 역전파를 함께 사용할 수 있는가

원리상 가능하지만 세 동작을 구분해야 한다.

| 혼합 방식 | 실제 의미 | 장점·한계 |
|---|---|---|
| 같은 BP 안의 복수 목적 | causal/MNTP 등 손실을 가중해 역전파 | 기존 도구를 재사용. NOISE의 forward-only 갱신은 아님 |
| 서로 다른 파라미터 집합 | 본체는 BP, 소수 비미분 제어계수만 forward 평가 | 전체 credit engine 교체를 피함. 제어값 탐색 비용/평가 누설 관리 필요 |
| 같은 가중치에 두 신호 | `g_BP + lambda * estimated_g_forward` 등으로 결합 | 원리상 계산 가능. 분산·편향·scale·STE 공간과 추가 forward 때문에 더 느리거나 나빠질 수 있음 |

또 GPU stream에 둘을 올린다고 실제 연산이 무료로 겹치지는 않는다. 동일 GPU의 계산/대역폭을 경쟁하고 활성 저장도 늘 수 있다. TinyLM은 추가 no-grad forward가 live quantized leaf를 교체할 수 있어 checkpoint backward 전에 끼워 넣는 순서도 안전하다고 가정할 수 없다. 같은 가중치 snapshot·RNG·원 gradient/양자화 cache 보존·실패 복구부터 확인해야 한다.

**총괄 판단**: 현재 BP를 대체하거나 전면 혼합하기보다, 후속에서는 소수 제어변수의 별도 forward 탐색과 기존 BP를 분리하는 편이 원인과 비용을 해석하기 쉽다. 이번에는 구현하지 않았다.

## 4. HRM-Text와 TST가 바꾸는 것은 다르다

HRM은 느린 H와 빠른 L의 두 상태, 반복 입력 주입, 모듈 출구 norm, 잘린 역전파 horizon을 결합한다. SwiGLU는 현재 부품과 맞지만 MLP tying이나 방문 수 증가만으로 HRM이 되지는 않는다. 공식 코드의 H/L 방문 cache와 horizon 배분은 CLA owner cache에 새 대응이 필요하다. 논문은40B unique/실제60B 학습·16×H100/46시간 조건이고 ACT를 사용하지 않아 추론 연산도 증가한다. DROP의13-gram 오염 신호도 보고하므로 전체 benchmark가 무오염이라는 설명은 부적절하다. [논문 방법·학습·오염 절](https://arxiv.org/html/2605.20613v1).

먼저 차용할 개념은 instruction 구간의 양방향 PrefixLM과 response-only 목적, 반복 모듈 출구 norm, forward 깊이와 gradient horizon 분리다. P107 문서 내 전체 양방향 MNTP mask와 PrefixLM은 다르며 답 구간의 미래 정답 노출을 막는 새 계약이 필요하다. 보조가 읽은 공식 main 코드의 commit은 고정하지 못해 완전 재현 설계는 미완이다.

TST는 연속 s개 임베딩을 평균해 다음 비중첩 bag을 예측하는 초기 단계 뒤 정상 NTP로 복구한다. 추론 head를 s개 붙이는 MTP도, 현재 P013의 문맥 분할도 아니다. 저자 설명의 대표 이득은 같은 계산예산에서 원문을 더 많이 소비한 결과다. 10B-A1B는 baseline1.05T/12311 B200-hours와 TST2T/4768 B200-hours 조건이다. 같은300M을 읽으면 자동2.5배라는 의미가 아니다. [논문v2](https://arxiv.org/abs/2605.06546v2), [저자 방법/제약](https://nousresearch.com/token-superposition).

이식할 때 `[a,b]→[b,c]`는 입력 b를 정답으로 재노출한다. 다음 비중첩 `[c,d]`를 예측하도록 shift해야 한다. 중복 target의 질량·문서/PAD·assistant-only 경계·유효 target 분모·단계/RNG 재개를 새로 정해야 한다. bag 내부 숫자/어순 정보를 잃으므로 정상 NTP 복구 비용까지 포함하고 최종 정규 causal 평가로 판단해야 한다. 출력 전용 next-bag는 보조의 개념 후보일 뿐 원 TST의 성과가 검증된 변형으로 채택하지 않았다.

## 5. AC-ODM·LFR·활성 기울기의 차용

AC-ODM은 도메인 loss/gradient 정렬을 사용해 actor-critic이 혼합률을 조절한다. 공식 학회 초록과 arXiv v2의 최대66% step 절감은 일치하지만 전체 PDF 바이트가 같다고 확인한 것은 아니다. arXiv 자원 표의 직접 모드는 ODM2.47초 대2.48초/step, 같은 목표 PPL까지1.46배이고17M 정책 파라미터를 둔다. 1B에서의0.4% 시간/2% 메모리를 약0.1B 학생에 그대로 적용할 수 없다. [공식 학회판](https://proceedings.mlr.press/v306/ma26i.html), [v2 자원표](https://arxiv.org/html/2505.23878v2).

TinyLM 접점은 sampler이며 SwiGLU 교체가 아니다. 후반 FFN gradient를 reward로 쓸 경우 공유 물리 파라미터의 중복 계수를 피하고 quantized leaf와 latent STE gradient를 구분해야 한다. actor/critic/target/replay/optimizer·도메인 노출/RNG까지 재개 범위가 늘어난다.

LFR 후보는 블록별 PPL을 기록하고 어려운 블록에 집중한 뒤 전체를 다시 Review한다. 현재 원장59의 유형별 masking과 단위가 다르다. 고정 블록ID·정규 causal NLL·이전 점수·다음 갱신 시점·전체 노출 회계가 필요하며 고손실의 불량 원문을 더 반복할 위험이 있다. 전체 scoring/embedding과 replay 비용을 포함해야 한다. [CoNLL 원문](https://aclanthology.org/2025.conll-1.18/). 정제 전 hard-example 선정으로 나쁜 자료를 더 학습시키지 않는다.

MAI-Base-2 보고서는 활성 기울기 clipping을 기존 global weight-gradient clipping에 추가한다. 활성값 clipping이나 Adaptive Gradient Clipping이라는 이름의 다른 방법과 구분한다. 잘린 코드 헤더를 유발 지점으로 추적해 전처리 오류를 발견한 사례는 현재 프로젝트에도 유용한 관찰 개념이다. 그러나 큰 활성 기울기 자체가 불량/의미 오류의 증거는 아니다. [사용자 지정 보고서pp.10–11](https://microsoft.ai/pdf/Frontier-Pre-training-at-Microsoft-AI.pdf?v=2).

v2도 clipping 위치/norm 축/threshold/주기/공식 코드는 확인하지 못했다. 현재 global clip을 없애거나 임의 수치로 production에 적용하지 않는다. 후속이라면 우선 관찰만 하고 정상 복사/숫자/코드와 진짜 손상 사례를 대조한다. 실제 clipping은 micro/target 정규화·혼합정밀 scaling·공유 방문·checkpoint 재계산을 포함해 별도 설계해야 한다. 쿼리 없는 PDF와 웹 추출 본문이 같다는 확인은 파일 SHA 동일성 증거가 아니다.

## 6. 후속 후보와 마감 상태

| 안 | 범위 | 장점 | 비용·선결 | 권장 |
|---|---|---|---|---|
| A 관찰·원형 보존 | 기존 BP/목표 고정, 활성 gradient·블록 노출과 손상 원문 연결의 기술 설계 | 구조 변경을 줄이고 정제/불안정 원인을 추적 | 자료 소유권·수집 위치/비용·정상 이상치 구분 | **우선** |
| B TST→NTP 본학습 설계 | bag 정답/분모/문서/재개 CPU 계약 뒤 최종 NTP까지 같은 전체 예산 비교 | 최종 추론 구조 유지, 가속 목표에 직접 대응 | 정제·충분한 고유 자료·입력 평균 연결·복구비용과 본학습 권한 | 다음 후보 |
| C 구조·credit 연구 | HRM의 H/L/MagicNorm/TBPTT 또는 NOISE 혼합을 각각 별도 팔로 설계 | 다른 계산/학습 경로를 직접 연구 | cache/STE/credit engine·전체 비용 큼, 각 축을 한꺼번에 바꾸지 않음 | 선결 뒤 |

AC-ODM/LFR은 A에서 도메인·블록 신호의 유효성과 비용을 확인한 뒤 따로 판단한다. 논문별 배수는 더하거나 곱하지 않는다. 기존 AdaMuon·MTP·방문정책·P013/MNTP 결과를 폐기하거나 같은 과학적 질문을 다시 실험한 것이 아니다.

사용자99에 따라 새 실험/구현을 확장하지 않고 현재 근거를 인계한다. 원장98은 이번 근거 회수와 적합성 판단을 기록하며 LFR 동정·고정 코드·세부 재현과 채택은 후속 미완으로 남긴다. 추가300M 금지는 유지한다. 정제 담당 전용 원문/코드/원장 접근·학습 자료 변경0이다.

총괄은 NOISE README와 두 고정 코드 일부·Dust 본문, HRM/AC-ODM arXiv 본문·공식 학회 초록, Microsoft 지정 PDF 본문·저자 TST 설명/초록을 확인했다. TST Appendix A·추가 표와 HRM 공식 코드 일부의 세부 판독은 보조 회신도 사용했다. 총괄의 TST PDF 직접 취득과 PDF 그림 렌더링은 도구에서 실패했으므로 전 논문 그림/코드를 모두 독립 검증했다는 주장은 하지 않는다. 실제 실행 재현0이다.
