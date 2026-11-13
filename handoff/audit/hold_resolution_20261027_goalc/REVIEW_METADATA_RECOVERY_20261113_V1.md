# 리뷰 경로·진행 이력의 묶음 회수와 부정 기록

page16 v10 snapshot은 G의29개 명시된 상대 Markdown TXT 링크 및 출력 열 이름을 구 수집기가 인식하지 못해 NO_EXACT_BODY_OUTPUT_PATH로 보류했다. 최초 adapter는 `새 본문 / 선택 경로`만 처리해 v11에서4개가 회복되고25개는 여전히 거절됐다. 두 번째 정확 표기 `새 본문`도 추가한 뒤7개 metadata 시험과 실제 v12 snapshot에서29개 전체가 회복돼 오류0이 됐다. 다중 링크·다른 ID·상위 경로·모호한 출력 열·배정 디렉터리 이탈은 그대로 거절한다. 옛 리뷰·TXT 수정이나 원문 재독·최초판독 실적 추가는0이다. 실패 v10/v11 snapshot과 log는 보존했다.

page18 v2 snapshot은 H review_008.md가 선언한494419/495199 최종 파일이 실제로 없어2개를 거절했다. 확인 결과 각 initial_candidate_v1.txt는 실제 원형 또는 미정리 후보와 같았다. 이는 완료로 적었지만 실제 두 항목의 수정이 남았던 오류다. H가 기존 초기본·옛 리뷰를 보존하고 두 task008_v2.txt를 실제 수정해 고정 final/changes 전체EOF를 확인했다. 새 review_008_v2.md 및 source sidecar에 정확 경로와SHA를 연결했고 page18 v3 수집 결과 오류0이다. 이미 읽은 원문은 재독하지 않고 최초 판독 실적을 늘리지 않았다.495358/495802/495997 기존 출력은 유지했다.

L348434에서 직접 sha256sum을 사용한 역할 범위 이탈은 ASSIGNED_FINAL_LITERAL_REVIEW_F3_F4_V1.md에 보존했다. 이후 저자는 자신의 생성TXT만 조회하는 고정 identities 경로를 사용한다. J475265는 초안에 원문 없는 SU(n)/SL(n)을 넣은 것을 final diff에서 발견해, 삭제하고 결손 rank의 첫 문장·따라서 직접종속절을 HOLD하도록 지시했다. 실제 마감 여부는 다음 snapshot의 저장물로 확인한다. 부정 기록을 새0오류 수집으로 지우지 않는다.

G는 TASK010 진행 갱신 때 기존 PROGRESS를 delete한 뒤 새 요약으로 재작성했다고 보고했다. 현재 파일은 다시 덮지 않도록 고정하고 다음과 같이 이전 이력을 기존 content-addressed archive로 연결했다. 실제 source 입력과 정제TXT 변경은 이 사건에 없으며 새 원문 사본도 만들지 않았다.

- 이전 진행기록: exact_cohort_review_archive_v1/50/50DB0112414B9DE48F1E0808CB0D40324A2E7C504E909176EABA5A0F23234E74.md. SHA50DB0112414B9DE48F1E0808CB0D40324A2E7C504E909176EABA5A0F23234E74를 실제 바이트로 검증했다. page16 v12 snapshot이 보관한 당시 TASK001–006/30ID와 판독기 실패·미출력 이력이다. 그 안의 TASK007 커서는 당시 기록이며 현재 명령이 아니다.
- 현재 진행기록: data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/legacy_review/remaining_field_title_page_016_counter_v1/PROGRESS_PAGE016_20261113_V1.md, 현재2197B/SHA2ACB54B5131B6B65541238439F96A26DB27579D5A3788AAC1DD1A7F71CBAAB24. TASK001–010/50ID와 TASK011/430191 커서를 담는다.

삭제·전체 재작성은 재승인하지 않았다. 이후 좁은 추가 패치로만 기록하도록 지시했고 G가 현재 파일 유지와 본문 정제 계속을 확인했다. 이 문서와 이전 archive를 다음 명시 로컬 저장에 포함한다. 새 캐시 소비 검증과 ROOT 채택·목표 완료를 이 기록 회수로 대신하지 않는다.
