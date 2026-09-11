# TinyLM Stage 1 High-Density v2 — 작업 준비 루트

- 상태: `PREPARATION_ONLY` (2026-09-10 KST)
- 이 루트에는 아직 train·validation 레코드, corpus, checkpoint, 자동 감사 결과가 없다.
- 목적: 보호 중인 Stage 1 v1을 바꾸지 않고, 자연성·출처 검증을 거친 별도 v2를 준비한다.

## v1 보호 경계

`../stage1_highdensity_dataset/`는 기존 확정본이며 이 v2 준비 작업의 입력 정본일 뿐 수정 대상이 아니다. 다음은 별도 승인 없이는 금지한다.

- v1의 source, train, val, audit report, ID, relations, text 수정·이동·삭제
- v1 파일을 v2 경로로 무비판 복사하거나 같은 ID를 v2에 재사용
- v2를 근거로 v1의 완료·품질 판정을 바꾸는 일

## 현재 참조 정본

실제 v2 생성에 들어가기 전에는 다음 문서의 최신 내용을 다시 읽고, v2 전용 설계 결정과 충돌하지 않는지 확인한다.

- `../stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`
- `../stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`

현재 Guide의 13개 controlled relations, 150-record family, split 격리, source-first 및 read-only audit 원칙은 유지 후보이다. 다만 v2의 primary literal 계약·새 ID prefix·범위는 사용자 승인 뒤 이 루트의 v2 설계서에서 확정한다.

## 디렉터리 역할

```text
sources/term_registry/  primary 용어·정의·출처·검토 상태의 source-side 원장
sources/train/          승인된 train 원고만 보관
sources/val/            승인된 validation 원고만 보관
train/, val/            감사 통과 뒤 포장된 JSON 산출물
tools/                  추적되는 read-only audit·builder 도구만 보관
audit_reports/          machine 결과와 human_review 판정 분리
manifests/              v1 입력 inventory와 v2 release manifest
migration/              v1→v2 결정·ID 매핑 및 제외 기록
work_ledger/            재개 지점과 승인 경계를 기록
```

## v2 생성 전 필수 관문

1. v1 read-only inventory와 SHA-256 기준선을 만든다.
2. 각 v2 primary의 자연성·정의·출처·semantic slot을 검토한다.
3. v2 범위, schema 방식, 새 ID 규약, validation 분리 기준을 사용자 승인으로 확정한다.
4. 승인된 source만 직접 작성하고, 구조·다양성·출처·자연성 검토 gate를 모두 통과시킨다.

이 준비 루트 자체는 v2 생성·포장·학습 승인이나 품질 PASS를 뜻하지 않는다.
