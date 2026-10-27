# 문맥 일정 및 MNTP 읽기 검토 위임의 사후 기록

- 기록 시각: 2026-10-27 12:38 KST. `file_receipt_recorded_after_dispatch=true`.
- 현재 사용자 96/97의 독립 미완료 연구 및 과거 문헌·정·반 역할 허용을 따른다. 총괄이 호출 메시지에 읽기 범위와 금지를 먼저 썼지만, 일부 후속 호출 전에 이 연결 문서를 작성하지 않았다. 사전 문서화 준수로 소급하지 않는다.
- 공통 요청 모델/추론: `gpt-6.1-sol` / `max`. 기존 에이전트를 후속 호출했으며 실제 공급자 모델을 이번에 다시 검증한 것은 아니다.
- 공통 허용: 아래의 지정 파일 텍스트와 공개 일차 문헌을 읽고 메시지로만 의견을 반환한다. `rg/sed/cat` 등 파일 읽기는 허용한다.
- 공통 금지: 파일 생성·편집, 구현·시험·Python 실행, 모델·GPU·체크포인트·학습자료·정제 담당 전용 경로 접근, 설치·다운로드·Git·삭제 및 하위 에이전트 호출. 총괄의 실행·편집 권한을 위임하지 않는다.

| 기존 에이전트 | 역할 | 이번 후속 읽기 범위 | 회수한 의견 |
|---|---|---|---|
| `literature_oct27_adamuon` | 문헌·아이디어 | GPT-BERT 논문 `2410.24159v2`, 저자 `ltgoslo/gpt-bert`의 고정 commit `9fc15074d5e2620ea4ad0871d57454c0f35e3ff0` 내 dataset/model_extra/train_multi_gpu 텍스트 | MNTP shift·문서 마스크·치환 비율·목적함수와 단일 GPU 이식 차이 |
| `thesis_oct27_adamuon` | 정 검토 | `tinylm/train/context_curriculum.py`, `scripts/diag_p013_context_curriculum.py`, 대응 두 test, `tinylm/model/transformer.py`, `modules.py`, `docs/research/20261027_문맥일정과_MNTP_접점.md` | 문맥 일정의 위치 보존·정규화 및 명시적 attention 마스크 연결의 타당성 |
| `antithesis_oct27_resources` | 반 검토 | 같은 문맥 일정/모델 소스·시험·설계 및 기존 `tinylm/data/loader.py`의 텍스트 | 가변 버퍼 복사·부분 실패·시간 상한·CLA/checkpoint/마스크 누설 반례 |

- 회수 보고는 모두 읽기 전용이며 보조 구현·시험·모델 실행을 맡기지 않았다. OS 수준 격리를 검증했다는 뜻은 아니다.
- P013 실제 실행 소스는 `p013_context_archive_v2.json`의 고정 33개 파일이며, 실행 중 총괄도 이를 편집하지 않는다. 이후 MNTP 코어 변경은 P013 실제 종료 회수 뒤 별도 소스·설계·회귀·스모크로 검증한다.
- 이후 새 호출은 역할·정확 경로·금지 행위·산출물·동결 소스가 적힌 문서를 먼저 저장하고 그 경로와 함께 전달한다. 현재 문서는 과거 누락을 치유했다는 증거가 아니라 누락 및 회수 범위의 기록이다.
