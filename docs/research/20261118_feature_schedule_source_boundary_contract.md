# Feature windows and explicit upstream source boundaries

## 1. Why and options

Current161/original61 authorizes required implementation for the unfinished DSKD storage/resume path. [Single-window producer](20261118_feature_window_producer_contract.md) already closes21 CPU contracts. Its checkpoint explicitly excludes the upstream iterator/RNG. Actual code tracing of feature_window/feature_producer/dskdv2_window and old recovery/1024 diagnostics found no multi-window source coordinator. Reuse their completed behavior; do not rerun21 tests or reinterpret feature counts as language-training tokens.

| Option | Content | Benefit | Limit | Impact | Work |
|---|---|---|---|---|---|
| A | Caller loops over independent FeatureProducer roots | Small change | Source-after state and active-window linkage are not durably bound; a crash can replay or skip source items | Existing lower component reused, upstream recovery remains missing | Low now/high caller debt |
| B | New bounded coordinator over unchanged producers, with explicit source state in committed record metadata | Recover window order and upstream cursor/RNG from durable committed records; preserve partial/orphan artifacts | Only adapters that implement the explicit state protocol; actual teacher/model resume and source rights remain separate | New module/tests and new owned roots; no lower API/default changes | Moderate software work |
| C | Full model/optimizer/GPU online trainer and75M language production | Addresses whole research objective | Actual rights/admission and exact GPU authority are unresolved; units/quality need independent gates | Multiple runtime/data owners | High; excluded here |

Choose B. If a lower feature record is fully committed and the caller then fails, recovery must use that record's source-after boundary. A precommit payload or partial line is preserved but does not advance the committed source. This promises committed-record accounting, not exactly-once external teacher calls.

## 2. Authority and impact

| Paths | Action | Authority | Excluded |
|---|---|---|---|
| scripts/p106b_feature_schedule.py and test_p106b_feature_schedule.py | New explicit bounded coordinator/source protocol and CPU tests | User161 required implementation, original61 multi-window/source gap | Existing producer/reader/consumer defaults and actual feature/model/checkpoint changes |
| Owned audit runner/snapshots and exact newly created /tmp fixture roots | Exercise real file commits/rollover/recovery with a stateful PCG64 synthetic source | Same necessary CPU numerical/software verification | Existing source/cache/private cleanup/TinyDataset reads, deletion/rename/overwrite |
| P106B/result101/document chain/WIP/coordination | Design and bounded result recovery | User161 reporting | root09, environment, Git and external changes |

| Axis | Treatment |
|---|---|
| Code/dependencies | Reuse actual FeatureProducer/FeatureWindow validation, fsync journal commits, hashes and sealed readback. New global window linkage plus upstream state protocol only. Existing consumers still own one complete KD update/window and optimizer/RNG state. |
| Data/schema | New recipe/global append-only event schema, bounded source-boundary metadata in new records only. No old-window migration. Original supplied row metadata and FP32 arrays stay unchanged apart from a reserved new transition field in a detached copy. |
| Tests | Required actual new-root rotation, interrupted pre/post lower commit, global partial events/orphans, stale-prefix recovery, strict source state/identity/checksum, quotas, locks and immutable old bytes. Stateful synthetic source verifies cursor plus NumPy RNG replay. |
| Documents | Stage8fs/result101 plus lists/baselines/methods/COMPASS and own WIP. No new CLI/training flags or launcher. |
| Debt/priority | Exact adapter protocol is net-new; real teacher/source RNG and whole training resume still need adapters. Global storage caps stop before a hypothetical huge cache; no automatic cleanup or disk-space claim. |
| GPU/model | No model construction, checkpoint, teacher request, inference, optimizer or CUDA; preserve current approval denials and deferred package/environment questions. |
| Ownership | Only exact new owned roots are inventoried; linked/nonregular/unexpected files are refused. Orphans/partial bytes are retained and count against quotas. |
| Comparison | Same synthetic source contract/seed/row order and FP32 bytes before/after reopen. No actual source population, corpus rights, quality or throughput comparison. |
| Evidence/units | Feature rows, selected KD positions, records, bytes/files/windows and per-open elapsed time are separate. Generated/training language tokens are not counted by this component. |

## 3. Question and prediction

Does a new bounded coordinator preserve committed feature bytes/order and the source cursor/RNG across window rollover, caller interruption and fresh reopen? Expect exact synthetic replay and refusal of altered complete events, source contracts, row transitions and physical/logical quotas. Source/model side effects before a commit cannot be undone by a file cursor. No full teacher/model/training or quality success is predicted.

## 4. Stages and contract

Freeze lower source pins -> new recipe/source-boundary protocol -> explicit multi-window coordinator -> authored synthetic failure/rotation/replay controls ->1024-width bounded shape contact -> scoped recovery. Do not change lower producer/reader/consumer code or rerun their closed suites without a new failure.

An upstream adapter declares a bounded JSON contract and supplies state_dict/load_state_dict/next_feature. A boundary includes that contract hash, next_record, a source_cursor object and an rng_state object. The coordinator validates exact schema/bytes/types and verifies the adapter restores the same declared state. It does not infer a source ID, rights or actual model RNG from arbitrary metadata. Each committed new record embeds before/after boundaries with consecutive ordinals.

The coordinator owns a persistent Linux lock and a new root. Its small canonical events link window opens/closes and final source exhaustion. Each global event uses one new exclusive file; only a complete canonical newline event file commits, and later external append/truncation is outside the immutable-file contract. Each lower producer retains original commit/recovery semantics. Recovery verifies all linked windows, record transitions and source-after chain, then restores a fresh adapter at the latest committed boundary. It preserves unreferenced new-window directories, payloads and partial event tails and counts them in physical quotas. Invalid complete events stop recovery. A lagging caller checkpoint is accepted only as a verified committed prefix; current disk commits remain authoritative.

One invocation may acquire new records for at most its explicit session_seconds, bounded by28800. Check the monotonic deadline before starting each next_feature; an already-running callback can overrun it. This is a prefetch stop, not a hard8-hour cancellation guarantee. Actual external process deadlines remain a separate caller duty. Budget rejection before commit restores the supplied source boundary where possible; an uncertain write failure invalidates the object and requires fresh disk recovery. No assumption of exactly-once teacher execution.

Rollover never splits/truncates a source record or selected-position list. Preflight a record on its own, global row/feature/selected/storage quotas and capacity for closure before committing it. Sealed windows export fresh original FeatureWindow readers; active partial windows remain recoverable. Default global caps are explicit implementation policy, not evidence that all75M features can be stored. A synthetic large logical count is never called an actual8-hour run.

## 5. Judgment

Require source-boundary/NumPy RNG and selected FP32 bytes/order equality versus uninterrupted controls, exact stale-prefix proof, complete-event corruption refusal, source mismatch rejection before next_feature, no duplicate committed row IDs across windows, bounded physical/logical counts, lock exclusion and unchanged pre-existing fixture bytes. Partial/orphan bytes must remain present after recovery. All returned receipts retain corpus_admitted=false and source-only resume scope.

## 6. Cost and preflight

CPU thread1/120 seconds, existing NumPy/Torch dependencies and new small /tmp fixtures; one1024-width shape check may create a few4MiB arrays. No actual source/cache/model/teacher/GPU or installation. Tag p106b_feature_schedule_v1_20261118 has no collision, and the plan query returned no equivalent run. Training tokens0; pool/accum/sigma/quality gates do not apply. Baselines recipe/defaults stay unchanged. The check only rules out known design errors; runtime behavior still requires execution.

## 7. Execution

New owned CPU helper only; no teacher/training/production launcher or default activation. Preserve all synthetic failure artifacts instead of cleanup.

## 8. Limits

Linux flock only; Windows unverified. Only the explicit adapter's declared cursor/RNG is restored. Real Native teacher/source-state adapters, model/optimizer/GradScaler/CE and complete training resume, actual8-hour/75M production, online coexistence, corpus rights/independent evaluation and quality remain NOT_RUN. Per-window/global owned-file and array bounds are not whole-process RSS/VRAM or arbitrary external storage guarantees.

## 9. History

[101 section646](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-feature-multiwindow-source-boundary-cpu) closes CPU19, stateful synthetic cursor/PCG64 recovery and forced3-window1024-width contact. Independent9-source/382-file readback passes; old7 unchanged. Source-only byte/order/prefix/error predictions supported. Actual teacher/model/full-training/8-hour/75M/rights/quality remain NOT_RUN.
