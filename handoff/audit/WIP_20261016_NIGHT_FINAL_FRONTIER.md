# TinyLM experiment frontier audit

- schema: `TINYLM_FRONTIER_V1`
- frontier SHA-256: `74380C2B90A645F3E9AE0C4B09293881BC53B62ADF959F2C1A7EEF3403C8CC15`
- physical/index/frontier: 129/129/129

| plan | state | readiness | live launcher | hours | first unfinished | first prerequisite | conflicts |
|---|---|---|---|---:|---|---|---|
| P001 | DONE | DONE | 없음 | 0.000 | 미식별 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-07-30 | 없음 |
| P002 | DONE | DONE | 없음 | 0.000 | 미식별 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-07-25 | 없음 |
| P003 | DONE | DONE | 없음 | 0.000 | 미식별 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-07-30 | 없음 |
| P004 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-07-24 | 없음 |
| P005 | ONGOING | HOLD | 없음 | 0.000 | 단계4 — ★승격 조합의 비트 동일성 (⚙1.4h · 학습 1) | > ⏸선결: m100R5 프리셋이 만들어진 뒤(= 사용자 최종 승인 뒤). 그 전에는 못 돌린다. | 없음 |
| P005b | ONGOING | HOLD | 없음 | 0.000 | 단계2 (= b-2) — ★RMS-match 규약을 실제로 돌린다 (⚙3.4h · 학습 2) | ⚠️구현 선결 ⚙0.3h: --qk-gain {fixed,learn} · --qk-gain-init(기본 fixed = 비트 동일). | 없음 |
| P006 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | MTP학습/추론과FastMTP분리. P101A8M 네팔실물완료·최종CE/답/망각별도·추론정합음성. FastMTP self-distillation/동적어휘미구현. \| 2026-10-13 | 없음 |
| P007 | ONGOING | HOLD | 없음 | 0.000 | 단계별 상태 | - P007B — 🚫 재실행 보류. 선결 = ① 공통 val 고정 ② L4 고갈 감지. | 없음 |
| P008 | DONE | DONE | 없음 | 0.000 | 미식별 | 결과 026 게이트 — s=0 이어도 메모리가 안 돌아온다 \| P043 의 선결 조건이 됐다 | 없음 |
| P009 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-07-24 | 없음 |
| P010 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-07-24 | 없음 |
| P011 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-07-24 | 없음 |
| P012 | DONE | DONE | 없음 | 0.000 | 미식별 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-07-25 | 없음 |
| P013 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-07-24 | 없음 |
| P014 | DONE | DONE | 없음 | 0.000 | 미식별 | > 레퍼런스 정확성·Triton·LUT 알고리즘 대조·상주 회계가 전부 끝났다(결과 003·016 §23·§24·028). 남은 것은 속도 하나이고 그것은 커널 구현이 선결이다. | 없음 |
| P014B | DONE | DONE | 없음 | 0.000 | 단계 3 — P014 로 인계 ⏸ G2 통과 후 | - 선결: 빌드(U5). §단계0 의 G0 중 라이선스는 통과, 빌드는 미결 | 없음 |
| P014C | DONE | DONE | 없음 | 0.000 | 단계 2 — 속도 게이트 ⏸ ← 지금 여기 · GPU 0 · 수 분 · 배치 미작성 | per-row \| O 개(층당 768~2048) \| ★PyTorch 내장 후보 있음(§4 확인 선결) | 없음 |
| P014D | ONGOING | HOLD | 없음 | 0.000 | 미식별 | ⚠️★이것이 D1 규약의 사례다: *"미룬다" 고 쓸 때 무엇이 선결이고 얼마인지를 숫자로.* | 없음 |
| P014E | ONGOING | HOLD | 없음 | 0.000 | 미식별 | - G0 WSL SH의 원 이름은 run_P014E_Stage0W_rotation_math_contract.sh였다. 사용자 실행은 합성12행 exit0으로 결과099에 기록했고 재현 명령 보존 뒤 삭제 이력으로 이관한다. G1~G3는 G0와 정확 checkpoint·wall 병목·품질 분모 선결 뒤 별도 suffix | 없음 |
| P015 | DONE | DONE | 없음 | 0.000 | 미식별 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-07-30 | 없음 |
| P016 | ONGOING | HOLD | 없음 | 0.000 | 단계5 — 3:4 CPU 커널: 속도 축 재심사 (⏸이식 선결 · 배치 없음) | 선결 \| ★사용자 허가 + moonshot 3791a88 에서 3파일 이식(⚙1.5h) + 빌드 환경(ninja·MSVC) | 없음 |
| P017 | DONE | DONE | 없음 | 0.000 | 미식별 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-07-30 | 없음 |
| P018 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | 일부 단계 완료 또는 구현 진행 중. 계획서의 최신 단계표를 따른다. \| 2026-08-08 | 없음 |
| P019 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-07-25 | 없음 |
| P020 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-07-25 | 없음 |
| P021 | DONE | DONE | 없음 | 0.000 | 미식별 | → P013 선결조건: seq 절반이면 mb 2배로 M 유지. 미준수 시 -8.7%. | 없음 |
| P022 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | > 1단계 선결조건 2건(둘 다 없으면 결론을 못 낸다): | 없음 |
| P022B | ONGOING | HOLD | 없음 | 0.000 | 단계 2 — BF16 옵티마이저 상태(논문 §3.3.3) ✅ 구현 완료 2026-08-07 · 배치 run_P022B_stage2_optstate.bat | - [ ] 단계1·2 는 구현 선결 → 배치를 만들지 않는다(ai_dev_tool/03 §1) | 없음 |
| P022C | ONGOING | HOLD | 없음 | 0.000 | Stage4 \| S3 \| 300M shadow 최종 확인 \| 현 계열 ruler 안, 2-seed 후속 판정 \| 1.6~3.2 | Wc weight cache는 2/3 형상 speed PASS지만 memory·NRMS 전 형상 FAIL. cache-only 통합 중단, shadow는 별도. \| 2026-09-21 | 없음 |
| P023 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 착수 시 선결 조건: | 없음 |
| P024 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-07-25 | 없음 |
| P025 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-07-25 | 없음 |
| P025B | ONGOING | HOLD | 없음 | 0.000 | Stage0a ⚠️ 무효 \| 실제 MLP 형상 native 2:4 진단 최초 시도 \| tinylm import 전에 종료; 과학적 결과 NOT_RUN(082) \| 0.1 미만 | Q1 \| 현 Ada/PyTorch에서 768↔2048·2048→768이 native 2:4 forward·input-grad를 실행하는가 \| 속도 축의 0단계 선결 | 없음 |
| P026 | DONE | DONE | 없음 | 0.000 | 단계 5 — 빠진 칸: qb_wsd60_s85 ✅ 완료 2026-07-31 (결과 015 §7) | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-08-13 | 없음 |
| P027 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | - 즉 선결과제 = 타잉-임베딩(emb.weight 를 lm_head 로 재사용) + CUDA Graphs 정적버퍼 충돌 해소. | 없음 |
| P028 | ONGOING | HOLD | 없음 | 0.000 | 단계 2 — 한국어 공통 원문 \| ⏸ 신설·대기 \| 아래 | > 선결: ① datasets/squad/train-v2.0.json 에서 고유 context 를 뽑아 텍스트로 펴는 로더 | 없음 |
| P029 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | Stage2W greedy/KV 두 모델×5문항 원답안10건 저장·exit0. 로그에는 길이만 있어 footer/EOS/반복 품질은 원답안 직접 검수 전 NOT_RUN; P097 공용 배너 오표기는 수정. 결과013 §6. \| 2026-09-25 | 없음 |
| P030 | ONGOING | HOLD | 없음 | 0.000 | 단계7b — 단계7 재측정. 이번엔 --drop-latent 를 준다 (⚙0.3h · 학습 0) | 선결 \| 없다 — 두 체크포인트가 다 있다 | 없음 |
| P030B | ONGOING | HOLD | 없음 | 0.000 | Stage1W 후속 \| Stage0W 결과 뒤 산정 \| 새 학습 없음 | 비용·선결 \| 값 | 없음 |
| P031 | DONE | DONE | 없음 | 0.000 | 미식별 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-08-01 | 없음 |
| P032 | DONE | DONE | 없음 | 0.000 | 미식별 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-08-01 | 없음 |
| P033 | PLANNED | HOLD | 없음 | 0.000 | 단계 3 — Chinchilla 전체 (조건부, 최종) | → 단계 1(데이터 공급 조사)이 이 계획의 최우선 선결과제다. 시간 계산보다 먼저다. | 없음 |
| P034 | DONE | DONE | 없음 | 0.000 | 단계 2 — _wq 단독 상주 모드 (Q2) ⏸ 대기 — 절감 배수가 정확히 2.00× 로 확정됐다 | 단계 3C (언팩 캐시) \| ⏸ 신설 · 구현 선결 \| 아래 | 없음 |
| P034B | DONE | DONE | 없음 | 0.000 | 미식별 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-08-30 | 없음 |
| P034C | ONGOING | HOLD | 없음 | 0.000 | 미식별 | - 상태: ✅단계1 배치 있음(run_P034C_stage1_rss_crosscheck.bat — 도구가 이미 다 있다) · 나머지는 구현 선결 | 없음 |
| P035 | DONE | DONE | 없음 | 0.000 | 단계 2 — 조건부 (단계 1 이 형태 민감성을 보일 때만) | qa_step* 이 더 좋음 \| 예측 반대. 급전이가 유리 \| 단계 2 착수. 다만 1런씩이라 재현런 선결 | 없음 |
| P035B | ONGOING | HOLD | 없음 | 0.000 | 미식별 | 현재 상태(2026-09-15): Stage1 A3 완료(결과 084). G0·G1은 PASS했으나 G2의 지속 후반 궤적차는 불성립했다. A4 adaptive/freeze 후보를 열 근거가 생기지 않았고 A5 기본값 변경은 미승인이다. \| 2026-09-16 | 없음 |
| P036 | DONE | DONE | 없음 | 0.000 | 단계1 에서 셋이 비슷 \| 우리 스케일엔 없음 \| 계획 종결. 결과 008·016 의 해석 확정 | - 표본 1개씩. 0.024 를 갓 넘으면 재현런 선결. | 없음 |
| P037 | ONGOING | HOLD | 없음 | 0.000 | 단계 1 — 경계 판정 신뢰도 ⏸ 대기 · GPU 불필요 · 수 분 (= 구 P028 단계 0.7) | Stage0W는 val/source 변경 효과를 측정한 것이 아니라, 기존 두 캐시가 어떤 차이를 갖고 있고 B/A를 안전하게 만들 수 있는지 묻는 실제 입력 감사다. overlap이 있으면 exit8로 정직하게 멈추고, B/A builder는 그 문서를 train에서 배제하는 계약 전에는 작동시키지 않는다. 단순 val SHA 차이/JS는 품질 인과가 아니다. B/A/C 신규 캐시 builder와 학습 런처는 Stag | 없음 |
| P038 | DONE | DONE | 없음 | 0.000 | 미식별 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-07-31 | 없음 |
| P039 | DONE | DONE | 없음 | 0.000 | 미식별 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-08-07 | 없음 |
| P040 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | 일부 단계 완료 또는 구현 진행 중. 계획서의 최신 단계표를 따른다. \| 2026-08-07 | 없음 |
| P041 | PLANNED | HOLD | 없음 | 0.000 | 단계 3 — 한국어 비율 스윕(선택) ⏸ · GPU 큼 | > 그래서 공통 원문 bpb(P028)가 유일한 다리이고, 한국어 공통 원문(P028 단계2)이 선결이다. | 없음 |
| P042 | ONGOING | HOLD | 없음 | 0.000 | 단계 3 — 본 런 확인 ⏸ 단계2 통과 시 · GPU 약 3.5h | 일부 단계 완료 또는 구현 진행 중. 계획서의 최신 단계표를 따른다. \| 2026-08-08 | 없음 |
| P043 | DONE | DONE | 없음 | 0.000 | 단계 2 — KD 와의 대결 ⏸ · GPU 0 (체크포인트 재사용) · 수 분 | 선결 \| 내용 \| 상태 | 없음 |
| P044 | DONE | DONE | 없음 | 0.000 | 단계 2 — 짝비교 ⏸ · GPU 0 · 수 분 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-08-31 | 없음 |
| P044B | DONE | DONE | 없음 | 0.000 | 미식별 | 순 \| 단계 \| 비용 \| 선결 | 없음 |
| P045 | DONE | DONE | 없음 | 0.000 | 미식별 | - 선결: 없음 | 없음 |
| P045B | DONE | DONE | 없음 | 0.000 | 단계1 착수 중 발견 — 🚫★★§3 의 "A1 과 A3 는 같은 걸음" 이 틀렸다 | 선결은 없다(플래그·프리셋 전부 존재). ★사용자가 큐에 넣기로 하면 그때 만든다: | 없음 |
| P046 | DONE | DONE | 없음 | 0.000 | 미식별 | - 선결: 없음. _svd_emb_init 구현 완료 | 없음 |
| P047 | DONE | DONE | 없음 | 0.000 | 단계 2 — 필터 재학습 ⏸ 조건부(단계1 이 양성) · GPU 약 3.5h + 캐시 생성 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-08-07 | 없음 |
| P048 | ONGOING | HOLD | 없음 | 0.000 | 단계 2 — 스택 검증 ⏸ 단계1 통과 시 · GPU 3.2h | 일부 단계 완료 또는 구현 진행 중. 계획서의 최신 단계표를 따른다. \| 2026-08-20 | 없음 |
| P049 | DONE | DONE | 없음 | 0.000 | 단계 2 — 메모리당 품질 곡선 ⏸ 단계1 후 · GPU 0 | 선결 구현 C1 — init_from_dense 의 깊이 확장 이식 | 없음 |
| P049B | ONGOING | HOLD | 없음 | 0.000 | 단계2 (벽시계 정합 mC_long) \| 약 4h \| ⏸ | (의사결정 함정 D1 — 선결을 숫자로 적었어야 했는데 그 숫자가 틀린 것이었다.) | 없음 |
| P050 | ONGOING | HOLD | 없음 | 0.000 | 단계 3 — 아키텍처 고도화 이후 재실행 ⏸ REVIEW2 확정 이후 | > P049 의 깊이 확장 이식 같은 복잡한 선결 구현이 불필요해진다. | 없음 |
| P050B | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 단계 \| 내용 \| 비용 \| 선결 | 없음 |
| P051 | DONE | DONE | 없음 | 0.000 | 단계 2 — (조건부) 다른 레버와의 결합 ⏸ 단계1 이 분해능 안일 때만 | 종결 판정과 재개 조건은 계획서·결과문서가 소유한다. \| 2026-08-30 | 없음 |
| P052 | ONGOING | HOLD | 없음 | 0.000 | 단계 1 — 시드 2024 로 두 팔 재학습 ⏸ · GPU 약 7h(3.5h × 2) · 무인 실행 가능 | > 신설 2026-08-07. REVIEW2 선결. 근거 = paired_eval.py 자체 경고 | 없음 |
| P053 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | 일부 단계 완료 또는 구현 진행 중. 계획서의 최신 단계표를 따른다. \| 2026-08-14 | 없음 |
| P054 | ONGOING | HOLD | 없음 | 0.000 | 단계 4 — ⏸ 조건부·낮은 우선순위: 600M 풀·wsd 로 부모 재학습 | > ★★안 C 는 안 A 의 선결이지 대안이 아니다. 20시간을 쓸지 말지를 3.2시간에 정한다. | 없음 |
| P055 | ONGOING | HOLD | 없음 | 0.000 | 단계1 (kd_alpha 스윕) \| ⏸ 조건부 대기 — 아래 참조 \| — | A3 \| KD/비KD 스텝 스케일 \| ⏸ 3회 연속 미측정 \| 선결 = json history 10줄 | 없음 |
| P056 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-08-13 | 없음 |
| P057 | ONGOING | HOLD | 없음 | 0.000 | 단계 0b 결과 \| 단계1 | 선결 \| 얼마 \| 상태 | 없음 |
| P058 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | 일부 단계 완료 또는 구현 진행 중. 계획서의 최신 단계표를 따른다. \| 2026-08-13 | 없음 |
| P059 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-08-13 | 없음 |
| P060 | DONE | DONE | 없음 | 0.000 | 미식별 | Windows 결과 046 보존·계획 종결. WSL native 후속은 P060B로 이관. \| 2026-08-20 | 없음 |
| P060B | ONGOING | HOLD | 없음 | 0.000 | Stage2W 🚫 정합 미통과 \| 배포 prefill/decode·장문 생성 정합성 \| seq128 decode 정합 실패; seq512/1024·속도·text NOT_RUN \| 088 §10.1 | WSL + sm_89는 플랫폼 선결을 만족한다. 패키지 존재는 커널 PASS가 아니다. | 없음 |
| P061 | DONE | DONE | 없음 | 0.000 | 단계1 (A·B 학습) \| ⏸ 우선순위 낮춤 — 아래 참조 \| — | 선결 \| 얼마 \| 상태 | 없음 |
| P061B | PLANNED | HOLD | 없음 | 0.000 | 미식별 | ★의사결정함정 D1 대로 숫자를 적는다: 선결은 P073 단계2(3.6h) 와 스크립트 ⚙30줄이고, | 없음 |
| P062 | ONGOING | HOLD | 없음 | 0.000 | 단계19 — 32 예산 최종 후보를 같은 토큰에서 붙인다 (⚙9.2h · 학습 3) | Q5 \| R=2 학습의 최적 lr 은 얼마인가 \| 단계1(선결 구현) | 없음 |
| P063 | ONGOING | HOLD | 없음 | 0.000 | 단계 2 — 판정 규칙 개정 ⏸ · 문서 | 일부 단계 완료 또는 구현 진행 중. 계획서의 최신 단계표를 따른다. \| 2026-08-20 | 없음 |
| P064 | DONE | DONE | 없음 | 0.000 | 미식별 | Stage0/0b 완료. KorQuAD 소차 판정 불가·NLI 퇴화로 지표를 내리고 P069/P085로 승계. \| 2026-09-19 | 없음 |
| P065 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | > ★의사결정 함정 D1: *"미룬다" 고 쓸 때는 무엇이 선결이고 그것이 얼마인지 숫자로 적는다. | 없음 |
| P066 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | > 구현이 선결이면 계획서에만 설계를 남긴다."* 아래는 전부 구현이 선결이다. | 없음 |
| P067 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | - 상태: ⏸단계0 만 착수 가능(학습 0). 단계1 이후는 구현이 선결이라 설계만 둔다 | 없음 |
| P068 | PLANNED | HOLD | 없음 | 0.000 | 단계2 — ⏸stochastic rounding(H-A 확인 후에만) | - 상태: ⏸설계만. 배치를 만들지 않았다 — 구현이 선결(§8) | 없음 |
| P069 | ONGOING | HOLD | 없음 | 0.000 | 단계3 — ⏸CE 방식 GSM8K | - 상태: 진행 중 — Stage0bW 사용자 LAMBADA 5,153문항×두 시드 완료(결과056 §9). P069 전체 지표·지능 서열은 아직 열려 있으며 옛 자산 선결은 §9에서 정정했다. | 없음 |
| P070 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | ⚙합 약 50줄. ★선결은 구현 하나뿐이고 실험 선결은 없다. | 없음 |
| P070B | PLANNED | HOLD | 없음 | 0.000 | Stage0Wc 회수 | B 권장 \| 고정 경로 기능→조건부 학습→마지막 라우터 \| P062 음성·P072 지도와 비교 가능, 중간 비용 \| 코드·모델 gate 선결 | 없음 |
| P071 | DONE | DONE | 없음 | 0.000 | 미식별 | 결과 054에서 CE/KD 청킹 등가성과 VRAM 효과를 확인해 종결. \| 2026-09-19 | 없음 |
| P072 | DONE | DONE | 없음 | 0.000 | 미식별 | 단계 \| 무엇 \| 비용 \| 선결 | 없음 |
| P073 | DONE | DONE | 없음 | 0.000 | 미식별 | Stage0~6b 완료. clip 격자는 이상 발생 전까지 명시 보류라 현 계획 종결. \| 2026-09-19 | 없음 |
| P074 | DONE | DONE | 없음 | 0.000 | 미식별 | ⏸단계1 결과를 보고 착수한다 — 지금 배치를 만들지 않는다(D1: 선결과 시간을 숫자로). | 없음 |
| P075 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | 선결 \| ★단계 0(잴 자가 없다) | 없음 |
| P076 | ONGOING | HOLD | 없음 | 0.000 | Stage2eW \| 새 두 최종 체크포인트를 같은 600M 결정적 val crop으로 paired 평가 \| 사용자 GPU 평가 약0.3h; 한 팔 실패면 평가 중단 | ⏸선결: 단계2 결과. 🚫압축 교사가 dense 교사보다 나쁘면(품질이 낮으므로) 교락이다 — | 없음 |
| P077 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | - 🚫단계1~4 는 전부 구현 선결이다. 배치를 만들지 않는다(R22). | 없음 |
| P078 | DONE | DONE | 없음 | 0.000 | 미식별 | ⏸선결: TinyDataset 단계0 승인 · 강제선택 채점기 · 단계0 의 H1/H2 판정. | 없음 |
| P079 | DONE | DONE | 없음 | 0.000 | 단계 재편 | 단계 \| 팔 \| 시간 \| 선결 | 없음 |
| P080 | PLANNED | HOLD | 없음 | 0.000 | 미식별 | - 상태: 🔜계획. 단계0·1 은 선결 없음(학습 0 · GPU 0) | 없음 |
| P081 | DONE | DONE | 없음 | 0.000 | 미식별 | - 현재 상태(2026-09-25 재감사): 🚫 Stage0 사용자 실측 음성(결과070). 아래 2026-08-31 선결 없음·균등0.39% 표기는 역사 초안이며 현재 새 Stage0 SH를 만들지 않는다. | 없음 |
| P082 | PLANNED | HOLD | 없음 | 0.000 | Stage 3~4 native/Gemma screen \| 10 GPU-h \| 20~40 GPU-h \| 40 GPU-h cap \| 생성·검증 포함; 구현 후 재산정 | 항목 \| 비용 \| 성격 \| 선결 | 없음 |
| P083 | PLANNED | HOLD | 없음 | 0.000 | Stage 7 LM Studio \| ⚙ 1~3일 + runtime 반영 대기 \| 불필요 \| downstream release 일정 | 실행 전. 계획서의 첫 선결과 비용을 확인한다. \| 2026-09-03 | 없음 |
| P084 | DONE | DONE | 없음 | 0.000 | Stage0(상주 실측) \| 🚫미실행 — mem_runtime.py 배치 없음. Stage1 json 이 대신 답했다 \| KV 엔트리 12 | ★mem_runtime.py 실측이 선결이고, 그 전에는 d16 팔을 설계하지 않는다. | 없음 |
| P085 | DONE | DONE | 없음 | 0.000 | Stage2 \| 외부 5모델 동일 채점기 대조 \| 0 \| 1.0h \| ⏳선결: 외부 HF 어댑터(⚙1h) | Stage2 \| 외부 5모델 동일 채점기 대조 \| 0 \| 1.0h \| ⏳선결: 외부 HF 어댑터(⚙1h) | 없음 |
| P086 | ONGOING | HOLD | 없음 | 0.000 | 단계2 — ★타잉 × Muon (⚙1.4h · 학습 1) | ★★Stage3 \| ★벡터 승수 · 중복 없는 배치 · 승수 WD 0(2026-09-08(2차) 재심으로 부활) \| 3.2h \| 3.2h \| ⏸구현 선결 ⚙0.4h — 아래 §단계3 | 없음 |
| P087 | DONE | DONE | 없음 | 0.000 | Stage0 val 언어 구성 \| 🚫미실행 — diag_val_lang.py 배치 없음 \| ⚠️*"한국어가 살아 있다"* 는 아직 주장 | Stage3bW paired Δ−0.2116·t−246.93로 누락 평가 회수. 단일시드 한계를 남기고 계획 종결. \| 2026-09-20 | 없음 |
| P088 | DONE | DONE | 없음 | 0.000 | Stage11 — ★★300M 가족과 600M 가족을 잇는다 (학습 0) — ✅2026-09-11 완료 | > 🚫지난 핸드오프가 이 명령을 못 적었다 — 그 이유가 아래 §선결이다. | 없음 |
| P089 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | 현재 상태(2026-09-14): Stage2b는 정상 종료했다. 폭 대가 +0.1017을 깊이 회복 +0.1028이 상쇄했지만 순이득은 −0.0011로 자 안이어서 채택선 미달·보류다 (결과 077 §12). \| 2026-09-14 | 없음 |
| P090 | ONGOING | HOLD | 없음 | 0.000 | 단계5 \| ⏸계속 사전학습 팔 — 고밀도 34,000 레코드를 사전학습에 얹는다 \| 2.5h \| 1 \| ⏸별개 축(§8) | > §1(왜 지능이 오르나) · §3(선결) · §4(데이터) · §5(벤치) · §9(성과가 없어도 유지할 가치)로 옮겼다. | 없음 |
| P090B | ONGOING | HOLD | 없음 | 0.000 | Stage1cW C 공통 원답안 \| ⚙0.3h \| 사용자 GPU/모델, 새 출력 JSONL | Stage0W~Stage1cW 중 실제 완료한 단계의 명령·로그는 결과096의 시간순 절·재현명령 부록이 소유한다. Stage1aW·1bW -done은 사용자 삭제 지시로 제거했고 Git 원본에서 복구 가능하다. 2배 train 풀 보정이 필요하면 총604M 별도 cache·새 단계명/태그의 선결 검토가 필요하다. Stag | 없음 |
| P091 | ONGOING | HOLD | 없음 | 0.000 | Stage5까지 최대 \| 18.3~22.6 | - 2026-09-19: R2의 산식·배선 선결을 독립 R2t gate로 구현했다. 실제 TinyLM tiny model에서 | 없음 |
| P092 | ONGOING | HOLD | 없음 | 0.000 | Stage0b ⚠️ 무효 \| mask/ternary forward-backward 최초 시도 \| tinylm import 전에 종료; 과학적 결과 NOT_RUN(083) \| 진입 시간만 | 결과 083 §9의 여덟 JSON은 모두 exit0·skip0다. 30M dense 5.02031 대비 static50 +0.64031, dynamic50 +0.65813, dynamic25 +0.51875로 사전 30M 중단선 +0.15를 세 branch 모두 초과했다. 그 뒤 실행된 100M는 실측으로  | 없음 |
| P093 | ONGOING | HOLD | 없음 | 0.000 | Stage4 \| Stage3 승자만 seed 또는 600M 한 축 전이 \| 두 조건 부호 일치 \| ⚙3.2~6.2h | D2-use-normalized \| 현 g2 구조에서 공유횟수별 gradient/update 규약만 교정 \| 정확 직접공유 \| anneal audit이 아니라 optimizer audit 확장 질문; 별도 계측 선결 | 없음 |
| P093B | ONGOING | HOLD | 없음 | 0.000 | Stage3W — 조건부 GSQ 삼진 인자·native LoRA round-trip (종료: 선결HOLD8·실물NOT_RUN) | > 초기2026-10-10 r8/16·GSQ식B의복원음성과factor선결HOLD는유지한다. 최신2026-10-11 결과103 §8~§12:dev선택/r8~64실물·표현48·실제반복24답/2186step회수. precision은선결HOLD,고정precision수치원인·C새학습은NOT_RUN이다. | 없음 |
| P094 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | 선결이므로 residual·storage 구현을 지금 만들지 않는다. 첫 행동은 R0 증거표이며, | 없음 |
| P095 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | S0b bridge 뒤 S0bT tiny Transformer 사용자 기능 실행도 read-before-write·prefix·reset·backward PASS(결과087 §5), state49,288B. learned WRITE·1MiB 실모델·언어 QA/학습/배포는 NOT_RUN. \| 2026-09-26 | 없음 |
| P096 | ONGOING | HOLD | 없음 | 0.000 | 미식별 | Q2a synthetic bounded-canary 계약 PASS. 실문항·팀 의미검토가 다음. \| 2026-09-19 | 없음 |
| P097 | ONGOING | HOLD | 없음 | 0.000 | Stage3R~4 \| 추가 학습 4.8h + 공통평가 1.2h \| 사용자 GPU | - Stage2 평가는 이제 선결 checkpoint 네 개가 있으나, 기존 eval_bench_suite.py가 단일 | 없음 |
| P098 | ONGOING | HOLD | 없음 | 0.000 | 단계1 — 300M 2x3 seed panel | > COMPASS 재귀 축. 사용자의 2026-09-21 48시간 queue·선결구현 | 없음 |
| P100 | ONGOING | HOLD | 없음 | 0.000 | 단계 4 — 구조·학습방법 가설, 단계 2·3 음성일 때만 | 사람 검토, PII·평가 오염, 첫 질문 그룹 분할, mask/길이 gate가 선결이다. | 없음 |
| P101A | ONGOING | HOLD | 없음 | 0.000 | Stage0 τ=1 logits max_abs≤1e-5와 gain gradient 비영 \| 작은 기능 계약만 PASS, 실제 M0 효과 NOT_RUN | 순 \| 단계·SH \| 선결/판정 | 없음 |
| P102A | ONGOING | HOLD | 없음 | 0.000 | Stage0bW S1 작은 모델 \| 약0.1h \| 사용자 CPU 모델 gate; Codex NOT_RUN | Stage1W T1 paired 100M 두 팔 \| ⚙각 0.7h, 합계 약1.4h \| 사용자 단일 GPU; smoke PASS 선결 | 없음 |
| P103A | ONGOING | HOLD | 없음 | 0.000 | Stage0cW X2 작은 모델 \| 약0.1h \| 사용자 CPU 모델 gate; Codex NOT_RUN | read-only 진단은 canonical JSONL·manifest SHA·legacy tokenizer SHA를 대조하고, 직렬화된 토큰 ID가 정확히 같은 prefix만 세며 원문을 출력하지 않는다. 재현 SH는 최소 공유 길이 32/64/128과 자연  | 없음 |
| P104A | ONGOING | HOLD | 없음 | 0.000 | Stage1 direct Triton 미호출·CUDA 미지원 \| UNSUPPORTED/NOT_RUN. reference fallback 성공을 direct PASS로 승격하지 않음 | 단계 \| 실물 파일·순서 \| 선결·예상 | 없음 |
| P105 | ONGOING | HOLD | 없음 | 0.000 | Stage2W 조건부 정제·matched 학습 \| 과거 P097 팔 기준 ⚙2.4h 이상+평가, 사전 재산정 \| 사용자 GPU | - 2026-09-25 21:04: 사용자 Stage1Wc 원본에서 7모델×40=280생성·감사 모두 exit0. 옛 출력과 model/case/decode 키·prompt·모델/토크나이저 SHA·seed·디코딩·생성문 280/280 동일, EOS94·상한186·EOS 부재0, 반복 후보140 | 없음 |
| P106 | ONGOING | HOLD | 없음 | 0.000 | Stage0mW/nW/oW \| FFN32 micro8 → FFN60 micro8 → FFN32 micro4. 교사 실제 생성과 P076 같은 모양의 합성 학생 Muon 1 step을 겹침 \| 세 팔 모두 짧은 공존 exit0·OOM0. nvidia-smi 시작 free−증가표본은 126/1,019/4,679MiB. 앞 두 팔은 안전여유 부족; micro4는 별도 학습 recipe 후보일 뿐 | 교사 출력 중 독립 검증된 answer 문자열만 기존 canonical assistant target으로 만들고, 불확실·오답은 학습에서 제외해 별도 원장에 둔다. 기존 P090B 공개 SFT의 license·사람 품질·오염·split/mask TRAIN_READY와 부모/tokenizer SHA가 선결이다. 학생 2M processed-token pilot는 기능·오염·비용 진단이지 지능 승격이 아니며 같은 원문/부모·토 | 없음 |
| P106B | ONGOING | READY | run_P106B_Stage4lW_gemma_chat32_repeat4.sh, run_P106B_Stage4mW_gemma_capability_multiaxis.sh, run_P106B_Stage4lWd_budget_literal_repeat4.sh, run_P106B_Stage4mWd_budget_literal_multiaxis.sh, run_P106B_Stage4kWf_mtp_completed_corpus.sh, run_P106B_Stage4k0Wf_mtp_corpus_student_wire.sh, run_P106B_Stage4lWe_mtp_corpus_chat32_repeat4.sh, run_P106B_Stage4mWe_mtp_corpus_multiaxis.sh, run_P106B_Stage4jWk_stream_mtp_fork_start.sh, run_P106B_Stage4jWl_stream_mtp_explicit_resume.sh, run_P106B_Stage4kWg_stream_completed_corpus.sh, run_P106B_Stage4k0Wg_stream_student_wire.sh, run_P106B_Stage4lWf_stream_chat32_repeat4.sh, run_P106B_Stage4mWf_stream_multiaxis.sh | 54.000 | Stage3fW 통합1 \| A1/A2/B2/B4/C4 현재 code·source·parent·tokenizer SHA PASSED 후,1서버2slot·slotctx6144·B2·bounded queue·Cepoch1 보존64+새변형64 \| micro8×accum16·한 optimizer만, 옛v17 concept는 새생성에서 제외; fresh KO32/EN32·형식/손실/gradient·NVML/GDN. 체크포인트0·품질 NO | > 현재 본경로 선결: 남은옛v5/v4/OFF/V2의14개live런처는해당버전75M/quota·원래과제/학습자가보는근거정책·wire/정확자식의선결이남아이번인계에서HOLD다. 파일존재/자동READY는실제실행가능증거가아니다. 현재짧은후속의성공/실패를옛버전의선결통과로대체하지않는다. | 없음 |
| P106C | ONGOING | HOLD | 없음 | 0.000 | Stage4W \| 256업데이트·384답·native2회 \| 같은 학생 | 구현은 p106c_data.py, p106c_replay.py, CPU 회귀다. 원본 부모/자료는 불변이고 새 HF/sft_ready/p106c_replay_v1/<phase>/에만 write-once 저장한다. 기존 파일·중단 출력이 있으면 덮지 않고 새 단 | 없음 |
| P106D | ONGOING | HOLD | 없음 | 0.000 | Stage1Wc — 새 namespace의 matched4096/64 / 사용자 자료 생성 NOT_RUN | > 계기: 사용자2026-10-09 A/C1/C3 적용·B 단일호출 질문/풀이 확인·신규 계획/SH/선결구현 요청. | 없음 |
