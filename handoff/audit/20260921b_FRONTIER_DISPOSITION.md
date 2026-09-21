# 2026-09-21b frontier disposition — 51.1h WSL 연구 pack

- frontier: `20260921b_FRONTIER.json`
- SHA-256: `7E239EF0F4A8DCDD38CE4F8539B60C34E7821F7A0470DF303621871FB592AA3C`
- coverage: non-DONE 72/72
- 편성: READY 50.8h + 앞 gate 0.3h = **연구 51.1h**. smoke/cleanup은 합계에서 제외.

| plan | disposition | 근거 |
|---|---|---|
| P004 | EXCLUDE | 구현·launcher 없는 실행 전 장기 KDA; 현 51.1h pack보다 준비도 낮음 |
| P005 | EXCLUDE | 구 단계는 후속 승인/프리셋 의존; P005b CLA LR 검증을 먼저 편성 |
| P005b | **INCLUDE READY 10.1h** | COMPASS CLA/KV 1순위; LR 1.0/1.5/2.0×3 seed 실물 SH·preflight 완료 |
| P006 | EXCLUDE | MTP/FastMTP 실행 전·미구현, 현 기준 후보와 직접 의사결정 없음 |
| P007 | EXCLUDE | 공통 val/L4 고갈 선결의 장기 token 축; 현 요청의 300M 이하 규약에서 제외 |
| P009 | EXCLUDE | 민감도 혼합정밀 실행 전·미구현 |
| P010 | EXCLUDE | 하이퍼넷 실행 전·미구현 |
| P011 | EXCLUDE | KD off 현 기본과 충돌하는 저토큰 교사 축; 재개 근거 없음 |
| P013 | EXCLUDE | seq warmup 실행 전; 즉시 의사결정 축 아님 |
| P014D | **INCLUDE GATE 0.1h** | moonshot 비교 후 generic g5 v1 구현; CPU actual-model 1.50× gate만 먼저 |
| P016 | EXCLUDE | 3:4 품질 축은 기존 결과에서 큰 대가; moonshot native는 P014D와 혼합 금지 |
| P018 | EXCLUDE | 결과037에서 압축 교사 핵심 문제 완주; 낡은 계획 상태를 신규 큐로 부활시키지 않음 |
| P019 | EXCLUDE | hidden 오프라인 KD 실행 전·KD off 기본과 우선순위 충돌 |
| P020 | EXCLUDE | ReLU²GLU+3bit KV 복합축 실행 전; 변수 분리 미완 |
| P022 | EXCLUDE | FP8 Ada의 명시 선결 2건 미충족 |
| P022B | EXCLUDE | 기존 dtype 결과 및 P022C 후속과 중복; 현 큐 의사결정자 아님 |
| P022C | EXCLUDE | cache-only 속도·memory·NRMS 계약 음성; 새 format/융합 설계 없이 재실행 금지 |
| P023 | EXCLUDE | Sophia 실행 전; RMS4 기본 확정 후 우선순위 낮음 |
| P024 | EXCLUDE | progressive stacking 실행 전·부모 대조 미완 |
| P025 | EXCLUDE | 고정 2:4 구계획; WSL 후속 P025B가 현 소유자 |
| P025B | **INCLUDE GATE 0.2h** | Wg M8192 graph 후보를 fwd+dgrad+wgrad+pack/accum whole primitive로 재판단 |
| P027 | EXCLUDE | CUDA Graph 구계획; P025B graph 귀속과 중복 |
| P028 | EXCLUDE | 공통 bpb 도구는 P097에서 사용; 한국어 원문 별도 선결 |
| P029 | EXCLUDE | 정성 probe는 P097 prompt panel 인간 판독 선결; GPU 큐로 대체 불가 |
| P030 | EXCLUDE | 과거 CPU 추론 상태 문구가 낡음; P014D/P060B deploy gate가 현 소유 |
| P033 | EXCLUDE | Chinchilla 스케일업 선결 조사·대규모 비용, 300M 큐 범위 밖 |
| P034C | EXCLUDE | RSS/상주 후속은 CPU 별도 게이트; 학습 51.1h에 중복 편성 안 함 |
| P035B | EXCLUDE | A3 결과 G2 불성립, adaptive/freeze 자동 개방 금지 |
| P037 | EXCLUDE | 데이터 파이프라인 남은 항목은 데이터 소유 범위·별도 |
| P040 | EXCLUDE | 타잉 학습속도 AB 구 조건; 현 기준선/옵티마이저와 불일치 |
| P041 | EXCLUDE | 한국어 코퍼스 장기 확장; P097 300M 재현 먼저 |
| P042 | EXCLUDE | KD 교사 추론화 과거 결과 완주; KD off 현 기본 |
| P048 | EXCLUDE | prelude/coda 레버 구 계획; 현 후보군 자 안 |
| P049B | EXCLUDE | P062가 승계·다수 단계 완주; 구 계획 문구 재실행 금지 |
| P050 | EXCLUDE | 부모/KD 분해 핵심 결과 완주; 낡은 ongoing 문구 |
| P050B | EXCLUDE | 부모 계보 선결 3건·미실행, 현 직접 의사결정 없음 |
| P052 | EXCLUDE | seed2024 및 3-seed 결과039 완주; 계획 문구만 낡음 |
| P053 | EXCLUDE | CE/KD chunk 등가성 결과054로 종결 |
| P054 | EXCLUDE | dense 부모 재생성 결과/후속 게이트 조건부, 즉시 READY 아님 |
| P055 | EXCLUDE | KD 원인규명 후 KD off 기본 확정; 추가 alpha 스윕 중복 금지 |
| P056 | EXCLUDE | optimizer-step quant cache 미구현; 속도 판정자 미준비 |
| P057 | EXCLUDE | attention tying 8/16 결과044 완주; 예약 문구만 낡음 |
| P058 | EXCLUDE | eval/save 주기 분리 구현·운영 완료 |
| P059 | EXCLUDE | 외부 기준선 어댑터/라이선스 선결, 51.1h 내 즉시 READY 아님 |
| P060B | **INCLUDE READY 7.8h** | cache decode GQA 신규 게이트 + on/off 300M 3-seed 품질 쌍 |
| P061B | EXCLUDE | 측정 기반 불균등 타잉 실행 전·다중 선결 |
| P062 | EXCLUDE | Stage19 포함 주요 재귀 실험 완주; 재주입은 새 P098이 소유 |
| P063 | EXCLUDE | 분해능 계열 결과049 등 완주; 판정 규칙 문서 축 |
| P065 | EXCLUDE | 결과051에서 B2/no-ckpt/레버 완주; 계획 문구 낡음 |
| P066 | EXCLUDE | 상주 목표 구 단계·배포 별도 판정 |
| P067 | EXCLUDE | 외부 tokenizer/교사 대용량·license·VRAM 선결, 현 큐에서 제외 |
| P068 | EXCLUDE | A1 결과055 완주, A2/A3은 문헌상 위험·저가치; 시간 채우기 구현 금지 |
| P069 | EXCLUDE | 다지표 평가 체계 데이터/하네스 선결 |
| P070 | EXCLUDE | P062 inplace가 uniform보다 +0.0116 악화해 계획 자체가 착수 보류를 지정 |
| P075 | EXCLUDE | 16MiB 예산 개방 선결; 현 토크나이저 변경 큐 금지 |
| P076 | EXCLUDE | Stage2 결과064 완주; attention-only는 별도 플래그/승인 선결 |
| P077 | EXCLUDE | fp16 KV 축 결과065에서 마지막 게이트 완주; 새 품질 gate 미설계 |
| P080 | EXCLUDE | 저밀도 benchmark 데이터 품질/마치게 선결 |
| P081 | EXCLUDE | 싱크가 causal 균등과 미분리·중앙 질량 16~20% 버림; 우선순위 하향 결과070 |
| P082 | EXCLUDE | 외부 Qwen/Gemma evaluator·license·C0 STOP·대규모 GPU cap 선결 |
| P083 | EXCLUDE | LM Studio downstream release 일정/외부 runtime 의존 |
| P086 | EXCLUDE | dense LRM scalar/vector 결과072로 두 차례 종결; tied 재개 조건 미충족 |
| P089 | EXCLUDE | width Stage2b 채택선 미달, Stage3 재승인 전 자동 개방 금지 |
| P090 | EXCLUDE | SFT/계속사전학습은 `datasets/TinyDataset/**` 보호 소유·데이터 승인 범위 밖 |
| P091 | EXCLUDE | actual selector R2/R3·trainer local state 실험설계가 미완; synthetic S 순위 불안정 후 자동 본런 금지 |
| P092 | **INCLUDE READY 15.8h** | Stage1aT 계약 뒤 full trainer·vectorized rewire·state reset 구현, 30M→100M→gate→300M 3seed |
| P093 | EXCLUDE | rank16 output NRMS 0.974 절대 viability 미달; 새 parameterization 없이 GPU 금지 |
| P094 | EXCLUDE | P022C packed/masterless evidence 미충족 HOLD |
| P095 | EXCLUDE | bridge 계약만 PASS; full Transformer shortcut/oracle 실험설계·batch memory 경로 미완 |
| P096 | EXCLUDE | 보호 실문항·팀 의미검토 선결, 자동 편성 금지 |
| P097 | **INCLUDE READY 6.0h** | Stage2Wb의 control bpb vs FineWeb2 YNAT/ARC 교환을 두 추가 seed로만 재판단 |
| P098 | **INCLUDE READY 11.1h** | COMPASS 재귀 1순위 선결인 embedding 덧셈판 구현, on/off 3-seed |

## 편성 판독

- READY는 50.8h를 전부 편성했다. P092 Stage3는 내부 100M gate 음성 시 exit8로 종료하므로
  51.1h는 **최대 실행 시간**이지 게이트 실패를 무시한 연속 강제가 아니다.
- P014D/P025B 0.3h는 GATED이며 정합/속도 문턱을 넘지 못하면 해당 축 후속을 열지 않는다.
- 실행이 아닌 정적 선결만 통과했으므로 모든 신규 품질·GPU 주장은 `NOT_RUN`이다.
