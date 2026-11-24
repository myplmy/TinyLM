# P107 bounded indexed document source and exact sampling

## 1. Why

Current161 authorizes required implementation and original58/59 first. Existing document_input.py loads every document into Python token tuples, then ExplicitDocumentSource clones all CPU int64 tensors. Its defaults cap16M tokens/128MB input, and its sampling rule is uniform document with replacement followed by uniform full crop. No indexed file source exists in the inspected P107 callers. A source for a larger admitted pool needs bounded token payload residency and exact source/RNG resume before actual Native training is considered.

| Option | Behavior | Benefit | Cost/limit | Impact | Implementation cost |
|---|---|---|---|---|---|
| A: resident | Raise the existing loader caps and keep every document tensor | Existing random access and sampler | Entire pool remains resident; merely raising limits does not solve memory | Existing defaults and large allocations | Low code/high memory |
| B: indexed | Scan sealed explicit JSONL once, retain record offsets/identities, read one selected document at a time | Preserves document order and uniform draw/crop RNG while bounding token payload | Initial full byte scan, bounded metadata and random file I/O; fresh reopen rescans | New opt-in module and source schema only | Medium validation and integration |
| C: sequential | Stream rows in file order through a small buffer | Simple mostly sequential reads | Changes document probabilities/order and RNG; not the same comparison | New sampling method and quality comparison | Medium implementation/high comparison debt |

Choose B. For a six-document pool of lengths3,24,25,26,29,55, the same seed/batch/length/micros must emit identical token/document-ID tensors and CPU generator states as the resident source, including short-document padding and every crop boundary. Sequential iteration cannot satisfy that control.

| Files/paths | Action | Authority | Excluded |
|---|---|---|---|
| tinylm/train/indexed_document_source.py | New bounded scanner/index and optional source | User161 required implementation/original58/59 | No existing trainer/input/source default edits |
| scripts/test_p107_indexed_document_source.py and owned audit helpers | Tiny synthetic file/input/RNG/trainer tests | Same required verification | Native construction, existing corpus/CP/feature reads, GPU |
| Exact new /tmp fixture roots | Exclusive synthetic JSONL/manifest files; preserve after tests | Same reversible CPU work | No old file mutation, deletion or corpus admission |
| P107/result107/document chain/own WIP | Plan/result recovery | User161 reporting | root09/Git/environment changes |

| Impact axis | Treatment |
|---|---|
| Code | New optional next_update/state_dict/load_state_dict source. Reuse the existing document_input byte/path/JSON helpers. Existing loader/CLI/trainer signatures and callers are unchanged. |
| Data | Accept the same explicit TRAIN manifest/row/admission format. New source schema refuses resident checkpoint import. No automatic preprocessing, download or corpus discovery. Default caps remain16M/128MB; an explicit bounded profile may request up to75M/1.28GB, not proof of production. |
| Tests | Exact resident token/document-ID/RNG controls, fresh source and full tiny trainer resume, bounded single-record reads, input/metadata quotas, malformed admission/rows/paths and read-error rollback. Guard Native constructor and preserve fixtures. |
| Documents | P107 Stage11W, new result107 section/condition signature, lists/baselines/methods/COMPASS and own WIP. No new model-run registry row or CLI flag is required for this programmatic CPU component. |
| Debt/order | Startup remains O(total file bytes), index metadata O(documents), selected access does file I/O. A persistent index, actual75M scale/RSS/performance and producer coordination are later separate work. |
| GPU authority | CPU thread1/small synthetic tokens and tiny ToyAttention only. No model/pretrained/GPU execution. |
| Ownership | No protected TinyDataset or other cleanup owner paths; no existing raw-log/cache/CP mutation, deletion/Git or packages. |
| Comparison | Keep ordered documents, vocabulary/padding, seed and exact draw/crop RNG. A capacity profile is not actual language exposure or an epoch. |
| Evidence | Payload/index-byte counters are not process RSS or model memory. Declared source SHA/admission bytes do not perform semantic/rights/leakage review. |
| Chain | New raw basename maps to exact result section and current source snapshot; prior107 CPU51 remains immutable and source-current. |

## 2. Question

Can explicit sealed rows be sampled through an offset index without retaining the whole token pool, while preserving resident draw/crop tensors and generator state and supporting exact fresh CPU trainer resume?

## 3. Prediction

Expect exact ordered token/document-ID/RNG equality for varied lengths, plus identical tiny trainer loss/targets/parameters and fresh resume. Expect metadata to grow with document count and startup to require a full scan; random I/O may be slower. This is a software/memory-layout question, not a predicted language-quality gain. A failure to preserve RNG or reject changed input invalidates the source contract.

## 4. Stages

Freeze existing source/input/trainer/controller pins -> bounded scanner and strict existing admission declaration -> offset-only source and distinct state schema -> resident exact controls and negative quota/path/identity tests -> tiny trainer/scaler integration and fresh resume -> result recovery. Only the new source is under implementation; existing CPU51 tests are not repeated when those sources do not change.

## 5. Judgment

Require exact token/document-ID and CPU generator equality, whole-file/selected-row hashes, unchanged file identities and full failed-update RNG/cursor rollback. Reject different manifest/tokenizer/admission/shape/seed/schema. A changed or inaccessible shard must fail closed. Index bytes and largest raw record/document are reported separately from actual RSS, which is not established here.

## 6. Cost

CPU thread1/120-second bound, new small JSONL fixtures with one roughly1M-token technical pool at most. No tokenizer/model execution, natural-language training or actual75M/8-hour production. Default indexed limits:16M tokens,128MB input,100000 documents,1MB raw record,32MB serialized record metadata and64 shards; explicit profiles cannot exceed75M/1.28GB or relax protected path/record guards.

## 7. Execution

Owned synthetic CPU helper only; no model launcher/batch. Tag p107_indexed_document_v1_20261118: check_run_registry tag and similar-plan queries both returned no match on Nov18. Independent variable: resident token storage versus offset-indexed file reads under the same sampler. Training-token/pool ratios and quality rulers are not applicable to this synthetic software gate; Native/quality remain NOT_RUN.

This preflight checks known design mistakes only; execution must establish the actual behavior.

## 8. Limits

No actual corpus admission, rights/semantic/leakage review,75M execution/whole-process RSS, Native/Muon/BF16-CUDA/compile/FSDP, language quality, CLI activation or default adoption. New source state is intentionally incompatible with resident source state. Full-source admission and actual model execution remain separate prerequisites.

## 9. History

Design/preflight complete. Existing source/input callers inspected and no indexed P107 implementation found. Implementation and CPU15 are now closed by [107 section21](../../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-indexed-document-source-cpu). Exact sampler/trainer/resume predictions were supported; real75M/RSS/Native quality remain NOT_RUN.
