# SODA input evidence, derivative lineage and student wire preparation

## 1. Why and three options

Original69/current161 require preparation for the unfinished75M teacher-language supply. The closed [input view](20261118_soda_named_input_view_contract.md) excludes old narrative targets. Direct code tracing found that public_refill.english_rows reads only id/inputs/targets/dataset_name, losing template/subdataset fields; deficit production computes conversation_split_key from the supplied first user text both before generation and when wrapping a candidate. Replacing that text with a shorter view would change the derivative split key. The saved2 rows have no previously assigned corpus split; do not invent one.

| Option | Content | Benefit | Limit | Impact | Work |
|---|---|---|---|---|---|
| A | Replace old source messages with the prefix everywhere | Small apparent change | Recomputes lineage from a different question and cannot qualify the four-column source row | Changes old producer/default semantics | Low initial cost, high provenance debt |
| B | Separate a prepared original canonical source from an evidence-only source, then reuse existing task/wrapper/mask functions | Preserves the legacy derivative key while checking actual prompt/student interfaces | Caller still needs full raw fields; no original SODA root or rights admission | New explicit preparation API/test only; old functions unchanged | Moderate bounded CPU work |
| C | Implement a new persistent source iterator and full production fork | Can eventually handle raw fields/cursors/quotas end to end | Actual source join/rights, GPU permission and full production remain unresolved | New source-state schema, pilot and long-run lifecycle | High; prerequisite work first |

Choose B. A925-character dialogue prefix and its longer original management question are distinct first-user inputs; the same normalization/hash algorithm does not make their keys interchangeable. Preserve the original canonical key before selecting evidence. This is a derivative input hash, not an original SODA ID or cross-template concept root.

## 2. Authority and impact before implementation

| Paths | Action | Authority | Excluded |
|---|---|---|---|
| scripts/p106b_soda_candidate_wire.py | New explicit prepared-source, teacher-payload and student-candidate functions | User161 required implementation and original69 preparation | No iterator/producer/CLI/default activation or file writes |
| scripts/test_p106b_soda_candidate_wire.py | Authored CPU lineage/payload/mask/budget controls | Same necessary verification | No model or existing corpus mutation |
| Owned audit runner/snapshots, saved2 rows and exact existing chat32 tokenizer | Reuse closed source cases; verify tokenizer bytes before CPU tokenization | Same bounded preparation | No Parquet rehash, new source acquisition, teacher/model call or corpus admission |
| P106B/result101/lists/baselines/methods/COMPASS and own WIP/coordination | Plan/result recovery | User161 documentation duty | No root09/environment/Git/deletion |

| Axis | Impact | Evidence and decision |
|---|---|---|
| Code/dependencies | New API | Reuse mixed_scale.attach, task_contract.payload/learner_turn, supported.attach_visible_source, teacher_wrapper.wrap_turns and actual mtp_sft.encode_record. Existing callers are unchanged. The previous view does not implement these interfaces. |
| Data/schema | New detached preparation object | Retain original canonical source separately from one-message input evidence; record declared provenance and legacy key/split policy. No corpus migration or actual split assignment. |
| Tests | Required | Target omission, original-key versus view-key, target-change noninterference, detached objects, bilingual task formats, multiple assistant spans and full1024-token refusal. Existing view tests need no rerun without edits. |
| Document chain | Required | Stage4ft5Wf/result101 and scoped plan/result lists, baselines, methods, COMPASS, WIP. No flag or training registry mutation. |
| Debt/priority | Bounded | Four-column iterator, persistent producer/cursor, source roots/rights and full population eligibility remain explicit follow-ups. Do not call this a75M production implementation. |
| GPU/model authority | Separate | Existing Torch is imported only for the pure actual Record encoder; no tensor/model construction, checkpoint, inference, training, CUDA initialization or network requests. |
| Ownership | Preserved | Only already saved owned review rows and existing tokenizer read; old source files, old logs/checkpoints, other cleanup work and TinyDataset excluded. |
| Comparison validity | Same cases | Same raw row and tokenizer; compare evidence scope and first-user hash. No learning pool, training tokens, quality sigma or performance comparison. |
| Evidence levels | CPU software only | Actual token counts include complete wrapped conversation and assistant end tokens. They establish fit for supplied authored turns only, not future teacher-output fit, semantic truth or quality. |

## 3. Question and prediction

Can original derivative keys remain exact while teacher payloads and student references use only the named input dialogue? Can existing wrappers and the real tokenizer produce correctly masked bounded one/three-turn candidates? Expect positive exact lineage/payload/mask checks for small supported cases. Long candidate answers may exceed1024 and must be refused without truncation. Root/rights remain HOLD regardless of a technical pass. Real teacher responses may still be unsupported or too long; no quality improvement is predicted here.

## 4. Stages

Freeze old source pins -> new explicit preparation object/functions -> authored CPU controls using a small tokenizer fixture -> saved2 input rows with the pinned chat32 tokenizer -> scoped readback/result recovery. No actual producer monkeypatch, model request, newly assigned corpus split or source iterator change.

The object exposes detached original/evidence sources. Compute the original key through the existing canonical first-user function before selecting the prefix. Keep proposed legacy modulo20 split distinct from original source split=train and from an actual assigned corpus split. No original root is inferred. Qualify exact raw fields with the previous view and declared source spec, record physical-file authentication=false, and conservatively refuse structural chat markers/control characters in the prefix before it reaches student ChatML. Preserve raw bytes externally; never rewrite the source to fit.

Teacher preparation calls the existing task contract on the evidence-only source, with source-relative fictional scope explicit in the trusted system framing. Student preparation reuses learner_turn/wrap_turns/attach_visible_source and the actual encode_record for all supplied turns; no original narrative target is passed as evidence. Caller-provided answers, teacher identity, source rights and truth are unverified. Include complete reference, role/template overhead, assistant end tokens and all turns in the1024-token bound; no truncation or prefix-only fit claim.

## 5. Judgment

Require original source immutability, exact existing first-user hash, explicit different view key when observed, target omission from both teacher and student content, unchanged payload/evidence under target change, detached values and unchanged old helpers. Exact tokenizer hash and complete actual Record x/y/segment counts must match independent serialization/assistant-span controls. Refuse missing raw fields, bad declared provenance, boundary markers, invalid output formats, zero targets or context overflow. Technical success never changes corpus_admitted/root_joined flags.

## 6. Cost and preflight

CPU thread1,120 seconds; existing tlm_torch environment/tokenizers, two previously saved raw rows and one existing tokenizer file. No install/download/new environment/model/GPU. Tag p106b_soda_candidate_wire_v1_20261118 has no collision; the plan query returned no equivalent logged experiment. A/B training-token/pool/seed/sigma checks are not applicable: training tokens0 and no quality comparison. Baselines standard recipe/defaults are unchanged. This is design verification only; actual interface behavior still needs the CPU checks.

## 7. Execution

New owned CPU helper only; training/teacher/production launcher is not created or executed. Existing mtp_sft.encode_record imports Torch but only processes Python token lists in this scope. Monitor CUDA initialization and prohibit model constructors/HTTP calls in the harness.

## 8. Limits

No raw-field preserving iterator, persistent production/resume/cursor, original SODA root or cross-template deduplication, physical source verification by this API, rights/semantic/corpus admission, actual teacher output or teacher-tokenizer context,75M/8-hour generation, training/quality/default adoption. Real2 are previously saved source cases with authored question/answer controls, not new teacher samples or independent factual examples.

## 9. 원본 배포 조건과 Aya 행 대조

Ai2의 원본 SODA 카드 `fdc848ab0183208ea7808206c91c724414d0a071`은 CC BY 4.0과 `original_index`의 Atomic10x 인덱스 의미를 명시한다. 카드가 공개한 `train`, `valid`, `test` 행 수는 각각 1,191,582, 146,346, 148,968이다. 조건을 적용할 때는 저자·자료·라이선스 링크와 템플릿 또는 번역 변경 내용을 남긴다. [원본 카드](https://huggingface.co/datasets/allenai/soda/blob/fdc848ab0183208ea7808206c91c724414d0a071/README.md) · [Ai2 배포 설명](https://allenai.org/blog/are-you-thirsty-for-social-chitchat-data-64c0895c654d) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

이미 검토한 Aya `SODA-inst` 여섯 행은 템플릿 1·3·4가 각각 두 행이며, 모두 Aya의 `train`이다. 여섯 행 모두 Aya `id`에서 해당 파일 내 행 위치를 빼면 8,396,473이고 `original_index` 열은 없다. Aya 카드도 `id`를 Aya 데이터 행의 고유값으로 설명한다. 따라서 원본 행과 분할을 연결하기 전에는 이 값들을 원본 키로 쓰거나 평가 분리의 증거로 쓸 수 없다. [Aya 카드](https://huggingface.co/datasets/CohereLabs/aya_collection) · [저장 행 대조](../../handoff/audit/research_20261118_01a1e647/SODA_ORIGIN_RIGHTS_READBACK_v1.json)

운영 편입에는 실제 원본 행과의 연결, 같은 원본의 템플릿·번역 파생본 묶음, 공식 TRAIN·VAL 분할 확인이 남는다. 이번 범위에서 원본 데이터 취득·편입은 0행이다.

### 9.1 Aya 영어 릴리스 내 중복과 기존 분할 검산

기존 영어 파일 일곱 개의 SODA 행 7,844,049개에서 서사 본문의 고유 해시 1,191,578개를 검산했다. `plain_4`의 주제·서사 1,191,582개는 `(T)`에서 똑같은 순서로 네 번 나타났다. 같은 서사·화자·발화의 `plain_1`과 `plain_2`를 함께 사용하면 기존 첫 사용자 질문 해시의 제안 분할은 622,192쌍 중 59,307쌍을 갈랐다. 같은 원천에서 질문 문구를 바꾸는 템플릿이 각각 다른 분할 키를 만들었다. [결과101 §695](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-soda-aya-duplicates-split)

운영 원천을 구성할 때 `(T)`의 순서 복제는 Aya 릴리스 내부에서 확인할 수 있다. 같은 서사가 다른 주제와 결합된 경우도 있어 원본 대조 시 주제와 대화 필드를 함께 사용한다. Ai2 원본 `original_index`와 원분할을 실제로 연결한 뒤 템플릿·언어 파생본을 한 묶음으로 배정한다. `original_source_split='train'`은 현재 준비 경로의 Aya 원천 표시이고 원본 SODA 분할은 `original_root_joined=False` 상태다. [현재 준비 경로](../../scripts/p106b_soda_candidate_wire.py) · [Ai2 원본 카드](https://huggingface.co/datasets/allenai/soda/blob/fdc848ab0183208ea7808206c91c724414d0a071/README.md)

### 9.2 지원 형식의 정확한 원본 연결

생산기와 같은 영문 template 1의 원문은 서사·보이는 화자·발화 순서로 비교한다. Ai2 세 파일의 지문·행 수를 검증한 뒤 유일한 원본 위치와 공식 분할을 반환한다. 동일 `original_index`의 공식 분할이 충돌하거나 같은 내용이 복수 행에 있으면 보류한다. 검증·시험의 연결 결과는 해당 분할로 유지한다. 현재 저장 Aya 두 행의 비교 키가 준비됐다. 실제 Ai2 파일 연결과 편입은 선결이 남아 있다. [결과101 §702](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-soda-original-lineage)

## 10. History

[101 section645](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-soda-parent-evidence-student-wire-cpu) closes CPU11,2 saved source cases,12 authored bilingual/task wires and20 prepared payloads; old17 unchanged. Maximum485 x tokens, complete independent masks/EOT and actual overflow refusal pass. Both original/view keys differ but proposed TRAIN splits stay the same. No iterator/producer/root/rights/teacher/75M/quality completion.
