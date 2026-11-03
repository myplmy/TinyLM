# 검토 완료 HOLD와 미처리 HOLD의 캐시 구분

사용자 전체 정제 지시와 objective의 CPU 코드·시험·별도 캐시 허가로 적용한다. impact-analysis 검토를 적용했다. 판정 자체를 완화하지 않고 새 캐시에 실제 검토 근거와 미처리 수를 보존한다.

| 안 | 내용 | 장점 | 한계 | 영향도·비용 |
|---|---|---|---|---|
| A | 기존 partial loader에서 모든 HOLD=unprocessed 유지 | 코드 추가 적음 | 실제 검토 후 비채택도 미처리로 집계 | 수량 설명 제한·낮음 |
| B | HOLD를 EXCLUDE로 일괄 전환 | 겉보기 미처리 감소 | 미판독 개명 및 판정 왜곡 | 허용 불가 |
| C | 개별 검토 근거가 핀으로 연결된 HOLD만 검토완료로 구분 | 비채택·잔여·실제 판독 수량을 보존 | 별도 엄격한 loader/소비자 검사 필요 | 새 adapter에 한정·중간 |

권장·수행 C. 기존 캐시의H115526은 그대로다. 새 roster에서는 한 원문의 모든 위치를 KEEP/EDIT/EXCLUDE/HOLD로 계속 보존하며, HOLD 안에서 미판독과 검토후 비채택을 분리한다. 전체goal이나 학습승인 값은 false다.

| 경로 | 동작·권한 | 제외 |
|---|---|---|
| 본 audit의 새 partition helper/test/cache adapter | objective의 구현·시험 허가로 신설 | 기존130 runtime pins/66정제코드 수정 없음 |
| ROOT_REVIEWED_TERMINAL_HOLD37_V1·1255247 철회·정확쌍 exception | 원문별 root판정 근거 읽기 | 미판독 다른원문에 확대 없음 |
| ROOT11·roster/cache의 새 버전 | 작성 후 실제 생성/독립 소비자 검증 | 원본·이전캐시 덮기/삭제 없음 |

코드: 기존 builder/독립 consumer/제한자료 projection을 재사용하고 새 adapter에서 loader와 HOLD 계수만 바꾼다. 데이터: 소스 SHA·원문 ID·위치·본문 SHA를 유지하고 reviewed HOLD에는 본문을 넣지 않는다. 시험: 근거 없는 완료표시/다른SHA/본문누출/이중계수를 거절한다. 문서: WIP/캐시 증명을 갱신하며 최종 METHODS/기준표/COMPASS 연쇄는 최종 전량 검증 뒤 수행한다. 기술부채: 버전을 고정하고 이전 partial의 unprocessed 의미는 소급변경하지 않는다.

GPU/모델/학습은 실행하지 않는다. TinyDataset·타 세션·보호 부모는 접근하지 않고 기존 metadata projection과 safe-view만 쓴다. 풀·토크나이저·학습·평가 경로를 바꾸지 않는다. 정적 시험/CPU캐시 검증과 의미검토·사실검증·모델품질은 별개다. 새 파생 아티팩트는 각각20MB미만이다.
