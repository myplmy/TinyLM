# 실험계획 P006 — MTP(학습용 aux 헤드) + FastMTP(추론 가속) [별개 2건]

> 용어 정리: **학습용 MTP**(DeepSeek-V3식 aux head)는 *수렴* 이득, **FastMTP**(Tencent,
> arXiv 첨부)는 *추론* 가속(speculative decoding, 2.03× 무손실). 서로 다른 목적 — 별개로 다룬다.

## Part A. 학습용 aux MTP 헤드 (수렴 가속)
### 목적
다음 토큰만이 아니라 미래 t+2..t+k 를 경량 헤드로 동시 예측하는 aux loss로 표현력·수렴 가속.

### 구현(안)
- 공유 factorized 헤드 위에 k−1개 경량 예측 경로(위치별 소형 프로젝션). 파라미터 최소.
- loss = CE(t+1) + λ·Σ_{j=2..k} CE(t+j),  k=2~4, λ 스윕.

### 판정
- 동일 토큰·시드에서 **val 수렴(loss-vs-step)**을 베이스라인(NTP only)과 비교. 이득이 노이즈 초과인지.
- 배포시 aux 헤드는 떼거나(추론 NTP) FastMTP(Part B)로 재활용.

### 리스크
- 소형·undertrained 모델에서 MTP 학습 이득은 불확실. tied·factorized 헤드와의 결합 설계 필요.

## Part B. FastMTP (추론 speculative decoding)
### 목적
자기회귀 병목 완화 → 배포 추론 2× 가속(무손실). CPU/엣지 지연 개선에 직접 기여.

### 선결
- Part A로 MTP 헤드 확보 → position-shared 단일 헤드를 self-distill 데이터로 정렬(추론 패턴 일치).
- language-aware dynamic vocab compression으로 draft 오버헤드 절감.

### 판정
- 7종 벤치에서 **acceptance rate · speedup**, 출력 무손실 확인. 표준 NTP 대비 배속.

### 비고
- FastMTP는 배포(추론) 최적화라 학습 격차·메모리 실험과 별개 트랙. CPU 삼진 커널과 결합 시 시너지.
- 구현 난이도: Part A 중간, Part B 높음(추론 프레임워크 통합).

## 2026-10-12 현재 구현과 미실행 범위

Part A의 경량 projection/미래지도 개념은 [P101A 후속](P101A_M0-U2-QK-MTP-기능계약.md)에서 assistant-turn horizon2/3/4·shared vocabulary로 구현했다. 사용자 선택은 같은8M×4epoch·scratch/parent×NTP/MTP 네 팔이며 CPU29시험은 [092 §10](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)에 있다. 실제 학습효과는 NOT_RUN이다. M0의E384 실패를 모든MTP가막힌사유로 쓰지 않는다.

Part B는 **완전 FastMTP 구현/실험이 아니다**. 별도 greedy prototype만 draft/main 검증·잘못된 suffix KV 재구축·head off/2/3/4로 준비했다. [FastMTP 원문](https://arxiv.org/html/2509.18362v1)의 position-shared self-distillation·recursive alignment·dynamic vocabulary compression은 아직 구현하지 않았다. 원문2.03배를 TinyLM 속도로 옮겨 쓰지 않는다. 학습된 새head가 생긴 뒤 P101A Stage4aWa/Wb에서 실물BF16 정합·시간·자원을 측정한다. Gemma외부교사 MTP의 실제6건은 [101 §91](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 별개 트랙이다.
