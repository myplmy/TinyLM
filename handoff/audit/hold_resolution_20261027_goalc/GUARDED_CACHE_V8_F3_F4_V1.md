# 다음 캐시의 guard5·분할 선택 결합

| 안 | 장점 | 단점·비용 |
|---|---|---|
| A. 기존 cache7/guard4 그대로 사용 | 새 구현이 없다 | 추가 두 원문의 안전 계약과 맞지 않아 다음 캐시에 사용할 수 없다 |
| B. 전체 캐시 엔진을 복제해 수정 | 호출 관계를 평면화할 수 있다 | EOS·중복·문서 경계·기존 예외 검증을 중복 구현하고 다시 입증해야 한다 |
| C. 기존 cache7에 좁은 runtime wrapper 추가 | 검증된 엔진·참조 census·이전 세 안전 파생본을 재사용한다 | 중첩 context의 계약 복원과 pins를 CPU로 별도 검증해야 한다 |

수행: C. 현 사용자 objective 1·6절과 중간 생성물 관리 지시 범위의 CPU 전처리 도구다. 새 `guarded_reviewed_cache_v8.py`, 해당 테스트, 다음 runner/preparer wrapper 및 작은 감사 근거만 신설한다. 기존 코드·원형·캐시15·데이터 TXT·환경 파일은 수정하지 않는다. 실행은 matching roster/opaque/census/code pins와 충분한 정제 누적 이후 하나의 다음 버전으로 묶는다.

| 축 | 영향·근거 |
|---|---|
| 코드 | cache7→cache6→cache4/3/2/1의 runtime을 재사용한다. guard5 checker는 guard4 함수 별칭을 먼저 호출하므로 guard5 검증을 전역 교체 전에 한 번 수행하고, 중첩 호출은 같은 SHA의 계약을 재사용해야 한다. build뿐 아니라 verify의 후반 proof 생성까지 guard5를 유지한다. |
| 데이터 | 두 신규 원형/후보는 채택 불가이고 네 parent alias가 정확한 metadata HOLD여야 한다. 원형 본문을 decode하지 않는다. 세 이전 승인 파생본은 이전 선택 행과 완전 동일해야 한다. 새 선택 manifest는 원래 dict/list로 재구성하고 물리 SHA와 조각 pins를 함께 보존한다. |
| 테스트 | metadata-only contract의 진입·중첩·예외 복원, 누락 alias/수치 변경/금지 본문 채택 거절, 세 안전 행 동일성, 분할 저장 호환을 검사한다. 실제 전체 캐시 build/consumer는 이 시험으로 대체하지 않는다. |
| 정본 문서 | `.agents/project.json`의 실험·모델·플래그 정본을 바꿀 조건 변경은 없다. WIP와 이 audit가 현재 도구·검증 상태를 기록하며 최종 A–E 문서 연쇄는 남아 있다. |
| 기술부채 | import 별칭과 patch 범위를 wrapper에 한정하고 종료 시 복원한다. 새 corpus/EOS/중복 엔진은 만들지 않는다. |
| 권한·소유권 | CPU만 허용, 모델/GPU/교사/학습/다운로드/TinyDataset/타 세션 자료 접근 없음. 임의 삭제 없음. |
| 비교·증거 수준 | 토크나이저·학습 노출·기존 평가 자료를 바꾸지 않는다. 도구 회귀 PASS는 캐시 또는 모델 품질 PASS가 아니다. |
| 저장량 | parent 460695행을 census에 복사하지 않고 기존 immutable metadata를 참조한다. 반복 전체 캐시·전체 roster 생성은 피한다. |

구체 실패 방지: guard5 검증 전 cache6.CONTRACT를 5로 바꾸면 기존 guard4 checker의 9/10/15 개수 assertion에 걸린다. 반대로 verify 후반에 계약이 4로 복원되면 실제 ledger가 5여도 proof의 계약 SHA가 4로 잘못 기록될 수 있다. 두 범위를 명시적으로 감싼다. filename observer는 이전 세 안전 파생본까지 금지하므로 전체 캐시에 설치하지 않고, 기존 byte metadata projector와 정확한 HOLD/안전 파생본 검증을 사용한다.
