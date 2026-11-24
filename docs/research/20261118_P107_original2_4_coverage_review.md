# P107 original2.4 coverage and remaining decisions

Original WIP58/59 share task2.4. Current161 requires original work before combined presets/full new training. This review reuses the actual owning reports and current source pins; it does not rerun a model or claim all requested learning results are complete.

| Original requirement | Existing evidence | Current conclusion |
|---|---|---|
| causal/MNTP masking, shifted target, visibility and batch ratio | Result107 sections1-6, actual fixed-budget F+B; explicit document helpers/trainer | Implemented and technically observed. The mixed fixed-budget F+B was about7.38% slower, not a free efficiency gain. |
| Uniform control, adaptive statistics and update cost | Sections7-8 and12: real Native uniform/observe/adaptive cost,24 synthetic optimizer updates | Technical control exists. Observe and uniform model trajectories EXACT; adaptive costs1.011021x uniform in one shared-host short experiment. |
| Real Korean/rare/numeric bias | Section7 explicitly uses simulated labels; section12 has no text corpus | NOT_RUN. Simulated labels/technical arrays do not answer real-language bias. Admitted real TRAIN and independent evaluation are required. |
| Keep mask rate/context/optimizer changes separate | Existing fixed profiles and new opt-in contracts; None-default source/state preservation | Existing controls retained. No new combined method or default activation. |
| causal-only KD with masked CE separately | Section16: CPU components/integration and Native None/KL/KL/None,16 synthetic updates | Implemented/technical cost observed. Same resident teacher causal KL adds33.344327% time and1478492160B reserved in this experiment; no teacher-quality or student-quality win. |
| Full model/optimizer/policy/source/RNG/session recovery | Sections13/15/17/18, new sections20-21 | Historical Native exact resume and new tiny CPU scaler/indexed-source resume exist, with distinct schemas and scopes. No actual new full-corpus/scaled Native run. |
| File input/CLI and larger bounded source | Section18 old bounded CLI; section21 optional offset source, unchanged old13 files | Existing technical CLI remains historical/expired; optional indexed programmatic source passes CPU15. Defaults unchanged; actual75M/RSS/CLI activation remain unmeasured. |
| Final causal generation and causal likelihood | No full admitted-corpus P107 comparison is recorded | NOT_RUN. Neither masked loss nor exact synthetic resume establishes final causal quality. |

The owning historical JSON reports were read directly:

- cost/report.json under p107_actual_train_link_v1_20261101: COMPLETE/final_exit0,24 physical updates, uniform10.1638219325s/observe10.4044438625s/adaptive10.2758370660s, observer EXACT, quality_claim/corpus_training false.
- resume/report.json in the same evidence root: COMPLETE/final_exit0,6 physical updates,781346521B in-memory boundary, resume EXACT, quality_claim/corpus_training false.
- p107_causal_kd_cost_v1_20261101/cost/report.json: COMPLETE/final_exit0,16 physical updates, teacher unchanged, quality_claim/corpus_training false.
- nov04_p107_cli/ROOT_READBACK_v1.json: actual_exit0, full state and following loss/targets/LR EXACT, logical2/physical3 updates,49 parts/781352215B, no real corpus or quality claim. These reports are separate experiments; counts are not added as unique-data or successful-quality totals.

[Result107](../../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md) remains the numerical owner. New [CPU51](../../handoff/audit/research_20261118_01a1e647/P107_SCALED_BRIDGE_CPU51_v2.json) and [indexed CPU15](../../handoff/audit/research_20261118_01a1e647/P107_INDEXED_SOURCE_CPU_v1.json) do not supersede the historical measurements.

The immediate requested quality/bias execution is blocked by unadmitted real TRAIN/source rights and the recorded automatic approval rejection of new model/GPU execution. This is a missing decision/authority/data admission, not a failed quality result. Preserve WIP58/59 as unfinished with that blocking condition; do not mark them DONE because the CPU components pass. User161 continues other independent original work and defers questions to the final report. Exact new training commands depend on admitted source/comparator identities and a current execution window; no placeholder command is presented as executable approval.

The75M teacher-language generation target in original69 is not75M hidden positions. Feature cache row counts, selected KD positions, source input tokens and generated/supervised language tokens remain separate units.
