# DSKD original causal microbatch frame adapter

## 1. Purpose and three alternatives

Original61/current161 leaves the actual StudentFrame provider unconnected. The old diag_p106b_dskdv2_bridge.py:student_cost constructs16 microbatches of8 rows and backward once per microbatch. The closed CEKDGroup owns one row at a time and sets retain_graph=False when that row ends. Passing eight slices of one shared forward graph directly to that row policy is therefore a distinct, untested integration risk. This finding is from source tracing, not a new Native failure.

| Option | Benefit | Limit | Impact | Cost |
|---|---|---|---|---|
| Forward every row separately | Fits the existing row contract | Changes original batch geometry/RNG and cannot certify batch8 | No old code change, wrong intended comparison | Low, but would need later replacement |
| Separate single-use microbatch frame/backward adapter | Keeps original fixed batch/shift and releases the shared graph after its last real row | More backward traversals than old summed-loss code; actual Native tolerance/cost unmeasured | New opt-in module and focused numerical tests only | Medium; one new graph-lifetime boundary |
| Replace the original consumer and full trainer with a batch-loss owner | Could backward once per original microbatch | Larger change to closed optimizer/scaler/LR/resume contracts; holds more loss graphs | Several old owners and schemas | High; not justified for this gap |

Choose the separate adapter. For example, when row0 and row1 share one eight-row hidden tensor, ending row0 must not free the body graph needed by row1. At the last supervised real row of that microbatch, release it before the next forward can refresh a TLinear quantized cache. Do not silently change the old row-only owner's meaning.

## 2. Allowed files and authority

| File/path | Planned action | Authority | Excluded |
|---|---|---|---|
| scripts/p106b_dskdv2_microbatch.py | Add explicit opt-in adapter | User161 needed implementation for original61 | No loader, dataset, CLI/default changes |
| scripts/test_p106b_dskdv2_microbatch.py | New tiny numerical oracles | Same current161 CPU work | No pretrained/Native model, old tensors or old data |
| Current owned audit, P106B, result101 and document chain | Before pins/new runlog/results/WIP | User161 recoverable research/report | No old raw/audit rewrite or root09 |
| Existing loss/trainer/LR/Record/model sources | Read and pin | Needed implementation analysis | Do not modify old owners, production trainer or environments |

## 3. Impact analysis

| Axis | Finding and bound |
|---|---|
| Code | Existing StudentFrame/CEKDGroup and pad_records are reused. No non-test production provider usage was found in the checked scripts. New consume wrapper owns batched forward and backward retain policy; no optimizer/scaler integration is claimed. |
| Data | Accept supplied in-memory original student packed ids/labels/turn_ids and exact ordered CE metadata. Validate and shift exactly once; no tokenizer/corpus/cache access or migration. |
| Tests | New shared-graph, fixed-batch, shift/owner and dense-gradient oracles are necessary; old reader/consumer/scaler suites are not rerun. |
| Documents | P106B stage/result101, baseline/METHODS/COMPASS, lists, living report/WIP and the old provider review supplement. No environment workflow edits. |
| Debt/priority | An opt-in part of original61, before presets. It does not attach to ScaledFeatureTrainer or claim full source/teacher/RNG/resume ownership. A later real integration must measure row-wise backward order/cost. |
| GPU authority | Existing Torch CPU only; actual Native/model/GPU launch remains denied and is not bypassed. |
| Ownership | New scalar/tiny synthetic values/features only. No existing checkpoint/feature/TinyDataset/other-owner access. |
| Valid comparison | Same model initialization, packed rows, fixed batch8/padding, objective/denominators and RNG in the reference and adapter. No language-quality inference. |
| Evidence | Numerical adapter success differs from actual Native compatibility, full training, language quality or adoption. |
| Source chain | Immutable before pins/snapshot and one new write-once runlog/receipt; source defaults remain unchanged. |

## 4. Exact token/frame policy

Require raw student ids/labels/turn_ids with equal lengths, ignored first raw target, supervised labels equal their raw token IDs and positive owners exactly on supervised positions. Metadata student_tokens explicitly means raw token count, not shifted-x length. Set x=ids[:-1],y=labels[1:],owners=turn_ids[1:] exactly once, then call the existing pad_records with explicit fixed width and batch size. Require exact row order/IDs/root/SHA declarations/CE target counts; create a separate hash for supplied packed-token values without claiming the declaration authenticates an original document or admission.

Retain one fixed-size forward's hidden/targets/owners and shared graph at a time. Same microbatch includes zero-loss dummy rows in a short last batch. Return original full-width StudentFrame slices without detach/recompute. No extra loss normalization. A backward context retains the graph until both the last real row and its final KD/CE chunk end. Do not forward the next microbatch before that point. Check supported quantized-cache tensor identity/version and frame versions before/after backward; reject parameter/cache mutation or unsupported frozen/update/unpack cache modes. Release owned references on completion or failure; do not claim model-owned caches, gradients or arbitrary external state were restored.

No private RNG or persistent provider cursor is introduced. Native model/private RNG, source state, hybrid modes and checkpoint transactions remain separately owned. The single-use adapter exposes no resume/checkpoint claim. The old CPU complete trainer is unchanged and does not automatically call this new adapter.

## 5. Numerical experiment and preflight

Independent variable: a batch-aware shared-graph lifetime wrapper versus manual dense fixed-microbatch backward on the same tiny fresh token model. The model intentionally includes a small batch-coupled operation so accidental row-by-row forwarding changes the reference. This is a numerical stress fixture, not the TinyLM architecture or language data.

Use batch8/width8 and17 ordered raw token examples, with three actual padded microbatches; mixed CE-only/KD rows and feature chunks cross both row and microbatch boundaries. Include FP64 and FP32/dropout/nonreentrant checkpoint cases, manual full-vocabulary DSKD sums, no optimizer update. Predetermined tolerances: FP64 gradient/loss atol2e-10,rtol2e-9; FP32 atol3e-5,rtol3e-4. Require all trainable gradient tensors including the forward projector when KD is active; frozen teacher/reverse remain gradient-free and all parameters unchanged. These are technical tolerances, not a sigma or a language-quality gate.

Expected invalid plain row-level graph freeing must fail in a caught negative-control test. New guards must fail before forward for invalid one-shift identity/owner/token/count metadata; failures during consumption invalidate both group and adapter, release owned graph references and reject reuse. Check original full microbatch counts/shapes, dummy padding, CE/KD denominator/order, within-batch graph retain flags, final graph release, checkpoint/dropout RNG and quant-cache replacement.

CPU1/120s, Torch2.10/Python3.10 existing environment; fresh parameters under1000, no actual Native/pretrained construction or weights. New synthetic feature/test artifacts under the owned audit, cap8MiB/128files; no deletions or overwrites. No packages/new environment/network during execution. Unused tag p106b_dskdv2_microbatch_frames_cpu_v1_20261118; no equivalent prior graph/batch adapter found. Model language tokens/steps and corpus pool are not applicable; no full-training budget claim. Old native micro8/accum16 values are intended future comparison conditions, not this tiny run's executed model training.

This preflight catches known design mistakes only. Numerical success cannot predict actual Native compatibility, speed, memory or quality.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 6. Primary technical references

[PyTorch2.10 backward](https://docs.pytorch.org/docs/2.10/generated/torch.autograd.backward.html) describes graph freeing and gradient accumulation. [PyTorch2.10 checkpoint](https://docs.pytorch.org/docs/2.10/checkpoint.html) describes recomputation/RNG and warns that changed function state can produce incorrect gradients. These support the graph/cache risk; they do not establish this adapter's correctness or any real model result.

## 7. Status and remaining boundary

[101 section650](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-causal-microbatch-frame-adapter-cpu) closes the separate adapter in8 new CPU tests/exit0 and independent full tiny-gradient/file readback. Original25 sources are unchanged. The wrapper uses more row/chunk backwards than the old summed microbatch and has not measured Native cost; no full trainer/resume, actual Native or quality adoption. Actual Native micro8/1024/BF16/TLinear/checkpoint numerics and full cost, source/provider/scaler/LR/resume integration, admitted TRAIN/teacher rights, online/offline state,75M/full student training and quality remain unfinished. A numerical pass will not close original61 as a whole.
