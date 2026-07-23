# 6. 학습 품질·안정

발산 없이, 주어진 예산에서 더 좋은 최종 모델을 얻는 기법.

| 기법 | 상태 | 버전 | 작동원리(개선 기여) | 트레이드오프 | 특기 |
|---|---|---|---|---|---|
| **QK-norm** | ✅ | v5 | 어텐션 로짓 폭주 억제 → NaN 발산 해결 | 없음 | v4 300M 발산 주원인 해결. 1e-3까지 안정 |
| **NaN 가드** | ✅ | v5 | clip_grad_norm_이 non-finite면 그 스텝 스킵 | — | 가중치 영구 오염 방지(186분 낭비 방지) |
| **삼진 어닐링** | ✅ | v4~ | 학습 중 FP→삼진으로 매끄럽게 전환(배포=종료 시점) | — | train/test 불일치 없음. compile 안전 버퍼(v5) |
| **STE (AMP 안전)** | ✅ | v4~ | 삼진 backward를 weight 함수 윈도로 → grad 선형 | — | GradScaler·배치크기 불변 |
| **공유 MLP LR 1/√g** | ✅ | v4~ | 그룹이 g회 누적 → LR 보정 | — | weight decay는 미보정이 더 나았음 |
| **warmup 비율 수정** | ✅ | v5 | `max(5, min(steps//10,100))` | — | 짧은 런에서 warmup이 학습 절반 먹던 버그 |
| **LR 재조정 (기본 6e-4)** | ✅ | v5 | d=768·유효배치 131K에 2e-3은 과다 | — | 발산 원인이던 LR 하향 |
| **자동 LR 탐색** | 🧪 | v6 (`lrfind`) | range test(발산의 1/3) + grid 스윕 | — | grid는 warmup 램프 포함(cold-start 오판 방지) |
| **베스트 체크포인트** | ✅ | v6 | val 최저 시 `{name}_best.pt` 저장(raw 기준) | 디스크 | 스케일별 이름으로 클로버 방지 |
| **EMA / 체크포인트 병합** | 🧪 | v6 (`--ema`) | 가중치 지수평균 → 무료 품질 향상 | **decay 스케일 주의** | 주 val은 raw 보고, EMA는 부가 `[ema]`. **실측(P002 t_base): 0.999@2289스텝은 무효**(final ema 4.30≫raw 3.96). 짧은 런은 0.99 권장 |
| **WSD 스케줄** | 🧪 | v6 (`--sched wsd`) | 긴 plateau + 마지막 20% 감쇠 | — | plateau 체크포인트 재사용(도메인 분기). 근거 MiniCPM |
| **조기 종료** | 🧪 | v6 (`--early-stop`) | val 개선 없이 N회 → 종료 | 본 실행은 undertrained라 효과 제한 | LR/아키텍처 스윕용 |
| **train-val 모니터** | ✅ | v6 | 매 eval에 `val-train` 출력 | — | 과적합 신호 감시(현재는 undertraining) |
| **스케일별 체크포인트 이름** | ✅ | v6 | `{preset}_{data}_{tokens}_{arch}` | — | tiny 스모크가 300M을 덮어쓰던 버그 해결 |
