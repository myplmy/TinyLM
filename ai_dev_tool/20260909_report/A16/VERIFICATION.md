# A16 검증 상태와 인계

작성일: 2026-09-09. **작성·정적 문맥 검토 상태이며 실행 검증 전이다.**

## 이번에 수행한 확인

- 원본 평가기 두 파일과 benchmark downloader의 전체 본문을 읽고 등록된 19+3 경로를 대조했다.
- P069/P085 계획, 050/056/074 결과 분석문서는 후속 절까지 확인했다. 074는 마지막 §23까지 반영했다.
- datasets/bench의 19개 파일을 끝까지 읽어 행 수와 SHA-256을 집계했다. 한국어 dev 3개도 행 수·해시를 확인했다.
- MMLU-Redux 5,700개 라벨/오류 필드, BFCL 2,351개 출처·ground_truth 유무를 전수 집계했다. DATA_AUDIT.json에 기록했다.
- 새 코드의 CLI parser → helper → canonical 모델 로더/공식 API 연결을 문맥상 검토했다.
- frozen 원본 복사본 2개가 원본과 SHA-256까지 같은 것을 읽기 전용 파일 해시로 확인했다.
- audit 시작과 종료 대조에서 원본 코드 7개의 SHA-256이 같았다.
- replacement의 Python 20개는 모두 원본 저장소에 없던 **새 경로**다. 그중 18개가 신규 구현/테스트, 2개가 원본 복사다.
- 기존 A01–A15, ALL, 원본 benchmark 경로를 이번에 수정·삭제·이동하지 않았다.

파일 해시·경로 검사는 코드 실행이나 수치 검증의 대체물이 아니다. manifest.json의 source_files와 package_files가 이번 상태의 기준이다.

## 수행하지 않은 것

| 항목 | 상태 / 이유 |
|---|---|
| Python 구문 검사, compileall, import, pytest/unittest | **실행 안 함**. 이번 사용자 지시의 코드 실행 금지 준수 |
| 프로젝트 check_static_all.py | **실행 안 함**. 일반 작업규약 R21보다 이번 사용자의 실행 금지 지시가 우선 |
| CHECK_PACKAGE.ps1 | 파일을 작성했으며 **실행하지 않음**. 같은 종류의 파일 해시는 읽기 전용 명령으로 직접 확인 |
| 모델·토크나이저 실행, checkpoint 역직렬화 | 실행 안 함. 예시 checkpoint는 존재만 확인 |
| GPU·학습·추론·벤치마크·tool simulator | 실행 안 함 |
| 패키지 설치·프로젝트 dependency 변경 | 수행 안 함 |
| official HumanEval/EvalPlus/BFCL/KorQuAD scorer 실행 | 수행 안 함 |
| 기존 원본 코드 적용·git·queue/W&B 수정 | 수행 안 함 |

## 사용자 사전 검증의 합격 조건

1. CHECK_PACKAGE의 경로·해시 대조가 통과한다. 같은 내용이 이미 설치된 경우는 허용하며 다른 새 경로 충돌이나 원본 기준 변경은 검토한다.
2. 작성된 CPU 테스트 **14개**가 실행되어 통과한다. 표본 모형을 쓸 뿐 TinyLM checkpoint·GPU를 쓰지 않는다.
3. pinned harness의 task 이름과 data/config가 정상적으로 해석된다. README의 2문항 smoke에서 sample ID, target, 실제 prompt, metric, filter를 확인한다.
4. 같은 checkpoint의 R/L은 checkpoint·tokenizer·TinyLM source hash가 일치한다. 다른 입력을 행 위치로 대응시키지 않는다.
5. 실제 모델에서 짧은 고정 요청의 no-cache/KV 결과를 대조한 뒤에만 --kv-cache를 사용한다. 이를 이번 CPU fixture 테스트 통과로 대신하지 않는다.
6. 긴 입력이 거부되면 incomplete로 기록한다. 명시적 left 팔은 절단 건수가 기록되는지 확인한다.
7. HumanEval 164 ID와 task별 sample 수, 공식 기능 검사 결과를 확인한다. EvalPlus는 공식 stdout의 집계와 공식 per-task JSON을 모두 확인한다.
8. BFCL 공식 v3 checkout을 확인하고 lock을 만든다. simple 범주의 공식 ID 400개 coverage, schema 보존, endpoint 오류 0, 공식 score 산출을 확인한 후 확대한다.
9. KorQuAD는 공식 v1.0 scorer 파일의 **출처 및 내용**을 확인한다. 해시는 이후 변경 감지 수단이지 출처 증명 수단이 아니다.
10. 검증 후 full split을 실행하고, 모델 seed/프로토콜별 결과를 분리한다. 이 검증 단계 자체를 연구 성능 개선 결과로 기록하지 않는다.

## 특히 미확인인 호환성

- 목표 harness는 v0.4.13이다. 공개 API와 task 자료를 조회했으나 이 환경에서 설치본을 import하지 않았다.
- BFCL은 공개 OSS handler/ModelConfig/CLI API에 연결하도록 구현했다. Gorilla v1.3 고정본의 전체 API를 설치·실행하여 확인한 것은 아니다. freeze의 release label은 사용자 확인 정보다. API 불일치는 실패로 드러나며 자동 legacy fallback을 하지 않는다.
- KorQuAD v1.0 공식 평가 파일 본문은 이번에 확보하지 못했다. 대체 코드가 그 파일을 받도록 했으며 로컬 v2.0이나 자작 정규화를 공식 v1.0으로 가장하지 않는다.
- 스크립트 일부는 로컬 dependency나 language resource의 최초 준비가 필요하다. Windows/WSL 환경 차이와 실제 VRAM 여유도 실행으로 확인해야 한다.
- official HumanEval/EvalPlus 테스트는 별도 사용자 실행 환경이 필요하다. 본 세션의 ‘생성 코드 실행 금지’ 때문에 실행 점수가 없다.

## 보존과 비교의 정확한 범위

frozen legacy 재생은 **기존 scoring/generation 함수를 공통 canonical 모델 로더·명시한 tokenizer에 연결**한다. 원본 main의 tag 추정, 기본 32k tokenizer 선택 등 과거 자동 선택 문제까지 재현한다는 뜻은 아니다. 그 main 경로는 원본 scripts에 그대로 남아 있다.

원본 main 재현 결과와 frozen 함수 대조 결과가 다르면 checkpoint·tokenizer·dtype·context·sampling을 먼저 확인한다. source 해시가 같아도 모델 상태나 설정이 다르면 동일 실행이 아니다.

## 사용자에게 부탁하는 것

코드 적용 및 실제 검증·실행은 아직 남아 있다. README의 순서와 위 합격 조건으로 결과를 확인해야 한다. 이번 패키지에는 성공한 동적 테스트 로그나 benchmark 점수가 없다.

-done 배치: 이번에 생성·삭제·이동한 배치가 없으며 기존 -done.bat를 정리하는 작업도 수행하지 않았다.
