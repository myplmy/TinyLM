# 완료 literal 유형의 새 고정본 진단 범위

대상은 remaining_literal_full_counter_v1 snapshot v20의 1,793개 저장 리뷰이며 본문 1,783개와 본문 없는 10개를 구분한다. 메타데이터 전량 검산 71a48e에서 보호 ID/SHA 일치는 0이었다. payload마다 같은 보호 계약을 다시 검사한 뒤에만 읽는다.

| 안 | 내용 | 영향과 비용 |
|---|---|---|
| 옛 부분 진단 재사용만 | v3 당시 부분 본문을 현재 전량으로 간주 | 새 출력/후속을 검사하지 못하므로 적용하지 않는다. |
| 검사 알고리즘 재작성 | literal 전용 numeric/code 등의 새 판정기 작성 | 기존 회귀 근거와 판정을 중복·변경하므로 적용하지 않는다. |
| 같은 판정기로 v20 검사 | 기존 field 진단 드라이버와 원래 exact_cohort/숫자 모듈을 고정해 입력·수량·출력 namespace만 변경 | 새 전체 본문 범위를 읽고 옛 기준과 비교할 수 있다. 이 방식을 적용한다. |

쓰기 대상은 audit_literal_bound_bodies_v1.py, 이 MD, LITERAL_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json 및 data_cache/p106b_hold_resolution_v1_20261027_goalc/literal_bound_body_diagnostics_v1/의 새 진단 기록뿐이다. 권한은 현재 전체 정제 목표의 CPU 분석·관련 코드/검사·별도 파생 자료 작성이다. 원형·candidate·작성자 TXT·기존 진단·roster·캐시는 변경하지 않는다.

코드 축: audit_field_bound_bodies_v1.py의 SHA 017052EE5484CEF7AEF801612A4BC7838F6CCAE7867F8702C916D1943BCB7186을 확인하고 입력 목록·결과 경로/이름·기대 수만 바꾼다. 그 드라이버가 AST로 재사용하는 audit_exact_cohort_bodies_v6.py와 numeric_atom_integrity_v1.py의 알고리즘/guard는 그대로다. 과거 producer의 top-level 출력 경로를 재실행하지 않는다.

데이터 축: 고정 v20 및 manifest/shard SHA와 개별 원형/선택 본문 SHA를 확인한다. ID와 원형 SHA 보호 검사는 payload보다 먼저다. UTF-8/EOF는 실제 바이트 차이를 기록하며 LF 변화 면제나 강제 절단은 없다. 새 기록은 개별 20,000,000바이트 미만으로 분할한다.

검사 축: 기대 리뷰1793/본문1783/본문없는10을 대조한다. 완료 후 원본 결과와 동등한 파일인지, 기록의 고유 ID·guard 합계·본문 없는 수·핀을 독립 검산한다. 코드/숫자/Unicode/style/순서 신호는 새 문맥 판독 대상으로 남기고 자동 채택/의미 PASS로 바꾸지 않는다.

정본 축: 새 실험·모델 수치·학습 풀 채택이 없으므로 기준표·METHODS·COMPASS·실험TSV를 이번 진단만으로 변경하지 않는다. 원장에는 검사 사실과 잔여만 반영한다. 기술부채 축: 중복 판정기를 만들지 않고 동결 드라이버를 재사용한다. 동일 본문 근거의 재판독을 줄일 수 있지만 속도 향상 비중은 아직 측정하지 않았다.

도메인 축: GPU·학습·모델 로딩은 0이며 설치/다운로드·보호 TinyDataset·타 세션 자료/프로세스·Git 외부 변경은 없다. EOS/캐시/누설·모델 품질과 이 본문 진단을 혼합하지 않는다. 신규 파생 진단이며 최종 캐시 빌드가 아니다. 총괄의 학습용 TXT 작성과 ROOT/캐시 채택은 0이다.
