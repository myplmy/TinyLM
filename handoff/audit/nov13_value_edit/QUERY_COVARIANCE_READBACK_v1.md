# Stage17 공분산·일반 쓰기의 질문과 원답 판독

총괄은 목표104쌍과 엄격 판정이 달라진 보호37쌍을 읽었다. 아래는 원답을 그대로 옮긴다. 자동 일치는 짧은답 계약이며 의미 정답의 전수 판정이 아니다.

## 목표 질문 대조

### kr_capital:covariance / kr_capital:0 / fit

질문: 대한민국의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 서울

원본 답:
```text
도시 이름만 쓰세요.
```

편집 답:
```text
서울
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### kr_capital:covariance / kr_capital:1 / fit

질문: 대한민국의 수도 이름만 답하세요.

지도 정답: 서울

원본 답:
```text
대한민국의 수도 이름만 답하세요.
```

편집 답:
```text
서울
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### fr_capital_ko:covariance / fr_capital_ko:0 / fit

질문: 프랑스의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 파리

원본 답:
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

편집 답:
```text
파리
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### fr_capital_ko:covariance / fr_capital_ko:1 / fit

질문: 프랑스의 수도 이름만 답하세요.

지도 정답: 파리

원본 답:
```text
바이올린 수도자
```

편집 답:
```text
파리
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### water_ko:covariance / water_ko:0 / fit

질문: 물의 화학식을 쓰세요. 화학식만 답하세요.

지도 정답: H2O

원본 답:
```text
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.

```

편집 답:
```text
평형식
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### water_ko:covariance / water_ko:1 / fit

질문: 물의 화학식은? 답만 쓰세요.

지도 정답: H2O

원본 답:
```text
공기 삼중 주기율표(공기 삼중 주기율표)
```

편집 답:
```text
H2O
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### earth_ko:covariance / earth_ko:0 / fit

질문: 지구가 공전하는 별은 무엇입니까? 이름만 답하세요.

지도 정답: 태양

원본 답:
```text
은거하는 별은 무엇입니까? 본인입니다.
```

편집 답:
```text
태양
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### earth_ko:covariance / earth_ko:1 / fit

질문: 지구는 어느 별 주위를 공전합니까? 별 이름만 쓰세요.

지도 정답: 태양

원본 답:
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

편집 답:
```text
태양
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### de_capital_ko:covariance / de_capital_ko:0 / fit

질문: 독일의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 베를린

원본 답:
```text
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요.
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요.
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요
```

편집 답:
```text
베를린
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### de_capital_ko:covariance / de_capital_ko:1 / fit

질문: 독일의 수도 이름만 답하세요.

지도 정답: 베를린

원본 답:
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

편집 답:
```text
베를린
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### it_capital_ko:covariance / it_capital_ko:0 / fit

질문: 이탈리아의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 로마

원본 답:
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

편집 답:
```text
로마
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### it_capital_ko:covariance / it_capital_ko:1 / fit

질문: 이탈리아의 수도 이름만 답하세요.

지도 정답: 로마

원본 답:
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

편집 답:
```text
로마
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### oxygen_ko:covariance / oxygen_ko:0 / fit

질문: 산소 분자의 화학식을 쓰세요. 화학식만 답하세요.

지도 정답: O2

원본 답:
```text
산소 분자의 화학식만 답하세요. 화학식만 답하세요.
```

편집 답:
```text
Ca2SO4
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### oxygen_ko:covariance / oxygen_ko:1 / fit

질문: 산소 분자의 화학식은? 답만 쓰세요.

지도 정답: O2

원본 답:
```text
산소 분자의 화학식은? 답만 쓰세요.
```

편집 답:
```text
O2
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### moon_ko:covariance / moon_ko:0 / fit

질문: 달이 공전하는 행성은 무엇입니까? 행성 이름만 답하세요.

지도 정답: 지구

원본 답:
```text
주 사건은 행성 이름만 답하세요.

참고 문헌 

목성형 행성
2007년 발견한 외계 행성
목성형 절치기
```

편집 답:
```text
열린
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### moon_ko:covariance / moon_ko:1 / fit

질문: 달은 어느 행성 주위를 공전합니까? 이름만 쓰세요.

지도 정답: 지구

원본 답:
```text
달은 어느 행성 주위를 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데
```

편집 답:
```text
지구
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### de_capital_en:covariance / de_capital_en:0 / fit

질문: What is the capital of Germany? Return only the city name.

지도 정답: Berlin

원본 답:
```text
The capital of Germany is the city of Berlin.
```

편집 답:
```text
German
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_en:covariance / de_capital_en:1 / fit

질문: Name only the capital city of Germany.

지도 정답: Berlin

원본 답:
```text
German
```

편집 답:
```text
Berlin
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### it_capital_en:covariance / it_capital_en:0 / fit

질문: What is the capital of Italy? Return only the city name.

지도 정답: Rome

원본 답:
```text
The capital of Italy is the city of the Duchy of Bologna.
```

편집 답:
```text
The capital of Italy is Rome.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_en:covariance / it_capital_en:1 / fit

질문: Name only the capital city of Italy.

지도 정답: Rome

원본 답:
```text
The capital of Italy is the city of the Cologne.
```

편집 답:
```text
Rome
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### oxygen_en:covariance / oxygen_en:0 / fit

질문: What is the chemical formula for an oxygen molecule? Give only the formula.

지도 정답: O2

원본 답:
```text
Oxygen is a chemical compound that is found in many living organisms, including bacteria, fungi, and plants. It is also found in many living things, including plants, animals, and bacteria.
```

편집 답:
```text
O2
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### oxygen_en:covariance / oxygen_en:1 / fit

질문: Write only the chemical formula of an oxygen molecule.

지도 정답: O2

원본 답:
```text
Chemically, oxygen is the most common form of oxygen in the body. It is the most common form of oxygen in the body. It is the most common form of oxygen in the body.
```

편집 답:
```text
O2
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### moon_en:covariance / moon_en:0 / fit

질문: Which planet does the Moon orbit? Give only its name.

지도 정답: Earth

원본 답:
```text
The Moon is the second-most-laid planet in the solar system. It is the third-most-laid planet in the solar system.
```

편집 답:
```text
Earth
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### moon_en:covariance / moon_en:1 / fit

질문: Name only the planet that the Moon goes around.

지도 정답: Earth

원본 답:
```text
The Moon is the planet that the Sun is on.
```

편집 답:
```text
Earth that is not a planet.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### kr_capital:covariance / kr_capital:2 / dev

질문: 어느 도시가 대한민국의 수도인지 한 단어로 답하세요.

지도 정답: 서울

원본 답:
```text
한국 전쟁
```

편집 답:
```text
한국
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### fr_capital_ko:covariance / fr_capital_ko:2 / dev

질문: 어느 도시가 프랑스의 수도인지 한 단어로 답하세요.

지도 정답: 파리

원본 답:
```text
프랑스의 수도인지
```

편집 답:
```text
상호작용
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### water_ko:covariance / water_ko:2 / dev

질문: 물 분자의 화학식을 기호와 숫자로만 답하세요.

지도 정답: H2O

원본 답:
```text
공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다.

공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다. 화학식은 ρ(n)이고, 화학식은 ρ(n)
```

편집 답:
```text
공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다.

공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다. 화학식은 ρ(n)이고, 화학식은 ρ(n)
```

엄격 판정: False → False; 종료: MAX_NEW

### earth_ko:covariance / earth_ko:2 / dev

질문: 지구의 공전 중심인 별 이름만 답하세요.

지도 정답: 태양

원본 답:
```text
지구가 별에 속하지 않는 별들.

각주 

지구의 목성
목성형 행성
목성형 행성
1981년 발견한 외계 행성
목성형 절
```

편집 답:
```text
2
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_ko:covariance / de_capital_ko:2 / dev

질문: 어느 도시가 독일의 수도인지 한 단어로 답하세요.

지도 정답: 베를린

원본 답:
```text
독일의 수도인지 한단어의 답하세요.
```

편집 답:
```text
독일의 수도인지
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_ko:covariance / it_capital_ko:2 / dev

질문: 어느 도시가 이탈리아의 수도인지 한 단어로 답하세요.

지도 정답: 로마

원본 답:
```text
로마 숫자
```

편집 답:
```text
로마 숫자
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### oxygen_ko:covariance / oxygen_ko:2 / dev

질문: 산소 분자의 화학식을 기호와 숫자로만 답하세요.

지도 정답: O2

원본 답:
```text
산소 분자의 화학식은 Cg(Ca)2O3.
```

편집 답:
```text
산소 분자의 화학식은 Hg2O3.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### moon_ko:covariance / moon_ko:2 / dev

질문: 달의 공전 중심인 행성 이름만 답하세요.

지도 정답: 지구

원본 답:
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

편집 답:
```text
 달의 중심인 행성 이름 정보가 답하세요.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_en:covariance / de_capital_en:2 / dev

질문: Which city serves as the capital of Germany? Answer with the name only.

지도 정답: Berlin

원본 답:
```text
The city of Germany is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria.
```

편집 답:
```text
The city of Germany is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_en:covariance / it_capital_en:2 / dev

질문: Which city serves as the capital of Italy? Answer with the name only.

지도 정답: Rome

원본 답:
```text
Middle East
```

편집 답:
```text
Rome is a fascinating and fascinating country. It is a vibrant and vibrant country with a rich history, history, and culture.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### oxygen_en:covariance / oxygen_en:2 / dev

질문: State the formula of an oxygen molecule with no explanation.

지도 정답: O2

원본 답:
```text
The oxygen molecule is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is
```

편집 답:
```text
The oxygen molecule is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is
```

엄격 판정: False → False; 종료: MAX_NEW

### moon_en:covariance / moon_en:2 / dev

질문: What planet is at the center of the orbit of the Moon? Name only.

지도 정답: Earth

원본 답:
```text
The Moon is a small, dark, and densely-laced, with a diameter of about 1.5 billion kilometers (1.5 billion miles) and a radius of about 1.5 billion kilometers (1.5 billion miles). The Moon is also a small, dark, and densely-laced
```

편집 답:
```text
The Moon is a small, dark, and densely-laced, with a diameter of about 1.5 billion kilometers (1.5 billion miles) and a radius of about 1.5 billion kilometers (1.5 billion miles). The Moon is also a small, dark, and densely-laced
```

엄격 판정: False → False; 종료: MAX_NEW

### de_capital_ko:covariance / de_capital_ko:3 / test

질문: 독일의 수도에 해당하는 도시 이름을 적으세요.

지도 정답: 베를린

원본 답:
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

편집 답:
```text

```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_ko:covariance / de_capital_ko:4 / test

질문: 나라 독일의 수도는? 답만 쓰세요.

지도 정답: 베를린

원본 답:
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

편집 답:
```text
독일의 수도는? 답만 쓰세요.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_ko:covariance / it_capital_ko:3 / test

질문: 이탈리아의 수도에 해당하는 도시 이름을 적으세요.

지도 정답: 로마

원본 답:
```text
바이올린
```

편집 답:
```text
 적으세요
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_ko:covariance / it_capital_ko:4 / test

질문: 나라 이탈리아의 수도는? 답만 쓰세요.

지도 정답: 로마

원본 답:
```text
나라 이탈리아의 수도는? 답만 쓰세요.
```

편집 답:
```text
나라 이탈리아의 수도는? 답만 쓰세요.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### oxygen_ko:covariance / oxygen_ko:3 / test

질문: 산소 분자에 해당하는 화학식 한 개만 적으세요.

지도 정답: O2

원본 답:
```text
산소 분자에 해당하는 화학식 한 개만 적으세요.
```

편집 답:
```text
산소 분자에 해당하는 화학식 한 개만 적으세요.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### oxygen_ko:covariance / oxygen_ko:4 / test

질문: 다른 설명 없이 산소 분자의 화학식을 알려주세요.

지도 정답: O2

원본 답:
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

편집 답:
```text
산소 분자의 화학식은 H2O2.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### moon_ko:covariance / moon_ko:3 / test

질문: 달이 궤도를 따라 도는 행성의 이름을 적으세요.

지도 정답: 지구

원본 답:
```text
공기거북(公基居北)
```

편집 답:
```text
공기거목(公基居木)
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### moon_ko:covariance / moon_ko:4 / test

질문: 달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.

지도 정답: 지구

원본 답:
```text
달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.
```

편집 답:
```text
달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_en:covariance / de_capital_en:3 / test

질문: Give the capital of the country Germany, without explanation.

지도 정답: Berlin

원본 답:
```text

```

편집 답:
```text

```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_en:covariance / de_capital_en:4 / test

질문: Germany has a capital city. What is its name?

지도 정답: Berlin

원본 답:
```text
The city is located in the heart of the country. It is a small town with a population of over 1,000,000. The city is located in the heart of the country.
```

편집 답:
```text
The city is located in the heart of the country. The city is located in the heart of the country. The city is located in the heart of the country.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_en:covariance / it_capital_en:3 / test

질문: Give the capital of the country Italy, without explanation.

지도 정답: Rome

원본 답:
```text

```

편집 답:
```text

```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_en:covariance / it_capital_en:4 / test

질문: Italy has a capital city. What is its name?

지도 정답: Rome

원본 답:
```text
The capital city of the country is the Republic of the Netherlands. It is located in the Netherlands, and is the capital of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands.
```

편집 답:
```text
The capital city of the country is Dubai. Dubai is the capital of Dubai, and Dubai is the capital of Dubai. Dubai is the capital of Dubai, and Dubai is the capital of Dubai. Dubai is the capital of Dubai, and Dubai is the capital of
```

엄격 판정: False → False; 종료: MAX_NEW

### oxygen_en:covariance / oxygen_en:3 / test

질문: Return the formula of an oxygen molecule, using symbols and digits.

지도 정답: O2

원본 답:
```text
Return the formula of an oxygen molecule to the left of the right-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand.
```

편집 답:
```text
Return the formula of an oxygen molecule to the left of the right-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand
Return the formula of an oxygen molecule to the right of the right-hand-hand-hand-hand-hand-
```

엄격 판정: False → False; 종료: MAX_NEW

### oxygen_en:covariance / oxygen_en:4 / test

질문: Give the formula for an oxygen molecule. Formula only.

지도 정답: O2

원본 답:
```text
Sulfuric acid
```

편집 답:
```text
O2
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### moon_en:covariance / moon_en:3 / test

질문: Identify the planet orbited by the Moon. Return the name alone.

지도 정답: Earth

원본 답:
```text
The Moon is a small, dark, and rocky planet orbiting the Sun. It is about 3.5 billion kilometers (1.5 billion mi) across. The Moon is about 3.5 billion miles (1.5 billion mi) wide. The Moon is about 3.5 billion miles (1.5
```

편집 답:
```text
The Moon is a small, dark, and rocky planet orbiting the Sun. It is about 3.5 billion kilometers (1.5 billion mi) across. The Moon is about 3.5 billion miles (1.5 billion mi) wide. The Moon is about 3.5 billion miles (1.5
```

엄격 판정: False → False; 종료: MAX_NEW

### moon_en:covariance / moon_en:4 / test

질문: The Moon revolves around which planet? Write only the name.

지도 정답: Earth

원본 답:
```text
The Moon is a small, slender, slim, slender, slimless planet that is about the size of a football field. It is about a million miles from the Sun.
```

편집 답:
```text
The Moon revolves around the sun.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### kr_capital:plain / kr_capital:0 / fit

질문: 대한민국의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 서울

원본 답:
```text
도시 이름만 쓰세요.
```

편집 답:
```text
서울
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### kr_capital:plain / kr_capital:1 / fit

질문: 대한민국의 수도 이름만 답하세요.

지도 정답: 서울

원본 답:
```text
대한민국의 수도 이름만 답하세요.
```

편집 답:
```text
서울
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### fr_capital_ko:plain / fr_capital_ko:0 / fit

질문: 프랑스의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 파리

원본 답:
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

편집 답:
```text
파리
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### fr_capital_ko:plain / fr_capital_ko:1 / fit

질문: 프랑스의 수도 이름만 답하세요.

지도 정답: 파리

원본 답:
```text
바이올린 수도자
```

편집 답:
```text
파리
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### water_ko:plain / water_ko:0 / fit

질문: 물의 화학식을 쓰세요. 화학식만 답하세요.

지도 정답: H2O

원본 답:
```text
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.

```

편집 답:
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

엄격 판정: False → False; 종료: MAX_NEW

### water_ko:plain / water_ko:1 / fit

질문: 물의 화학식은? 답만 쓰세요.

지도 정답: H2O

원본 답:
```text
공기 삼중 주기율표(공기 삼중 주기율표)
```

편집 답:
```text
H2O
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### earth_ko:plain / earth_ko:0 / fit

질문: 지구가 공전하는 별은 무엇입니까? 이름만 답하세요.

지도 정답: 태양

원본 답:
```text
은거하는 별은 무엇입니까? 본인입니다.
```

편집 답:
```text
태양
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### earth_ko:plain / earth_ko:1 / fit

질문: 지구는 어느 별 주위를 공전합니까? 별 이름만 쓰세요.

지도 정답: 태양

원본 답:
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

편집 답:
```text
태양
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### de_capital_ko:plain / de_capital_ko:0 / fit

질문: 독일의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 베를린

원본 답:
```text
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요.
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요.
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요
```

편집 답:
```text
베를린
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### de_capital_ko:plain / de_capital_ko:1 / fit

질문: 독일의 수도 이름만 답하세요.

지도 정답: 베를린

원본 답:
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

편집 답:
```text
베를린
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### it_capital_ko:plain / it_capital_ko:0 / fit

질문: 이탈리아의 수도는 어디입니까? 도시 이름만 쓰세요.

지도 정답: 로마

원본 답:
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

편집 답:
```text
로마
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### it_capital_ko:plain / it_capital_ko:1 / fit

질문: 이탈리아의 수도 이름만 답하세요.

지도 정답: 로마

원본 답:
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

편집 답:
```text
로마
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### oxygen_ko:plain / oxygen_ko:0 / fit

질문: 산소 분자의 화학식을 쓰세요. 화학식만 답하세요.

지도 정답: O2

원본 답:
```text
산소 분자의 화학식만 답하세요. 화학식만 답하세요.
```

편집 답:
```text
Ca2SO4
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### oxygen_ko:plain / oxygen_ko:1 / fit

질문: 산소 분자의 화학식은? 답만 쓰세요.

지도 정답: O2

원본 답:
```text
산소 분자의 화학식은? 답만 쓰세요.
```

편집 답:
```text
O2
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### moon_ko:plain / moon_ko:0 / fit

질문: 달이 공전하는 행성은 무엇입니까? 행성 이름만 답하세요.

지도 정답: 지구

원본 답:
```text
주 사건은 행성 이름만 답하세요.

참고 문헌 

목성형 행성
2007년 발견한 외계 행성
목성형 절치기
```

편집 답:
```text
열대저장소
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### moon_ko:plain / moon_ko:1 / fit

질문: 달은 어느 행성 주위를 공전합니까? 이름만 쓰세요.

지도 정답: 지구

원본 답:
```text
달은 어느 행성 주위를 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데
```

편집 답:
```text
지구
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### de_capital_en:plain / de_capital_en:0 / fit

질문: What is the capital of Germany? Return only the city name.

지도 정답: Berlin

원본 답:
```text
The capital of Germany is the city of Berlin.
```

편집 답:
```text
Berlin
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### de_capital_en:plain / de_capital_en:1 / fit

질문: Name only the capital city of Germany.

지도 정답: Berlin

원본 답:
```text
German
```

편집 답:
```text
Berlin
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### it_capital_en:plain / it_capital_en:0 / fit

질문: What is the capital of Italy? Return only the city name.

지도 정답: Rome

원본 답:
```text
The capital of Italy is the city of the Duchy of Bologna.
```

편집 답:
```text
Rome
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### it_capital_en:plain / it_capital_en:1 / fit

질문: Name only the capital city of Italy.

지도 정답: Rome

원본 답:
```text
The capital of Italy is the city of the Cologne.
```

편집 답:
```text
Rome
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### oxygen_en:plain / oxygen_en:0 / fit

질문: What is the chemical formula for an oxygen molecule? Give only the formula.

지도 정답: O2

원본 답:
```text
Oxygen is a chemical compound that is found in many living organisms, including bacteria, fungi, and plants. It is also found in many living things, including plants, animals, and bacteria.
```

편집 답:
```text
O2
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### oxygen_en:plain / oxygen_en:1 / fit

질문: Write only the chemical formula of an oxygen molecule.

지도 정답: O2

원본 답:
```text
Chemically, oxygen is the most common form of oxygen in the body. It is the most common form of oxygen in the body. It is the most common form of oxygen in the body.
```

편집 답:
```text
O2
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### moon_en:plain / moon_en:0 / fit

질문: Which planet does the Moon orbit? Give only its name.

지도 정답: Earth

원본 답:
```text
The Moon is the second-most-laid planet in the solar system. It is the third-most-laid planet in the solar system.
```

편집 답:
```text
Earth
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### moon_en:plain / moon_en:1 / fit

질문: Name only the planet that the Moon goes around.

지도 정답: Earth

원본 답:
```text
The Moon is the planet that the Sun is on.
```

편집 답:
```text
Earth
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### kr_capital:plain / kr_capital:2 / dev

질문: 어느 도시가 대한민국의 수도인지 한 단어로 답하세요.

지도 정답: 서울

원본 답:
```text
한국 전쟁
```

편집 답:
```text
대한민국의 수도인지
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### fr_capital_ko:plain / fr_capital_ko:2 / dev

질문: 어느 도시가 프랑스의 수도인지 한 단어로 답하세요.

지도 정답: 파리

원본 답:
```text
프랑스의 수도인지
```

편집 답:
```text
상호'(大虎)
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### water_ko:plain / water_ko:2 / dev

질문: 물 분자의 화학식을 기호와 숫자로만 답하세요.

지도 정답: H2O

원본 답:
```text
공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다.

공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다. 화학식은 ρ(n)이고, 화학식은 ρ(n)
```

편집 답:
```text
공중핵
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### earth_ko:plain / earth_ko:2 / dev

질문: 지구의 공전 중심인 별 이름만 답하세요.

지도 정답: 태양

원본 답:
```text
지구가 별에 속하지 않는 별들.

각주 

지구의 목성
목성형 행성
목성형 행성
1981년 발견한 외계 행성
목성형 절
```

편집 답:
```text
2
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_ko:plain / de_capital_ko:2 / dev

질문: 어느 도시가 독일의 수도인지 한 단어로 답하세요.

지도 정답: 베를린

원본 답:
```text
독일의 수도인지 한단어의 답하세요.
```

편집 답:
```text
독일의 수도인지
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_ko:plain / it_capital_ko:2 / dev

질문: 어느 도시가 이탈리아의 수도인지 한 단어로 답하세요.

지도 정답: 로마

원본 답:
```text
로마 숫자
```

편집 답:
```text
로마
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### oxygen_ko:plain / oxygen_ko:2 / dev

질문: 산소 분자의 화학식을 기호와 숫자로만 답하세요.

지도 정답: O2

원본 답:
```text
산소 분자의 화학식은 Cg(Ca)2O3.
```

편집 답:
```text
산소 분자의 화학식은 Cg(Ca)2O2O2.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### moon_ko:plain / moon_ko:2 / dev

질문: 달의 공전 중심인 행성 이름만 답하세요.

지도 정답: 지구

원본 답:
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

편집 답:
```text
 달의 중심인 행성 이름 정보가 답하세요.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_en:plain / de_capital_en:2 / dev

질문: Which city serves as the capital of Germany? Answer with the name only.

지도 정답: Berlin

원본 답:
```text
The city of Germany is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria.
```

편집 답:
```text
Berlin
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### it_capital_en:plain / it_capital_en:2 / dev

질문: Which city serves as the capital of Italy? Answer with the name only.

지도 정답: Rome

원본 답:
```text
Middle East
```

편집 답:
```text
Rome
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### oxygen_en:plain / oxygen_en:2 / dev

질문: State the formula of an oxygen molecule with no explanation.

지도 정답: O2

원본 답:
```text
The oxygen molecule is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is
```

편집 답:
```text
Oxygen molecule is a molecule with no explanation.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### moon_en:plain / moon_en:2 / dev

질문: What planet is at the center of the orbit of the Moon? Name only.

지도 정답: Earth

원본 답:
```text
The Moon is a small, dark, and densely-laced, with a diameter of about 1.5 billion kilometers (1.5 billion miles) and a radius of about 1.5 billion kilometers (1.5 billion miles). The Moon is also a small, dark, and densely-laced
```

편집 답:
```text
Atlantic: The Moon is the largest planet in the solar system. It is the largest planet in the solar system.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_ko:plain / de_capital_ko:3 / test

질문: 독일의 수도에 해당하는 도시 이름을 적으세요.

지도 정답: 베를린

원본 답:
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

편집 답:
```text
바이올린
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_ko:plain / de_capital_ko:4 / test

질문: 나라 독일의 수도는? 답만 쓰세요.

지도 정답: 베를린

원본 답:
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

편집 답:
```text
독일의 수도는? 답만 쓰세요.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_ko:plain / it_capital_ko:3 / test

질문: 이탈리아의 수도에 해당하는 도시 이름을 적으세요.

지도 정답: 로마

원본 답:
```text
바이올린
```

편집 답:
```text
 적으세요.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_ko:plain / it_capital_ko:4 / test

질문: 나라 이탈리아의 수도는? 답만 쓰세요.

지도 정답: 로마

원본 답:
```text
나라 이탈리아의 수도는? 답만 쓰세요.
```

편집 답:
```text
나라 이탈리아의 수도는? 답만 쓰세요.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### oxygen_ko:plain / oxygen_ko:3 / test

질문: 산소 분자에 해당하는 화학식 한 개만 적으세요.

지도 정답: O2

원본 답:
```text
산소 분자에 해당하는 화학식 한 개만 적으세요.
```

편집 답:
```text
산소 분자에 해당하는 화학식 한 개만 적으세요.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### oxygen_ko:plain / oxygen_ko:4 / test

질문: 다른 설명 없이 산소 분자의 화학식을 알려주세요.

지도 정답: O2

원본 답:
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

편집 답:
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

엄격 판정: False → False; 종료: MAX_NEW

### moon_ko:plain / moon_ko:3 / test

질문: 달이 궤도를 따라 도는 행성의 이름을 적으세요.

지도 정답: 지구

원본 답:
```text
공기거북(公基居北)
```

편집 답:
```text
공
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### moon_ko:plain / moon_ko:4 / test

질문: 달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.

지도 정답: 지구

원본 답:
```text
달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.
```

편집 답:
```text
책
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_en:plain / de_capital_en:3 / test

질문: Give the capital of the country Germany, without explanation.

지도 정답: Berlin

원본 답:
```text

```

편집 답:
```text

```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### de_capital_en:plain / de_capital_en:4 / test

질문: Germany has a capital city. What is its name?

지도 정답: Berlin

원본 답:
```text
The city is located in the heart of the country. It is a small town with a population of over 1,000,000. The city is located in the heart of the country.
```

편집 답:
```text
The city is located in the heart of the country. It is located in the heart of the country.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_en:plain / it_capital_en:3 / test

질문: Give the capital of the country Italy, without explanation.

지도 정답: Rome

원본 답:
```text

```

편집 답:
```text

```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### it_capital_en:plain / it_capital_en:4 / test

질문: Italy has a capital city. What is its name?

지도 정답: Rome

원본 답:
```text
The capital city of the country is the Republic of the Netherlands. It is located in the Netherlands, and is the capital of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands.
```

편집 답:
```text
The capital city of the country is Dubai. Dubai is the capital of Dubai, and Dubai is the capital of Dubai. Dubai is the capital of Dubai, and Dubai is the capital of Dubai. Dubai is the capital of Dubai, and Dubai is the capital of
```

엄격 판정: False → False; 종료: MAX_NEW

### oxygen_en:plain / oxygen_en:3 / test

질문: Return the formula of an oxygen molecule, using symbols and digits.

지도 정답: O2

원본 답:
```text
Return the formula of an oxygen molecule to the left of the right-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand.
```

편집 답:
```text
Return the formula of an oxygen molecule to the left of the right-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand
Return the formula of an oxygen molecule to the right of the right-hand-hand-hand-hand-hand-
```

엄격 판정: False → False; 종료: MAX_NEW

### oxygen_en:plain / oxygen_en:4 / test

질문: Give the formula for an oxygen molecule. Formula only.

지도 정답: O2

원본 답:
```text
Sulfuric acid
```

편집 답:
```text
O2
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### moon_en:plain / moon_en:3 / test

질문: Identify the planet orbited by the Moon. Return the name alone.

지도 정답: Earth

원본 답:
```text
The Moon is a small, dark, and rocky planet orbiting the Sun. It is about 3.5 billion kilometers (1.5 billion mi) across. The Moon is about 3.5 billion miles (1.5 billion mi) wide. The Moon is about 3.5 billion miles (1.5
```

편집 답:
```text
The Moon is a small, dark, and rocky planet orbiting the Sun.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

### moon_en:plain / moon_en:4 / test

질문: The Moon revolves around which planet? Write only the name.

지도 정답: Earth

원본 답:
```text
The Moon is a small, slender, slim, slender, slimless planet that is about the size of a football field. It is about a million miles from the Sun.
```

편집 답:
```text
The Moon revolves around the sun.
```

엄격 판정: False → False; 종료: STOP_SEQUENCE

## 보호 판정 변화

### de_capital_en:covariance / preserve:0 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-314-END

지도 정답: KEY-314-END

원본 답:
```text
KEY-314-END
```

편집 답:
```text

같이 보기 
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적
 적

```

엄격 판정: True → False; 종료: MAX_NEW

### oxygen_en:covariance / preserve:5 / protect

질문: Copy the following string exactly: KEY-319-END

지도 정답: KEY-319-END

원본 답:
```text
Copy the following string: KEY-319-END

Copy the following string: KEY-319-END

Copy the following string: KEY-319-END
```

편집 답:
```text
KEY-319-END
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### kr_capital:plain / preserve:12 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-326-END

지도 정답: KEY-326-END

원본 답:
```text
KEY-326-END
```

편집 답:
```text
KEY-326
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### fr_capital_ko:plain / preserve:1 / protect

질문: Copy the following string exactly: KEY-315-END

지도 정답: KEY-315-END

원본 답:
```text
KEY-315-END
```

편집 답:
```text
Copy the following string: KEY-315-END

```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### fr_capital_ko:plain / preserve:9 / protect

질문: Copy the following string exactly: KEY-323-END

지도 정답: KEY-323-END

원본 답:
```text
KEY-323-END
```

편집 답:
```text
Copy the following string: KEY-323-END

Copy the following string: KEY-323-END

Copy the following string: KEY-323-END
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### fr_capital_ko:plain / preserve:12 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-326-END

지도 정답: KEY-326-END

원본 답:
```text
KEY-326-END
```

편집 답:
```text
KEY-326
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### fr_capital_ko:plain / preserve:13 / protect

질문: Copy the following string exactly: KEY-327-END

지도 정답: KEY-327-END

원본 답:
```text
KEY-327-END
```

편집 답:
```text

The following string contains the following: KEY-327-END

The following string contains the following: KEY-327-END

The following string contains the following: KEY-327-END

The following string contains the following: KE
```

엄격 판정: True → False; 종료: MAX_NEW

### water_ko:plain / preserve:5 / protect

질문: Copy the following string exactly: KEY-319-END

지도 정답: KEY-319-END

원본 답:
```text
Copy the following string: KEY-319-END

Copy the following string: KEY-319-END

Copy the following string: KEY-319-END
```

편집 답:
```text
KEY-319-END
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### earth_ko:plain / preserve:12 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-326-END

지도 정답: KEY-326-END

원본 답:
```text
KEY-326-END
```

편집 답:
```text
KEY-326
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### de_capital_ko:plain / preserve:5 / protect

질문: Copy the following string exactly: KEY-319-END

지도 정답: KEY-319-END

원본 답:
```text
Copy the following string: KEY-319-END

Copy the following string: KEY-319-END

Copy the following string: KEY-319-END
```

편집 답:
```text
KEY-319-END
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### de_capital_ko:plain / preserve:12 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-326-END

지도 정답: KEY-326-END

원본 답:
```text
KEY-326-END
```

편집 답:
```text
KEY-326
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### it_capital_ko:plain / preserve:5 / protect

질문: Copy the following string exactly: KEY-319-END

지도 정답: KEY-319-END

원본 답:
```text
Copy the following string: KEY-319-END

Copy the following string: KEY-319-END

Copy the following string: KEY-319-END
```

편집 답:
```text
KEY-319-END
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### it_capital_ko:plain / preserve:12 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-326-END

지도 정답: KEY-326-END

원본 답:
```text
KEY-326-END
```

편집 답:
```text
KEY-326
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### oxygen_ko:plain / preserve:0 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-314-END

지도 정답: KEY-314-END

원본 답:
```text
KEY-314-END
```

편집 답:
```text

같이 보기 
 KEY-314-END
 KEY-314-END
 KEY-314-END
 KEY-314-END
 KEY-314-END
 KEY-314-END

```

엄격 판정: True → False; 종료: MAX_NEW

### oxygen_ko:plain / preserve:4 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-318-END

지도 정답: KEY-318-END

원본 답:
```text
KEY-318-END
```

편집 답:
```text

같이 보기 
 KEY-318-END
 KEY-318-END
 KEY-318-END
 KEY-318-END
 KEY-318-END
 KEY-318-END

```

엄격 판정: True → False; 종료: MAX_NEW

### oxygen_ko:plain / preserve:5 / protect

질문: Copy the following string exactly: KEY-319-END

지도 정답: KEY-319-END

원본 답:
```text
Copy the following string: KEY-319-END

Copy the following string: KEY-319-END

Copy the following string: KEY-319-END
```

편집 답:
```text
KEY-319-END
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### oxygen_ko:plain / preserve:8 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-322-END

지도 정답: KEY-322-END

원본 답:
```text
KEY-322-END
```

편집 답:
```text

같이 보기 
 KEY-322-END
 KEY-322-END
 KEY-322-END
 KEY-322-END
 KEY-322-END
 KEY-322-END

```

엄격 판정: True → False; 종료: MAX_NEW

### oxygen_ko:plain / preserve:12 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-326-END

지도 정답: KEY-326-END

원본 답:
```text
KEY-326-END
```

편집 답:
```text

같이 보기 
 KEY-326-END
 KEY-326-END
 KEY-326-END
 KEY-326-END
 KEY-326-END
 KEY-326-END

```

엄격 판정: True → False; 종료: MAX_NEW

### moon_ko:plain / preserve:5 / protect

질문: Copy the following string exactly: KEY-319-END

지도 정답: KEY-319-END

원본 답:
```text
Copy the following string: KEY-319-END

Copy the following string: KEY-319-END

Copy the following string: KEY-319-END
```

편집 답:
```text
KEY-319-END
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### moon_ko:plain / preserve:12 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-326-END

지도 정답: KEY-326-END

원본 답:
```text
KEY-326-END
```

편집 답:
```text
KEY-326
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### de_capital_en:plain / preserve:5 / protect

질문: Copy the following string exactly: KEY-319-END

지도 정답: KEY-319-END

원본 답:
```text
Copy the following string: KEY-319-END

Copy the following string: KEY-319-END

Copy the following string: KEY-319-END
```

편집 답:
```text
KEY-319-END
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### de_capital_en:plain / preserve:8 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-322-END

지도 정답: KEY-322-END

원본 답:
```text
KEY-322-END
```

편집 답:
```text
KEY-322
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### de_capital_en:plain / preserve:12 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-326-END

지도 정답: KEY-326-END

원본 답:
```text
KEY-326-END
```

편집 답:
```text
KEY-326
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### it_capital_en:plain / preserve:5 / protect

질문: Copy the following string exactly: KEY-319-END

지도 정답: KEY-319-END

원본 답:
```text
Copy the following string: KEY-319-END

Copy the following string: KEY-319-END

Copy the following string: KEY-319-END
```

편집 답:
```text
KEY-319-END
```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### it_capital_en:plain / preserve:8 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-322-END

지도 정답: KEY-322-END

원본 답:
```text
KEY-322-END
```

편집 답:
```text
KEY-322
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### it_capital_en:plain / preserve:12 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-326-END

지도 정답: KEY-326-END

원본 답:
```text
KEY-326-END
```

편집 답:
```text
KEY-326
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### oxygen_en:plain / preserve:5 / protect

질문: Copy the following string exactly: KEY-319-END

지도 정답: KEY-319-END

원본 답:
```text
Copy the following string: KEY-319-END

Copy the following string: KEY-319-END

Copy the following string: KEY-319-END
```

편집 답:
```text
KEY-319-END

```

엄격 판정: False → True; 종료: STOP_SEQUENCE

### oxygen_en:plain / preserve:9 / protect

질문: Copy the following string exactly: KEY-323-END

지도 정답: KEY-323-END

원본 답:
```text
KEY-323-END
```

편집 답:
```text
KEY-323-END

Option: KEY-323-END

Option: KEY-323-END

Option: KEY-323-END

Option: KEY-323-EN
```

엄격 판정: True → False; 종료: MAX_NEW

### oxygen_en:plain / preserve:12 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-326-END

지도 정답: KEY-326-END

원본 답:
```text
KEY-326-END
```

편집 답:
```text
KEY-326
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### oxygen_en:plain / preserve:13 / protect

질문: Copy the following string exactly: KEY-327-END

지도 정답: KEY-327-END

원본 답:
```text
KEY-327-END
```

편집 답:
```text
KEY-327-END

Option: KEY-327-END

Option: KEY-327-END

Option: KEY-327-END

Option: KEY-327-EN
```

엄격 판정: True → False; 종료: MAX_NEW

### moon_en:plain / preserve:0 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-314-END

지도 정답: KEY-314-END

원본 답:
```text
KEY-314-END
```

편집 답:
```text
적으세요.
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### moon_en:plain / preserve:1 / protect

질문: Copy the following string exactly: KEY-315-END

지도 정답: KEY-315-END

원본 답:
```text
KEY-315-END
```

편집 답:
```text
Copy the following string: KEY-315-END

Copy the following string: KEY-315-END

Copy the following string: KEY-315-END
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### moon_en:plain / preserve:4 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-318-END

지도 정답: KEY-318-END

원본 답:
```text
KEY-318-END
```

편집 답:
```text
적으세요.
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### moon_en:plain / preserve:8 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-322-END

지도 정답: KEY-322-END

원본 답:
```text
KEY-322-END
```

편집 답:
```text
적으세요.
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### moon_en:plain / preserve:9 / protect

질문: Copy the following string exactly: KEY-323-END

지도 정답: KEY-323-END

원본 답:
```text
KEY-323-END
```

편집 답:
```text
Copy the following string: KEY-323-END

Copy the following string: KEY-323-END

Copy the following string: KEY-323-END
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### moon_en:plain / preserve:12 / protect

질문: 다음 문자열만 그대로 적으세요: KEY-326-END

지도 정답: KEY-326-END

원본 답:
```text
KEY-326-END
```

편집 답:
```text
적으세요.
```

엄격 판정: True → False; 종료: STOP_SEQUENCE

### moon_en:plain / preserve:13 / protect

질문: Copy the following string exactly: KEY-327-END

지도 정답: KEY-327-END

원본 답:
```text
KEY-327-END
```

편집 답:
```text

The following string contains the following: KEY-327-END

The following string contains the following: KEY-327-END

The following string contains the following: KEY-327-END

The following string contains the following: KE
```

엄격 판정: True → False; 종료: MAX_NEW

