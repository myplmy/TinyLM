# DSKD batched frames in the complete scheduled CPU training owner

## 1. Remaining original work and alternatives

Original61/current161 needs the separately closed CausalMicrobatchFrames to reach complete optimizer/scaler/LR/source/save-resume ownership. This stage connects that path in a numerical CPU fixture. Later explicit GPU authorization and the Bonsai/Reading evaluations belong to their own run records.

| Option | Benefit | Limit | Impact | Cost |
|---|---|---|---|---|
| Duplicate the full step/checkpoint owner | Avoids editing the old class | Duplicates rollback/scaler/LR invariants | New parallel owner with drift risk | High maintenance |
| Add one protected group-consumption hook and a separate opt-in subclass | Reuses complete owner/state rules and preserves the default call path | Requires relevant old-owner regressions | One controlled old-source delta plus new module/test | Medium; choose |
| Global monkeypatch of CEKDGroup/provider/backward | Small apparent edit | Hidden process-wide behavior, unsafe simultaneous owners and opaque contracts | Runtime-global mutation | Unacceptable technical debt |

Choose one protected hook. A default row-provider owner continues the same group.consume/provider/controller callbacks. Only the new subclass consumes a typed packed-token update through the batch-frame adapter. Do not retrofit a declared batch policy into old checkpoint semantics.

## 2. Exact authorization and impact

| File/path | Action | Authority | Excluded |
|---|---|---|---|
| scripts/p106b_dskdv2_training.py | Add _group_consumer(group,update) factory before controller setup; replace only inline consumption with its returned callable | User161 required original61 implementation | No CEKDGroup/optimizer/scaler/load contract changes |
| scripts/p106b_dskdv2_microbatch_training.py and test | New typed update and explicit scheduled CPU subclass/oracles | Same current CPU implementation scope | No Native loader/default/CLI/GPU |
| Current audit, P106B/result101/document chain/WIP | Before/after source proof, new result recovery | Current recoverable research/report | Old raw/audit/CP, root09, other owners unchanged |
| Existing adapters/scheduler/regression sources | Read/pin; run only affected owner tests | Necessary validation after a real owner delta | No unchanged CEKD14 or batch-frame8 suite rerun |

| Axis | Bound |
|---|---|
| Code | One old file/method extraction; source AST must show unchanged CEKDGroup and every other old method. New protected hook defaults to the exact previous callbacks. New subclass owns typed packed updates and its own checkpoint envelope. |
| Data | New in-memory tiny token/feature fixtures only. No real corpus/cache/old features/checkpoint/tokenizer, model admission or migrations. Source contract explicitly declares raw packed policy and source-owned private RNG. |
| Tests | Affected old ScaledFeatureTrainer10 and ScheduledFeatureTrainer10 regressions are warranted by the extracted hook. Add focused batched full-update/manual reference/resume/overflow/dirty-restore/schema tests. |
| Documents | Plan/result/baseline/METHODS/COMPASS/lists/report/WIP and provider-review supplement. Historical old25-byte-unchanged report remains true for its completed phase; this new phase changes one recorded old source. |
| Debt | Reuse actual complete CPU owner rather than a copy. Typed update has no file/model loader. Actual Native source/teacher/RNG/data admission and future GPU costs remain separate. |
| Execution scope | Numerical CPU fixtures for this stage. Actual Native and GPU evaluation use their own plans and admission. |
| Ownership | All fresh numerical outputs retained in a new audit root; checkpoint loads accept only files freshly created by this run with weights_only. Old regression temporary outputs are redirected to that owned root by a location-only fixture wrapper. |
| Comparison | Same complete CE rows, KD subset selection, model initialization, source/RNG, active optimizers, clipping and consumed LR in manual/owner pairs. |
| Evidence | Small numerical steps, not student-language training or quality/adoption. Real source edits justify exactly scoped regressions; no test-count success inflation. |
| Closure | Preserve pre-edit source and record the one allowed AST delta. New write-once raw/receipt/numeric checkpoint evidence; no old result/run rewrite. |

## 3. Implementation contract

The base _group_consumer factory returns a controller-taking callable with the previous group.consume lambdas verbatim and does not change the public signature/state schema/default behavior. Bind that callable before controller/LR setup, then invoke it at the former inline consumption site. This lets the new subclass validate packed values before any LR mutation. Keep CEKDGroup and all optimizer/source/RNG/scaler/LR implementations unchanged.

PackedFeatureTrainingUpdate extends the existing immutable update with supplied raw packed student values. The new source contract must explicitly identify this update type and raw-token-count/once-shift policy. The new CPU subclass constructs a single-use CausalMicrobatchFrames for each complete group, routes its effective retain_graph to the existing controller, and returns group accounting plus the batch audit. No adapter graph/private cursor persists across healthy update boundaries. Source/private RNG is still explicitly owned by the source; arbitrary teacher/model state is not certified.

Preserve the inherited scheduled active-optimizer policy, consumed-group overflow clock and dedicated projector optimizer. A zero-KD group preserves projector values/moments/steps/LR. Failed consumption remains dirty and needs a complete restore; source/global RNG restoration alone is not full rollback. No optimizer mutation before all group backward callbacks finish.

Use a distinct outer batched-scheduled checkpoint envelope with exact batch/pad/raw-token/graph policy and the unchanged scheduled boundary inside. Reject old row-only envelopes, changed batch policy or packed update shape/identity. No historical checkpoint migration. Parent scheduled/base validators still own every complete model/buffer/projector/optimizer/source/scaler/global-RNG check. Fresh test model/source objects must recover identical future reports/rates/state; no runtime object graph is serialized.

## 4. Numerical gates and cost

Fresh55-variable FP32 token fixture, fixed batch8/width8/17 real rows, source-selected KD subset and explicit source-local Python RNG, dropout/nonreentrant checkpoint as needed. This is no language dataset or actual Native architecture. Run only the20 affected old owner/schedule regressions, not unchanged CEKD14 or adapter8. Freeze new test count/source after implementation, before execution.

New gates: unscaled manual same-batch complete updates against scaled scheduled batch ownership; zero-KD projector state including LR; consumed overflow skips all active optimizers; source-local/global RNG and full fresh-object save/resume; schema/policy/typed-update rejection before mutation; partial-forward/gradient failure dirty state and complete restoration. Exact resume uses bit equality. Independent manual-update comparisons allow parameter/moment atol3e-6/rtol5e-5 and loss/gradient atol3e-5/rtol3e-4, fixed before running. No corpus/sigma/quality inference or tuning for a desired result.

Existing Python3.10/Torch2.10 CPU1/180s. New output cap4MiB/256files; new bounded numerical checkpoints only. Pin the old27 adapter/training sources before edits. Expected allowed code delta is one old source; old CEKDGroup AST and other owner methods stay equal. New tag p106b_dskdv2_microbatch_training_cpu_v1_20261118 must be unused in registry before execution. Actual Native micro8/1024/BF16/production teacher/private state/cost and admitted TRAIN/75M/full student quality stay NOT_RUN.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 5. Status

CPU evidence closed across two executions. Twenty affected owner checks and five new checks passed in v1, which exited 1 on the string optimizer setting. The v2 retry compared optimizer settings exactly and retained the original numerical tolerance for tensor moments. It passed the remaining manual-update check with the same product code. Fresh checkpoint restoration matched the next four groups and complete state exactly. Actual Native and admitted production training remain open. [Result 101 §652](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-dskd-batched-scheduled-training-cpu)
