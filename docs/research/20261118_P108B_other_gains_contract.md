# Stored Winogrande and HellaSwag gain decomposition

## 1. Why and alternatives

Current161/original141-142 reporting found that the earlier BoolQ accuracy gain mostly accompanied a yesward shift without improved observed ranking. The same prior official11 has two other small PRIMARY increases, Winogrande635→646/1267 and HellaSwag2765→2780/10042. Existing readback has correctness/paired tests but no complete per-choice confusion. Their interpretation is a new unresolved question, not a reason to rerun closed BoolQ or models.

| Option | Benefit | Limit | Decision |
|---|---|---|---|
| Reuse only old aggregate accuracies | Preserves original evidence | Leaves choice distribution and task-specific scoring unexplained | Keep as owner |
| Read complete old score dumps for these two tasks | New per-choice/recall/switch evidence, CPU only | Post-hoc final-item analysis | Choose |
| Generate new model answers or tune a threshold | Could test new behavior | Model denial and final-label selection boundary | Defer |

## 2. Authority and impact

User161 permits needed original-result CPU analysis through11/18 17:00KST. Exact old report/manifest/sample shards and three local official-metric code owners are read/pinned only. No referenced dataset/cache/model/checkpoint/feature is opened. New numeric summaries/rows live under the current owned audit. Preserve original PRIMARY/Holm11; diagnostic macro recall/F1 and binary ranking do not become new task PRIMARYs or confirmatory tests. No threshold fit, final-label training/model selection or new prediction.

## 3. Task definitions and predictions

Winogrande is multiple-input: doc_to_choice builds two sentence prefixes by replacing the underscore with option1/option2, doc_to_target is the same trailing sentence string, and the gold index is answer1→0/2→1 from doc_to_text. A raw saved target string is therefore not the binary label. PRIMARY is unnormalized acc.

HellaSwag uses the processed doc.choices and integer label. PRIMARY is acc_norm: each original loglikelihood is divided by len(original_processed_choice) in Python characters, not continuation token count, UTF-8 bytes or the request string with its leading delimiter. Reuse the rule owned by scripts/p106b_official_tasks.py and the existing independent readback; do not import their model/dataset loader chains.

New metric direction is unpredicted. Technical gates must recover full1267/10042 correspondence, old635/646 and2765/2780 PRIMARY counts, old Winogrande66/55 and HellaSwag206/191 gain/loss counts, and every saved raw acc/acc_norm decision. Rank and exhaustive-pair AUC for binary Winogrande must match exactly. HellaSwag uses per-choice recall/confusion, with no new multiclass AUC definition.

## 4. Steps and judgment

Pin exact inputs/code -> stream paired complete shards and verify raw/concat SHA/order/identity -> reconstruct task requests/choices/gold -> reproduce PRIMARY -> per-choice confusion/prediction counts/recall/macro-F1/transition accounting -> independent numeric readback -> result recovery. Fail on drift/identity/schema/nonfinite/count/decision mismatch. A small, absent or negative new diagnostic effect is an outcome, not an execution failure. Preserve all old p-values and their one-parent/item-dependence limits; no new significance test.

## 5. Cost/preflight

Stdlib CPU1/120s, exact input limit128MiB and64KiB per raw line, new numeric output limit12MiB. Two tasks×two arms22618 rows; Winogrande has628×639 pairs per arm. No Torch/tokenizer/model/GPU/network/package/environment. Tag p108b_other_gains_decomposition_v1_20261118 is unused and registry plan hits have one unrelated generic term. No new language pool/tokens/accum/sigma comparison. Preflight can reject known design errors only; execution NOT_RUN until new receipt/runlog.

## 6. Limits/result

Already opened final items and one selected edit. No semantic understanding cause, random-equivalence proof, independent seed/generalization or new trained/deployed model. New ranking for Winogrande concerns option ordering, not BoolQ yes/no semantics. [108 section73](../../test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md#p108b-other-gains-stored-primary-decomposition) closes the complete old-score analysis in v2/exit0. V1 compared four process-local fewshot function address reprs and failed before score rows; the exact diagnosis/original failure and a detached-view-only recovery are preserved. All task PRIMARY/old counts and independent numeric/ROC checks pass. Metric point gains remain descriptive and old Holm p1.0; no new model or broad quality adoption.
