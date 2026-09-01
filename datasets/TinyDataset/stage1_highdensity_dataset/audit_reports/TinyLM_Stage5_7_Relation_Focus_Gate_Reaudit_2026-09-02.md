# TinyLM Stage5~7 `relation_focus` 강제 제거 재감사 보고서

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- 범위: Stage5~7 pilot 12 files, 1,800 records, canonical source 12 files
- 변경 범위: Stage5~7 builder 3개와 공유 Stage5 pilot auditor 1개

## 1. 변경 결론

`relation_focus`를 `relations`의 whitelist로 사용하던 네 실행 조건을 제거했다. `relation_focus`는 curriculum 계획을 설명하는 참고 metadata일 뿐 허용 목록·필수 교집합·분포 목표가 아니다.

다음 실제 gate는 유지했다.

- 고정 통제어휘 13개 밖 relation 0
- record당 relation 2~5개
- 한 record 안 relation 중복 0
- `other`와 canonical source의 `other_type` 대응
- primary concept의 text 명시
- source와 JSON projection 일치
- relation이 text에서 직접 근거를 갖는지는 원고 작성자와 의미 감사자가 판독

따라서 고차 능력은 `type`이 담당하며, `relations`에 새 이름을 추가하거나 area에 맞추려고 text에 없는 relation을 붙이지 않는다.

## 2. 변경 파일

| 파일 | 변경 후 SHA-256 |
|---|---|
| `stage5_highdensity_dataset/tools/build_pilot.py` | `d1bbc664598429b23d16098984ada4c72db7be07e66172ec4aca3d101e1d46d0` |
| `stage5_highdensity_dataset/tools/audit_pilot.py` | `8c6738df0c3f205ed9332a997428628d38fc50293b46a8dc0f6a12bef4828985` |
| `stage6_highdensity_dataset/tools/build_pilot.py` | `ebb5db2283874d0c4565020327790a0dbb12f6433dcb3f17bfb7ffe5c65a0dd3` |
| `stage7_highdensity_dataset/tools/build_pilot.py` | `0779e923776f828ed5463e115d302c9aeefab83bd0f44c72aadf2a6e31fe4210` |

Stage6·7의 `audit_pilot.py`는 변경하지 않았다. 두 wrapper는 수정된 Stage5 공유 auditor를 호출한다.

## 3. 실행·정적 검사

다음 builder 검사를 corpus 출력 없이 `--check-only`로 실행했다.

```text
python -X utf8 stage5_highdensity_dataset/tools/build_pilot.py --check-only
python -X utf8 stage6_highdensity_dataset/tools/build_pilot.py --check-only
python -X utf8 stage7_highdensity_dataset/tools/build_pilot.py --check-only
```

세 Stage 모두 4/4 pilot source를 150 records로 검사해 PASS했다. Stage5~7의 builder·auditor 6개는 Python AST parse 오류 0이며, 실행 가능한 `area["relation_focus"]`, `relation outside area focus`, `relation focus` 오류 추가 경로는 0개다.

## 4. Pilot 재감사

읽기 전용 독립 검사로 manifest의 pilot 예약, source header와 150행, JSON schema projection, `type`·split, concept literal, `other_type`, relation cardinality·중복·통제어휘를 전수 대조했다.

| Stage | files | records | train/val | relation 배정 | 규칙 오류 |
|---:|---:|---:|---:|---:|---:|
| 5 | 4 | 600 | 450/150 | 1,810 | 0 |
| 6 | 4 | 600 | 450/150 | 1,680 | 0 |
| 7 | 4 | 600 | 450/150 | 1,477 | 0 |
| **합계** | **12** | **1,800** | **1,350/450** | **4,967** | **0** |

현재 pilot은 우연히 모든 relation이 기존 `relation_focus` 안에 있어 밖의 발생은 0회다. 이는 whitelist 유지 근거가 아니다. 도구의 runtime 강제가 제거됐으므로 앞으로는 text가 직접 뒷받침하는 13개 relation이라면 area focus 밖 label도 허용한다.

### 13개 relation 합산 분포

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 0 |
| `classification` | 678 |
| `boundary` | 1,233 |
| `contrast` | 75 |
| `comparison` | 312 |
| `function` | 352 |
| `role` | 377 |
| `process` | 343 |
| `state` | 853 |
| `attribute` | 423 |
| `other` | 321 |

## 5. 의미감사·무결성 연결

기존 독립 의미감사 `TinyLM_Stage5_7_Pilot_Independent_Semantic_Audit_2026-09-02.md`는 Stage5~7을 모두 PASS로 판정했다. 이번 재감사에서 그 보고서의 SHA-256은 `e5ed88b6d921b73df74ddb74031a3cbe20519b6ccfcd4f98dbdccb5df2154ee6`이다.

통합 pilot 감사의 파일별 기준과 비교한 결과는 다음과 같다.

- pilot JSON SHA-256: 12/12 일치
- canonical source SHA-256: 12/12 일치
- corpus/source 수정: 0 files
- JSON/source parse·projection·relation 오류: 0

기계 결과는 `audit_reports/machine/TinyLM_Stage5_7_Relation_Focus_Gate_Reaudit_2026-09-02.json`에 보존했다.

## 6. 최종 판정

**PASS.** Stage5~7의 `relation_focus` whitelist 강제는 제거됐고, 13개 통제어휘·2~5개·내부 중복 금지·source projection 검사는 유지됐다. 기존 pilot 의미감사 PASS와 corpus/source 해시는 그대로다.
