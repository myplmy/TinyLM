# A06 v04 의미 재서술 사전 변경 계획 — locator 75 r2 (2026-09-14)

- precondition: source v04 `E50F648FF756743F460E32AD4CE3FA39E5505EDFBE46F8174C8A9CAA0FCBD960`, registry `A8DBA46805E4D7E8509C8989E12E19C0513A612D39C2CDABFD914C21A23DF165`.
- 대상 locator: `stage2_(16)relational_composition_high_density_train_v04.source.psv:75`.
- 기존 concept `수압 센서와 방류 기록이 어긋날 때 응집조 유입 상태를 보류하는 기준`은 원인 절과 상태 판단을 모두 primary에 넣어 과도하게 길다.
- 새 concept `응집조 유입 보류 기준`은 실제 판단 대상인 상태 기준만 남긴다. 수압 센서·방류 기록의 불일치, 담당자의 보류 판단, 응집제 투입 제한은 text에 유지한다.
- relations `part_of, state, attribute`, `other_type`, text, locator·행 순서와 registry의 비-primary field는 보존한다. source의 concept와 같은 registry locator의 primary만 동기화한다.
