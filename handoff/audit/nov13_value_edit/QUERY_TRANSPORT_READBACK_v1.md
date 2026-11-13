# Stage18 마지막 위치 값·응답·전체 쓰기 원답 대조

총괄은 새156답을 읽고 원래 원답/전체쓰기156답과 대조했다. 자동 짧은답 일치와 의미판독은 다르며 공개표현은 독립평가가 아니다.

## kr_capital:0 / fit

질문: 대한민국의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 서울

### 원본

```text
도시 이름만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
서울
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
서울
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
서울
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
서울
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
서울
```

엄격 일치: True / 종료: STOP_SEQUENCE

## kr_capital:1 / fit

질문: 대한민국의 수도 이름만 답하세요.

지도 정답: 서울

### 원본

```text
대한민국의 수도 이름만 답하세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
서울
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
서울
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
서울
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
서울
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
서울
```

엄격 일치: True / 종료: STOP_SEQUENCE

## kr_capital:2 / dev

질문: 어느 도시가 대한민국의 수도인지 한 단어로 답하세요.

지도 정답: 서울

### 원본

```text
한국 전쟁
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
평양
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
한국
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
한국
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
대한민국의 수도인지
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
대한민국의 수도인지
```

엄격 일치: False / 종료: STOP_SEQUENCE

## fr_capital_ko:0 / fit

질문: 프랑스의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 파리

### 원본

```text
베를린의 도시 이름
베를린의 수도
베오울프주의 도시
베오울프주의 도시
베오울프주의 도시
베를린의 역사적 지역
베를린의 역사적 지역
베를린의 역사적 지역
베를린의 역사적 지역
베를린의 역사적 지역
베를린
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
파리
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
파리
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
파리
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
파리
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
파리
```

엄격 일치: True / 종료: STOP_SEQUENCE

## fr_capital_ko:1 / fit

질문: 프랑스의 수도 이름만 답하세요.

지도 정답: 파리

### 원본

```text
바이올린 수도자
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
파리
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
파리
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
파리
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
파리
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
파리
```

엄격 일치: True / 종료: STOP_SEQUENCE

## fr_capital_ko:2 / dev

질문: 어느 도시가 프랑스의 수도인지 한 단어로 답하세요.

지도 정답: 파리

### 원본

```text
프랑스의 수도인지
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
상호'(大虎)
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
상호작용
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
상호작용
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
상호'(大虎)
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
상호'(大虎)
```

엄격 일치: False / 종료: STOP_SEQUENCE

## water_ko:0 / fit

질문: 물의 화학식을 쓰세요. 화학식만 답하세요.

지도 정답: H2O

### 원본

```text
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.

```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
H2O
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
공기식만 답하세요. 화학식만 답하세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
평형식
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
공기식만 답하세요. 화학식만 답하세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
평형화식 답하세요. 화학식만 답하세요.

같이 보기 
 화학식
 화학식
 화학식
 화학식
 화학식
 화학식
 화학식
 화학식
 화학식
 화학식
 화학식
 화학식
 화학식
 화학식
 화학식
```

엄격 일치: False / 종료: MAX_NEW

## water_ko:1 / fit

질문: 물의 화학식은? 답만 쓰세요.

지도 정답: H2O

### 원본

```text
공기 삼중 주기율표(공기 삼중 주기율표)
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
H2O
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
H2O
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
H2O
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
H2O
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
H2O
```

엄격 일치: True / 종료: STOP_SEQUENCE

## water_ko:2 / dev

질문: 물 분자의 화학식을 기호와 숫자로만 답하세요.

지도 정답: H2O

### 원본

```text
공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다.

공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다. 화학식은 ρ(n)이고, 화학식은 ρ(n)
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
공중핵
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다.

공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다. 화학식은 ρ(n)이고, 화학식은 ρ(n)
```

엄격 일치: False / 종료: MAX_NEW

### 공분산 전체쓰기

```text
공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다.

공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다. 화학식은 ρ(n)이고, 화학식은 ρ(n)
```

엄격 일치: False / 종료: MAX_NEW

### 일반 실제응답 한 위치

```text
공중핵
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
공중핵
```

엄격 일치: False / 종료: STOP_SEQUENCE

## earth_ko:0 / fit

질문: 지구가 공전하는 별은 무엇입니까? 이름만 답하세요.

지도 정답: 태양

### 원본

```text
은거하는 별은 무엇입니까? 본인입니다.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
태양
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
태양
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
태양
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
태양
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
태양
```

엄격 일치: True / 종료: STOP_SEQUENCE

## earth_ko:1 / fit

질문: 지구는 어느 별 주위를 공전합니까? 별 이름만 쓰세요.

지도 정답: 태양

### 원본

```text
경계면적은 1,048,641m2

지구의 공전궤도로는 다음과 같다.

참고 문헌 

지구의 공전궤도
서쪽 지점에서 태양저화기지구의 어머니 별
20:00
18:00
18:00
18:00
18
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
태양
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
태양
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
태양
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
태양
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
태양
```

엄격 일치: True / 종료: STOP_SEQUENCE

## earth_ko:2 / dev

질문: 지구의 공전 중심인 별 이름만 답하세요.

지도 정답: 태양

### 원본

```text
지구가 별에 속하지 않는 별들.

각주 

지구의 목성
목성형 행성
목성형 행성
1981년 발견한 외계 행성
목성형 절
```

엄격 일치: False / 종료: EOS

### 고정값 한 위치

```text
2
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
2
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
2
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
2
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
2
```

엄격 일치: False / 종료: STOP_SEQUENCE

## de_capital_ko:0 / fit

질문: 독일의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 베를린

### 원본

```text
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요.
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요.
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
베를린
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
베를린
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
베를린
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
베를린
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
베를린
```

엄격 일치: True / 종료: STOP_SEQUENCE

## de_capital_ko:1 / fit

질문: 독일의 수도 이름만 답하세요.

지도 정답: 베를린

### 원본

```text
독일의 수도 이름만 답하세요.

독일의 수도 이름
독일의 군사사
독일의 군사사
독일의 군사사
독일의 군사사
독일의 군사사
독일의 군사사
독일의 군사사
독일의 군사사
독일의 군사사
독일의 군사사
독일의 군사사
독일의 군사사
독일의 군사
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
베를린
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
베를린
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
베를린
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
베를린
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
베를린
```

엄격 일치: True / 종료: STOP_SEQUENCE

## de_capital_ko:2 / dev

질문: 어느 도시가 독일의 수도인지 한 단어로 답하세요.

지도 정답: 베를린

### 원본

```text
독일의 수도인지 한단어의 답하세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
독일의 수도인지
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
독일의 수도인지
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
독일의 수도인지
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
독일의 수도인지
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
독일의 수도인지
```

엄격 일치: False / 종료: STOP_SEQUENCE

## de_capital_ko:3 / test

질문: 독일의 수도에 해당하는 도시 이름을 적으세요.

지도 정답: 베를린

### 원본

```text
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국
바이마르 공화국

```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
바이올린
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
바이올린
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
바이올린
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
바이올린
```

엄격 일치: False / 종료: STOP_SEQUENCE

## de_capital_ko:4 / test

질문: 나라 독일의 수도는? 답만 쓰세요.

지도 정답: 베를린

### 원본

```text
독일의 수도는 독일에 있다.

같이 보기 
 독일-소련 관계

각주

외부 링크 

 독일 수도방위사령부

독일-소련 관계
독일-소련 관계
독일-소련 관계
독일-소련 관계
독일-소련 관계
독일-소련 관계
독일-소련 관계
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
독일의 수도는? 답만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
독일의 수도는? 답만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
독일의 수도는? 답만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
독일의 수도는? 답만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
독일의 수도는? 답만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

## it_capital_ko:0 / fit

질문: 이탈리아의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 로마

### 원본

```text
이탈리아의 수도는 어디입니까? 도시 이름만 쓰세요.

같이 보기 
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마

```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

## it_capital_ko:1 / fit

질문: 이탈리아의 수도 이름만 답하세요.

지도 정답: 로마

### 원본

```text
이탈리아의 수도 이름.

같이 보기 
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
 로마
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

## it_capital_ko:2 / dev

질문: 어느 도시가 이탈리아의 수도인지 한 단어로 답하세요.

지도 정답: 로마

### 원본

```text
로마 숫자
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
로마 숫자
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
로마 숫자
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
로마
```

엄격 일치: True / 종료: STOP_SEQUENCE

## it_capital_ko:3 / test

질문: 이탈리아의 수도에 해당하는 도시 이름을 적으세요.

지도 정답: 로마

### 원본

```text
바이올린
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
 적으세요
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
 적으세요
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
 적으세요
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
 적으세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
 적으세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

## it_capital_ko:4 / test

질문: 나라 이탈리아의 수도는? 답만 쓰세요.

지도 정답: 로마

### 원본

```text
나라 이탈리아의 수도는? 답만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
나라 이탈리아의 수도는?
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
나라 이탈리아의 수도는? 답만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
나라 이탈리아의 수도는? 답만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
나라 이탈리아의 수도는? 답만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
나라 이탈리아의 수도는? 답만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

## oxygen_ko:0 / fit

질문: 산소 분자의 화학식을 쓰세요. 화학식만 답하세요.

지도 정답: O2

### 원본

```text
산소 분자의 화학식만 답하세요. 화학식만 답하세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
Ca2SO4
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
Ca2SO4
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
Ca2SO4
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
Ca2SO4
```

엄격 일치: False / 종료: STOP_SEQUENCE

## oxygen_ko:1 / fit

질문: 산소 분자의 화학식은? 답만 쓰세요.

지도 정답: O2

### 원본

```text
산소 분자의 화학식은? 답만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

## oxygen_ko:2 / dev

질문: 산소 분자의 화학식을 기호와 숫자로만 답하세요.

지도 정답: O2

### 원본

```text
산소 분자의 화학식은 Cg(Ca)2O3.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Ca2O4
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
산소 분자의 화학식은 Cg(Ca)2O3.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
산소 분자의 화학식은 Hg2O3.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
산소 분자의 화학식은 Cg(Ca)2O3.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
산소 분자의 화학식은 Cg(Ca)2O2O2.
```

엄격 일치: False / 종료: STOP_SEQUENCE

## oxygen_ko:3 / test

질문: 산소 분자에 해당하는 화학식 한 개만 적으세요.

지도 정답: O2

### 원본

```text
산소 분자에 해당하는 화학식 한 개만 적으세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Ca2O3
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
산소 분자에 해당하는 화학식 한 개만 적으세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
산소 분자에 해당하는 화학식 한 개만 적으세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
산소 분자에 해당하는 화학식 한 개만 적으세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
산소 분자에 해당하는 화학식 한 개만 적으세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

## oxygen_ko:4 / test

질문: 다른 설명 없이 산소 분자의 화학식을 알려주세요.

지도 정답: O2

### 원본

```text
산소 분자의 화학식은 산소 분자의 화학식은 산소(OH)와 산소(OH)가 결합되어 있다.

같이 보기 
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소

```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
산소 분자의 화학식은 산소 분자의 화학식은 산소(OH)와 산소(OH)가 결합되어 있다.

같이 보기 
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소

```

엄격 일치: False / 종료: MAX_NEW

### 공분산 실제응답 한 위치

```text
산소 분자의 화학식은 산소 분자의 화학식은 산소(OH)와 산소(OH)가 결합되어 있다.

같이 보기 
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소

```

엄격 일치: False / 종료: MAX_NEW

### 공분산 전체쓰기

```text
산소 분자의 화학식은 H2O2.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
산소 분자의 화학식은 산소 분자의 화학식은 산소(OH)와 산소(OH)가 결합되어 있다.

같이 보기 
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소

```

엄격 일치: False / 종료: MAX_NEW

### 일반 전체쓰기

```text
산소 분자의 화학식은 산소 분자의 화학식은 산소(OH)와 산소(OH)가 결합되어 있다.

같이 보기 
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소
 산소

```

엄격 일치: False / 종료: MAX_NEW

## moon_ko:0 / fit

질문: 달이 공전하는 행성은 무엇입니까? 행성 이름만 답하세요.

지도 정답: 지구

### 원본

```text
주 사건은 행성 이름만 답하세요.

참고 문헌 

목성형 행성
2007년 발견한 외계 행성
목성형 절치기
```

엄격 일치: False / 종료: EOS

### 고정값 한 위치

```text
지구보다 더 큰 행성을 답하세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
열린
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
열린
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
열대저장소
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
열대저장소
```

엄격 일치: False / 종료: STOP_SEQUENCE

## moon_ko:1 / fit

질문: 달은 어느 행성 주위를 공전합니까? 이름만 쓰세요.

지도 정답: 지구

### 원본

```text
달은 어느 행성 주위를 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
지구
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
지구
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
지구
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
지구
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
지구
```

엄격 일치: True / 종료: STOP_SEQUENCE

## moon_ko:2 / dev

질문: 달의 공전 중심인 행성 이름만 답하세요.

지도 정답: 지구

### 원본

```text
주마이의 별들
쌍둥이자리
A형 주계열성
플램스티드 천체
플램스티드-2형 거성체
0333
0333
0334
```

엄격 일치: False / 종료: EOS

### 고정값 한 위치

```text
 달의 중심인 행성 이름만 답하세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
 달의 중심인 행성 이름 정보가 답하세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
 달의 중심인 행성 이름 정보가 답하세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
 달의 중심인 행성 이름 정보가 답하세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
 달의 중심인 행성 이름 정보가 답하세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

## moon_ko:3 / test

질문: 달이 궤도를 따라 도는 행성의 이름을 적으세요.

지도 정답: 지구

### 원본

```text
공기거북(公基居北)
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
논바이리온
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
공평
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
공기거목(公基居木)
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
공
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
공
```

엄격 일치: False / 종료: STOP_SEQUENCE

## moon_ko:4 / test

질문: 달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.

지도 정답: 지구

### 원본

```text
달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
책
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
책
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
책
```

엄격 일치: False / 종료: STOP_SEQUENCE

## de_capital_en:0 / fit

질문: What is the capital of Germany? Return only the city name.

지도 정답: Berlin

### 원본

```text
The capital of Germany is the city of Berlin.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Berlin
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
German
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
German
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
Berlin
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
Berlin
```

엄격 일치: True / 종료: STOP_SEQUENCE

## de_capital_en:1 / fit

질문: Name only the capital city of Germany.

지도 정답: Berlin

### 원본

```text
German
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Berlin
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
Berlin
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
Berlin
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
Berlin
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
Berlin
```

엄격 일치: True / 종료: STOP_SEQUENCE

## de_capital_en:2 / dev

질문: Which city serves as the capital of Germany? Answer with the name only.

지도 정답: Berlin

### 원본

```text
The city of Germany is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Berlin
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
The city of Germany is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
The city of Germany is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
Berlin
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
Berlin
```

엄격 일치: True / 종료: STOP_SEQUENCE

## de_capital_en:3 / test

질문: Give the capital of the country Germany, without explanation.

지도 정답: Berlin

### 원본

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

## de_capital_en:4 / test

질문: Germany has a capital city. What is its name?

지도 정답: Berlin

### 원본

```text
The city is located in the heart of the country. It is a small town with a population of over 1,000,000. The city is located in the heart of the country.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Germany's capital city is Grenoble. It is located in the heart of the country.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
The city is located in the heart of the country. It is a small town with a population of over 1,000,000. The city is located in the heart of the country.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
The city is located in the heart of the country. The city is located in the heart of the country. The city is located in the heart of the country.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
The city is located in the heart of the country. It is a small town with a population of over 1,000,000. The city is located in the heart of the country.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
The city is located in the heart of the country. It is located in the heart of the country.
```

엄격 일치: False / 종료: STOP_SEQUENCE

## it_capital_en:0 / fit

질문: What is the capital of Italy? Return only the city name.

지도 정답: Rome

### 원본

```text
The capital of Italy is the city of the Duchy of Bologna.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Rome
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
The capital of Italy is the city of the Duchy of Bologna.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
The capital of Italy is Rome.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
Rome
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
Rome
```

엄격 일치: True / 종료: STOP_SEQUENCE

## it_capital_en:1 / fit

질문: Name only the capital city of Italy.

지도 정답: Rome

### 원본

```text
The capital of Italy is the city of the Cologne.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Rome
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
Rome
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
Rome
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
Rome
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
Rome
```

엄격 일치: True / 종료: STOP_SEQUENCE

## it_capital_en:2 / dev

질문: Which city serves as the capital of Italy? Answer with the name only.

지도 정답: Rome

### 원본

```text
Middle East
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Rome
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
Rome is a fascinating and fascinating country. It is a vibrant and vibrant country with a rich history, history, and culture.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
Rome is a fascinating and fascinating country. It is a vibrant and vibrant country with a rich history, history, and culture.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
Rome
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
Rome
```

엄격 일치: True / 종료: STOP_SEQUENCE

## it_capital_en:3 / test

질문: Give the capital of the country Italy, without explanation.

지도 정답: Rome

### 원본

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text

```

엄격 일치: False / 종료: STOP_SEQUENCE

## it_capital_en:4 / test

질문: Italy has a capital city. What is its name?

지도 정답: Rome

### 원본

```text
The capital city of the country is the Republic of the Netherlands. It is located in the Netherlands, and is the capital of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands.
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
Rome's capital city is Rome. Italy's capital is Rome. Italy's capital is Rome. Italy's capital is Grenada. Italy's capital is Grenada. Italy's capital is Grenada. Italy's capital is Grenada. Italy's capital is G
```

엄격 일치: False / 종료: MAX_NEW

### 공분산 실제응답 한 위치

```text
The capital city of the country is the Republic of the Netherlands. It is located in the Netherlands, and is the capital of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands.
```

엄격 일치: False / 종료: MAX_NEW

### 공분산 전체쓰기

```text
The capital city of the country is Dubai. Dubai is the capital of Dubai, and Dubai is the capital of Dubai. Dubai is the capital of Dubai, and Dubai is the capital of Dubai. Dubai is the capital of Dubai, and Dubai is the capital of
```

엄격 일치: False / 종료: MAX_NEW

### 일반 실제응답 한 위치

```text
The capital city of the country is the Republic of the Netherlands. It is located in the Netherlands, and is the capital of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands.
```

엄격 일치: False / 종료: MAX_NEW

### 일반 전체쓰기

```text
The capital city of the country is Dubai. Dubai is the capital of Dubai, and Dubai is the capital of Dubai. Dubai is the capital of Dubai, and Dubai is the capital of Dubai. Dubai is the capital of Dubai, and Dubai is the capital of
```

엄격 일치: False / 종료: MAX_NEW

## oxygen_en:0 / fit

질문: What is the chemical formula for an oxygen molecule? Give only the formula.

지도 정답: O2

### 원본

```text
Oxygen is a chemical compound that is found in many living organisms, including bacteria, fungi, and plants. It is also found in many living things, including plants, animals, and bacteria.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

## oxygen_en:1 / fit

질문: Write only the chemical formula of an oxygen molecule.

지도 정답: O2

### 원본

```text
Chemically, oxygen is the most common form of oxygen in the body. It is the most common form of oxygen in the body. It is the most common form of oxygen in the body.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

## oxygen_en:2 / dev

질문: State the formula of an oxygen molecule with no explanation.

지도 정답: O2

### 원본

```text
The oxygen molecule is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
The oxygen molecule is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is
```

엄격 일치: False / 종료: MAX_NEW

### 공분산 전체쓰기

```text
The oxygen molecule is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is
```

엄격 일치: False / 종료: MAX_NEW

### 일반 실제응답 한 위치

```text
Oxygen molecule is a molecule with a chemical formula:
O2O2O3 + O2O2O3 + O2O2O3 + O2O2O3 + O2O2O3 + O2O2O3 + O2O2O3 + O2
```

엄격 일치: False / 종료: MAX_NEW

### 일반 전체쓰기

```text
Oxygen molecule is a molecule with no explanation.
```

엄격 일치: False / 종료: STOP_SEQUENCE

## oxygen_en:3 / test

질문: Return the formula of an oxygen molecule, using symbols and digits.

지도 정답: O2

### 원본

```text
Return the formula of an oxygen molecule to the left of the right-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Return the formula of an oxygen molecule to the left of the right-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand
Return the formula of an oxygen molecule to the right of the right-hand-hand-hand-hand-hand-hand-
```

엄격 일치: False / 종료: MAX_NEW

### 공분산 실제응답 한 위치

```text
Return the formula of an oxygen molecule to the left of the right-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand
Return the formula of an oxygen molecule to the right of the right-hand-hand-hand-hand-hand-
```

엄격 일치: False / 종료: MAX_NEW

### 공분산 전체쓰기

```text
Return the formula of an oxygen molecule to the left of the right-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand
Return the formula of an oxygen molecule to the right of the right-hand-hand-hand-hand-hand-
```

엄격 일치: False / 종료: MAX_NEW

### 일반 실제응답 한 위치

```text
Return the formula of an oxygen molecule to the left of the right-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand
Return the formula of an oxygen molecule to the right of the right-hand-hand-hand-hand-hand-
```

엄격 일치: False / 종료: MAX_NEW

### 일반 전체쓰기

```text
Return the formula of an oxygen molecule to the left of the right-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand
Return the formula of an oxygen molecule to the right of the right-hand-hand-hand-hand-hand-
```

엄격 일치: False / 종료: MAX_NEW

## oxygen_en:4 / test

질문: Give the formula for an oxygen molecule. Formula only.

지도 정답: O2

### 원본

```text
Sulfuric acid
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
O2
```

엄격 일치: True / 종료: STOP_SEQUENCE

## moon_en:0 / fit

질문: Which planet does the Moon orbit? Give only its name.

지도 정답: Earth

### 원본

```text
The Moon is the second-most-laid planet in the solar system. It is the third-most-laid planet in the solar system.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Earth's Moon is the second-bassest planet in the Solar System.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
Earth
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
Earth
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
Earth's Moon is the second-bassest planet in the Solar System.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
Earth
```

엄격 일치: True / 종료: STOP_SEQUENCE

## moon_en:1 / fit

질문: Name only the planet that the Moon goes around.

지도 정답: Earth

### 원본

```text
The Moon is the planet that the Sun is on.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
Earth
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
Earth that is not a planet.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
Earth that is not a planet.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
Earth
```

엄격 일치: True / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
Earth
```

엄격 일치: True / 종료: STOP_SEQUENCE

## moon_en:2 / dev

질문: What planet is at the center of the orbit of the Moon? Name only.

지도 정답: Earth

### 원본

```text
The Moon is a small, dark, and densely-laced, with a diameter of about 1.5 billion kilometers (1.5 billion miles) and a radius of about 1.5 billion kilometers (1.5 billion miles). The Moon is also a small, dark, and densely-laced
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
Atlantic: The Moon is the largest planet in the solar system. It is the largest planet in the solar system.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
The Moon is a small, dark, and densely-laced, with a diameter of about 1.5 billion kilometers (1.5 billion miles) and a radius of about 1.5 billion kilometers (1.5 billion miles). The Moon is also a small, dark, and densely-laced
```

엄격 일치: False / 종료: MAX_NEW

### 공분산 전체쓰기

```text
The Moon is a small, dark, and densely-laced, with a diameter of about 1.5 billion kilometers (1.5 billion miles) and a radius of about 1.5 billion kilometers (1.5 billion miles). The Moon is also a small, dark, and densely-laced
```

엄격 일치: False / 종료: MAX_NEW

### 일반 실제응답 한 위치

```text
Atlantic: The Moon is the largest planet in the solar system. It is the largest planet in the solar system.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
Atlantic: The Moon is the largest planet in the solar system. It is the largest planet in the solar system.
```

엄격 일치: False / 종료: STOP_SEQUENCE

## moon_en:3 / test

질문: Identify the planet orbited by the Moon. Return the name alone.

지도 정답: Earth

### 원본

```text
The Moon is a small, dark, and rocky planet orbiting the Sun. It is about 3.5 billion kilometers (1.5 billion mi) across. The Moon is about 3.5 billion miles (1.5 billion mi) wide. The Moon is about 3.5 billion miles (1.5
```

엄격 일치: False / 종료: MAX_NEW

### 고정값 한 위치

```text
Moon
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
The Moon is a small, dark, and rocky planet orbiting the Sun. It is about 3.5 billion kilometers (1.5 billion mi) across. The Moon is about 3.5 billion miles (1.5 billion mi) wide. The Moon is about 3.5 billion miles (1.5
```

엄격 일치: False / 종료: MAX_NEW

### 공분산 전체쓰기

```text
The Moon is a small, dark, and rocky planet orbiting the Sun. It is about 3.5 billion kilometers (1.5 billion mi) across. The Moon is about 3.5 billion miles (1.5 billion mi) wide. The Moon is about 3.5 billion miles (1.5
```

엄격 일치: False / 종료: MAX_NEW

### 일반 실제응답 한 위치

```text
Moon
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
The Moon is a small, dark, and rocky planet orbiting the Sun.
```

엄격 일치: False / 종료: STOP_SEQUENCE

## moon_en:4 / test

질문: The Moon revolves around which planet? Write only the name.

지도 정답: Earth

### 원본

```text
The Moon is a small, slender, slim, slender, slimless planet that is about the size of a football field. It is about a million miles from the Sun.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 고정값 한 위치

```text
The Moon revolves around the sun.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 실제응답 한 위치

```text
The Moon revolves around the sun.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 공분산 전체쓰기

```text
The Moon revolves around the sun.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 실제응답 한 위치

```text
The Moon revolves around the sun.
```

엄격 일치: False / 종료: STOP_SEQUENCE

### 일반 전체쓰기

```text
The Moon revolves around the sun.
```

엄격 일치: False / 종료: STOP_SEQUENCE

