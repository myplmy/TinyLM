# 2026-09-23 체크포인트 전수 재판정 — 삭제는 사용자 실행 전까지 0건

- 범위: `runs/ckpt/*.pt` 파일명·크기와 `checkpoints.tsv`, `runs/logs/*.json` 부모/교사 참조, 현재 실험 SH·진단기의 입력 계약만 조사했다. 모델·GPU·체크포인트 본문은 로드하지 않았다.
- 판정 정본: [checkpoints.tsv](../../checkpoints.tsv), SHA-256 `84a1d52ba38526bca30ba7cd3a0442f9f4eda4ce9562749b49f8fc6234745a7d`. 이 지문은 본 감사 시점의 값이며 이후 TSV 수정 시 다시 계산한다.
- **관측**: 실물 359건·229.189 GiB. TSV 571행 중 실물 359건·역사적으로 이미 없는 212건. 미등록 실물 0, symlink 0, 현재 log JSON 파싱 오류 0.
- **사용자 실행 전 후보**: `delete` 실물 142건·60.677 GiB, `keep` 실물 217건·168.512 GiB, 실물 `hold` 0건. 이것은 잠재 회수량이지 삭제 결과가 아니다.

## 1. 왜 기존 2.74 GiB가 작았나

기존 TSV의 실물 `delete`는 62건·2.737 GiB였고, 새 108건·76.813 GiB는 모두 미등록이었다. 최초 감사기는 `steps<500`을 일괄 delete로 보아 P092 Stage1W 30M(229 step) **품질 게이트**를 잘못 지울 뻔했다. [ckpt_audit.py](../../scripts/ckpt_audit.py)를 정확한 `tiny_synthetic_*_sm_*` 재생성 산출물만 자동 delete, 그 밖은 기본 hold로 교정하고 새 108건을 등록한 다음, 사용자의 직접 검수 지시로 실물 hold 131건을 재판정했다.

| 직접 재판정한 그룹 | 건수 | 예상 회수 GiB | 근거와 보존한 것 |
|---|---:|---:|---|
| 비보호 `_best` | 56 | 40.508 | 모든 final 짝 실존, 현재 런처·평가기 exact 참조 0, 부모/교사 파생보호 0. final 45건은 `keep`으로 올려 G2 본체/형제 정합 유지 |
| 완료 단기·열세 final | 9 | 6.046 | P060B Stage1W 250-step 2건은 paired 도구가 JSON만 읽음; P035B A3 250-step 3건은 G2 부정·A4 미개방; P005b CLA2 LR2.0 세 seed 3건 열세; P076 norm_mean 1건 열세. 해당 JSON·결과·대조 final 보존 |
| 완료 역사 대조 final | 15 | 11.385 | 초기 REVIEW1/타잉·KD/300·600M pool 계열. 각 짝 JSON 실존, 현재 WSL 런처·기본 진단·부모 참조 0. 현재 기본 진단에서 쓰는 `mC_g8_k4`는 제외·keep |
| 기존 실물 delete | 62 | 2.737 | 이번에 새로 승격한 대상 아님. 기존 TSV verdict와 파생보호 재대조 후 현시점 blocker 0 |
| **합계** | **142** | **60.677** | `checkpoints.tsv`가 정확한 파일명·판정·행별 이유의 유일한 정본 |

**보호 예외**: `denseb`와 `denseb_best`는 부모 계보 정규식, `dense2_best`는 실제 `init_from_src`, 폭 실험 `w512_d20_parent`와 best 형제는 실제 자식 참조 때문에 keep이다. `mC_g8_k4`는 `bench_infer`, `mem_runtime`, `paired_eval`, `diag_kvcache`의 기본 모델이라 keep이다. 새 P092 Stage3Wb는 100M **final**을 읽으므로 그 final을 keep하고 best만 후보로 두었다. P097 Stage4W·P100은 P097 final을 읽는다. 삭제 후보와 현재 보호 집합의 교집합 0건, hold 본체/delete-best G2 충돌 0건이다.

이 판정은 현 계획·현재 런처 기준이다. 미래 실험에서 삭제 후보를 부모/교사로 다시 쓰려면 사용자 cleanup 전에 TSV를 keep으로 바꾸고 동일 감사를 재실행한다. 원본 JSON·문서만으로 체크포인트 자체를 복원할 수는 없다.

## 2. WSL 사용자 정리 실행기 검토와 보완

[run_cleanup_checkpoints.sh](../../run_cleanup_checkpoints.sh)의 종전 두 프로세스 흐름은 dry-run 뒤 `cleanup_ckpt.py --yes`가 목록을 새로 계산하므로 미리 본 적 없는 새 파일이 삭제 대상에 들어갈 수 있었다. 사용자 승인으로 WSL SH를 단일 `--interactive` 프로세스로 바꿨다. [cleanup_ckpt.py](../../scripts/cleanup_ckpt.py)는 화면에 표시한 각 후보의 정규 파일 여부·device/inode·크기·mtime/ctime과 TSV bytes를 고정한다. 정확한 대문자 `YES` 전에는 삭제하지 않고, YES 직전 TSV/부모참조/모든 파일을 재검증해 하나라도 달라지면 삭제 0건으로 중단한다. unlink 직전에도 대상별 identity를 재확인한다.

합성 fixture는 취소, 파일 교체, TSV 변경, 새 부모 참조가 각각 삭제 호출 0건임을 검증했고, unchanged mock에서 정확한 한 파일만 unlink 호출 대상으로 잡혔다. Bash 구문은 PASS. **실제 사용자 파일 삭제 E2E는 NOT_RUN**이며, 완전한 동시 writer 방지는 협조 없는 파일시스템에서 보장하지 못하므로 실행 전 모든 학습·체크포인트 writer가 멈춘 상태여야 한다. 과거 Windows BAT와 직접 `cleanup_ckpt.py --yes`는 이번 단일 프로세스 보호로 이관하지 않았다. 현재 WSL에서는 오직 `./run_cleanup_checkpoints.sh`를 사용한다.

사용자는 실행 전 프리뷰에서 142건·약 60.7 GiB를 다시 확인하고, 예상과 다르면 YES를 입력하지 않는다. 이번 AI 작업에서 cleanup·삭제·GPU·모델 로딩·staging·commit·push는 모두 0건이다.
