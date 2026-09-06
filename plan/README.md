# Moonshot 전용 계획 네임스페이스

이 폴더는 `moonshot` 브랜치에서만 사용하는 고위험·고불확실성 실험 계획을 담는다.
일반 실험의 `test_plan/`, `test_result/`, `experiments.tsv`와는 연결하지 않는다.

## 고정 규약

| 산출물 | 규약 |
|---|---|
| 계획 번호 | `PMnnn` |
| 계획서 | `plan/PMnnn__MOONSHOT__주제__PLAN.md` |
| 실행 배치 | `moonshot_batch/run_PMnnn__MOONSHOT__StageX_주제.bat` |
| 실행 로그 | `moonshot_result/*_PMnnn__MOONSHOT__StageX_*` |
| 결과 분석 | `moonshot_result/PMnnn__MOONSHOT__주제__RESULT.md` |
| 체크포인트 태그 | 주제/아키텍처 접두사 뒤에 `_pmnnn__...` |

`__MOONSHOT__`과 이중 밑줄 `__`은 일반 실험과 섞이지 않게 하는 예약 구분자다.
PM 산출물을 일반 실험 폴더나 일반 큐에 등재하지 않는다.

## 브랜치 경계

- 이 브랜치에서 `main`으로 merge, rebase, cherry-pick, push를 시도하지 않는다.
- 검증된 방법을 일반 작업으로 옮기는 결정과 이식은 사용자가 별도 main 작업에서 한다.
- PM 배치는 `scripts/check_moonshot_namespace.py`가 현재 브랜치와 경로를 확인한 뒤에만 진행한다.
- AI는 `.bat`, 학습, 모델 로딩, torch 진단을 실행하지 않는다. 사용자가 배치를 실행한다.
- AI가 수행하는 검증은 torch를 import하지 않는 정적 검사에 한정한다.

현재 계획:

- [PM000 Latin GQA](./PM000__MOONSHOT__LATIN_GQA__PLAN.md)
- [PM001 Triton 계약·3:4 CPU LUT](./PM001__MOONSHOT__TERNARY_TRITON_AND_SPARSE34_CPU_LUT__PLAN.md)

PM000의 Stage0·Stage0B와 `fdce364` 기준 sparse34 재스모크는 사용자 실행에서 PASS했다.
PM001 이후 변경은 그 과거 로그가 검증하지 않으며 PM001 전용 Stage0/1/2를 새로 실행해야 한다.
