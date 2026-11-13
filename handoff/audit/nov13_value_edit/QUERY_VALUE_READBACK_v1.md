# Stage16 마지막 입력 위치의 실제 원답 판독

총괄이 원래 답과 실제 편집의 목표52쌍, 달라진 보호18쌍을 읽었다. 아래 원답은 표시용 정제 없이 보존한다.
이미 공개한 표현이며 독립 평가가 아니다. 모든12편집은 norm5% 초과의 큰편집진단이고 기본채택0이다.
fit22/24·dev1/12·표현1/16과 다른 표현의 질문복사/오답·보호 손상을 함께 기록한다.
영어 독일 fit의 원답은 Berlin을 포함한 맞는 사실문장이라 짧은답 개선을 모두 새 지식 획득으로 세지 않는다.
영어 산소 표현4는 Sulfuric acid에서 O2, 영어 이탈리아 dev는 Middle East에서 Rome으로 바뀌었다.
한국어 달 편집은 KEY-323-END 복사를 질문나열로 망가뜨렸다. 보호 정답의 단순합85/192는 같은16문항을12번 재사용한 수다.
판독 범위는52+18쌍이며 무작위팔/전체1668답의 전사 의미검수 완료라고 하지 않는다.

## 목표 질문

### kr_capital:last_value_write / kr_capital:0 / fit

```plaintext
질문: 대한민국의 수도는 어디입니까? 도시 이름만 쓰세요.
정답 계약: 서울
원래 답:
도시 이름만 쓰세요.
편집 후 답:
서울
```
엄격 판정: True; 종료: STOP_SEQUENCE

### kr_capital:last_value_write / kr_capital:1 / fit

```plaintext
질문: 대한민국의 수도 이름만 답하세요.
정답 계약: 서울
원래 답:
대한민국의 수도 이름만 답하세요.
편집 후 답:
서울
```
엄격 판정: True; 종료: STOP_SEQUENCE

### kr_capital:last_value_write / kr_capital:2 / dev

```plaintext
질문: 어느 도시가 대한민국의 수도인지 한 단어로 답하세요.
정답 계약: 서울
원래 답:
한국 전쟁
편집 후 답:
한국
```
엄격 판정: False; 종료: STOP_SEQUENCE

### fr_capital_ko:last_value_write / fr_capital_ko:0 / fit

```plaintext
질문: 프랑스의 수도는 어디입니까? 도시 이름만 쓰세요.
정답 계약: 파리
원래 답:
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
편집 후 답:
파리
```
엄격 판정: True; 종료: STOP_SEQUENCE

### fr_capital_ko:last_value_write / fr_capital_ko:1 / fit

```plaintext
질문: 프랑스의 수도 이름만 답하세요.
정답 계약: 파리
원래 답:
바이올린 수도자
편집 후 답:
파리
```
엄격 판정: True; 종료: STOP_SEQUENCE

### fr_capital_ko:last_value_write / fr_capital_ko:2 / dev

```plaintext
질문: 어느 도시가 프랑스의 수도인지 한 단어로 답하세요.
정답 계약: 파리
원래 답:
프랑스의 수도인지
편집 후 답:
상호작용
```
엄격 판정: False; 종료: STOP_SEQUENCE

### water_ko:last_value_write / water_ko:0 / fit

```plaintext
질문: 물의 화학식을 쓰세요. 화학식만 답하세요.
정답 계약: H2O
원래 답:
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.
공기식만 답하세요. 화학식만 답하세요.

편집 후 답:
H2O
```
엄격 판정: True; 종료: STOP_SEQUENCE

### water_ko:last_value_write / water_ko:1 / fit

```plaintext
질문: 물의 화학식은? 답만 쓰세요.
정답 계약: H2O
원래 답:
공기 삼중 주기율표(공기 삼중 주기율표)
편집 후 답:
H2O
```
엄격 판정: True; 종료: STOP_SEQUENCE

### water_ko:last_value_write / water_ko:2 / dev

```plaintext
질문: 물 분자의 화학식을 기호와 숫자로만 답하세요.
정답 계약: H2O
원래 답:
공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다.

공중핵과 같은 화학식은 ρ(n)이고, 화학식은 ρ(n)이다. 화학식은 ρ(n)이고, 화학식은 ρ(n)
편집 후 답:
공중핵자화식
```
엄격 판정: False; 종료: STOP_SEQUENCE

### earth_ko:last_value_write / earth_ko:0 / fit

```plaintext
질문: 지구가 공전하는 별은 무엇입니까? 이름만 답하세요.
정답 계약: 태양
원래 답:
은거하는 별은 무엇입니까? 본인입니다.
편집 후 답:
태양
```
엄격 판정: True; 종료: STOP_SEQUENCE

### earth_ko:last_value_write / earth_ko:1 / fit

```plaintext
질문: 지구는 어느 별 주위를 공전합니까? 별 이름만 쓰세요.
정답 계약: 태양
원래 답:
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
편집 후 답:
태양
```
엄격 판정: True; 종료: STOP_SEQUENCE

### earth_ko:last_value_write / earth_ko:2 / dev

```plaintext
질문: 지구의 공전 중심인 별 이름만 답하세요.
정답 계약: 태양
원래 답:
지구가 별에 속하지 않는 별들.

각주 

지구의 목성
목성형 행성
목성형 행성
1981년 발견한 외계 행성
목성형 절
편집 후 답:
2
```
엄격 판정: False; 종료: STOP_SEQUENCE

### de_capital_ko:last_value_write / de_capital_ko:0 / fit

```plaintext
질문: 독일의 수도는 어디입니까? 도시 이름만 쓰세요.
정답 계약: 베를린
원래 답:
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요.
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요.
독일의 수도는 어디입니까? 도시 이름만 쓰세요.
독일의 도시 이름만 쓰세요
편집 후 답:
베를린
```
엄격 판정: True; 종료: STOP_SEQUENCE

### de_capital_ko:last_value_write / de_capital_ko:1 / fit

```plaintext
질문: 독일의 수도 이름만 답하세요.
정답 계약: 베를린
원래 답:
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
편집 후 답:
베를린
```
엄격 판정: True; 종료: STOP_SEQUENCE

### de_capital_ko:last_value_write / de_capital_ko:2 / dev

```plaintext
질문: 어느 도시가 독일의 수도인지 한 단어로 답하세요.
정답 계약: 베를린
원래 답:
독일의 수도인지 한단어의 답하세요.
편집 후 답:
독일의 수도인지
```
엄격 판정: False; 종료: STOP_SEQUENCE

### de_capital_ko:last_value_write / de_capital_ko:3 / test

```plaintext
질문: 독일의 수도에 해당하는 도시 이름을 적으세요.
정답 계약: 베를린
원래 답:
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

편집 후 답:

```
엄격 판정: False; 종료: STOP_SEQUENCE

### de_capital_ko:last_value_write / de_capital_ko:4 / test

```plaintext
질문: 나라 독일의 수도는? 답만 쓰세요.
정답 계약: 베를린
원래 답:
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
편집 후 답:
독일의 수도는? 답만 쓰세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### it_capital_ko:last_value_write / it_capital_ko:0 / fit

```plaintext
질문: 이탈리아의 수도는 어디입니까? 도시 이름만 쓰세요.
정답 계약: 로마
원래 답:
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

편집 후 답:
로마
```
엄격 판정: True; 종료: STOP_SEQUENCE

### it_capital_ko:last_value_write / it_capital_ko:1 / fit

```plaintext
질문: 이탈리아의 수도 이름만 답하세요.
정답 계약: 로마
원래 답:
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
편집 후 답:
로마
```
엄격 판정: True; 종료: STOP_SEQUENCE

### it_capital_ko:last_value_write / it_capital_ko:2 / dev

```plaintext
질문: 어느 도시가 이탈리아의 수도인지 한 단어로 답하세요.
정답 계약: 로마
원래 답:
로마 숫자
편집 후 답:
로마 숫자
```
엄격 판정: False; 종료: STOP_SEQUENCE

### it_capital_ko:last_value_write / it_capital_ko:3 / test

```plaintext
질문: 이탈리아의 수도에 해당하는 도시 이름을 적으세요.
정답 계약: 로마
원래 답:
바이올린
편집 후 답:
 적으세요
```
엄격 판정: False; 종료: STOP_SEQUENCE

### it_capital_ko:last_value_write / it_capital_ko:4 / test

```plaintext
질문: 나라 이탈리아의 수도는? 답만 쓰세요.
정답 계약: 로마
원래 답:
나라 이탈리아의 수도는? 답만 쓰세요.
편집 후 답:
나라 이탈리아의 수도는? 답만 쓰세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### oxygen_ko:last_value_write / oxygen_ko:0 / fit

```plaintext
질문: 산소 분자의 화학식을 쓰세요. 화학식만 답하세요.
정답 계약: O2
원래 답:
산소 분자의 화학식만 답하세요. 화학식만 답하세요.
편집 후 답:
O2
```
엄격 판정: True; 종료: STOP_SEQUENCE

### oxygen_ko:last_value_write / oxygen_ko:1 / fit

```plaintext
질문: 산소 분자의 화학식은? 답만 쓰세요.
정답 계약: O2
원래 답:
산소 분자의 화학식은? 답만 쓰세요.
편집 후 답:
O2
```
엄격 판정: True; 종료: STOP_SEQUENCE

### oxygen_ko:last_value_write / oxygen_ko:2 / dev

```plaintext
질문: 산소 분자의 화학식을 기호와 숫자로만 답하세요.
정답 계약: O2
원래 답:
산소 분자의 화학식은 Cg(Ca)2O3.
편집 후 답:
산소 분자의 화학식은 CgO3.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### oxygen_ko:last_value_write / oxygen_ko:3 / test

```plaintext
질문: 산소 분자에 해당하는 화학식 한 개만 적으세요.
정답 계약: O2
원래 답:
산소 분자에 해당하는 화학식 한 개만 적으세요.
편집 후 답:
산소 분자에 해당하는 화학식 한 개만 적으세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### oxygen_ko:last_value_write / oxygen_ko:4 / test

```plaintext
질문: 다른 설명 없이 산소 분자의 화학식을 알려주세요.
정답 계약: O2
원래 답:
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

편집 후 답:
산소 분자의 화학식은 H2O2.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### moon_ko:last_value_write / moon_ko:0 / fit

```plaintext
질문: 달이 공전하는 행성은 무엇입니까? 행성 이름만 답하세요.
정답 계약: 지구
원래 답:
주 사건은 행성 이름만 답하세요.

참고 문헌 

목성형 행성
2007년 발견한 외계 행성
목성형 절치기
편집 후 답:
지구보다 더 큰 행성을 답하세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### moon_ko:last_value_write / moon_ko:1 / fit

```plaintext
질문: 달은 어느 행성 주위를 공전합니까? 이름만 쓰세요.
정답 계약: 지구
원래 답:
달은 어느 행성 주위를 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데 도움이 되는 별들을 공전하는 데
편집 후 답:
지구
```
엄격 판정: True; 종료: STOP_SEQUENCE

### moon_ko:last_value_write / moon_ko:2 / dev

```plaintext
질문: 달의 공전 중심인 행성 이름만 답하세요.
정답 계약: 지구
원래 답:
주마이의 별들
쌍둥이자리
A형 주계열성
플램스티드 천체
플램스티드-2형 거성체
0333
0333
0334
편집 후 답:
 달의 중심인 행성 이름 정보가 답하세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### moon_ko:last_value_write / moon_ko:3 / test

```plaintext
질문: 달이 궤도를 따라 도는 행성의 이름을 적으세요.
정답 계약: 지구
원래 답:
공기거북(公基居北)
편집 후 답:
공기거목(公基居木)
```
엄격 판정: False; 종료: STOP_SEQUENCE

### moon_ko:last_value_write / moon_ko:4 / test

```plaintext
질문: 달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.
정답 계약: 지구
원래 답:
달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.
편집 후 답:
달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### de_capital_en:last_value_write / de_capital_en:0 / fit

```plaintext
질문: What is the capital of Germany? Return only the city name.
정답 계약: Berlin
원래 답:
The capital of Germany is the city of Berlin.
편집 후 답:
Berlin
```
엄격 판정: True; 종료: STOP_SEQUENCE

### de_capital_en:last_value_write / de_capital_en:1 / fit

```plaintext
질문: Name only the capital city of Germany.
정답 계약: Berlin
원래 답:
German
편집 후 답:
Berlin
```
엄격 판정: True; 종료: STOP_SEQUENCE

### de_capital_en:last_value_write / de_capital_en:2 / dev

```plaintext
질문: Which city serves as the capital of Germany? Answer with the name only.
정답 계약: Berlin
원래 답:
The city of Germany is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria.
편집 후 답:
The city of Germany is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria. It is the capital of the German state of Bavaria.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### de_capital_en:last_value_write / de_capital_en:3 / test

```plaintext
질문: Give the capital of the country Germany, without explanation.
정답 계약: Berlin
원래 답:

편집 후 답:

```
엄격 판정: False; 종료: STOP_SEQUENCE

### de_capital_en:last_value_write / de_capital_en:4 / test

```plaintext
질문: Germany has a capital city. What is its name?
정답 계약: Berlin
원래 답:
The city is located in the heart of the country. It is a small town with a population of over 1,000,000. The city is located in the heart of the country.
편집 후 답:
The city is located in the heart of the country. It is located in the heart of the country.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### it_capital_en:last_value_write / it_capital_en:0 / fit

```plaintext
질문: What is the capital of Italy? Return only the city name.
정답 계약: Rome
원래 답:
The capital of Italy is the city of the Duchy of Bologna.
편집 후 답:
Rome
```
엄격 판정: True; 종료: STOP_SEQUENCE

### it_capital_en:last_value_write / it_capital_en:1 / fit

```plaintext
질문: Name only the capital city of Italy.
정답 계약: Rome
원래 답:
The capital of Italy is the city of the Cologne.
편집 후 답:
Rome
```
엄격 판정: True; 종료: STOP_SEQUENCE

### it_capital_en:last_value_write / it_capital_en:2 / dev

```plaintext
질문: Which city serves as the capital of Italy? Answer with the name only.
정답 계약: Rome
원래 답:
Middle East
편집 후 답:
Rome
```
엄격 판정: True; 종료: STOP_SEQUENCE

### it_capital_en:last_value_write / it_capital_en:3 / test

```plaintext
질문: Give the capital of the country Italy, without explanation.
정답 계약: Rome
원래 답:

편집 후 답:

```
엄격 판정: False; 종료: STOP_SEQUENCE

### it_capital_en:last_value_write / it_capital_en:4 / test

```plaintext
질문: Italy has a capital city. What is its name?
정답 계약: Rome
원래 답:
The capital city of the country is the Republic of the Netherlands. It is located in the Netherlands, and is the capital of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands. The capital is the Netherlands of the Netherlands.
편집 후 답:
The capital city of the United Kingdom is London. It is the capital of the United Kingdom of Great Britain. It is the capital of the United Kingdom of the United Kingdom of Great Britain. It is the capital of the United Kingdom of the United Kingdom of Great Britain.

The capital of the United Kingdom of Great
```
엄격 판정: False; 종료: MAX_NEW

### oxygen_en:last_value_write / oxygen_en:0 / fit

```plaintext
질문: What is the chemical formula for an oxygen molecule? Give only the formula.
정답 계약: O2
원래 답:
Oxygen is a chemical compound that is found in many living organisms, including bacteria, fungi, and plants. It is also found in many living things, including plants, animals, and bacteria.
편집 후 답:
O2
```
엄격 판정: True; 종료: STOP_SEQUENCE

### oxygen_en:last_value_write / oxygen_en:1 / fit

```plaintext
질문: Write only the chemical formula of an oxygen molecule.
정답 계약: O2
원래 답:
Chemically, oxygen is the most common form of oxygen in the body. It is the most common form of oxygen in the body. It is the most common form of oxygen in the body.
편집 후 답:
O2
```
엄격 판정: True; 종료: STOP_SEQUENCE

### oxygen_en:last_value_write / oxygen_en:2 / dev

```plaintext
질문: State the formula of an oxygen molecule with no explanation.
정답 계약: O2
원래 답:
The oxygen molecule is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is
편집 후 답:
The oxygen molecule is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is a molecule with a very small amount of oxygen. It is
```
엄격 판정: False; 종료: MAX_NEW

### oxygen_en:last_value_write / oxygen_en:3 / test

```plaintext
질문: Return the formula of an oxygen molecule, using symbols and digits.
정답 계약: O2
원래 답:
Return the formula of an oxygen molecule to the left of the right-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand-hand.
편집 후 답:
Return the formula of an oxygen molecule to the oxygen molecule.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### oxygen_en:last_value_write / oxygen_en:4 / test

```plaintext
질문: Give the formula for an oxygen molecule. Formula only.
정답 계약: O2
원래 답:
Sulfuric acid
편집 후 답:
O2
```
엄격 판정: True; 종료: STOP_SEQUENCE

### moon_en:last_value_write / moon_en:0 / fit

```plaintext
질문: Which planet does the Moon orbit? Give only its name.
정답 계약: Earth
원래 답:
The Moon is the second-most-laid planet in the solar system. It is the third-most-laid planet in the solar system.
편집 후 답:
Earth's Moon is the second-bassest planet in the Solar System.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### moon_en:last_value_write / moon_en:1 / fit

```plaintext
질문: Name only the planet that the Moon goes around.
정답 계약: Earth
원래 답:
The Moon is the planet that the Sun is on.
편집 후 답:
Earth
```
엄격 판정: True; 종료: STOP_SEQUENCE

### moon_en:last_value_write / moon_en:2 / dev

```plaintext
질문: What planet is at the center of the orbit of the Moon? Name only.
정답 계약: Earth
원래 답:
The Moon is a small, dark, and densely-laced, with a diameter of about 1.5 billion kilometers (1.5 billion miles) and a radius of about 1.5 billion kilometers (1.5 billion miles). The Moon is also a small, dark, and densely-laced
편집 후 답:
The Moon is a small, dark, and densely-laced, with a diameter of about 1.5 billion kilometers (1.5 billion miles) and a radius of about 1.5 billion kilometers (1.5 billion miles). The Moon is also a small, dark, and densely-laced
```
엄격 판정: False; 종료: MAX_NEW

### moon_en:last_value_write / moon_en:3 / test

```plaintext
질문: Identify the planet orbited by the Moon. Return the name alone.
정답 계약: Earth
원래 답:
The Moon is a small, dark, and rocky planet orbiting the Sun. It is about 3.5 billion kilometers (1.5 billion mi) across. The Moon is about 3.5 billion miles (1.5 billion mi) wide. The Moon is about 3.5 billion miles (1.5
편집 후 답:
The Moon is a small, dark, and rocky planet orbiting the Sun. It is about 3.5 billion kilometers (1.5 billion mi) across. The Moon is about 3.5 billion miles (1.5 billion mi) wide. The Moon is about 3.5 billion miles (1.5
```
엄격 판정: False; 종료: MAX_NEW

### moon_en:last_value_write / moon_en:4 / test

```plaintext
질문: The Moon revolves around which planet? Write only the name.
정답 계약: Earth
원래 답:
The Moon is a small, slender, slim, slender, slimless planet that is about the size of a football field. It is about a million miles from the Sun.
편집 후 답:
The Moon revolves around the sun.
```
엄격 판정: False; 종료: STOP_SEQUENCE

## 답이 달라진 보호 질문

### kr_capital:last_value_write / preserve:10 / protect

```plaintext
질문: 의자을 공백으로 구분하여 정확히 세 번 적으세요.
정답 계약: 의자 의자 의자
원래 답:
의자을 공백으로 구분.
편집 후 답:
세 번 적으세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### fr_capital_ko:last_value_write / preserve:3 / protect

```plaintext
질문: Write blue exactly three times separated by spaces.
정답 계약: blue blue blue
원래 답:
The blue is the number of times separated by spaces.
편집 후 답:
The blue is the number of blue spaces separated by spaces.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### fr_capital_ko:last_value_write / preserve:15 / protect

```plaintext
질문: Write lamp exactly three times separated by spaces.
정답 계약: lamp lamp lamp
원래 답:
Line two times separated by spaces separated by spaces.
편집 후 답:
Line the lamp with the lamp and place it on the lamp.

The lamp is in the lamp.

The lamp is in the lamp.

The lamp is in the lamp.

The lamp is in the lamp.

The
```
엄격 판정: False; 종료: MAX_NEW

### water_ko:last_value_write / preserve:3 / protect

```plaintext
질문: Write blue exactly three times separated by spaces.
정답 계약: blue blue blue
원래 답:
The blue is the number of times separated by spaces.
편집 후 답:
The blue is the result of the same process as the blue.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### earth_ko:last_value_write / preserve:10 / protect

```plaintext
질문: 의자을 공백으로 구분하여 정확히 세 번 적으세요.
정답 계약: 의자 의자 의자
원래 답:
의자을 공백으로 구분.
편집 후 답:
세 번 적으세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### de_capital_ko:last_value_write / preserve:6 / protect

```plaintext
질문: 책을 공백으로 구분하여 정확히 세 번 적으세요.
정답 계약: 책 책 책
원래 답:
세 번 적으세요.
편집 후 답:
 적으세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### de_capital_ko:last_value_write / preserve:15 / protect

```plaintext
질문: Write lamp exactly three times separated by spaces.
정답 계약: lamp lamp lamp
원래 답:
Line two times separated by spaces separated by spaces.
편집 후 답:
Line the lamp with the lamp and place it on the lamp.

The lamp is in the lamp.

The lamp is in the lamp.

The lamp is in the lamp.

The lamp is in the lamp.

The
```
엄격 판정: False; 종료: MAX_NEW

### it_capital_ko:last_value_write / preserve:3 / protect

```plaintext
질문: Write blue exactly three times separated by spaces.
정답 계약: blue blue blue
원래 답:
The blue is the number of times separated by spaces.
편집 후 답:
The blue is the result of the same process as the blue.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### it_capital_ko:last_value_write / preserve:5 / protect

```plaintext
질문: Copy the following string exactly: KEY-319-END
정답 계약: KEY-319-END
원래 답:
Copy the following string: KEY-319-END

Copy the following string: KEY-319-END

Copy the following string: KEY-319-END
편집 후 답:
KEY-319-END
```
엄격 판정: True; 종료: STOP_SEQUENCE

### oxygen_ko:last_value_write / preserve:3 / protect

```plaintext
질문: Write blue exactly three times separated by spaces.
정답 계약: blue blue blue
원래 답:
The blue is the number of times separated by spaces.
편집 후 답:
The blue is the result of the same process as the blue.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### moon_ko:last_value_write / preserve:9 / protect

```plaintext
질문: Copy the following string exactly: KEY-323-END
정답 계약: KEY-323-END
원래 답:
KEY-323-END
편집 후 답:
Copy the following string: KEY-323-END

Copy the following string: KEY-323-END

Copy the following string: KEY-323-END
```
엄격 판정: False; 종료: STOP_SEQUENCE

### moon_ko:last_value_write / preserve:10 / protect

```plaintext
질문: 의자을 공백으로 구분하여 정확히 세 번 적으세요.
정답 계약: 의자 의자 의자
원래 답:
의자을 공백으로 구분.
편집 후 답:
세 번 적으세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### de_capital_en:last_value_write / preserve:3 / protect

```plaintext
질문: Write blue exactly three times separated by spaces.
정답 계약: blue blue blue
원래 답:
The blue is the number of times separated by spaces.
편집 후 답:
The blue is the result of the same process as the blue.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### it_capital_en:last_value_write / preserve:3 / protect

```plaintext
질문: Write blue exactly three times separated by spaces.
정답 계약: blue blue blue
원래 답:
The blue is the number of times separated by spaces.
편집 후 답:
The blue is separated by spaces.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### oxygen_en:last_value_write / preserve:3 / protect

```plaintext
질문: Write blue exactly three times separated by spaces.
정답 계약: blue blue blue
원래 답:
The blue is the number of times separated by spaces.
편집 후 답:
The blue is the result of the same process as the blue.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### oxygen_en:last_value_write / preserve:5 / protect

```plaintext
질문: Copy the following string exactly: KEY-319-END
정답 계약: KEY-319-END
원래 답:
Copy the following string: KEY-319-END

Copy the following string: KEY-319-END

Copy the following string: KEY-319-END
편집 후 답:
KEY-319-END
```
엄격 판정: True; 종료: STOP_SEQUENCE

### oxygen_en:last_value_write / preserve:10 / protect

```plaintext
질문: 의자을 공백으로 구분하여 정확히 세 번 적으세요.
정답 계약: 의자 의자 의자
원래 답:
의자을 공백으로 구분.
편집 후 답:
세 번 적으세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

### moon_en:last_value_write / preserve:10 / protect

```plaintext
질문: 의자을 공백으로 구분하여 정확히 세 번 적으세요.
정답 계약: 의자 의자 의자
원래 답:
의자을 공백으로 구분.
편집 후 답:
세 번 적으세요.
```
엄격 판정: False; 종료: STOP_SEQUENCE

