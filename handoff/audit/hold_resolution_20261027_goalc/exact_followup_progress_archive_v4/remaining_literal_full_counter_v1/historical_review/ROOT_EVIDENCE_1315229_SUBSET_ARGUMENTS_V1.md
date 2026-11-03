# 1315229 인수 소유 관계 중재

총괄이 지정 original 6,992바이트의 처음부터 끝까지 읽었다. 새 학습 본문은 Luna만 작성한다.

확인한 1차 자료: [Microsoft Subset(MDX)](https://learn.microsoft.com/en-us/sql/mdx/subset-mdx?view=sql-server-ver17). 2026-11-03 실제 페이지의 Arguments와 Remarks를 읽었다. Start는 반환 시작 위치이며 0 기반이고, Count는 반환 개수다. Count 생략은 지정 Start부터 끝까지라는 뜻이다. 이 근거는 SQL Server MDX에 한정하며 다른 제품 일반화가 아니다.

지정 원문의 `In specifying «Count»` 문장에서 0/1을 첫째/둘째 위치로 설명한 인수 이름만 «Start»로 정정한다. 이 한 단어 사실 정정과 근거를 sidecar에 명시한다. Count가 개수라는 앞뒤 설명과 충돌하므로 단순 표시 차이가 아니다.

바로 앞 Count 생략 설명 안의 `which is "position zero,"`는 모든 Start가 0이라는 잘못된 한정이므로 그 삽입절만 원형 분리한다. 지정 Start부터 끝까지라는 나머지 설명은 보존한다. 새로운 기본 Start 값이나 함수 서명을 만들지 않는다.

`.Children` 앞 집합 이름이 소실된 두 예시, 실제 빠진 Table 1과 직접 결과 예고는 별도 결손 경계다. 실제 Q1/Q2 위치와 1998/3개라는 완결 설명을 이름 없는 집합 표현의 채움 재료로 쓰지 않는다. 일반 비교와 완결된 설명은 보존한다. 본 자료 검토는 예시 실행 또는 전체 글 사실 검증이 아니다.
