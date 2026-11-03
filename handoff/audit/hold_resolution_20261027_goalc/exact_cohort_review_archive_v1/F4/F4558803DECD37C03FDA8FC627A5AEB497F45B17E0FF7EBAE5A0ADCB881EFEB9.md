# expanded_train:1376910 hold

## 분리한 원문

> For example:
> SELECT t1.a, t2.b FROM t2, (SELECT x+y AS a FROM t1 WHERE z<100) WHERE="1" a="1">5 100)>
> Would be rewritten using query flattening as:
> SELECT t1.x+t1.y AS a, t2.b FROM t2, t1 WHERE z<100 AND="1" a="1">5 100>

> and so it will not recognize that the LEFT JOIN in the following query could be strength-reduced:
> SELECT urls.url FROM urls LEFT JOIN (SELECT * FROM (SELECT url_id AS uid, max(retrieval_time) AS rtime FROM lookups GROUP BY 1 ORDER BY 1) WHERE uid IN (358341,358341,358341) ) recent ON u.source_seed_id = recent.xyz OR u.url_id = recent.xyz WHERE DATETIME(recent.rtime) > DATETIME('now', '-5 days');

> This can happen if all of the following are true:

> Here is a simple example of omitting a LEFT JOIN:
> CREATE TABLE t1(ipk INTEGER PRIMARY KEY, v1); CREATE TABLE t2(ipk INTEGER PRIMARY KEY, v2); CREATE TABLE t3(ipk INTEGER PRIMARY KEY, v3); SELECT v1, v3 FROM t1 LEFT JOIN t2 USING (t1.ipk=t2.ipk) LEFT JOIN t3 USING (t1.ipk=t3.ipk)
> The t2 table is completely unused in the query above, and so the query planner is able to implement the query as if it were written:
> SELECT v1, v3 FROM t1 LEFT JOIN t3 USING (t1.ipk=t3.ipk)

> The resulting evaluation is like this:
> SELECT x, y, b FROM t2 JOIN (SELECT DISTINCT a, b FROM t1 WHERE b BETWEEN 10 AND 20) WHERE b BETWEEN 10 AND 20;

## 근거

query-flattening 예제의 SQL은 인용된 구간에 속성형 `WHERE="1" ...`/`AND="1" ...` 조각이 섞여 문장으로 읽을 수 없습니다. LEFT JOIN strength-reduction 예제는 실제 `urls` 테이블과 `u` 별칭, `recent.xyz` 사이의 연결이 완결되지 않았습니다. LEFT JOIN 제거 설명은 조건 목록이 빠져 있고, 뒤 예제의 `USING` 표현도 원문 그대로는 손상된 SQL입니다. Push-down 예제는 결과 SQL의 join key/`ON` 조건이 보이지 않아 앞서 명시된 `x=a` 관계를 보존하지 못합니다. 이 코드와 직접 예고/해설을 실행 가능한 예로 남기거나 문법·관계를 추정해 복구하지 않았습니다. 나머지 문서의 완결 SQL, 표/열/수치/조건, 설명은 본문에 보존했습니다.
