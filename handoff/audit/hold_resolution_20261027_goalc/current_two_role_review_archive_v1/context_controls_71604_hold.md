# 71604 보류 원문과 근거

대상 본문: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/resume_guard_counter_20261102_v1/expanded_train_71604_reviewed_v2.txt

| 원문 위치 | 보류 원문 또는 범위 | 처리 근거 |
|---|---|---|
| expanded_train_71604_original_0001.txt:2 | `관계 의 추이적 폐포를 찾거나` | 첫 절의 추이적 폐포 대상이 비어 있다. 뒤의 실제 원문 구절 `가중 그래프의 모든 꼭짓점 쌍 간의 최대 폭 경로를 (슐츠 선거 제도와 결합해서) 찾는 것이 가능하다`는 본문에 원문 어휘대로 보존했다. |
| expanded_train_71604_original_0001.txt:10 | `이 방법은 그래프에서 의 비교로 진행할 수 있다. 그 이유는 그래프에서는 최대 의 변이 있을 수 있고, 모든 변의 조합을 확인하기 때문이다.` | 비교 연산과 변의 상한이 비어 있어 복잡도 근거를 복원하지 않았다. 같은 줄의 완결된 알고리즘 설명은 본문에 보존했다. |
| expanded_train_71604_original_0001.txt:12-29 앞부분 | 꼭짓점 집합/번호, 경유 집합, 함수 정의, 두 경로 경우, 최적 경로 설명, 변 가중치 및 재귀식, 점화 순서 설명 | 식과 인덱스가 연속적으로 빠져 있어 정의·재귀식·점화 논리를 복원하지 않았다. 완결된 기본 의사코드는 본문에 보존했다. |
| expanded_train_71604_original_0001.txt:45-47 | 그래프 그림을 전제로 한 반복별 경로 설명, 경로 `[2,1,3]`, `[2,3]`, `[4,2,1,3]`, `[4,2]` 및 반복 인덱스 설명 | 그림이 없고 반복 인덱스·수식이 빠진 부분과 결합되어 예시를 독립적으로 해석할 수 없다. |
| expanded_train_71604_original_0001.txt:51-56의 `그 과정은 다음과 같다` 뒤 | 음수 사이클을 감지하는 반복 개선, 초기 경로 거리, 개선 조건, 검출되는 경로의 식별자에 관한 네 항목 | 핵심 경로 인덱스와 조건이 비어 있다. 본문에는 독립적으로 완결된 음수 사이클 정의와 대각 성분 검사 설명을 유지했다. |
| expanded_train_71604_original_0001.txt:58 끝부분 | `위의 예시의 모든 변을 방향이 없다고 생각하면`으로 시작하는 `4 - 2 - 4`의 가중치 합 `-2` 예시 | 보류된 그래프 예시에 직접 의존하므로 수열과 수치를 그 그래프 없이 독립 주장으로 옮기지 않았다. |
| expanded_train_71604_original_0001.txt:62 | 최단 경로 트리 설명 중 시간복잡도와 트리 저장 공간복잡도 값 | 두 복잡도 값이 비어 있다. 앞뒤의 완결된 경로 복원 설명은 본문에 보존했다. |
| expanded_train_71604_original_0001.txt:64-85 | `dist`/`next` 배열 선언의 빈 크기 식과 경로 복원 의사코드 전체. 원문에는 `next`의 초기값 `null`이 명시되어 있음. | 배열 크기와 `dist`의 초기값 식이 결손되어 있다. `next` 초기값 `null`이 없다고 보지 않는다. 두 선언에 직접 의존하는 두 절차를 하나의 경로 복원 예제로 별도 보류했다. 완결된 절차 이름·인수·루프·갱신문은 원문 그대로 아래에 보존한다. |
| expanded_train_71604_original_0001.txt:87-92 | 연산량 및 행렬 수열로 복잡도를 유도하는 문단 | 연산량, 행렬 수, 총 연산 수, 최종 복잡도 식이 빠져 있다. |
| expanded_train_71604_original_0001.txt:119 중간 절 | 음수 가중치가 없는 희소 그래프에서 모든 꼭짓점 출발 데이크스트라와 반복 데이크스트라의 수행 시간(피보나치 힙 사용 시 포함)을 비교하는 부분 | 비교 복잡도 식과 비교 조건이 빠져 있다. 완결된 밀집 그래프 문장과 음수 가중치가 있는 희소 그래프의 Johnson 알고리즘 설명은 본문에 보존했다. |
| expanded_train_71604_original_0001.txt:123 | 내용이 없는 `참고 문헌` 머리말 | 참고 문헌 항목이 제시되지 않아 본문에 빈 머리말을 남기지 않았다. |

## 경로 복원 의사코드 원문 보존

```text
 let dist be a  array of minimum distances initialized to  (infinity)
 let next be a  array of vertex indices initialized to null

 procedure FloydWarshallWithPathReconstruction ()
    for each edge (u,v)
       dist[u][v] ← w(u,v)  // 변 (u,v)의 가중치
       next[u][v] ← v
    for k from 1 to |V| ''// 일반적인 플로이드-워셜의 수행
       for i from 1 to |V|
          for j from 1 to |V|
             if dist[i][j] > dist[i][k] + dist[k][j] then
                dist[i][j] ← dist[i][k] + dist[k][j]
                next[i][j] ← next[i][k]

 procedure Path(u, v)
    if next[u][v] = null then
        return []
    path = [u]
    while u ≠ v
        u ← next[u][v]
        path.append(u)
    return path
```
