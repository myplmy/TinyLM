# SFT용 Fresh 코퍼스 v1

이 디렉터리는 기존 고밀도·저밀도·held-out 코퍼스의 문장을 재료로 삼지 않고 직접 작성한 문맥 기반 positive SFT 파일럿을 보관한다.

현재 승인 범위는 Phase 0과 Phase 1뿐이다. Phase 2 확장, rejected sidecar, 학습, 모델 로드, 체크포인트 생성 및 모델 평가는 승인되지 않았다.

Phase 1 파일럿 1,000건과 source-disjoint eval 300건은 생성 및 비토큰 정적 감사를 마쳤다. 하드 실패는 0건이며 실제 토큰 계측은 사용자 승인 전이므로 `TOKEN_CALIBRATION_PENDING`이다. 상세 결과와 평가 예약 교정 이력은 `PHASE1_PILOT_REPORT_V1.md`에 있다.

## 디렉터리

- `PHASE0_DESIGN_REVIEW_V1.md`: 적용 설계와 실행 경계
- `PHASE1_PILOT_REPORT_V1.md`: 파일럿 결과, 감사 해석 및 남은 승인 게이트
- `prompts/`: 작성에 적용한 프롬프트
- `authoring/`: 직접 작성한 감사 가능 원고
- `sources/`: 학습 입력에서 제외되는 source ledger
- `train/`: canonical positive SFT JSONL
- `eval/`: source-disjoint 자동채점 평가와 평가 source ledger
- `manifests/`: 자산, 버전, 분포, 해시 및 상태
- `audit/`: 정적 감사 결과와 위반·후보 목록
- `tools/`: 이 코퍼스만을 위한 기계적 패키징·감사 도구

## 고정 경계

- 데이터셋 표시명: `SFT용 Fresh 코퍼스 v1`
- dataset version: `v1`
- canonical schema: `canonical_version=1`
- serializer: TinyLM v1 `chatml`
- 학습 직렬화 대상: `messages`만
- 학습 손실 대상: assistant text와 승인된 assistant 종료 경계
- 다른 모든 데이터셋: 읽기 전용 보호 대상
- 토큰 계측: 사용자 별도 승인 전 미실행
- 상태: Phase 1 제출 뒤 `SCALE_UP_NOT_AUTHORIZED`
