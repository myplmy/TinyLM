# TinyLM Stage2~10 Family·Manifest Revision 감사 보고서

- 기준일: 2026-09-02 KST
- 판정: **PASS**
- 범위: 중앙 concept-family 원장 revision 및 Stage2~10 `PREPARATION_MANIFEST.json` 9개 동기화
- corpus JSON·canonical source·Guide·Design·작업원장: 수정하지 않음

## 1. 통합 결과

| 항목 | 값 |
|---|---:|
| 전체 family/files | 4,370 |
| train / validation | 3,933 / 437 |
| 전체 records | 655,500 |
| primary 보존 | 2,250 |
| contingency 활성 | 225 |
| 신규 family | 1,895 |
| validation unseen 목표 | 7,866 = 18/file |

## 2. 무결성 검사

| 검사 | 오류 |
|---|---:|
| `total_file_count_errors` | 0 |
| `split_count_errors` | 0 |
| `origin_count_errors` | 0 |
| `primary_preservation_errors` | 0 |
| `contingency_preservation_errors` | 0 |
| `fragment_projection_errors` | 0 |
| `duplicate_reservation_ids` | 0 |
| `duplicate_filenames` | 0 |
| `duplicate_id_ranges` | 0 |
| `duplicate_concrete_ids` | 0 |
| `duplicate_exact_concept_families` | 0 |
| `duplicate_normalized_concept_families` | 0 |
| `area_allocation_errors` | 0 |
| `version_continuity_errors` | 0 |
| `split_domain_overlap_errors` | 0 |
| `filename_formula_errors` | 0 |
| `range_formula_errors` | 0 |
| `packet_type_errors` | 0 |
| `validation_target_errors` | 0 |
| `relation_focus_policy_errors` | 0 |
| `relation_focus_vocabulary_errors` | 0 |
| `manifest_projection_errors` | 0 |
| `manifest_sha_errors` | 0 |

54개 area의 train/validation 승인 배분과 version 연속성을 전수 대조했다. 각 Stage에서 train과 validation의 정규화 domain 교집합은 0이며, `relation_focus`는 13개 통제 어휘 안의 편집 초점일 뿐 whitelist·필수 교집합·분포 목표가 아니다.

## 3. Provenance와 SHA-256

- predecessor 중앙 원장: `823881a7d7074d2c5e3c54a9c732262004ddabf7b4fade75825a963a58346c99`
- revision 중앙 원장: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`
- Stage2~6 fragment: `069d431b52a35b6b110a55553dca9748ec25d8e02e973d1d38666be8c04c5bfb`
- Stage7~10 fragment: `79c011c66aa1a441ce81a028a2da6f3f1eacde14448a6d5f98f93d6399b5fb93`

| Stage | manifest SHA-256 |
|---:|---|
| 2 | `1802fd79354a9ff3cd36872a7f2c32a89ae1803e94aae9ce40edea7cbe4b0c0e` |
| 3 | `8626bae131e66df24611f22c2777d66c49892b933a96a61ee74a549fe6c39df4` |
| 4 | `d32feb1cb378d4e4a1dff08cf560d70619901c6428c6c533c03772834eed8f48` |
| 5 | `1c8049c8e65f05b6fe169a791b4d871b1a69cba4c34b066b1c070d302be829f2` |
| 6 | `95a8811ab7623e70c50e551173d136ed4ebaf0563b0e28cddb85bd84b57a8714` |
| 7 | `564b0b4dcc7b5d3a38215825b944d76628abc1b575ca6fbeb577a20b4e7e2296` |
| 8 | `0b296d37d0c8e0957a3dc535466c5f244a53e199848e90ca10c1a6c89a9d8ac8` |
| 9 | `772cc1596f32271c7ee377e08459f475002082bb28080f205011aeba5c8146e2` |
| 10 | `68d610b6153f703edb79d2e3cfa64324edd4453e254091093d893f51f842c495` |

## 4. 판정

중앙 원장의 4,370개 reservation과 9개 manifest의 Stage subset·중앙 SHA가 exact 일치한다. 이 revision은 family 생성 권한을 확정하지만 전체 corpus 생성 완료를 주장하지 않는다.
