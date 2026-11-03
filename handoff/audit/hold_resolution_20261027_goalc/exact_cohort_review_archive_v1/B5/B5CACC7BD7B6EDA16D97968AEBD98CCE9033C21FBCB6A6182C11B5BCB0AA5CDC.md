# 425847 원형 보류 구간

- 원형: `The only difference is that ‘<>’ is in line with the ISO standard while ‘!=`
  - 판정 근거: 문장이 끝나기 전에 닫히지 않은 `!=` 인용으로 중단된다. 바로 앞 문장은 이미 두 연산자가 같은 출력을 주는 원문 주장을 보존하므로 끊긴 후속 비교만 분리한다.
- 원형: `To search for data that begins with the string \\abc , the WHERE clause must use an escape character as follows: …`
  - 판정 근거: 예고된 WHERE 절 예제가 없다. `\\abc` 문자열 및 ANSI SQL 백슬래시 설명은 실제 입력에 적힌 채로 새 본문에 유지하고, 미상 구문은 만들지 않는다.
