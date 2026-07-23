# TinyLM 방법론 원장 (living document)

이 문서는 TinyLM에 **제안·적용된 모든 기법**을 분류별로 추적한다. 개선·제안이
추가될 때마다 갱신한다. 분류별 상세는 [`methods/`](methods/) 하위 파일 참조.

## 분류

| # | 분류 | 파일 |
|---|---|---|
| 1 | 아키텍처 구조 | [methods/01_architecture.md](methods/01_architecture.md) |
| 2 | 메모리 감축 | [methods/02_memory.md](methods/02_memory.md) |
| 3 | 지식 품질 향상 | [methods/03_knowledge_quality.md](methods/03_knowledge_quality.md) |
| 4 | 컨텍스트 길이 | [methods/04_context_length.md](methods/04_context_length.md) |
| 5 | 학습 속도 | [methods/05_training_speed.md](methods/05_training_speed.md) |
| 6 | 학습 품질·안정 | [methods/06_training_quality.md](methods/06_training_quality.md) |

## 상태 범례

- ✅ **적용**: 코드에 반영되어 기본/상시 동작
- 🧪 **실험옵션**: 코드에 있으나 플래그/프리셋로 켜는 것
- 💡 **제안**: 아직 미구현, 검토·제안 단계
- 🔜 **로드맵**: 확장(1.7B/배포) 단계에서 예정
- 🚫 **폐기**: 측정·검토 후 제외

## 버전 개요

- **v4** — 단일파일 아키텍처. 측정 기반 설계 확정(prelude/coda, 어텐션 독립, MLP 타잉,
  CLA2, factorized embedding, g128 삼진). 300M 실전에서 NaN 발산.
- **v5** — 학습 발산 해결(QK-norm, NaN 가드, compile 안전 어닐, LR 재조정).
- **v6** — `tinylm/` 패키지 모듈화 + 효율/실험 기능(EMA·WSD·베스트ckpt·조기종료·
  스케일별 체크포인트 이름·자동 LR 탐색·KD·부모초기화·ternary-LoRA·FiLM·깊은 프리셋·
  reduce-overhead·TF32·HF 리다이렉트·크기별 데이터 캐시).

## 현재까지의 핵심 측정치 (m100, ko-en 300M, lr 1e-3)

- dense 기준선: 최종 val **3.8241**, best **3.7797** (132.5M, 30.9MB).
- tied 기준선: 최종 val **3.9452** (72.9M, 17.1MB, 감축 **1.82×**).
- **손실 격차 +0.1178** — 단, 300M은 크게 undertrained(파라미터당 ~4토큰 vs Chinchilla ~20)
  이라 수렴 격차의 과대추정일 가능성. 격차 축소 실험 진행 중(KD·부모초기화·ternary-LoRA·FiLM).

## 갱신 규칙

새 기법을 추가/적용하면: 해당 분류 파일의 표에 **행 추가**(기법·상태·버전·작동원리·
트레이드오프·특기) 하고, 상태/버전을 갱신한다. 측정 결과가 나오면 특기란에 수치를 남긴다.
