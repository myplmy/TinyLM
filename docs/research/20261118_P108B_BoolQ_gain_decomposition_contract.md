# P108B BoolQ gain decomposition: stored-score contract

## 1. Why and alternatives

Current161/original141-142 reporting has a real prior positive:1840→1914/3270 official BoolQ accuracy,205 gains/131 losses and Holm11 p0.000704432. The current raw readback reports class counts and accuracy but no per-label prediction/recall or ranking AUC. Reusing the existing final scores can distinguish different descriptive meanings of that gain without a new model call.

| Option | Benefit | Limit | Choice |
|---|---|---|---|
| Quote accuracy/p only | Already verified | Does not separate label frequency from ranking discrimination | Retain as original result |
| Decompose the same complete stored scores | New descriptive per-label/switch/ranking evidence, no model cost | Post-hoc analysis of already opened final items | Choose |
| Rerun models or fit/select a test threshold | Could change model/prediction behavior | New model denial, test selection and a different experiment | Defer; no such action |

## 2. Authority and impact

User161 permits needed CPU/log analysis through11/18 17:00KST; the user's result request specifically asks whether there were substantive successes. Read only the two exact original report/sample-manifest/sample-shard sets and the prior OFFICIAL11_PRIMARY_READBACK. Never read referenced model/checkpoint/cache/dataset assets. New numeric audit outputs only; no source edit, generation, threshold fitting, corpus admission, environment/Git/root09 action.

The old Holm11 accuracy result remains unchanged and is separate from P108E's Holm0/33. New macro recall/F1 and AUC are diagnostic metrics, not retroactively declared task PRIMARYs or confirmatory tests. No new p-value, inferential claim, independent seed or unseen final dataset is introduced.

## 3. Question and prediction

Does the observed raw-accuracy increase accompany balanced recall and score ranking changes, and which true-label/switch counts supply the74 net correct cases? The direction of those new metrics is unknown before execution. Technical predictions are exact full3270 correspondence,1840/1914 correct and205/131 gain/loss reproduction. A rank/tie AUC must equal an independent complete positive-negative pair count as an exact rational value.

## 4. Steps

Pin seven exact original JSON/JSONL files; verify report/shard manifest SHA and0 exits. Keep full rows and input/doc/target/argument identities in the original order. Recompute primary argmax from the two original unnormalized loglikelihoods with the official first-index tie rule. Labels/choices remain no=0,yes=1. No normalized-score substitution or retokenization.

Compute true-label×prediction counts, prediction proportions, both class recalls, balanced accuracy, diagnostic macro-F1,205/131 transitions by label, and AUC of yes-score minus no-score. Use sorted tied midranks and an independent exhaustive pair count, with half credit for exact ties. Save numeric per-row IDs/hashes/scores/decisions for independent reconstruction; no question/passage text is copied into the new output.

## 5. Judgment

Fail on source SHA/schema/nonfinite/identity/order/count/argmax/accuracy/old gain-loss mismatch or unequal exact-rational AUC computations. A higher or lower new metric is an analysis outcome, not an execution failure. No winner, coefficient, threshold, training example or model default is selected from these final labels.

## 6. Cost and preflight

Stdlib CPU only, one process/thread and120-second timeout; input budget32MiB, raw lines<=64KiB, output budget4MiB.3270 rows include2033 positive×1237 negative=2514821 pairs per arm; two complete pair checks are about5.03M ordinary scalar comparisons. No Torch/Transformers/tokenizer/model/GPU/network/import installation.

Tag p108b_boolq_gain_decomposition_v1_20261118 is unused; registry plan hits have one generic term and are unrelated training runs. This is stored-result analysis, with no language-training pool/tokens/accum/sigma or new model inference. Preflight checks known design errors; actual new computation remains NOT_RUN until its original runlog/receipt closes.

## 7. Limits

Per-label recall and ranking do not establish comprehension causality, explain every weight effect, reverse the actual accuracy gain, or validate general language quality. One parent/one selected edit and passage/item dependencies remain. Test threshold calibration and training must not follow from the new diagnostic in this task.

## 8. Result

[108 section72](../../test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md#p108b-boolq-gain-decomposition) closes the computation. Original accuracy/205 gains/131 losses reproduce; no-to-yes switches contribute net75 and reverse switches net-1. Diagnostic balanced accuracy moves49.3206 to49.5263%, AUC0.506751 to0.503383. Exact rank/pair/third ROC agreement and3270-row independent readback pass. Metric direction was not predicted; comprehension/causal/generalization significance remains unclaimed.
