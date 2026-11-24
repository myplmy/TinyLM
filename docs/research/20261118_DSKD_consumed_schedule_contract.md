# DSKD consumed-group learning-rate schedule contract

## 1. Original gap and alternatives

Current161/original61 follows the closed [A14+B10 CPU boundary](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-tiny-cpu-complete-dskd-training-boundary). That owner intentionally pins fixed optimizer settings, including LR; mutating LR would be refused. A production LR schedule is still missing. This stage closes that software gap alone, not actual Native or language quality.

| Alternative | Benefit | Cost/risk | Decision |
|---|---|---|---|
| Extend the closed ScaledFeatureTrainer directly | One public class | Changes the newly sealed fixed-LR/default path and prior pins | Defer |
| Add an explicit scheduled subclass and versioned checkpoint envelope | Reuses CE/KD, scaler and complete-state implementation; old sources remain exact | New explicit LR ownership and validation methods | Choose |
| Expand the historical eager Native diagnostic | Existing real-model diagnostic | Changes sealed evidence and needs denied model/GPU execution | Defer |

## 2. Authority and impact

User161 permits needed implementation and CPU numerical work until2026-11-18 17:00KST. This stage uses new authored tiny FP32 matrices in the existing environment, not Native/pretrained models or old checkpoints. The actual GPU/model denial remains in force. No package/download/environment/Git/deletion/root09 or protected/other-owner access is added.

| Axis | Contract |
|---|---|
| Comparison | Same original tiny CE5 rows/15 targets and KD2 rows/7 positions; manual unscaled optimizer reference, not a quality experiment |
| Data/schema | New explicit schedule contract/envelope only; no historical checkpoint migration or relabelling |
| Runtime | CPU dense FP32 AdamW/SGD/Muon as already supported; fixed scaler and base owner byte unchanged |
| Single sources | Reuse tinylm/train/anneal_schedule.py:lr_factor directly; no duplicate LR formula, production trainer/CLI defaults unchanged |
| State/failure | Consumed-group clock includes overflow; inactive projector LR/state stays unchanged; partial failure needs complete restore |
| Evidence | Complete tiny CPU numerical state/future loss/recovery only; no Native, quality, speed, memory or75M claim |

## 3. Question and prediction

Can an explicit consumed-group schedule share the existing production LR formula without weakening fixed-LR validation, preserve zero-KD projector state, and resume all future rates/losses/complete state exactly? Expect manual unscaled tiny FP32 updates and scheduled scaled updates to match exactly with power-of-two scaling; if not, retain the failure and assess the actual numerical discrepancy before changing any gate. Expect complete fresh-object recovery, overflow clock progression and pure invalid-snapshot refusal. No language-quality prediction.

## 4. Chosen boundary

ConsumedGroupSchedule declares steps/warm/sched/decay_frac and the exact clock policy. Only cosine/wsd/stable/decay are accepted; finite positive base rates are captured from every optimizer group. Ordinal0 is the first original group. The canonical lr_factor owns warmup/cooldown, with0<=ordinal<steps. Planned budget exhaustion stops before a source call; earlier normal source exhaustion remains normal.

ScheduledFeatureTrainer is explicit and separate from the unchanged fixed-LR class. It normalizes only the LR field when checking immutable optimizer identity, while independently requiring live rates to match the declared last-active consumed ordinal for each optimizer. Every other optimizer setting remains pinned. Before the active optimizers run, their rates become base_lr*factor(consumed_ordinal). Inactive projector groups retain their previous LR as well as values/moments/steps. Overflow still consumes the complete original group and schedule ordinal but skips all optimizer calls.

The new checkpoint envelope includes exact schedule policy, base rates, completed ordinal, per-optimizer last-active ordinals/current rates, and the unchanged complete-boundary state. Student optimizers must last be active at completed-1; projector state must agree with the current scaler active set. Saved optimizer rates must match that schedule state before any live copy. Validation passes a detached base-rate-normalized copy to the existing fixed-settings validator, then loads the original checked saved state. No historical checkpoint is changed or silently accepted as the new schema.

## 5. Execution and checks

Pin the old18 sources plus the canonical LR module and production compatibility wrapper. Add only scripts/p106b_dskdv2_scheduled_training.py and its separate test. Use a direct unscaled CEKDGroup/manual-optimizer reference with identical initial model/projector/source/Python/NumPy/Torch RNG; compare every final model/buffer/projector/optimizer/source/RNG value and per-group loss. Check fresh safe numerical checkpoint resume across warmup/cooldown, overflow, zero-KD groups, partial optimizer failure, invalid policy/rate/counter snapshots and exact budget/EOF behavior.

No prior closed suites are rerun merely to add a count; unchanged old20 hashes and the new independent numerical reference protect the boundary. New fixtures/checkpoints are retained. Every CPU log, failure, source snapshot and receipt gets a unique namespace.

## 6. Cost and preflight

One CPU thread,120-second hard timeout, existing Torch2.10/NumPy/Python3.10. Tiny numerical payload target below8MiB. No actual language-training pool/tokens, standard accum/sigma threshold, Native/model asset, CUDA, network, new teacher output or corpus admission. Tag p106b_dskd_schedule_cpu_v1_20261118 was unused; the registry plan query returned only unrelated300M logs with one generic matching term. The independent variable is LR/control ownership, not another real training configuration.

This preflight rejects known design mistakes only; execution remains NOT_RUN until the new receipt and original runlog close.

## 7. Limits and follow-up

Actual Native/corpus/provider/teacher state and authenticated assets, BF16/CUDA/DDP/full-size costs,8-hour/75M generation, rights/split/admission and student quality remain separate. The per-optimizer last-active ordinal is a checked local control declaration, not proof of an external source's full historical KD population. Only fresh objects in the same process are planned; cross-process and production model identity are not promised.

## 8. Result

[101 section649](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-consumed-group-lr-schedule-cpu) closes10 new CPU controls/exit0. Independent manual unscaled updates and fresh complete future rates/losses/state are exact, including zero-KD/overflow/dirty recovery. Old20/current22 source and21 fixture-file readback pass. Actual Native/provider/teacher/75M/rights/quality remain NOT_RUN.
