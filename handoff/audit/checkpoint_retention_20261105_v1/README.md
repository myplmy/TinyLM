# 사용자110 체크포인트·optimizer 한정 정리 결과

2026-11-05 사용자가 승인한184개 모델의 optimizer 제거와 격리 스모크128개 삭제를
총괄 Codex가 CPU로 수행했다. 연구목표109는 사용자 요청으로 paused이며 재개하지 않았다.
GPU·모델 구조 생성·순전파·학습·설치·다운로드·Git 변경은 하지 않았다.

## 실제 수행과 공간

| 항목 | 수행 전 | 수행 후 |
|---|---:|---:|
| 일반 연구·부모 모델 파일 | 364개 | 364개 |
| 일반 모델 논리 크기 | 237188938102B /220.8994GiB | 146889371648B /136.8014GiB |
| optimizer가 있는 일반 모델 | 223개 | 보호39개 |
| optimizer 없는 일반 모델 | 141개 | 325개 |
| 지정 스모크 체크포인트 | 128개 | 0개 |
| WSL 가용 공간·작업자 실측 | 437.4424GiB | 527.1770GiB |
| Windows Z 가용·같은 작업자 구간 | 4.37274GiB | 4.37274GiB |

대상 파일의 논리 감소는96350165210B, 할당 감소는96350527488B로89.73342GiB다.
이는 WSL 파일시스템에서의 정리다. Z의 물리 공간 반환은 관측되지 않았으며 WSL 종료,
VHDX 축소/trim 등 시스템 작업은 이번 범위에서 수행하지 않았다. 앞선 타 작업의 공간
변화를 이 정리의 성과에 더하지 않았다.

## 모델 보존 방식과 검증

184개는 원래 파일명을 유지했다. 새 체크포인트를 별도로 직렬화하고 검증한 뒤 원래
체크포인트 경로로 원자 교체했다. 제거한 root 필드는 opt와 opt_muon뿐이다.
model/cfg/step/tokenizer·보조 헤드 등 나머지 필드와 Tensor의 raw storage 비트,
dtype·shape·stride·offset·공유 storage 관계를 전후 지문으로 검증했다.
CPU map_location으로 읽고 저장하므로 저장 장치 태그는 CPU 아카이브 형식이다.
가중치 정밀도 변환·양자화·추가 학습은 없으며 optimizer를 새로 만드는 후속 학습의
초기값 또는 추론/비교용으로 보존한다. 제거한 optimizer로 정확 resume할 수는 없다.

각 모델의 원래 파일 SHA와 새 파일 SHA, 보존 지문·제거 필드·전후 identity는
[models/](models/)의184개 기록이 소유한다. 원로그·옛 결과 보고서의 역사 SHA를 고치지 않았다.
checkpoints.tsv는 해당184개 행의 실제 MiB와 old/new SHA 이력을 갱신하고 keep을 유지했다.
그 밖의 운영 행548개는 그대로다. 전체 파일 스냅샷은 CHECKPOINTS_BEFORE.tsv와
CHECKPOINTS_AFTER.tsv에 보존했다.

## 보호와 삭제 경계

실제 unlink는 승인된 두 성공 스모크 세션의 .pt128경로에만 적용했다.
그 두 세션의 dense/final·best4개와 실패 세션66개는 유지했다.
일반 CP180개·격리 CP70개·P107 상태100파일·관련 원로그/보고서295개, 합계645개는
전후 SHA와 inode/크기/mtime/ctime이 일치했다. 일반 보호39개·가중치 전용141개,
명시 보존 연구9개, P107 두49조각 상태가 포함된다. 체크포인트 외 삭제는0이다.
다른 세션 정제 전용 자료·코드·캐시·프로세스와 보호 TinyDataset은 접근하지 않았다.

## 근거와 검사

- 사용자 원문과 정확한184/128 범위: APPROVED_SCOPE_v1.json.
- 동결 계획: PLAN_v1.json, SHA93160F6728E7478CC1A77C9D55671D44A754CA0A15C74C62EC5008EF8C9E0F7E.
- 모델별 사전 검증 후 교체·스모크 삭제 의도/실행: JOURNAL_v1.jsonl.
- 실제 작업자 종료0: APPLY_v1.log 및 RECEIPT_v1.json.
- 새 프로세스 재검산 종료0: ROOT_READBACK_v1.log 및 ROOT_READBACK_v1.json.
- CPU 계약13개 통과: CPU_TEST_v3.log. Tensor 변화·alias 손실·보조 필드/dtype 변화·
  손상 stage 거부와 비승인 경로/필드 거부를 포함한다.
- 최초 CPU11개 중 protocol2 bytes metadata 지원 누락1건을 실제 변경 전에 발견했다.
  임의 global을 허용하지 않고 latin1 bytes만 제한 지원하여12개, root OrderedDict 보존을
  보강해13개를 통과했다. CPU_TEST_v1/v2 원로그도 남겼다.
- WIP 공식 API 호출과 공개 조정 메모 쓰기를 한 shell 입력에 묶은 마감 명령은
  직접 WIP 쓰기 guard가 사전 차단했다. 실제 실행0이며 두 쓰기를 분리해
  wip.py --done110·capsule-check를 통과했다. guard나 권한 범위를 넓히지 않았다.
- 소유 범위 사전 정적359입력은6PASS/0오류/71NOT_RUN이다. 전역77종 또는 GPU 스모크
  PASS로 해석하지 않는다. 이번에는 GPU 스모크나 모델 품질 평가를 실행하지 않았다.

새 생성된 감사 기록은 파일별20MB 미만으로 유지한다. 폴더·원로그·보고서·데이터·캐시를
정리 대상으로 확장하지 않았다. 커밋/staging/push/PR은 이번 승인에 없어 수행하지 않았다.
