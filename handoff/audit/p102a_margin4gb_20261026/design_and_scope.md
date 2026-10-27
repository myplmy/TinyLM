# P102A Stage2hW — 실제 동결 모델의 CE margin 진단

권한은 사용자94번의 CPU/GPU 4GB 제한이다. 타세션 정제 원장과 goalc 파생 경로·보호 데이터는 열거나 수정하지 않는다. 원형 모델·입력·기본 CE/KL 및 과거 수치 문턱은 불변이다.

| 안 | 범위 | 장점 | 한계 | 영향 | 비용 |
|---|---|---|---|---|---|
| A 선택 | CPU 실제 두 모델 순전파와 GPU 소량 로짓 CE 미분 | 낮은 VRAM으로 실제 margin 미측정 해소 | 최종 동결 모형·일부 고정 crop만 관측 | 새 진단/시험과 P102A 계획·결과 | 최초 CPU 실측 필요, 내부900초 상한 |
| B | learned prefix router의 labels/head/TEST | 방문 선택의 구현 공백 해소 | 자료·선별·새 학습 계약이 더 필요 | 별도 라우터와 자료 | 현재보다 큼·미측정 |
| C | 미완 공식 벤치마크 추가 | 미측정 능력축 보완 | 의존성·공식 평가 계약 준비 필요 | 별도 평가 도구·원형 | 미측정 |

A는 새 학습 없이 사용자가 참고한 CE 논문의 실제 적용 선결을 확인한다. 제품/optimizer 변경0, 코드 중복은 기존 route loader·state fingerprint·ce_sum을 재사용해 피한다. 새코드는 scripts/diag_p102a_logit_margin.py와 scripts/test_p102a_logit_margin.py, 이세션 전용 감사·작은결과·P102A 전용 문서만 소유한다. COMPASS/기준표/METHODS/공유목록은 다른 세션이 갱신할 수 있어 즉시 동시편집하지 않고 필요한 연쇄 갱신사항을 별도 기록한다.

동일 학습 원형과16개 사전 고정 update의 첫 crop으로 각16384·두모델32768 target을 관측한다. 비정답 전체 logsumexp를 뺀 실제 정답 margin을 쓰고 최대 logit/top1-top2로 대체하지 않는다. CPU 실제 ce_sum의 분리된 logits gradient와 FP64 안정 target 식을 대조하며 GPU는 고margin8·저margin4·중앙4 위치에 제한한다. GPU 선택은 편향된 수치 probe이므로 전량 빈도로 합산하지 않는다.

사전 예측은 수치 소실이 높은 margin에서만 관측될 수 있으나 선택한 실제 원문에서는 드물거나0일 수도 있다는 것이다. 0이면 이 표본에서 근거를 못 찾았다는 뜻이며 과거 학습 전체나 자유 반복의 원인을 배제하지 않는다. 수치/메모리/소유정리의 완결과 오류를 구분하고 품질 문턱은 만들지 않는다.

CPU 모델 forward와 GPU CE는 서로 다른 단계다. 모델은 GPU로 이동하지 않는다. GPU caching allocator는128MiB 한도이며 전역 관측 사용량은4,000,000,000B 미만이어야 한다. 먼저512MiB 여유를 두고 context를 열며 초과/조회불가 시 GPU 단계를 중단한다. 전역 표본계측은 연속 peak 증명이 아니며 allocator 상한과 구분한다. 타사용 프로세스를 중지하지 않는다.

preflight: 같은 원형 두 checkpoint·같은 crop/토크나이저, 새 tag 조회 기존0이다. optimizer/학습토큰/풀2배 조건은 학습0이므로 해당없음이다. source/입력 pin·새 출력·외부OS timeout과 내부900초·정리/원형재해시가 실행 선결이다. 본학습 지능·반복 인과·학습 중 과거 margin은 미판정이다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
