# SFT용 Fresh 코퍼스 v2

> **현재 상태: `SEMANTIC_SOURCE_FAMILY_AUDIT_FAIL` — 학습·평가 사용 금지.**
> eval 360건 전부의 가공어-정규화 source 유형이 train과 겹친다. 상세는
> `audit/sft_fresh_v2_semantic_diversity_audit.md`를 따른다.

이 디렉터리는 v1과 독립된 신규 SFT 데이터 패키지다. 기존 `SFT/`의 v1 파일은 입력이나
출력으로 수정하지 않는다.

고정 계약은 `prompts/sft_fresh_v2_authoring_prompt.md`에 있다. 학습 문자열은 canonical
레코드의 `messages`만 `chatml`로 직렬화한다. `meta`, source ledger, 감사 파일은 학습 입력이
아니다.

현재 범위는 데이터 생성과 CPU 정적 감사뿐이다. 루트의 `sft_fresh_eval`은 v1 파일에 고정되어
있고 T1 `multiple_choice` 우도 채점을 지원하지 않으므로, 실제 v2 평가 경로는
`V2_T1_SCORER_PENDING` 상태로 별도 구현해야 한다.

## 생성 결과

- train: `train/sft_fresh_v2_train.canonical.jsonl` — 22,200건
- train source ledger: `sources/sft_fresh_v2_train_source_ledger.jsonl` — 22,200건
- source-disjoint eval: `eval/sft_fresh_v2_eval_360.canonical.jsonl` — 360건
- eval source ledger: `eval/sft_fresh_v2_eval_source_ledger_360.jsonl` — 360건
- 실제 train ChatML serialized token: 10,037,990
- 실제 train supervised-loss token: 4,033,318 (40.1805%)

정적 감사는 `audit/sft_fresh_v2_static_audit.json`과 `.md`, 보호 자산 8-token 전수 감사는
`audit/sft_fresh_v2_overlap_audit.json`과 `.md`가 소유한다. held-out v2.8 및 ko-en 600M
train pool의 exact 공유 8-token 유형은 모두 0건이었다. 다만 이는 의미 source-family
격리 실패를 상쇄하지 않는다. hash 후보는 원래 token ID 8개와
재대조했으며, 전체 일치 유형 목록은 `audit/sft_fresh_v2_overlap_match_types.jsonl`이다.

LLM judge는 사용하지 않았다. 따라서 사람 채점 50건 일치율 파일은 적용 대상이 아니다.
모델 로드·GPU·학습·체크포인트·모델 평가는 모두 수행하지 않았다.
