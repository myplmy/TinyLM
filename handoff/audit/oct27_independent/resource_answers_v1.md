# 완료 TinyLM 5모델의 실제 질문·답 원문

2026-10-27 Stage11bW의 CUDA 원답 20개다. 정식 벤치마크나 새 소규모 학습의 지능평가가 아니다. FP32/MATH·KV on·MTP off·greedy·최대64토큰이며 산수는 plain, 대상 질문은 ChatML이다. CPU 원답과 토큰은 연결 JSON에 별도 보존한다. 출력에 정답 단어가 있어도 대상·종료·문장 전체가 적절한지 따로 읽어야 한다.

## native595-q / ko_arithmetic

질문: 1+1은?

답변 원문:

```text


같이 보기 
 제3의 법칙
 제4의 법칙
 제5의 법칙
 제6의 법칙
 제7의 법칙
 제8의 법칙
 제9의 법칙
 제10의 법칙
 제11의 법칙
 제12의 법칙
 제13의 법칙
 제14의 법칙
```

종료: MAX_NEW / 생성 64토큰

## native595-q / en_arithmetic

질문: What is 1+1? Give only the answer.

답변 원문:

```text

- 1+1 = 1+1 = 1+1 = 1+1 = 1+1 = 1+1 = 1+1 = 1+1 = 1+1 = 1+1 = 1+1 = 1+1 = 1+1 = 1+1 = 1+1 = 1+
```

종료: MAX_NEW / 생성 64토큰

## native595-q / ko_context

질문: A는 사과고 B는 당근이다. B는 무엇인가? 답만 쓰세요.

답변 원문:

```text
A는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근
```

종료: MAX_NEW / 생성 64토큰

## native595-q / en_context

질문: A is an apple and B is a carrot. What is B? Give only the answer.

답변 원문:

```text
A is a carrot, a is a carrot, a is a carrot, a is a carrot, a is a carrot, a is a carrot, a is a carrot, a is a carrot, a is a carrot, a is a carrot, a is a car
```

종료: MAX_NEW / 생성 64토큰

## native595-f / ko_arithmetic

질문: 1+1은?

답변 원문:

```text
+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1
```

종료: MAX_NEW / 생성 64토큰

## native595-f / en_arithmetic

질문: What is 1+1? Give only the answer.

답변 원문:

```text

- What is the difference between 1+1 and 1+1?
- What is the difference between 1+1 and 1+1?
- What is the difference between 1+1 and 1+1?
- What is the difference between 1+1 and 1+1?
- What is
```

종료: MAX_NEW / 생성 64토큰

## native595-f / ko_context

질문: A는 사과고 B는 당근이다. B는 무엇인가? 답만 쓰세요.

답변 원문:

```text

같이 보기 
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고
 사과고

```

종료: MAX_NEW / 생성 64토큰

## native595-f / en_context

질문: A is an apple and B is a carrot. What is B? Give only the answer.

답변 원문:

```text
A is a carrot. What is B? Give only the answer.
B is a carrot. What is B? Give only the answer.
B is a carrot. What is B? Give only the answer.
B is a carrot. What is B? Give only the answer.

```

종료: MAX_NEW / 생성 64토큰

## new595-broad-f / ko_arithmetic

질문: 1+1은?

답변 원문:

```text


같이 보기 
 비전

각주

외부 링크 

대한민국의 자동차 제조 기업
대한민국의 브랜드
대한민국의 브랜드
대한민국의 자동차 제조 기업
대한민국의 브랜드
대한민국의 브랜드
대한민국의 브랜드
대한민국의 브랜드
대한민국의 브랜드
대한민국의 브랜드
대한민국의 브랜드
대한민국의 자동차 제조 기업
대한민국의 브랜드
대한민국의 자동차 제조
```

종료: MAX_NEW / 생성 64토큰

## new595-broad-f / en_arithmetic

질문: What is 1+1? Give only the answer.

답변 원문:

```text

2+1 = 1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1
```

종료: MAX_NEW / 생성 64토큰

## new595-broad-f / ko_context

질문: A는 사과고 B는 당근이다. B는 무엇인가? 답만 쓰세요.

답변 원문:

```text
B는 사과고입니다.<|im_end|>
```

종료: STOP_SEQUENCE / 생성 7토큰

## new595-broad-f / en_context

질문: A is an apple and B is a carrot. What is B? Give only the answer.

답변 원문:

```text
Ba<|im_end|>
```

종료: STOP_SEQUENCE / 생성 3토큰

## format_muon / ko_arithmetic

질문: 1+1은?

답변 원문:

```text


1.1+1은 
1.1+1은 
1.1+1은 
1.1+1은 
1.1+1은 
1.1+1은 
1.1+1은 
1.1+1은
```

종료: MAX_NEW / 생성 64토큰

## format_muon / en_arithmetic

질문: What is 1+1? Give only the answer.

답변 원문:

```text

- What is the difference between the two?
- What is the difference between the two?
- What is the difference between the two?
- What is the difference between the two?
- What is the difference between the two?
- What is the difference between the two?
- What is
```

종료: MAX_NEW / 생성 64토큰

## format_muon / ko_context

질문: A는 사과고 B는 당근이다. B는 무엇인가? 답만 쓰세요.

답변 원문:

```text
A는 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고 B가 사과고
```

종료: MAX_NEW / 생성 64토큰

## format_muon / en_context

질문: A is an apple and B is a carrot. What is B? Give only the answer.

답변 원문:

```text
A is a carrot that is made from a variety of materials. It is made from a variety of materials.
A is a carrot made from a variety of materials. It is made from a variety of materials.
A is a carrot made from a variety of materials. It is made from a variety
```

종료: MAX_NEW / 생성 64토큰

## format_normuon / ko_arithmetic

질문: 1+1은?

답변 원문:

```text


같이 보기 
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
 라오스
```

종료: MAX_NEW / 생성 64토큰

## format_normuon / en_arithmetic

질문: What is 1+1? Give only the answer.

답변 원문:

```text

- 1+1 is the answer.
- 1+1 is the answer.
- 1+1 is the answer.
- 1+1 is the answer.
- 1+1 is the answer.
- 1+1 is the answer.
- 1+1 is the answer.

```

종료: MAX_NEW / 생성 64토큰

## format_normuon / ko_context

질문: A는 사과고 B는 당근이다. B는 무엇인가? 답만 쓰세요.

답변 원문:

```text
B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고 B는 사과고
```

종료: MAX_NEW / 생성 64토큰

## format_normuon / en_context

질문: A is an apple and B is a carrot. What is B? Give only the answer.

답변 원문:

```text
A is a carrot. What is B? Give only the answer.oggle.oggle.oggle.oggle.oggle.oggle.oggle.oggle.oggle.oggle.oggle.oggle.oggle.oggle.oggle.oggle.ogg
```

종료: MAX_NEW / 생성 64토큰
