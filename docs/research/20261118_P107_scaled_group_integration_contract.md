# P107 explicit consumed-group overflow policy and CPU trainer contact

## 1. Why

Current161/original58/59 authorize required implementation after standalone107 section19 CPU14. Existing source/policy/session owners are adaptive_training.py, adaptive_masking.py, document_source.py and hybrid_session.py. Preserve their historical exact-resume evidence. Only the opt-in adaptive trainer and standalone controller validation contact need edits.

| Overflow policy | Behavior | Benefit | Cost/limit |
|---|---|---|---|
| A: replay | Rewind source/RNG/policy and restore all forward-mutated state before replay at a lower scale | Same group retried | Requires a complete forward-state transaction/buffer/cache contract; more coupling |
| B: consume | Complete finite-loss observation group, advance source/policy/schedule cursor, record optimizer skip separately | Fits existing consumed-input/session progress with explicit distinct counters | Fewer optimizer steps than logical groups when overflow occurs; must report both |
| C: abort | Stop and require external full restore/new profile | Conservative failure | No ordinary dynamic overflow continuation |

Choose B, as an explicitly required opt-in value `CONSUME_GROUP_COMMIT_FINITE_OBSERVATIONS_ADVANCE_SCHEDULE_V1`. Default None has no new behavior or state keys. Each enabled cursor counts consumed groups, not successful optimizer steps. Finite observations may update adaptive statistics even when gradients overflow; buffers/RNG and source follow the consumed forward work. Invalid/nonfinite loss and arbitrary optimizer exceptions remain failures requiring complete external restore.

| Files/paths | Action | Authority | Excluded |
|---|---|---|---|
| tinylm/train/adaptive_training.py | Optional factory/protocol/scaled state/explicit overflow contact | Current161 required implementation/original58/59 | Default None loss/state changes, Native execution |
| scripts/p107_scaled_optimizer_group.py | Pure checkpoint validation/contract accessor, preserving standalone behavior | Same contact integration | Library changes and automatic source policy |
| scripts/test_p107_scaled_integration.py and owned audit helpers | Synthetic CPU default oracle/overflow/schedule/KD/restore tests | Same required verification | Pretrained/Native instances, protected data/old CP/actual GPU |
| Exact owned source snapshot | Preserve before bytes/hash and None-default oracle | Same reversible research work | Old audit/cache/source archives unchanged |
| P107/result107/document chain/own WIP | Narrow result recovery | Current161 reporting | root09/Git/environment mutations0 |

| Impact axis | Treatment |
|---|---|
| Code | Existing source has eleven adaptive CPU contracts and separate causal-KD tests. Add optional controller factory with exact parameter/optimizer/run binding. Keep policy/session defaults unchanged. |
| Data/state | New schema only when enabled; include controller contract/state and explicit overflow policy. Validate scalar controller checkpoint before copying model state. Rebuild a fresh controller after full caller-owned model/optimizer restore. |
| Tests | Freeze before source and four-update loss/full-state hash oracle. Check default None equivalence, finite opt-in equivalence, consumed overflow/source/policy/buffer progress, scheduler counters, causal-only KL, fresh resume after skip and invalid-state no-copy. |
| Documents | Existing P107 source hashes become historical for the intentionally changed file. Preserve exact before snapshot, old results and current version distinction. |
| Debt/order | Native/CUDA/GradScaler performance, actual corpus/75M streaming/quality and compile remain unverified. |
| GPU authority | No GPU/model/old checkpoint execution. Tiny newly initialized CPU fixtures only. |
| Ownership | No other cleanup/protected corpus, installed package or old raw-log changes. No deletion/Git. |
| Comparison | Same seeded synthetic inputs/dropout/masking/optimizer settings. None-state bit hashes and exact synthetic resumed states do not certify Native quality. |
| Evidence | Logical groups/source observations and real optimizer steps/skips are separate fields. No automatic optimizer-exception rollback is claimed. |
| Chain | New raw logs map to a new result107 section with before/current sources and non-adoption limits. |

## 2. Question

Can an explicit consume-group policy bind the validated scaler to P107 without changing None defaults, preserve source/policy/session/scaler state across CPU resume and distinguish skipped optimization from completed input work?

## 3. Prediction

Expect old None loss/targets/full-state hashes unchanged. Finite scaled synthetic updates should match unscaled controls within FP32 tolerance. On overflow, parameters/optimizers stay unchanged while source/policy/forward buffers/cursor advance once; the next update and a resumed update should match. These are synthetic software predictions only.

## 4. Stages

Freeze old source/None oracle -> pure controller checkpoint validator/contract -> explicit optional factory and bound complete-group policy -> new enabled checkpoint schema -> CPU default/finite/overflow/KD/schedule/restore and related adaptive regressions -> new result closure.

## 5. Judgment

Reject an enabled path without the exact policy and matching factory ownership/run/number of micros. Require None-default equality and overflow/source counter assertions. Malformed controller state must fail before copying weights. Failures stay dirty until full restore; rebuild the controller rather than reusing stale scaler optimizer stages.

## 6. Cost

CPU thread1/120 seconds, small random document/parameter fixtures only. No real corpus or language-training claim. Native class construction is forbidden during the CPU suite. Existing BF16 defaults are unchanged; no package/installation/new environment.

## 7. Execution

Freeze the new before-source/None oracle in the owning audit namespace, then run the exact new CPU suite. No Native/GPU launcher. New tag p107_scaled_trainer_v1_20261118 must pass registry collision preflight before execution.

## 8. Limits

None-default/state and synthetic CPU proofs are not actual Native/Muon/large teacher, CUDA/FSDP/compile or language quality. Consuming overflow groups changes the relation between input groups and optimizer steps; quality comparisons must disclose both. Unregistered opaque forward side effects and full-source data admission are not certified.

## 9. History

Standalone CPU14 is closed; existing product/source owners were read. Trainer integration was NOT_RUN at design; execution recoveries below own the later evidence.

Execution recovery: [107 section20](../../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-scaled-trainer-consumed-group-cpu) closes old-source oracle and CPU50. None loss/target/state hashes, explicit consumed/optimizer counters and fresh CPU restore predictions were supported. Actual Native/large teacher/BF16-CUDA/CLI/75M quality remain NOT_RUN.

Final recovery: result107 section20.1 closes CPU51 after explicit CPU scalar normalization under a meta default device. Current source11 is pinned separately; the first14/50 snapshots remain historical. Native/CUDA/quality limits stay unchanged.
