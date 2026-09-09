# TinyLM 보고서 v2 후속 조치 패키지

**A01–A15를 개별 폴더로 구성했다.** 코드가 필요한 12개 조치에는 수정안, 바로 복사할 전체 파일, 회귀 테스트를 넣었다. A07·A12·A14에는 실험개선안 문서만 작성했다. 여러 조치를 함께 적용할 수 있는 [ALL 통합본](ALL/README.md)도 제공한다.

상태는 **코드 작성 완료·실행 미검증**이다. 원본 프로젝트에 적용하거나 Python 실행, import, compile, 정적 검사 프로그램, 테스트, 학습, 평가를 수행하지 않았다. 파일의 본문 읽기·작성·복사·목록 및 SHA-256 대조만 수행했다. 기존 v1/v2 보고서는 그대로 보존했다.

## 1. 어디부터 볼 것인가

| 폴더 | 우선순위 | 지금 필요한 조치 | 적용 파일 / 원본 사본 수 |
|---|---|---|---:|
| [A01](A01/README.md) | P0 | held-out 버전·schema·cache 고정 | 9 / 2 |
| [A02](A02/README.md) | P0 | 오염 scan/합집합 제외, 정확한 bpb | 11 / 1 |
| [A03](A03/README.md) | P0 | 문항 ID·margin·로컬/HF 점수 규약 | 10 / 2 |
| [A04](A04/README.md) | P0 | paired 통계·family bootstrap | 6 / 0 |
| [A05](A05/README.md) | P0 | Fresh SFT 계측·mask·학습·생성 채점 | 15 / 2 |
| [A06](A06/README.md) | P0 | 같은 배포 모델의 품질·KV·메모리·속도 | 15 / 4 |
| [A07](A07/README.md) | P1 | 고유량·언어 혼합·노출/step 재분석 | 문서만 |
| [A08](A08/README.md) | P1 | matrix WD 대조·실제 optimizer update 계측 | 7 / 2 |
| [A09](A09/README.md) | P1 | 실제 WD와 적용 LR history의 LRM 진단 | 8 / 2 |
| [A10](A10/README.md) | P1 | causal null에 맞춘 attention sink 진단 | 6 / 1 |
| [A11](A11/README.md) | P1 | 정본 그룹과 실제 dense MLP 집약 진단 | 6 / 1 |
| [A12](A12/README.md) | 조건부 | residual 차단과 KV 공급자 삭제의 인과 분리 | 문서만 |
| [A13](A13/README.md) | P1 | 검증된 교사 응답과 같은 ID의 N_REF 대조 | 18 / 2 |
| [A14](A14/README.md) | 조건부 | 기존 폭·깊이·재귀 결과의 비교 완성 | 문서만 |
| [A15](A15/README.md) | 조건부 | 새 학습 경로의 CE·gradient·update 등가성 | 8 / 1 |

파일 수는 각 조치의 필요한 공통 파일까지 포함한다. 조치 사이에 같은 파일이 반복될 수 있다. 통합본의 고유 Python 파일은 **48개 = 기존 파일 교체 13개 + 신규 파일 35개**다. 신규 파일에는 테스트 11개 모듈과 fixture 1개가 포함된다. 테스트 메서드 44개는 **작성 수**이며 통과 수가 아니다.

각 README는 보고서의 지적 → 수정 방법 → 사용자가 실행할 명령 → 인수 기준 → 남는 실험을 연결한다. 이미 정상 완료된 full 학습·paired 실험을 전량 다시 수행하는 계획이 아니다.

## 2. 디렉터리 구조와 복사 방법

```text
20260909_report/
  README.md                       ← 이 안내
  manifest.json                   ← 원본/교체본 해시, 조치별 파일 목록
  CHECK_PACKAGE.ps1               ← 사용자가 실행할 읽기 전용 파일 검사
  VERIFICATION.md                 ← 이번 작업의 실제 확인 범위
  A01/
    README.md                     ← 수정안과 실험 순서
    replacement/
      scripts/...
      tinylm/...
      tests/report_20260909/...
    original/                     ← 교체 대상의 원본 사본만
      scripts/...
  ...
  A07/README.md                   ← 개선안만, 코드 없음
  A12/README.md
  A14/README.md
  ALL/
    README.md
    replacement/                  ← 고유 적용 파일 48개
    original/                     ← 원본 사본 13개
```

1. 개별 적용은 해당 `Axx/README.md`를 읽고 **`Axx/replacement/` 안의 내용**을 프로젝트 루트 `Z:\TinyLM\`에 병합 복사한다.
2. 전체 적용은 **`ALL/replacement/` 안의 내용**을 같은 위치에 한 번 복사한다. 통합본과 개별본의 겹치는 파일은 바이트 단위로 같다.
3. 예를 들어 `A05/replacement/tinylm/chat/supervision.py`의 목적지는 `Z:\TinyLM\tinylm\chat\supervision.py`다. `replacement`라는 폴더 자체를 프로젝트에 넣는 방식이 아니다.
4. `tinylm`·`scripts` 전체 폴더를 삭제하지 않는다. 패키지에 없는 기존 모듈은 그대로 필요하다. `original/`과 보고서 문서는 적용 코드가 아니다.
5. 교체 대상 원본이 없는 A04 등에는 `original/`을 만들지 않았다. 동일 공통 파일이 여러 조치에 들어간 경우 적용 순서와 무관하게 같은 내용이 된다.
6. 작성 후 원본이 바뀌었다면 제공한 전체 파일로 덮어쓰지 말고, `original`↔`replacement` 차이를 최신 원본에 반영한다. manifest는 그 변경 여부를 확인하는 기준이다.

**실제 원본에 복사하는 작업은 이번 요청 범위에서 수행하지 않았다.** 자동 적용·삭제·이동 스크립트도 넣지 않았다.

## 3. 파일 검사와 실행 검증은 구분한다

사용자는 적용 전 아래 읽기 전용 검사기로 선택 조치의 사본/해시와 현재 프로젝트를 대조할 수 있다. 이 검사기도 이번 작업에서는 실행하지 않았다.

```powershell
& .\ai_dev_tool\20260909_report\CHECK_PACKAGE.ps1 -Action ALL -ProjectRoot Z:\TinyLM
```

개별 적용은 `-Action A05`처럼 바꾼다. ALL은 모든 개별 폴더의 공통 파일 복사본도 확인한다.

| 검사기 상태 | 의미 |
|---|---|
| BASELINE_MATCH | 현재 원본이 작성 기준과 같음 |
| NEW_PATH_AVAILABLE | 신규 파일의 목적지가 비어 있음 |
| ALREADY_APPLIED | 현재 파일이 이 교체본과 같음 |
| CONCURRENT_CHANGE_OR_COLLISION | 현재 원본 변경 또는 신규 경로 충돌; 변경 내용을 검토해야 함 |
| ORIGINAL_MISSING / DIRECTORY_COLLISION | 필요한 원본 누락 또는 파일/디렉터리 충돌 |

또한 기존에 그대로 사용할 핵심 모듈 28개와 v1/v2 보고서의 해시를 확인한다. 해시 검사는 **실행 가능성, 수치 정확성, GPU 메모리, 모델 품질의 검증이 아니다.** 실제 확인한 사본 수와 원본 보존 범위는 [VERIFICATION.md](VERIFICATION.md)에 기록했다.

적용 후 기존 TinyLM Python 환경에서 사용자가 실행할 회귀 테스트 명령은 다음과 같다.

```powershell
python -m unittest discover -s tests/report_20260909 -p "test_*.py"
```

개별 조치만 적용하면 그 폴더에 포함된 테스트만 실행된다. 이 작은 테스트 뒤에 각 README의 경로 확인·대조 평가를 수행해야 한다. 기존 저장소의 필요한 검사도 사용자의 실행 절차에 포함하되, 미실행 상태를 PASS로 바꾸지 않는다.

## 4. 기존 환경과 입력 파일

기존 TinyLM 환경의 `torch`, `tokenizers`, `numpy`를 사용한다. A06의 RSS 계측에는 `psutil`, HF 모델 평가/교사 생성에는 `transformers`와 해당 모델을 지원하는 기존 버전이 필요하다. 자동 설치, 모델 다운로드, 외부 API 호출을 하는 경로는 추가하지 않았다. A01에서 제공한 `--only stage1_heldout` 명령은 로컬 자료만 사용한다. 기존 fetch의 다른 공개 benchmark 다운로드 기능과 선택적 W&B 업로드는 사용자가 그 옵션을 실행할 때만 동작한다.

각 문서의 `$AuditCheckpoint` 등은 실제 파일을 지정하는 자리다. 프로젝트 루트에서 예를 들어 다음처럼 설정한다.

```powershell
$AuditCheckpoint = 'Z:\TinyLM\runs\ckpt\사용할_실제_체크포인트.pt'
$AuditTokenizer = 'Z:\TinyLM\data_cache\tok-ko-en-32768.json'
```

체크포인트 이름은 예시를 그대로 쓰지 않고 존재하는 정확한 파일로 바꾼다. 부모가 HF tokenizer를 사용했다면 해당 tokenizer를 지정해야 한다. 어휘 크기의 일치는 token ID 의미의 일치까지 입증하지 않는다.

| 변수/입력 | 필요한 내용 |
|---|---|
| AuditReferenceCheckpoint | 같은 평가 계약의 대조 checkpoint |
| AuditDenseParent / AuditStudentCheckpoint | A11에서 비교할 실제 dense 부모와 같은 middle 깊이의 학생 |
| AuditTeacherSnapshot | config·가중치·tokenizer·native chat template가 있는 특정 로컬 HF snapshot 디렉터리 |
| AuditPrompts | A06에 사용할 충분히 긴 대표 prompt의 고유 id/text JSONL |
| AuditFamilyMap | 출력 문항 ID → 검수한 source family의 JSON 사전 |
| AuditVerification | A13 교사 응답의 원문/응답 SHA와 검수 근거를 담은 JSONL |
| AuditSmallTrain | A15 길이 제한 이내인 train 자료의 작은 별도 사본 |

이미 존재하는 Fresh 자료는 `datasets/TinyDataset/SFT/train/sft_fresh_v1_train_1000.canonical.jsonl`과 `eval/sft_fresh_v1_eval_300.canonical.jsonl`이다. 기본 SQuAD 경로는 `datasets/squad/train-v2.0.json`이다. 데이터 cache 디렉터리는 `ko-en_600000000`처럼 정수 suffix를 사용한다. 문서의 bin 예시는 후보가 실제 사용한 stream과 dtype로 바꿔야 한다.

학습/생성 명령의 출력은 새로운 `runs/audit_20260909/...` 경로로 지정한다. 같은 출력 파일을 덮어쓰지 않는 도구는 이미 존재하면 실패한다. 중단된 산출물을 자동 삭제·복구하지 않으므로 다음 실행에는 새 출력 경로를 사용한다.

## 5. 변경된 인터페이스와 판정 범위

| 대상 | 적용 후 달라지는 점 |
|---|---|
| A01 held-out | 버전별 cache와 meta 필요. 기존 무버전 cache를 자동 평가하지 않음 |
| A02 common_bpb | `--out-jsonl` 필수. 오염 제외에는 실제 manifest 필요. 서로 다른 tokenizer scan은 merge 도구로 합집합을 만들고 모든 후보에 같은 corpus 적용 |
| A03 eval_bench_suite | 문항별 ID/hash/skip 기록. 로컬 mean-NLL 점수는 공식 acc_norm이 아님. 명시적 W&B는 bench_v2 namespace 사용 |
| A05 SFT | 별도 `scripts/train_sft.py` 진입점. fresh optimizer·constant LR·native tokenizer JSON·단일 장치·no packing 범위 |
| A06 deployment | 선택한 같은 객체로 계측. 반환 경계 tensor 합이 40MiB 미만이어도 내부 CPU workspace 증거가 부족하면 PASS를 내지 않음 |
| A08 trainer/CLI | matrix WD/audit 옵션 추가. 미지정 기본 레시피 보존. 옛 Muon checkpoint의 optimizer state 없는 정확한 resume는 거절 |
| A09 LRM | `--tag` 또는 `--ckpt`. WD>0의 역보정은 적용 LR history 필요. 미해결이면 exit 2이며 품질 실패가 아님 |
| A09 기존 LR 정합 검사 | `check_lr_factor_sync.py`는 복제 수식 비교에서 cfg/history 연결 검사로 변경. 기존 static_all의 옛 설명 문자열은 새 수치 검증 결과가 아님 |
| A10/A11 진단기 | 명시적 checkpoint/bin/group 입력 사용. 예전 preset/models 배치 명령은 각 README의 새 명령으로 바꿔야 함 |
| A13 text KD | 생성과 정답 검증을 분리. 검증된 같은 ID의 N_REF/T_VERIFIED를 함께 작성 |
| A15 등가성 | 고정 작은 batch·fresh optimizer 1 update 범위. 반올림 일치, 허용 오차 일치, tensor byte 일치를 분리 |

A01/A03의 평가기, A05/A13의 serializer·mask처럼 서로 영향을 주는 공통 파일은 **통합한 한 버전**을 개별 폴더에도 넣었다. 원본의 모든 배치·출력 parser에 대한 전면 호환을 실행 검증한 것은 아니다. 특히 위 변경 인터페이스를 사용하는 옛 자동 실행 명령을 그대로 재가동하지 말고 해당 README의 명령과 출력 계약을 사용한다.

## 6. 코드 작성 중 추가로 확인한 문제

- **Fresh SFT 채점 규약:** eval 11행의 정본 “미리내통이다.”와 허용 답 “미리내통”이 다르다. 32행의 “열 어절 이내” 조건도 채점 메타데이터에 빠져 있다. A05는 reference-only 전수 검사와 원문 SHA가 연결된 별도 grading override를 제공한다. 원본 답/규칙을 자동 완화하지 않았다.
- **Muon 재개 상태:** 원본 trainer의 checkpoint 저장/복구에 Muon optimizer state가 빠져 있었다. A08 교체본에 저장·복구를 추가했다. 정상적인 fresh full run을 소급 무효 처리하는 발견은 아니다.
- **서로 다른 tokenizer의 오염 검사:** 개별 scan의 제외 목록만 적용하면 모델마다 평가 집합이 달라질 수 있다. A02는 동일 corpus 검사 결과를 합집합으로 묶는 도구를 제공한다.

이 항목들의 실제 실행 결과는 아직 없다. 새로운 문제 발견과 수정 코드 작성, 회귀 테스트 통과, 연구 실험의 종결은 서로 다른 상태로 유지한다.

## 7. 권장 적용 순서

1. A01–A04로 평가 자료·채점·비교 계약을 먼저 연결하고 최종 후보와 KD 대조군의 필요한 평가만 갱신한다.
2. A05는 reference 규약 감사 → 실제 loss-token 계측 → B0 평가 → 작은 S1 SFT 순서다. A13은 이 기준 위에서 같은 accepted ID의 N_REF와 비교한다.
3. A06은 같은 checkpoint의 변환 경로를 하나씩 비교한다. 작은 LUT의 메모리와 큰 unpack-cache의 속도를 같은 결과로 합치지 않는다.
4. A09–A11은 기존 checkpoint의 재진단부터 수행한다. A08의 빠진 matched 대조와 A07/A12/A14의 조건부 실험은 해당 판단에 필요할 때만 연다.
5. A15는 새로 연결한 학습 경로에 사용한다. 기존에 완료된 모든 학습을 되풀이하는 gate가 아니다.

현재 장비의 가용 VRAM 13–14GB를 기준으로 SFT 예시는 micro-batch 1부터 시작하도록 작성했다. 15GB 근방의 OOM이나 실제 학습 시간은 미실측이다. 40MiB 목표 달성과 지능 향상 여부는 이 패키지를 적용해 얻을 후속 실험 결과로 판단해야 한다.

기존 연구 근거 원장은 [v1](20260909_TinyLM_40MiB_연구타당성_비판평가_및_개선전략_보고서.md), 실행 조치의 근거는 [v2](20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md)에 남아 있다.
