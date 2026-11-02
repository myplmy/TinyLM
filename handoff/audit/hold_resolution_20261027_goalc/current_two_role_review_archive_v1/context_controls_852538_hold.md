# 852538 보류 원문과 근거

대상 본문: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/resume_guard_counter_20261102_v1/expanded_train_852538_reviewed_v7.txt

| 원문 위치 | 보류 원문 또는 범위 | 처리 근거 |
|---|---|---|
| expanded_train_852538_original_0001.txt:23-25 | 완전정보 결과 및 사회적 선택함수가 true type profile을 결과/할당에 매핑한다는 설명 뒤의 빈 수식 구간 | 정의가 결손 mapping 식에 직접 이어진다. 별도로 완결된 `In contrast...` 메커니즘 설명은 본문에 남겼다. |
| expanded_train_852538_original_0001.txt:38-40 | `Its proof is quite direct. Assume ...`로 시작하는 전략·보수·기대효용 균형 증명과 `195/5000` artifact | 관련 전략·보수 기호와 관계식이 없어 증명을 재구성할 수 없다. 수치 artifact를 본문 내용으로 해석하지 않는다. |
| expanded_train_852538_original_0001.txt:45-47 | 완결된 `Under such a mechanism...` 설명 뒤 `Formally, choose [missing] such that [missing formula]` | 선택 변수 및 조건식이 빠져 있다. 바로 앞의 완결된 truth-telling 설명은 본문에 유지했다. |
| expanded_train_852538_original_0001.txt:55-58 | `To implement a social choice function [missing] is to find some [missing] transfer function ... outcome [missing]. Formally, if ...` 뒤의 빈 식 | implementability 정의의 함수·결과 및 allocation 동등 조건이 빠져 있다. |
| expanded_train_852538_original_0001.txt:59 | `we say the mechanism implements the social choice function.` | 55-58행의 빠진 정의식을 마무리하는 끝절이다. 별도의 완결 주장으로 남기지 않는다. |
| expanded_train_852538_original_0001.txt:61-67 | 계시 원리로 구현하는 전달 함수 및 truthfully implementable 정의, 누락된 allocation/transfer-function 기호·조건식 | 정의 대상과 조건이 비어 있어 수식이나 변수를 만들지 않는다. |
| expanded_train_852538_original_0001.txt:69 | `인센티브 호환성 (IC) 제약이라고도 한다.` | 지시 대상이 누락된 단편이다. |
| expanded_train_852538_original_0001.txt:71 앞문장 | `응용 프로그램에서 IC 조건은 [missing]의 모양을 유용한 방법으로 설명하는 핵심 요소이다.` | 핵심 대상이 빠져 문장이 완결되지 않는다. 같은 원문의 전달함수 분석 분리 및 IR 설명은 v7 본문에 남겼다. |
| expanded_train_852538_original_0001.txt:74-80 | type-contingent utility, vector allocation의 차원/재화 수, implementability 부등식 및 연속성 조건, 필요조건 유도 | utility·allocation 변수와 조건식이 빠져 있다. 이를 해석하는 바로 다음 문단도 별도 보류한다. |
| expanded_train_852538_original_0001.txt:82-92 앞부분 | `Its meaning can be understood in two pieces`; 첫 조각의 MRS 증가; `In short...` truth-telling 해석; 두 번째 조각의 단조성; 두 조각의 상호작용, higher-type quantity/discount/ironing 설명 | 빠진 필요조건 식을 직접 해석하므로 MRS 증가나 단조성을 일반 명제로 재서술하지 않는다. 뒤의 다중 재화 대체 예시는 독립적이어서 본문에 유지했다. |
| expanded_train_852538_original_0001.txt:95-105 및 original_0002.txt:1 | `Mechanism design papers usually make two assumptions...`; 빠진 가정식; `This is known by several names...` single-crossing/MRS 설명; 누락된 기술 조건; `any monotonic [missing] is implementable` 관계와 이어지는 single-good 결론 | single-crossing 문장의 `This`가 바로 앞의 누락된 가정식을 가리킨다. 이 설명을 독립된 새 일반 명제로 바꾸지 않는다. 결론의 monotonic 대상과 implementability 관계도 빠져 있으며 표제에서 주어를 생성하지 않는다. |
| expanded_train_852538_original_0002.txt:19-21 | VCG 설정의 agent 수, private valuations, currency 값 및 socially optimal allocation을 정의하는 빈 식 | 변수 및 allocation 식이 비어 있다. 식 앞의 독립적인 VCG 배경과 truth-telling 설명은 본문에 유지했다. |
| expanded_train_852538_original_0002.txt:23-27 뒷부분 | `The payment is calculated` / 빈 payment 식 / `which sums the distortion in the utilities of the other agents...` | 뒤의 계산 설명은 빠진 payment 식에 종속된다. 식 앞에서 끝나는 완결된 VCG truth-telling 설명은 본문에 남겼다. |
| expanded_train_852538_original_0002.txt:32-37 | `한 사회자가 ... 사회적 선택 함수 f()는 독재적이지만,` 및 뒤의 미완결 구현 조건·`X` 조건 사슬 | f() 문장이 접속어로 끝나고 조건 사슬의 내용이 빠져 있다. 직전의 완결된 영어 Gibbard–Satterthwaite 설명은 본문에 유지했다. |
| expanded_train_852538_original_0002.txt:46 | `Mirrlees introduces... transfer function t()...` 문장들 및 결손 type parameter로 끝나는 single-good setting 도입 | root 중재에 따라 t()가 포함된 setting 문장도 hold한다. 별도 IR/IC 참여 설명(53행)은 독립적이어서 본문에 유지했다. |
| expanded_train_852538_original_0002.txt:57 | 교장의 잉여 평균 왜곡 및 `위의 조건`을 충족하는 역상 구간에 x를 맞추라는 설명 | 앞의 결손 조건을 지시하고 구간/역상 내용도 완결되지 않는다. |
| expanded_train_852538_original_0002.txt:73-75 | `Chapter 7 of .`, `Chapter 23 of .`, `. Applications...` | 서지명/저자가 비어 있다. 채워진 Noam Nisan, Roger B. Myerson, Eric Maskin 자료는 본문에 유지했다. |
| expanded_train_852538_original_0002.txt:59-61 및 끝 분류 | 내용주·각주 빈 표제와 끝의 `게임 이론` 분류 | 학습 본문에서 내용주/각주 편집 표제와 분류 꼬리말을 분리했다. |
| expanded_train_852538_original_0002.txt:6 | `는 대규모 경매의 모든 구성원이 판매자에게 동일한 예상 수익을 보장하고 예상 수익이 판매자가 할 수 있는 최선이라는 유명한 결과를 제공한다. 다음과 같은 경우` | 원문에서 정리 이름 주어가 소실된 미완결 결론이다. 표제에서 주어를 생성해 붙이지 않고 문장만 본문에서 뺐으며, 실제로 채워진 다섯 조건과 마지막 조건 설명은 유지했다. |

Harsanyi (1967)의 채워진 비밀 메시지 설명, 다중 재화 대체 예시, 수익 등가정리의 다섯 조건과 마지막 조건 설명, 완결 VCG·Gibbard–Satterthwaite·Myerson–Satterthwaite 설명은 본문에 유지했다. v7 본문에는 HOLD 표식·검수 문구·보관 설명 또는 새 변수·식이 없다.
