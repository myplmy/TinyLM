# 실험계획 P008 (C1) — 점진적 타잉 (untied→tied, LoRA 스케일 어닐)

## 목적
KD 없이(또는 KD와 결합) 격차를 줄인다. 배포 메모리는 그대로(LoRA가 0으로 사라짐).
"제약 점진 부과"(삼진 어닐과 동일 원리): 초반엔 층별 특화(≈untied) → 종료 시 완전 타잉.

## 방법
- 기존 ternary-LoRA를 켜되, **LoRA 출력 스케일 s(t) 를 학습 중 1→0 으로 어닐**(예: 코사인, 60% 지점 0).
- 종료 시 s=0 → LoRA 무효 → **순수 타잉**(1.82× 유지). dense 교사 없이도 격차 축소 기대.

## 선결(구현)
- LoRA forward에 스케일 곱(현재 없음) + 버퍼 스케줄(set_anneal 방식). config `lora_decay` + trainer가 매 스텝 설정.

## 조건 (m100, ko-en 300M, lr 1e-3, --no-ckpt)
| tag | 옵션 |
|---|---|
| t_prog | --lora-rank 32 --lora-decay (KD 없음) |
| t_prog_kd | 위 + --init-from --kd |

## 비교
- 기존 t_base(+0.1317), t_lora32(+0.0979, 고정 LoRA), t_kdinit(+0.0012)와 대조.
- 목표: (a) **KD 없이** 고정 LoRA보다 격차↓(어닐이 특화→통합을 부드럽게), (b) KD 결합 시 추가 이득 여부.

## 판정
- 격차(vs dense 3.8241), 메모리(LoRA=0이라 1.82×). |g|max 감시(LoRA는 |g| 상승 경향).

## 근거
- Dynamic Layer Tying(2401.12819), share-then-unshare(2110.03848). 삼진 어닐과 동형.
