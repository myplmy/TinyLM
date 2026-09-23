# 2026-09-24 완료·취소 실험 SH 재현성과 삭제 감사

- **대상**: root `run_*-done.sh` 14건과 `run_P092_Stage3W_full_trainer_300M_seeds-cancel.sh` 1건. 원본 SH·로그·체크포인트는 수정·삭제하지 않았다.
- **쓰기 증거**: 기존 [append_repro.py](../../scripts/append_repro.py) dry-run은 결손13/기존1, 단위 fixture PASS였다. 사용자 지시에 따라 `--apply`로 [083](../../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md), [090](../../test_result/090_20260919_P097-세-cache는-완성됐지만-학습은-0step이다.md), [091](../../test_result/091_20260923_P098-R2-초기임베딩-재주입은-3시드-실무-동급.md)의 **맨 아래에 13개 launcher별 부록**을 추가했다. 재실행 dry-run은 추가0/건너뜀14, `git diff --numstat`은 세 결과문서에서 각각 +28/+44/+79줄·삭제0이다.
- **판정 계약**: ① 사용자 완료·`-done` 역사, ② 해당 결과문서의 명령 문자열 일치, ③ 똑같은 SH의 재실행 예정 없음. `sync_experiments_tsv.py`는 ①②만 검사하고 종료코드0은 삭제 승인 뜻이 아니다. 다음 표의 ③은 각 계획의 현재 후속을 사람 판독했다.

| 군 | SH 수 | ①② 재검사 | ③ 정확한 재실행 | 삭제 처분 |
|---|---:|---|---|---|
| P014D Stage1Wc | 1 | 3/3 명령, [069](../../test_result/069_20260902_P014D-디코드-프로파일이-경로이름을-양자화형식으로-넘겨-두-팔-다-죽었다.md)에 기존 보존 | 같은 scalar v1 재실행 계획 없음; 후속 SIMD/ABI는 새 단계 | **추가 링크 선결 HOLD**: [직전 핸드오프](../202609232309_HANDOFF.md)의 Markdown 링크가 해당 SH를 직접 가리킴 |
| P092 Stage1W/Stage2W | 2 | 4/4+4/4을 결과083에 추가 | Stage3Wb는 기존 checkpoint 진단이지 30M/100M 같은 SH 재실행이 아님 | **조건 충족 삭제 후보 2** |
| P097 Stage3a~dW | 4 | 각 1/1을 결과090에 추가 | Stage4W는 여섯 기존 checkpoint의 공통평가; 같은 4개 학습 SH 재실행 예정 없음 | **조건 충족 삭제 후보 4**; Stage4 결과 전까지 사용자 보존 선택도 합리적 |
| P098 Stage1a~fW·Stage2W | 7 | 학습6/6·paired eval3/3을 결과091에 추가 | 3시드 단순 덧셈판은 미승격, 동일 SH의 예정 재실행 없음 | **조건 충족 삭제 후보 7** |
| **합계** | **14** | **14/14 문자열 보존** | 정확한 재실행 예약 0 | **즉시 링크정합 후보13 / 링크 정리 선결1**; 실제 삭제0 |

완료 14개 파일 크기의 합은 **16,565 bytes**다. 삭제 자체는 디스크 용량 확보 수단으로 거의 무의미하다. 후보13도 **사용자 파일별 승인 전에는 삭제하지 않는다**. P014D 1개는 삭제 승인뿐 아니라 과거 핸드오프 링크를 어떻게 보존할지 별도 문서 결정이 필요하다. 결과문서의 추출 부록은 원 명령을 보존하지만 `$python_bin` 정의·repository cwd·코드/캐시 버전·runlog wrapper까지 하나의 독립 실행 파일로 재현하는 것은 아니다. 삭제를 선택해도 해당 조건은 결과·계획·Git 이력에서 함께 확인해야 한다.

### 사용자 승인 시 검토할 정확한 13개 파일

- `run_P092_Stage1W_full_trainer_30M-done.sh`
- `run_P092_Stage2W_full_trainer_100M-done.sh`
- `run_P097_Stage3aW_ctrl_v2_s2024-done.sh`
- `run_P097_Stage3bW_fineweb2_s2024-done.sh`
- `run_P097_Stage3cW_ctrl_v2_s31415-done.sh`
- `run_P097_Stage3dW_fineweb2_s31415-done.sh`
- `run_P098_Stage1aW_r2_ctrl_s1337-done.sh`
- `run_P098_Stage1bW_r2_reinject_s1337-done.sh`
- `run_P098_Stage1cW_r2_ctrl_s2024-done.sh`
- `run_P098_Stage1dW_r2_reinject_s2024-done.sh`
- `run_P098_Stage1eW_r2_ctrl_s31415-done.sh`
- `run_P098_Stage1fW_r2_reinject_s31415-done.sh`
- `run_P098_Stage2W_r2_reinject_pair-done.sh`

위 13개는 **삭제 승인 목록이 아니라 후보 목록**이다. 삭제할 정확한 파일명을 사용자가 선택해야 하며, 원본 로그·체크포인트 삭제 권한까지 확장되지 않는다.

## 취소 SH 별도 판정

[구 P092 Stage3W 300M×3시드 취소본](../../run_P092_Stage3W_full_trainer_300M_seeds-cancel.sh)은 **실행 완료가 아니라 gate 실패로 열리지 않은 옛 설계**다. 8,899 bytes이고 12개 300M 학습 호출과 선행 gate가 이 SH에만 정확히 남는다. [P092 계획](../../test_plan/P092_Dynamic-Sparse-Training-연결희소성.md)과 [결과083](../../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md), 직전 핸드오프가 이 파일로 직접 링크한다. 지금 삭제하면 원안 명령과 링크가 함께 사라진다. **삭제 부적합·보존 권장**. 훗날 제거하려면 미실행 설계 원문을 다른 보존 위치에 옮기고 역참조를 조정한 뒤 사용자 별도 승인이 필요하다. Stage3Wb 연구축은 계속된다.

## 왜 13개 명령이 빠졌나 — 확인된 두 시점

1. `ea363b3` 결과 회수 커밋은 14개 원본 로그의 결과 closure와 14개 `-done` 개명을 함께 기록했지만, 기존 `append_repro.py --apply`를 호출하지 않았다. [closure 검사](../../scripts/check_result_closure.py)는 **raw-log basename↔결과문서 절**만 확인하고 SH 명령은 확인하지 않는다. [sync 검사](../../scripts/sync_experiments_tsv.py)는 누락을 `[보류]`로 인쇄하지만 종료코드0인 **보고 전용**이므로 종합 정적 PASS가 이 부채를 막지 못했다. 이는 런처 파서 부재가 아니라 결과 문서화 절차의 누락이다.
2. `c4a05b7` 후속 작업에서는 읽기 전용 삭제 감사를 하여 1후보/13보류를 **보고했다**. 그 요청은 삭제 가능성 확인이지 결과문서 개정 승인으로 취급하지 않아 자동 보완을 하지 않았다. 이는 그 시점의 권한 경계였지만, 앞선 결과 회수 때 재현 부록을 함께 남기지 않은 결함을 해소하지는 못했다.

**재발방지 권고(미구현):** 로그 closure PASS와 `-done` 개명 사이에 exact launcher→해당 결과문서 명령 검사를 **별도 실패 gate**로 둔다. 현재 `sync`의 종료코드0·전역 결과 corpus 검색만으로 완료 판단하지 말고, 각 SH를 해당 결과문서로 매핑해 ①②를 검사한다. ③재실행 계획과 링크 역참조는 사람이 판정한다. 검사기 구현은 이번 사용자의 제안서 검토·문서 보완 범위 밖이므로 `DESIGNED / NOT_RUN`이며 승인 없이 작업흐름 코드를 바꾸지 않았다.

## 범위 밖 잔여

`sync_experiments_tsv.py`는 과거 TSV 고아행 16건을 계속 보고한다. 이번 지시는 SH 재현·삭제 판정이므로 `--apply`로 TSV를 옮기지 않았다. 보호 `datasets/TinyDataset/**`, GPU·모델·queue·smoke, 체크포인트·원본 로그 변경, 실제 SH 삭제, staging·commit·push는 모두 0건이다.
