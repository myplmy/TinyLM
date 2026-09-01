# TinyLM Stage2~10 family 의미 적합성·독립 감사 보고서

- 감사일: 2026-09-02 KST
- 전체 판정: **PASS_WITH_TAXONOMY_POLICY_NOTE**
- 의미 적합성: **PASS**
- strict canonical-axis 정책: **POLICY_DECISION_REQUIRED**
- 범위: 두 예약 fragment의 4,370 families, Stage2~10의 54 areas
- 비수정 원칙: fragment·중앙 원장·manifest·corpus·source·Guide·Design·작업원장은 변경하지 않았다.

## 1. 결론

4,370개 family를 병합해 전수 규칙 검사하고, 54개 area마다 primary·contingency·new의 train/validation 표본을 직접 판독했다. 학습목표에서 벗어난 family, domain–axis 의미 충돌, placeholder, 인공 번호 합성, 과도하게 범용인 domain은 발견되지 않았다.

다만 Stage2~6 신규 1,025행은 중앙 `semantic_axes`의 의미를 세분화한 alias이며 exact 문자열 목록에는 없다. 현행 Guide·Design은 이 배열을 폐쇄 어휘라고 선언하지 않으므로 의미 오류로 판정하지 않았다. 그러나 downstream이 exact allowlist로 검사한다면 중앙 revision 전에 alias/canonical 투영 정책을 확정해야 한다.

## 2. 핵심 수치

| 검사 | 결과 |
|---|---:|
| fragment rows | 4,370 |
| Stage/area coverage | 9 / 54 |
| 직접 판독 origin·split samples | 315 |
| exact concept-family duplicate excess | 0 |
| 정규화 payload duplicate excess | 0 |
| 동일 domain+axis duplicate excess | 0 |
| Stage 간 정규화 payload duplicate groups | 0 |
| Stage별 train–val domain overlap | 0 |
| 전체 train–val domain overlap | 0 |
| placeholder / 범용 / 인공 합성 family | 0 / 0 / 0 |
| concept_family payload 불일치 | 0 |
| area 학습목표 의미 불일치 | 0 |
| canonical exact axes | 3,120 |
| 승인 contingency axis 예외 | 225 |
| 의미 정렬된 미등록 extension aliases | 1,025 |

## 3. Stage별 구성

| Stage | rows | train/val | primary/contingency/new | domain overlap |
|---:|---:|---:|---:|---:|
| 2 | 480 | 432/48 | 250/25/205 | 0 |
| 3 | 470 | 423/47 | 250/25/195 | 0 |
| 4 | 440 | 396/44 | 250/25/165 | 0 |
| 5 | 600 | 540/60 | 250/25/325 | 0 |
| 6 | 410 | 369/41 | 250/25/135 | 0 |
| 7 | 470 | 423/47 | 250/25/195 | 0 |
| 8 | 500 | 450/50 | 250/25/225 | 0 |
| 9 | 510 | 459/51 | 250/25/235 | 0 |
| 10 | 490 | 441/49 | 250/25/215 | 0 |

## 4. 54개 area 직접 표본·의미 판정

각 표본 열은 `primary / contingency / new` 순서다. 한 origin에 validation 행이 존재하면 train과 validation을 모두 직접 검토했으며, 아래에는 첫 식별자만 압축 표시한다. 전체 315개 표본의 family·domain·axis와 판정은 machine JSON `direct_samples`에 있다.

| Stage-area | slug | P/C/N | 직접 표본 식별자 | 판정 |
|---|---|---:|---|---|
| S2-A01 | `causal_structure` | 50/5/41 | `S2-A01-T-001 / S2-A01-T-046 / S2-A01-T-050` | PASS |
| S2-A02 | `conditional_dependency` | 50/5/40 | `S2-A02-T-001 / S2-A02-T-046 / S2-A02-T-050` | PASS |
| S2-A03 | `temporal_order` | 40/3/34 | `S2-A03-T-001 / S2-A03-T-037 / S2-A03-T-039` | PASS |
| S2-A04 | `state_transition` | 40/4/33 | `S2-A04-T-001 / S2-A04-T-037 / S2-A04-T-041` | PASS |
| S2-A05 | `modality_possibility` | 40/5/32 | `S2-A05-T-001 / S2-A05-T-037 / S2-A05-T-041` | PASS |
| S2-A06 | `relational_composition` | 30/3/25 | `S2-A06-T-001 / S2-A06-T-028 / S2-A06-T-030` | PASS |
| S3-A01 | `goal_action` | 50/5/38 | `S3-A01-T-001 / S3-A01-T-046 / S3-A01-T-050` | PASS |
| S3-A02 | `procedure_sequence` | 50/3/40 | `S3-A02-T-001 / S3-A02-T-046 / S3-A02-T-048` | PASS |
| S3-A03 | `planning_decomposition` | 40/2/34 | `S3-A03-T-001 / S3-A03-T-037 / S3-A03-T-039` | PASS |
| S3-A04 | `constraint_resource` | 40/5/31 | `S3-A04-T-001 / S3-A04-T-037 / S3-A04-T-041` | PASS |
| S3-A05 | `decision_priority` | 40/5/30 | `S3-A05-T-001 / S3-A05-T-037 / S3-A05-T-041` | PASS |
| S3-A06 | `execution_recovery` | 30/5/22 | `S3-A06-T-001 / S3-A06-T-028 / S3-A06-T-032` | PASS |
| S4-A01 | `discourse_reference` | 50/5/33 | `S4-A01-T-001 / S4-A01-T-046 / S4-A01-T-050` | PASS |
| S4-A02 | `ellipsis_coreference` | 50/5/33 | `S4-A02-T-001 / S4-A02-T-046 / S4-A02-T-050` | PASS |
| S4-A03 | `dialogue_state` | 40/5/26 | `S4-A03-T-001 / S4-A03-T-037 / S4-A03-T-041` | PASS |
| S4-A04 | `question_answer` | 40/5/25 | `S4-A04-T-001 / S4-A04-T-037 / S4-A04-T-041` | PASS |
| S4-A05 | `speech_act_pragmatics` | 40/3/27 | `S4-A05-T-001 / S4-A05-T-037 / S4-A05-T-039` | PASS |
| S4-A06 | `implicature_context` | 30/2/21 | `S4-A06-T-001 / S4-A06-T-028 / S4-A06-T-030` | PASS |
| S5-A01 | `induction` | 50/5/65 | `S5-A01-T-001 / S5-A01-T-046 / S5-A01-T-050` | PASS |
| S5-A02 | `deduction` | 50/5/65 | `S5-A02-T-001 / S5-A02-T-046 / S5-A02-T-050` | PASS |
| S5-A03 | `counterexample_generalization` | 40/5/52 | `S5-A03-T-001 / S5-A03-T-037 / S5-A03-T-041` | PASS |
| S5-A04 | `compositional_novelty` | 40/5/51 | `S5-A04-T-001 / S5-A04-T-037 / S5-A04-T-041` | PASS |
| S5-A05 | `analogical_transfer` | 40/3/52 | `S5-A05-T-001 / S5-A05-T-037 / S5-A05-T-039` | PASS |
| S5-A06 | `structural_transfer` | 30/2/40 | `S5-A06-T-001 / S5-A06-T-028 / S5-A06-T-030` | PASS |
| S6-A01 | `long_context` | 50/5/27 | `S6-A01-T-001 / S6-A01-T-046 / S6-A01-T-050` | PASS |
| S6-A02 | `multihop_inference` | 50/5/27 | `S6-A02-T-001 / S6-A02-T-046 / S6-A02-T-050` | PASS |
| S6-A03 | `constraint_satisfaction` | 40/5/21 | `S6-A03-T-001 / S6-A03-T-037 / S6-A03-T-041` | PASS |
| S6-A04 | `multiobjective_tradeoff` | 40/5/21 | `S6-A04-T-001 / S6-A04-T-037 / S6-A04-T-041` | PASS |
| S6-A05 | `multisource_integration` | 40/3/22 | `S6-A05-T-001 / S6-A05-T-037 / S6-A05-T-039` | PASS |
| S6-A06 | `uncertainty_management` | 30/2/17 | `S6-A06-T-001 / S6-A06-T-028 / S6-A06-T-030` | PASS |
| S7-A01 | `instruction_intent` | 50/5/38 | `S7-A01-T-001 / S7-A01-T-046 / S7-A01-T-050` | PASS |
| S7-A02 | `output_format` | 50/5/38 | `S7-A02-T-001 / S7-A02-T-046 / S7-A02-T-050` | PASS |
| S7-A03 | `multiturn_dialogue` | 40/5/31 | `S7-A03-T-001 / S7-A03-T-037 / S7-A03-T-041` | PASS |
| S7-A04 | `tool_protocol` | 40/5/31 | `S7-A04-T-001 / S7-A04-T-037 / S7-A04-T-041` | PASS |
| S7-A05 | `safety_uncertainty` | 40/3/32 | `S7-A05-T-001 / S7-A05-T-037 / S7-A05-T-039` | PASS |
| S7-A06 | `practical_task` | 30/2/25 | `S7-A06-T-001 / S7-A06-T-028 / S7-A06-T-030` | PASS |
| S8-A01 | `evidence_quality` | 50/5/45 | `S8-A01-T-001 / S8-A01-T-046 / S8-A01-T-050` | PASS |
| S8-A02 | `error_detection` | 50/5/45 | `S8-A02-T-001 / S8-A02-T-046 / S8-A02-T-050` | PASS |
| S8-A03 | `argument_critique` | 40/5/35 | `S8-A03-T-001 / S8-A03-T-037 / S8-A03-T-041` | PASS |
| S8-A04 | `verification_validation` | 40/5/35 | `S8-A04-T-001 / S8-A04-T-037 / S8-A04-T-041` | PASS |
| S8-A05 | `revision_correction` | 40/3/37 | `S8-A05-T-001 / S8-A05-T-037 / S8-A05-T-039` | PASS |
| S8-A06 | `calibration_abstention` | 30/2/28 | `S8-A06-T-001 / S8-A06-T-028 / S8-A06-T-030` | PASS |
| S9-A01 | `research_synthesis` | 50/5/48 | `S9-A01-T-001 / S9-A01-T-046 / S9-A01-T-050` | PASS |
| S9-A02 | `tool_orchestration` | 50/5/47 | `S9-A02-T-001 / S9-A02-T-046 / S9-A02-T-050` | PASS |
| S9-A03 | `workflow_state` | 40/5/37 | `S9-A03-T-001 / S9-A03-T-037 / S9-A03-T-041` | PASS |
| S9-A04 | `collaboration_handoff` | 40/5/36 | `S9-A04-T-001 / S9-A04-T-037 / S9-A04-T-041` | PASS |
| S9-A05 | `monitoring_adaptation` | 40/3/38 | `S9-A05-T-001 / S9-A05-T-037 / S9-A05-T-039` | PASS |
| S9-A06 | `provenance_audit` | 30/2/29 | `S9-A06-T-001 / S9-A06-T-028 / S9-A06-T-030` | PASS |
| S10-A01 | `expert_integration` | 50/5/43 | `S10-A01-T-001 / S10-A01-T-046 / S10-A01-T-050` | PASS |
| S10-A02 | `crossdomain_synthesis` | 50/5/42 | `S10-A02-T-001 / S10-A02-T-046 / S10-A02-T-050` | PASS |
| S10-A03 | `long_horizon` | 40/5/34 | `S10-A03-T-001 / S10-A03-T-037 / S10-A03-T-041` | PASS |
| S10-A04 | `adversarial_robustness` | 40/5/34 | `S10-A04-T-001 / S10-A04-T-037 / S10-A04-T-041` | PASS |
| S10-A05 | `safe_autonomy` | 40/3/35 | `S10-A05-T-001 / S10-A05-T-037 / S10-A05-T-039` | PASS |
| S10-A06 | `metacognitive_control` | 30/2/27 | `S10-A06-T-001 / S10-A06-T-028 / S10-A06-T-030` | PASS |

## 5. semantic-axis taxonomy 주의사항

strict exact-list 검사에서는 총 1,250행이 canonical 배열 밖이다. 이 가운데 225행은 중앙 원장이 이미 예약한 contingency axis이고, 나머지 1,025행은 Stage2~6 신규 세분 axis다. Stage7~10 신규 870행은 모두 canonical exact다.

권고안:

1. **권고:** Stage2~6의 현재 세분 `semantic_axis`를 보존하고 중앙 원장에 area별 approved alias 또는 `semantic_axis_canonical` 투영을 함께 등록한다.
2. builder·auditor는 세분 axis와 canonical projection의 일치를 검증한다.
3. 1,025행을 단순 문자열 치환하지 않는다. closest-canonical로 맹목 치환하면 domain+axis 중복 excess가 52건 생긴다.
4. exact closed list를 정말 요구한다면 family domain도 하위 상황으로 다시 세분해 중복을 없앤 뒤 별도 승인을 받는다.

영향받는 정확한 reservation 1,025개와 제안 canonical axis는 machine JSON `taxonomy_note.affected_reservations`에 전수 기록했다. 다음은 area·split별 범위다.

| Stage-area | slug | split | count | version | reservation 범위 | aliases |
|---|---|---|---:|---|---|---:|
| S2-A01 | `causal_structure` | train | 38 | v50~v87 | `S2-A01-T-050~S2-A01-T-087` | 5 |
| S2-A01 | `causal_structure` | val | 3 | v07~v09 | `S2-A01-V-007~S2-A01-V-009` | 3 |
| S2-A02 | `conditional_dependency` | train | 37 | v50~v86 | `S2-A02-T-050~S2-A02-T-086` | 5 |
| S2-A02 | `conditional_dependency` | val | 3 | v07~v09 | `S2-A02-V-007~S2-A02-V-009` | 3 |
| S2-A03 | `temporal_order` | train | 31 | v39~v69 | `S2-A03-T-039~S2-A03-T-069` | 5 |
| S2-A03 | `temporal_order` | val | 3 | v06~v08 | `S2-A03-V-006~S2-A03-V-008` | 3 |
| S2-A04 | `state_transition` | train | 29 | v41~v69 | `S2-A04-T-041~S2-A04-T-069` | 5 |
| S2-A04 | `state_transition` | val | 4 | v05~v08 | `S2-A04-V-005~S2-A04-V-008` | 4 |
| S2-A05 | `modality_possibility` | train | 29 | v41~v69 | `S2-A05-T-041~S2-A05-T-069` | 5 |
| S2-A05 | `modality_possibility` | val | 3 | v06~v08 | `S2-A05-V-006~S2-A05-V-008` | 3 |
| S2-A06 | `relational_composition` | train | 23 | v30~v52 | `S2-A06-T-030~S2-A06-T-052` | 5 |
| S2-A06 | `relational_composition` | val | 2 | v05~v06 | `S2-A06-V-005~S2-A06-V-006` | 2 |
| S3-A01 | `goal_action` | train | 35 | v50~v84 | `S3-A01-T-050~S3-A01-T-084` | 5 |
| S3-A01 | `goal_action` | val | 3 | v07~v09 | `S3-A01-V-007~S3-A01-V-009` | 3 |
| S3-A02 | `procedure_sequence` | train | 37 | v48~v84 | `S3-A02-T-048~S3-A02-T-084` | 5 |
| S3-A02 | `procedure_sequence` | val | 3 | v07~v09 | `S3-A02-V-007~S3-A02-V-009` | 3 |
| S3-A03 | `planning_decomposition` | train | 30 | v39~v68 | `S3-A03-T-039~S3-A03-T-068` | 5 |
| S3-A03 | `planning_decomposition` | val | 4 | v05~v08 | `S3-A03-V-005~S3-A03-V-008` | 4 |
| S3-A04 | `constraint_resource` | train | 28 | v41~v68 | `S3-A04-T-041~S3-A04-T-068` | 5 |
| S3-A04 | `constraint_resource` | val | 3 | v06~v08 | `S3-A04-V-006~S3-A04-V-008` | 3 |
| S3-A05 | `decision_priority` | train | 28 | v41~v68 | `S3-A05-T-041~S3-A05-T-068` | 5 |
| S3-A05 | `decision_priority` | val | 2 | v06~v07 | `S3-A05-V-006~S3-A05-V-007` | 2 |
| S3-A06 | `execution_recovery` | train | 20 | v32~v51 | `S3-A06-T-032~S3-A06-T-051` | 5 |
| S3-A06 | `execution_recovery` | val | 2 | v05~v06 | `S3-A06-V-005~S3-A06-V-006` | 2 |
| S4-A01 | `discourse_reference` | train | 30 | v50~v79 | `S4-A01-T-050~S4-A01-T-079` | 5 |
| S4-A01 | `discourse_reference` | val | 3 | v07~v09 | `S4-A01-V-007~S4-A01-V-009` | 3 |
| S4-A02 | `ellipsis_coreference` | train | 30 | v50~v79 | `S4-A02-T-050~S4-A02-T-079` | 5 |
| S4-A02 | `ellipsis_coreference` | val | 3 | v07~v09 | `S4-A02-V-007~S4-A02-V-009` | 3 |
| S4-A03 | `dialogue_state` | train | 24 | v41~v64 | `S4-A03-T-041~S4-A03-T-064` | 5 |
| S4-A03 | `dialogue_state` | val | 2 | v06~v07 | `S4-A03-V-006~S4-A03-V-007` | 2 |
| S4-A04 | `question_answer` | train | 23 | v41~v63 | `S4-A04-T-041~S4-A04-T-063` | 5 |
| S4-A04 | `question_answer` | val | 2 | v06~v07 | `S4-A04-V-006~S4-A04-V-007` | 2 |
| S4-A05 | `speech_act_pragmatics` | train | 25 | v39~v63 | `S4-A05-T-039~S4-A05-T-063` | 5 |
| S4-A05 | `speech_act_pragmatics` | val | 2 | v06~v07 | `S4-A05-V-006~S4-A05-V-007` | 2 |
| S4-A06 | `implicature_context` | train | 19 | v30~v48 | `S4-A06-T-030~S4-A06-T-048` | 5 |
| S4-A06 | `implicature_context` | val | 2 | v04~v05 | `S4-A06-V-004~S4-A06-V-005` | 2 |
| S5-A01 | `induction` | train | 59 | v50~v108 | `S5-A01-T-050~S5-A01-T-108` | 5 |
| S5-A01 | `induction` | val | 6 | v07~v12 | `S5-A01-V-007~S5-A01-V-012` | 5 |
| S5-A02 | `deduction` | train | 59 | v50~v108 | `S5-A02-T-050~S5-A02-T-108` | 5 |
| S5-A02 | `deduction` | val | 6 | v07~v12 | `S5-A02-V-007~S5-A02-V-012` | 5 |
| S5-A03 | `counterexample_generalization` | train | 47 | v41~v87 | `S5-A03-T-041~S5-A03-T-087` | 5 |
| S5-A03 | `counterexample_generalization` | val | 5 | v06~v10 | `S5-A03-V-006~S5-A03-V-010` | 5 |
| S5-A04 | `compositional_novelty` | train | 46 | v41~v86 | `S5-A04-T-041~S5-A04-T-086` | 5 |
| S5-A04 | `compositional_novelty` | val | 5 | v06~v10 | `S5-A04-V-006~S5-A04-V-010` | 5 |
| S5-A05 | `analogical_transfer` | train | 48 | v39~v86 | `S5-A05-T-039~S5-A05-T-086` | 5 |
| S5-A05 | `analogical_transfer` | val | 4 | v06~v09 | `S5-A05-V-006~S5-A05-V-009` | 4 |
| S5-A06 | `structural_transfer` | train | 36 | v30~v65 | `S5-A06-T-030~S5-A06-T-065` | 5 |
| S5-A06 | `structural_transfer` | val | 4 | v04~v07 | `S5-A06-V-004~S5-A06-V-007` | 4 |
| S6-A01 | `long_context` | train | 25 | v50~v74 | `S6-A01-T-050~S6-A01-T-074` | 5 |
| S6-A01 | `long_context` | val | 2 | v07~v08 | `S6-A01-V-007~S6-A01-V-008` | 2 |
| S6-A02 | `multihop_inference` | train | 25 | v50~v74 | `S6-A02-T-050~S6-A02-T-074` | 5 |
| S6-A02 | `multihop_inference` | val | 2 | v07~v08 | `S6-A02-V-007~S6-A02-V-008` | 2 |
| S6-A03 | `constraint_satisfaction` | train | 19 | v41~v59 | `S6-A03-T-041~S6-A03-T-059` | 5 |
| S6-A03 | `constraint_satisfaction` | val | 2 | v06~v07 | `S6-A03-V-006~S6-A03-V-007` | 2 |
| S6-A04 | `multiobjective_tradeoff` | train | 19 | v41~v59 | `S6-A04-T-041~S6-A04-T-059` | 5 |
| S6-A04 | `multiobjective_tradeoff` | val | 2 | v06~v07 | `S6-A04-V-006~S6-A04-V-007` | 2 |
| S6-A05 | `multisource_integration` | train | 21 | v39~v59 | `S6-A05-T-039~S6-A05-T-059` | 5 |
| S6-A05 | `multisource_integration` | val | 1 | v06~v06 | `S6-A05-V-006~S6-A05-V-006` | 1 |
| S6-A06 | `uncertainty_management` | train | 15 | v30~v44 | `S6-A06-T-030~S6-A06-T-044` | 5 |
| S6-A06 | `uncertainty_management` | val | 2 | v04~v05 | `S6-A06-V-004~S6-A06-V-005` | 2 |

## 6. 무결성·비변경 확인

- Stage2~6 fragment SHA-256: `069d431b52a35b6b110a55553dca9748ec25d8e02e973d1d38666be8c04c5bfb`
- Stage7~10 fragment SHA-256: `79c011c66aa1a441ce81a028a2da6f3f1eacde14448a6d5f98f93d6399b5fb93`
- 중앙 snapshot SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`
- Guide SHA-256: `5a68e3fcc55edd1a4d47ad3c9a4a904120d9164fd6ed0055f7803efb4b4a8246`
- Design SHA-256: `0540c1572bdb729ffbfc9c627e1243f00e87beb4e56ae72667ef8f07ec553eaa`
- Curriculum SHA-256: `39eaa7d8423596dd2e643cb4fdc60d476196bd39353063bc4c8cf49f6be632b8`
- 이번 감사에서 위 파일을 수정하지 않았다.

## 7. 최종 판정

의미 적합성·교차 독립성은 **PASS**다. 중앙 통합 전에 남은 유일한 결정은 Stage2~6 세분 axis를 정식 alias/canonical projection으로 등록할지 여부이며, 이를 해결하지 않고 exact whitelist를 강제하면 1,025행이 거짓 실패가 된다.
