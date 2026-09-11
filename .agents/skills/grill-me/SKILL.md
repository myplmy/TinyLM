---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---

> **TinyLM Codex 이식본.** 현재 사용자 범위와 [AGENTS.md](../../../AGENTS.md)가 우선한다.

계획이나 설계를 결정 트리로 분해해 공유 이해에 도달할 때까지 압박 면담한다.

## 진행 규칙

1. 저장소에서 답할 수 있는 질문은 먼저 코드·문서를 읽어 해결한다. 사용자에게 조사 가능한
   사실을 되묻지 않는다.
2. 의존 관계가 있는 결정은 **한 질문씩** 묻고 답을 받은 뒤 다음 분기로 간다.
3. 각 질문에는 실질적으로 다른 2~3개 선택지, 장단점, 권장안과 근거를 붙인다.
   선택형 질문 도구를 쓰면 권장안을 첫 옵션 + `(Recommended)`로 둔다.
4. 실행·파일 쓰기·외부 상태 변경 권한이 필요한 질문은 선택형 도구로 대신하지 않고
   정확한 대상과 영향을 적은 짧은 일반 질문으로 묻는다.
5. 답을 받으면 합의 내용을 현재 설계에 즉시 반영해 요약한 뒤 다음 질문으로 간다.
   문서 수정은 사용자가 요청하거나 승인한 범위에서만 한다.
6. 코드·문서 근거, 실제 경로, 구체 시나리오를 사용한다. 추상 표현만 되풀이하지 않는다.

완료 시 확정 결정, 기각안과 이유, 열린 질문, 다음 행동을 짧게 정리한다.
