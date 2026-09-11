# Stage 1 High-Density v2 작업원장

| 일시 | 상태 | 범위 | 확인 내용 | 다음 승인 필요 작업 |
|---|---|---|---|---|
| 2026-09-10 KST | `PREPARATION_ONLY` | v2 작업 루트 | 독립 폴더와 source·audit·manifest·migration·ledger 경계를 준비했다. 실제 레코드·source·corpus·audit script·audit 결과는 0건이다. v1 파일은 수정하지 않았다. | v1 naturalness/provenance inventory 범위와 v2 schema·ID·대상 영역 승인 |
| 2026-09-11 KST | `PENDING_USER_REVIEW_BEFORE_V2_REWRITE` | primary+은/는 retrospective signal | v1 read-only 전수값은 train 76.6647%, validation 85.3333%, 전체 77.6178%다. 이는 도입부 집중도 signal이며 v1 결함 판정이나 v2 수치 상한이 아니다. | area·family 층화 사람 검토, v2 term registry·도입부 다양성·naturalness/provenance 기준 및 수치 gate의 사용자 승인 |

## 재개 규칙

1. 먼저 `README.md`, v2 설계서, 기존 고밀도 Guide와 Design Spec의 최신 상태를 읽는다.
2. `stage1_highdensity_dataset/`를 변경 대상으로 해석하지 않는다.
3. v2 source 또는 tool을 만들기 전에 사용자 승인 범위와 대상 area를 원장에 기록한다.
4. 모든 실제 데이터 변경 뒤에는 해당 범위의 manifest·audit·원장만 갱신한다.

## 현재 금지 상태

- v2 train/val/source record 생성
- v1→v2 자동 변환 또는 기존 파일 수정
- Stage2 자연성 감사 script 구현 및 Stage2 설계서 반영
- v2 품질·완료·학습 가능 판정
