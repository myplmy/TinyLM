# Moonshot 코드 격리 경계

이 패키지는 `moonshot` 브랜치의 실험 알고리즘을 PM 번호별 모듈로 격리한다. branch를
`main`에 병합하는 용도가 아니다. 충분한 성능 증거가 생긴 경우에만 사용자가 별도 main
작업에서 아래 manifest를 검토해 필요한 변경을 선택 이식한다.

## PM000 Latin GQA 이식 manifest

알고리즘 정본은 [`pm000_latin_gqa.py`](pm000_latin_gqa.py) 한 파일이다. torch를 import하지
않으며 schedule, validation, 실제 layer visit counter, K/V shift 선택을 소유한다.

공통 코드의 integration hook은 다음으로 제한한다.

| 파일 | hook | 제거/이식 경계 |
|---|---|---|
| `tinylm/config.py` | 필드 2개, 정본 import, validation 호출 | 두 필드와 호출 제거 |
| `tinylm/cli.py` | train CLI 플래그 2개 전달 | parser/kwargs 제거 |
| `tinylm/train/trainer.py` | config 적용, 방어 검증, JSON 3필드 | PM 블록 제거 |
| `tinylm/model/transformer.py` | 실제 layer visit별 `pass_id` 전달 | counter와 인자 제거 |
| `tinylm/model/modules.py` | attention 소비 직전 비파괴 rotation | order와 rotation hook 제거 |

진단·계측·배치 인프라는 `scripts/diag_pm000_latin_gqa.py`,
`scripts/check_moonshot_namespace.py`, `scripts/check_smoke.py`, `scripts/batch/tool_smoke.bat`,
`scripts/runlog.py`, `scripts/dryrun_batch.py`, `scripts/lint_bat.py`, `moonshot_batch/`, `plan/`,
`moonshot_result/`에 있다. 이들은 제품 경로와 별도의 검증 자산이다. 공통 smoke의 PM arm도
`_pm000__` tag를 사용하고 `runlog.py`가 일반 registry에서 제외한다.

## 호환성 계약

- 기본값 `fixed`는 runtime order가 `None`이어서 rotation helper를 호출하지 않는다.
- 새 학습 파라미터와 state-dict key는 없다.
- checkpoint의 두 config 필드는 보존되며, 필드가 없는 구 checkpoint는 `getattr(..., fixed/0)`
  경로로 기존 동작을 유지한다.
- 알고리즘 또는 hook을 바꾸면 기존 Stage0 로그를 재사용하지 않고 새 stage 이름으로 사용자
  동적 검증을 다시 수행한다.
- 2026-09-06 08:52의 첫 smoke는 tag 격리 보강 전 `sm_gqapass`로 실행된 역사적 증거다.
  그 로컬 일반-registry 행을 이 작업에서 삭제하지 않았으며, 이후 실행부터 위 계약을 적용한다.
