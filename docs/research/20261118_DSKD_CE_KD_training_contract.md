# Complete original CE rows with a bounded DSKD subset

## 1. Why and options

Current161/original61 preparation follows reader17/consumer40/producer21/multi-window19. Actual tracing found that the existing Native cost diagnostic already preserves all128 CE rows/772 targets and adds only accepted KD positions. Its historical result stays valid. The new bounded FeatureWindow contains rows with selected KD positions; using only those rows as the CE population would change the objective. The next connection must preserve the original CE order/population and independent global CE/KD denominators.

| Option | Content | Benefit | Limit | Impact | Work |
|---|---|---|---|---|---|
| A | Train CE only on rows present in the feature window | Small adapter | Drops original CE-only rows and changes the denominator/population | Scientifically invalid as the original-CE comparator | Low implementation, rejected |
| B | Explicit whole CE group plus ordered KD subset; reuse existing CE and KD functions | Retains original targets/order, bounded per-row graphs and correct two denominators | Actual Native memory/precision/quality and a concrete corpus adapter still require admission | New opt-in group/training boundary only; old code unchanged | Moderate CPU implementation |
| C | Expand the old eager Native diagnostic into the whole trainer | Reuses a historical working diagnostic | Eager feature arrays, closed source pins and model/GPU blockers remain | Changes old sealed path and runtime | High; separate actual-model stage |

Choose B. For CE rows c0,k0,c1,k1,c2 with KD only in k0/k1, all five original CE rows must contribute in that order. KD chunks can release each row's graph only after its CE term has been included. This is a software/numerical question, not a new language-quality experiment.

## 2. Authority and impact

| Paths | Action | Authority | Excluded |
|---|---|---|---|
| scripts/p106b_dskdv2_training.py | New explicit CE/KD group; gated opt-in complete-boundary trainer | User161 required implementation, original61 CE/GradScaler/resume gap | Old helpers/default trainer/model/GPU activation |
| scripts/test_p106b_dskdv2_training.py | Small newly initialized CPU numerical fixture tests | Same necessary numerical/software verification | Native/pretrained model or old checkpoint loading, language training/quality |
| Existing CE consumer, DSKD window/bridge, fixed scaled group and cpu_copy helper | Read/pin/reuse exact implementations | Same narrow preparation | Editing existing defaults, source gates or old results |
| Owned audit runner/snapshots and exact new /tmp fixtures | Bounded reference/failure/save/restore controls | Same scope | Existing data/cache/checkpoints/raw logs, TinyDataset/other cleanup, deletion |
| P106B/result101/chain and own WIP/coordination | Plan/result recovery | User161 reporting | root09/environment/Git/external state |

| Axis | Decision |
|---|---|
| Code/dependencies | Reuse p106b_actd_consumer.components with ACTD disabled for the exact original CE; NativeFeatureUpdate for KD; fixed ScaledOptimizerGroup and actual cpu_copy. Current Native _head_logits/_emb_w/_emb_up_w code was read, not executed. New grouping/boundary orchestration only. |
| Data/schema | Explicit declared original CE metadata/order and feature-window KD subsequence with matching row/root/record/source identity. New full-boundary schema must distinguish consumed groups, applied optimizer groups and skips. No old corpus/window migration or automatic admission. |
| Tests | A: independent dense FP64 full CE+KD values/gradients, CE-only prefix/middle/suffix, chunk/batch boundaries, target/owner/order/count errors and failure graph disposal. B: new tiny FP32 model, multiple optimizers, dropout/RNG, variable callbacks, zero-KD groups, overflow/partial optimizer failure and complete fresh restore. |
| Documents | Stage8fgA/B/result101 and scoped lists/baselines/methods/COMPASS/WIP. No new user training launcher or CLI flags. |
| Debt/priority | A owns loss/backward accounting only. B owns its own explicit trainer boundary. Actual Native/corpus adapter, production schedule, full-size memory/time and quality stay separate. |
| Model authority | Only newly initialized tiny numerical fixtures; no existing Native/pretrained model, weights/checkpoint load, inference, long training or GPU. Preserve prior automatic approval rejections. |
| Ownership | New bounded fixture arrays/state only. Source metadata is a declaration; root/rights/provenance/quality are not certified by matching hashes. |
| Comparison | Same exact tiny fixture, original CE labels/order/head and KD positions, independent full CE denominator and KD denominator. No language pool, token budget, sigma or real-model generalization claim. |
| Evidence | Numerical gradients/optimizer/save-restore contracts are distinct from actual student learning or deployment. No integrated preset or zero-base TinyLM training before original ledger prerequisites. |

## 3. Questions and prediction

Can bounded KD chunks preserve the independent dense gradient when all original CE-only rows remain in order? Expect tiny FP64 equality within1e-10 and exact target/order/count accounting. Can a separate CPU trainer preserve complete model/buffers, all optimizers, source, public scaler state and Python/NumPy/Torch RNG across fresh restore? Expect exact deterministic tiny-fixture states, including declared overflow consumption. No prediction of Native FP32/BF16 agreement, memory, speed, learning or quality.

## 4. Stages

### A: complete original objective and graph lifecycle

Pin old sources -> new explicit CE rows/KD subsequence preflight -> original frame validation -> existing CE sum for every row -> bounded KD callbacks, attaching that row's CE at its last KD backward -> remaining CE-only rows -> exact whole-group accounting. Require matching original identities, declared CE counts and full-frame labels/owners; no feature row is treated as the complete CE population. A failure invalidates the group; the caller must discard partial gradients/forward state. No optimizer or checkpoint ownership in A.

### B: gated complete CPU training boundary

After A numerical controls pass, add an opt-in trainer using fresh fixed ScaledOptimizerGroup instances for each declared callback count/active optimizer set. Carry only validated public scaler scalars/counters into the newly bound controller, recording that rebinding; never relabel or rewrite a historical checkpoint. A separate projector optimizer permits a zero-KD group to leave projector weights and optimizer state unchanged. Student optimizer membership stays explicit.

Overflow policy consumes the complete finite-loss group and RNG/source progression while skipping all active optimizers; attempted/applied/skipped groups are separate. Any uncertain forward/optimizer failure makes the trainer dirty until a complete explicit restore. Partial optimizer effects are not rolled back by a cursor. A full checkpoint includes model/buffers, external trainable/frozen projectors if not registered in the model, all optimizers, source declaration/cursor, scaler carry state and Python/NumPy/Torch RNG. Frozen teacher assets remain an explicitly caller-owned identity reference, not a copied or newly authenticated model. Prevalidate shapes/layout/schema/source before copying; failed restores remain dirty.

B implementation choices after A passed: preserve the closed CEKDGroup AST and existing fixed scaler byte-for-byte. A new owner stores the prior validated fixed-controller state with its declared active parameter/optimizer indices and callback count. Before the next group, validate that prior state against its own binding, construct a fresh fixed controller for the new binding, copy only its public scaler dictionary/attempt-step-skip counters into the fresh public state template, recompute the new template checksum and call its normal load_state_dict. Record old/new binding and old-state hash; never modify the original state object or old checkpoint. This handles changing callback counts without stale per-optimizer scaler stages.

The projector has a dedicated optimizer containing only that trainable matrix. A complete zero-KD group runs student optimizers alone, so projector values, decay, momentum and optimizer step count remain unchanged. The initial CPU boundary supports dense FP32 masters and fixed-LR AdamW/SGD/Muon state; actual GPU/mixed precision, sparse/fused/capturable optimizers and production scheduling are separate. Source adapters must provide a pure validate_checkpoint in addition to next_update/state_dict/load_state_dict. Save module training flags as well as state tensors/buffers. Validate RNG with local probes before copying; dirty full restores may still fail and are not atomic rollback.

## 5. Judgment

A must match independent full dense loss/gradients and retain every original CE row/target once, including rows with no KD. Wrong KD order, source identity, counts/targets/owners, frame shapes, parameter mutation or premature graph release must fail. Expected backward count must be available before execution. A emits no optimizer/full-resume claim.

B must produce exact complete-boundary state and future losses after fresh deterministic CPU restore; preserve zero-KD projector state, skip all active optimizers on injected gradient overflow and recover from partial optimizer failure only with a full prior snapshot. Existing fixed-scaler/default code remains byte unchanged. No pass admits a corpus or proves actual Native training.

## 6. Cost and preflight

Each CPU stage thread1/120 seconds, existing Torch/NumPy only, new small numerical matrices and synthetic source/state files. Tags p106b_dskd_cekd_group_v1_20261118 and p106b_dskd_training_boundary_v1_20261118 are unused; both plan queries returned no equivalent run. Actual language-training tokens0; standard pool/accum/sigma gates do not apply. Any tiny optimizer updates are numerical boundary tests, not model-quality training. No package/download/new environment/GPU.

## 7. Execution

Owned CPU helpers only, no actual model/training/teacher/production launcher. B is conditional on successful A controls. Preserve all evidence and fixtures.

## 8. Limits

Actual Native/teacher/corpus adapters, physical source or rights/independent split admission, production LR schedule, BF16/CUDA/DDP/full-size memory/time,8-hour/75M generation and student quality remain NOT_RUN. Declared teacher assets are not authenticated by the CPU fixture. Stage A is not a full trainer; stage B's technical result will not establish actual language learning or the final integrated TinyLM preset.

## 9. History

[101 section648](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-tiny-cpu-complete-dskd-training-boundary) closes A14+B10=24 CPU tests. The tiny full state/future losses/three RNGs match after fresh safe checkpoint restore; public scalar rebinding, zero-KD preservation, overflow/dirty-failure controls pass. Old16 sources/four A class ASTs remain exact. Host3.12/CPU3.10 AST preflight failure is retained and recovered with v2. Actual Native/corpus/provider/teacher/production schedule/75M/quality remain unverified.

The separate [consumed-group schedule](20261118_DSKD_consumed_schedule_contract.md) now closes10 new CPU controls in101 section649 without changing this fixed-LR owner or its tests. Actual Native/provider/teacher/75M/quality remain unverified.
