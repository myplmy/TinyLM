# P108B stored-score sensitivity to observed dependence groups

## 1. Question and alternatives

Original141-142/current161 requires an accurate account of actual gains. Closed108 sections72/73 leave item dependence unresolved. The outcome-free census found BoolQ3270 rows/2939 exact-passage groups and HellaSwag10042 rows/8407 exact typed-source_id groups. This is a new uncertainty calculation on old scores, not a repeated model evaluation.

| Option | Benefit | Limit | Decision |
|---|---|---|---|
| Keep only old item-level paired tests | Preserves original results | Does not examine observed shared fields | Preserve as original evidence |
| Paired resampling of entire observed groups | Retains pairing and within-group rows | Group independence and semantic roots remain unproved | Choose as exploratory sensitivity |
| New held-out models, independent seeds or original-source roots | Could support broader inference | New model launch is denied; original roots are not established | Defer, do not invent roots |

## 2. Authority, impact and sources

User161's CPU research window ends11/18 17:00KST. Read only the current owned closed numeric audits, their receipts and outcome-free mappings. Do not reopen models, checkpoint tensors, tokenizer/features, corpus caches or protected/private data. No old raw/score/receipt is modified. New write-once runner, before pins, source snapshot, CPU runlog, numeric replicates and result section belong to the current audit.

| Project impact axis | Bound |
|---|---|
| Execution authority | Existing NumPy CPU1 only; no model/Torch/GPU, download or installation |
| Ownership | Seven exact owned JSON/JSONL inputs; no referenced assets or other owner content |
| Comparison | Same old parent/edit, same full rows/labels/PRIMARY; same group draws for both arms |
| Evidence | Exploratory uncertainty on stored predictions, not a new quality run or adoption |
| Document chain | P108 stage/result108, result list, baseline/METHODS/COMPASS, living report and WIP161 |

Resampling entire clusters is described by [Cameron and Miller2015](https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015.pdf). The index-pairing and percentile conventions are documented by [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html); this runner uses existing NumPy, not SciPy or a new install. These sources do not certify the observed dataset groups. The [HellaSwag author page](https://rowanzellers.com/hellaswag/) and [original paper](https://arxiv.org/abs/1905.07830) describe ActivityNet/WikiHow sources but do not by themselves prove source_id is the independent original article unit. Same-ID grouping is an explicitly limited inference. A direct repository request returned HTTP451; no mirror/raw-route bypass is used.

## 3. Fixed grouping and estimands

Use exact mapping hashes from OBSERVED_EVAL_GROUP_FIELD_CENSUS_v1.json. BoolQ uses the unmodified passage text; HellaSwag uses the exact typed JSON source_id. No outcomes choose groups; missing keys stop the analysis. Match every mapping doc_id/doc_hash to the closed numeric row. Group order is first occurrence. Unique keys do not certify independent semantic roots, rights or splits. Winogrande is excluded because no defensible original shared-source key was established.

Fixed family: BoolQ edited-minus-original PRIMARY accuracy, balanced accuracy, macro-F1 and yes-minus-no score AUC; HellaSwag edited-minus-original PRIMARY acc_norm, balanced accuracy and macro-F1. Seven diagnostics, with no additional selected endpoint. Preserve all old PRIMARY counts, old Holm11 p-values and night P108E0/33. No threshold fitting, final-label training or model selection.

## 4. Resampling contract

For each task draw G groups with replacement, carrying all rows in each sampled group. Do not sample rows within a group. Use the same cluster multiplicities for both arms and all task metrics. The number of rows can vary; recalculate ratios/confusion/label denominators and weighted AUC on each resample. Preserve ties with half credit. AUC weights are the product of positive and negative row multiplicities.

Use100000 replicates, batch32, independent task streams NumPy PCG64 with SeedSequence([1337,108,task_index]), task_index0 BoolQ/1 HellaSwag. Fix initial/final RNG state and save all seven replicate columns. Report percentile95% bounds and a second, nominal Bonferroni7 diagnostic bound with tails0.05/(2*7),1-0.05/(2*7), NumPy quantile method linear. The latter is an approximate bootstrap sensitivity summary, not certified family coverage or a new confirmatory test. No resample is silently dropped/redrawn; absent labels or nonfinite values fail.

## 5. Numerical gates and resources

Before the full calculation require: all-one group weights recover both closed confusions/point metrics; three fixed integer multiplicity probes match independently expanded rows; binary AUC also matches independent weighted exhaustive pairs; synthetic tied-score oracle agrees; and a fixed64-draw RNG prefix is unchanged by batch partition. These are estimator checks, not language-quality successes.

Single CPU thread,300s timeout, existing Python3.10.19/NumPy2.2.6. Input cap16MiB, new numeric output cap8MiB, designed working-array budget128MiB. The budget is not measured process RSS; record actual Linux process peak RSS separately. The largest conservative row count is2939*9=26451/8407*10=84070; integer moments are below2**53 for exact float64 accumulation. No whole-corpus or large-matrix/model calculation. Tag p108b_observed_cluster_bootstrap_v1_20261118 was absent in the registry query; there is no matching prior diagnostic.

## 6. Interpretation and recovery

Direction and interval exclusion are unpredicted. A positive, null or negative diagnostic is a result; do not change the protocol to obtain a desired direction. Save distributions/mean/SD/extremes/histograms, with all100000 finite replicates. Retain failures and use a new version for recovery. Independently read saved NPY files and recalculate interval summaries before closing result108.

Already opened final items, a selected edit, unproved cluster independence, unequal group sizes, possible dependence across different keys, and no independent training seeds remain. Observed-group sensitivity cannot prove comprehension, original-root inference, generalization, equality, deployment or a new improved TinyLM.

## 7. Execution status

[Result108 section74](../../test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md#p108b-observed-group-bootstrap-sensitivity) closes the predeclared CPU calculation07:01:53KST/exit0. All100000 paired resamples per task/seven saved diagnostic summaries pass independent numerical readback, without a full rerun. This remains approximate post-hoc observed-group sensitivity, with no new model or original-root certification.
