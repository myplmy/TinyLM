# Complete optimizer-group loss scaling

## 1. Why

Current161 authorizes original58/59 required implementation. P107 has causal/MNTP losses, adaptive statistics, schedule and completed-boundary restore, but no GradScaler contact. Preserve historical P107 sources and test a separate numerical component first. Installed torch is2.10.0+cu130; read its actual amp/grad_scaler.py and [version2.10 AMP examples](https://docs.pytorch.org/docs/2.10/notes/amp_examples.html).

Keep a constant scale while accumulating, unscale each optimizer once before clipping and update once after the group. Official multiple-optimizer examples permit separate skip decisions. This component adds an explicit complete-group finite gate. Its global skip is an extension, not an exact reproduction of independent skips. Installed load_state_dict does not reset per-optimizer stages, so restore public state into a fresh owned scaler.

| Option | Work | Benefit | Limit | Impact/cost |
|---|---|---|---|---|
| A | Multi-window/source-cursor producer | Extends producer21 | Actual source/teacher RNG and whole scheduler remain separate | Medium/high |
| B | Separate scaled optimizer-group controller | Verifies accumulation, all-group overflow rejection and fresh-scaler restore without model/data | P107 source/policy/schedule skip semantics remain separate | Medium |
| C | Wait for Native execution | No new source | Independent numerical contact remains absent | Low |

Choose B. If auxiliary gradients overflow, skip both auxiliary and matrix steps before any parameter update. An arbitrary later optimizer exception can still leave earlier parameters changed; mark the controller failed and require external full restoration.

| Files/paths | Action | Authority | Excluded |
|---|---|---|---|
| scripts/p107_scaled_optimizer_group.py and test_p107_scaled_optimizer_group.py | New controller/CPU contracts | Current161/original58/59 | Native/CP/corpus/GPU0 |
| Installed amp source/P107 trainer/session | Read/hash | Same narrow verification | Library/P107 source mutation0 |
| P107/result107/lists/baselines/methodology/COMPASS/own WIP | Narrow plan/result synchronization | Current161 recovery duty | root09/Git/environment0 |

| Axis | Treatment |
|---|---|
| Code | No model load, autocast policy, data or scheduler control; new explicit component only. |
| Data | Newly initialized small FP32 parameters and optimizer states; old checkpoint/feature/dataset reads0. |
| Tests | Independent unscaled update, accumulation/clipping, all-group overflow skip, growth/backoff, fresh checkpoint restore, malformed state and partial-step failure. |
| Documents | Preserve historical P107 results and distinguish remaining Native/GradScaler integration. |
| Debt/order | Caller still decides source/policy/schedule progress after a skip. No production trainer claim. |
| GPU | Existing approval-review denials remain; CPU GradScaler/parameters only. |
| Ownership | Installed source read-only, new files/own audit; protected/other cleanup/raw-log mutation0. |
| Comparison | Same synthetic values/objectives/optimizer settings/clip; no quality or AMP speed claim. |
| Evidence | Global finite rejection is not rollback of arbitrary optimizer errors. Controller state omits model/optimizer/source/RNG. |
| Chain | Pin exact sources/raw evidence; keep defaults and old training outcomes unchanged. |

## 2. Question

Does one scale cover all accumulated losses before complete unscale/finite checks/clip, all-step or all-skip, one scale update and clean-boundary fresh-scaler restore?

## 3. Prediction

Expect finite power-of-two scaling to preserve a synthetic independent FP32 update within explicit tolerance. Inf in either optimizer should skip both. Fresh scaler restore should prevent stale optimizer-stage errors. No Native quality/acceleration prediction.

## 4. Stages

Exclusive complete FP32 ownership/support checks -> fixed-scale backward accumulation -> unscale all once -> global finite gate -> clip/step all or skip all -> update once/clear gradients -> clean checkpoint. Restore a matching run/layout into a fresh controller/scaler only.

## 5. Judgment

Require finite reference/overflow no-step checks and exact ownership. Reject mid-group/failed export or restore. Any optimizer exception requires caller-owned full restoration. Source/policy/schedule decisions remain unimplemented.

## 6. Cost

CPU thread1/120 seconds; small synthetic FP32 parameters and installed PyTorch2.10 only. Language tokens/model loads0. CUDA/NCCL/fused/capturable/differentiable optimizers and whole-training memory are not admitted.

## 7. Execution

Tag p107_scaled_optimizer_group_v1_20261118 collision check passed. CPU raw evidence belongs to result107; no GPU/training launcher.

## 8. Limits

Not yet connected to P107 source/policy/scheduler, actual Native/Muon training, distributed/FSDP/compile or full model/optimizer/RNG resume. BF16 does not automatically need scaling or imply a gain. CPU2.10 proof does not certify another release/device.

## 9. History

Read installed scaler source/signature and P107 update/state owners. New execution NOT_RUN. Known design checks and actual scientific outcomes remain separate.

Execution recovery: [107 section19](../../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-scaled-optimizer-group-cpu) closes14 CPU contracts. Finite reference, all-group overflow skip and fresh public scaler restore predictions were supported. P107/source/policy/schedule/Native integration and quality remain NOT_RUN.
